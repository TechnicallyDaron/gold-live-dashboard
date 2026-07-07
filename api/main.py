"""
api/main.py — N-CORE Quant API.

Two jobs, one always-on service:
  1. JSON endpoints for the mobile PWA (and anything else).
  2. The Telegram webhook: command-driven answers from your phone
     (/bias sofi, /levels gold, /status ...) — pure engine math,
     ZERO AI credits. The /ask AI tier is stubbed until funded.

Run locally:   uvicorn api.main:app --reload --port 8000
Railway start: uvicorn api.main:app --host 0.0.0.0 --port $PORT
"""
import os
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import requests
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

import quant_core as qc

app = FastAPI(title="N-CORE Quant API", version="1.0.0")

# NOTE: open CORS while the PWA is being built; tighten allow_origins to
# the PWA's domain before sharing the API URL anywhere public.
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")


# =====================================================================
# JSON API — the PWA's data contract
# =====================================================================
@app.get("/api/health")
def health():
    return {
        "status": "online",
        "time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "watchlist_assets": len(qc.load_watchlist()),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
    }


@app.get("/api/watchlist")
def watchlist():
    return qc.load_watchlist()


@app.get("/api/positions")
def positions():
    return qc.load_positions()


@app.get("/api/quote/{asset}")
def quote(asset: str):
    ticker, name, unit = qc.resolve_ticker(asset)
    q = qc.get_quote(ticker)
    if q is None:
        raise HTTPException(status_code=502, detail=f"Feed down for {ticker}")
    return {"asset": name, "ticker": ticker, "unit": unit, **q}


@app.get("/api/bias/{asset}")
def bias(asset: str):
    ticker, name, unit = qc.resolve_ticker(asset)
    try:
        b = qc.get_bias(ticker)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Feed down for {ticker}")
    b["asset"] = name
    b["ticker"] = ticker
    b["unit"] = unit
    return b


@app.get("/api/backtest/{asset}")
def backtest(asset: str, strategy: str = "meanrev"):
    if strategy not in qc.STRATEGIES:
        raise HTTPException(status_code=400,
                            detail=f"Unknown strategy. Options: {list(qc.STRATEGIES)}")
    ticker, name, _ = qc.resolve_ticker(asset)
    try:
        trades, stats = qc.run_backtest(ticker, strategy)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Feed down for {ticker}")
    return {
        "asset": name, "ticker": ticker,
        "strategy": strategy, "strategy_meta": qc.STRATEGIES[strategy],
        "viability": qc.viability(stats),
        "stats": stats,
        "trades": trades[-40:],
    }


@app.get("/api/macro")
def macro():
    return qc.macro_calendar()


@app.get("/api/news/{asset}")
def news(asset: str):
    ticker, _, _ = qc.resolve_ticker(asset)
    return qc.news_items(ticker)


PULSE_TICKERS = {"SPY": "SPY", "QQQ": "QQQ", "GLD": "GLD", "BTC": "BTC-USD",
                 "AAPL": "AAPL", "NVDA": "NVDA", "TSLA": "TSLA"}


@app.get("/api/tape")
def tape():
    """One call, whole marquee: quotes for the pulse instruments.
    Dead feeds return null for that symbol — render them honestly."""
    out = []
    for label, tk in PULSE_TICKERS.items():
        q = qc.get_quote(tk)
        out.append({"symbol": label, "ticker": tk, "quote": q})
    return out


@app.get("/api/history/{asset}")
def history(asset: str, days: int = 500):
    """Chart series: price + 20EMA baseline + ±2σ bands + 200EMA macro.
    Rows are chronological; NaN indicator rows are dropped."""
    days = max(30, min(days, 1300))
    ticker, name, unit = qc.resolve_ticker(asset)
    try:
        df = qc.fetch_history(ticker)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Feed down for {ticker}")
    valid = df.dropna(subset=["Baseline", "Upper_Band", "Lower_Band", "Macro_Filter"]).tail(days)
    rows = [{
        "date": idx.strftime("%Y-%m-%d"),
        "price": round(float(r.Price), 2),
        "baseline": round(float(r.Baseline), 2),
        "upper": round(float(r.Upper_Band), 2),
        "lower": round(float(r.Lower_Band), 2),
        "macro": round(float(r.Macro_Filter), 2),
    } for idx, r in zip(valid.index, valid.itertuples())]
    return {"asset": name, "ticker": ticker, "unit": unit, "rows": rows}


# =====================================================================
# TELEGRAM WEBHOOK — the command bot (Phase 4a: pure math, no AI spend)
# =====================================================================
def tg_send(chat_id, text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML",
                  "disable_web_page_preview": True},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def _fmt_bias(asset_query: str) -> str:
    ticker, name, unit = qc.resolve_ticker(asset_query)
    q = qc.get_quote(ticker)
    if q is None:
        return f"\u274C Feed down for {name} ({ticker}). Try again shortly."
    b = qc.get_bias(ticker)
    return (f"<b>{b['state']}</b> \u2014 {name}\n"
            f"Spot ${b['price']:,.2f}{unit} | Z {b['z']:+.2f}\u03C3 | {b['trend']}\n\n"
            f"\U0001F3AF Arm ${b['arm_level']:,.2f} ({b['dist_to_arm_pct']:+.2f}%)\n"
            f"\U0001F6D1 Invalidation ${b['invalidation']:,.2f}\n"
            f"\U0001F4CD Target (20 EMA) ${b['target']:,.2f} ({b['dist_to_target_pct']:+.2f}%)")


def _fmt_status() -> str:
    lines = ["\U0001F4CA <b>Terminal Status</b>"]
    for asset_name, d in qc.load_watchlist().items():
        try:
            b = qc.get_bias(d["ticker"])
            icon = b["state"].split(" ")[0]
            trend = "\u25B2" if "BULLISH" in b["trend"] else "\u25BC"
            lines.append(f"{icon} <b>{asset_name}</b> ${b['price']:,.2f} | "
                         f"Z {b['z']:+.2f} | {trend}")
        except Exception:
            lines.append(f"\u274C <b>{asset_name}</b> \u2014 feed down")
    return "\n".join(lines)


def _fmt_positions() -> str:
    pos = qc.load_positions()
    if not pos:
        return "\U0001F6E1 No positions on file."
    lines = ["\U0001F6E1 <b>Guarded Positions</b>"]
    for pid, p in pos.items():
        lines.append(
            f"\u2022 {p.get('asset','?')} ${p.get('strike','?')}"
            f"{str(p.get('type',''))[:1].upper()} exp {p.get('expiration','?')}\n"
            f"   stop ${p.get('premium_stop','?')} | time stop {p.get('time_stop','\u2014')} | "
            f"inval {p.get('invalidation_above') or p.get('invalidation_below') or '\u2014'}"
        )
    return "\n".join(lines)


HELP_TEXT = (
    "\u26A1 <b>N-CORE Command Bot</b>\n\n"
    "/status \u2014 every asset's state at a glance\n"
    "/bias &lt;asset&gt; \u2014 full readout + action levels\n"
    "/levels &lt;asset&gt; \u2014 same as /bias\n"
    "/backtest &lt;asset&gt; \u2014 strategy viability verdicts\n"
    "/positions \u2014 Guardian-watched positions\n"
    "/macro \u2014 upcoming high-impact releases\n"
    "/ask &lt;question&gt; \u2014 AI analysis (coming in Phase 4b)\n\n"
    "<i>Pure engine math. Statistical interpretation, not financial advice.</i>"
)


def _fmt_backtest(asset_query: str) -> str:
    ticker, name, _ = qc.resolve_ticker(asset_query)
    lines = [f"\U0001F4CA <b>Backtest Matrix \u2014 {name}</b> (5y, honest fills)"]
    for key, meta in qc.STRATEGIES.items():
        try:
            _, stats = qc.run_backtest(ticker, key)
            v = qc.viability(stats)
            pf = "\u221E" if v["profit_factor"] is None else f"{v['profit_factor']:.2f}"
            lines.append(f"{v['verdict']} <b>{meta['name']}</b>\n"
                         f"   PF {pf} | win {stats['all']['win_rate']*100:.0f}% | "
                         f"{stats['strategy_return']*100:+.1f}% | {stats['all']['n']} trades")
        except Exception:
            lines.append(f"\u274C {meta['name']} \u2014 feed down")
    return "\n".join(lines)


def _fmt_macro() -> str:
    events = [e for e in qc.macro_calendar() if e.get("upcoming")][:6]
    if not events:
        return "\U0001F6A8 No upcoming high-impact releases on the feed."
    lines = ["\U0001F6A8 <b>Upcoming High-Impact</b>"]
    for e in events:
        lines.append(f"\u2022 {e['time_et']} ET \u2014 {e['currency']} {e['event']} "
                     f"(F {e['forecast']})")
    return "\n".join(lines)


def route_command(text: str) -> str:
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower().split("@")[0] if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/start", "/help"):
        return HELP_TEXT
    if cmd == "/status":
        return _fmt_status()
    if cmd in ("/bias", "/levels"):
        return _fmt_bias(arg) if arg else "Usage: /bias sofi"
    if cmd == "/backtest":
        return _fmt_backtest(arg) if arg else "Usage: /backtest gold"
    if cmd == "/positions":
        return _fmt_positions()
    if cmd == "/macro":
        return _fmt_macro()
    if cmd == "/ask":
        return ("\U0001F916 AI analysis is Phase 4b \u2014 not yet funded by the operator. "
                "The math commands above are free: /status, /bias, /backtest.")
    return "Unknown command. /help for the list."


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=None),
):
    # Layer 1: shared-secret header set at webhook registration
    if TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="bad secret")

    update = await request.json()
    msg = update.get("message") or update.get("edited_message") or {}
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    text = (msg.get("text") or "").strip()

    # Layer 2: hard allowlist — strangers get silence, not errors
    if not chat_id or (TELEGRAM_CHAT_ID and chat_id != str(TELEGRAM_CHAT_ID)):
        return {"ok": True}
    if not text:
        return {"ok": True}

    reply = route_command(text)
    tg_send(chat_id, reply)
    return {"ok": True}
