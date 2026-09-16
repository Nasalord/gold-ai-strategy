# Existing-strategy rebaseline — 2016 or earliest trustworthy history

Date: 2026-09-16

## Purpose

The project now uses a common long-history rule for strategies that have already passed source/parity work: score the **unchanged frozen strategy from 2016-01-01 to the latest reliable data**, or from the provider's earliest trustworthy history when that market/feed begins later. Reliable history that predates 2016 remains additional evidence and is not discarded.

This is a durability screen, not an optimizer. No parameter was changed after reading these results.

## Coverage

| Strategy | Standardized scored start | Reason |
|---|---|---|
| AI8 BTCUSDT 2H | 2017-08-17 | Binance Spot BTCUSDT history in this research path begins after 2016 |
| AI2 ETHUSDT 15m | 2017-08-17 | Binance Spot ETHUSDT history begins after 2016 |
| AI38 GBPUSD 4H | 2016-01-01 | Dukascopy history covers 2016; older 2005+ evidence remains separately relevant |
| AI58 USDJPY 15m ORB | 2016-01-01 | Dukascopy history covers 2016; older 2011+ evidence remains separately relevant |
| EXP6 NQ 10m | 2023-01-01 only with current continuous public source | Current validated NQ source cannot support a 2016 rebaseline; 2026 remains a separate provider/sample |

## Standardized long-history results

Returns below use each strategy's **frozen creator/reference sizing** and therefore are not directly comparable as deployment returns. Profit factor, drawdown, cost survival, pre-creator evidence and OOS behavior are more informative.

| Strategy | Coverage | Trades | Net % | PF | Closed-trade DD % | 2x-cost net % | 2x-cost PF | 2x-cost DD % |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **AI8** | 2017-08-17 → 2026-09-16 | 718 | **+1024.26** | **1.614** | **51.01** | **+908.09** | **1.524** | **54.49** |
| **AI2** | 2017-08-17 → 2026-09-16 | 386 | **+2429.14** | **1.552** | **264.56** | **+2106.33** | **1.458** | **272.82** |
| **AI38** | 2016-01-01 → 2026-09-16 | 261 | **+357.31** | **1.415** | **49.83** | **+247.41** | **1.263** | **66.74** |
| **AI58** | 2016-01-01 → 2026-09-16 | 490 | **+400.33** | **1.438** | **32.83** | **+309.58** | **1.321** | **42.19** |

### Pre-creator / creator / post-creator split

| Strategy | Pre-creator | Creator/reconstruction window | Post-creator OOS |
|---|---|---|---|
| **AI8** | **+386.02%, PF 1.606** | **+504.11%, PF 1.742** | **+112.52%, PF 1.319** |
| **AI2** | **+624.41%, PF 1.360** | **+1564.85%, PF 1.998** | **+233.28%, PF 1.213** |
| **AI38** | **+85.96%, PF 1.248** from 2016-2020 | **+203.31%, PF 1.627** | **+68.04%, PF 1.359** |
| **AI58** | **+92.87%, PF 1.203** from 2016-2021 | **+275.62%, PF 1.731** | **+31.83%, PF 1.398** |

AI38 has an important conflicting deeper-history result that must not be hidden: its separately validated 2005-2020 backlog was negative with PF below 1. The 2016+ standardized result therefore improves the recent-regime case but does not erase the older failure.

AI58 also has validated history before 2016; that evidence remains part of its record rather than being discarded by the standardized comparison.

## Latest rolling windows

These standardized windows use the same frozen engines and data ending 2026-09-16. Existing prospective health monitors may use slightly different exact boundary dates and continuous-state slicing, so their health classifications remain the authoritative prospective-monitor view.

| Strategy | Latest 6m | Latest 12m | Latest 24m | Latest 36m | Latest 60m |
|---|---|---|---|---|---|
| **AI8** | **+23.07%, PF 1.617** | **−50.14%, PF 0.665** | **+126.96%, PF 1.502** | **+281.66%, PF 1.731** | **+430.19%, PF 1.563** |
| **AI2** | **+15.76%, PF 1.092** | **−183.97%, PF 0.641** | **+235.05%, PF 1.263** | **+532.18%, PF 1.454** | **+478.69%, PF 1.228** |
| **AI38** | **−23.98%, PF 0.480** | **+48.16%, PF 1.817** | **+74.24%, PF 1.559** | **+59.08%, PF 1.256** | **+237.29%, PF 1.663** |
| **AI58** | **+0.43%, PF 1.012** | **+38.38%, PF 1.522** | **+88.46%, PF 1.477** | **+116.38%, PF 1.415** | **+307.00%, PF 1.672** |

## Calendar-year behavior

The full-history totals are not smooth. Losing years remain important evidence:

- **AI8:** negative in 2018, 2022 and partial 2026; the latest 12 months are materially weak even though 24-60 month windows remain strong.
- **AI2:** negative in partial 2017, 2022 and partial 2026; creator sizing produces drawdown greater than initial capital and is not a viable deployment model.
- **AI38:** negative in 2016, 2017, 2024 and partial 2026; older 2005-2020 evidence was also weak.
- **AI58:** negative in 2017, near-flat 2019, negative 2020, and then positive calendar years 2021-2026-to-date. Its standardized full-history drawdown is the lowest of this four-strategy group, but the creator uses 7x fixed notional and therefore still requires normalized small-account testing.

## EXP6 coverage result

The EXP6 Triple MACD NQ public continuous source still begins in late 2022 for warmup, with scored history from 2023. Re-running the frozen evidence produced:

| Period | Net % | PF | Trades |
|---|---:|---:|---:|
| 2023 | **−10.93** | **0.948** | 73 |
| 2024 | **+159.75** | **2.028** | 66 |
| Jan-May 2025 creator-overlap | **+36.22** | **1.296** | 24 |
| Jun-Oct 2025 fresh OOS | **−17.26** | **0.713** | 25 |
| Full public 2023-Oct 2025 | **+221.36** | **1.412** | 187 |
| Separate May-Sep 2026 sample | **+35.69** | **3.395** | 6 |

This is not a 2016-present test. The two providers are deliberately **not stitched into a false continuous series**. EXP6 therefore remains below the project's long-history qualification gate regardless of its aggregate headline return.

## Research interpretation

### AI8

**Long-history signal contender; current 12-month regime weak; small-account gate pending.** The earliest available Binance history, pre-creator period, creator reconstruction, post-creator OOS and doubled-cost full history are all positive. The creator's pyramided fixed-cash sizing is not the eventual deployment model.

### AI2

**Signal remains historically interesting, but creator sizing is rejected.** Full history and doubled-cost history are positive, but the creator's 4x fixed notional creates >100% modeled drawdowns. The existing monitor already uses normalized sizing; a standardized full-history ~$5k/1x feasibility run is required before treating AI2 as a practical contender.

### AI38

**2016+ watchlist, not a clean long-term pass.** The standardized 2016+ history, costs and OOS are positive, but the previously validated 2005-2020 failure is material evidence against universal durability. It remains useful for regime research but is not a leading automation candidate.

### AI58

**Long-history signal contender; normalized small-account gate pending.** The standardized 2016+ full history, pre-creator history, creator window, post-creator OOS and doubled costs are all positive, with the lowest standardized full-history drawdown of the four rebaselined strategies. The creator's $70k notional on $10k capital is not acceptable as the deployment assumption.

### EXP6

**Insufficient long-history coverage.** Preserve as a frozen watchlist experiment, but do not count it as passing the 10-year/earliest-history screen.

## Next gate

The next apples-to-apples step for surviving contenders is a **small-account rebaseline around $5,000** using feasible position granularity and no hidden creator leverage. That should be run on AI8, AI2 and AI58 first, with AI38 retained as a secondary regime comparison. Parameters and signal logic remain frozen; only the deployment sizing layer changes.
