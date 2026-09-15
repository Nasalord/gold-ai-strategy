import unittest
from datetime import time

from ai_investing_lab.strategies.ai58_usdjpy import (
    AI58Config,
    RankingSheetBenchmark,
    TradeDirection,
    VideoBenchmark,
    VideoOOSBenchmark,
)


class AI58VideoPresetTests(unittest.TestCase):
    def test_optimized_video_preset(self):
        cfg = AI58Config.optimized_15m()
        self.assertEqual(cfg.timeframe_minutes, 15)
        self.assertEqual(cfg.timezone, "America/New_York")
        self.assertEqual(cfg.range_start, time(6, 0))
        self.assertEqual(cfg.range_end, time(8, 15))
        self.assertEqual(cfg.direction, TradeDirection.LONG_ONLY)
        self.assertTrue(cfg.use_tdfi)
        self.assertEqual(cfg.tdfi_lookback, 50)
        self.assertEqual(cfg.tdfi_filter_high, 0.0)
        self.assertEqual(cfg.tdfi_filter_low, 0.0)
        self.assertTrue(cfg.use_trailing_atr)
        self.assertEqual(cfg.trailing_atr_length, 450)
        self.assertEqual(cfg.trailing_atr_multiplier, 11.0)
        self.assertFalse(cfg.use_force_exit)
        self.assertEqual(cfg.fixed_notional_usd, 70_000.0)
        self.assertEqual(cfg.initial_capital_usd, 10_000.0)
        self.assertEqual(cfg.slippage_ticks, 12)
        self.assertEqual(cfg.min_tick, 0.001)
        self.assertEqual(cfg.commission_usd_per_standard_lot_per_side, 3.50)

    def test_fixed_exit_values_are_explicit_asr_hypothesis(self):
        cfg = AI58Config.optimized_15m()
        self.assertEqual(cfg.stop_mult, 100.0)
        self.assertEqual(cfg.tp_rr, 100.0)

    def test_video_and_ranking_benchmarks_remain_separate(self):
        video = VideoBenchmark()
        ranking = RankingSheetBenchmark()
        self.assertEqual(video.trades, 185)
        self.assertEqual(ranking.trades, 229)
        self.assertNotEqual(video.net_profit_pct, ranking.net_profit_pct)

    def test_video_oos_benchmark(self):
        oos = VideoOOSBenchmark()
        self.assertEqual(oos.trades, 24)
        self.assertEqual(oos.win_rate_pct, 50.0)
        self.assertEqual(oos.profit_factor, 1.57)


if __name__ == "__main__":
    unittest.main()
