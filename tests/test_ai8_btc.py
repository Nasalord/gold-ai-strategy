import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ai_investing_lab.strategies.ai8_btc import (
    AI8Backtester,
    AI8Config,
    Candle,
    SizingMode,
    ema,
    range_filter,
    rma,
)


class AI8Tests(unittest.TestCase):
    def test_source_inputs_are_locked(self):
        cfg = AI8Config.creator_video()
        self.assertEqual(cfg.timeframe_minutes, 120)
        self.assertEqual(cfg.supertrend_atr_length, 8)
        self.assertAlmostEqual(cfg.supertrend_factor, 1.6)
        self.assertEqual(cfg.adx_smoothing, 14)
        self.assertEqual(cfg.di_length, 14)
        self.assertEqual(cfg.adx_limit, 18)
        self.assertEqual(cfg.range_period, 175)
        self.assertAlmostEqual(cfg.range_multiplier, 5.0)
        self.assertEqual(cfg.stop_atr_length, 50)
        self.assertAlmostEqual(cfg.stop_atr_multiplier, 10.0)
        self.assertAlmostEqual(cfg.risk_reward_ratio, 100.0)
        self.assertTrue(cfg.long_only)

    def test_video_properties_are_locked(self):
        cfg = AI8Config.creator_video()
        self.assertEqual(cfg.initial_capital_usd, 100_000.0)
        self.assertEqual(cfg.sizing_mode, SizingMode.FIXED_CASH)
        self.assertEqual(cfg.fixed_cash_usd, 80_000.0)
        self.assertEqual(cfg.pyramiding, 7)
        self.assertEqual(cfg.commission_pct_per_side, 0.1)
        self.assertEqual(cfg.slippage_ticks, 2)

    def test_pine_source_defaults_remain_separate_from_video_properties(self):
        source = AI8Config.pine_source_default()
        self.assertEqual(source.sizing_mode, SizingMode.PERCENT_EQUITY)
        self.assertEqual(source.percent_of_equity, 15.0)
        self.assertEqual(source.pyramiding, 1)
        self.assertEqual(AI8Config.creator_percent_equity().percent_of_equity, 80.0)
        self.assertEqual(AI8Config.creator_fixed_cash().fixed_cash_usd, 80_000.0)

    def test_ema_seeds_from_first_non_na_value(self):
        values = [None, 10.0, 12.0, 14.0]
        out = ema(values, 3)
        self.assertIsNone(out[0])
        self.assertAlmostEqual(out[1], 10.0)
        self.assertAlmostEqual(out[2], 11.0)
        self.assertAlmostEqual(out[3], 12.5)

    def test_rma_uses_sma_seed(self):
        out = rma([1.0, 2.0, 3.0, 4.0], 3)
        self.assertEqual(out[:2], [None, None])
        self.assertAlmostEqual(out[2], 2.0)
        self.assertAlmostEqual(out[3], 2.0 + (4.0 - 2.0) / 3.0)

    def test_range_filter_emits_transition_not_every_trending_bar(self):
        closes = [100, 99, 98, 97, 98, 99, 100, 101, 100, 99, 98]
        _, longs, shorts = range_filter(closes, period=1, multiplier=0.1)
        self.assertLessEqual(sum(longs), 2)
        self.assertLessEqual(sum(shorts), 2)

    def test_percent_equity_sizing_compounds_and_fixed_cash_does_not(self):
        pct = AI8Backtester(
            AI8Config.creator_percent_equity(commission_pct_per_side=0, slippage_ticks=0)
        )
        fixed = AI8Backtester(
            AI8Config.creator_video(commission_pct_per_side=0, slippage_ticks=0)
        )
        self.assertAlmostEqual(pct._entry_notional(100_000.0), 80_000.0)
        self.assertAlmostEqual(pct._entry_notional(150_000.0), 120_000.0)
        self.assertAlmostEqual(fixed._entry_notional(100_000.0), 80_000.0)
        self.assertAlmostEqual(fixed._entry_notional(150_000.0), 80_000.0)

    def test_cash_quantity_uses_signal_price_not_fill_price(self):
        bt = AI8Backtester(AI8Config.creator_video())
        self.assertAlmostEqual(bt._entry_quantity(100_000.0, 40_000.0), 2.0)
        self.assertAlmostEqual(bt._entry_quantity(500_000.0, 40_000.0), 2.0)

    def test_commission_is_percent_of_actual_transaction(self):
        bt = AI8Backtester(AI8Config.creator_video())
        self.assertAlmostEqual(bt._commission(80_123.45), 80.12345)

    def test_slippage_is_two_btcusdt_ticks(self):
        bt = AI8Backtester(AI8Config.creator_video())
        self.assertAlmostEqual(bt.slippage, 0.02)

    def test_pyramiding_cap_limits_open_entry_legs(self):
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        candles = [
            Candle(base + timedelta(hours=2 * i), 100, 101, 99, 100)
            for i in range(7)
        ]
        directions = [1, -1, 1, -1, 1, -1, 1]
        cfg = AI8Config.creator_video(
            pyramiding=2,
            fixed_cash_usd=1_000,
            commission_pct_per_side=0,
            slippage_ticks=0,
        )
        n = len(candles)
        with (
            patch("ai_investing_lab.strategies.ai8_btc.engine.adx", return_value=[20.0] * n),
            patch(
                "ai_investing_lab.strategies.ai8_btc.engine.supertrend_direction",
                return_value=directions,
            ),
            patch("ai_investing_lab.strategies.ai8_btc.engine.atr", return_value=[1.0] * n),
            patch(
                "ai_investing_lab.strategies.ai8_btc.engine.range_filter",
                return_value=([100.0] * n, [False] * n, [False] * n),
            ),
        ):
            result = AI8Backtester(cfg).run(candles, close_at_end=True)
        self.assertEqual(result.metrics.trades, 2)

    def test_newest_entry_reissues_shared_stop_for_all_legs(self):
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        candles = [
            Candle(base + timedelta(hours=0), 100, 101, 99, 100),
            Candle(base + timedelta(hours=2), 100, 101, 99, 100),
            Candle(base + timedelta(hours=4), 100, 105, 95, 102),
            Candle(base + timedelta(hours=6), 110, 111, 109, 110),
            Candle(base + timedelta(hours=8), 110, 111, 95, 108),
        ]
        directions = [1, -1, 1, -1, 1]
        cfg = AI8Config.creator_video(
            pyramiding=7,
            fixed_cash_usd=1_000,
            commission_pct_per_side=0,
            slippage_ticks=0,
            stop_atr_multiplier=10,
        )
        n = len(candles)
        with (
            patch("ai_investing_lab.strategies.ai8_btc.engine.adx", return_value=[20.0] * n),
            patch(
                "ai_investing_lab.strategies.ai8_btc.engine.supertrend_direction",
                return_value=directions,
            ),
            patch("ai_investing_lab.strategies.ai8_btc.engine.atr", return_value=[1.0] * n),
            patch(
                "ai_investing_lab.strategies.ai8_btc.engine.range_filter",
                return_value=([100.0] * n, [False] * n, [False] * n),
            ),
        ):
            result = AI8Backtester(cfg).run(candles)
        self.assertEqual(result.metrics.trades, 2)
        self.assertTrue(all(t.exit_price == 100.0 for t in result.trades))
        self.assertTrue(all(t.exit_reason.value == "stop_loss" for t in result.trades))

    def test_intrabar_drawdown_is_reported_separately(self):
        result = AI8Backtester(AI8Config.creator_video()).run([])
        self.assertEqual(result.metrics.max_intrabar_drawdown_pct, 0.0)

    def test_empty_backtest(self):
        result = AI8Backtester(AI8Config.creator_video()).run([])
        self.assertEqual(result.metrics.trades, 0)
        self.assertEqual(result.metrics.net_profit_pct, 0.0)

    def test_candle_validation_requires_timezone(self):
        with self.assertRaises(ValueError):
            Candle(datetime(2026, 1, 1), 100, 101, 99, 100).validate()
        Candle(datetime(2026, 1, 1, tzinfo=timezone.utc), 100, 101, 99, 100).validate()


if __name__ == "__main__":
    unittest.main()
