import unittest

from ai_investing_lab.strategies.ai65_gold import (
    BacktestMetrics,
    evaluate_creator_parity,
)


class AI65ParityTests(unittest.TestCase):
    def metrics(self, **overrides):
        values = dict(
            trades=670,
            wins=353,
            losses=317,
            win_rate_pct=52.69,
            gross_profit=1000.0,
            gross_loss=599.88,
            net_profit=55294.0,
            net_profit_pct=552.94,
            profit_factor=1.667,
            expectancy=82.528,
            average_winner=1.0,
            average_loser=-1.0,
            average_r=0.1,
            max_drawdown_pct=25.73,
            ambiguous_trades=0,
        )
        values.update(overrides)
        return BacktestMetrics(**values)

    def test_exact_creator_benchmark_passes(self):
        result = evaluate_creator_parity(self.metrics())
        self.assertTrue(result["passed"])
        self.assertTrue(all(result["checks"].values()))

    def test_material_trade_count_mismatch_fails(self):
        result = evaluate_creator_parity(self.metrics(trades=660))
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["trades"])


if __name__ == "__main__":
    unittest.main()
