"""Download US vol-structure, cross-asset and India small-cap series (Yahoo daily closes) to data/xmkt3/all_close.csv. Run: <venv>/bin/python scripts/dl_xmkt3.py"""
import os, yfinance as yf, pandas as pd
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = ['^VIX9D', '^VIX3M', '^VVIX', '^SKEW', '^MOVE', '^OVX', 'BTC-USD', '^SOX', '^IRX', '^FVX', '^TNX', 'TLT', 'SI=F', 'XLU', 'XLP', 'SPY', 'UUP', 'FXI', '^CNXSC', '^NSMIDCP', '^NSEI', 'KWEB', 'COPX']
d = yf.download(T, start='2016-06-01', end='2026-11-04', progress=False, auto_adjust=True)['Close']; d.index.name = 'date'
d.to_csv(f'{R}/data/xmkt3/all_close.csv'); print(d.notna().sum().to_string())
