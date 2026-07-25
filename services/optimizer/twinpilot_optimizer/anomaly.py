"""Hybrid anomaly detection — hard rules first, ML optional and non-overriding."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class AnomalySeverity(str, Enum):
    NONE = "NONE"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class AnomalyFinding:
    rule: str
    severity: AnomalySeverity
    message: str
    estimated_value: float | None = None


@dataclass
class SensorSeries:
    zone_id: str
    values: list[float]
    timestamps_age_seconds: list[float]
    neighbor_means: list[float] | None = None
    model_prediction: float | None = None


def detect_temperature_anomalies(
    series: SensorSeries,
    *,
    min_plausible: float = 10.0,
    max_plausible: float = 40.0,
    max_rate_c_per_min: float = 2.0,
    stuck_epsilon: float = 0.01,
    neighbor_delta: float = 4.0,
    model_delta: float = 5.0,
    max_age_seconds: float = 300.0,
) -> list[AnomalyFinding]:
    findings: list[AnomalyFinding] = []
    if not series.values:
        findings.append(
            AnomalyFinding("missing_data", AnomalySeverity.HIGH, "No temperature samples")
        )
        return findings

    latest = series.values[-1]
    age = series.timestamps_age_seconds[-1] if series.timestamps_age_seconds else 0.0

    if age > max_age_seconds:
        findings.append(
            AnomalyFinding(
                "stale_sensor",
                AnomalySeverity.HIGH,
                f"Sensor has not updated for {age:.0f}s",
                estimated_value=_estimate(series),
            )
        )

    if latest < min_plausible or latest > max_plausible:
        findings.append(
            AnomalyFinding(
                "implausible_temperature",
                AnomalySeverity.CRITICAL,
                f"Temperature {latest:.1f}°C outside plausible bounds",
                estimated_value=_estimate(series),
            )
        )

    if len(series.values) >= 2 and len(series.timestamps_age_seconds) >= 2:
        dt_min = max(
            (series.timestamps_age_seconds[-2] - series.timestamps_age_seconds[-1]) / 60.0,
            1e-3,
        )
        rate = abs(series.values[-1] - series.values[-2]) / dt_min
        if rate > max_rate_c_per_min:
            findings.append(
                AnomalyFinding(
                    "rapid_change",
                    AnomalySeverity.HIGH,
                    f"Temperature changing at {rate:.1f}°C/min",
                    estimated_value=_estimate(series),
                )
            )

    if len(series.values) >= 5:
        window = np.array(series.values[-5:])
        if float(np.ptp(window)) <= stuck_epsilon:
            findings.append(
                AnomalyFinding(
                    "stuck_reading",
                    AnomalySeverity.WARNING,
                    "Temperature reading appears stuck",
                    estimated_value=_estimate(series),
                )
            )

    if series.neighbor_means:
        neighbor = float(np.mean(series.neighbor_means))
        if abs(latest - neighbor) > neighbor_delta and latest <= max_plausible:
            findings.append(
                AnomalyFinding(
                    "neighbor_disagreement",
                    AnomalySeverity.WARNING,
                    f"Disagrees with nearby zones by {abs(latest - neighbor):.1f}°C",
                    estimated_value=neighbor,
                )
            )

    if series.model_prediction is not None and abs(latest - series.model_prediction) > model_delta:
        # Only secondary if not already critical implausible
        if not any(f.rule == "implausible_temperature" for f in findings):
            findings.append(
                AnomalyFinding(
                    "model_disagreement",
                    AnomalySeverity.WARNING,
                    f"Disagrees with twin prediction by {abs(latest - series.model_prediction):.1f}°C",
                    estimated_value=series.model_prediction,
                )
            )

    return findings


def detect_co2_anomalies(value: float) -> list[AnomalyFinding]:
    if value < 300 or value > 5000:
        return [
            AnomalyFinding(
                "implausible_co2",
                AnomalySeverity.HIGH,
                f"CO₂ {value:.0f} ppm outside plausible bounds",
            )
        ]
    return []


def detect_power_spike(current_kw: float, previous_kw: float, factor: float = 2.5) -> list[AnomalyFinding]:
    if previous_kw > 1 and current_kw > previous_kw * factor:
        return [
            AnomalyFinding(
                "power_spike",
                AnomalySeverity.HIGH,
                f"Sudden power spike from {previous_kw:.1f} to {current_kw:.1f} kW",
            )
        ]
    return []


def optional_isolation_score(values: list[float]) -> float | None:
    """Secondary IsolationForest-like score. Never overrides hard rules.

    Returns a relative anomaly score in [0, 1] or None if insufficient data /
    sklearn unavailable.
    """
    if len(values) < 16:
        return None
    try:
        from sklearn.ensemble import IsolationForest
    except Exception:
        # Deterministic fallback score using robust z-score
        arr = np.array(values, dtype=float)
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med))) or 1.0
        z = abs(arr[-1] - med) / (1.4826 * mad)
        return float(min(1.0, z / 6.0))

    model = IsolationForest(n_estimators=64, contamination=0.08, random_state=42)
    arr = np.array(values, dtype=float).reshape(-1, 1)
    model.fit(arr)
    raw = -float(model.score_samples(arr[-1:].reshape(1, -1))[0])
    return float(min(1.0, max(0.0, (raw - 0.3) / 0.7)))


def _estimate(series: SensorSeries) -> float | None:
    if series.neighbor_means:
        return float(np.mean(series.neighbor_means))
    if series.model_prediction is not None:
        return series.model_prediction
    if len(series.values) >= 2:
        return float(np.median(series.values[:-1]))
    return None
