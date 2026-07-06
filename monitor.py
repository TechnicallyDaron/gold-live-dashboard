"""
monitor.py — Signal monitor for the Quant Intelligence Terminal.

Run by GitHub Actions on a cron schedule. For each asset in watchlist.json:
  1. Fetch daily data and compute the bias state (same math as the app,
     via the shared signal_engine module).
  2. Compare against the state recorded in signal_state.json from the last run.
  3. On a STATE CHANGE only, send a Telegram alert with the trigger levels.
  4. Write the new state file (the workflow commits it back to the repo).

Environment variables required for alerts:
  TELEGRAM_BOT_TOKEN  — from @BotFather
  TELEGRAM_CHAT_ID    — your personal chat id with the bot

If either is missing, the script runs in dry-run mode and prints the alerts
to stdout instead (useful for local testing: `python monitor.py`).
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

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


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


def main():
    with open(WATCHLIST_FILE) as f:
        watchlist = json.load(f)

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            previous = json.load(f)
    else:
        previous = {}

    meta = previous.get("_meta", {})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    send_digest = meta.get("last_digest") != today
    digest_lines = []

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
            # Preserve the last known state so a transient feed failure
            # doesn't generate a phantom "state change" on recovery.
            if asset in previous:
                new_state[asset] = previous[asset]
            failures += 1
            continue

        state = bias["state"]
        new_state[asset] = {
            "state": state,
            "price": round(bias["price"], 2),
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        digest_lines.append(format_digest_line(asset, details.get("unit", ""), bias))

        prev_state = previous.get(asset, {}).get("state")
        if prev_state is None:
            # First run for this asset: record baseline, alert only if already armed
            if "ARMED" in state:
                send_telegram(format_alert(asset, details.get("unit", ""), bias, "unmonitored"))
                changes += 1
        elif state != prev_state:
            send_telegram(format_alert(asset, details.get("unit", ""), bias, prev_state))
            changes += 1

    if send_digest and digest_lines:
        header = f"📊 <b>Daily Terminal Digest</b> — {datetime.now(timezone.utc).strftime('%b %d')}"
        footer = "<i>Descriptive snapshot only — alerts fire separately on state changes.</i>"
        if send_telegram(header + "\n\n" + "\n".join(digest_lines) + "\n\n" + footer):
            meta["last_digest"] = today

    new_state["_meta"] = meta
    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f, indent=2)

    print(f"Checked {len(watchlist)} assets | {changes} state change(s) | {failures} feed failure(s)")
    # Exit 0 even with feed failures — transient Yahoo throttling shouldn't
    # mark the workflow red. Total failure of every asset is worth flagging:
    if failures == len(watchlist) and len(watchlist) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()