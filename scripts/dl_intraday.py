"""Download the 1-minute Nifty spot CSVs from github.com/technovusin/nifty50-historical-data into data/intraday/."""
import os, sys, requests
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'intraday'); os.makedirs(out, exist_ok=True)
tree = requests.get('https://api.github.com/repos/technovusin/nifty50-historical-data/git/trees/HEAD?recursive=1', timeout=30).json()['tree']
for x in tree:
    p = x['path']
    if p.startswith('1min/') and p.endswith('.csv'):
        dest = os.path.join(out, os.path.basename(p))
        r = requests.get('https://raw.githubusercontent.com/technovusin/nifty50-historical-data/HEAD/' + p, timeout=120)
        open(dest, 'wb').write(r.content); print('saved', dest, len(r.content))
