"""
api/analytics.py — Phase 5: the high-alpha layer.

All NEW math lives here. quant_core.py and signal_engine.py are law and
remain untouched. Entry-condition logic mirrors the backtest engine's
rules exactly (documented inline) — any future change to those rules
must be made in both places or, better, refactored into quant_core.
"""
import math
import os
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

import quant_core as qc

# ── Edge thresholds (env-tunable) ────────────────────────────
EDGE_WIN_RATE = float(os.getenv("EDGE_WIN_RATE", "0.65"))
EDGE_MIN_N = int(os.getenv("EDGE_MIN_N", "15"))
RISK_BUDGET_PCT = 3.5          # max entry→invalidation distance for VALID
EXHAUSTION_Z = 2.5             # extreme-zone threshold


# ── Shared computations ──────────────────────────────────────
def _sigma_z(row):
    """Per-row z using the band geometry: Upper = Baseline + 2σ."""
    sigma = (row["Upper_Band"] - row["Baseline"]) / 2.0
    if sigma <= 0 or math.isnan(sigma):
        return 0.0
    return float((row["Price"] - row["Baseline"]) / sigma)


def _rsi_series(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def atr(ticker: str, period: int = 14) -> float:
    df = qc.fetch_history(ticker)
    prev_close = df["Price"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    val = tr.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    return round(float(val), 4)


def structure_snapshot(ticker: str, days: int = 3) -> dict:
    """Last-N candles + z trajectory + band compression state."""
    df = qc.fetch_history(ticker).dropna(
        subset=["Baseline", "Upper_Band", "Lower_Band", "Macro_Filter"])
    tail = df.tail(max(days, 2))
    candles = [{
        "date": idx.strftime("%Y-%m-%d"),
        "open": round(float(r["Open"]), 2), "high": round(float(r["High"]), 2),
        "low": round(float(r["Low"]), 2), "close": round(float(r["Price"]), 2),
        "z": round(_sigma_z(r), 2),
    } for idx, r in tail.iterrows()]

    bw = (df["Upper_Band"] - df["Lower_Band"]) / df["Baseline"]
    bw_now, bw_avg = float(bw.iloc[-1]), float(bw.tail(60).mean())
    compression = round(bw_now / bw_avg, 2) if bw_avg else 1.0
    return {
        "candles": candles,
        "z_trajectory": [c["z"] for c in candles],
        "band_width_pct": round(bw_now * 100, 2),
        "compression_ratio": compression,   # <1 = squeezing, >1 = expanded
        "compression_label": ("SQUEEZE" if compression < 0.75 else
                              "EXPANDED" if compression > 1.25 else "NORMAL"),
    }


def _signals_today(ticker: str) -> dict:
    """Which strategies fire on the LATEST close. Mirrors the backtest
    engine's entry rules exactly (see quant_core._run_backtest)."""
    df = qc.fetch_history(ticker).dropna(
        subset=["Baseline", "Upper_Band", "Lower_Band", "Macro_Filter"])
    row = df.iloc[-1]
    close, lower, upper, macro_v = (float(row["Price"]), float(row["Lower_Band"]),
                                    float(row["Upper_Band"]), float(row["Macro_Filter"]))
    rsi_v = float(_rsi_series(df["Price"]).iloc[-1])
    out = {}
    out["meanrev"] = ("long" if (close < lower and close > macro_v) else
                      "short" if (close > upper and close < macro_v) else None)
    out["breakout"] = ("long" if (close > upper and close > macro_v) else
                       "short" if (close < lower and close < macro_v) else None)
    out["rsi"] = ("long" if (rsi_v < 30 and close > macro_v) else
                  "short" if (rsi_v > 70 and close < macro_v) else None)
    sigma = (upper - float(row["Baseline"])) / 2.0
    z_v = (close - float(row["Baseline"])) / sigma if sigma > 0 else 0.0
    d = df["Price"].diff()
    g2 = d.clip(lower=0).ewm(alpha=1/2, adjust=False).mean()
    l2 = (-d.clip(upper=0)).ewm(alpha=1/2, adjust=False).mean()
    rsi2_v = float((100 - 100 / (1 + g2 / l2.replace(0, np.nan))).iloc[-1])
    out["pullback"] = ("long" if (z_v <= -0.75 and close > macro_v) else
                       "short" if (z_v >= 0.75 and close < macro_v) else None)
    out["rsi2"] = ("long" if (rsi2_v < 10 and close > macro_v) else
                   "short" if (rsi2_v > 90 and close < macro_v) else None)
    return out


# ── 1) MULTI-STRATEGY ALPHA OPTIMIZER ────────────────────────
def optimized_edge(asset: str) -> dict:
    """A candidate edge = a strategy that is (a) signaling on today's
    structure AND (b) carries a 5-YEAR win rate >= EDGE_WIN_RATE with
    >= EDGE_MIN_N trades and positive expectancy in that direction.
    The last-30-day window is reported as REGIME CONTEXT only — 21
    daily bars cannot statistically validate anything."""
    ticker, name, _ = qc.resolve_ticker(asset)
    today = _signals_today(ticker)
    candidates, scanned = [], []
    for key, meta in qc.STRATEGIES.items():
        side = today.get(key)
        _, stats = qc.run_backtest(ticker, key)
        v = qc.viability(stats)
        d = stats.get(side or "all", stats["all"])
        wr, n = d["win_rate"], d["n"]
        expectancy = wr * d["avg_win"] + (1 - wr) * d["avg_loss"]
        rec = {"strategy": key, "name": meta["name"], "signal_today": side,
               "win_rate_5y": round(wr, 4), "trades_5y": n,
               "expectancy_pct": round(expectancy * 100, 2),
               "viability": v["verdict"]}
        scanned.append(rec)
        if side and n >= EDGE_MIN_N and wr >= EDGE_WIN_RATE and expectancy > 0:
            candidates.append(rec)

    # Regime context (informational, never validation)
    df = qc.fetch_history(ticker).dropna(subset=["Baseline", "Upper_Band", "Lower_Band"])
    last30 = df.tail(30)
    zs = [_sigma_z(r) for _, r in last30.iterrows()]
    breaks = sum(1 for z in zs if abs(z) >= 2)
    drift = float(last30["Price"].iloc[-1] / last30["Price"].iloc[0] - 1)
    regime = {
        "window_days": len(last30),
        "band_breaks": breaks,
        "drift_pct": round(drift * 100, 2),
        "label": ("TRENDING" if abs(drift) > 0.06 and breaks >= 4 else
                  "CHOPPY" if breaks <= 2 else "MIXED"),
        "note": "Context only — 30 daily bars cannot statistically validate a strategy.",
    }
    return {
        "asset": name, "ticker": ticker,
        "flag": "EDGE_FOUND" if candidates else "NO_EDGE",
        "candidates": candidates,
        "scanned": scanned,
        "regime": regime,
        "thresholds": {"win_rate": EDGE_WIN_RATE, "min_trades": EDGE_MIN_N},
    }


# ── 2) MACRO RISK RADAR ──────────────────────────────────────
_HIGH_IMPACT_KEYS = ("CPI", "PPI", "FOMC", "FED", "NONFARM", "NFP",
                     "RATE", "GDP", "UNEMPLOYMENT", "POWELL")


def macro_radar(window_hours: float = 3.0) -> dict:
    """Today's USD high-impact events with a live countdown. The frontend
    hijacks the ticker tape when hijack=True."""
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except Exception:
        et = timezone.utc
    now = datetime.now(et)
    hits = []
    for e in qc.macro_calendar():
        if e.get("currency") != "USD" or not e.get("upcoming"):
            continue
        title = str(e.get("event", "")).upper()
        if not any(k in title for k in _HIGH_IMPACT_KEYS):
            continue
        # time_et format: "Tue 02:00 PM". NOTE: strptime IGNORES %a for
        # date math (bare parse lands on 1900-01-01, a Monday) — so the
        # weekday must be resolved explicitly from the token.
        try:
            parts = e["time_et"].split()
            wd = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
                  "Fri": 4, "Sat": 5, "Sun": 6}[parts[0]]
            t = datetime.strptime(" ".join(parts[1:]), "%I:%M %p")
            days_ahead = (wd - now.weekday()) % 7
            event_dt = (now + timedelta(days=days_ahead)).replace(
                hour=t.hour, minute=t.minute, second=0, microsecond=0)
        except Exception:
            continue
        seconds = (event_dt - now).total_seconds()
        if seconds < -1800:   # released >30m ago — radar off for it
            continue
        hits.append({
            "event": e["event"], "time_et": e["time_et"],
            "seconds_remaining": int(seconds),
            "minutes_remaining": int(seconds // 60),
        })
    hits.sort(key=lambda x: x["seconds_remaining"])
    nearest = hits[0] if hits else None
    hijack = bool(nearest and 0 <= nearest["seconds_remaining"] <= window_hours * 3600)
    return {"hijack": hijack, "nearest": nearest, "events_today": hits,
            "window_hours": window_hours}


# ── 3) STRUCTURAL VALIDATION — rules decide, AI narrates ────
def validate_rules(asset: str, entry: float, side: str | None = None) -> dict:
    ticker, name, unit = qc.resolve_ticker(asset)
    b = qc.get_bias(ticker)
    engine_dir = b.get("direction")
    side = (side or engine_dir or ("long" if entry <= b["price"] else "short")).lower()

    reasons, verdict = [], "VALID"
    if engine_dir is None:
        verdict = "INVALID"
        reasons.append("no armed statistical edge — price is inside equilibrium or fighting the HTF trend")
    elif side != engine_dir:
        verdict = "INVALID"
        reasons.append(f"proposed {side.upper()} fights the engine's armed {engine_dir.upper()} setup")
    else:
        risk_pct = abs(entry - b["invalidation"]) / entry * 100
        if risk_pct > RISK_BUDGET_PCT:
            verdict = "INVALID"
            reasons.append(f"entry→invalidation risk {risk_pct:.1f}% exceeds the {RISK_BUDGET_PCT}% budget")
        if (side == "long" and entry >= b["target"]) or (side == "short" and entry <= b["target"]):
            verdict = "INVALID"
            reasons.append("entry is at/past the reversion target — the move is already spent")
    if verdict == "VALID":
        reasons.append("side matches the armed edge and risk sits inside the structural budget")
    return {"asset": name, "ticker": ticker, "unit": unit, "entry": entry,
            "side": side, "verdict": verdict, "reasons": reasons, "bias": b}


# ── 4) THETA SHIELD ──────────────────────────────────────────
def theta_shield(positions: dict | None = None) -> list:
    """Volatility-adjusted time horizon per position. Horizon = days the
    ATR needs to cover the distance to target (×1.5 buffer), capped by
    80% of days-to-expiry and any explicit time_stop. Pass positions to
    scope per-user; defaults to the operator's book."""
    out = []
    today = date.today()
    for pid, p in (positions if positions is not None else qc.load_positions()).items():
        rec = {"id": pid, **p}
        try:
            ticker, _, _ = qc.resolve_ticker(str(p.get("asset", "")))
            b = qc.get_bias(ticker)
            a = atr(ticker)
            dist = abs(b["price"] - b["target"])
            horizon = max(2.0, math.ceil((dist / a) * 1.5)) if a > 0 else None

            caps = []
            try:
                exp = datetime.strptime(p["expiration"], "%Y-%m-%d").date()
                caps.append(max((exp - today).days, 0) * 0.8)
            except Exception:
                pass
            try:
                ts = datetime.strptime(p["time_stop"], "%Y-%m-%d").date()
                entry_d = datetime.strptime(p.get("entry_date", ""), "%Y-%m-%d").date()
                caps.append((ts - entry_d).days)
            except Exception:
                pass
            if horizon is not None and caps:
                horizon = min([horizon] + [c for c in caps if c and c > 0])

            entry_date = p.get("entry_date")
            if entry_date and horizon:
                elapsed = (today - datetime.strptime(entry_date, "%Y-%m-%d").date()).days
                pct = round(min(elapsed / horizon, 1.5) * 100, 1)
                status = ("CUT" if pct >= 100 else
                          "WARN_80" if pct >= 80 else "OK")
            else:
                elapsed, pct = None, None
                status = "NO_ENTRY_DATE" if not entry_date else "NO_HORIZON"
            rec["shield"] = {
                "atr": a, "spot": b["price"], "target": b["target"],
                "horizon_days": horizon, "elapsed_days": elapsed,
                "pct_exhausted": pct, "status": status,
            }
            ed = qc.get_next_earnings(ticker)
            rec["earnings"] = {"date": ed,
                               "before_expiry": bool(ed and p.get("expiration")
                                                     and ed <= p["expiration"])}
            # ── Live PnL: REAL option premium only. Never spot-derived. ──
            entry_prem = p.get("entry_premium") or p.get("entry")
            live = None
            if entry_prem and p.get("expiration") and p.get("strike") and p.get("type"):
                live = qc.get_option_premium(ticker, p["expiration"],
                                             float(p["strike"]), p["type"])
            if live and entry_prem:
                rec["pnl"] = {"live_premium": round(live, 2),
                              "entry_premium": round(float(entry_prem), 2),
                              "pnl_pct": round((live - float(entry_prem)) / float(entry_prem) * 100, 2),
                              "source": "option_chain"}
            else:
                rec["pnl"] = {"live_premium": None, "entry_premium": entry_prem,
                              "pnl_pct": None, "source": None,
                              "note": "Option chain unreachable — PnL unavailable (never estimated from spot)."}
        except Exception:
            rec["shield"] = {"status": "DATA_ERROR"}
        out.append(rec)
    return out


# ── 5) EXHAUSTION DETECTION ──────────────────────────────────
def exhaustion_state(ticker: str) -> dict:
    """Extreme-zone thrust (|z| >= 2.5) PLUS deceleration — z fading from
    yesterday's extreme or RSI rolling back through its extreme band.
    A raw band touch alone is NOT exhaustion (it fires on every strong
    trend day); the decel pairing is what marks a spent thrust."""
    df = qc.fetch_history(ticker).dropna(
        subset=["Baseline", "Upper_Band", "Lower_Band"])
    if len(df) < 3:
        return {"triggered": False}
    z1 = _sigma_z(df.iloc[-1])
    z2 = _sigma_z(df.iloc[-2])
    rsi = _rsi_series(df["Price"])
    r1, r2 = float(rsi.iloc[-1]), float(rsi.iloc[-2])
    price = round(float(df["Price"].iloc[-1]), 2)

    side = None
    if max(z1, z2) >= EXHAUSTION_Z:
        side = "upside"
        decel = (z1 < z2) or (r2 > 70 and r1 < r2)
    elif min(z1, z2) <= -EXHAUSTION_Z:
        side = "downside"
        decel = (z1 > z2) or (r2 < 30 and r1 > r2)
    else:
        decel = False
    return {"triggered": bool(side and decel), "side": side,
            "z": round(z1, 2), "z_prev": round(z2, 2),
            "rsi": round(r1, 1), "price": price}


# ── 6) STRATEGY LAB — walk-forward validation, per-asset assignment ─
LAB_SPLIT = 0.70            # optimize on first 70%, verdict on last 30% ONLY
LAB_MIN_TEST_TRADES = 10
LAB_MIN_WIN_RATE = 0.55
LAB_MIN_PF = 1.3
LAB_MIN_TRAIN_PF = 1.1      # consistency: train can't have been a loser


def _segment_stats(stats, seg_days):
    s = stats["all"]
    wr, aw, al, n = s["win_rate"], s["avg_win"], s["avg_loss"], s["n"]
    exp = wr * aw + (1 - wr) * al
    gl = abs((1 - wr) * al)
    pf = (wr * aw / gl) if gl > 0 else (float("inf") if wr * aw > 0 else 0.0)
    return {
        "n": n, "win_rate": round(wr, 4),
        "profit_factor": None if pf == float("inf") else round(pf, 2),
        "expectancy_pct": round(exp * 100, 2),
        "return_pct": round(stats["strategy_return"] * 100, 2),
        "max_dd_pct": round(stats["max_drawdown"] * 100, 2),
        "signals_per_week": round(n / max(seg_days / 7.0, 1), 2),
    }


def walk_forward(ticker: str, strategy: str) -> dict:
    df = qc.fetch_history(ticker).dropna(
        subset=["Baseline", "Upper_Band", "Lower_Band", "Macro_Filter"])
    i = int(len(df) * LAB_SPLIT)
    train_df, test_df = df.iloc[:i], df.iloc[i:]
    _, tr = qc._run_backtest(ticker, strategy, df=train_df)
    _, te = qc._run_backtest(ticker, strategy, df=test_df)
    tr_days = max((train_df.index[-1] - train_df.index[0]).days, 1)
    te_days = max((test_df.index[-1] - test_df.index[0]).days, 1)
    train, test = _segment_stats(tr, tr_days), _segment_stats(te, te_days)

    reasons = []
    if test["n"] < LAB_MIN_TEST_TRADES:
        reasons.append(f"only {test['n']} out-of-sample trades (< {LAB_MIN_TEST_TRADES})")
    if test["win_rate"] < LAB_MIN_WIN_RATE:
        reasons.append(f"OOS win rate {test['win_rate']*100:.0f}% < {LAB_MIN_WIN_RATE*100:.0f}%")
    pf_t = test["profit_factor"] if test["profit_factor"] is not None else 99
    if pf_t < LAB_MIN_PF:
        reasons.append(f"OOS profit factor {pf_t} < {LAB_MIN_PF}")
    if test["expectancy_pct"] <= 0:
        reasons.append("OOS expectancy is not positive")
    pf_tr = train["profit_factor"] if train["profit_factor"] is not None else 99
    if pf_tr < LAB_MIN_TRAIN_PF:
        reasons.append("in-sample segment was itself a loser (inconsistent)")

    return {"strategy": strategy, "name": qc.STRATEGIES[strategy]["name"],
            "train": train, "test": test,
            "validated": not reasons,
            "fail_reasons": reasons}


def strategy_lab(asset: str) -> dict:
    """Every strategy family, walk-forward validated. The 'assigned'
    strategy is the ONE per asset: best out-of-sample expectancy among
    the validated. NOTHING_VALIDATED is a protective verdict, not a bug."""
    ticker, name, _ = qc.resolve_ticker(asset)
    results = [walk_forward(ticker, k) for k in qc.STRATEGIES]
    validated = [r for r in results if r["validated"]]
    validated.sort(key=lambda r: r["test"]["expectancy_pct"], reverse=True)
    assigned = validated[0] if validated else None
    return {
        "asset": name, "ticker": ticker,
        "flag": "STRATEGY_ASSIGNED" if assigned else "NOTHING_VALIDATED",
        "assigned": assigned,
        "results": results,
        "criteria": {"split": LAB_SPLIT, "min_test_trades": LAB_MIN_TEST_TRADES,
                     "min_win_rate": LAB_MIN_WIN_RATE, "min_profit_factor": LAB_MIN_PF},
        "note": ("Verdicts are rendered on the held-out final 30% of history only \u2014 "
                 "a strategy that only wins on the data it was tuned on is a mirage."),
    }


# ── 7) PLAYBOOK + SCAN ───────────────────────────────────────
def load_playbook() -> dict:
    """assignments keyed UPPER by display name AND ticker for easy lookup.
    DB rows (redeploy-proof) take precedence; playbook.json is fallback."""
    try:
        from api import store as _store
        db_assignments = _store.get_playbook_assignments()
    except Exception:
        db_assignments = None
    try:
        if db_assignments is not None:
            assignments = db_assignments
        else:
            with open("playbook.json") as f:
                assignments = (json.load(f).get("assignments") or {})
        out = {}
        for key, a in assignments.items():
            ticker, name, _ = qc.resolve_ticker(key)
            rec = {"key": key, "strategy": a.get("strategy"),
                   "strategy_name": a.get("name"), "assigned_at": a.get("assigned_at")}
            out[key.upper()] = rec
            out[ticker.upper()] = rec
        return out
    except Exception:
        return {}


# ── 11) PLAYBOOK EXPANSION — lab the whole book, same thresholds ──
def lab_book(progress=None, budget_s: float | None = None) -> dict:
    """Run the Strategy Lab across every UNASSIGNED watchlist asset.
    Assigned names are never re-labbed (stability rule: assignments stand
    >= 1 month). Thresholds untouched — coverage grows, the bar doesn't move.
    New assignments persist to DB (redeploy-proof) + playbook.json."""
    import os as _os
    import time as _t
    from datetime import date as _date
    from api import store as _store
    budget = budget_s if budget_s is not None else float(_os.getenv("LABBOOK_BUDGET_S", "480"))
    deadline = _t.monotonic() + budget
    pb = load_playbook()
    new_assignments, failed = [], []
    todo = [n for n in qc.load_watchlist() if not pb.get(n.upper())]
    skipped = [n for n in qc.load_watchlist() if pb.get(n.upper())]
    ran_out = False
    for i, name in enumerate(todo):
        if _t.monotonic() > deadline:
            ran_out = True
            break
        if progress and i and i % 6 == 0:
            try:
                progress(f"\U0001F9EA {i}/{len(todo)} labbed \u2014 still working\u2026")
            except Exception:
                pass
        try:
            lab = strategy_lab(name)
        except Exception:
            failed.append({"asset": name, "reason": "lab error (feed?)"})
            continue
        if lab["flag"] == "STRATEGY_ASSIGNED":
            a = lab["assigned"]
            rec = {"asset": name, "strategy": a["strategy"],
                   "strategy_name": a["name"], "test": a["test"]}
            new_assignments.append(rec)
            today = _date.today().isoformat()
            _store.save_playbook_assignment(name, a["strategy"], a["name"],
                                            today, a["test"])
            try:
                with open("playbook.json") as f:
                    fpb = json.load(f)
            except Exception:
                fpb = {"assignments": {}}
            fpb.setdefault("assignments", {})[name] = {
                "strategy": a["strategy"], "name": a["name"], "assigned_at": today}
            with open("playbook.json", "w") as f:
                json.dump(fpb, f, indent=2)
        else:
            top = max(lab["results"],
                      key=lambda r: r["test"]["expectancy_pct"]) if lab["results"] else None
            failed.append({"asset": name,
                           "reason": (top["fail_reasons"][0] if top and top["fail_reasons"]
                                      else "nothing validated")})
    total_spw = 0.0
    for rec in load_playbook().values():
        pass  # keys are duplicated per asset; compute below from new list only
    return {"new_assignments": new_assignments, "nothing_validated": failed,
            "already_assigned": sorted(set(skipped)), "ran_out_of_time": ran_out,
            "expected_new_signals_per_week": round(
                sum(r["test"].get("signals_per_week") or 0 for r in new_assignments), 2)}


def assignment_for(asset: str):
    ticker, name, _ = qc.resolve_ticker(asset)
    pb = load_playbook()
    return pb.get(name.upper()) or pb.get(ticker.upper()) or pb.get(asset.upper())


def scan_playbook() -> list:
    """The Monday-morning command: which ASSIGNED strategies are firing
    on the current close? Returns only live hits."""
    hits, seen = [], set()
    pb = load_playbook()
    for rec in pb.values():
        if rec["key"] in seen:
            continue
        seen.add(rec["key"])
        try:
            ticker, name, unit = qc.resolve_ticker(rec["key"])
            side = _signals_today(ticker).get(rec["strategy"])
            if side:
                q = qc.get_quote(ticker) or {}
                hits.append({"asset": name, "ticker": ticker,
                             "strategy": rec["strategy"],
                             "strategy_name": rec["strategy_name"],
                             "side": side, "price": q.get("price")})
        except Exception:
            continue
    return hits


import json  # (idempotent; used above)


# ── 8) PLAIN-HONEST TRANSLATOR ───────────────────────────────
#     Rubber-band metaphors: yes. Jargon: no. Promises: NEVER —
#     history is phrased as history, not prediction.
STRATEGY_PLAIN = {
    "meanrev": "buy-the-dip / fade-the-spike at extreme stretch",
    "breakout": "ride the breakout with the bigger trend",
    "rsi": "buy washouts / fade blowoffs (momentum gauge)",
    "pullback": "buy shallow dips inside an uptrend",
    "rsi2": "fast snap-back after a sharp washout",
}


def plain_state(b: dict):
    """(emoji, headline, action_line) in everyday language, numbers kept."""
    state = b.get("state", "")
    if "LONG-REVERSION ARMED" in state:
        return ("🟢",
                "Buy-the-dip setup is LIVE — price is stretched unusually far "
                "below its average while the bigger trend still points up.",
                f"Zone: near ${b['arm_level']:,.2f} · Wrong if it closes past "
                f"${b['invalidation']:,.2f} · Target back around ${b['target']:,.2f}")
    if "SHORT-REVERSION ARMED" in state:
        return ("🔴",
                "Fade-the-spike setup is LIVE — price is stretched unusually far "
                "above its average while the bigger trend points down.",
                f"Zone: near ${b['arm_level']:,.2f} · Wrong if it closes past "
                f"${b['invalidation']:,.2f} · Target back around ${b['target']:,.2f}")
    if "WATCH" in state:
        return ("👀",
                "Getting interesting — price is drifting toward the edge of its "
                "normal range. Not a setup yet; worth watching.",
                f"A setup would trigger near ${b['arm_level']:,.2f}")
    return ("😴",
            "No setup — price is inside its normal range. Nothing statistically "
            "interesting here. Waiting IS the move.",
            f"Nearest level worth watching: ${b['arm_level']:,.2f} "
            f"({b['dist_to_arm_pct']:+.1f}% away)")


# ── 9) CHART CARD RENDERER — dark, 30 candles, level overlays ──
CHART_TOKENS = {"bg": "#0B0E14", "panel": "#10141F", "grid": "#1E2635",
                "up": "#2FBF71", "down": "#E4574C", "text": "#C7CEDB",
                "entry": "#39FF14", "stop": "#E4574C", "target": "#4DA6FF"}


def render_chart_card(ticker: str, title: str, entry: float | None = None,
                      stop: float | None = None, target: float | None = None,
                      bars: int = 30) -> bytes:
    """PNG bytes: last-N candles on charcoal with entry/stop/target lines."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = qc.fetch_history(ticker).tail(bars)
    T = CHART_TOKENS
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=150)
    fig.patch.set_facecolor(T["bg"]); ax.set_facecolor(T["panel"])

    xs = range(len(df))
    for i, (_, r) in enumerate(df.iterrows()):
        up = r["Price"] >= r["Open"]
        c = T["up"] if up else T["down"]
        ax.vlines(i, r["Low"], r["High"], color=c, linewidth=1)
        lo, hi = sorted([r["Open"], r["Price"]])
        ax.add_patch(plt.Rectangle((i - .32, lo), .64, max(hi - lo, 1e-9),
                                   facecolor=c, edgecolor=c, linewidth=.5))
    for level, key, label in ((entry, "entry", "ENTRY ZONE"),
                              (stop, "stop", "INVALIDATION"),
                              (target, "target", "TAKE PROFIT")):
        if level:
            ax.axhline(level, color=T[key], linewidth=1.6,
                       linestyle="-" if key != "entry" else "--")
            ax.text(len(df) - .5, level, f" {label} ${level:,.2f}",
                    color=T[key], fontsize=7.5, va="bottom", ha="right",
                    fontweight="bold")
    ax.set_title(title, color=T["text"], fontsize=11, fontweight="bold",
                 loc="left", pad=10)
    ax.grid(color=T["grid"], linewidth=.5, alpha=.6)
    ax.tick_params(colors=T["text"], labelsize=7)
    for s in ax.spines.values():
        s.set_color(T["grid"])
    ax.set_xlim(-1, len(df))
    ax.set_xticks([])
    fig.tight_layout()
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=T["bg"])
    plt.close(fig)
    return buf.getvalue()


# ── 10) CANDIDATES — breadth scan of the fast families, UNVALIDATED ──
def candidates() -> list:
    """On-demand velocity scan across the whole watchlist for the fast
    families (pullback, rsi2). Explicitly UNVALIDATED: leads for /lab,
    never signals. Thread-safe 12s deadline (signal alarms crash in a
    threadpool): returns partial results instead of hanging."""
    import time as _t
    deadline = _t.monotonic() + float(os.getenv("CANDIDATES_BUDGET_S", "12"))
    out, truncated = [], False
    for name, d in qc.load_watchlist().items():
        if _t.monotonic() > deadline:
            truncated = True
            break
        try:
            sig = _signals_today(d["ticker"])
        except Exception:
            continue
        for fam in ("pullback", "rsi2"):
            side = sig.get(fam)
            if side:
                q = qc.get_quote(d["ticker"]) or {}
                out.append({"asset": name, "ticker": d["ticker"], "family": fam,
                            "family_name": qc.STRATEGIES[fam]["name"],
                            "side": side, "price": q.get("price"),
                            "validated": bool(assignment_for(name) and
                                              assignment_for(name)["strategy"] == fam)})
    if truncated and out:
        out[-1]["scan_truncated"] = True
    return out
