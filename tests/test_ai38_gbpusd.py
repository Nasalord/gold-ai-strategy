from __future__ import annotations

import unittest

from ai_investing_lab.strategies.ai38_gbpusd import AI38Backtester, AI38Config
from ai_investing_lab.strategies.ai38_gbpusd.indicators import crossover, crossunder, ema, growth_percent, momentum


class AI38IndicatorTests(unittest.TestCase):
    def test_ema_and_momentum(self):
        values = [1.0, 2.0, 3.0, 4.0]
        e = ema(values, 2)
        self.assertEqual(e[0], 1.0)
        self.assertIsNotNone(e[-1])
        m = momentum(values, 2)
        self.assertIsNone(m[1])
        self.assertEqual(m[2], 2.0)

    def test_cross_helpers(self):
        values = [-1.0, 1.0, -1.0]
        self.assertTrue(crossover(values, 0.0, 1))
        self.assertTrue(crossunder(values, 0.0, 2))

    def test_growth_percent(self):
        values = [1.0, 2.0, 3.0, 2.0]
        self.assertAlmostEqual(growth_percent(values, 2, 2, rising=True), 100.0)
        self.assertAlmostEqual(growth_percent(values, 3, 2, rising=False), 50.0)


class AI38EngineTests(unittest.TestCase):
    def test_empty_run(self):
        result = AI38Backtester(AI38Config.creator_4h()).run([])
        self.assertEqual(result.metrics.trades, 0)

    def test_creator_costs(self):
        cfg = AI38Config.creator_4h()
        self.assertEqual(cfg.fixed_units, 100_000.0)
        self.assertAlmostEqual(cfg.commission_usd_per_contract_per_side * cfg.fixed_units, 5.0)
        self.assertAlmostEqual(cfg.slippage_ticks * cfg.min_tick, 0.0002)

    def test_both_direction_preserves_source_or_growth_gate(self):
        cfg = AI38Config.creator_4h()
        self.assertEqual(cfg.trade_direction, "Both")
        self.assertTrue(cfg.use_ema_growth_check)


if __name__ == "__main__":
    unittest.main()
