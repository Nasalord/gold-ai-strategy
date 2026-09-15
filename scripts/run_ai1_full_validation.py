from __future__ import annotations

import argparse, csv, json
from dataclasses import asdict
from datetime import datetime, timezone
from math import inf
from pathlib import Path

from ai_investing_lab.strategies.ai1_btc import AI1Backtester, AI1Config, Candle

UTC = timezone.utc
DATA_START = datetime(2017, 8, 17, tzinfo=UTC)
BACKLOG_START = datetime(2018, 3, 1, tzinfo=UTC)
CREATOR_START = datetime(2020, 3, 1, tzinfo=UTC)
CREATOR_END = datetime(2024, 3, 1, tzinfo=UTC)
OOS1_END = datetime(2025, 3, 1, tzinfo=UTC)
OOS2_END = datetime(2026, 3, 1, tzinfo=UTC)
VALIDATION_END = datetime(2026, 9, 15, tzinfo=UTC)
OOS_WARMUP_START = datetime(2023, 1, 1, tzinfo=UTC)


def parse_iso(v: str) -> datetime:
    d = datetime.fromisoformat(v.replace('Z','+00:00'))
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)


def load_csv(path: Path) -> list[Candle]:
    out=[]
    with path.open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out.append(Candle(parse_iso(r['timestamp']), float(r['open']), float(r['high']), float(r['low']), float(r['close']), float(r.get('volume') or 0)))
    return sorted(out, key=lambda x:x.time)


def run(candles, cfg, start, end):
    return AI1Backtester(cfg).run(candles, trade_start=start, trade_end=end)


def metrics(result):
    closed=[t for t in result.trades if t.closed]
    return {**asdict(result.metrics),
            'long_trades':sum(t.side.value=='long' for t in closed),
            'short_trades':sum(t.side.value=='short' for t in closed),
            'stop_exits':sum(t.exit_reason and t.exit_reason.value=='stop' for t in closed),
            'target_exits':sum(t.exit_reason and t.exit_reason.value=='target' for t in closed),
            'signal_exits':sum(t.exit_reason and t.exit_reason.value=='t3_or_ssl' for t in closed)}


def summarize_slice(trades, start, end, initial=10_000.0):
    ts=[t for t in trades if t.closed and t.exit_time and start <= t.exit_time < end]
    ts.sort(key=lambda t:(t.exit_time,t.entry_time))
    wins=[t for t in ts if t.net_pnl_usd>0]; losses=[t for t in ts if t.net_pnl_usd<=0]
    gp=sum(t.net_pnl_usd for t in wins); gl=abs(sum(t.net_pnl_usd for t in losses)); net=sum(t.net_pnl_usd for t in ts)
    eq=peak=initial; dd=0.0
    for t in ts:
        eq += t.net_pnl_usd; peak=max(peak,eq)
        if peak>0: dd=max(dd,(peak-eq)/peak)
    return {'trades':len(ts),'wins':len(wins),'losses':len(losses),'win_rate_pct':100*len(wins)/len(ts) if ts else 0.0,
            'net_profit_usd':net,'net_profit_pct':100*net/initial,'profit_factor':gp/gl if gl else (inf if gp else 0.0),
            'max_closed_trade_drawdown_pct':100*dd}


def shift_months(dt, delta):
    x=dt.year*12+dt.month-1+delta; y,m=divmod(x,12)
    return datetime(y,m+1,1,tzinfo=UTC)


def rolling(trades, months):
    rows=[]; end=shift_months(BACKLOG_START,months)
    last=datetime(2026,9,1,tzinfo=UTC)
    while end<=last:
        start=shift_months(end,-months)
        rows.append({'start':start.date().isoformat(),'end':end.date().isoformat(),**summarize_slice(trades,start,end)})
        end=shift_months(end,1)
    return rows


def pct_rank(vals, current):
    return 100*sum(v<=current for v in vals)/len(vals) if vals else 0.0


def oos_variant(candles, label, **overrides):
    cfg=AI1Config.creator_10m(**overrides)
    r=run(candles,cfg,CREATOR_END,VALIDATION_END)
    return {'label':label,'overrides':overrides,'full_oos':metrics(r),
            'oos_2024_2025':summarize_slice(r.trades,CREATOR_END,OOS1_END),
            'oos_2025_2026':summarize_slice(r.trades,OOS1_END,OOS2_END),
            'recent_2026_03_09':summarize_slice(r.trades,OOS2_END,VALIDATION_END)}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('csv_path',type=Path); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args()
    candles=load_csv(args.csv_path)
    cfg=AI1Config.creator_10m()

    backlog=run(candles,cfg,BACKLOG_START,CREATOR_START)
    creator=run(candles,cfg,CREATOR_START,CREATOR_END)
    oos=run(candles,cfg,CREATOR_END,VALIDATION_END)
    continuous=run(candles,cfg,BACKLOG_START,VALIDATION_END)
    paper=run(candles,AI1Config.creator_10m(fixed_cash_usd=10_000.0),BACKLOG_START,VALIDATION_END)

    oos_candles=[c for c in candles if c.time>=OOS_WARMUP_START]
    variants=[
        oos_variant(oos_candles,'baseline'),
        oos_variant(oos_candles,'commission_1p5x',commission_pct_per_side=0.15),
        oos_variant(oos_candles,'commission_2x',commission_pct_per_side=0.20),
        oos_variant(oos_candles,'slippage_2x',slippage_ticks=4),
        oos_variant(oos_candles,'costs_2x',commission_pct_per_side=0.20,slippage_ticks=4),
        oos_variant(oos_candles,'ssl_120',ssl_period=120),
        oos_variant(oos_candles,'ssl_160',ssl_period=160),
        oos_variant(oos_candles,'t3_fast_35',t3_fast_length=35),
        oos_variant(oos_candles,'t3_fast_45',t3_fast_length=45),
        oos_variant(oos_candles,'t3_slow_80',t3_slow_length=80),
        oos_variant(oos_candles,'t3_slow_100',t3_slow_length=100),
        oos_variant(oos_candles,'adx_smoothing_80',adx_smoothing=80),
        oos_variant(oos_candles,'adx_smoothing_120',adx_smoothing=120),
        oos_variant(oos_candles,'di_100',di_length=100),
        oos_variant(oos_candles,'di_120',di_length=120),
        oos_variant(oos_candles,'adx_ema_60',adx_ema_length=60),
        oos_variant(oos_candles,'adx_ema_100',adx_ema_length=100),
        oos_variant(oos_candles,'atr_length_100',atr_length=100),
        oos_variant(oos_candles,'atr_length_140',atr_length=140),
    ]

    years={}
    for y in range(2018,2027):
        s=max(BACKLOG_START,datetime(y,1,1,tzinfo=UTC)); e=min(VALIDATION_END,datetime(y+1,1,1,tzinfo=UTC))
        if s<e: years[str(y)]=summarize_slice(continuous.trades,s,e)

    roll={}
    for m in (6,12,24):
        rows=rolling(continuous.trades,m)
        current=summarize_slice(continuous.trades,shift_months(datetime(2026,9,1,tzinfo=UTC),-m),VALIDATION_END)
        roll[str(m)]={'profitable_fraction':sum(r['net_profit_pct']>0 for r in rows)/len(rows),
                      'pf_above_1_fraction':sum(r['profit_factor']>1 for r in rows)/len(rows),
                      'latest_partial_to_2026_09_15':current,
                      'latest_return_percentile':pct_rank([r['net_profit_pct'] for r in rows],current['net_profit_pct']),
                      'latest_pf_percentile':pct_rank([r['profit_factor'] for r in rows],current['profit_factor']),
                      'windows':rows}

    neighbors=[v for v in variants if v['label'] not in {'baseline','commission_1p5x','commission_2x','slippage_2x','costs_2x'}]
    double=next(v for v in variants if v['label']=='costs_2x')
    gates={'backlog_positive':backlog.metrics.net_profit_pct>0,'backlog_pf_gt_1':backlog.metrics.profit_factor>1,
           'oos_positive':oos.metrics.net_profit_pct>0,'oos_pf_gt_1':oos.metrics.profit_factor>1,
           'double_cost_oos_positive':double['full_oos']['net_profit_pct']>0,'double_cost_oos_pf_gt_1':double['full_oos']['profit_factor']>1,
           'all_neighbors_oos_positive':all(v['full_oos']['net_profit_pct']>0 for v in neighbors),
           'all_neighbors_oos_pf_gt_1':all(v['full_oos']['profit_factor']>1 for v in neighbors)}

    classification='LONG_HISTORY_AND_OOS_VALIDATED' if all(gates.values()) else ('OOS_FAILED' if not gates['oos_positive'] or not gates['oos_pf_gt_1'] else 'OOS_POSITIVE_ROBUSTNESS_MIXED')
    payload={'method':'Frozen AI1 source-faithful reconstruction; no parameter selection after OOS inspection.',
             'data':{'source':'Official Binance Vision Spot 5m aggregated to 10m','bars':len(candles),'first':candles[0].time.isoformat(),'last':candles[-1].time.isoformat()},
             'windows':{'backlog':'2018-03-01 to 2020-03-01','creator':'2020-03-01 to 2024-03-01','oos':'2024-03-01 to 2026-09-15 exclusive'},
             'baseline':{'backlog':metrics(backlog),'creator':metrics(creator),'oos':metrics(oos)},
             'paper_1x_normalized':{'full_2018_2026':metrics(paper)},
             'continuous_creator_sizing':{'full_2018_2026':metrics(continuous)},
             'year_by_year':years,'rolling':roll,'variants':variants,'gates':gates,'classification':classification,
             'notes':['Creator sizing is 10x fixed notional and is not treated as a practical risk configuration.','The 1x normalization keeps signals/cost assumptions but uses $10k fixed notional on $10k reference capital.']}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(payload,indent=2,allow_nan=True),encoding='utf-8')
    print(json.dumps({'classification':classification,'gates':gates,'baseline':payload['baseline'],'paper_1x':payload['paper_1x_normalized'],'latest_rolling':{k:v['latest_partial_to_2026_09_15'] for k,v in roll.items()}},indent=2,allow_nan=True))

if __name__=='__main__': main()
