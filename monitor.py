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

    meta["pulse_ref"] = pulse_refs
    new_state["_meta"] = meta
    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f, indent=2)

    print(f"Checked {len([a for a in watchlist if not a.startswith('_')])} assets | "
          f"{changes} state change(s) | {len(pulse_lines)} pulse mover(s) | {failures} feed failure(s)")
    if failures == len(watchlist) and len(watchlist) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()