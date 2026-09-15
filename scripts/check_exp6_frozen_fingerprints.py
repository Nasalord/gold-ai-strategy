from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"missing validation artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def assert_close(label: str, actual: float, expected: float, tolerance: float) -> None:
    if abs(float(actual) - expected) > tolerance:
        raise AssertionError(
            f"{label}: expected {expected} ± {tolerance}, got {actual}"
        )


def assert_equal(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify frozen Experiment 6 validation fingerprints."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root

    parity = load(root / "exp6_public_parity" / "exp6_public_parity.json")
    oos = load(root / "exp6_public_oos" / "exp6_public_oos.json")
    robustness_2025 = load(
        root / "exp6_public_robustness" / "exp6_public_robustness.json"
    )
    regimes = load(root / "exp6_public_regimes" / "exp6_public_regimes.json")
    sample_2026 = load(root / "exp6_2026_sample" / "exp6_2026_sample.json")
    robustness_2026 = load(
        root / "exp6_2026_robustness" / "exp6_2026_robustness.json"
    )

    # Jan-May 2025 creator-overlap fingerprint. Exact creator parity is still
    # unresolved, but the public-data reconstruction itself must stay stable.
    p = parity["creator_8_5m"]
    assert_equal("parity trades", p["trades"], 24)
    assert_close("parity net %", p["net_profit_pct"], 36.22, 0.25)
    assert_close("parity PF", p["profit_factor"], 1.296, 0.02)
    assert_equal("parity target trades", parity["creator_target"]["trades"], 27)

    # First untouched OOS failure must remain reproducible; a later code change
    # is not allowed to silently turn the historical failure into a pass.
    o = oos["metrics"]["creator_8_5m"]
    assert_equal("fresh-2025 OOS trades", o["trades"], 25)
    assert_close("fresh-2025 OOS net %", o["net_profit_pct"], -17.26, 0.25)
    assert_close("fresh-2025 OOS PF", o["profit_factor"], 0.713, 0.02)

    r25 = robustness_2025["summary"]
    assert_equal("2025 neighbour count", r25["neighbors"], 22)
    assert_equal("2025 profitable+PF>1 neighbours", r25["positive_and_pf_gt_1"], 0)

    # Regime fingerprints are deliberately broad enough for harmless floating
    # point variation while still catching semantic/backtest drift.
    reg = regimes["results"]
    assert_equal("2023 trades", reg["2023"]["trades"], 73)
    assert_close("2023 net %", reg["2023"]["net_profit_pct"], -10.93, 0.30)
    assert_close("2023 PF", reg["2023"]["profit_factor"], 0.948, 0.03)
    assert_equal("2024 trades", reg["2024"]["trades"], 66)
    assert_close("2024 net %", reg["2024"]["net_profit_pct"], 159.75, 0.75)
    assert_close("2024 PF", reg["2024"]["profit_factor"], 2.028, 0.03)

    # April 2026 is warmup only. The frozen recovery window begins May 1.
    assert_equal("2026 sample start", sample_2026["window"]["start"], "2026-05-01")
    s26 = sample_2026["metrics"]["creator_8_5m"]
    assert_equal("2026 recovery trades", s26["trades"], 6)
    assert_close("2026 recovery net %", s26["net_profit_pct"], 35.69, 0.50)
    assert_close("2026 recovery PF", s26["profit_factor"], 3.395, 0.06)

    r26 = robustness_2026["summary"]
    assert_equal("2026 neighbour count", r26["neighbors"], 22)
    assert_equal("2026 profitable+PF>1 neighbours", r26["positive_and_pf_gt_1"], 17)

    print("EXP6 frozen validation fingerprints verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
