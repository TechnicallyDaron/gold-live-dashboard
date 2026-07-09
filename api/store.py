"""
N-CORE — data access layer. ONE rule: when Supabase is configured, the
DATABASE is the source of truth; JSON files are seed/fallback only.
Every function takes user_id; single-operator mode uses OPERATOR_USER_ID.
Atomicity note (honest): close_position performs journal-insert THEN
position-update sequentially; a crash between them leaves a journal entry
with an open position (safe: re-close is idempotent-ish), never a lost trade.
"""
import json
import os
from datetime import datetime, timezone

from . import db

OPERATOR = os.getenv("OPERATOR_USER_ID", "")  # your auth.users uuid


def resolve_user(user: dict | None) -> str | None:
    """uuid when DB mode; None → file mode."""
    if not db.enabled():
        return None
    if user and user.get("id") and user.get("mode") != "file-fallback":
        return user["id"]
    return OPERATOR or None


# ── WATCHLIST ────────────────────────────────────────────────
def get_watchlist(user_id: str | None) -> dict:
    """DB mode: the user's rows are the truth — an empty watchlist is EMPTY,
    never silently backfilled with someone else's book. File fallback exists
    only when the database itself is unconfigured."""
    if user_id:
        rows = db.select("watchlists", {"user_id": user_id},
                         order="priority.asc,id.asc")
        return {r["display_name"]: {"ticker": r["ticker"], "name": r["display_name"],
                                    "unit": r.get("unit") or "/sh"} for r in rows}
    with open("watchlist.json") as f:
        return json.load(f)


def add_watchlist(user_id: str | None, name: str, ticker: str, unit: str) -> None:
    if user_id:
        db.insert("watchlists", {"user_id": user_id, "display_name": name,
                                 "ticker": ticker, "unit": unit})
        return
    wl = get_watchlist(None)
    wl[name] = {"ticker": ticker, "name": name, "unit": unit}
    with open("watchlist.json", "w") as f:
        json.dump(wl, f, indent=2)


def remove_watchlist(user_id: str | None, name: str) -> None:
    if user_id:
        db.delete("watchlists", {"user_id": user_id, "display_name": name})
        return
    wl = get_watchlist(None)
    wl.pop(name, None)
    with open("watchlist.json", "w") as f:
        json.dump(wl, f, indent=2)


# ── POSITIONS ────────────────────────────────────────────────
def get_positions(user_id: str | None) -> dict:
    if user_id:
        rows = db.select("positions", {"user_id": user_id, "status": "open"},
                         order="id.asc")
        out = {}
        for r in rows:
            out[str(r["id"])] = {
                "asset": r["asset"], "ticker": r.get("ticker") or r["asset"],
                "type": r["contract_type"], "strike": float(r["strike"]),
                "entry_premium": float(r["entry_premium"]),
                "entry_date": r["entry_date"], "expiration": r["expiration"],
                "premium_stop": r.get("premium_stop"),
                "time_stop": r.get("time_stop"),
                "invalidation_above": r.get("invalidation_above"),
                "invalidation_below": r.get("invalidation_below"),
            }
        return out
    with open("positions.json") as f:
        return json.load(f)


def add_position(user_id: str | None, rec: dict) -> str:
    if user_id:
        row = db.insert("positions", {
            "user_id": user_id, "asset": rec["asset"],
            "contract_type": rec["type"], "strike": rec["strike"],
            "entry_premium": rec["entry_premium"], "entry_date": rec["entry_date"],
            "expiration": rec["expiration"], "premium_stop": rec.get("premium_stop"),
            "time_stop": rec.get("time_stop"),
            "invalidation_above": rec.get("invalidation_above"),
            "invalidation_below": rec.get("invalidation_below"),
        })[0]
        return str(row["id"])
    import time as _t
    pid = f"{rec['asset'].lower()}_{rec['type']}_{int(_t.time())}"
    pos = get_positions(None)
    pos[pid] = rec
    with open("positions.json", "w") as f:
        json.dump(pos, f, indent=2)
    return pid


def close_position(user_id: str | None, pid: str, journal_entry: dict) -> None:
    """Journal write FIRST (the record is what matters), then position update."""
    if user_id:
        je = dict(journal_entry)
        je["user_id"] = user_id
        je.pop("id", None)
        je["contract_type"] = je.pop("type", None)   # column-name mapping
        db.insert("journal", je)
        db.update("positions", {"user_id": user_id, "id": pid},
                  {"status": "closed"})
        return
    j = get_journal(None)
    j.append(journal_entry)
    with open("journal.json", "w") as f:
        json.dump(j, f, indent=2)
    pos = get_positions(None)
    pos.pop(pid, None)
    with open("positions.json", "w") as f:
        json.dump(pos, f, indent=2)


# ── JOURNAL ──────────────────────────────────────────────────
def get_journal(user_id: str | None) -> list:
    if user_id:
        rows = db.select("journal", {"user_id": user_id}, order="logged_at.asc")
        for r in rows:
            r.pop("user_id", None)
        return rows
    try:
        with open("journal.json") as f:
            return json.load(f)
    except Exception:
        return []


# ── COOLDOWNS (restart-proof alert dedupe) ───────────────────
_mem_cooldowns: dict = {}


def cooldown_active(key: str) -> bool:
    now = datetime.now(timezone.utc)
    if db.enabled():
        try:
            rows = db.select("cooldowns", {"key": key}, limit=1)
            if rows:
                until = datetime.fromisoformat(rows[0]["until_ts"].replace("Z", "+00:00"))
                return until > now
            return False
        except Exception:
            pass  # DB hiccup → fall through to memory (fail-open, deduped in-session)
    until = _mem_cooldowns.get(key)
    return bool(until and until > now)


def cooldown_set(key: str, hours: float) -> None:
    from datetime import timedelta
    until = datetime.now(timezone.utc) + timedelta(hours=hours)
    _mem_cooldowns[key] = until
    if db.enabled():
        try:
            db.upsert("cooldowns", {"key": key, "until_ts": until.strftime("%Y-%m-%dT%H:%M:%SZ")},
                      on_conflict="key")
        except Exception:
            pass


# ── SCREENER RESULTS ─────────────────────────────────────────
def save_screener(scan_date: str, hits: list) -> None:
    if db.enabled():
        try:
            db.delete("screener_results", {"scan_date": scan_date})
            if hits:
                db.insert("screener_results",
                          [{"scan_date": scan_date, **h} for h in hits])
            return
        except Exception:
            pass
    with open("screener.json", "w") as f:
        json.dump({"scan_date": scan_date, "hits": hits}, f, indent=2)


def get_screener() -> dict:
    if db.enabled():
        try:
            rows = db.select("screener_results", order="scan_date.desc,rvol.desc",
                             limit=50)
            if rows:
                latest = rows[0]["scan_date"]
                hits = [r for r in rows if r["scan_date"] == latest]
                for r in hits:
                    r.pop("id", None)
                return {"scan_date": latest, "hits": hits}
        except Exception:
            pass
    try:
        with open("screener.json") as f:
            return json.load(f)
    except Exception:
        return {"scan_date": None, "hits": []}


# ── PLAYBOOK (DB rows survive redeploys; file is engine cache/fallback) ──
def get_playbook_assignments() -> dict | None:
    """{key: {strategy, name, assigned_at, stats...}} from DB, or None if
    DB disabled/empty (caller falls back to playbook.json)."""
    if not db.enabled() or not OPERATOR:
        return None
    try:
        rows = db.select("playbooks", {"user_id": OPERATOR}, order="asset_key.asc")
    except Exception:
        return None
    if not rows:
        return None
    return {r["asset_key"]: {"strategy": r["strategy"], "name": r["strategy_name"],
                             "assigned_at": r["assigned_at"]} for r in rows}


def save_playbook_assignment(key: str, strategy: str, strategy_name: str,
                             assigned_at: str, stats: dict | None = None) -> None:
    if db.enabled() and OPERATOR:
        try:
            row = {"user_id": OPERATOR, "asset_key": key, "strategy": strategy,
                   "strategy_name": strategy_name, "assigned_at": assigned_at}
            if stats:
                row.update({"oos_win_rate": stats.get("win_rate"),
                            "oos_profit_factor": stats.get("profit_factor"),
                            "oos_expectancy_pct": stats.get("expectancy_pct")})
            db.upsert("playbooks", row, on_conflict="user_id,asset_key")
        except Exception:
            pass
