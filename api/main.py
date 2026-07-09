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
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

import json as _json
import time as _time
from collections import deque

import quant_core as qc
from api import ai
from api import analytics
from api import db, screener, store
from pydantic import BaseModel
import asyncio
from datetime import date
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")

# ── DB-as-truth: when Supabase is configured, the ENGINE reads the
#    operator's rows from Postgres; files remain the fallback. This single
#    override makes agent/telegram/analytics DB-aware with zero edits.
qc.load_watchlist = lambda: store.get_watchlist(store.resolve_user(None))
qc.load_positions = lambda: store.get_positions(store.resolve_user(None))

app = FastAPI(title="N-CORE Quant API", version="1.0.0")

# NOTE: open CORS while the PWA is being built; tighten allow_origins to
# the PWA's domain before sharing the API URL anywhere public.
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
AGENT_INTERVAL = int(os.getenv("AGENT_INTERVAL", "1200"))   # seconds; >=900 respects feed limits

# ── Notification queue (Volt Bell) + web-push subscriptions ──
NOTIFICATIONS = deque(maxlen=50)
PUSH_SUBS_FILE = "push_subs.json"


def notify(kind: str, title: str, body: str):
    evt = {"ts": int(_time.time()), "kind": kind, "title": title, "body": body}
    NOTIFICATIONS.appendleft(evt)
    _web_push_all(evt)
    return evt


def _load_subs():
    try:
        with open(PUSH_SUBS_FILE) as f:
            return _json.load(f)
    except Exception:
        return []


def _web_push_all(evt):
    """Native lock-screen pushes. Requires VAPID_PRIVATE_KEY +
    VAPID_CLAIMS_EMAIL env; silently no-ops when unconfigured."""
    key = os.getenv("VAPID_PRIVATE_KEY")
    email = os.getenv("VAPID_CLAIMS_EMAIL")
    subs = _load_subs()
    if not (key and email and subs):
        return
    try:
        from pywebpush import webpush
    except Exception:
        return
    alive = []
    for sub in subs:
        try:
            webpush(subscription_info=sub,
                    data=_json.dumps({"title": evt["title"], "body": evt["body"]}),
                    vapid_private_key=key,
                    vapid_claims={"sub": f"mailto:{email}"})
            alive.append(sub)
        except Exception:
            continue   # dead subscription — pruned
    if len(alive) != len(subs):
        try:
            with open(PUSH_SUBS_FILE, "w") as f:
                _json.dump(alive, f)
        except Exception:
            pass


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
    a = analytics.assignment_for(asset)
    if a:
        side = None
        try:
            side = analytics._signals_today(ticker).get(a["strategy"])
        except Exception:
            pass
        b["assigned_strategy"] = {"strategy": a["strategy"], "name": a["strategy_name"],
                                  "assigned_at": a.get("assigned_at")}
        b["signaling_today"] = bool(side)
        b["signal_side"] = side
    else:
        b["assigned_strategy"] = None
        b["signaling_today"] = False
        b["signal_side"] = None
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


# ── SUPABASE AUTH SCAFFOLD — zero new deps: verified over REST ──
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")


def get_current_user(authorization: str | None = Header(default=None)):
    """FastAPI dependency. File-mode fallback FIRST: if Supabase env vars
    are absent (both None, empty, or not set), return file-fallback. Only
    demand bearer token if Supabase is actually configured."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return {"id": "operator", "mode": "file-fallback"}
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = authorization.split(" ", 1)[1]
    try:
        r = requests.get(f"{SUPABASE_URL}/auth/v1/user",
                         headers={"apikey": SUPABASE_ANON_KEY,
                                  "Authorization": f"Bearer {token}"}, timeout=8)
    except Exception:
        raise HTTPException(status_code=503, detail="Auth service unreachable.")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return r.json()


@app.get("/api/me")
def me(user: dict = Depends(get_current_user)):
    return {"user": {"id": user.get("id"), "email": user.get("email")},
            "mode": user.get("mode", "supabase")}


PERSISTENCE_WARNING = ("Saved to the live service. NOTE: Railway's filesystem resets on "
                       "every redeploy — commit important changes to GitHub, or wait for "
                       "the Supabase persistence phase.")


class WatchBody(BaseModel):
    name: str
    ticker: str
    unit: str = "/sh"


@app.post("/api/watchlist")
def add_watchlist(body: WatchBody, user: dict = Depends(get_current_user)):
    uid = store.resolve_user(user)
    wl = store.get_watchlist(uid)
    if body.name in wl:
        raise HTTPException(status_code=409, detail=f"'{body.name}' already tracked.")
    if qc.get_quote(body.ticker.upper()) is None:
        raise HTTPException(status_code=422, detail=f"{body.ticker.upper()} returned no data from the feed.")
    store.add_watchlist(uid, body.name, body.ticker.upper(), body.unit)
    out = {"watchlist": store.get_watchlist(uid)}
    if not uid:
        out["persistence_warning"] = PERSISTENCE_WARNING
    return out


@app.delete("/api/watchlist/{name}")
def remove_watchlist(name: str, user: dict = Depends(get_current_user)):
    uid = store.resolve_user(user)
    wl = store.get_watchlist(uid)
    match = next((k for k in wl if k.lower() == name.lower()), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"'{name}' not on the watchlist.")
    if len(wl) <= 1:
        raise HTTPException(status_code=409, detail="Cannot remove the last asset.")
    store.remove_watchlist(uid, match)
    out = {"watchlist": store.get_watchlist(uid)}
    if not uid:
        out["persistence_warning"] = PERSISTENCE_WARNING
    return out


class PositionBody(BaseModel):
    asset: str
    strike: float
    contract_type: str          # "call" | "put"
    entry_premium: float
    entry_date: str             # YYYY-MM-DD
    expiration: str             # YYYY-MM-DD
    premium_stop: float | None = None
    time_stop: str | None = None
    invalidation_above: float | None = None
    invalidation_below: float | None = None


@app.post("/api/positions")
def add_position(body: PositionBody, user: dict = Depends(get_current_user)):
    if body.contract_type.lower() not in ("call", "put"):
        raise HTTPException(status_code=422, detail="contract_type must be 'call' or 'put'.")
    uid = store.resolve_user(user)
    rec = {k: v for k, v in body.dict().items() if v is not None}
    rec["asset"] = body.asset.upper()
    rec["type"] = rec.pop("contract_type").lower()
    pid = store.add_position(uid, rec)
    out = {"id": pid, "position": rec, "shield_armed": bool(body.entry_date)}
    if not uid:
        out["persistence_warning"] = PERSISTENCE_WARNING
    return out


@app.get("/api/screener")
def api_screener():
    return store.get_screener()


@app.get("/api/scan")
def api_scan():
    return {"hits": analytics.scan_playbook(),
            "playbook_size": len({r["key"] for r in analytics.load_playbook().values()})}


@app.get("/api/notifications")
def api_notifications(since: int = 0):
    return [e for e in NOTIFICATIONS if e["ts"] > since]


@app.post("/api/push/subscribe")
async def push_subscribe(request: Request):
    sub = await request.json()
    if not sub.get("endpoint"):
        raise HTTPException(status_code=422, detail="Not a push subscription.")
    subs = _load_subs()
    if not any(s.get("endpoint") == sub["endpoint"] for s in subs):
        subs.append(sub)
        with open(PUSH_SUBS_FILE, "w") as f:
            _json.dump(subs, f)
    return {"ok": True, "subscriptions": len(subs),
            "push_configured": bool(os.getenv("VAPID_PRIVATE_KEY"))}


@app.get("/api/candidates")
def api_candidates():
    return {"candidates": analytics.candidates(),
            "note": "\u26A0\uFE0F UNVALIDATED leads from the fast families across the whole "
                    "watchlist. Run /lab on an asset before treating any of these as a signal."}


# ── JOURNAL: the permanent, honest audit log ──
JOURNAL_FILE = "journal.json"


def _load_journal():
    try:
        with open(JOURNAL_FILE) as f:
            return _json.load(f)
    except Exception:
        return []


class CloseBody(BaseModel):
    exit_premium: float
    exit_date: str | None = None          # YYYY-MM-DD, default today
    thesis: str | None = None
    rule_compliant: bool | None = None    # did the exit follow the plan?
    notes: str | None = None


@app.post("/api/positions/{pid}/close")
def close_position(pid: str, body: CloseBody, user: dict = Depends(get_current_user)):
    pos = qc.load_positions()
    if pid not in pos:
        raise HTTPException(status_code=404, detail=f"Position '{pid}' not found.")
    p = pos[pid]
    entry_prem = float(p.get("entry_premium") or p.get("entry") or 0)
    pnl_pct = (round((body.exit_premium - entry_prem) / entry_prem * 100, 2)
               if entry_prem else None)
    exit_d = body.exit_date or date.today().isoformat()
    holding = None
    try:
        holding = (datetime.strptime(exit_d, "%Y-%m-%d").date() -
                   datetime.strptime(p.get("entry_date", ""), "%Y-%m-%d").date()).days
    except Exception:
        pass
    a = analytics.assignment_for(p.get("asset", ""))
    verdict_now = None
    try:
        verdict_now = analytics.validate_rules(p.get("asset", ""), float(p.get("strike", 0)))["verdict"]
    except Exception:
        pass
    entry = {
        "id": pid, "asset": p.get("asset"), "type": p.get("type"),
        "strike": p.get("strike"), "expiration": p.get("expiration"),
        "entry_date": p.get("entry_date"), "exit_date": exit_d,
        "entry_premium": entry_prem, "exit_premium": body.exit_premium,
        "pnl_pct": pnl_pct, "holding_days": holding,
        "strategy": (a or {}).get("strategy"),
        "strategy_name": (a or {}).get("strategy_name"),
        "verdict_at_close": verdict_now,
        "thesis": body.thesis, "rule_compliant": body.rule_compliant,
        "notes": body.notes, "logged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    store.close_position(store.resolve_user(user), pid, entry)
    notify("journal", f"\U0001F4D2 {entry['asset']} closed {pnl_pct:+.1f}%" if pnl_pct is not None
           else f"\U0001F4D2 {entry['asset']} closed", body.notes or "Logged to the journal.")
    return {"journal_entry": entry, "persistence_warning": PERSISTENCE_WARNING}


@app.get("/api/journal")
def api_journal(user: dict = Depends(get_current_user)):
    """Entries + behavioral aggregates: the operator's mirror."""
    j = store.get_journal(store.resolve_user(user))
    by_strat = {}
    for e in j:
        k = e.get("strategy_name") or "Unassigned"
        by_strat.setdefault(k, []).append(e)
    aggregates = {"total_trades": len(j)}
    if j:
        pnls = [e["pnl_pct"] for e in j if e.get("pnl_pct") is not None]
        holds = [e["holding_days"] for e in j if e.get("holding_days") is not None]
        rc = [e["rule_compliant"] for e in j if e.get("rule_compliant") is not None]
        aggregates.update({
            "win_rate": round(sum(1 for p in pnls if p > 0) / len(pnls), 4) if pnls else None,
            "avg_pnl_pct": round(sum(pnls) / len(pnls), 2) if pnls else None,
            "avg_holding_days": round(sum(holds) / len(holds), 1) if holds else None,
            "rule_adherence": round(sum(1 for r in rc if r) / len(rc), 4) if rc else None,
            "per_strategy": {k: {
                "n": len(v),
                "win_rate": round(sum(1 for e in v if (e.get("pnl_pct") or 0) > 0) / len(v), 4),
                "avg_pnl_pct": round(sum(e.get("pnl_pct") or 0 for e in v) / len(v), 2),
            } for k, v in by_strat.items()},
        })
    return {"entries": j, "aggregates": aggregates}





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
# THE AGENT WORKER — continuous automation, both channels, deduped.
#   Cycle: playbook scan → exhaustion check → macro proximity.
#   Interval floor 900s: faster polling risks the price feed banning
#   us, which kills everything. Plain-honest language on every alert.
# =====================================================================
# Restart-proof dedupe: cooldowns live in Postgres (store.cooldown_*),
# so a redeploy can never re-fire the same alert (the IWM 4x bug).
ALERT_COOLDOWN_H = float(os.getenv("ALERT_COOLDOWN_HOURS", "20"))


def _agent_pass():
    """One full cycle. Extracted from the loop so tests can drive it."""
    today = date.today().isoformat()

    # 1) Playbook: assigned strategies firing on the live close
    for h in analytics.scan_playbook():
        k = f"pb:{h['ticker']}:{h['side']}"
        if store.cooldown_active(k):
            continue
        store.cooldown_set(k, ALERT_COOLDOWN_H)
        verb = "buy-the-dip" if h["side"] == "long" else "fade-the-spike"
        px = f" at ${h['price']:,.2f}" if h.get("price") else ""
        body = (f"{h['asset']}{px}: your validated {h['strategy_name']} strategy "
                f"just fired a {verb} setup. This is the exact pattern that made "
                f"money in walk-forward testing \u2014 check the app for levels.")
        caption = f"\U0001F3AF <b>PLAYBOOK SETUP LIVE</b>\n\n{body}"
        sent_media = False
        try:
            b = qc.get_bias(h["ticker"])
            png = analytics.render_chart_card(
                h["ticker"], f"{h['asset']} \u2014 {h['strategy_name']} ({h['side'].upper()})",
                entry=b.get("arm_level"), stop=b.get("invalidation"), target=b.get("target"))
            sent_media = tg_send_photo(TELEGRAM_CHAT_ID, png, caption)
        except Exception:
            pass
        if not sent_media:
            tg_send(TELEGRAM_CHAT_ID, caption)
        notify("playbook", f"\U0001F3AF {h['asset']} setup live", body)

    # 2) Exhaustion: spent thrusts at extremes
    for name, d in qc.load_watchlist().items():
        try:
            st = analytics.exhaustion_state(d["ticker"])
        except Exception:
            continue
        if st.get("triggered"):
            k = f"ex:{d['ticker']}:{st['side']}"
            if store.cooldown_active(k):
                continue
            store.cooldown_set(k, ALERT_COOLDOWN_H)
            caption = (f"\U0001F4B0 <b>TAKE PROFIT ALERT</b> \U0001F4B0\n\n"
                       f"{name} has reached extreme overextension exhaustion at "
                       f"${st['price']:,.2f}. Lock in options contract premium immediately.")
            sent_media = False
            try:
                b = qc.get_bias(d["ticker"])
                png = analytics.render_chart_card(
                    d["ticker"], f"{name} \u2014 EXHAUSTION at ${st['price']:,.2f}",
                    stop=b.get("invalidation"), target=b.get("target"))
                sent_media = tg_send_photo(TELEGRAM_CHAT_ID, png, caption)
            except Exception:
                pass
            if not sent_media:
                tg_send(TELEGRAM_CHAT_ID, caption)
            notify("exhaustion", f"\U0001F4B0 {name} looks exhausted",
                   f"The move in {name} is losing steam at ${st['price']:,.2f} after an "
                   f"extreme stretch \u2014 historically where thrusts stall. If you're "
                   f"in profit, consider locking some in.")

    # 3) Macro proximity: big USD news inside the 3-hour window
    try:
        rad = analytics.macro_radar()
        if rad.get("hijack") and rad.get("nearest"):
            ev = rad["nearest"]
            k = f"mr:{ev['event']}:{today}"
            if not store.cooldown_active(k):
                store.cooldown_set(k, ALERT_COOLDOWN_H)
                body = (f"{ev['event']} hits in about {ev['minutes_remaining']} minutes. "
                        f"Big news like this can shake every asset on the board \u2014 "
                        f"setups armed into it carry extra gap risk.")
                tg_send(TELEGRAM_CHAT_ID, f"\u26A0\uFE0F <b>HEADS UP \u2014 BIG NEWS SOON</b>\n\n{body}")
                notify("macro", f"\u26A0\uFE0F {ev['event']} in {ev['minutes_remaining']}m", body)
    except Exception:
        pass


async def _agent_loop():
    while True:
        try:
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID and os.getenv("AGENT", "on") != "off":
                _agent_pass()
        except Exception:
            pass
        await asyncio.sleep(max(AGENT_INTERVAL, 900))


def _fmt_digest() -> str:
    """The Daily Digest: conversational, top-4 HUB assets only, zero jargon."""
    wl = qc.load_watchlist()
    top4 = list(wl.items())[:4]
    lines = ["\u2600\uFE0F <b>Good morning! Here's how your top assets look "
             "heading into the open:</b>", ""]
    firing = 0
    for name, d in top4:
        try:
            b = qc.get_bias(d["ticker"])
        except Exception:
            lines.append(f"\u274C <b>{name}</b> \u2014 feed unreachable right now.")
            continue
        emoji, headline, _ = analytics.plain_state(b)
        arrow = "\u2197\uFE0F" if "BULLISH" in b["trend"] else "\u2198\uFE0F"
        first = headline.split("\u2014")[0].strip().rstrip(".")
        lines.append(f"{emoji} <b>{name}</b> {arrow} ${b['price']:,.2f}{d.get('unit','')}"
                     f" \u2014 {first}.")
        a = analytics.assignment_for(name)
        if a:
            try:
                if analytics._signals_today(d["ticker"]).get(a["strategy"]):
                    firing += 1
                    lines.append(f"    \u26A1 Your validated {a['strategy_name']} "
                                 f"strategy is live on this one today.")
            except Exception:
                pass
    lines.append("")
    lines.append("\U0001F3AF A playbook setup is live \u2014 check the app."
                 if firing else
                 "\U0001F634 No validated setups at the bell. Patience pays.")
    lines.append("<i>Statistics, not certainties \u2014 have a great session.</i>")
    return "\n".join(lines)


async def _run_daily_screener():
    """Post-close Catalyst Screener on completed bars, then alert fresh hits."""
    hits = await asyncio.to_thread(screener.run_screener)
    scan_date = datetime.now(NY).date().isoformat()
    store.save_screener(scan_date, hits)
    fresh = [h for h in hits if not store.cooldown_active(f"scr:{h['ticker']}")]
    for h in fresh:
        store.cooldown_set(f"scr:{h['ticker']}", 144)   # 6 days: one alert per breakout
    if fresh and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        lines = [f"\U0001F680 <b>Catalyst Screener \u2014 {len(fresh)} fresh "
                 f"52-week breakout{'s' if len(fresh) != 1 else ''} on \u2265"
                 f"{screener.RVOL_MIN:g}\u00D7 volume today:</b>"]
        for h in fresh[:10]:
            lines.append(f"\u2022 <b>{h['ticker']}</b> ${h['price']:,.2f} \u2014 "
                         f"{h['rvol']:.1f}\u00D7 normal volume, broke out {h['breakout_date']}")
        lines.append("<i>Breakout confluence, not advice \u2014 run /lab before trading any.</i>")
        tg_send(TELEGRAM_CHAT_ID, "\n".join(lines))
        notify("screener", f"\U0001F680 {len(fresh)} fresh breakouts",
               ", ".join(h["ticker"] for h in fresh[:10]))
    return hits


async def _clock_loop():
    """NY-anchored scheduler: Digest 09:30 ET, Screener 16:15 ET, weekdays."""
    while True:
        try:
            now = datetime.now(NY)
            if now.weekday() < 5 and os.getenv("AGENT", "on") != "off":
                hhmm = now.hour * 100 + now.minute
                dkey = f"digest:{now.date().isoformat()}"
                if 930 <= hhmm < 945 and not store.cooldown_active(dkey):
                    store.cooldown_set(dkey, 20)
                    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                        tg_send(TELEGRAM_CHAT_ID, _fmt_digest())
                skey = f"screener:{now.date().isoformat()}"
                if 1615 <= hhmm < 1645 and not store.cooldown_active(skey):
                    store.cooldown_set(skey, 20)
                    await _run_daily_screener()
        except Exception:
            pass
        await asyncio.sleep(60)


def tg_set_my_commands():
    """Native Telegram command menu (the clean three-line menu button) —
    replaces the screen-hogging reply keyboard entirely."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    cmds = [
        {"command": "status", "description": "Your whole board in one glance"},
        {"command": "bias", "description": "Full read on one asset (e.g. /bias gold)"},
        {"command": "scan", "description": "Any validated playbook setups today?"},
        {"command": "screener", "description": "Fresh 52-week breakout catalysts"},
        {"command": "lab", "description": "Walk-forward test an asset (e.g. /lab nvda)"},
        {"command": "playbook", "description": "Your active validated strategies"},
        {"command": "candidates", "description": "Unvalidated fast-family leads"},
        {"command": "valid", "description": "Grade a trade idea (e.g. /valid sofi 16.5 short)"},
        {"command": "positions", "description": "Trades the Guardian is watching"},
        {"command": "journal", "description": "Your trade history + win rate"},
        {"command": "macro", "description": "Big economic events this week"},
        {"command": "ask", "description": "Ask anything about an asset"},
        {"command": "help", "description": "What everything does, in plain English"},
    ]
    try:
        r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyCommands",
                          json={"commands": cmds}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


@app.on_event("startup")
async def _start_background():
    tg_set_my_commands()
    asyncio.create_task(_agent_loop())
    asyncio.create_task(_clock_loop())


# =====================================================================
# TELEGRAM WEBHOOK# =====================================================================
# TELEGRAM WEBHOOK — the command bot (Phase 4a: pure math, no AI spend)
# =====================================================================
MAIN_KEYBOARD = {
    "keyboard": [["\U0001F9EA Strategy Lab", "\U0001F50D Scan Playbook"],
                 ["\U0001F4F1 Status", "\U0001F6E1 Positions"],
                 ["\U0001F4D6 Playbook", "\u2753 Help"]],
    "resize_keyboard": True, "is_persistent": True,
}


def asset_inline_keyboard(action: str):
    """Inline grid of watchlist assets; a tap fires '{action}|{name}'."""
    rows, row = [], []
    for n in qc.load_watchlist().keys():
        row.append({"text": n, "callback_data": f"{action}|{n}"[:64]})
        if len(row) == 3:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return {"inline_keyboard": rows}


def tg_send_photo(chat_id, png_bytes: bytes, caption: str) -> bool:
    """Chart-card dispatch. Falls back to text if the media send fails."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption[:1024], "parse_mode": "HTML"},
            files={"photo": ("chart.png", png_bytes, "image/png")},
            timeout=20,
        )
        return r.status_code == 200
    except Exception:
        return False


def tg_answer_callback(callback_id):
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
                      json={"callback_query_id": callback_id}, timeout=5)
    except Exception:
        pass


def tg_send(chat_id, text: str, reply_markup: dict | None = None) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        payload = {"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML",
                   "disable_web_page_preview": True}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json=payload, timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def _fmt_bias(asset_query: str) -> str:
    ticker, name, unit = qc.resolve_ticker(asset_query)
    q = qc.get_quote(ticker)
    if q is None:
        return f"\u274C Can't reach the price feed for {name} right now. Try again in a minute."
    b = qc.get_bias(ticker)
    emoji, headline, action = analytics.plain_state(b)
    trend_plain = ("the bigger trend points UP" if "BULLISH" in b["trend"]
                   else "the bigger trend points DOWN")
    stretch = abs(b["z"])
    stretch_plain = ("sitting right around normal" if stretch < 1 else
                     "moderately stretched" if stretch < 2 else
                     "VERY stretched \u2014 like a pulled rubber band")
    out = (f"{emoji} <b>{name}</b> \u2014 ${b['price']:,.2f}{unit}\n"
           f"{headline}\n\n"
           f"\U0001F4CF Price is {stretch_plain} vs its recent average, and {trend_plain}.\n"
           f"\U0001F3AF {action}")
    a = analytics.assignment_for(asset_query)
    if a:
        side = analytics._signals_today(ticker).get(a["strategy"])
        if side:
            out += (f"\n\n\u26A1 <b>Your playbook strategy ({a['strategy_name']}) is "
                    f"firing a {side.upper()} setup right now.</b>")
        else:
            out += (f"\n\n\U0001F4D6 Playbook: {a['strategy_name']} assigned \u2014 "
                    f"not triggering today.")
    return out


def _fmt_status() -> str:
    lines = ["\U0001F4CA <b>Your whole board, one glance:</b>"]
    for asset_name, d in qc.load_watchlist().items():
        try:
            b = qc.get_bias(d["ticker"])
            emoji, _, _ = analytics.plain_state(b)
            word = {"\U0001F7E2": "dip-buy setup LIVE", "\U0001F534": "fade setup LIVE",
                    "\U0001F440": "getting close", "\U0001F634": "quiet"}[emoji]
            lines.append(f"{emoji} <b>{asset_name}</b> ${b['price']:,.2f} \u2014 {word}")
        except Exception:
            lines.append(f"\u274C <b>{asset_name}</b> \u2014 feed unreachable")
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
    "\u26A1 <b>Your terminal, in plain English.</b> Tap the menu buttons below, "
    "or type any of these:\n\n"
    "\U0001F4F1 <b>/status</b> \u2014 your whole board in one glance: which assets are "
    "quiet, which have a live setup.\n"
    "\U0001F3AF <b>/bias</b> gold \u2014 the full story on one asset: how stretched the "
    "price is, where to get in, where you're wrong, where to take profit.\n"
    "\U0001F9EA <b>/lab</b> nvda \u2014 tests 5 trading styles on 5 years of data and "
    "tells you which (if any) actually made money on data it never saw.\n"
    "\U0001F50D <b>/scan</b> \u2014 checks your playbook: are any of your validated "
    "strategies firing a setup TODAY?\n"
    "\U0001F4D6 <b>/playbook</b> \u2014 your active book: which strategy is assigned "
    "to which asset, and when.\n"
    "\U0001F50E <b>/valid</b> sofi 16.50 short \u2014 grades a trade idea against the "
    "math: VALID or INVALID, with three quick reasons.\n"
    "\U0001F4CA <b>/backtest</b> gold \u2014 report card for every strategy on this asset.\n"
    "\U0001F6E1 <b>/positions</b> \u2014 the trades your Guardian is watching.\n"
    "\U0001F6A8 <b>/macro</b> \u2014 big economic news coming this week that can shake prices.\n"
    "\U0001F916 <b>/ask</b> gold is now a good entry? \u2014 ask anything; answers come "
    "from YOUR live numbers, not the internet.\n\n"
    "<i>Everything here reads out statistics, not certainties \u2014 and none of it "
    "is financial advice.</i>"
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

    # Menu-button taps arrive as plain text — map them to commands
    BUTTON_MAP = {"\U0001F9EA Strategy Lab": "/labmenu", "\U0001F50D Scan Playbook": "/scan",
                  "\U0001F4F1 Status": "/status", "\U0001F6E1 Positions": "/positions",
                  "\U0001F4D6 Playbook": "/playbook", "\u2753 Help": "/help"}
    raw = text.strip()
    for label, mapped in BUTTON_MAP.items():
        # labels arrive as REAL emoji chars; compare against decoded label
        if raw == label.encode().decode("unicode_escape") or raw == label:
            cmd, arg = mapped, ""
            break

    if cmd in ("/start", "/help"):
        return HELP_TEXT

    if cmd == "/labmenu":
        return "__LABMENU__"

    if cmd == "/scan":
        hits = analytics.scan_playbook()
        if not hits:
            return ("\U0001F50D <b>Playbook scan: nothing firing today.</b>\n"
                    "None of your validated strategies see a setup on the current "
                    "prices. A quiet day \u2014 sitting out IS the strategy.")
        lines = ["\u26A1 <b>Playbook scan \u2014 LIVE setups:</b>"]
        for h in hits:
            verb = "buy-the-dip" if h["side"] == "long" else "fade-the-spike"
            px = f" at ${h['price']:,.2f}" if h.get("price") else ""
            lines.append(f"\U0001F3AF <b>{h['asset']}</b>{px} \u2014 your validated "
                         f"<b>{h['strategy_name']}</b> is firing a {verb} ({h['side'].upper()}) setup.")
        return "\n".join(lines)

    if cmd == "/screener":
        s = store.get_screener()
        if not s.get("hits"):
            return ("\U0001F680 <b>Catalyst Screener:</b> no fresh 52-week "
                    "breakouts on elevated volume in the latest scan "
                    f"({s.get('scan_date') or 'no scan yet'}). Scarcity is the filter working.")
        lines = [f"\U0001F680 <b>Catalyst Screener \u2014 {s['scan_date']}:</b>"]
        for h in s["hits"][:10]:
            lines.append(f"\u2022 <b>{h['ticker']}</b> ${h['price']:,.2f} \u2014 "
                         f"{h['rvol']:.1f}\u00D7 volume, broke out {h['breakout_date']}")
        return "\n".join(lines)

    if cmd == "/candidates":
        cands = analytics.candidates()
        if not cands:
            return "\U0001F50E No fast-family setups anywhere on the board today."
        lines = ["\U0001F50E <b>Velocity candidates</b> \u2014 \u26A0\uFE0F UNVALIDATED leads, not signals:"]
        for c2 in cands[:12]:
            tag = "\u2705 validated" if c2["validated"] else "\u26A0\uFE0F run /lab first"
            px = f" ${c2['price']:,.2f}" if c2.get("price") else ""
            lines.append(f"\u2022 <b>{c2['asset']}</b>{px} \u2014 {c2['family_name']} "
                         f"{c2['side'].upper()} ({tag})")
        return "\n".join(lines)

    if cmd == "/journal":
        import json as __j
        try:
            with open("journal.json") as f:
                j = __j.load(f)
        except Exception:
            j = []
        if not j:
            return "\U0001F4D2 Journal is empty \u2014 close a position to write history."
        pnls = [e["pnl_pct"] for e in j if e.get("pnl_pct") is not None]
        wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100 if pnls else 0
        lines = [f"\U0001F4D2 <b>Journal</b> \u2014 {len(j)} trades | win rate {wr:.0f}%"]
        for e in j[-5:]:
            pp = f"{e['pnl_pct']:+.1f}%" if e.get("pnl_pct") is not None else "\u2014"
            lines.append(f"\u2022 {e['asset']} {str(e.get('type','')).upper()} "
                         f"{e.get('entry_date','?')} \u2192 {e.get('exit_date','?')}: <b>{pp}</b>")
        return "\n".join(lines)

    if cmd == "/playbook":
        pb = analytics.load_playbook()
        uniq = {r["key"]: r for r in pb.values()}
        if not uniq:
            return "\U0001F4D6 No playbook yet \u2014 run /lab on your assets to earn assignments."
        lines = ["\U0001F4D6 <b>Your active playbook</b> (walk-forward validated):"]
        for key, r in uniq.items():
            lines.append(f"\u2022 <b>{key}</b> \u2192 {r['strategy_name']} "
                         f"({analytics.STRATEGY_PLAIN.get(r['strategy'], '')}) \u2014 "
                         f"assigned {r.get('assigned_at', '?')}")
        lines.append("\nFull stats live in PLAYBOOK.md in the repo \u2014 the honest audit trail.")
        return "\n".join(lines)
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

    # ── Inline-button taps (callback queries) ──
    cq = update.get("callback_query")
    if cq:
        chat_id = str(((cq.get("message") or {}).get("chat") or {}).get("id", ""))
        if not chat_id or (TELEGRAM_CHAT_ID and chat_id != str(TELEGRAM_CHAT_ID)):
            return {"ok": True}
        tg_answer_callback(cq.get("id"))
        data = (cq.get("data") or "")
        if "|" in data:
            action, target = data.split("|", 1)
            if action == "lab":
                tg_send(chat_id, route_command(f"/lab {target}"))
            elif action == "bias":
                tg_send(chat_id, route_command(f"/bias {target}"))
        return {"ok": True}

    msg = update.get("message") or update.get("edited_message") or {}
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    text = (msg.get("text") or "").strip()

    # Layer 2: hard allowlist — strangers get silence, not errors
    if not chat_id or (TELEGRAM_CHAT_ID and chat_id != str(TELEGRAM_CHAT_ID)):
        return {"ok": True}
    if not text:
        return {"ok": True}

    reply = route_command(text)
    if reply == "__LABMENU__":
        tg_send(chat_id, "\U0001F9EA Pick an asset to run the lab on:",
                reply_markup=asset_inline_keyboard("lab"))
    elif text.strip().split("@")[0].lower() == "/start":
        # Reply keyboards are retired: remove any lingering one and point
        # to the native command menu (the \u2630 button beside the input).
        tg_send(chat_id, reply, reply_markup={"remove_keyboard": True})
    else:
        tg_send(chat_id, reply)
    return {"ok": True}
