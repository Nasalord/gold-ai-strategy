# AI58 creator-video settings evidence

Source video: `https://www.youtube.com/watch?v=J8a8wlewhTk`

This note records the settings recovered from the user-supplied transcript. It is evidence, not an optimization log.

## Optimized setup stated in the video

- Symbol/provider: USDJPY on **IC Markets**.
- Execution timeframe: **15 minutes**.
- Optimized opening range: **06:00 to 08:15 America/New_York** (the video also describes the chart as 14:00–16:15 on its displayed UTC3 chart).
- Direction: **long only**.
- TDFI: enabled; lookback **50**; long/high threshold **0**. The later strategy-settings narration says both high and low limits are zero. The low threshold is irrelevant for the long-only preset.
- ATR trailing stop: enabled. The external NNFX ATR illustration is configured with **X = 450** and **SL = 11**; these are mapped to the uploaded Pine engine's ATR length=450 and multiplier=11 for the source-parity hypothesis.
- No practical fixed take-profit; exits are described as occurring through the ATR trailing stop.
- No force-exit rule is described for the optimized setup; the narration says the trailing stop is the only possible exit.
- Initial capital: **$10,000**.
- Default order size: **$70,000** (7x notional/account ratio in the creator test).
- Commission: **$3.50 per standard lot per side**; the narration also quotes **0.006 JPY per contract**, which should be treated as a separate contract-accounting statement rather than silently reconciled.
- Slippage: **12 ticks = 1.2 pips**.
- Bar magnifier: enabled.
- Recalculation: every tick.

## Fixed stop / TP ambiguity

The transcript ASR says: "Both values are set at one" immediately before saying the **only possible way to exit is the trailing stop-loss**. In the uploaded Pine engine, setting the fixed stop and TP controls to literal `1` would leave active fixed exits and contradict that narration. The most plausible ASR interpretation is **100** for both values, making the fixed exits effectively unreachable while the ATR trailing stop controls the trade.

For research this is encoded explicitly as a hypothesis, not as a silently asserted fact. If a screenshot of the optimized strategy-input panel becomes available, it overrides this inference.

## Creator benchmark shown in the video

Optimization/in-sample window:
- **2021-09-01 through 2025-09-01**
- **185 trades**
- about **+287% net profit**
- about **17% maximum drawdown**
- about **1.70 profit factor**

Post-optimization window shown:
- **2025-09-01 through 2026-03-14**
- **24 trades**
- about **+32% net profit**
- about **14% maximum drawdown**
- **50% win rate**
- about **1.57 profit factor**

The later ranking spreadsheet reports a different AI58 benchmark (229 trades, +309.74%, PF 1.736, win 45.41%, DD 20.79%), so the repository must keep the **video benchmark** and **ranking-sheet benchmark** separate rather than forcing one to match the other.
