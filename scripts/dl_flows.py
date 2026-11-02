"""Download FII/DII monthly flows and Nifty P/E (HARI-KIRAN-REDDY/FIIDIIData) and the NSDL FPI monthly mirror (MrChartist/fii-dii-data)."""
import os, requests
root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
for sub, repo, files in [('fii2', 'HARI-KIRAN-REDDY/FIIDIIData', ['fii_dii.csv', 'nifty_pe_pb_div.csv']), ('fii', 'MrChartist/fii-dii-data', ['data/fpi_yearly_monthly.json', 'data/fpi_monthly_history.json', 'data/history.json'])]:
    os.makedirs(os.path.join(root, sub), exist_ok=True)
    for f in files:
        r = requests.get(f'https://raw.githubusercontent.com/{repo}/HEAD/{f}', timeout=60)
        open(os.path.join(root, sub, os.path.basename(f)), 'wb').write(r.content); print('saved', sub, os.path.basename(f))
