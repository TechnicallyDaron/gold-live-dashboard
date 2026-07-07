"""
api/ai.py — Phase 4b: the AI tier.

Design for cost efficiency:
  - Model: env AI_MODEL, default claude-haiku-4-5 (fractions of a cent
    per answer). Promote to a bigger model by changing one env var.
  - Cache: identical question + asset + similar price within TTL = free.
  - Compact context: the engine's pre-computed stats (a few hundred
    tokens), never raw market data.
  - Budget breaker: env AI_DAILY_LIMIT (default 60 calls/day). When hit,
    callers get a clean 'budget reached' — the meter cannot run away.
"""
import hashlib
import json
import os
import threading
import time
from datetime import date

import quant_core as qc

MODEL = os.getenv("AI_MODEL", "claude-haiku-4-5")
DAILY_LIMIT = int(os.getenv("AI_DAILY_LIMIT", "60"))

try:
    import anthropic
    _client = (anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
               if os.getenv("ANTHROPIC_API_KEY") else None)
except Exception:
    _client = None


class AIUnavailable(Exception):
    """No API key configured on this service."""


class AIBudgetExceeded(Exception):
    """Daily call limit reached — resets at midnight UTC."""


_cache = {}
_lock = threading.Lock()
_spend = {"day": None, "count": 0}


def usage_today():
    with _lock:
        return {"day": _spend["day"], "count": _spend["count"], "limit": DAILY_LIMIT}


def _take_budget():
    with _lock:
        today = date.today().isoformat()
        if _spend["day"] != today:
            _spend["day"], _spend["count"] = today, 0
        if _spend["count"] >= DAILY_LIMIT:
            raise AIBudgetExceeded()
        _spend["count"] += 1


def _cached_completion(key: str, ttl: int, prompt: str, max_tokens: int) -> str:
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    if _client is None:
        raise AIUnavailable()
    _take_budget()
    resp = _client.messages.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text
    with _lock:
        _cache[key] = (now, text)
    return text


def _context(asset: str):
    """Compact, engine-computed context. Returns (name, ticker, ctx, px_bucket)."""
    ticker, name, unit = qc.resolve_ticker(asset)
    b = qc.get_bias(ticker)
    _, stats = qc.run_backtest(ticker)
    d = stats.get(b.get("direction") or "all", stats["all"])
    ctx = (
        f"- State: {b['state']}\n"
        f"- Spot: ${b['price']:,.2f}{unit} | Z-score: {b['z']:+.2f} std devs | {b['trend']}\n"
        f"- 20 EMA: ${b['baseline']:,.2f} | Bands: ${b['lower']:,.2f} / ${b['upper']:,.2f}\n"
        f"- Arm: ${b['arm_level']:,.2f} ({b['dist_to_arm_pct']:+.2f}%) | "
        f"Invalidation: ${b['invalidation']:,.2f} | Target: ${b['target']:,.2f}\n"
        f"- Setup base rates (5y, this direction): {d['n']} trades, "
        f"win rate {d['win_rate']*100:.1f}%, avg win {d['avg_win']*100:+.2f}%, "
        f"avg loss {d['avg_loss']*100:+.2f}%\n"
        f"- Strategy 5y: {stats['strategy_return']*100:+.1f}% vs B&H "
        f"{stats['buy_hold_return']*100:+.1f}%, max DD {stats['max_drawdown']*100:.1f}%"
    )
    return name, ticker, ctx, round(b["price"], 0)


def ask(asset: str, question: str) -> str:
    """Plain-language answer grounded ONLY in the live engine readout."""
    name, ticker, ctx, px = _context(asset)
    qhash = hashlib.sha1(question.lower().strip().encode()).hexdigest()[:10]
    key = f"ask:{ticker}:{px}:{qhash}"
    prompt = (
        f"You are a quantitative analyst explaining a trading terminal readout "
        f"for {name} ({ticker}) to its owner. Answer their question plainly, in "
        f"simple language, using ONLY the numbers below. 3-5 sentences max. End "
        f"with one short sentence noting this is statistical interpretation, not "
        f"financial advice.\n\nLive terminal readout:\n{ctx}\n\n"
        f"Question: {question}"
    )
    return _cached_completion(key, 900, prompt, 400)


def sentiment(asset: str) -> dict:
    """One consolidated call: overall sentiment + per-headline macro tilt.
    Returns {overall, impacts, items}; {raw} fallback if JSON parse fails."""
    ticker, name, _ = qc.resolve_ticker(asset)
    items = qc.news_items(ticker)
    if not items:
        return {"overall": None, "impacts": [], "items": []}
    block = "\n".join(f"{i}. {it['title']}" for i, it in enumerate(items))
    key = f"sent:{ticker}:{hashlib.sha1(block.encode()).hexdigest()[:10]}"
    prompt = (
        f"You are a senior market analyst. Analyze these numbered financial "
        f"headlines for {name} ({ticker}).\n\nHeadlines:\n{block}\n\n"
        f"Respond with ONLY a JSON object, no markdown fences, no preamble, in "
        f"exactly this shape:\n"
        f'{{"overall": {{"sentiment": "Bullish|Bearish|Neutral", "score": '
        f'<integer -10 to 10>, "summary": "<2 sentences on short-term price '
        f'direction>"}}, "impacts": [{{"i": <headline number>, "tilt": '
        f'"bullish|bearish|neutral", "impact": "<one sentence: the macro effect '
        f'of this headline on {name}>"}}]}}\n\n'
        f"Include one impacts entry per headline. Be concise and direct."
    )
    text = _cached_completion(key, 1800, prompt, 900)
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        parsed["items"] = items
        return parsed
    except Exception:
        return {"raw": text, "items": items, "overall": None, "impacts": []}


def validate(asset: str, entry: float, side: str | None = None) -> dict:
    """Rules decide, AI narrates. The verdict comes from analytics.validate_rules
    and the model is instructed that it CANNOT be softened or overridden."""
    from api import analytics
    r = analytics.validate_rules(asset, entry, side)
    snap = analytics.structure_snapshot(r["ticker"])
    b = r["bias"]
    candles = "\n".join(
        f"  {c['date']}: O {c['open']} H {c['high']} L {c['low']} C {c['close']} (z {c['z']:+.2f})"
        for c in snap["candles"])
    payload = (
        f"Proposed trade: {r['side'].upper()} {r['asset']} @ ${entry:,.2f} (spot ${b['price']:,.2f})\n"
        f"Rule verdict (FINAL, computed by the engine): {r['verdict']}\n"
        f"Rule reasons: {'; '.join(r['reasons'])}\n"
        f"Last 3 candles:\n{candles}\n"
        f"Z trajectory: {snap['z_trajectory']}\n"
        f"Band width {snap['band_width_pct']}% | compression {snap['compression_ratio']} ({snap['compression_label']})\n"
        f"Levels — Arm ${b['arm_level']:,.2f} | Invalidation ${b['invalidation']:,.2f} | Target ${b['target']:,.2f} | {b['trend']}"
    )
    key = f"valid:{r['ticker']}:{round(entry,2)}:{r['side']}:{round(b['price'],0)}"
    prompt = (
        "You are a quantitative structural analyst. Using ONLY the data below, write EXACTLY "
        "three bullets, each starting with the bold label and <= 18 words:\n"
        "• **Market State** — ...\n• **Momentum** — ...\n• **Structural Bands** — ...\n"
        f"Then a final line, verbatim format: **STRUCTURALLY {r['verdict']}** — <one short clause "
        f"from the rule reasons>. The verdict word MUST be {r['verdict']}; do not soften, hedge, or "
        "override it.\n\n" + payload
    )
    text = _cached_completion(key, 600, prompt, 350)
    return {"verdict": r["verdict"], "side": r["side"], "reasons": r["reasons"],
            "asset": r["asset"], "entry": entry, "analysis": text}
