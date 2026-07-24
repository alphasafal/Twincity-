"""Helpers for infrastructure/scripts/replay.sh — keep shell quoting simple."""

from __future__ import annotations

import json
import sys
from typing import Any


def _load() -> Any:
    return json.load(sys.stdin)


def main() -> None:
    cmd = sys.argv[1]
    data = _load()
    if cmd == "token":
        print(data["access_token"])
    elif cmd == "building_id":
        print(data[0]["id"])
    elif cmd == "status":
        zones = ((data.get("state") or {}).get("zones")) or {}
        print(
            f"    mode={data.get('mode')} power={data.get('live_total_load_kw')} "
            f"zones={len(zones)} comfort={data.get('comfort_compliance_pct')}"
        )
    elif cmd == "balanced_plan_id":
        plans = data["plans"]
        print(next(p["id"] for p in plans if p["source"] == "BALANCED"))
    elif cmd == "apply":
        print(f"    applied decision={data.get('decision_id')}")
    elif cmd == "fault_status":
        conf = data.get("confidence") or {}
        score = conf.get("score", 0) if isinstance(conf, dict) else conf
        print(
            f"    mode={data.get('mode')} confidence={round(float(score or 0), 3)} "
            f"alerts={data.get('active_alerts')}"
        )
    elif cmd == "infeasible":
        bad = [p for p in data["plans"] if not p["feasibility"]]
        print("    infeasible_plans=", len(bad))
        if bad:
            reason = (bad[0]["predicted_metrics_json"].get("infeasibility_reasons") or [""])[0]
            print("   ", reason[:140])
    elif cmd == "assistant":
        answer = data["answer"]
        print("    observation:", (answer.get("observation") or "")[:140])
        print("    recommendation:", (answer.get("recommendation") or "")[:140])
    elif cmd == "rollback":
        print(
            f"    rollback={data.get('status')} actions={len(data.get('actions') or [])}"
        )
    elif cmd == "ledger":
        print(f"    ledger_entries={len(data)}")
    elif cmd == "audit":
        print(
            f"    audit_events={len(data)} types={sorted({r['event_type'] for r in data})}"
        )
    else:
        raise SystemExit(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
