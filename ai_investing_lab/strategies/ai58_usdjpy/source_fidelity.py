from __future__ import annotations

from .orb_engine import AI58Backtester, Candle, Trade, _Session


class SourceFaithfulAI58Backtester(AI58Backtester):
    """Tightens one source semantic around range pre-arming.

    The uploaded Pine source requires `flat` in `canPreArm`. The original Python
    port could pre-arm the next session's order while a multi-session position
    remained open, then use that stale range-end TDFI after the old position
    eventually exited. Pine does not do that: if the position remains open on
    the final range bar, pre-arm is blocked; after the position later closes,
    the normal fallback may arm using the then-current TDFI.

    This subclass corrects that behavior without changing any strategy
    parameters. It can be folded into the base engine after parity validation.
    """

    def __init__(self, config):
        super().__init__(config)
        self._position_remained_open_on_bar = False

    def run(self, *args, **kwargs):
        # Each independent dataset/backtest must start with clean simulator
        # state. This matters when the same research object is reused for an
        # in-sample run and a later out-of-sample run.
        self._position_remained_open_on_bar = False
        return super().run(*args, **kwargs)

    def _evaluate_active_exit(self, trade: Trade, candle: Candle) -> bool:
        closed = super()._evaluate_active_exit(trade, candle)
        self._position_remained_open_on_bar = not closed
        return closed

    def _lock_and_arm(
        self,
        session: _Session,
        *,
        tdfi: float | None,
        arm_time,
    ) -> None:
        if self._position_remained_open_on_bar:
            return
        super()._lock_and_arm(session, tdfi=tdfi, arm_time=arm_time)
