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
        allowed = {"user_id", "position_id", "asset", "contract_type", "strike",
                   "entry_date", "exit_date", "entry_premium", "exit_premium",
                   "pnl_pct", "holding_days", "strategy", "strategy_name",
                   "verdict_at_close", "thesis", "rule_compliant", "notes", "logged_at"}
        je = {k: v for k, v in je.items() if k in allowed}   # Postgres rejects unknowns
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
                            "oos_expectancy_pct": stats.get("expectancy_pct"),
                            "oos_signals_per_week": stats.get("signals_per_week")})
            db.upsert("playbooks", row, on_conflict="user_id,asset_key")
        except Exception:
            pass


# ── SIGNAL LEDGER: the machine's own track record ───────────
LEDGER_FILE = "ledger.json"


def _ledger_file():
    try:
        with open(LEDGER_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def save_signal(rec: dict) -> None:
    if db.enabled():
        try:
            db.insert("signal_ledger", rec)
            return
        except Exception:
            pass
    led = _ledger_file()
    rec = dict(rec)
    rec["id"] = (max((e.get("id", 0) for e in led), default=0) + 1)
    rec["status"] = rec.get("status", "open")
    led.append(rec)
    with open(LEDGER_FILE, "w") as f:
        json.dump(led, f, indent=2)


def get_open_signals() -> list:
    if db.enabled():
        try:
            return db.select("signal_ledger", {"status": "open"})
        except Exception:
            return []
    return [e for e in _ledger_file() if e.get("status", "open") == "open"]


def resolve_signal(sid, status: str, resolved_date: str, resolve_price, result_pct) -> None:
    patch = {"status": status, "resolved_date": resolved_date,
             "resolve_price": resolve_price, "result_pct": result_pct}
    if db.enabled():
        try:
            db.update("signal_ledger", {"id": sid}, patch)
            return
        except Exception:
            pass
    led = _ledger_file()
    for e in led:
        if e.get("id") == sid:
            e.update(patch)
    with open(LEDGER_FILE, "w") as f:
        json.dump(led, f, indent=2)


def get_ledger(limit: int = 200) -> list:
    if db.enabled():
        try:
            return db.select("signal_ledger", order="fired_date.desc", limit=limit)
        except Exception:
            return []
    return list(reversed(_ledger_file()))[:limit]


def get_playbook_stats() -> list:
    """Assignments with validation stats for the frontend."""
    if db.enabled() and OPERATOR:
        try:
            rows = db.select("playbooks", {"user_id": OPERATOR},
                             order="oos_signals_per_week.desc.nullslast")
            return [{"key": r["asset_key"], "strategy": r["strategy"],
                     "strategy_name": r["strategy_name"], "assigned_at": r["assigned_at"],
                     "win_rate": r.get("oos_win_rate"),
                     "profit_factor": r.get("oos_profit_factor"),
                     "signals_per_week": r.get("oos_signals_per_week")} for r in rows]
        except Exception:
            pass
    try:
        with open("playbook.json") as f:
            pb = json.load(f).get("assignments") or {}
        return [{"key": k, "strategy": a.get("strategy"),
                 "strategy_name": a.get("name"), "assigned_at": a.get("assigned_at"),
                 "win_rate": None, "profit_factor": None, "signals_per_week": None}
                for k, a in pb.items()]
    except Exception:
        return []
