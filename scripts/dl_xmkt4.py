"""Download India sector indices and India ETFs (Yahoo daily closes) to data/xmkt4/all_close.csv. Run: <venv>/bin/python scripts/dl_xmkt4.py"""
import os, yfinance as yf, pandas as pd
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = ['^NSEBANK', '^CNXIT', '^CNXFMCG', '^CNXPHARMA', '^CNXMETAL', '^CNXAUTO', '^CNXREALTY', '^CNXENERGY', '^CNXPSUBANK', '^CNXINFRA', '^CNXPSE', '^CNXMNC', 'INDA', 'EPI']
d = yf.download(T, start='2016-06-01', end='2026-11-04', progress=False, auto_adjust=True)['Close']; d.index.name = 'date'
os.makedirs(f'{R}/data/xmkt4', exist_ok=True); d.to_csv(f'{R}/data/xmkt4/all_close.csv'); print(d.notna().sum().to_string())
