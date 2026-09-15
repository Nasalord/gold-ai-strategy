import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ai_investing_lab.strategies.ai58_usdjpy import (
    AI58Backtester,
    AI58Config,
    Candle,
    ExitReason,
    Side,
    SizingMode,
    TradeDirection,
)


NY = ZoneInfo("America/New_York")


def c(y, m, d, hh, mm, o, h, l, cl):
    return Candle(
        datetime(y, m, d, hh, mm, tzinfo=NY).astimezone(timezone.utc),
        o,
        h,
        l,
        cl,
    )


class AI58USDJPYTests(unittest.TestCase):
    def cfg(self, **overrides):
        base = dict(
            slippage_ticks=0,
            commission_usd_per_standard_lot_per_side=0.0,
            min_tick=0.001,
        )
        base.update(overrides)
        return AI58Config.source_default_15m(**base)

    def test_source_defaults_match_uploaded_template(self):
        cfg = AI58Config.source_default_15m()
        self.assertEqual(cfg.range_start.hour, 9)
        self.assertEqual(cfg.range_start.minute, 30)
        self.assertEqual(cfg.range_end.hour, 9)
        self.assertEqual(cfg.range_end.minute, 45)
        self.assertEqual(cfg.direction, TradeDirection.BOTH)
        self.assertEqual(cfg.stop_mult, 1.0)
        self.assertEqual(cfg.tp_rr, 1.5)
        self.assertFalse(cfg.use_force_exit)
        self.assertFalse(cfg.use_tdfi)
        self.assertFalse(cfg.use_trailing_atr)

    def test_optimized_preset_is_now_video_derived(self):
        cfg = AI58Config.optimized_15m()
        self.assertEqual(cfg.range_start.hour, 6)
        self.assertEqual(cfg.range_start.minute, 0)
        self.assertEqual(cfg.range_end.hour, 8)
        self.assertEqual(cfg.range_end.minute, 15)
        self.assertEqual(cfg.direction, TradeDirection.LONG_ONLY)
        self.assertTrue(cfg.use_tdfi)
        self.assertTrue(cfg.use_trailing_atr)

    def test_long_breakout_arms_after_range_and_uses_source_geometry(self):
        candles = [
            c(2026, 9, 14, 9, 30, 150.00, 150.10, 149.90, 150.00),
            c(2026, 9, 14, 9, 45, 150.00, 150.20, 149.95, 150.15),
        ]
        result = AI58Backtester(self.cfg()).run(
            candles, close_open_position_at_end=False
        )
        self.assertEqual(len(result.trades), 1)
        trade = result.trades[0]
        self.assertEqual(trade.side, Side.LONG)
        self.assertAlmostEqual(trade.entry_price, 150.10)
        self.assertAlmostEqual(trade.base_distance_jpy, 0.20)
        self.assertAlmostEqual(trade.stop_price, 149.90)
        self.assertAlmostEqual(trade.target_price, 150.40)

    def test_new_entry_cannot_exit_on_same_historical_bar(self):
        candles = [
            c(2026, 9, 14, 9, 30, 150.00, 150.10, 149.90, 150.00),
            # This bar crosses the entry and would also cross the target if the
            # exit order existed intrabar. Pine creates the exit only at close.
            c(2026, 9, 14, 9, 45, 150.00, 150.50, 149.95, 150.20),
        ]
        result = AI58Backtester(self.cfg()).run(
            candles, close_open_position_at_end=False
        )
        self.assertEqual(len(result.trades), 1)
        self.assertFalse(result.trades[0].closed)

    def test_short_breakout_geometry(self):
        cfg = self.cfg(direction=TradeDirection.SHORT_ONLY)
        candles = [
            c(2026, 9, 14, 9, 30, 150.00, 150.10, 149.90, 150.00),
            c(2026, 9, 14, 9, 45, 150.00, 150.05, 149.80, 149.85),
        ]
        result = AI58Backtester(cfg).run(
            candles, close_open_position_at_end=False
        )
        trade = result.trades[0]
        self.assertEqual(trade.side, Side.SHORT)
        self.assertAlmostEqual(trade.entry_price, 149.90)
        self.assertAlmostEqual(trade.base_distance_jpy, 0.20)
        self.assertAlmostEqual(trade.stop_price, 150.10)
        self.assertAlmostEqual(trade.target_price, 149.60)

    def test_oco_uses_tradingview_intrabar_path_when_both_sides_hit(self):
        range_bar = c(2026, 9, 14, 9, 30, 150.00, 150.10, 149.90, 150.00)

        high_first = c(2026, 9, 14, 9, 45, 150.08, 150.20, 149.80, 150.00)
        result = AI58Backtester(self.cfg()).run(
            [range_bar, high_first], close_open_position_at_end=False
        )
        self.assertEqual(result.trades[0].side, Side.LONG)

        low_first = c(2026, 9, 15, 9, 30, 150.00, 150.10, 149.90, 150.00)
        low_first_break = c(2026, 9, 15, 9, 45, 149.92, 150.20, 149.80, 150.00)
        result = AI58Backtester(self.cfg()).run(
            [low_first, low_first_break], close_open_position_at_end=False
        )
        self.assertEqual(result.trades[0].side, Side.SHORT)

    def test_tdfi_is_checked_when_order_is_armed_and_does_not_retry(self):
        cfg = self.cfg(use_tdfi=True)
        candles = [
            c(2026, 9, 14, 9, 30, 150.00, 150.10, 149.90, 150.00),
            c(2026, 9, 14, 9, 45, 150.00, 150.05, 149.95, 150.00),
            c(2026, 9, 14, 10, 0, 150.00, 150.30, 149.70, 150.20),
        ]
        # 0.0 is neither > +0.05 nor < -0.05, so no orders are created on
        # the range bar. Later TDFI values must not cause a retry.
        tdfi = {
            candles[0].time: 0.0,
            candles[1].time: 1.0,
            candles[2].time: -1.0,
        }
        result = AI58Backtester(cfg).run(candles, tdfi_override=tdfi)
        self.assertEqual(result.metrics.trades, 0)

    def test_tdfi_can_arm_only_long_or_only_short(self):
        candles = [
            c(2026, 9, 14, 9, 30, 150.00, 150.10, 149.90, 150.00),
            c(2026, 9, 14, 9, 45, 150.00, 150.20, 149.80, 150.00),
        ]
        cfg = self.cfg(use_tdfi=True)
        result = AI58Backtester(cfg).run(
            candles,
            tdfi_override={candles[0].time: 0.5, candles[1].time: 0.5},
            close_open_position_at_end=False,
        )
        self.assertEqual(result.trades[0].side, Side.LONG)

        range_bar = c(2026, 9, 15, 9, 30, 150.00, 150.10, 149.90, 150.00)
        break_bar = c(2026, 9, 15, 9, 45, 150.00, 150.20, 149.80, 150.00)
        result = AI58Backtester(cfg).run(
            [range_bar, break_bar],
            tdfi_override={range_bar.time: -0.5, break_bar.time: -0.5},
            close_open_position_at_end=False,
        )
        self.assertEqual(result.trades[0].side, Side.SHORT)

    def test_force_exit_submits_on_trigger_bar_and_fills_next_open(self):
        cfg = self.cfg(
            direction=TradeDirection.LONG_ONLY,
            use_force_exit=True,
            force_exit=datetime.strptime("10:00", "%H:%M").time(),
            stop_mult=10.0,
            tp_rr=10.0,
        )
        candles = [
            c(2026, 9, 14, 9, 30, 150.00, 150.10, 149.90, 150.00),
            c(2026, 9, 14, 9, 45, 150.00, 150.20, 149.95, 150.10),
            c(2026, 9, 14, 10, 0, 150.10, 150.15, 150.05, 150.10),
            c(2026, 9, 14, 10, 15, 150.12, 150.15, 150.08, 150.11),
        ]
        result = AI58Backtester(cfg).run(candles)
        trade = result.trades[0]
        self.assertEqual(trade.exit_reason, ExitReason.FORCE_EXIT)
        self.assertEqual(trade.exit_time, candles[-1].time)
        self.assertAlmostEqual(trade.exit_price, 150.12)

    def test_usdjpy_pnl_is_converted_to_usd(self):
        bt = AI58Backtester(self.cfg())
        gross = bt._gross_pnl_usd(Side.LONG, 150.0, 151.0, 70_000.0)
        self.assertAlmostEqual(gross, 70_000.0 / 151.0)

    def test_creator_commission_scales_by_standard_lot(self):
        cfg = AI58Config.source_default_15m(
            slippage_ticks=0,
            commission_usd_per_standard_lot_per_side=3.50,
        )
        bt = AI58Backtester(cfg)
        self.assertAlmostEqual(bt._commission_usd(70_000.0), 4.90)

    def test_risk_sizing_is_capped_by_paper_notional(self):
        cfg = self.cfg(
            sizing_mode=SizingMode.RISK_BASED,
            risk_per_trade_pct=0.25,
            max_notional_usd=10_000.0,
        )
        bt = AI58Backtester(cfg)
        theoretical, actual = bt._position_size(
            side=Side.LONG,
            equity_usd=10_000.0,
            entry_price=150.0,
            stop_price=149.0,
        )
        self.assertGreater(theoretical, 0)
        self.assertLessEqual(actual, 10_000.0)


if __name__ == "__main__":
    unittest.main()
