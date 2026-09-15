from __future__ import annotations

import argparse
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path


def _load_regime_module():
    path = Path(__file__).with_name("run_ai58_regime_risk.py")
    spec = importlib.util.spec_from_file_location("ai58_regime_risk", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load run_ai58_regime_risk.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen AI58 regime classifier through a dynamic end date"
    )
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--analysis-end", type=_parse_date, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    regime = _load_regime_module()
    if args.analysis_end <= regime.REFERENCE_END:
        raise ValueError("--analysis-end must be after the frozen reference-history cutoff")

    # Keep the March 15, 2026 reference distribution frozen forever. Only the
    # evaluation horizon advances, preventing the monitor from learning from the
    # period it is supposed to judge.
    regime.ANALYSIS_END = args.analysis_end

    original_argv = sys.argv[:]
    try:
        sys.argv = [
            "run_ai58_regime_risk.py",
            str(args.csv_path),
            "--output",
            str(args.output),
        ]
        regime.main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main()
