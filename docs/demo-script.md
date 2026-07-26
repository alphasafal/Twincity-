# Demo Script

## Path 1 — Operator UI (mock twin, 5–8 minutes)

1. `./scripts/setup.sh && ./scripts/run_demo.sh`
2. Open http://localhost:3000 — login `manager@twinpilot.demo` / `TwinPilot-Manager-Demo!`
3. Show live zones, run a scenario (hot day), generate plans, simulate, Safety Shield validate, approve/apply.
4. Show decision + audit + prediction ledger.
5. State clearly: **this path uses the mock digital twin**, not EnergyPlus meters.

## Path 2 — Measured EnergyPlus closed loop (evaluation, ~1 minute runtime)

1. `./scripts/setup_energyplus.sh`
2. `./scripts/run_baseline.sh`
3. `./scripts/run_agent.sh`
4. `./scripts/compare_results.sh`
5. Open `results/comparison/comparison.md` and quote **only** those numbers.
6. Optionally open `results/agent/actions.json` to show SafetyShield-gated actuator writes.

## Talking points

- AI proposes; safety validates; EnergyPlus physics executes.
- Baseline and agent share identical IDF/EPW/occupancy/period.
- LLM cannot set actuators directly.
- Known limitation: interactive dashboard defaults to mock; measured proof is the experiment harness.
