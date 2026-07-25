#!/usr/bin/env python3
"""Clean-clone dashboard payload check (no long-running demo server required)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path[:0] = [
    str(ROOT / "services" / "api"),
    str(ROOT / "services" / "optimizer"),
    str(ROOT / "services" / "simulator"),
]

from app.services.experiment_store import experiment_dashboard_payload  # noqa: E402


def main() -> int:
    with_data = experiment_dashboard_payload()
    print(
        "with_data_available",
        with_data.get("available"),
        "reductions",
        with_data.get("reductions"),
    )
    assert with_data.get("available") is True, "expected fresh results available"

    bk = Path("/tmp/cleanclone-nodata-bk")
    if bk.exists():
        shutil.rmtree(bk)
    bk.mkdir()
    for d in ("baseline", "agent", "comparison"):
        src = ROOT / "results" / d
        dst = bk / d
        dst.mkdir()
        for f in src.iterdir():
            if f.name == ".gitkeep":
                continue
            shutil.move(str(f), str(dst / f.name))

    nodata = experiment_dashboard_payload()
    print(
        "nodata_available",
        nodata.get("available"),
        "missing",
        nodata.get("missing_artifacts"),
    )
    assert nodata.get("available") is not True, "no-data must not report available"

    for d in ("baseline", "agent", "comparison"):
        for f in (bk / d).iterdir():
            shutil.move(str(f), str(ROOT / "results" / d / f.name))

    restored = experiment_dashboard_payload()
    print("restored_available", restored.get("available"))
    assert restored.get("available") is True
    print("DASHBOARD_PAYLOAD_CHECK=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
