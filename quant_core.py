"""
quant_core.py — The pure quant engine. NO Streamlit imports.

This is the single brain shared by every face of the terminal:
  - api/main.py (FastAPI service: the PWA's backend + Telegram webhook)
  - eventually app.py (the Streamlit desktop terminal)
  - monitor.py already shares signal_engine with this module

Caching is a simple thread-safe TTL store (replaces st.cache_data).
Network seams (_download_history / _download_quote) are isolated so
tests can monkeypatch them.
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from signal_engine import add_indicators, compute_bias, STOP_LOSS_PCT

# ── TTL cache ────────────────────────────────────────────────
_cache = {}
_lock = threading.Lock()


def _cached(key, ttl, fn):
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    val = fn()
    with _lock:
        _cache[key] = (now, val)
    return val


# ── Files (repo root = service working dir) ─────────────────
DEFAULT_WATCHLIST = {
    "Gold": {"ticker": "GC=F", "name": "Gold Market", "unit": "/oz"},
    "S&P 500": {"ticker": "^GSPC", "name": "S&P 500 Index", "unit": ""},
    "SOFI": {"ticker": "SOFI", "name": "SoFi Technologies", "unit": "/sh"},
}


def load_watchlist():
    try:
        with open("watchlist.json") as f:
            wl = json.load(f)
        if isinstance(wl, dict) and wl:
            return wl
    except Exception:
        pass
    return dict(DEFAULT_WATCHLIST)


def load_positions():
    try:
        with open("positions.json") as f:
            return json.load(f)
    except Exception:
        return {}


def resolve_ticker(asset: str):
    """Accept a watchlist display name (case-insensitive) or a raw ticker.
    Returns (ticker, display_name, unit)."""
    wl = load_watchlist()
    for name, d in wl.items():
        if name.lower() == asset.lower():
            return d["ticker"], d.get("name", name), d.get("unit", "")
    return asset.upper(), asset.upper(), ""


# ── Network seams (monkeypatchable) ──────────────────────────
def _download_history(ticker: str) -> pd.DataFrame:
    end = datetime.today()
    start = end - timedelta(days=1825)
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].astype(float).copy()
    return df.rename(columns={"Close": "Price"})


def _download_quote(ticker: str):
    try:
        df = yf.download(ticker, period="1mo", auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        closes = df["Close"].dropna().astype(float)
        if len(closes) >= 2:
            c, p = float(closes.iloc[-1]), float(closes.iloc[-2])
            return c, c - p, ((c - p) / p) * 100
    except Exception:
        pass
    try:
        fi = yf.Ticker(ticker).fast_info
        c = float(fi["last_price"])
        p = float(fi["previous_close"])
        return c, c - p, ((c - p) / p) * 100
    except Exception:
        return None


def _download_option_premium(ticker: str, expiration: str, strike: float, opt_type: str):
    t = yf.Ticker(ticker)
    ch = t.option_chain(expiration)
    tbl = ch.puts if opt_type.lower() == "put" else ch.calls
    row = tbl[tbl["strike"] == float(strike)]
    if len(row):
        px = row["lastPrice"].iloc[0]
        return float(px) if px and px > 0 else None
    return None


def get_option_premium(ticker: str, expiration: str, strike: float, opt_type: str):
    """Live contract premium from the option chain. None = unavailable —
    callers must show PNL UNAVAILABLE, never derive PnL from spot."""
    key = f"opt:{ticker}:{expiration}:{strike}:{opt_type}"
    try:
        return _cached(key, 120, lambda: _download_option_premium(ticker, expiration, strike, opt_type))
    except Exception:
        return None


def _download_next_earnings(ticker: str):
    from datetime import date as _d
    t = yf.Ticker(ticker)
    try:
        ed = t.earnings_dates
        upcoming = [d for d in ed.index if d.date() >= _d.today()]
        if upcoming:
            return min(upcoming).date().isoformat()
    except Exception:
        pass
    try:
        cal = t.calendar
        dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if dates:
            return min(dates).isoformat()
    except Exception:
        pass
    return None


def _download_ticker_name(ticker: str):
    try:
        info = yf.Ticker(ticker).info
        return info.get("shortName") or info.get("longName")
    except Exception:
        return None


def get_ticker_name(ticker: str):
    """Company/asset display name, cached 12h. Falls back to the ticker."""
    try:
        n = _cached(f"tname:{ticker}", 43200, lambda: _download_ticker_name(ticker))
        return n or ticker.upper()
    except Exception:
        return ticker.upper()


def get_next_earnings(ticker: str):
    """Next earnings date as ISO string, or None. Cached 12h; never raises."""
    try:
        return _cached(f"earn:{ticker}", 43200, lambda: _download_next_earnings(ticker))
    except Exception:
        return None


# ── Public engine surface ────────────────────────────────────
def get_quote(ticker: str):
    """{price, change, pct} or None. Never fabricates $0.00."""
    q = _cached(f"q:{ticker}", 120, lambda: _download_quote(ticker))
    if q is None:
        return None
    price, change, pct = q
    return {"price": round(price, 2), "change": round(change, 2), "pct": round(pct, 2)}


def fetch_history(ticker: str) -> pd.DataFrame:
    return _cached(f"h:{ticker}", 60, lambda: add_indicators(_download_history(ticker)))


def get_bias(ticker: str) -> dict:
    return compute_bias(fetch_history(ticker))


STRATEGIES = {
    "meanrev": {"name": "Mean Reversion",
                "desc": "Band touch WITH the 200 EMA trend \u2192 revert to the 20 EMA"},
    "breakout": {"name": "Momentum Breakout",
                 "desc": "Band break WITH the 200 EMA trend \u2192 ride until the 20 EMA gives up"},
    "rsi": {"name": "RSI Reversion",
            "desc": "RSI(14) below 30 / above 70 with the trend filter \u2192 exit at RSI 50"},
    "pullback": {"name": "Trend Pullback",
                 "desc": "Shallow dip (\u22120.75\u03C3) WITH the 200 EMA trend \u2192 exit at +0.5\u03C3. Built for weekly-cadence signals."},
    "ema920": {"name": "RSI & 9/20 Confluence",
               "desc": "RSI stretch (\u226435 or \u226565) resolved by the 9 EMA crossing the 20 EMA on a confirmed close \u2192 ride until the cross reverses"},
    "breakout52": {"name": "Catalyst Momentum",
                   "desc": "Fresh 52-week-high breakout on elevated volume \u2192 ride the post-breakout drift, exit on trend loss"},
    "gapfade": {"name": "Gap Reversal",
                "desc": "Hard gap against the prevailing trend that closes strong \u2192 enter the recovery back to the mean"},
    "trend": {"name": "Trend Rider",
              "desc": "Price reclaims the 20 EMA with the macro trend, not overextended \u2192 ride until the trend breaks"},
    "rsi2": {"name": "Fast RSI(2)",
             "desc": "RSI(2) washout (<10 / >90) with the trend filter \u2192 exit at 65/35. High-frequency reversion."},
}


def run_backtest(ticker: str, strategy: str = "meanrev"):
    """Cached full-history run. For walk-forward segments, call
    _run_backtest with an explicit df slice."""
    """Honest execution: signals on close \u2192 fills next open, intraday
    stops with gap handling, compounded equity. Returns (trades, stats)."""
    return _cached(f"bt:{ticker}:{strategy}", 300, lambda: _run_backtest(ticker, strategy))


def _run_backtest(ticker: str, strategy: str, df=None):
    if df is None:
        df = fetch_history(ticker)
    valid = df.dropna(subset=["Upper_Band", "Lower_Band", "Baseline", "Macro_Filter"]).copy()

    delta = valid["Price"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    valid["RSI"] = 100 - 100 / (1 + rs)
    g2 = delta.clip(lower=0).ewm(alpha=1 / 2, adjust=False).mean()
    l2 = (-delta.clip(upper=0)).ewm(alpha=1 / 2, adjust=False).mean()
    valid["RSI2"] = 100 - 100 / (1 + g2 / l2.replace(0, np.nan))
    sigma = (valid["Upper_Band"] - valid["Baseline"]) / 2.0
    valid["Z"] = (valid["Price"] - valid["Baseline"]) / sigma.replace(0, np.nan)
    valid["EMA9"] = valid["Price"].ewm(span=9, adjust=False).mean()
    valid["PrevEMA9"] = valid["EMA9"].shift(1)
    valid["RSI_MINW"] = valid["RSI"].rolling(10, min_periods=1).min()
    valid["RSI_MAXW"] = valid["RSI"].rolling(10, min_periods=1).max()
    valid["P252H"] = valid["High"].shift(1).rolling(252, min_periods=200).max()
    valid["P252L"] = valid["Low"].shift(1).rolling(252, min_periods=200).min()
    valid["PrevClose"] = valid["Price"].shift(1)
    valid["PrevBaseline"] = valid["Baseline"].shift(1)
    if "Volume" in valid.columns:
        valid["VolR"] = valid["Volume"] / valid["Volume"].rolling(30).mean()
    else:
        valid["VolR"] = np.nan   # volume condition waived when feed lacks it

    equity, equity_marks = 1.0, [1.0]
    position, entry_price, entry_date = 0, 0.0, None
    pending_entry, pending_exit_label = 0, None
    trades = []

    def close_trade(exit_price, exit_date, label):
        nonlocal equity, position, entry_price, entry_date, pending_exit_label
        r = ((exit_price - entry_price) / entry_price if position == 1
             else (entry_price - exit_price) / entry_price)
        equity *= (1 + r)
        equity_marks.append(equity)
        trades.append({
            "type": label,
            "direction": "long" if position == 1 else "short",
            "entry_date": entry_date.strftime("%Y-%m-%d"),
            "exit_date": exit_date.strftime("%Y-%m-%d"),
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "return_pct": round(r * 100, 2),
        })
        position, entry_price, entry_date, pending_exit_label = 0, 0.0, None, None

    for bar in valid.itertuples():
        open_, high, low, close = float(bar.Open), float(bar.High), float(bar.Low), float(bar.Price)
        baseline_v, upper_v = float(bar.Baseline), float(bar.Upper_Band)
        lower_v, macro_v = float(bar.Lower_Band), float(bar.Macro_Filter)
        rsi_v = None if pd.isna(bar.RSI) else float(bar.RSI)
        p252h = None if pd.isna(bar.P252H) else float(bar.P252H)
        p252l = None if pd.isna(bar.P252L) else float(bar.P252L)
        prev_c = None if pd.isna(bar.PrevClose) else float(bar.PrevClose)
        prev_b = None if pd.isna(bar.PrevBaseline) else float(bar.PrevBaseline)
        volr_ok = pd.isna(bar.VolR) or float(bar.VolR) >= 1.5
        ema9 = None if pd.isna(bar.EMA9) else float(bar.EMA9)
        prev9 = None if pd.isna(bar.PrevEMA9) else float(bar.PrevEMA9)
        rsi_min5 = None if pd.isna(bar.RSI_MINW) else float(bar.RSI_MINW)
        rsi_max5 = None if pd.isna(bar.RSI_MAXW) else float(bar.RSI_MAXW)
        rsi2_v = None if pd.isna(bar.RSI2) else float(bar.RSI2)
        z_v = None if pd.isna(bar.Z) else float(bar.Z)

        if position == 0 and pending_entry != 0:
            position, entry_price, entry_date, pending_entry = pending_entry, open_, bar.Index, 0
        elif position != 0 and pending_exit_label is not None:
            close_trade(open_, bar.Index, pending_exit_label)

        if position == 1:
            stop = entry_price * (1 - STOP_LOSS_PCT)
            if low <= stop:
                close_trade(min(open_, stop), bar.Index, "Long (Stop Loss Hit)")
        elif position == -1:
            stop = entry_price * (1 + STOP_LOSS_PCT)
            if high >= stop:
                close_trade(max(open_, stop), bar.Index, "Short (Stop Loss Hit)")

        if position == 1:
            if (strategy == "meanrev" and close >= baseline_v) or \
               (strategy == "breakout" and close < baseline_v) or \
               (strategy == "rsi" and rsi_v is not None and rsi_v >= 50) or \
               (strategy == "pullback" and z_v is not None and z_v >= 0.5) or \
               (strategy == "rsi2" and rsi2_v is not None and rsi2_v >= 65) or \
               (strategy == "breakout52" and close < baseline_v) or \
               (strategy == "gapfade" and z_v is not None and z_v >= 0.0) or \
               (strategy == "trend" and close < baseline_v) or \
               (strategy == "ema920" and ema9 is not None and prev9 is not None
                and prev_b is not None and prev9 >= prev_b and ema9 < baseline_v):
                pending_exit_label = "Long Exit (Signal)"
        elif position == -1:
            if (strategy == "meanrev" and close <= baseline_v) or \
               (strategy == "breakout" and close > baseline_v) or \
               (strategy == "rsi" and rsi_v is not None and rsi_v <= 50) or \
               (strategy == "pullback" and z_v is not None and z_v <= -0.5) or \
               (strategy == "rsi2" and rsi2_v is not None and rsi2_v <= 35) or \
               (strategy == "breakout52" and close > baseline_v) or \
               (strategy == "gapfade" and z_v is not None and z_v <= 0.0) or \
               (strategy == "trend" and close > baseline_v) or \
               (strategy == "ema920" and ema9 is not None and prev9 is not None
                and prev_b is not None and prev9 <= prev_b and ema9 > baseline_v):
                pending_exit_label = "Short Exit (Signal)"

        if position == 0 and pending_entry == 0:
            if strategy == "meanrev":
                if close < lower_v and close > macro_v:
                    pending_entry = 1
                elif close > upper_v and close < macro_v:
                    pending_entry = -1
            elif strategy == "breakout":
                if close > upper_v and close > macro_v:
                    pending_entry = 1
                elif close < lower_v and close < macro_v:
                    pending_entry = -1
            elif strategy == "rsi" and rsi_v is not None:
                if rsi_v < 30 and close > macro_v:
                    pending_entry = 1
                elif rsi_v > 70 and close < macro_v:
                    pending_entry = -1
            elif strategy == "pullback" and z_v is not None:
                if z_v <= -0.75 and close > macro_v:
                    pending_entry = 1
                elif z_v >= 0.75 and close < macro_v:
                    pending_entry = -1
            elif strategy == "rsi2" and rsi2_v is not None:
                if rsi2_v < 10 and close > macro_v:
                    pending_entry = 1
                elif rsi2_v > 90 and close < macro_v:
                    pending_entry = -1
            elif strategy == "breakout52":
                if p252h is not None and close > p252h and close > macro_v and volr_ok:
                    pending_entry = 1
                elif p252l is not None and close < p252l and close < macro_v and volr_ok:
                    pending_entry = -1
            elif strategy == "gapfade" and prev_c is not None:
                if open_ <= prev_c * 0.985 and close > open_ and close > macro_v:
                    pending_entry = 1
                elif open_ >= prev_c * 1.015 and close < open_ and close < macro_v:
                    pending_entry = -1
            elif strategy == "ema920" and None not in (ema9, prev9, prev_b, rsi_min5, rsi_max5):
                if prev9 <= prev_b and ema9 > baseline_v and rsi_min5 <= 35:
                    pending_entry = 1        # oversold stretch resolved by the 9/20 cross up
                elif prev9 >= prev_b and ema9 < baseline_v and rsi_max5 >= 65:
                    pending_entry = -1       # overbought stretch resolved by the cross down
            elif strategy == "trend" and prev_c is not None and prev_b is not None and z_v is not None:
                if prev_c <= prev_b and close > baseline_v and close > macro_v and z_v <= 1.0:
                    pending_entry = 1
                elif prev_c >= prev_b and close < baseline_v and close < macro_v and z_v >= -1.0:
                    pending_entry = -1

    def stat_block(subset):
        rets = [t["return_pct"] / 100 for t in subset]
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r <= 0]
        return {
            "n": len(rets),
            "win_rate": round((len(wins) / len(rets)) if rets else 0.0, 4),
            "avg_win": round(float(np.mean(wins)) if wins else 0.0, 4),
            "avg_loss": round(float(np.mean(losses)) if losses else 0.0, 4),
        }

    eq = np.array(equity_marks)
    dd = (eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)
    first, last = float(valid["Price"].iloc[0]), float(valid["Price"].iloc[-1])
    stats = {
        "strategy_return": round(equity - 1.0, 4),
        "buy_hold_return": round((last - first) / first, 4),
        "max_drawdown": round(float(dd.min()) if len(eq) > 1 else 0.0, 4),
        "all": stat_block(trades),
        "long": stat_block([t for t in trades if t["direction"] == "long"]),
        "short": stat_block([t for t in trades if t["direction"] == "short"]),
    }
    return trades, stats


def viability(stats: dict):
    s = stats["all"]
    n, wr, aw, al = s["n"], s["win_rate"], s["avg_win"], s["avg_loss"]
    expectancy = wr * aw + (1 - wr) * al
    gross_win, gross_loss = wr * aw, abs((1 - wr) * al)
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    if n < 15:
        verdict, cls = "\u26A0\uFE0F INSUFFICIENT SAMPLE", "mid"
    elif pf >= 1.3 and expectancy > 0:
        verdict, cls = "\u2705 VIABLE EDGE", "good"
    elif pf >= 0.9:
        verdict, cls = "\U0001F7E1 COIN-FLIP \u2014 NO EDGE", "mid"
    else:
        verdict, cls = "\u274C NOT VIABLE", "bad"
    return {"verdict": verdict, "class": cls,
            "profit_factor": None if pf == float("inf") else round(pf, 2),
            "expectancy_pct": round(expectancy * 100, 2)}


def macro_calendar():
    return _cached("macro", 1800, _fetch_macro)


def _fetch_macro():
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except Exception:
        et = None
    events = []
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code == 200:
            now = datetime.now().astimezone()
            for e in r.json():
                if str(e.get("impact", "")).lower() != "high":
                    continue
                try:
                    dt = datetime.fromisoformat(e.get("date", ""))
                except Exception:
                    dt = None
                upcoming = bool(dt and dt >= now)
                events.append({
                    "time_et": dt.astimezone(et).strftime("%a %I:%M %p") if (dt and et) else "\u2014",
                    "currency": e.get("country", "?"),
                    "event": e.get("title", "?"),
                    "forecast": e.get("forecast") or "N/A",
                    "previous": e.get("previous") or "N/A",
                    "upcoming": upcoming,
                    "_ts": dt.timestamp() if dt else 9e12,
                })
            events.sort(key=lambda x: (not x["upcoming"], x["_ts"]))
            for ev in events:
                ev.pop("_ts", None)
    except Exception:
        pass
    return events


def news_items(ticker: str):
    return _cached(f"news:{ticker}", 1800, lambda: _fetch_news(ticker))


def _fetch_news(ticker: str):
    from bs4 import BeautifulSoup
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "lxml-xml")
        items = []
        for it in soup.find_all("item")[:8]:
            title = it.title.get_text(strip=True) if it.title else ""
            if len(title) < 20:
                continue
            items.append({
                "title": title,
                "link": it.link.get_text(strip=True) if it.link else "",
                "published": it.pubDate.get_text(strip=True) if it.pubDate else "",
            })
        return items
    except Exception:
        return []
