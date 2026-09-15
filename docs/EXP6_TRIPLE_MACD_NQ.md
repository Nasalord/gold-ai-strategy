# Experiment 6 — Triple MACD NQ1! 10m

**Status:** `SOURCE RECONSTRUCTED → STRUCTURAL PARITY SUBSTANTIALLY REPRODUCED / EXACT PARITY UNRESOLVED → FRESH 2025 OOS FAILED → 2026 SMALL-SAMPLE RECOVERY`

**Classification:** **WATCHLIST / SHADOW-PAPER RESEARCH ONLY.** Do not promote this strategy to a validated edge or live workflow. The frozen parameters may be observed prospectively, but the broad 2025 OOS failure and unresolved TradingView parity remain permanent caveats.

## Source

- Trade Smart AI video supplied by the user: `https://www.youtube.com/watch?v=GPhfLs0_iLQ`
- Source/optimization folder supplied by the user: `https://drive.google.com/drive/folders/1BrH2FXi-UPuoUSgrUkED_ncYoyEhUNd1`
- Drive file name: `34 - Triple MACD Strategy Script.txt`
- The `34` is treated as a script/catalog number only. No verified `AIxx` optimization ID has been established.

## Frozen NQ1! 10-minute preset

The implementation uses the creator's NQ optimization without retuning:

| Parameter | Frozen value |
| --- | ---: |
| Market | CME E-mini Nasdaq-100 futures / NQ1! |
| Timeframe | 10 minutes |
| Chande momentum filter | Off |
| Trend MA filter | Off |
| TDFI filter | On |
| TDFI lookback | 50 |
| TDFI high | 0.9 |
| TDFI low | -0.8 |
| TDFI smoothing | Off |
| Long MACD | 150 / 450 / 9 |
| Mid MACD | 45 / 70 / 9 |
| Short MACD | 28 / 23 / 9 |
| Entry A | On |
| Entry B | Off |
| Stop lookback | Previous 10 bars, excluding signal bar |
| Reward:risk | 3.5:1 |
| Direction | Long + short |
| Initial capital | $1,000,000 |
| Order cash | $8,500,000 |
| Commission | $2.50 / contract / filled order |
| Slippage | 5 ticks |

For CME NQ, the harness uses a $20 index-point multiplier and 0.25-point minimum tick. Cash order sizing is translated to contracts from `cash / (price * point_value)`, using whole contracts for the parity baseline.

## Source semantics reproduced

The emulator intentionally reproduces the supplied Pine behavior rather than improving it:

- three MACD histogram state machines use the supplied NQ lengths;
- Entry A only;
- TDFI is checked when a pipeline begins, not continuously at every later step;
- market entry is created on the signal-bar close and filled on the next bar open;
- five ticks of slippage are applied to market entries and adverse stop fills;
- stop is `ta.lowest(low, 10)[1]` for longs / `ta.highest(high, 10)[1]` for shorts;
- target is calculated from the signal close and frozen stop at 3.5R;
- only one position is held at a time;
- state pipelines reset after an exit and cannot replace the trade on the same bar;
- commission is charged per contract on each filled order.

The dedicated Triple-MACD regression suite contains eight tests and passes in the parity, OOS, regime, and robustness workflows.

## Creator benchmarks

### Optimization period — creator reported

Approximately Jan 2021 through Jan 2025:

- 288 trades
- +618% net profit
- ~25% maximum drawdown
- profit factor ~1.6

This full TradingView optimization-period result has **not** been independently reproduced because the available intraday futures sources do not provide a source-faithful NQ1! series back to 2021.

### Creator after-optimization check

Jan 1 2025 through Jun 1 2025:

- 27 trades
- +19% net profit
- ~51% maximum drawdown
- profit factor ~1.1

The creator also reduced order size from about $8.5m to about $4m and reported roughly +7.7% with ~24% maximum drawdown over the same period.

## Independent structural parity — Jan 1 to Jun 1, 2025

Using the committed public NQ minute dataset from `MeNameek/AnooReplay`, resampled to 10-minute bars with warmup and the frozen emulator:

| Metric | Creator target | Independent |
| --- | ---: | ---: |
| Trades | 27 | **24** |
| Net profit | +19% | **+36.22%** |
| Profit factor | 1.10 | **1.296** |
| Win rate | not used as primary target | **33.33%** |
| Closed-trade DD | TV reported ~51% | **22.88%** |

The trade-count miss is only three trades, so signal generation is substantially reproduced, but the P&L/DD differences are too large to call exact creator parity passed. The likely remaining source of disagreement is continuous-contract/feed/execution semantics rather than parameter choice.

**Parity classification:** `SUBSTANTIAL STRUCTURAL REPRODUCTION / EXACT PARITY UNRESOLVED`.

## Untouched fresh OOS — Jun 1 to Oct 6, 2025

No parameters were changed after the creator-overlap test.

### Frozen baseline

| Case | Trades | Net | PF | Closed DD |
| --- | ---: | ---: | ---: | ---: |
| Creator $8.5m sizing | 25 | **-17.26%** | **0.713** | **41.28%** |
| $4m sizing control | 25 | **-8.04%** | **0.709** | 18.92% |
| $1m normalized cash sizing | 25 | **-2.51%** | **0.631** | 4.63% |
| 2x commission + slippage | 25 | **-19.36%** | **0.687** | 43.18% |

Direction diagnostics also failed on both sides:

- longs: 16 trades, PF ~0.678, negative net P&L;
- shorts: 9 trades, PF ~0.763, negative net P&L.

The failure is therefore not explained by leverage or one direction alone.

## Fresh-2025 local robustness

Twenty-two predeclared one-factor neighbours were tested around the frozen MACD, TDFI, stop-lookback, and R:R values. These tests are diagnostics only; no neighbour may replace the baseline because of OOS performance.

**Result: 0 / 22 neighbours were both profitable and PF > 1.**

Examples:

- TDFI high 0.85: -6.57%, PF 0.889;
- TDFI lookback 45: -32.50%, PF 0.513;
- stop lookback 8: -0.23%, PF 0.996 — closest to breakeven, but still a failure;
- R:R 4.0: -36.28%, PF 0.429.

This is strong evidence that the Jun–Oct 2025 breakdown was broad rather than one brittle exact parameter point.

## Regime evidence — public 2023–2025 history

These older periods are descriptive because 2023–2024 overlap the creator's optimization era.

| Period | Trades | Net | PF | Win rate | Closed DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | 73 | **-10.93%** | **0.948** | 19.18% | 50.27% |
| 2024 | 66 | **+159.75%** | **2.028** | 33.33% | 21.21% |
| Jan–May 2025 creator-overlap | 24 | **+36.22%** | **1.296** | 33.33% | 22.88% |
| Jun–Oct 2025 fresh OOS | 25 | **-17.26%** | **0.713** | 28.00% | 41.28% |

The independent data therefore does not support a stable universal edge: 2023 was weak, 2024 exceptional, early 2025 positive, and the first genuinely fresh 2025 period failed. This is consistent with strong regime dependence.

## Independent 2026 recovery sample

A separate public NQ one-minute sample from `getdata-finance/nq-1m-ohlcv-stocks-historical-data` covers Apr 1 through Sep 2, 2026. April is used only as indicator warmup; the frozen strategy is evaluated from **May 1 through Sep 3, 2026**.

| Case | Trades | Net | PF | Closed DD |
| --- | ---: | ---: | ---: | ---: |
| Creator $8.5m sizing | **6** | **+35.69%** | **3.395** | 6.53% |
| $4m sizing | 6 | +14.91% | 3.201 | 3.41% |
| $1m normalized sizing | 6 | **+2.55%** | **3.395** | 0.66% |
| 2x execution costs | 6 | +35.30% | 3.321 | 6.70% |

This is an encouraging recovery, but six closed trades is a very small sample and cannot erase the prior broad OOS failure by itself.

## 2026 recovery robustness

The same 22 predeclared one-factor neighbours were tested over the warmup-corrected May–Sep 2026 window.

**17 / 22 neighbours were both profitable and PF > 1.**

The recovery therefore is not isolated to the exact baseline. However, sensitivity remains visible in several nearby settings:

- mid MACD fast 40: -1.52%, PF 0.956;
- mid MACD fast 50: -23.76%, PF 0.690;
- mid MACD slow 77: -23.86%, PF 0.689;
- TDFI lookback 45: -44.07%, PF 0.535;
- stop lookback 12: -17.78%, PF 0.486.

Other neighbours remained strong, including stop lookback 8 (+5.61%, PF 1.198), R:R 3.0 (+28.46%, PF 2.909), R:R 4.0 (+42.93%, PF 3.881), and several TDFI-threshold neighbours.

Because these variants have only roughly five to seven trades each, this breadth is supportive but not conclusive.

## Final research judgment

### Evidence for the strategy

- supplied source code was reconstructed into a deterministic emulator;
- signal frequency on creator OOS is fairly close (24 vs 27 trades);
- creator-overlap Jan–May 2025 is independently profitable;
- May–Sep 2026 shows a strong recovery on a separate public dataset;
- 17/22 local neighbours share the 2026 recovery;
- 2026 recovery survives 2x execution costs.

### Evidence against the strategy

- exact TradingView parity remains unresolved;
- 2023 was below PF 1 in the independent historical sample;
- the first genuinely fresh Jun–Oct 2025 OOS period failed materially;
- **0/22** local neighbours survived that failed 2025 window;
- both long and short sides failed in fresh 2025 OOS;
- 2026 recovery contains only six baseline trades and shows sensitivity in several mid-MACD/TDFI/stop neighbours;
- creator $8.5m cash sizing is highly aggressive and should not be interpreted as a practical research allocation.

### Classification

**`WATCHLIST / SHADOW-PAPER RESEARCH ONLY`**

This is **not** promoted to `VALIDATED EDGE`. It is also not rejected outright because the later independent 2026 sample recovered strongly and broadly enough to justify collecting prospective evidence with the parameters permanently frozen.

If forward monitoring is added, use normalized research sizing and evaluate signal health rather than the creator's leveraged headline return. No retuning is permitted in response to weak future results.

## Validation code and workflows

Core:

- `ai_investing_lab/strategies/triple_macd_nq/config.py`
- `ai_investing_lab/strategies/triple_macd_nq/indicators.py`
- `ai_investing_lab/strategies/triple_macd_nq/engine.py`
- `tests/test_triple_macd_nq.py`

Validation:

- `scripts/run_exp6_public_nq_parity.py`
- `scripts/run_exp6_public_oos.py`
- `scripts/run_exp6_public_robustness.py`
- `scripts/run_exp6_public_regimes.py`
- `scripts/run_exp6_2026_sample.py`
- `scripts/run_exp6_2026_robustness.py`

GitHub Actions:

- `.github/workflows/exp6_triple_macd_public_parity.yml`
- `.github/workflows/exp6_triple_macd_public_oos.yml`
- `.github/workflows/exp6_triple_macd_public_robustness.yml`
- `.github/workflows/exp6_triple_macd_public_regimes.yml`
- `.github/workflows/exp6_triple_macd_2026_sample.yml`
- `.github/workflows/exp6_triple_macd_2026_robustness.yml`

All of these workflows are research/paper-only. They do not place orders or alter brokerage state.
