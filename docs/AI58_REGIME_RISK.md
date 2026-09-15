# AI58 — Regime-Risk Classification

Status: **WEAK BUT WITHIN HISTORICAL TOLERANCE**

This analysis keeps the creator-video AI58 USDJPY parameters frozen. Thresholds are derived only from history ending **2026-03-15**, before the fresh post-video period being classified.

## Current trailing performance through 2026-09-14

```text
6 months   24 trades   -8.01%   PF 0.808   win rate 29.17%
12 months  48 trades  +29.93%   PF 1.385   win rate 41.67%
24 months  94 trades  +80.01%   PF 1.422   win rate 42.55%
```

The six-month window is weak, but the 12- and 24-month windows remain profitable with PF above 1.

## Current drawdown

Closed-trade equity is currently in an unrecovered drawdown:

```text
peak time                  2026-06-18
current/trough time        2026-09-13
max drawdown               2.68%
duration                   ~87 days
trades underwater          14
```

Historical completed drawdown distribution before the fresh post-video period:

```text
median depth               2.14%
90th percentile depth      9.14%
95th percentile depth     16.29%
maximum depth             20.57%

median duration           ~31.6 days
90th percentile duration ~282.9 days
95th percentile duration ~480.2 days
maximum duration          ~654.4 days
```

The current drawdown is around the **64th percentile by depth** and **71st percentile by duration** versus the pre-fresh-period history. It is not historically extreme.

Past severe examples include:

```text
2012      ~20.57% drawdown, ~252 days peak-to-recovery
2013      ~20.00% drawdown, ~266 days
2016-18   ~16.95% drawdown, ~654 days
2015-16   ~13.66% drawdown, ~557 days
2018-20    ~7.38% drawdown, ~505 days
```

## Losing streaks

Current ending losing streak:

```text
2 consecutive losing trades
```

Reference history before 2026-03-15:

```text
median losing streak       2 trades
90th percentile             4 trades
95th percentile             5 trades
maximum                     7 trades
```

The current ending streak is therefore normal by historical standards.

## Rolling-window context

Reference distributions ending no later than 2026-03-15:

```text
6-month windows
  profitable               75.29%
  median return            +16.54%
  10th percentile return   -13.33%
  median PF                 1.403
  10th percentile PF        0.730

12-month windows
  profitable               80.95%
  median return            +36.16%
  10th percentile return    -9.61%
  median PF                 1.435

24-month windows
  profitable               94.23%
  median return            +70.36%
  10th percentile return   +11.15%
  median PF                 1.403
```

The latest six-month return ranks around the **15.5th percentile** historically. The latest 12-month return is around the **40.5th percentile**, while the latest 24-month return is around the **52.6th percentile**.

## Frozen classifier

The research classifier was defined before reading the current classification result:

```text
historically_normal
  latest 6m positive / PF > 1 and no historical-risk threshold breach

weak_but_within_historical_tolerance
  latest 6m weak, but 12/24m behavior and drawdown/streak remain inside historical limits

high_risk_dormant
  12m weak OR drawdown/streak exceeds pre-fresh-period 95th percentile

structural_concern
  24m weak AND both drawdown depth and duration exceed their pre-fresh-period 95th percentiles
```

Current AI58 classification:

```text
WEAK_BUT_WITHIN_HISTORICAL_TOLERANCE
```

The current six-month weakness is real, but neither the 12/24-month performance nor drawdown depth, drawdown duration, or losing streak has breached the predeclared high-risk thresholds.

## Interpretation

This result does **not** justify changing AI58's parameters to repair 2026. It also does not prove the recent weakness will recover. It says only that the current drawdown is consistent with weak regimes the unchanged strategy has survived historically.

AI58 remains research/shadow-paper only. No broker execution or live-trading path should be enabled from this result.

## Limitation

Drawdown depth and duration use closed-trade equity because the current research engine does not retain full bar-level mark-to-market equity. TradingView-style intrabar drawdown can differ.
