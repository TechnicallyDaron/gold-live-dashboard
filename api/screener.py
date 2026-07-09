"""
N-CORE — Catalyst Screener. Runs ONCE daily after the close on COMPLETED
bars (no partial-day RVOL lies). Three-rule confluence, all must pass:
  1. RVOL: today's volume >= 2.0x trailing 30-day average volume
  2. Breakout: today's close > the max high of the prior 365 days
  3. Temporal lock: the FIRST such cross happened within the current
     calendar week (Mon..today) — fresh breakouts only, no stale leaders.
Universe: curated liquid large-caps in universe.json (editable).
"""
import json
import os
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

RVOL_MIN = float(os.getenv("SCREENER_RVOL_MIN", "2.0"))


def load_universe() -> list:
    try:
        with open("universe.json") as f:
            return json.load(f)["tickers"]
    except Exception:
        return []


CHUNK = int(os.getenv("SCREENER_CHUNK", "40"))


def _download_universe(tickers: list) -> dict:
    """Seam. CHUNKED daily download (~14 months) so memory stays flat on a
    small container — a single 298-ticker megabatch OOM-kills Railway."""
    out = {}
    for i in range(0, len(tickers), CHUNK):
        batch = tickers[i:i + CHUNK]
        try:
            raw = yf.download(batch, period="14mo", interval="1d",
                              group_by="ticker", auto_adjust=False,
                              progress=False, threads=True)
        except Exception:
            continue
        for t in batch:
            try:
                df = raw[t].dropna(subset=["Close"])
                if len(df) >= 260:
                    out[t] = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            except Exception:
                continue
        del raw
    return out


def _week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def evaluate(df: pd.DataFrame) -> dict | None:
    """Apply the three rules to one asset's completed daily bars."""
    if len(df) < 260:
        return None
    today = df.index[-1].date()
    close = float(df["Close"].iloc[-1])
    vol = float(df["Volume"].iloc[-1])
    avg30 = float(df["Volume"].iloc[-31:-1].mean())
    if not avg30 or vol < RVOL_MIN * avg30:
        return None                                   # Rule 1

    prior_high_now = float(df["High"].iloc[:-1].tail(365).max())
    if close <= prior_high_now:
        return None                                   # Rule 2

    # Rule 3: find the FIRST day the close crossed above its own trailing
    # 365d prior high; must fall inside the current calendar week.
    monday = _week_monday(today)
    breakout_date = None
    week_mask = [i for i in range(len(df)) if df.index[i].date() >= monday]
    for i in week_mask:
        if i < 260:
            continue
        c = float(df["Close"].iloc[i])
        ph = float(df["High"].iloc[:i].tail(365).max())
        prev_c = float(df["Close"].iloc[i - 1])
        prev_ph = float(df["High"].iloc[:i - 1].tail(365).max())
        if c > ph and prev_c <= prev_ph:
            breakout_date = df.index[i].date().isoformat()
            break
    if breakout_date is None:
        return None
    return {"price": round(close, 2), "rvol": round(vol / avg30, 2),
            "breakout_date": breakout_date}


def run_screener() -> list:
    tickers = load_universe()
    data = _download_universe(tickers)
    hits = []
    for t, df in data.items():
        try:
            r = evaluate(df)
        except Exception:
            continue
        if r:
            hits.append({"ticker": t, **r})
    hits.sort(key=lambda h: h["rvol"], reverse=True)
    return hits
