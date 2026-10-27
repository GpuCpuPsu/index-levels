"""Daily OHLCV from Yahoo Finance (yfinance), split/dividend adjusted, cached on disk.

Indexes use Yahoo's caret symbols: ^GSPC is the S&P 500 index (SPX).
"""
import json
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE = Path(__file__).resolve().parent.parent / "cache"
FIELDS = ["Open", "High", "Low", "Close", "Volume"]


def load(ticker, start, end):
    """DataFrame[Open, High, Low, Close, Volume] indexed by int YYYYMMDD; cached per ticker."""
    CACHE.mkdir(exist_ok=True)
    start, end = pd.Timestamp(start).strftime("%Y-%m-%d"), pd.Timestamp(end).strftime("%Y-%m-%d")
    path, meta_path = CACHE / f"{ticker}.csv", CACHE / "_ranges.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if not path.exists() or ticker not in meta or meta[ticker][0] > start or meta[ticker][1] < end:
        raw = yf.download(ticker, start=start, end=(pd.Timestamp(end) + pd.Timedelta(days=1)),
                          auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw[FIELDS].dropna(how="all")
        if raw.empty:
            raise SystemExit(f"no Yahoo data for {ticker}")
        raw.to_csv(path)
        meta[ticker] = [start, end]
        meta_path.write_text(json.dumps(meta, indent=1))
    f = pd.read_csv(path, index_col=0, parse_dates=True)
    f = f.loc[(f.index >= start) & (f.index <= end)]
    f.index = f.index.strftime("%Y%m%d").astype(int)
    return f
