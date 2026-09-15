import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ai_investing_lab.strategies.ai65_gold import (
    AI65Backtester,
    AI65Config,
    Candle,
    ExecutionMode,
    ExitReason,
    SizingMode,
    TDFIGating,
    compute_tdfi,
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


class AI65GoldTests(unittest.TestCase):
    def cfg(self, **kwargs):
        base = dict(
            timeframe_minutes=60,
            slippage_ticks=0,
            commission_per_contract_per_side=0.0,
            min_tick=0.01,
        )
        base.update(kwargs)
        return AI65Config.creator_1h(**base)

    def test_target_rr_conversion(self):
        cfg = self.cfg()
        self.assertAlmostEqual(cfg.internal_tp_rr, 3.3 / 3.8)

    def test_tdfi_ema_seeds_from_first_value(self):
        values = compute_tdfi([100, 101, 102, 103, 104, 105], lookback=2)
        self.assertIsNone(values[0])
        self.assertIsNotNone(values[1])

    def test_flat_tdfi_is_na_not_zero(self):
        values = compute_tdfi([100.0] * 20, lookback=5)
        self.assertTrue(all(v is None for v in values))

    def test_13_bar_is_excluded_and_breakout_can_enter_intrabar(self):
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 104, 107, 50, 106.5),
        ]
        tdfi = {candles[1].time: 0.0, candles[2].time: 0.0}
        result = AI65Backtester(self.cfg()).run(candles, tdfi_override=tdfi)
        self.assertEqual(len(result.trades), 1)
        trade = result.trades[0]
        self.assertEqual(trade.or_high, 106)
        self.assertEqual(trade.or_low, 99)
        self.assertEqual(trade.entry_price, 106)
        self.assertAlmostEqual(trade.base_distance, 7)
        self.assertEqual(trade.order_arm_time, candles[1].time + timedelta(hours=1))

    def test_tdfi_equal_threshold_does_not_arm(self):
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 104, 110, 103, 108),
        ]
        tdfi = {candles[1].time: -0.05, candles[2].time: 1.0}
        result = AI65Backtester(self.cfg()).run(candles, tdfi_override=tdfi)
        self.assertEqual(result.metrics.trades, 0)

    def test_source_arm_filter_does_not_retry_later(self):
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 104, 105, 103, 104),
            c(2026, 9, 14, 14, 0, 104, 110, 103, 109),
        ]
        tdfi = {
            candles[1].time: -0.2,
            candles[2].time: 1.0,
            candles[3].time: 1.0,
        }
        result = AI65Backtester(self.cfg()).run(candles, tdfi_override=tdfi)
        self.assertEqual(result.metrics.trades, 0)

    def test_video_oanda_preset_uses_breakout_tdfi_and_three_decimal_tick(self):
        cfg = AI65Config.video_oanda_1h()
        self.assertEqual(cfg.symbol, "OANDA:XAUUSD")
        self.assertEqual(cfg.timeframe_minutes, 60)
        self.assertEqual(cfg.tdfi_gating, TDFIGating.ENTRY_TIME)
        self.assertEqual(cfg.min_tick, 0.001)
        self.assertEqual(cfg.slippage_ticks, 100)

    def test_video_entry_time_can_trade_when_arm_time_tdfi_fails(self):
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 104, 110, 103, 108),
        ]
        tdfi = {
            candles[1].time: -0.2,
            candles[2].time: 0.2,
        }

        source_cfg = self.cfg()
        source = AI65Backtester(source_cfg).run(
            candles,
            tdfi_override=tdfi,
            close_open_position_at_end=False,
        )
        self.assertEqual(source.metrics.trades, 0)

        video_cfg = AI65Config.video_oanda_1h(
            slippage_ticks=0,
            commission_per_contract_per_side=0.0,
        )
        video = AI65Backtester(video_cfg).run(
            candles,
            tdfi_override=tdfi,
            close_open_position_at_end=False,
        )
        self.assertEqual(len(video.trades), 1)
        self.assertEqual(video.trades[0].entry_time, candles[2].time)
        self.assertEqual(video.trades[0].tdfi_at_arm, -0.2)
        self.assertEqual(video.trades[0].tdfi_at_entry, 0.2)

    def test_video_entry_time_waits_for_later_qualifying_breakout_bar(self):
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 104, 108, 103, 107),
            c(2026, 9, 14, 14, 0, 107, 109, 106, 108),
        ]
        tdfi = {
            candles[1].time: -0.2,
            candles[2].time: -0.2,
            candles[3].time: 0.2,
        }
        cfg = AI65Config.video_oanda_1h(
            slippage_ticks=0,
            commission_per_contract_per_side=0.0,
        )
        result = AI65Backtester(cfg).run(
            candles,
            tdfi_override=tdfi,
            close_open_position_at_end=False,
        )
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].entry_time, candles[3].time)
        self.assertEqual(result.trades[0].tdfi_at_entry, 0.2)

    def test_stop_and_target_geometry_uses_actual_fill(self):
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 108, 109, 107, 108),
        ]
        tdfi = {candles[1].time: 0.0, candles[2].time: 0.0}
        result = AI65Backtester(self.cfg()).run(
            candles, tdfi_override=tdfi, close_open_position_at_end=False
        )
        trade = result.trades[0]
        self.assertEqual(trade.entry_price, 108)
        self.assertEqual(trade.base_distance, 9)
        self.assertAlmostEqual(trade.stop_price, 108 - 9 * 3.8)
        self.assertAlmostEqual(trade.target_price, 108 + 9 * 3.3)
        self.assertNotAlmostEqual(trade.target_price, 108 + 9 * 3.8 * 3.3)

    def test_creator_sizing_is_fixed_notional(self):
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 108, 109, 107, 108),
        ]
        tdfi = {x.time: 0.0 for x in candles}
        result = AI65Backtester(self.cfg()).run(
            candles, tdfi_override=tdfi, close_open_position_at_end=False
        )
        trade = result.trades[0]
        self.assertAlmostEqual(trade.notional_exposure, 70_000)

    def test_guarded_3m_uses_risk_based_capped_sizing(self):
        cfg = AI65Config.guarded_3m(
            slippage_ticks=0,
            commission_per_contract_per_side=0.0,
            max_notional=1_000.0,
            risk_per_trade_pct=0.25,
        )
        bt = AI65Backtester(cfg)
        theoretical, actual = bt._position_size(
            equity=10_000.0, entry_price=100.0, stop_price=90.0
        )
        self.assertAlmostEqual(theoretical, 2.5)
        self.assertAlmostEqual(actual, 2.5)

        _, actual_capped = bt._position_size(
            equity=10_000.0, entry_price=100.0, stop_price=99.9
        )
        self.assertAlmostEqual(actual_capped, 10.0)

    def test_one_trade_per_session(self):
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 104, 140, 103, 130),
            c(2026, 9, 14, 14, 0, 106, 150, 100, 120),
        ]
        tdfi = {x.time: 0.0 for x in candles}
        result = AI65Backtester(self.cfg()).run(candles, tdfi_override=tdfi)
        self.assertEqual(result.metrics.trades, 1)
        self.assertEqual(result.trades[0].exit_reason, ExitReason.TAKE_PROFIT)

    def test_force_exit_fills_next_bar_open(self):
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 104, 107, 103, 106),
            c(2026, 9, 14, 21, 0, 106, 108, 105, 107),
            c(2026, 9, 14, 22, 0, 107, 108, 106, 107.5),
            c(2026, 9, 14, 23, 0, 108, 109, 107, 108.5),
        ]
        tdfi = {x.time: 0.0 for x in candles}
        result = AI65Backtester(self.cfg()).run(candles, tdfi_override=tdfi)
        trade = result.trades[0]
        self.assertEqual(trade.exit_reason, ExitReason.FORCE_EXIT)
        self.assertEqual(trade.exit_time, candles[-1].time)
        self.assertEqual(trade.exit_price, 108)

    def test_guarded_mode_blocks_post_22_entry(self):
        cfg = AI65Config.creator_1h(
            execution_mode=ExecutionMode.GUARDED,
            sizing_mode=SizingMode.RISK_BASED,
            slippage_ticks=0,
            commission_per_contract_per_side=0.0,
        )
        candles = [
            c(2026, 9, 14, 11, 0, 100, 105, 99, 103),
            c(2026, 9, 14, 12, 0, 103, 106, 101, 104),
            c(2026, 9, 14, 13, 0, 104, 105, 103, 104),
            c(2026, 9, 14, 22, 0, 104, 120, 103, 115),
        ]
        tdfi = {x.time: 0.0 for x in candles}
        result = AI65Backtester(cfg).run(candles, tdfi_override=tdfi)
        self.assertEqual(result.metrics.trades, 0)

    def test_dst_conversion_keeps_new_york_session_clock(self):
        candle = c(2026, 3, 9, 11, 0, 100, 101, 99, 100)
        self.assertEqual(candle.time.hour, 15)


if __name__ == "__main__":
    unittest.main()
