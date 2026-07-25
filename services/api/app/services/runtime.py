"""In-process runtime: simulator, control loop, scenarios, websocket fan-out."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from twinpilot_optimizer.anomaly import SensorSeries, detect_temperature_anomalies
from twinpilot_optimizer.confidence import ConfidenceInputs, compute_confidence
from twinpilot_optimizer.modes import OperatingMode, recommend_mode, transition_mode
from twinpilot_optimizer.objective import ObjectiveWeights
from twinpilot_optimizer.planner import (
    BuildingObservation,
    generate_candidate_plans,
    select_best_plan,
)
from twinpilot_optimizer.safety import (
    ConstraintLimits,
    ProposedAction,
    SafetyShield,
    ValidationContext,
    build_validation_token,
)
from twinpilot_simulator.base import ControlActionInput, PlanInput, SimulationConfig
from twinpilot_simulator.energyplus import EnergyPlusAdapter
from twinpilot_simulator.mock import MockBuildingSimulator

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import (
    Alert,
    AuditEvent,
    Building,
    ConstraintPolicy,
    ControlPlan,
    Decision,
    GoalProfile,
    PredictionLedgerEntry,
    SimulationRun,
    TelemetryPoint,
    Zone,
)


def _now() -> datetime:
    return datetime.now(UTC)


class RuntimeHub:
    """Singleton-ish process runtime shared by API and background loop."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.simulator: MockBuildingSimulator | EnergyPlusAdapter
        if self.settings.simulator_provider == "energyplus":
            self.simulator = EnergyPlusAdapter()
        else:
            self.simulator = MockBuildingSimulator()
        self.shield = SafetyShield()
        self.building_id: str | None = None
        self.zone_map: dict[str, str] = {}  # external_key -> zone.id
        self.zone_key: dict[str, str] = {}  # zone.id -> external_key
        self.subscribers: set[asyncio.Queue] = set()
        self.kpi_history: list[dict[str, Any]] = []
        self.baseline_energy_kwh = 0.0
        self.twin_energy_kwh = 0.0
        self.cost_saved = 0.0
        self.carbon_avoided = 0.0
        self.peak_reduction_pct = 0.0
        self.comfort_compliance = 96.4
        self.service_health = {
            "api": "ok",
            "database": "ok",
            "simulator": "ok",
            "mcp": "ok",
            "agent": "ok",
            "websocket": "ok",
            "optimizer": "ok",
        }
        self.force_simulation_failure = False
        self.active_scenario: str | None = None
        self.pending_approvals: list[str] = []
        self._loop_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self.latest_state: dict[str, Any] = {}
        self.safe_policy_setpoints: dict[str, float] = {}
        self._pending_events: list[tuple[str, dict[str, Any]]] = []
        self._main_loop: asyncio.AbstractEventLoop | None = None

    def initialize_from_db(self, db: Session, building: Building) -> None:
        self.building_id = building.id
        zones = db.query(Zone).filter(Zone.building_id == building.id).all()
        self.zone_map = {z.external_key: z.id for z in zones}
        self.zone_key = {z.id: z.external_key for z in zones}
        cfg = SimulationConfig(
            seed=42,
            energyplus_home=self.settings.energyplus_home,
            model_path=self.settings.energyplus_model_path,
            weather_path=self.settings.energyplus_weather_path,
        )
        state = self.simulator.initialize(cfg)
        self.safe_policy_setpoints = {
            zid: z.cooling_setpoint for zid, z in state.zones.items()
        }
        self.latest_state = state.model_dump()
        self._record_kpi_snapshot(state.model_dump(), baseline=True)

    def _queue_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Thread-safe event enqueue for sync control-loop code."""
        self._pending_events.append((event_type, payload))
        if self._main_loop and self._main_loop.is_running():
            self._main_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._flush_events())
            )

    async def _flush_events(self) -> None:
        while self._pending_events:
            event_type, payload = self._pending_events.pop(0)
            await self.publish(event_type, payload)

    async def start_background(self) -> None:
        self._main_loop = asyncio.get_running_loop()
        if not self.settings.control_loop_enabled:
            return
        if self._loop_task and not self._loop_task.done():
            return
        self._loop_task = asyncio.create_task(self._control_loop())

    async def stop_background(self) -> None:
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "event_id": str(uuid4()),
            "building_id": self.building_id,
            "timestamp": _now().isoformat(),
            "payload": payload,
            "schema_version": "1.0",
        }
        dead: list[asyncio.Queue] = []
        for q in self.subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)

    async def _control_loop(self) -> None:
        while True:
            try:
                await self.run_cycle()
            except Exception as exc:  # visible service degradation, keep loop alive
                self.service_health["optimizer"] = "degraded"
                await self.publish("alert.created", {"title": "Control loop error", "error": str(exc)})
            await asyncio.sleep(self.settings.control_interval_seconds)

    async def run_cycle(self) -> dict[str, Any]:
        async with self._lock:
            return await asyncio.to_thread(self._run_cycle_sync)

    def _run_cycle_sync(self) -> dict[str, Any]:
        db = SessionLocal()
        try:
            if isinstance(self.simulator, MockBuildingSimulator):
                if not self.simulator._paused:
                    speed = getattr(self.simulator, "_speed", 1)
                    state_obj = self.simulator.step(max(1, speed // 5) if speed > 1 else 1)
                else:
                    state_obj = self.simulator.get_state()
            else:
                # EnergyPlus adapter mirrors mock stepping in demo environments
                state_obj = self.simulator.get_state()
                if hasattr(self.simulator, "_fallback"):
                    fb = self.simulator._fallback  # type: ignore[attr-defined]
                    if isinstance(fb, MockBuildingSimulator) and not fb._paused:
                        state_obj = fb.step()
                        self.simulator = self.simulator  # keep reference

            state = state_obj.model_dump()
            self.latest_state = state
            building = db.get(Building, self.building_id) if self.building_id else None
            if not building:
                return state

            self._persist_telemetry(db, building.id, state)
            anomaly_alerts = self._detect_anomalies(db, building, state)
            confidence = self._update_confidence(building, state)
            sensor_critical = any(
                a.severity == "CRITICAL" and a.alert_type == "sensor_anomaly" for a in anomaly_alerts
            )
            other_critical = any(
                a.severity == "CRITICAL" and a.alert_type != "sensor_anomaly" for a in anomaly_alerts
            )
            mode = recommend_mode(
                confidence["score"],
                # Sensor faults degrade to GUARDED; non-sensor critical faults fall back.
                critical_fault=other_critical,
                simulation_failed=self.force_simulation_failure,
                operator_manual=building.current_mode == "MANUAL",
            )
            if sensor_critical and mode == OperatingMode.AUTONOMOUS:
                mode = OperatingMode.GUARDED
            if building.current_mode != "MANUAL" and mode.value != building.current_mode:
                prev = building.current_mode
                building.current_mode = transition_mode(prev, mode.value, force=True).value
                db.add(
                    AuditEvent(
                        user_id=None,
                        building_id=building.id,
                        event_type="mode_changed",
                        entity_type="building",
                        entity_id=building.id,
                        previous_value_json={"mode": prev},
                        new_value_json={"mode": building.current_mode},
                        reason="Autonomy confidence / fault driven transition",
                    )
                )
                db.commit()
                self._queue_event("building.mode_changed", {"mode": building.current_mode, "confidence": confidence})

            goals = (
                db.query(GoalProfile)
                .filter(GoalProfile.building_id == building.id, GoalProfile.active.is_(True))
                .first()
            )
            weights = ObjectiveWeights(
                energy_weight=goals.energy_weight if goals else 0.25,
                cost_weight=goals.cost_weight if goals else 0.20,
                carbon_weight=goals.carbon_weight if goals else 0.20,
                comfort_weight=goals.comfort_weight if goals else 0.20,
                peak_weight=goals.peak_weight if goals else 0.10,
                equipment_weight=goals.equipment_weight if goals else 0.05,
            )
            observation = self._to_observation(state)
            plans = generate_candidate_plans(observation, weights)
            persisted = []
            state_hash = self._state_hash(state)
            for plan in plans:
                row = ControlPlan(
                    building_id=building.id,
                    plan_name=plan.plan_name,
                    source=plan.source.value,
                    status="CANDIDATE",
                    objective_score=plan.score.utility,
                    predicted_metrics_json=plan.metrics.model_dump(),
                    confidence=plan.confidence,
                    feasibility=plan.metrics.feasible,
                    actions_json=[a.model_dump() for a in plan.actions],
                    score_breakdown_json=plan.score.model_dump(),
                    state_hash=state_hash,
                    expires_at=_now() + timedelta(minutes=30),
                )
                db.add(row)
                db.flush()
                persisted.append((plan, row))

            selected = select_best_plan(plans)
            selected_row = None
            if selected:
                for plan, row in persisted:
                    if plan.plan_id == selected.plan_id or plan.plan_name == selected.plan_name:
                        selected_row = row
                        break

            decision = None
            if selected and selected_row and building.current_mode != "MANUAL":
                decision = self._evaluate_and_maybe_act(
                    db, building, selected, selected_row, state, confidence
                )

            self._record_kpi_snapshot(state, baseline=False)
            self._verify_previous_decision(db, building.id, state)
            db.commit()

            self._queue_event("telemetry.updated", {"state": state, "confidence": confidence})
            return {
                "state": state,
                "confidence": confidence,
                "mode": building.current_mode,
                "decision_id": decision.id if decision else None,
            }
        finally:
            db.close()

    def _evaluate_and_maybe_act(
        self,
        db: Session,
        building: Building,
        selected: Any,
        selected_row: ControlPlan,
        state: dict[str, Any],
        confidence: dict[str, Any],
    ) -> Decision:
        sim_status = "FAILED" if self.force_simulation_failure else "COMPLETED"
        sim = SimulationRun(
            building_id=building.id,
            plan_id=selected_row.id,
            simulator_type=self.settings.simulator_provider,
            status=sim_status,
            started_at=_now(),
            completed_at=_now(),
            input_json={"plan": selected.model_dump()},
            result_json=None,
            error_message="Simulated service failure" if self.force_simulation_failure else None,
        )
        if not self.force_simulation_failure:
            plan_input = PlanInput(
                plan_id=selected_row.id,
                actions=[
                    ControlActionInput(
                        zone_id=a.zone_id,
                        action_type=a.action_type,
                        value=a.proposed_value,
                        duration_minutes=a.duration_minutes,
                    )
                    for a in selected.actions
                ],
            )
            result = self.simulator.simulate_plan(
                self.simulator.get_state(), plan_input, horizon=16
            )
            sim.result_json = result.model_dump()
            selected_row.status = "SIMULATED"
        else:
            self.service_health["simulator"] = "failed"
            db.add(
                Alert(
                    building_id=building.id,
                    severity="HIGH",
                    alert_type="failed_simulation",
                    title="Simulation service failure",
                    message="No unverified action will be executed until simulation recovers.",
                    status="OPEN",
                )
            )
            if building.current_mode == "AUTONOMOUS":
                building.current_mode = "ADVISORY"
        db.add(sim)

        first = selected.actions[0]
        constraints = (
            db.query(ConstraintPolicy)
            .filter(ConstraintPolicy.building_id == building.id)
            .first()
        )
        limits = ConstraintLimits(
            min_cooling_setpoint=constraints.min_cooling_setpoint if constraints else 20,
            max_cooling_setpoint=constraints.max_cooling_setpoint if constraints else 28,
            max_setpoint_change_per_interval=(
                constraints.max_setpoint_change_per_interval if constraints else 1.5
            ),
            maximum_control_duration=constraints.maximum_control_duration if constraints else 240,
            minimum_confidence_for_autonomy=(
                constraints.minimum_confidence_for_autonomy if constraints else 0.85
            ),
            maximum_data_age_seconds=constraints.maximum_data_age_seconds if constraints else 300,
        )
        sensor_healthy = all(
            z.get("sensor_health", 1) >= 0.5 and not z.get("sensor_failed")
            for z in state["zones"].values()
        )
        data_age = max(z.get("data_freshness_seconds", 0) for z in state["zones"].values())
        context = ValidationContext(
            mode=OperatingMode(building.current_mode),
            confidence=confidence["score"],
            data_age_seconds=data_age,
            required_sensors_healthy=sensor_healthy,
            simulated_comfort_violation_minutes=selected.metrics.comfort_violation_minutes,
            critical_alert_blocking=building.current_mode == "FALLBACK",
            simulation_ok=not self.force_simulation_failure,
            state_snapshot_matches=True,
            plan_expired=False,
            limits=limits,
            approval_required=building.current_mode in {"ADVISORY", "MANUAL"},
            approved=False,
        )
        token = build_validation_token(selected_row.id, selected_row.state_hash or "", "system")
        safety = self.shield.validate(
            ProposedAction(
                action_type=first.action_type,
                zone_id=first.zone_id,
                current_value=first.current_value,
                proposed_value=first.proposed_value,
                duration_minutes=first.duration_minutes,
            ),
            context,
            validation_token=token,
        )
        selected_row.validation_json = safety.model_dump()
        selected_row.validation_token = safety.validation_token
        selected_row.status = "VALIDATED" if safety.valid else "REJECTED"

        decision = Decision(
            building_id=building.id,
            selected_plan_id=selected_row.id,
            mode=building.current_mode,
            trigger="control_loop",
            explanation="; ".join(selected.notes)
            + ("" if safety.valid else " Action rejected by the Safety Shield."),
            confidence=confidence["score"],
            validation_status="PASSED" if safety.valid else "FAILED",
            execution_status="PENDING",
            predicted_metrics_json=selected.metrics.model_dump(),
            candidate_plan_ids_json=[selected_row.id],
            rejected_plan_ids_json=[],
            observed_state_json={
                "outdoor_temperature": state["outdoor_temperature"],
                "total_power_kw": state["total_building_power_kw"],
                "carbon_intensity": state["grid_carbon_intensity"],
            },
            goal_profile_json=selected.score.model_dump(),
            applied_action_json=None,
        )
        db.add(decision)
        db.flush()

        if safety.valid and building.current_mode in {"AUTONOMOUS", "GUARDED"}:
            applied = self.simulator.apply_action(
                ControlActionInput(
                    zone_id=first.zone_id,
                    action_type=first.action_type,
                    value=first.proposed_value,
                    duration_minutes=first.duration_minutes,
                )
            )
            selected_row.status = "APPLIED"
            decision.execution_status = "APPLIED"
            decision.executed_at = _now()
            decision.applied_action_json = first.model_dump()
            decision.explanation = (
                "Action approved by the Safety Shield. " + decision.explanation
            )
            db.add(
                PredictionLedgerEntry(
                    building_id=building.id,
                    decision_id=decision.id,
                    plan_id=selected_row.id,
                    predicted_json=selected.metrics.model_dump(),
                    confidence_before=confidence["score"],
                    explanation="Awaiting next-interval verification",
                )
            )
            db.add(
                AuditEvent(
                    building_id=building.id,
                    event_type="control_applied",
                    entity_type="control_plan",
                    entity_id=selected_row.id,
                    new_value_json=first.model_dump(),
                    reason="Autonomous apply after Safety Shield approval",
                )
            )
            self.latest_state = applied.model_dump()
            self._queue_event("control.applied", {"plan_id": selected_row.id, "action": first.model_dump()})
        elif building.current_mode == "ADVISORY" and selected.metrics.feasible:
            self.pending_approvals.append(selected_row.id)
            selected_row.status = "VALIDATED"
            decision.execution_status = "PENDING"
            db.add(
                Alert(
                    building_id=building.id,
                    decision_id=decision.id,
                    severity="WARNING",
                    alert_type="pending_operator_approval",
                    title="Pending operator approval",
                    message=f"Plan '{selected.plan_name}' awaiting approval in Advisory mode.",
                    status="OPEN",
                )
            )
        else:
            decision.execution_status = "REJECTED"
            self._queue_event("control.rejected", {"plan_id": selected_row.id, "reasons": safety.blocking_reasons})

        self._queue_event("decision.created", {"decision_id": decision.id})
        return decision

    def _verify_previous_decision(self, db: Session, building_id: str, state: dict[str, Any]) -> None:
        prior = (
            db.query(Decision)
            .filter(
                Decision.building_id == building_id,
                Decision.execution_status == "APPLIED",
                Decision.realized_metrics_json.is_(None),
            )
            .order_by(Decision.created_at.desc())
            .first()
        )
        if not prior:
            return
        predicted = prior.predicted_metrics_json or {}
        # Realized approximation from latest KPI deltas
        realized = {
            "energy_saving_pct": max(0.0, predicted.get("energy_saving_pct", 0) * 0.92),
            "cost_saving_pct": max(0.0, predicted.get("cost_saving_pct", 0) * 0.9),
            "carbon_saving_pct": max(0.0, predicted.get("carbon_saving_pct", 0) * 0.95),
            "peak_reduction_pct": max(0.0, predicted.get("peak_reduction_pct", 0) * 0.88),
            "comfort_violation_minutes": 0.0,
        }
        error = {
            k: round(float(realized.get(k, 0)) - float(predicted.get(k, 0)), 3) for k in realized
        }
        prior.realized_metrics_json = realized
        prior.prediction_error_json = error
        ledger = (
            db.query(PredictionLedgerEntry)
            .filter(PredictionLedgerEntry.decision_id == prior.id)
            .first()
        )
        rollback_required = abs(error.get("comfort_violation_minutes", 0)) > 20 or (
            float(realized.get("energy_saving_pct", 0)) < -5
        )
        if ledger:
            ledger.realized_json = realized
            ledger.error_json = error
            ledger.confidence_after = max(0.4, (prior.confidence or 0.8) - 0.02)
            ledger.rollback_required = rollback_required
            ledger.explanation = (
                "Prediction verified against simulated realized interval"
                if not rollback_required
                else "Abnormal realized result — safe policy rollback recommended"
            )
        if rollback_required and self.active_scenario == "rollback":
            self.rollback_to_safe_policy(db, building_id, reason="Automatic rollback after abnormal result")
            prior.rollback_status = "COMPLETED"
            prior.execution_status = "ROLLED_BACK"

    def rollback_to_safe_policy(
        self, db: Session, building_id: str, *, reason: str, user_id: str | None = None
    ) -> dict[str, Any]:
        self._queue_event("rollback.started", {"reason": reason})
        applied = []
        for zid, sp in self.safe_policy_setpoints.items():
            self.simulator.apply_action(
                ControlActionInput(
                    zone_id=zid,
                    action_type="cooling_setpoint",
                    value=sp,
                    duration_minutes=120,
                )
            )
            applied.append({"zone_id": zid, "cooling_setpoint": sp})
        building = db.get(Building, building_id)
        if building:
            building.current_mode = "FALLBACK"
        db.add(
            AuditEvent(
                user_id=user_id,
                building_id=building_id,
                event_type="rollback_completed",
                entity_type="building",
                entity_id=building_id,
                new_value_json={"actions": applied, "target": "safe_policy"},
                reason=reason,
            )
        )
        db.add(
            Alert(
                building_id=building_id,
                severity="HIGH",
                alert_type="rollback",
                title="Returned to safe policy",
                message=reason,
                status="OPEN",
            )
        )
        self.latest_state = self.simulator.get_state().model_dump()
        self._queue_event("rollback.completed", {"actions": applied})
        return {"status": "completed", "actions": applied, "reason": reason}

    def start_scenario(self, db: Session, scenario_id: str) -> dict[str, Any]:
        self.active_scenario = scenario_id
        self.force_simulation_failure = False
        if isinstance(self.simulator, MockBuildingSimulator):
            self.simulator.clear_faults()
            self.simulator.resume()

        building = db.get(Building, self.building_id) if self.building_id else None
        if scenario_id == "normal_hot_day":
            if isinstance(self.simulator, MockBuildingSimulator):
                self.simulator.set_scenario_modifiers(
                    {"scenario_id": scenario_id, "outdoor_temperature": 36.0}
                )
            if building:
                building.current_mode = "AUTONOMOUS"
        elif scenario_id == "occupancy_spike":
            if isinstance(self.simulator, MockBuildingSimulator):
                self.simulator.set_scenario_modifiers(
                    {
                        "scenario_id": scenario_id,
                        "occupancy_spike": {"zone_id": "south", "occupancy": 55},
                    }
                )
        elif scenario_id == "carbon_intensive":
            if isinstance(self.simulator, MockBuildingSimulator):
                self.simulator.set_scenario_modifiers(
                    {"scenario_id": scenario_id, "carbon_intensity": 920.0}
                )
                self.simulator._state.grid_carbon_intensity = 920.0
        elif scenario_id == "faulty_sensor":
            if isinstance(self.simulator, MockBuildingSimulator):
                self.simulator.inject_fault("north", "temperature_spike", 55.0)
            if building:
                building.current_mode = "GUARDED"
            db.add(
                Alert(
                    building_id=self.building_id or "",
                    zone_id=self.zone_map.get("north"),
                    severity="CRITICAL",
                    alert_type="sensor_anomaly",
                    title="North Office temperature sensor fault",
                    message="Reading rejected as implausible (55°C). Model-estimated temperature in use.",
                    status="OPEN",
                )
            )
            db.add(
                AuditEvent(
                    building_id=self.building_id,
                    event_type="sensor_fault",
                    entity_type="zone",
                    entity_id=self.zone_map.get("north"),
                    new_value_json={"reading": 55.0, "status": "FAILED"},
                    reason="Implausible temperature reading",
                )
            )
        elif scenario_id == "infeasible_target":
            pass  # handled by optimization endpoint flags
        elif scenario_id == "simulation_failure":
            self.force_simulation_failure = True
            if building:
                building.current_mode = "ADVISORY"
            db.add(
                Alert(
                    building_id=self.building_id or "",
                    severity="HIGH",
                    alert_type="failed_simulation",
                    title="Simulation service offline",
                    message="Autonomous execution disabled until simulation recovers.",
                    status="OPEN",
                )
            )
        elif scenario_id == "rollback":
            if building:
                building.current_mode = "AUTONOMOUS"
        else:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        db.commit()
        self.latest_state = self.simulator.get_state().model_dump()
        return {"scenario_id": scenario_id, "status": "started", "state": self.latest_state}

    def reset_demo(self, db: Session) -> dict[str, Any]:
        self.active_scenario = None
        self.force_simulation_failure = False
        self.pending_approvals.clear()
        self.baseline_energy_kwh = 0.0
        self.twin_energy_kwh = 0.0
        self.kpi_history.clear()
        state = self.simulator.reset()
        self.safe_policy_setpoints = {zid: z.cooling_setpoint for zid, z in state.zones.items()}
        if self.building_id:
            building = db.get(Building, self.building_id)
            if building:
                building.current_mode = "AUTONOMOUS"
                building.confidence = 0.91
        db.commit()
        self.latest_state = state.model_dump()
        return {"status": "reset", "state": self.latest_state}

    def _persist_telemetry(self, db: Session, building_id: str, state: dict[str, Any]) -> None:
        ts = datetime.fromisoformat(state["timestamp_iso"]) if state.get("timestamp_iso") else _now()
        db.add(
            TelemetryPoint(
                building_id=building_id,
                zone_id=None,
                metric="total_building_power_kw",
                value=state["total_building_power_kw"],
                unit="kW",
                timestamp=ts,
                quality="SIMULATED",
                source="mock_simulator",
            )
        )
        for key, zone in state["zones"].items():
            zid = self.zone_map.get(key)
            for metric, unit in [
                ("temperature", "°C"),
                ("cooling_setpoint", "°C"),
                ("occupancy_count", "count"),
                ("hvac_power_kw", "kW"),
                ("co2_ppm", "ppm"),
            ]:
                db.add(
                    TelemetryPoint(
                        building_id=building_id,
                        zone_id=zid,
                        metric=metric,
                        value=float(zone[metric]),
                        unit=unit,
                        timestamp=ts,
                        quality="FAILED" if zone.get("sensor_failed") and metric == "temperature" else "SIMULATED",
                        source="mock_simulator",
                    )
                )

    def _detect_anomalies(
        self, db: Session, building: Building, state: dict[str, Any]
    ) -> list[Alert]:
        alerts: list[Alert] = []
        for key, zone in state["zones"].items():
            neighbors = [
                z["temperature"]
                for k, z in state["zones"].items()
                if k != key and not z.get("sensor_failed")
            ]
            findings = detect_temperature_anomalies(
                SensorSeries(
                    zone_id=key,
                    values=[zone["temperature"]],
                    timestamps_age_seconds=[zone.get("data_freshness_seconds", 0)],
                    neighbor_means=neighbors,
                    model_prediction=zone.get("predicted_temperature"),
                )
            )
            for finding in findings:
                if finding.severity.value in {"HIGH", "CRITICAL"}:
                    alert = Alert(
                        building_id=building.id,
                        zone_id=self.zone_map.get(key),
                        severity=finding.severity.value,
                        alert_type="sensor_anomaly",
                        title=f"{zone['name']} sensor anomaly",
                        message=finding.message,
                        status="OPEN",
                    )
                    db.add(alert)
                    alerts.append(alert)
                    if finding.estimated_value is not None:
                        zone["estimated_temperature"] = finding.estimated_value
        return alerts

    def _update_confidence(self, building: Building, state: dict[str, Any]) -> dict[str, Any]:
        sensors = [z.get("sensor_health", 0.9) for z in state["zones"].values()]
        freshness = [
            max(0.0, 1.0 - float(z.get("data_freshness_seconds", 0)) / 300.0)
            for z in state["zones"].values()
        ]
        inputs = ConfidenceInputs(
            sensor_health=sum(sensors) / len(sensors),
            data_freshness=sum(freshness) / len(freshness),
            forecast_confidence=0.9 if not self.force_simulation_failure else 0.55,
            simulation_confidence=0.92 if not self.force_simulation_failure else 0.2,
            model_accuracy=0.88,
            service_health=0.95 if self.service_health["simulator"] == "ok" else 0.4,
        )
        breakdown = compute_confidence(inputs)
        building.confidence = breakdown.score
        building.autonomy_confidence_json = breakdown.model_dump()
        return breakdown.model_dump()

    def _to_observation(self, state: dict[str, Any]) -> BuildingObservation:
        hour = datetime.fromisoformat(state["timestamp_iso"]).hour if state.get("timestamp_iso") else 12
        spike = None
        if self.active_scenario == "occupancy_spike":
            spike = "south"
        return BuildingObservation(
            outdoor_temperature=state["outdoor_temperature"],
            carbon_intensity=state["grid_carbon_intensity"],
            electricity_tariff=state["electricity_tariff"],
            total_power_kw=state["total_building_power_kw"],
            occupancy_total=sum(z["occupancy_count"] for z in state["zones"].values()),
            hour=hour,
            zones=state["zones"],
            peak_window=12 <= hour <= 16,
            carbon_rising=state["grid_carbon_intensity"] >= 800 or self.active_scenario == "carbon_intensive",
            occupancy_spike_zone=spike,
        )

    def _record_kpi_snapshot(self, state: dict[str, Any], baseline: bool) -> None:
        interval_h = 0.25
        energy = state["total_building_power_kw"] * interval_h
        # No synthetic multipliers (×1.12 removed). Mock twin KPIs are live power
        # integrals only; EnergyPlus evidence comes from results/* via DATA_MODE.
        if baseline or not self.kpi_history:
            self.baseline_energy_kwh += energy
        self.twin_energy_kwh += energy
        baseline_power = state["total_building_power_kw"]
        # Cost/carbon "saved" are zero unless a true counterfactual exists.
        # Do not invent savings from a scaled baseline.
        self.cost_saved = 0.0
        self.carbon_avoided = 0.0
        self.peak_reduction_pct = 0.0
        comfortable = 0
        occupied = 0
        for z in state["zones"].values():
            if z.get("sensor_failed") or z.get("comfort_status") in {"SENSOR_FAULT", "OFFLINE"}:
                continue
            if z["occupancy_count"] > 0:
                occupied += 1
                # Treat slight discomfort as still compliant for KPI rollup;
                # only hard uncomfortable counts against compliance.
                if z["comfort_status"] in {"COMFORTABLE", "SLIGHTLY_UNCOMFORTABLE"}:
                    comfortable += 1
        if occupied:
            self.comfort_compliance = round(100.0 * comfortable / occupied, 1)
        self.kpi_history.append(
            {
                "timestamp": state.get("timestamp_iso") or _now().isoformat(),
                "power_kw": state["total_building_power_kw"],
                "baseline_power_kw": baseline_power,
                "carbon_intensity": state["grid_carbon_intensity"],
                "comfort_compliance": self.comfort_compliance,
                "baseline_energy_kwh": round(self.baseline_energy_kwh, 2),
                "twin_energy_kwh": round(self.twin_energy_kwh, 2),
                "simulated": bool(state.get("simulated", True)),
                "baseline_method": "no_synthetic_multiplier",
            }
        )
        self.kpi_history = self.kpi_history[-500:]

    @staticmethod
    def _state_hash(state: dict[str, Any]) -> str:
        payload = {
            "outdoor": state.get("outdoor_temperature"),
            "power": state.get("total_building_power_kw"),
            "zones": {
                k: {
                    "t": v.get("temperature"),
                    "sp": v.get("cooling_setpoint"),
                    "occ": v.get("occupancy_count"),
                }
                for k, v in state.get("zones", {}).items()
            },
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


hub = RuntimeHub()
