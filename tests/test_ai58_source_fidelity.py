import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ai_investing_lab.strategies.ai58_usdjpy import AI58Config, Candle, TradeDirection
from ai_investing_lab.strategies.ai58_usdjpy.source_fidelity import SourceFaithfulAI58Backtester


NY = ZoneInfo("America/New_York")


def c(y, m, d, hh, mm, o, h, l, cl):
    return Candle(
        datetime(y, m, d, hh, mm, tzinfo=NY).astimezone(timezone.utc),
        o,
        h,
        l,
        cl,
    )


class AI58SourceFidelityTests(unittest.TestCase):
    def test_open_position_blocks_next_session_prearm(self):
        cfg = AI58Config.source_default_15m(
            direction=TradeDirection.LONG_ONLY,
            stop_mult=1.0,
            tp_rr=100.0,
            slippage_ticks=0,
            commission_usd_per_standard_lot_per_side=0.0,
        )
        candles = [
            # Day 1 range + breakout. Stop is 149.90 and remains unhit overnight.
            c(2026, 9, 14, 9, 30, 150.00, 150.10, 149.90, 150.00),
            c(2026, 9, 14, 9, 45, 150.05, 150.20, 150.00, 150.15),
            c(2026, 9, 14, 10, 0, 150.15, 150.30, 150.05, 150.20),
            # Day 2 range forms while the Day 1 position is still open.
            c(2026, 9, 15, 9, 30, 151.00, 151.10, 150.90, 151.00),
            # Old position stops here. This same bar also breaks Day 2 range high.
            # Source `flat` blocked Day 2 pre-arm, so no new entry may fill yet.
            c(2026, 9, 15, 9, 45, 151.00, 151.20, 149.80, 151.05),
            # Fallback order armed after the old position closed; it can fill now.
            c(2026, 9, 15, 10, 0, 151.05, 151.30, 151.00, 151.20),
        ]

        result = SourceFaithfulAI58Backtester(cfg).run(
            candles, close_open_position_at_end=False
        )
        self.assertEqual(len(result.trades), 2)
        self.assertEqual(result.trades[1].entry_time, candles[-1].time)


if __name__ == "__main__":
    unittest.main()
