from ai_investing_lab.strategies.triple_macd_nq.config import TripleMACDNQConfig
from ai_investing_lab.strategies.triple_macd_nq.engine import (
    TripleMACDNQBacktester,
    advance_long_a,
    advance_short_a,
    previous_window_high,
    previous_window_low,
)
from ai_investing_lab.strategies.triple_macd_nq.indicators import ema, macd_hist, tdfi


def test_creator_preset_is_frozen_to_supplied_nq_csv():
    c = TripleMACDNQConfig.creator_nq_10m()
    assert (c.long_fast, c.long_slow) == (150, 450)
    assert (c.mid_fast, c.mid_slow) == (45, 70)
    assert (c.short_fast, c.short_slow) == (28, 23)
    assert c.macd_signal == 9
    assert c.use_tdfi_filter and not c.use_chande_filter and not c.use_trend_filter
    assert (c.tdfi_lookback, c.tdfi_high, c.tdfi_low) == (50, 0.9, -0.8)
    assert c.enable_entry_a and not c.enable_entry_b
    assert c.sl_lookback == 10 and c.risk_reward == 3.5
    assert c.trade_direction == "Both"


def test_nq_contract_spec_and_creator_cost_assumptions():
    c = TripleMACDNQConfig.creator_nq_10m()
    assert c.point_value == 20.0
    assert c.min_tick == 0.25
    assert c.slippage_ticks == 5
    assert c.commission_usd_per_contract_per_order == 2.5
    bt = TripleMACDNQBacktester(c)
    assert bt._contracts(20_000.0) == 21.0
    assert bt._commission(21.0) == 52.5


def test_pine_ema_seed_and_macd_are_deterministic():
    xs = [10.0, 11.0, 13.0, 12.0]
    assert ema(xs, 3) == [10.0, 10.5, 11.75, 11.875]
    h = macd_hist(xs, 2, 3, 2)
    assert len(h) == len(xs)
    assert h[0] == 0.0


def test_entry_a_long_pipeline_and_filter_only_gate_initiation():
    c = TripleMACDNQConfig.creator_nq_10m()
    state, fire = advance_long_a(
        0, long_pos=True, mid_light_g=True, short_red=False, mid_dark_g=False,
        tdfi_value=0.91, cfg=c,
    )
    assert (state, fire) == (1, False)
    state, fire = advance_long_a(
        state, long_pos=True, mid_light_g=False, short_red=True, mid_dark_g=False,
        tdfi_value=-1.0, cfg=c,
    )
    assert (state, fire) == (2, False)
    state, fire = advance_long_a(
        state, long_pos=True, mid_light_g=False, short_red=False, mid_dark_g=True,
        tdfi_value=-1.0, cfg=c,
    )
    assert (state, fire) == (0, True)


def test_entry_a_long_resets_when_long_term_histogram_loses_positive_regime():
    c = TripleMACDNQConfig.creator_nq_10m()
    state, fire = advance_long_a(
        2, long_pos=False, mid_light_g=False, short_red=False, mid_dark_g=True,
        tdfi_value=1.0, cfg=c,
    )
    assert (state, fire) == (0, False)


def test_entry_a_short_pipeline_is_symmetric_with_asymmetric_tdfi_threshold():
    c = TripleMACDNQConfig.creator_nq_10m()
    state, fire = advance_short_a(
        0, long_pos=False, mid_light_r=True, short_green=False, mid_dark_r=False,
        tdfi_value=-0.81, cfg=c,
    )
    assert (state, fire) == (1, False)
    state, fire = advance_short_a(
        state, long_pos=False, mid_light_r=False, short_green=True, mid_dark_r=False,
        tdfi_value=1.0, cfg=c,
    )
    assert (state, fire) == (2, False)
    state, fire = advance_short_a(
        state, long_pos=False, mid_light_r=False, short_green=False, mid_dark_r=True,
        tdfi_value=1.0, cfg=c,
    )
    assert (state, fire) == (0, True)


def test_stop_window_excludes_signal_bar_like_ta_lowest_lookback_index_1():
    lows = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 50]
    highs = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 200]
    assert previous_window_low(lows, 10, 10) == 91
    assert previous_window_high(highs, 10, 10) == 109


def test_tdfi_has_source_shape_and_stays_normalized():
    close = [100.0 + i * 0.1 for i in range(300)]
    x = tdfi(close, 50, smooth=False)
    vals = [v for v in x if v is not None]
    assert len(x) == len(close)
    assert vals
    assert max(abs(v) for v in vals) <= 1.000000000001
