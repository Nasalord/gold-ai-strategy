from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from ai_investing_lab.strategies.ai1_btc import AI1Backtester, AI1Config, Candle
from ai_investing_lab.strategies.ai1_btc.indicators import atr, crossover, crossunder, ssl_state


class AI1IndicatorTests(unittest.TestCase):
    def test_cross_helpers(self):
        a = [1.0, 2.0, 1.0]
        b = [1.5, 1.5, 1.5]
        self.assertTrue(crossover(a, b, 1))
        self.assertTrue(crossunder(a, b, 2))

    def test_ssl_state_can_flip(self):
        highs = [10, 10, 10, 12, 12, 12, 12]
        lows = [9, 9, 9, 10, 8, 8, 8]
        closes = [9.5, 9.5, 9.5, 12.5, 9.5, 7.5, 7.5]
        state = ssl_state(highs, lows, closes, 3)
        self.assertIn(1, state)
        self.assertIn(-1, state)

    def test_atr_wilder_seed(self):
        highs = [11, 12, 13, 14]
        lows = [9, 10, 11, 12]
        closes = [10, 11, 12, 13]
        values = atr(highs, lows, closes, 3)
        self.assertIsNone(values[1])
        self.assertIsNotNone(values[2])


class AI1EngineTests(unittest.TestCase):
    def test_empty_run(self):
        result = AI1Backtester(AI1Config.creator_10m()).run([])
        self.assertEqual(result.metrics.trades, 0)

    def test_config_overrides(self):
        cfg = AI1Config.creator_10m(fixed_cash_usd=10_000.0, commission_pct_per_side=0.2)
        self.assertEqual(cfg.fixed_cash_usd, 10_000.0)
        self.assertEqual(cfg.commission_pct_per_side, 0.2)


if __name__ == "__main__":
    unittest.main()
