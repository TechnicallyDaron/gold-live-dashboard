"""
monitor.py — Signal monitor for the Quant Intelligence Terminal.

Run by GitHub Actions on a cron schedule (every 30 min during market hours).
Three message types, strictly separated:

1. STATE-CHANGE ALERTS (always on): fires the moment an asset's bias state
   changes (NO TRADE -> WATCH -> ARMED etc). The highest-priority signal.
2. DAILY DIGEST (once per day, first run): snapshot of every asset's state.
3. INTRADAY PULSE (every >=2h, movement-gated): reports ONLY assets that
   moved meaningfully since their last reported reference point —
   z-score shift >= 0.5, price move >= 1.0%, or a 20 EMA cross.
   Quiet markets send nothing. References accumulate, so a slow grind
   still triggers once its cumulative move crosses a threshold.

Env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (dry-run prints if missing).
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import yfinance as yf

from signal_engine import add_indicators, compute_bias

WATCHLIST_FILE = "watchlist.json"
STATE_FILE = "signal_state.json"

# ── Pulse tuning ─────────────────────────────────────────────
PULSE_INTERVAL_HOURS = 2      # minimum gap between pulse checks
PULSE_Z_DELTA = 0.5           # z-score shift that counts as movement
PULSE_PCT_DELTA = 1.0         # % price move that counts as movement
PULSE_CROSS_MIN_DZ = 0.25     # min z shift for an EMA-cross to count (kills flutter)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def _utcnow():
    return datetime.now(timezone.utc)


def fetch_data(ticker: str) -> pd.DataFrame:
    end = datetime.today()
    start = end - timedelta(days=1825)
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].astype(float).copy()
    df = df.rename(columns={"Close": "Price"})
    return add_indicators(df)


def send_telegram(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[DRY RUN — no Telegram credentials]\n" + message + "\n" + "-" * 40)
        return True
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"Telegram API error {r.status_code}: {r.text}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)
        return False


def format_alert(asset: str, unit: str, bias: dict, previous_state: str) -> str:
    lines = [
        f"<b>{bias['state']}</b> — {asset}",
        f"(was: {previous_state})",
        "",
        f"Spot: ${bias['price']:,.2f}{unit}  |  Z: {bias['z']:+.2f}",
        f"HTF Trend: {bias['trend']}",
        "",
        f"🎯 Arm level: ${bias['arm_level']:,.2f} ({bias['dist_to_arm_pct']:+.2f}%)",
        f"🛑 Invalidation: ${bias['invalidation']:,.2f}",
        f"📍 Reversion target (20 EMA): ${bias['target']:,.2f} ({bias['dist_to_target_pct']:+.2f}%)",
        "",
        "<i>Statistical state change, not financial advice. Verify before acting.</i>",
    ]
    return "\n".join(lines)


def format_digest_line(asset: str, unit: str, bias: dict) -> str:
    icon = bias["state"].split(" ")[0]
    trend = "▲" if "BULLISH" in bias["trend"] else "▼"
    return (f"{icon} <b>{asset}</b> ${bias['price']:,.2f}{unit} | "
            f"Z {bias['z']:+.2f} | HTF {trend} | "
            f"arm {bias['dist_to_arm_pct']:+.1f}% away")


def pulse_movement(bias: dict, ref: dict):
    """Return a human reason string if the asset moved meaningfully vs its
    reference point, else None."""
    dz = bias["z"] - ref["z"]
    dpct = (bias["price"] / ref["price"] - 1.0) * 100 if ref["price"] else 0.0
    reasons = []
    if abs(dz) >= PULSE_Z_DELTA:
        reasons.append(f"Z {ref['z']:+.2f} → {bias['z']:+.2f}")
    if abs(dpct) >= PULSE_PCT_DELTA:
        arrow = "▲" if dpct > 0 else "▼"
        reasons.append(f"{arrow} {dpct:+.1f}%")
    if (bias["z"] > 0) != (ref["z"] > 0) and abs(dz) >= PULSE_CROSS_MIN_DZ:
        side = "above" if bias["z"] > 0 else "below"
        reasons.append(f"crossed {side} the 20 EMA")
    return " | ".join(reasons) if reasons else None


def format_pulse_line(asset: str, unit: str, bias: dict, reason: str) -> str:
    icon = bias["state"].split(" ")[0]
    return (f"{icon} <b>{asset}</b> ${bias['price']:,.2f}{unit} — {reason}\n"
            f"    now {bias['dist_to_arm_pct']:+.1f}% from arm level (${bias['arm_level']:,.2f})")



# =====================================================================
# 🛡 POSITION GUARDIAN — enforces the exit rules you set when sober
# =====================================================================
POSITIONS_FILE = "positions.json"
TIME_STOP_WARNINGS = [3, 1, 0]      # days before your self-imposed time stop
EXPIRY_WARNINGS = [7, 3, 1, 0]      # days before contract expiration


def fetch_option_mark(ticker: str, expiration: str, strike: float, opt_type: str):
    """Best-effort live option price via the yfinance chain. Returns float or None.
    Option feeds are flaky — every caller must survive a None."""
    try:
        chain = yf.Ticker(ticker).option_chain(expiration)
        table = chain.puts if opt_type.lower() == "put" else chain.calls
        row = table[abs(table["strike"] - strike) < 0.001]
        if row.empty:
            return None
        bid = float(row["bid"].iloc[0] or 0)
        ask = float(row["ask"].iloc[0] or 0)
        last = float(row["lastPrice"].iloc[0] or 0)
        if bid > 0 and ask > 0:
            return round((bid + ask) / 2, 2)
        return last if last > 0 else None
    except Exception:
        return None


def guardian_check(meta: dict, underlying_prices: dict, now) -> int:
    """Check every logged position against its exit rules. Returns alert count.
    Dedupe: each rule fires once (date-keyed for the premium stop) via
    sent-keys stored in meta['guardian'][position_id]."""
    if not os.path.exists(POSITIONS_FILE):
        return 0
    try:
        with open(POSITIONS_FILE) as f:
            positions = json.load(f)
    except Exception as e:
        print(f"positions.json unreadable: {e}", file=sys.stderr)
        return 0

    gstate = meta.get("guardian", {})
    today = now.date()
    alerts = 0

    for pid, pos in positions.items():
        sent = set(gstate.get(pid, []))
        label = f"{pos['asset']} ${pos['strike']:.2f}{pos['type'][0].upper()} {pos['expiration']}"
        msgs = []

        # ── Date rules ───────────────────────────────────────
        try:
            exp = datetime.strptime(pos["expiration"], "%Y-%m-%d").date()
            dte = (exp - today).days
            for d in EXPIRY_WARNINGS:
                key = f"exp{d}"
                if dte == d and key not in sent:
                    when = "EXPIRES TODAY" if d == 0 else f"{d} day(s) to expiration"
                    msgs.append((key, f"⏳ {when}. All remaining premium is time value at risk."))
        except Exception:
            pass

        if pos.get("time_stop"):
            try:
                ts = datetime.strptime(pos["time_stop"], "%Y-%m-%d").date()
                dts = (ts - today).days
                for d in TIME_STOP_WARNINGS:
                    key = f"ts{d}"
                    if dts == d and key not in sent:
                        when = "is TODAY" if d == 0 else f"in {d} day(s)"
                        msgs.append((key, f"🕐 Your self-imposed TIME STOP {when}. "
                                          f"No confirmed move = your rule says salvage remaining premium."))
            except Exception:
                pass

        # ── Underlying invalidation ─────────────────────────
        u_price = underlying_prices.get(pos["ticker"])
        if u_price is None:
            try:
                q = yf.Ticker(pos["ticker"]).fast_info
                u_price = float(q["last_price"])
            except Exception:
                u_price = None
        if u_price is not None:
            if pos.get("invalidation_above") and u_price > float(pos["invalidation_above"]) and "inval" not in sent:
                msgs.append(("inval", f"❌ THESIS INVALIDATED: underlying ${u_price:,.2f} is ABOVE your "
                                      f"invalidation level ${float(pos['invalidation_above']):,.2f}. "
                                      f"Your rule: exit, don't average."))
            if pos.get("invalidation_below") and u_price < float(pos["invalidation_below"]) and "inval" not in sent:
                msgs.append(("inval", f"❌ THESIS INVALIDATED: underlying ${u_price:,.2f} is BELOW your "
                                      f"invalidation level ${float(pos['invalidation_below']):,.2f}. "
                                      f"Your rule: exit, don't average."))

        # ── Premium stop (best-effort, re-alerts daily while breached) ──
        if pos.get("premium_stop"):
            mark = fetch_option_mark(pos["ticker"], pos["expiration"], float(pos["strike"]), pos["type"])
            if mark is not None and mark <= float(pos["premium_stop"]):
                key = f"prem{today.isoformat()}"
                if key not in sent:
                    pnl = (mark - float(pos["premium_paid"])) / float(pos["premium_paid"]) * 100
                    msgs.append((key, f"🛑 PREMIUM STOP HIT: contract marks ~${mark:.2f} vs your "
                                      f"${float(pos['premium_stop']):.2f} stop ({pnl:+.0f}% vs entry). "
                                      f"Your rule: out mechanically, no renegotiation."))

        if msgs:
            body = "\n\n".join(m for _, m in msgs)
            note = pos.get("notes", "")
            text = (f"🛡 <b>Position Guardian</b> — {label}\n\n{body}"
                    + (f"\n\n<i>Thesis on file: {note}</i>" if note else "")
                    + "\n\n<i>These are YOUR rules, set before the position went live.</i>")
            if send_telegram(text):
                sent.update(k for k, _ in msgs)
                alerts += len(msgs)

        gstate[pid] = sorted(sent)

    meta["guardian"] = gstate
    return alerts

def main():
    with open(WATCHLIST_FILE) as f:
        watchlist = json.load(f)

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            previous = json.load(f)
    else:
        previous = {}

    meta = previous.get("_meta", {})
    pulse_refs = meta.get("pulse_ref", {})
    now = _utcnow()
    today = now.strftime("%Y-%m-%d")

    send_digest = meta.get("last_digest") != today

    last_pulse_str = meta.get("last_pulse")
    pulse_due = True
    if last_pulse_str:
        try:
            last_pulse = datetime.fromisoformat(last_pulse_str)
            pulse_due = (now - last_pulse) >= timedelta(hours=PULSE_INTERVAL_HOURS)
        except Exception:
            pulse_due = True

    digest_lines = []
    pulse_lines = []
    underlying_prices = {}
    new_state = {}
    changes = 0
    failures = 0

    for asset, details in watchlist.items():
        if asset.startswith("_"):
            continue
        try:
            df = fetch_data(details["ticker"])
            bias = compute_bias(df)
        except Exception as e:
            print(f"[{asset}] data fetch/compute failed: {e}", file=sys.stderr)
            if asset in previous:
                new_state[asset] = previous[asset]
            failures += 1
            continue

        state = bias["state"]
        unit = details.get("unit", "")
        underlying_prices[details["ticker"]] = bias["price"]
        new_state[asset] = {
            "state": state,
            "price": round(bias["price"], 2),
            "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        digest_lines.append(format_digest_line(asset, unit, bias))

        # ── 1. State-change alerts (always on) ──────────────
        prev_state = previous.get(asset, {}).get("state")
        if prev_state is None:
            if "ARMED" in state:
                send_telegram(format_alert(asset, unit, bias, "unmonitored"))
                changes += 1
        elif state != prev_state:
            send_telegram(format_alert(asset, unit, bias, prev_state))
            changes += 1

        # ── 3. Pulse movement check ─────────────────────────
        ref = pulse_refs.get(asset)
        if ref is None:
            # First sighting: set reference, never report against nothing
            pulse_refs[asset] = {"z": bias["z"], "price": bias["price"]}
        elif pulse_due:
            reason = pulse_movement(bias, ref)
            if reason:
                pulse_lines.append(format_pulse_line(asset, unit, bias, reason))
                pulse_refs[asset] = {"z": bias["z"], "price": bias["price"]}
            # No movement: reference stays put so slow grinds accumulate

    # ── 2. Daily digest (first run of the day) ──────────────
    if send_digest and digest_lines:
        header = f"📊 <b>Daily Terminal Digest</b> — {now.strftime('%b %d')}"
        footer = "<i>Descriptive snapshot only — alerts fire separately on state changes.</i>"
        if send_telegram(header + "\n\n" + "\n".join(digest_lines) + "\n\n" + footer):
            meta["last_digest"] = today

    # ── 3. Intraday pulse (movement-gated) ──────────────────
    if pulse_due:
        if pulse_lines:
            header = f"⏱ <b>Pulse</b> — {now.strftime('%H:%M')} UTC"
            footer = "<i>Movement since last reported reference. Quiet assets omitted.</i>"
            send_telegram(header + "\n\n" + "\n".join(pulse_lines) + "\n\n" + footer)
        # Clock advances whether or not anything moved — the next check is ~2h out
        meta["last_pulse"] = now.isoformat(timespec="seconds")

    guardian_alerts = guardian_check(meta, underlying_prices, now)

    meta["pulse_ref"] = pulse_refs
    new_state["_meta"] = meta
    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f, indent=2)

    print(f"Checked {len([a for a in watchlist if not a.startswith('_')])} assets | "
          f"{changes} state change(s) | {len(pulse_lines)} pulse mover(s) | "
          f"{guardian_alerts} guardian alert(s) | {failures} feed failure(s)")
    if failures == len(watchlist) and len(watchlist) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
