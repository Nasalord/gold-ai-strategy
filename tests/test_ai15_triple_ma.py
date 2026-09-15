from dataclasses import replace
from datetime import datetime, timedelta, timezone

from ai_investing_lab.strategies.ai15_triple_ma.config import TripleMAConfig
from ai_investing_lab.strategies.ai15_triple_ma.engine import Candle, ExitReason, TripleMABacktester
from ai_investing_lab.strategies.ai15_triple_ma.indicators import crossed_above, tma

UTC = timezone.utc


def test_creator_es_10m_preset_is_distinct_from_pine_file_defaults():
    creator = TripleMAConfig.creator_es_10m()
    assert (creator.ma_a_length, creator.ma_b_length, creator.ma_c_length) == (35, 150, 100)
    assert (creator.ma_a_type, creator.ma_b_type, creator.ma_c_type) == ("TMA", "EMA", "SMA")
    assert creator.source == "low"
    assert creator.atr_length == 20
    assert creator.stop_atr_multiple == 8.5
    assert creator.target_atr_multiple == 6.5
    assert creator.initial_capital_usd == 100_000.0
    assert creator.order_cash_usd == 1_250_000.0
    assert creator.point_value == 50.0
    assert creator.min_tick == 0.25
    assert creator.slippage_ticks == 5
    assert creator.commission_usd_per_contract_per_order == 2.0

    defaults = TripleMAConfig.pine_file_defaults()
    assert (defaults.ma_a_length, defaults.ma_b_length, defaults.ma_c_length) == (2, 3, 375)
    assert defaults.atr_length == 100
    assert defaults.stop_atr_multiple == 10.5
    assert defaults.target_atr_multiple == 30.0


def test_one_mes_paper_case_changes_only_position_economics():
    creator = TripleMAConfig.creator_es_10m()
    mes = TripleMAConfig.one_mes_paper()
    assert mes.fixed_contracts == 1.0
    assert mes.initial_capital_usd == 5_000.0
    assert mes.point_value == 5.0
    assert (mes.ma_a_length, mes.ma_b_length, mes.ma_c_length) == (
        creator.ma_a_length,
        creator.ma_b_length,
        creator.ma_c_length,
    )
    assert (mes.atr_length, mes.stop_atr_multiple, mes.target_atr_multiple) == (
        creator.atr_length,
        creator.stop_atr_multiple,
        creator.target_atr_multiple,
    )


def test_tma_matches_double_sma_construction_from_pine_source():
    values = [1.0, 2.0, 3.0, 4.0]
    assert tma(values, 3) == [None, None, 2.0, 3.0]


def test_crossed_above_uses_current_strict_and_previous_non_strict_comparison():
    a = [1.0, 1.0, 2.0]
    b = [1.0, 1.5, 1.8]
    assert not crossed_above(a, b, 1)
    assert crossed_above(a, b, 2)


def test_signal_fills_next_bar_and_exit_can_fill_on_entry_bar():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = [1.0, 1.0, 1.0, 2.0, 3.0]
    candles = [
        Candle(start + timedelta(minutes=10 * i), x, x + 0.1, x - 0.1, x, 1.0)
        for i, x in enumerate(closes)
    ]
    cfg = replace(
        TripleMAConfig.creator_es_10m(),
        ma_a_length=2,
        ma_b_length=3,
        ma_c_length=4,
        ma_a_type="SMA",
        ma_b_type="SMA",
        ma_c_type="SMA",
        source="close",
        atr_length=1,
        stop_atr_multiple=1.0,
        target_atr_multiple=1.0,
        fixed_contracts=1.0,
        point_value=1.0,
        slippage_ticks=0,
        commission_usd_per_contract_per_order=0.0,
    )
    result = TripleMABacktester(cfg).run(candles)
    assert result.metrics.trades == 1
    trade = result.trades[0]
    assert trade.signal_time == candles[3].time
    assert trade.entry_time == candles[4].time
    assert trade.entry_price == 3.0
    assert trade.exit_reason == ExitReason.TARGET
    assert trade.exit_time == candles[4].time


def test_creator_cash_sizing_uses_futures_point_value():
    bt = TripleMABacktester(TripleMAConfig.creator_es_10m())
    assert bt._contracts(5000.0) == 5.0
    assert bt._commission(5.0) == 10.0
