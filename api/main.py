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
from api import ai
from api import analytics
from pydantic import BaseModel
import asyncio
from datetime import date

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


class AskBody(BaseModel):
    asset: str
    question: str


@app.post("/api/ask")
def api_ask(body: AskBody):
    try:
        return {"answer": ai.ask(body.asset, body.question),
                "usage": ai.usage_today()}
    except ai.AIUnavailable:
        raise HTTPException(status_code=503, detail="AI not configured — set ANTHROPIC_API_KEY on this service.")
    except ai.AIBudgetExceeded:
        raise HTTPException(status_code=429, detail=f"Daily AI budget reached ({ai.DAILY_LIMIT} calls). Resets at midnight UTC.")


@app.get("/api/sentiment/{asset}")
def api_sentiment(asset: str):
    try:
        return ai.sentiment(asset)
    except ai.AIUnavailable:
        raise HTTPException(status_code=503, detail="AI not configured — set ANTHROPIC_API_KEY on this service.")
    except ai.AIBudgetExceeded:
        raise HTTPException(status_code=429, detail=f"Daily AI budget reached ({ai.DAILY_LIMIT} calls). Resets at midnight UTC.")


@app.get("/api/optimized-edge/{asset}")
def optimized_edge(asset: str):
    try:
        return analytics.optimized_edge(asset)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Feed down for {asset}")


@app.get("/api/macro-radar")
def macro_radar(window_hours: float = 3.0):
    return analytics.macro_radar(window_hours)


class ValidateBody(BaseModel):
    asset: str
    entry: float
    side: str | None = None


@app.post("/api/validate")
def api_validate(body: ValidateBody):
    try:
        return {**ai.validate(body.asset, body.entry, body.side), "usage": ai.usage_today()}
    except ai.AIUnavailable:
        r = analytics.validate_rules(body.asset, body.entry, body.side)
        r.pop("bias", None)
        return {**r, "analysis": None, "note": "Rules-only verdict — AI narration unavailable (no API key)."}
    except ai.AIBudgetExceeded:
        raise HTTPException(status_code=429, detail=f"Daily AI budget reached ({ai.DAILY_LIMIT}).")


@app.get("/api/strategy-lab/{asset}")
def strategy_lab(asset: str):
    try:
        return analytics.strategy_lab(asset)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Feed down for {asset}")


@app.get("/api/shield")
def shield():
    return analytics.theta_shield()


@app.get("/api/exhaustion/{asset}")
def exhaustion(asset: str):
    ticker, name, _ = qc.resolve_ticker(asset)
    try:
        return {"asset": name, "ticker": ticker, **analytics.exhaustion_state(ticker)}
    except Exception:
        raise HTTPException(status_code=502, detail=f"Feed down for {ticker}")


# =====================================================================
# EXHAUSTION MONITOR — background loop, dedupe once per asset/side/day
# =====================================================================
_exh_sent = set()


async def _exhaustion_loop():
    while True:
        try:
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID and os.getenv("EXHAUSTION_ALERTS", "on") != "off":
                for name, d in qc.load_watchlist().items():
                    st = analytics.exhaustion_state(d["ticker"])
                    if st.get("triggered"):
                        k = f"{d['ticker']}:{st['side']}:{date.today().isoformat()}"
                        if k not in _exh_sent:
                            _exh_sent.add(k)
                            tg_send(TELEGRAM_CHAT_ID,
                                    f"💰 <b>TAKE PROFIT ALERT</b> 💰\n\n"
                                    f"{name} has reached extreme overextension exhaustion at "
                                    f"${st['price']:,.2f}. Lock in options contract premium immediately.")
        except Exception:
            pass
        await asyncio.sleep(900)


@app.on_event("startup")
async def _start_background():
    asyncio.create_task(_exhaustion_loop())


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
    "/valid &lt;asset&gt; &lt;entry&gt; [side] \u2014 structural VALID/INVALID verdict\n"
    "/edge &lt;asset&gt; \u2014 alpha optimizer scan (or NO_EDGE)\n"
    "/lab &lt;asset&gt; \u2014 walk-forward strategy lab + per-asset assignment\n"
    "/ask &lt;asset&gt; &lt;question&gt; \u2014 AI read on the live numbers\n\n"
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
    if cmd == "/valid":
        toks = arg.split()
        if len(toks) < 2:
            return "Usage: /valid <asset> <entry> [long|short]\nExample: /valid sofi 16.50 short"
        try:
            entry = float(toks[1])
        except ValueError:
            return "Entry must be a number. Example: /valid sofi 16.50"
        side = toks[2].lower() if len(toks) > 2 else None
        try:
            v = ai.validate(toks[0], entry, side)
            return f"🔎 <b>{v['asset']}</b> — {v['side'].upper()} @ ${entry:,.2f}\n\n{v['analysis']}"
        except ai.AIUnavailable:
            r = analytics.validate_rules(toks[0], entry, side)
            return (f"🔎 <b>{r['asset']}</b> — {r['side'].upper()} @ ${entry:,.2f}\n"
                    f"<b>STRUCTURALLY {r['verdict']}</b> — {r['reasons'][0]}")
        except ai.AIBudgetExceeded:
            return f"🤖 Daily AI budget reached ({ai.DAILY_LIMIT})."
        except Exception:
            return "❌ Validation failed — feed hiccup. Try again shortly."

    if cmd == "/lab":
        target = arg or "gold"
        try:
            lab = analytics.strategy_lab(target)
        except Exception:
            return "\u274C Feed down \u2014 try again shortly."
        lines = [f"\U0001F9EA <b>Strategy Lab \u2014 {lab['asset']}</b> (verdicts on held-out 30%)"]
        for r in lab["results"]:
            t = r["test"]
            mark = "\u2705" if r["validated"] else "\u274C"
            pf = t["profit_factor"] if t["profit_factor"] is not None else "\u221E"
            lines.append(f"{mark} <b>{r['name']}</b> \u2014 OOS: win {t['win_rate']*100:.0f}% | "
                         f"PF {pf} | {t['expectancy_pct']:+.2f}%/trade | {t['signals_per_week']}/wk")
        if lab["assigned"]:
            lines.append(f"\n\U0001F3AF <b>ASSIGNED: {lab['assigned']['name']}</b> \u2014 "
                         f"the one strategy for this asset.")
        else:
            lines.append("\n\U0001F6E1 <b>NOTHING VALIDATED</b> \u2014 no family survived "
                         "out-of-sample. Standing aside on this asset IS the strategy.")
        return "\n".join(lines)

    if cmd == "/edge":
        target = arg or "gold"
        try:
            e = analytics.optimized_edge(target)
        except Exception:
            return "❌ Feed down — try again shortly."
        if e["flag"] == "NO_EDGE":
            return (f"🛡 <b>NO_EDGE — {e['asset']}</b>\n"
                    f"No strategy is both signaling today AND ≥{int(e['thresholds']['win_rate']*100)}% "
                    f"win rate over 5y (≥{e['thresholds']['min_trades']} trades). "
                    f"Regime: {e['regime']['label']}. Sitting on hands IS the position.")
        lines = [f"⚡ <b>EDGE FOUND — {e['asset']}</b>"]
        for c in e["candidates"]:
            lines.append(f"• {c['name']} → {c['signal_today'].upper()} | "
                         f"5y win {c['win_rate_5y']*100:.0f}% ({c['trades_5y']} trades) | "
                         f"exp {c['expectancy_pct']:+.2f}%/trade")
        return "\n".join(lines)

    if cmd == "/ask":
        if not arg:
            return "Usage: /ask <asset> <question>\nExample: /ask sofi is now a good entry?"
        tokens = arg.split(maxsplit=1)
        asset = tokens[0]
        question = tokens[1] if len(tokens) > 1 else "Give me the full read on this setup."
        try:
            return f"\U0001F916 <b>{asset.upper()}</b>\n\n{ai.ask(asset, question)}"
        except ai.AIUnavailable:
            return "\U0001F916 AI not configured \u2014 ANTHROPIC_API_KEY missing on the API service."
        except ai.AIBudgetExceeded:
            return f"\U0001F916 Daily AI budget reached ({ai.DAILY_LIMIT}). Pure-math commands still free: /bias, /status."
        except Exception:
            return "\u274C AI call failed \u2014 feed or API hiccup. Try again shortly."
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
