"""
N-CORE Feed Adapter — Massive (Polygon.io) provider.

Every market-data download in the system flows through seams. This module
can re-point those seams at the Massive/Polygon REST API. Design rules:

  1. yfinance stays the DEFAULT. Nothing changes until the operator sets
     DATA_PROVIDER=polygon (plus POLYGON_API_KEY) on the api service.
  2. Options premiums and earnings dates STAY on yfinance for now — the
     stocks plan carries no options data; that migration is Phase 15.
  3. /api/feedcheck compares the two providers bar-for-bar before cutover.
     Trust is earned, even by data vendors.
"""
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

BASE = os.getenv("POLYGON_BASE", "https://api.polygon.io")


def _key() -> str:
    return os.getenv("POLYGON_API_KEY", "")


def _get(path: str, params: dict | None = None) -> dict:
    p = {"apiKey": _key()}
    if params:
        p.update(params)
    r = requests.get(f"{BASE}{path}", params=p, timeout=15)
    r.raise_for_status()
    return r.json()


def _aggs(ticker: str, days: int) -> pd.DataFrame:
    """Daily aggregates → engine-shaped frame (Open/High/Low/Price[/Volume])."""
    end = datetime.today()
    start = end - timedelta(days=days)
    j = _get(f"/v2/aggs/ticker/{ticker.upper()}/range/1/day/"
             f"{start:%Y-%m-%d}/{end:%Y-%m-%d}",
             {"adjusted": "true", "sort": "asc", "limit": 50000})
    rows = j.get("results") or []
    if not rows:
        raise RuntimeError(f"polygon: no bars for {ticker}")
    idx = pd.to_datetime([r["t"] for r in rows], unit="ms").normalize()
    df = pd.DataFrame({"Open": [r["o"] for r in rows],
                       "High": [r["h"] for r in rows],
                       "Low": [r["l"] for r in rows],
                       "Price": [r["c"] for r in rows],
                       "Volume": [r.get("v") for r in rows]},
                      index=idx).astype(float)
    return df


def polygon_history(ticker: str) -> pd.DataFrame:
    """Drop-in for qc._download_history (5y daily, Close→Price)."""
    return _aggs(ticker, 1825)[["Open", "High", "Low", "Price"]]


def polygon_quote(ticker: str):
    """Drop-in for qc._download_quote → (price, change, pct).
    Snapshot first (15-min delayed on Starter); falls back to the last
    two daily bars if the snapshot endpoint is unavailable."""
    try:
        j = _get(f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}")
        t = j.get("ticker") or {}
        price = (t.get("lastTrade") or {}).get("p") or (t.get("day") or {}).get("c")
        prev = (t.get("prevDay") or {}).get("c")
        if price and prev:
            price, prev = float(price), float(prev)
            return price, price - prev, (price - prev) / prev * 100
    except Exception:
        pass
    df = _aggs(ticker, 40)
    closes = df["Price"].dropna()
    if len(closes) >= 2:
        c, p = float(closes.iloc[-1]), float(closes.iloc[-2])
        return c, c - p, (c - p) / p * 100
    return None


def polygon_ticker_name(ticker: str):
    """Drop-in for qc._download_ticker_name."""
    try:
        j = _get(f"/v3/reference/tickers/{ticker.upper()}")
        return (j.get("results") or {}).get("name")
    except Exception:
        return None


def polygon_universe_hist(batch: list) -> dict:
    """Drop-in for analytics._download_universe_hist (5y, engine columns).
    Sequential per-ticker — the Starter plan has no rate limit, and one
    ticker per request keeps memory flat on the container."""
    out = {}
    for t in batch:
        try:
            df = _aggs(t, 1825)
            if len(df) >= 750:
                out[t] = df
        except Exception:
            continue
        time.sleep(0.05)
    return out


def polygon_universe_recent(tickers: list) -> dict:
    """Drop-in for screener._download_universe (~14 months, yf-style
    columns: Close/High/Low/Open/Volume — the screener reads Close)."""
    out = {}
    for t in tickers:
        try:
            df = _aggs(t, 430)
            out[t] = df.rename(columns={"Price": "Close"})
        except Exception:
            continue
        time.sleep(0.05)
    return out


def feed_check(tickers: list) -> dict:
    """Bar-for-bar comparison: yfinance vs polygon over the last ~30
    closes. Cutover confidence, quantified."""
    import quant_core as qc
    report, worst = [], 0.0
    for t in tickers:
        try:
            yf_df = qc._yf_download_history(t) if hasattr(qc, "_yf_download_history") \
                else None
            if yf_df is None:
                import yfinance as yf
                end = datetime.today()
                raw = yf.download(t, start=end - timedelta(days=90), end=end,
                                  auto_adjust=True, progress=False)
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)
                yf_df = raw.rename(columns={"Close": "Price"})
            pg_df = _aggs(t, 90)
            a = yf_df["Price"].dropna().tail(30)
            b = pg_df["Price"].dropna().tail(30)
            a.index = a.index.normalize()
            joined = pd.concat([a, b["Price"] if isinstance(b, pd.DataFrame) else b],
                               axis=1, join="inner")
            joined.columns = ["yf", "pg"]
            if not len(joined):
                report.append({"ticker": t, "bars_compared": 0,
                               "max_diff_pct": None, "verdict": "NO OVERLAP"})
                continue
            diff = ((joined["yf"] - joined["pg"]).abs() / joined["pg"] * 100)
            mx = round(float(diff.max()), 3)
            worst = max(worst, mx)
            report.append({"ticker": t, "bars_compared": int(len(joined)),
                           "max_diff_pct": mx,
                           "verdict": "MATCH" if mx < 0.5 else "DIVERGENT"})
        except Exception as e:
            report.append({"ticker": t, "error": str(e)[:120]})
    return {"provider_base": BASE, "worst_diff_pct": worst,
            "cutover_safe": worst < 0.5 and all("error" not in r for r in report),
            "detail": report}


def install() -> str:
    """Re-point the seams if the operator has flipped the switch.
    Returns the active provider name for the startup log."""
    if os.getenv("DATA_PROVIDER", "yfinance").lower() != "polygon" or not _key():
        return "yfinance"
    import quant_core as qc
    from api import analytics, screener
    qc._download_history = polygon_history
    qc._download_quote = polygon_quote
    qc._download_ticker_name = polygon_ticker_name
    analytics._download_universe_hist = polygon_universe_hist
    screener._download_universe = lambda tickers: polygon_universe_recent(tickers)
    return "polygon (Massive)"
