# AI8 TradingView emulator diagnostic

Status: **SOURCE/VIDEO VERIFIED — TRADE GENERATION NEAR PARITY — CREATOR RETURN/PF NOT REPRODUCED**

This diagnostic keeps all AI8 strategy inputs frozen and varies only platform/execution interpretations that can legitimately differ between an independent Python reconstruction and TradingView's broker emulator.

## Creator benchmark

BTCUSDT 2h, 2020-03-01 to 2024-03-01:

- 319 trades
- +637.97% net profit
- PF 1.969
- 44.51% win rate
- 27.87% max drawdown

Video-verified Properties/behavior:

- initial capital $100,000
- fixed cash order size $80,000 per accepted entry
- pyramiding 7
- commission 0.1% on each entry and exit
- slippage 2 ticks
- Long only
- Range Filter sell closes the Long stack
- newest 10x ATR stop is described by the creator as the active stop for the stacked Long position

## Independent Binance spot baseline

With official Binance Vision spot 2h candles and one year of indicator prehistory:

- 325 trades
- +504.11% net profit
- PF 1.7423
- 44.00% win rate
- 26.55% closed-trade DD approximation
- 306 Range Filter exits / 19 stop exits

Trade generation is close to the creator benchmark, but return and PF are materially lower.

## Broker-emulator controls

None materially changed the result:

- cash quantity calculated at signal close vs actual fill
- shared stop replacement at signal close vs after next-open entry fill
- allow/disallow price exit on the entry bar
- BTC quantity-step rounding

All remained approximately 325 trades / +504.1% / PF 1.742.

## Calculation-start / warmup controls

TradingView documents that Deep Backtesting with a selected date range can start recursive indicator calculations at the beginning of that range. We therefore tested different prehistory lengths.

| Calculation history | Trades | Net | PF | Win |
|---|---:|---:|---:|---:|
| Exact 2020-03-01 start | 324 | +514.81% | 1.7673 | 44.14% |
| 30d warmup | 325 | +504.11% | 1.7423 | 44.00% |
| 60d+ warmup | 325 | +504.11% | 1.7423 | 44.00% |

Deep-start behavior improves the result slightly but does not reproduce the benchmark.

An 80%-of-equity sizing control produced +990.85% with roughly 80% closed-trade DD, which strongly disagrees with the creator's reported 27.87% DD. This supports the fixed-$80K interpretation rather than percent-of-equity compounding.

## Exit-order scope controls

| Exit interpretation | Trades | Net | PF | Win | DD |
|---|---:|---:|---:|---:|---:|
| Shared latest stop | 325 | +504.11% | 1.7423 | 44.00% | 26.55% |
| Per-leg original stops | 325 | +477.03% | 1.6761 | 43.69% | 33.60% |
| No ATR stop; Range Filter only | 322 | +509.23% | 1.7702 | 45.34% | 34.82% |

The creator-described shared-latest-stop behavior remains the closest interpretation. Removing the stop does not explain the missing return/PF.

## Feed control

A Binance USD-M perpetual control was previously tested with the same frozen strategy and was farther from the benchmark than Binance spot:

- 323 trades
- +456.44%
- PF 1.651
- 44.27% win

So switching from Binance spot to Binance perpetual does not resolve parity.

## Decision

The current evidence supports the strategy mechanics and properties but **does not independently reproduce the creator's headline return/PF**. We should not tune indicator parameters or execution assumptions to force the benchmark.

Current classification:

`SOURCE VERIFIED -> VIDEO SETTINGS VERIFIED -> TRADE GENERATION NEAR PARITY -> RETURN/PF PARITY UNRESOLVED`

Next research should either obtain the creator's exact TradingView symbol/feed and exported Strategy Tester trade list, or treat the independent Binance spot reconstruction as the reproducible baseline for any OOS/robustness work.

Research/backtest/paper only. No live broker execution.
