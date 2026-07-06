"""
signal_engine.py — Pure statistical logic shared by the Streamlit app and the
Telegram alert bot. NO Streamlit imports allowed in this file: keeping the math
here means the dashboard and the alerts can never disagree about what a signal is.
"""
import pandas as pd

STOP_LOSS_PCT = 0.025


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: DataFrame with columns Open/High/Low/Price (daily bars).
    Output: same frame with Baseline, Std_Dev, bands, and Macro_Filter added.
    """
    df = df.copy()
    df["Baseline"] = df["Price"].ewm(span=20, adjust=False).mean()
    df["Std_Dev"] = df["Price"].rolling(20).std()
    df["Upper_Band"] = df["Baseline"] + (df["Std_Dev"] * 2.0)
    df["Lower_Band"] = df["Baseline"] - (df["Std_Dev"] * 2.0)
    df["Macro_Filter"] = df["Price"].ewm(span=200, adjust=False).mean()
    return df


def compute_bias(df: pd.DataFrame) -> dict:
    """
    Translate the current statistical state into a directional bias,
    the evidence behind it, and concrete trigger levels.
    """
    row = df.dropna(subset=["Baseline", "Std_Dev", "Upper_Band", "Lower_Band", "Macro_Filter"]).iloc[-1]
    price = float(row["Price"])
    baseline = float(row["Baseline"])
    std = float(row["Std_Dev"])
    upper = float(row["Upper_Band"])
    lower = float(row["Lower_Band"])
    macro = float(row["Macro_Filter"])

    z = (price - baseline) / std if std > 0 else 0.0
    trend_up = price > macro

    if price < lower and trend_up:
        state, direction, color = "🟢 LONG-REVERSION ARMED", "long", "green"
        headline = "Price is in the Discount Array with HTF trend support. This is the exact setup the strategy trades."
    elif price > upper and not trend_up:
        state, direction, color = "🔴 SHORT-REVERSION ARMED", "short", "red"
        headline = "Price is in the Premium Array against a bearish HTF trend. Short-reversion conditions are met."
    elif z <= -1.5 and trend_up:
        state, direction, color = "🟡 LONG WATCH", "long", "orange"
        headline = "Price is approaching the Lower Band with trend support. Not armed yet — watch the trigger level."
    elif z >= 1.5 and not trend_up:
        state, direction, color = "🟡 SHORT WATCH", "short", "orange"
        headline = "Price is approaching the Upper Band in a bearish HTF regime. Not armed yet."
    else:
        state, direction, color = "⚪ NO TRADE", None, "gray"
        headline = "Price is inside statistical equilibrium, or the band break conflicts with the HTF trend. The strategy has no edge here — standing aside IS the position."

    if direction == "short" or (direction is None and z > 0):
        arm_level = upper
        invalidation = upper * (1 + STOP_LOSS_PCT)
    else:
        arm_level = lower
        invalidation = lower * (1 - STOP_LOSS_PCT)

    return {
        "state": state, "direction": direction, "color": color, "headline": headline,
        "price": price, "baseline": baseline, "z": z,
        "upper": upper, "lower": lower, "macro": macro,
        "trend": "BULLISH (above 200 EMA)" if trend_up else "BEARISH (below 200 EMA)",
        "arm_level": arm_level,
        "invalidation": invalidation,
        "target": baseline,
        "dist_to_arm_pct": ((arm_level - price) / price) * 100,
        "dist_to_target_pct": ((baseline - price) / price) * 100,
    }
