from __future__ import annotations

import unittest

from ai_investing_lab.strategies.ai2_eth import AI2Backtester, AI2Config
from ai_investing_lab.strategies.ai2_eth.indicators import atr, crossover, ema, tma


class AI2IndicatorTests(unittest.TestCase):
    def test_frozen_config(self):
        cfg = AI2Config.creator_15m()
        self.assertEqual((cfg.ma_a_type, cfg.ma_a_length), ("TMA", 2))
        self.assertEqual((cfg.ma_b_type, cfg.ma_b_length), ("EMA", 3))
        self.assertEqual((cfg.ma_c_type, cfg.ma_c_length), ("SMA", 375))
        self.assertEqual(cfg.source, "low")
        self.assertEqual(cfg.atr_length, 100)
        self.assertEqual(cfg.atr_stop_multiplier, 10.5)
        self.assertEqual(cfg.atr_take_profit_multiplier, 30.0)
        self.assertEqual(cfg.fixed_cash_usd, 40_000.0)
        self.assertEqual(cfg.commission_pct_per_side, 0.1)
        self.assertEqual(cfg.slippage_ticks, 2)

    def test_tma_two_is_two_bar_sma(self):
        values = [1.0, 2.0, 4.0, 8.0]
        self.assertEqual(tma(values, 2), [None, 1.5, 3.0, 6.0])

    def test_ema_three_seeds_first_value(self):
        values = [10.0, 12.0, 14.0]
        self.assertEqual(ema(values, 3), [10.0, 11.0, 12.5])

    def test_cross_helper(self):
        self.assertTrue(crossover([1.0, 2.0], [1.5, 1.5], 1))

    def test_atr_wilder_seed(self):
        values = atr([11, 12, 13, 14], [9, 10, 11, 12], [10, 11, 12, 13], 3)
        self.assertIsNone(values[1])
        self.assertAlmostEqual(values[2], 2.0)


class AI2EngineTests(unittest.TestCase):
    def test_empty_run(self):
        result = AI2Backtester(AI2Config.creator_15m()).run([])
        self.assertEqual(result.metrics.trades, 0)

    def test_cost_override(self):
        cfg = AI2Config.creator_15m(commission_pct_per_side=0.2, slippage_ticks=4)
        self.assertEqual(cfg.commission_pct_per_side, 0.2)
        self.assertEqual(cfg.slippage_ticks, 4)


if __name__ == "__main__":
    unittest.main()
