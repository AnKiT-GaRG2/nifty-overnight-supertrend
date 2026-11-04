"""Download sector indices, Asian/European indices and Nifty heavyweights (Yahoo, close prices) to data/xmkt2/all_close.csv. Run: <venv>/bin/python scripts/dl_xmkt2.py"""
import os, yfinance as yf, pandas as pd
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = ['^CNXIT', '^CNXFMCG', '^CNXAUTO', '^CNXPHARMA', '^CNXMETAL', '^CNXREALTY', '^CNXFIN', '^CNXENERGY', '^CNXPSUBANK', '^CNXINFRA', '^N225', '^HSI', '^KS11', '^AXJO', '^FTSE', '^GDAXI', 'HDFCBANK.NS', 'RELIANCE.NS', 'ICICIBANK.NS', 'INFY.NS', 'TCS.NS']
d = yf.download(T, start='2016-06-01', end='2026-11-04', progress=False, auto_adjust=True)['Close']; d.index.name = 'date'
d.to_csv(f'{R}/data/xmkt2/all_close.csv'); print(d.notna().sum().to_string())
