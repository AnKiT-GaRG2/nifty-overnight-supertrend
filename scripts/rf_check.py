import sys, os; sys.path.insert(0, 'scripts')
from rf import *
import time; t = time.time(); R = RF(); P = periods(R.days); print('built in', round(time.time() - t, 1), 's; days', R.n, '| nonzero rd', int((R.rd != 0).sum()), 'rn', int((R.rn != 0).sum()))
one = np.ones(R.n)
for nm, mode in [('buy&hold (both legs)', 'both'), ('night only always', 'night'), ('day only always', 'day')]:
    for itr in (False, True):
        r = R.run(one, mode, itr); print(f'{nm:24s} interest={itr!s:5s}', ' | '.join(f'{k} {met(r,*P[k],R.days)["CAGR"]:5.1f}/{met(r,*P[k],R.days)["DD"]:6.1f}' for k in P))
print('premium (next contract vs spot) mean %.3f%%; avg dte %.0f; OI nan share %.2f' % (np.nanmean(R.basis) * 100, np.nanmean(R.dte), np.isnan(R.oi).mean()))
