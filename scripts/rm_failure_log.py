"""Builds results/rm/FAILURE_LOG.md from train_results.json + validation looks (first-look numbers copied from the run logs)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rm_ideas import IDEAS, RES
tr = json.load(open(f'{RES}/train_results.json')); va2 = json.load(open(f'{RES}/validation_results.json')); p4 = json.load(open(f'{RES}/phase4_results.json'))
first = {'A1': (0.44, -0.162, 'fail'), 'A2': (0.57, -0.072, 'fail (L=50, edge pick)'), 'A3': (0.63, -0.077, 'fail (n=20,m=3.5, corner pick)'), 'B2h': (0.24, -0.089, 'fail (p=90, edge pick)')}
why = {'A1': 'Symmetric shorts doubled turnover (174 trades/yr) and lost in the 2022-23 chop; validation drawdown -16%.',
       'A2': 'Shorting below the 200-DMA-style filter did not pay in 2022-23; Sharpe below baseline at both L=50 and L=100.',
       'A3': 'Daily Supertrend agreement: after the plateau-rule correction only 38% of neighbours beat baseline on train, so the idea fails train (a lone peak).',
       'B1e': 'Efficiency-ratio chop filter removed profitable trend days; train Sharpe far below baseline for every cell.', 'B1a': 'ADX chop filter: same, 0 of neighbours beat baseline.',
       'B2h': 'PASSED: standing aside when prior-day VIX percentile > 80 cut train drawdown from -13.4% to -5.6% and validated (second look). Failed the final test: Sharpe -0.09 vs 0.46.',
       'B2l': 'Standing aside in low-vol regimes did not help.', 'C1': 'Confirmation bars only delayed entries; best cell is n=1 = the baseline itself.',
       'D1': 'Intraday-only lost the overnight return (night leg Sharpe ~2 vs day leg ~-1.4 on the synthetic series).', 'D2': 'Opening-range breakout: train Sharpe 0.52 at best, no plateau.',
       'D3': 'Skipping entries in the first/last bars changed almost nothing; best cell is no skipping.', 'E1': 'Gap fade/follow lost money (train Sharpe -0.47, drawdown -27%).',
       'F1': 'Daily RSI(2) mean reversion in range regimes: only ~26 trades/yr, train Sharpe 0.08.', 'G1': 'Diagnostic only. Overnight-only has Sharpe 1.98 on the synthetic series but 252 trades/yr and -26% drawdown; real futures nights earn far less (report section 8).',
       'G1b': 'Diagnostic only. Day-leg-only loses money on the synthetic series.', 'H1': 'OI x price quadrants (prior-day data): train Sharpe 0.19.', 'H2': 'US overnight return as gap predictor: priced into the open, as expected (train Sharpe negative).'}
L = ['# Failure log (every idea gets a row the day it is tested; train = 2017-04..2021-12, baseline train Sharpe 1.15 / MaxDD -13.4%, validation baseline 0.73 / -7.7%)\n',
     '| ID | Date | Idea | Hypothesis (expected sign written before running) | Params tried | Train Sharpe / DD (chosen cell) | Validation Sharpe / DD | Verdict | Why it failed or passed |', '|---|---|---|---|---|---|---|---|---|']
n = 0
for idea, (fam, meth, grid, hyp, sign) in IDEAS.items():
    n += 1; v = tr[idea]; b = v['best']; cells = len(v['rows'])
    val = '-'
    if idea in first: val = f'look 1: {first[idea][0]:.2f} / {first[idea][1]:.1%}'
    if idea in va2: val += f'; look 2 ({va2[idea]["cell"]}): {va2[idea]["Sharpe"]:.2f} / {va2[idea]["MaxDD"]:.1%}'
    verdict = ('PASS validation (then FAILED the locked test)' if idea == 'B2h' else ('fail validation' if idea in first else ('diagnostic' if idea.startswith('G') else 'fail train')))
    L.append(f'| F-{n:03d} | 2026-11-03 | {idea} ({fam}) | {hyp} (expected {sign}) | {cells} cell(s): {json.dumps(grid)} | {b["Sharpe"]:.2f} / {b["MaxDD"]:.1%} at {json.dumps(b["cell"])} | {val} | {verdict} | {why[idea]} |')
for nm, m in p4['train_stages']:
    pass
L.append('\n## Risk-layer components (Phase 4, on the surviving signal B2h; each must raise train Sharpe by >= 0.02 AND improve MaxDD by >= 0.25 pt)\n')
L.append('| Component | Result on train | Kept? |\n|---|---|---|')
L.append(f"| stop + risk sizing k in {{2,2.5,3}} | k=2.0: Sharpe {p4['k_grid'][0]['Sharpe']:.2f}; k=2.5: {p4['k_grid'][1]['Sharpe']:.2f}; k=3.0: {p4['k_grid'][2]['Sharpe']:.2f} (centre k=2.5 chosen) | mandatory |")
L.append(f"| vol targeting 12/15/18% | best {p4['tv_best']:.0%}: Sharpe {[r for r in p4['tv_grid'] if r['tv']==p4['tv_best']][0]['Sharpe']:.2f} vs 1.68 without | {'yes' if p4['tv_kept'] else 'no'} |")
L.append(f"| overnight cap 8 lots | Sharpe collapsed to ~0.1 (the overnight leg carries the return) | {'yes' if p4['ov_kept'] else 'no'} |")
L.append(f"| drawdown brake (halve at -10%) | never triggered, no change | {'yes' if p4['dd_kept'] else 'no'} |")
L.append(f"| daily loss limit 1.5% | never triggered, no change | {'yes' if p4['dl_kept'] else 'no'} |")
L.append('\n## Final frozen strategy (B2h p=80 + k=2.5 stop sizing)\n\nTrain Sharpe 1.68 / -6.2%; validation 0.60 / -5.5% (baseline 0.73 / -7.7%); **locked test -0.09 / -8.7% vs baseline 0.46 / -6.6%: NO-GO.**')
open(f'{RES}/FAILURE_LOG.md', 'w').write('\n'.join(L)); print(len(L), 'lines')
