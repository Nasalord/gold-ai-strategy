# Experiment 6 — Triple MACD NQ1! 10m

**Research phase:** `COMPLETE / PARAMETERS FROZEN`

**Classification:** **WATCHLIST / SHADOW-PAPER RESEARCH ONLY.** The strategy is not promoted to a validated edge or live workflow. Exact TradingView parity remains unresolved, the first genuinely fresh 2025 OOS window failed broadly, and the later 2026 recovery is still a small sample. No retuning is permitted in response to future results.

## Source and frozen preset

Source material is the user-supplied Trade Smart AI Triple MACD strategy/video and the NQ optimization settings reconstructed from that material. The implementation uses the creator's NQ1! 10-minute preset without retuning:

| Parameter | Frozen value |
| --- | ---: |
| Market | CME E-mini Nasdaq-100 futures / NQ1! |
| Timeframe | 10 minutes |
| Chande momentum filter | Off |
| Trend MA filter | Off |
| TDFI filter | On |
| TDFI lookback | 50 |
| TDFI high / low | 0.9 / -0.8 |
| TDFI smoothing | Off |
| Long MACD | 150 / 450 / 9 |
| Mid MACD | 45 / 70 / 9 |
| Short MACD | 28 / 23 / 9 |
| Entry A / Entry B | On / Off |
| Stop lookback | Previous 10 bars, excluding signal bar |
| Reward:risk | 3.5:1 |
| Direction | Long + short |
| Initial capital | $1,000,000 |
| Creator order cash | $8,500,000 |
| Commission | $2.50 / contract / filled order |
| Slippage | 5 ticks |

For CME NQ, the harness uses a $20 index-point multiplier and a 0.25-point minimum tick. Cash sizing is translated to whole contracts using `cash / (price * point_value)` for the creator-parity baseline.

## Reproduced source semantics

The emulator intentionally reproduces the supplied Pine-style behavior rather than improving it:

- three MACD histogram state machines use the supplied NQ lengths;
- Entry A only;
- TDFI gates pipeline initiation;
- market entry is signaled on the bar close and filled on the next bar open;
- five ticks of slippage are applied to market entries and adverse stop fills;
- stops use the prior 10 bars, excluding the signal bar;
- targets are frozen from the signal close and stop at 3.5R;
- only one position is held at a time;
- pipelines reset after an exit and cannot replace a trade on the same bar;
- commission is charged per contract on each filled order.

The deterministic regression suite also locks the shadow-monitor health thresholds.

## Creator benchmarks

Creator-reported optimization period, approximately Jan 2021 through Jan 2025:

- 288 trades
- +618% net profit
- ~25% maximum drawdown
- profit factor ~1.6

The complete TradingView optimization-period series has not been independently reproduced because the available public intraday continuous-futures sources do not provide a source-faithful NQ1! series back to 2021.

Creator-reported Jan 1 through Jun 1, 2025 check:

- 27 trades
- +19% net profit
- ~51% maximum drawdown
- profit factor ~1.1

## Independent structural parity — Jan 1 to Jun 1, 2025

Using the public `MeNameek/AnooReplay` NQ minute dataset, resampled to 10-minute bars with warmup:

| Metric | Creator target | Independent |
| --- | ---: | ---: |
| Trades | 27 | **24** |
| Net profit | +19% | **+36.22%** |
| Profit factor | 1.10 | **1.296** |
| Win rate | — | **33.33%** |
| Closed-trade DD | TV reported ~51% | **22.88%** |

The three-trade count miss indicates substantial structural reproduction, but the P&L and drawdown differences are too large to declare exact creator parity.

**Parity classification:** `SUBSTANTIAL STRUCTURAL REPRODUCTION / EXACT PARITY UNRESOLVED`.

## Untouched fresh OOS — Jun 1 to Oct 6, 2025

No parameters were changed after the creator-overlap reconstruction.

| Case | Trades | Net | PF | Closed DD |
| --- | ---: | ---: | ---: | ---: |
| Creator $8.5m sizing | 25 | **-17.26%** | **0.713** | **41.28%** |
| $4m sizing control | 25 | **-8.04%** | **0.709** | 18.92% |
| $1m normalized cash sizing | 25 | **-2.51%** | **0.631** | 4.63% |
| 2x commission + slippage | 25 | **-19.36%** | **0.687** | 43.18% |

Both directions were negative in the fresh window, so the failure is not explained by leverage or one side alone.

## Fresh-2025 local robustness

Twenty-two predeclared one-factor neighbours were tested around the frozen MACD, TDFI, stop-lookback, and R:R values.

**Result: 0 / 22 neighbours were both profitable and PF > 1.**

This is strong evidence that the Jun-Oct 2025 breakdown was broad rather than an isolated exact-parameter failure. Neighbours are diagnostic only and may not replace the baseline after observing OOS.

## Regime evidence — public 2023–2025 history

| Period | Trades | Net | PF | Win rate | Closed DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | 73 | **-10.93%** | **0.948** | 19.18% | 50.27% |
| 2024 | 66 | **+159.75%** | **2.028** | 33.33% | 21.21% |
| Jan–May 2025 creator overlap | 24 | **+36.22%** | **1.296** | 33.33% | 22.88% |
| Jun–Oct 2025 fresh OOS | 25 | **-17.26%** | **0.713** | 28.00% | 41.28% |

The independent history does not support a stable universal edge. Performance is strongly regime-dependent.

## Independent 2026 recovery sample

A separate public NQ one-minute sample from `getdata-finance/nq-1m-ohlcv-stocks-historical-data` begins Apr 1, 2026. **April is warmup only. The frozen evaluation window begins May 1, 2026 and ends Sep 3, 2026.** The runner default is locked to this window.

| Case | Trades | Net | PF | Closed DD |
| --- | ---: | ---: | ---: | ---: |
| Creator $8.5m sizing | **6** | **+35.69%** | **3.395** | 6.53% |
| $4m sizing | 6 | +14.91% | 3.201 | 3.41% |
| $1m normalized sizing | 6 | **+2.55%** | **3.395** | 0.66% |
| 2x execution costs | 6 | +35.30% | 3.321 | 6.70% |

The recovery is encouraging but too small to erase the broad 2025 failure.

## 2026 recovery robustness

The same 22 predeclared one-factor neighbours were tested over the May-Sep 2026 window.

**17 / 22 neighbours were both profitable and PF > 1.**

The breadth supports the recovery, but most variants still contain only roughly five to seven trades. The evidence remains provisional.

## Frozen final judgment

### Evidence for continued observation

- deterministic source reconstruction is implemented;
- creator-overlap signal frequency is fairly close at 24 versus 27 trades;
- early 2025 reconstruction is independently profitable;
- an independent 2026 dataset shows a strong recovery;
- 17/22 local neighbours share the 2026 recovery;
- the 2026 recovery survives 2x execution costs.

### Evidence against promotion

- exact TradingView parity remains unresolved;
- 2023 is below PF 1;
- the first genuinely fresh Jun-Oct 2025 OOS window failed materially;
- 0/22 local neighbours survived that 2025 window;
- both long and short sides failed in fresh 2025 OOS;
- the 2026 recovery contains only six baseline trades;
- creator $8.5m sizing is highly aggressive and is not the monitoring allocation.

### Final classification

**`WATCHLIST / SHADOW-PAPER RESEARCH ONLY`**

The research/backtest phase is complete. The parameters are frozen. Future evidence is collected prospectively through the shadow monitor using normalized research sizing. No future weak or strong result may be used to retune this frozen Experiment 6 record.

The monitor remains in `observing_insufficient_sample` until at least **20 closed trades** have accumulated from the frozen monitoring window. After the sample gate, the predeclared health rules classify positive net + PF > 1 as healthy, net <= 0 or PF <= 1 as weak, and negative net + PF < 0.8 as structural concern.

## Validation implementation

Core:

- `ai_investing_lab/strategies/triple_macd_nq/config.py`
- `ai_investing_lab/strategies/triple_macd_nq/indicators.py`
- `ai_investing_lab/strategies/triple_macd_nq/engine.py`
- `tests/test_triple_macd_nq.py`

Validation scripts:

- `scripts/run_exp6_public_nq_parity.py`
- `scripts/run_exp6_public_oos.py`
- `scripts/run_exp6_public_robustness.py`
- `scripts/run_exp6_public_regimes.py`
- `scripts/run_exp6_2026_sample.py`
- `scripts/run_exp6_2026_robustness.py`
- `scripts/check_exp6_frozen_fingerprints.py`

GitHub Actions:

- `.github/workflows/exp6_full_validation.yml` — deliberate complete validation only; never runs on ordinary pushes.
- `.github/workflows/exp6_triple_macd_shadow_monitor.yml` — weekly or manual frozen monitoring only; ordinary code pushes do not trigger it.

The full-validation workflow reproduces parity, fresh OOS, cost-sensitive cases, local robustness, regime evidence, the 2026 recovery, and the 2026 robustness result, then verifies the known frozen result fingerprints. This preserves validation depth while avoiding repeated heavy runs during normal development.

See `docs/ACTIONS_USAGE_POLICY.md` for the project-wide GitHub Actions practice.
