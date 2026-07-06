import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()
import plotly.graph_objects as go
import anthropic
from datetime import datetime, timedelta

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Quant Intelligence Terminal",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Anthropic client: fail loudly, once, at startup ─────────
API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=API_KEY) if API_KEY else None

# ── Constants ────────────────────────────────────────────────
asset_mapping = {
    "Gold": {"ticker": "GC=F", "name": "Gold Market", "unit": "/oz"},
    "S&P 500": {"ticker": "^GSPC", "name": "S&P 500 Index", "unit": ""},
    "SOFI": {"ticker": "SOFI", "name": "SoFi Technologies", "unit": "/sh"}
}
STOP_LOSS_PCT = 0.025

# ── Session state ────────────────────────────────────────────
if "active_trades" not in st.session_state:
    st.session_state.active_trades = {}


# =====================================================================
# 🔧 SHARED HELPERS
# =====================================================================
def md_safe(text: str) -> str:
    """Escape $ so Streamlit markdown doesn't treat prices as LaTeX."""
    return text.replace("$", "\\$")


@st.cache_data(ttl=60)
def load_market_data(ticker):
    """Daily OHLC + indicator columns. Asset-agnostic column names."""
    end = datetime.today()
    start = end - timedelta(days=1825)
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close"]].astype(float).copy()
    df = df.rename(columns={"Close": "Price"})

    df["Baseline"] = df["Price"].ewm(span=20, adjust=False).mean()
    df["Std_Dev"] = df["Price"].rolling(20).std()
    df["Upper_Band"] = df["Baseline"] + (df["Std_Dev"] * 2.0)
    df["Lower_Band"] = df["Baseline"] - (df["Std_Dev"] * 2.0)
    df["Macro_Filter"] = df["Price"].ewm(span=200, adjust=False).mean()
    return df


@st.cache_data(ttl=120)
def fetch_portal_quote(ticker):
    """
    Robust quote fetch with fallback. Returns (price, change, pct) or None.
    NEVER fabricates a $0.00 quote — a dead feed must look dead.
    """
    # Attempt 1: recent daily bars (1mo window survives holidays/weekends)
    try:
        df = yf.download(ticker, period="1mo", auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        closes = df["Close"].dropna().astype(float)
        if len(closes) >= 2:
            c, p = float(closes.iloc[-1]), float(closes.iloc[-2])
            return c, c - p, ((c - p) / p) * 100
    except Exception:
        pass

    # Attempt 2: fast_info endpoint (different Yahoo route, often survives
    # when the chart download endpoint is rate-limited)
    try:
        fi = yf.Ticker(ticker).fast_info
        c = float(fi["last_price"])
        p = float(fi["previous_close"])
        return c, c - p, ((c - p) / p) * 100
    except Exception:
        return None


# =====================================================================
# 🎯 BIAS ENGINE (pure math — no AI, no gate, instant)
# =====================================================================
def compute_bias(df):
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

    # Trigger levels (direction-aware)
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


# =====================================================================
# 📊 BACKTEST ENGINE (compounded equity, next-bar fills, real stats)
# =====================================================================
@st.cache_data(ttl=300)
def run_backtest(ticker, asset_name):
    """
    Mean-reversion backtest with honest execution:
    signals on the close → fills at the NEXT bar's open,
    intraday stop checks with gap handling, compounded equity.
    """
    df = load_market_data(ticker)
    valid = df.dropna(subset=["Upper_Band", "Lower_Band", "Baseline", "Macro_Filter"]).copy()

    equity = 1.0
    equity_marks = [1.0]
    position = 0
    entry_price = 0.0
    entry_date = None
    pending_entry = 0
    pending_exit_label = None
    trades = []

    def close_trade(exit_price, exit_date, label):
        nonlocal equity, position, entry_price, entry_date, pending_exit_label
        if position == 1:
            trade_return = (exit_price - entry_price) / entry_price
        else:
            trade_return = (entry_price - exit_price) / entry_price
        equity *= (1 + trade_return)
        equity_marks.append(equity)
        trades.append({
            "Asset": asset_name,
            "Type": label,
            "Entry Date": entry_date.strftime("%Y-%m-%d"),
            "Exit Date": exit_date.strftime("%Y-%m-%d"),
            "Entry Price": f"${entry_price:,.2f}",
            "Exit Price": f"${exit_price:,.2f}",
            "Return": f"{trade_return * 100:+.2f}%",
            "_ret": trade_return,
            "_dir": "long" if position == 1 else "short",
        })
        position = 0
        entry_price = 0.0
        entry_date = None
        pending_exit_label = None

    for bar in valid.itertuples():
        open_ = float(bar.Open)
        high = float(bar.High)
        low = float(bar.Low)
        close = float(bar.Price)

        if position == 0 and pending_entry != 0:
            position = pending_entry
            entry_price = open_
            entry_date = bar.Index
            pending_entry = 0
        elif position != 0 and pending_exit_label is not None:
            close_trade(open_, bar.Index, pending_exit_label)

        if position == 1:
            stop = entry_price * (1 - STOP_LOSS_PCT)
            if low <= stop:
                close_trade(min(open_, stop), bar.Index, "Long (Stop Loss Hit)")
        elif position == -1:
            stop = entry_price * (1 + STOP_LOSS_PCT)
            if high >= stop:
                close_trade(max(open_, stop), bar.Index, "Short (Stop Loss Hit)")

        if position == 1 and close >= float(bar.Baseline):
            pending_exit_label = "Long (Discount Fill)"
        elif position == -1 and close <= float(bar.Baseline):
            pending_exit_label = "Short (Premium Burn)"

        if position == 0 and pending_entry == 0:
            if close < float(bar.Lower_Band) and close > float(bar.Macro_Filter):
                pending_entry = 1
            elif close > float(bar.Upper_Band) and close < float(bar.Macro_Filter):
                pending_entry = -1

    def stat_block(subset):
        rets = [t["_ret"] for t in subset]
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r <= 0]
        return {
            "n": len(rets),
            "win_rate": (len(wins) / len(rets)) if rets else 0.0,
            "avg_win": float(np.mean(wins)) if wins else 0.0,
            "avg_loss": float(np.mean(losses)) if losses else 0.0,
        }

    eq = np.array(equity_marks)
    running_max = np.maximum.accumulate(eq)
    drawdowns = (eq - running_max) / running_max
    first = float(valid["Price"].iloc[0])
    last = float(valid["Price"].iloc[-1])

    stats = {
        "strategy_return": equity - 1.0,
        "buy_hold_return": (last - first) / first,
        "max_drawdown": float(drawdowns.min()) if len(eq) > 1 else 0.0,
        "all": stat_block(trades),
        "long": stat_block([t for t in trades if t["_dir"] == "long"]),
        "short": stat_block([t for t in trades if t["_dir"] == "short"]),
    }
    display_trades = [{k: v for k, v in t.items() if not k.startswith("_")} for t in trades]
    return display_trades, stats


# =====================================================================
# 🚨 MACRO CALENDAR (Forex Factory red folders)
# =====================================================================
@st.cache_data(ttl=3600)
def fetch_forex_factory_red_folders():
    url = "https://www.forexfactory.com/calendar"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    red_folders = []
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "lxml")
        for row in soup.find_all("tr", class_="calendar__row"):
            impact_cell = row.find("td", class_="calendar__impact")
            if impact_cell and impact_cell.find("span", class_="icon--impact-high"):
                currency_el = row.find("td", class_="calendar__currency")
                event_el = row.find("td", class_="calendar__event")
                actual_el = row.find("td", class_="calendar__actual")
                forecast_el = row.find("td", class_="calendar__forecast")
                if currency_el and event_el:
                    red_folders.append({
                        "Currency": currency_el.get_text(strip=True),
                        "Event": event_el.get_text(strip=True),
                        "Actual": (actual_el.get_text(strip=True) if actual_el else "") or "Pending",
                        "Forecast": (forecast_el.get_text(strip=True) if forecast_el else "") or "N/A",
                    })
        return red_folders[:8]
    except Exception:
        return []


@st.cache_data(ttl=1800)
def fetch_market_headlines(ticker):
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml-xml")
        headlines = []
        for item in soup.find_all("title"):
            text = item.get_text(strip=True)
            if len(text) > 20 and "Yahoo" not in text:
                headlines.append(text)
        return headlines[:8]
    except Exception:
        return []


# =====================================================================
# 🤖 CACHED AI CALLS (all fire on-demand via buttons)
# =====================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def ai_bias_memo(_client, name, ticker, bias_snapshot, stats_snapshot, macro_snapshot):
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=700,
        messages=[{
            "role": "user",
            "content": f"""You are a cynical institutional quantitative risk manager. A retail trader's dashboard has computed the statistical state below for {name} ({ticker}). Your job is to interpret it coldly — no encouragement, no hedging into vagueness. Base rates and math only.

Current Statistical State:
{bias_snapshot}

5-Year Backtest Base Rates for this exact setup (next-bar fills, compounded):
{stats_snapshot}

High-Impact Macro Events This Week:
{macro_snapshot}

Write a tight memo with exactly these sections:
1. BIAS VERDICT: One sentence — does the statistical evidence support acting right now, or standing aside?
2. EVIDENCE WEIGHING: 3 bullets max — which numbers above carry the verdict and which are noise.
3. WHAT WOULD CHANGE THE CALL: The exact price levels or macro events that flip or kill this bias.
4. BASE RATE REALITY CHECK: One sentence contrasting the trader's likely expectation with the historical win rate and avg win/loss.

This is statistical interpretation, not financial advice. Be direct."""
        }]
    )
    return response.content[0].text


@st.cache_data(ttl=1800, show_spinner=False)
def ai_sentiment(_client, name, ticker, headline_text):
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""You are a senior market analyst. Analyze these recent financial headlines for {name} ({ticker}) and return:
1. Overall sentiment: Bullish, Bearish, or Neutral
2. Sentiment score: -10 to +10
3. A 2-3 sentence summary of what the news signals for short term price direction

Headlines:
{headline_text}

Be concise and direct."""
        }]
    )
    return response.content[0].text


@st.cache_data(ttl=900, show_spinner=False)
def ai_stress_test(_client, asset_name, trade_key, days_left, price_bucket,
                   market_snapshot, stats_snapshot):
    trade = st.session_state.active_trades[asset_name]
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": f"""You are a cynical, strict institutional quantitative risk manager. Aggressively stress-test this retail trader's options thesis using hard data and math. Do not encourage them or validate their biases.

Position Parameters:
- Type: {trade['Type']}
- Strike: ${trade['Strike']}
- Time Horizon: {days_left} days until expiration
- Entry Premium Paid: ${trade['Entry Premium']}
- Trader's Narrative/Thesis: {trade['Thesis']}

Current Statistical Market Realities for {asset_name}:
{market_snapshot}

Historical Base Rates for this setup (5yr backtest, next-bar fills, compounded):
{stats_snapshot}

Provide a critical, data-driven cross-examination structured exactly as follows:
1. DATA-DRIVEN THESIS STRESS-TEST: Use spot vs 20 EMA and the volatility bands to challenge the core logic.
2. MATHEMATICAL HURDLE: Exact % move needed to break even given premium vs strike, contrasted with the {days_left}-day window.
3. HISTORICAL BASE RATE CHECK: Judge the thesis against the backtest win rate, avg win/loss, and max drawdown.
4. ASSUMPTION STACK: List every implicit assumption that must go perfectly for this option not to expire worthless.
5. CONCRETE RISK CUTOFF: An explicit stop-loss price or time-decay boundary where this trade is structurally dead."""
        }]
    )
    return response.content[0].text


def require_client(feature: str) -> bool:
    if client is None:
        st.error(f"⚠️ ANTHROPIC_API_KEY missing — {feature} is disabled until it's set in your .env file.")
        return False
    return True


def get_selected_asset():
    return st.session_state.get("asset_select", list(asset_mapping.keys())[0])


# =====================================================================
# PAGE 1: 🎛️ COMMAND CENTER
# =====================================================================
def page_command_center():
    st.title("🎛️ Command Center")
    st.caption(f"Mean Reversion Terminal · Updated: {datetime.now().strftime('%B %d, %Y %I:%M %p')}")

    if client is None:
        st.error("⚠️ ANTHROPIC_API_KEY not found — AI features are disabled. Set it in your .env file.")

    st.subheader("Watchlist & Signal Status")
    cols = st.columns(3)

    for index, (asset_name, details) in enumerate(asset_mapping.items()):
        quote = fetch_portal_quote(details["ticker"])
        with cols[index]:
            if quote is None:
                st.markdown(
                    f"""
                    <div style="border: 2px solid #5a2a2a; padding: 22px; border-radius: 12px; text-align: center; background-color: #1a1a1a; margin-bottom: 10px;">
                        <h2 style="margin: 0; color: #FFFFFF; font-size: 24px;">{asset_name}</h2>
                        <h3 style="margin: 8px 0; color: #FF6347; font-size: 20px;">— FEED DOWN —</h3>
                        <p style="margin: 0; color: #888; font-size: 14px;">Quote source unavailable</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                continue

            c_price, diff, pct = quote
            color = "#32CD32" if diff >= 0 else "#FF6347"
            sign = "+" if diff >= 0 else ""

            # Compute the live bias state for the card
            try:
                bias = compute_bias(load_market_data(details["ticker"]))
                bias_label = bias["state"]
            except Exception:
                bias_label = "⚪ DATA ERROR"

            st.markdown(
                f"""
                <div style="border: 2px solid #3e3e3e; padding: 22px; border-radius: 12px; text-align: center; background-color: #1a1a1a; margin-bottom: 10px;">
                    <h2 style="margin: 0; color: #FFFFFF; font-size: 24px;">{asset_name}</h2>
                    <h3 style="margin: 8px 0; color: #CCCCCC; font-size: 20px;">${c_price:,.2f}{details['unit']}</h3>
                    <p style="margin: 0 0 8px 0; color: {color}; font-weight: bold; font-size: 15px;">{sign}{pct:.2f}% Today</p>
                    <p style="margin: 0; color: #FFFFFF; font-size: 14px; font-weight: bold;">{bias_label}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.info("👈 Pick an asset in the sidebar, then open **Bias Engine** for the full statistical breakdown and trigger levels.")

    st.markdown("---")
    st.subheader("🚨 High-Impact Macro Events This Week")
    with st.spinner("Loading macro calendar..."):
        macro_events = fetch_forex_factory_red_folders()

    if macro_events:
        st.dataframe(pd.DataFrame(macro_events), use_container_width=True, hide_index=True)
        st.caption("Red-folder events can violently expand volatility across all assets. Signals armed into these events carry elevated gap risk.")
    else:
        st.success("✅ No high-impact macro events detected on the current horizon.")


# =====================================================================
# PAGE 2: 🎯 BIAS ENGINE (the core decision screen)
# =====================================================================
def page_bias_engine():
    asset = get_selected_asset()
    details = asset_mapping[asset]
    st.title(f"🎯 Bias Engine — {details['name']}")

    with st.spinner("Computing statistical state..."):
        try:
            df = load_market_data(details["ticker"])
            bias = compute_bias(df)
            trades, stats = run_backtest(details["ticker"], asset)
        except Exception:
            st.error("Data feed failure for this asset. Try again shortly — Yahoo rate limits are usually temporary.")
            return

    # ── 1. THE VERDICT ───────────────────────────────────────
    banner = {"green": st.success, "red": st.error, "orange": st.warning, "gray": st.info}[bias["color"]]
    banner(f"### {bias['state']}\n{bias['headline']}")

    # ── 2. THE EVIDENCE ─────────────────────────────────────
    st.subheader("Evidence")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Price", f"${bias['price']:,.2f}{details['unit']}")
    c2.metric("Deviation (Z-Score)", f"{bias['z']:+.2f}σ", help="Standard deviations from the 20 EMA equilibrium. ±2σ = band touch.")
    c3.metric("20 EMA Equilibrium", f"${bias['baseline']:,.2f}")
    c4.metric("HTF Trend (200 EMA)", bias["trend"].split(" ")[0], help=bias["trend"])

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Lower Band (−2σ)", f"${bias['lower']:,.2f}")
    c6.metric("Upper Band (+2σ)", f"${bias['upper']:,.2f}")
    dir_stats = stats.get(bias["direction"] or "all", stats["all"])
    c7.metric("Setup Win Rate (5yr)", f"{dir_stats['win_rate']*100:.1f}%", help=f"Based on {dir_stats['n']} historical trades of this direction.")
    c8.metric("Avg Win / Avg Loss", f"{dir_stats['avg_win']*100:+.1f}% / {dir_stats['avg_loss']*100:+.1f}%")

    # ── 3. THE TRIGGERS ─────────────────────────────────────
    st.subheader("Action Levels")
    t1, t2, t3 = st.columns(3)
    t1.metric("Arm Level (band touch)", f"${bias['arm_level']:,.2f}", f"{bias['dist_to_arm_pct']:+.2f}% away", delta_color="off")
    t2.metric("Invalidation (stop zone)", f"${bias['invalidation']:,.2f}", help=f"Entry beyond this level violates the {STOP_LOSS_PCT*100:.1f}% risk budget the backtest assumes.")
    t3.metric("Reversion Target (20 EMA)", f"${bias['target']:,.2f}", f"{bias['dist_to_target_pct']:+.2f}% from spot", delta_color="off")

    # ── 4. MACRO RISK OVERLAY ───────────────────────────────
    macro_events = fetch_forex_factory_red_folders()
    if macro_events:
        with st.expander(f"🚨 {len(macro_events)} high-impact macro events this week — gap risk on armed signals"):
            st.dataframe(pd.DataFrame(macro_events), use_container_width=True, hide_index=True)

    # ── 5. ON-DEMAND AI INTERPRETATION ──────────────────────
    st.markdown("---")
    if st.button("🤖 Generate AI Bias Memo", use_container_width=True):
        if require_client("the AI bias memo"):
            bias_snapshot = (
                f"- State: {bias['state']}\n"
                f"- Spot: ${bias['price']:,.2f} | Z-score: {bias['z']:+.2f} std devs\n"
                f"- 20 EMA: ${bias['baseline']:,.2f} | 200 EMA: ${bias['macro']:,.2f} ({bias['trend']})\n"
                f"- Bands: ${bias['lower']:,.2f} / ${bias['upper']:,.2f}\n"
                f"- Arm: ${bias['arm_level']:,.2f} | Invalidation: ${bias['invalidation']:,.2f} | Target: ${bias['target']:,.2f}"
            )
            stats_snapshot = (
                f"- Direction-relevant trades: {dir_stats['n']} | Win rate: {dir_stats['win_rate']*100:.1f}%\n"
                f"- Avg win: {dir_stats['avg_win']*100:+.2f}% | Avg loss: {dir_stats['avg_loss']*100:+.2f}%\n"
                f"- Strategy compounded: {stats['strategy_return']*100:+.2f}% vs B&H {stats['buy_hold_return']*100:+.2f}%\n"
                f"- Max drawdown (trade-level): {stats['max_drawdown']*100:.2f}%"
            )
            macro_snapshot = "\n".join(
                f"- {e['Currency']}: {e['Event']} (Forecast: {e['Forecast']})" for e in macro_events
            ) or "- None detected"
            with st.spinner("Interpreting the numbers..."):
                try:
                    memo = ai_bias_memo(client, details["name"], details["ticker"],
                                        bias_snapshot, stats_snapshot, macro_snapshot)
                    st.markdown(md_safe(memo))
                except Exception:
                    st.error("AI call failed — check your API key, network, or rate limits.")


# =====================================================================
# PAGE 3: 📈 LIVE CHART
# =====================================================================
def page_live_chart():
    asset = get_selected_asset()
    details = asset_mapping[asset]
    st.title(f"📈 Live Chart — {details['name']}")

    with st.expander("📖 How to read this chart"):
        st.markdown("""
        - **20 EMA (Baseline)** = institutional equilibrium / fair value anchor.
        - **±2σ Bands** = Premium and Discount Arrays. A close beyond a band is a statistical overextension.
        - **200 EMA (Macro Trend)** = higher-timeframe bias filter. The strategy only trades reversion *with* this trend.
        """)

    @st.fragment(run_every=15)
    def render_live_chart():
        try:
            live_df = load_market_data(details["ticker"])
        except Exception:
            st.error("Chart data feed failure — retrying automatically.")
            return
        valid_plot = live_df.tail(500).dropna().copy()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Price"], mode='lines', name=f'{asset} Price', line=dict(color='#FFD700', width=2.5)))
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Baseline"], mode='lines', name='20 EMA Baseline', line=dict(color='#00BFFF', width=1.5, dash='dash')))
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Macro_Filter"], mode='lines', name='200 EMA Macro Trend', line=dict(color='#A9A9A9', width=2)))
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Upper_Band"], mode='lines', name='Upper Band (Premium)', line=dict(color='#FF6347', width=1, dash='dot')))
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Lower_Band"], mode='lines', name='Lower Band (Discount)', line=dict(color='#32CD32', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.01)'))

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#1a1a1a", plot_bgcolor="#1a1a1a",
            margin=dict(l=20, r=20, t=20, b=20), height=600, hovermode="x unified",
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickprefix="$", tickformat=",.2f"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{asset}_{datetime.now().timestamp()}")
        st.caption("Auto-refreshes every 15 seconds.")

    render_live_chart()


# =====================================================================
# PAGE 4: 📰 NEWS & SENTIMENT
# =====================================================================
def page_sentiment():
    asset = get_selected_asset()
    details = asset_mapping[asset]
    st.title(f"📰 News & Sentiment — {details['name']}")

    with st.spinner("Scanning market news..."):
        headlines = fetch_market_headlines(details["ticker"])

    if not headlines:
        st.warning("No headlines available from the feed right now.")
        return

    st.subheader("Latest Headlines")
    for h in headlines:
        st.markdown(f"- {md_safe(h)}")

    st.markdown("---")
    if st.button("🤖 Run AI Sentiment Analysis", use_container_width=True):
        if require_client("sentiment analysis"):
            with st.spinner("Analyzing sentiment..."):
                try:
                    result = ai_sentiment(client, details["name"], details["ticker"], "\n".join(headlines))
                    st.markdown(md_safe(result))
                except Exception:
                    st.error("AI call failed — check your API key, network, or rate limits.")


# =====================================================================
# PAGE 5: 📊 BACKTEST LAB
# =====================================================================
def page_backtest():
    asset = get_selected_asset()
    details = asset_mapping[asset]
    st.title(f"📊 Backtest Lab — {details['name']}")
    st.caption("Honest execution model: signals on the close, fills at the NEXT bar's open, intraday stop checks, compounded equity.")

    with st.spinner("Running 5-year backtest..."):
        try:
            trades, stats = run_backtest(details["ticker"], asset)
        except Exception:
            st.error("Data feed failure for this asset — try again shortly.")
            return

    col1, col2, col3 = st.columns(3)
    col1.metric("Compounded Strategy Return", f"{stats['strategy_return']*100:+.2f}%")
    col2.metric("Buy & Hold Benchmark", f"{stats['buy_hold_return']*100:+.2f}%")
    col3.metric("Max Drawdown", f"{stats['max_drawdown']*100:.2f}%",
                help="Measured on trade-close equity — open-position drawdown can be worse.")

    st.subheader("Base Rates by Direction")
    b1, b2, b3 = st.columns(3)
    for col, key, label in [(b1, "all", "All Trades"), (b2, "long", "Longs (Discount Bounce)"), (b3, "short", "Shorts (Premium Fade)")]:
        s = stats[key]
        col.markdown(f"**{label}**")
        col.metric("Trades / Win Rate", f"{s['n']} / {s['win_rate']*100:.1f}%")
        col.metric("Avg Win / Avg Loss", f"{s['avg_win']*100:+.2f}% / {s['avg_loss']*100:+.2f}%")

    if trades:
        st.subheader("Trade Log")
        st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)
    else:
        st.info(f"No signals matched the strategy parameters for {asset} in this window.")


# =====================================================================
# PAGE 6: 🦅 OPTIONS CO-PILOT (optional — never a gate to analysis)
# =====================================================================
def page_copilot():
    asset = get_selected_asset()
    details = asset_mapping[asset]
    st.title(f"🦅 Options Co-Pilot — {details['name']}")
    st.caption("Optional: log a live options position to have it stress-tested against the statistics. All analysis pages work without this.")

    if asset not in st.session_state.active_trades:
        st.session_state.active_trades[asset] = None

    current_trade = st.session_state.active_trades[asset]

    if current_trade is None:
        st.subheader("📝 Log an Active Options Position")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            type_opt = st.selectbox("Position Type", ["Long Call 🟢", "Long Put 🔴"], key=f"type_{asset}")
        with c2:
            strike = st.number_input("Strike Price ($)", min_value=0.0, step=0.5, key=f"strike_{asset}")
        with c3:
            exp_date = st.date_input("Expiration Date", key=f"exp_{asset}")
        with c4:
            premium = st.number_input("Entry Premium / Cost ($)", min_value=0.0, step=0.01, key=f"prem_{asset}")

        thesis = st.text_area("Trade thesis (e.g., Playing the discount bounce off the Lower Band)", key=f"thesis_{asset}")

        if st.button("🚀 Deploy Co-Pilot Tracking", use_container_width=True):
            st.session_state.active_trades[asset] = {
                "Type": type_opt,
                "Strike": strike,
                "Expiration": exp_date.strftime("%Y-%m-%d"),
                "Entry Premium": premium,
                "Thesis": thesis,
                "Logged At": datetime.now().strftime("%Y-%m-%d %I:%M %p")
            }
            st.rerun()
        return

    st.warning(f"🚨 ACTIVE POSITION: {current_trade['Type']} | Strike: ${current_trade['Strike']} | Exp: {current_trade['Expiration']}")
    try:
        days_left = (datetime.strptime(current_trade['Expiration'], "%Y-%m-%d").date() - datetime.today().date()).days
    except Exception:
        days_left = "N/A"

    tc1, tc2 = st.columns([3, 1])
    with tc1:
        st.markdown(f"**Your Thesis:** *{current_trade['Thesis']}*")
        st.caption(f"Logged: {current_trade['Logged At']}")
    with tc2:
        if st.button("🏁 Clear Position", use_container_width=True):
            st.session_state.active_trades[asset] = None
            st.rerun()

    st.markdown("---")
    if st.button("🦅 Run AI Stress-Test", use_container_width=True):
        if require_client("the AI stress-test"):
            try:
                df = load_market_data(details["ticker"])
                bias = compute_bias(df)
                trades, stats = run_backtest(details["ticker"], asset)
            except Exception:
                st.error("Data feed failure — cannot stress-test without live statistics.")
                return

            market_snapshot = (
                f"- Spot: ${bias['price']:,.2f} | Z-score: {bias['z']:+.2f} std devs\n"
                f"- 20 EMA: ${bias['baseline']:,.2f} | 200 EMA: ${bias['macro']:,.2f} ({bias['trend']})\n"
                f"- Bands: ${bias['lower']:,.2f} / ${bias['upper']:,.2f}"
            )
            s = stats["all"]
            stats_snapshot = (
                f"- Trades: {s['n']} | Win rate: {s['win_rate']*100:.1f}%\n"
                f"- Avg win: {s['avg_win']*100:+.2f}% | Avg loss: {s['avg_loss']*100:+.2f}%\n"
                f"- Max drawdown: {stats['max_drawdown']*100:.2f}%"
            )
            trade_key = f"{current_trade['Type']}|{current_trade['Strike']}|{current_trade['Expiration']}|{current_trade['Entry Premium']}|{current_trade['Logged At']}"
            with st.spinner("🦅 Cross-examining your thesis..."):
                try:
                    analysis = ai_stress_test(client, asset, trade_key, days_left,
                                              round(bias["price"], 0), market_snapshot, stats_snapshot)
                    st.chat_message("assistant", avatar="🦅").markdown(md_safe(analysis))
                except Exception:
                    st.error("AI call failed — check your API key, network, or rate limits.")


# =====================================================================
# 🧭 NAVIGATION (true multipage app)
# =====================================================================
pages = [
    st.Page(page_command_center, title="Command Center", icon="🎛️", default=True),
    st.Page(page_bias_engine, title="Bias Engine", icon="🎯"),
    st.Page(page_live_chart, title="Live Chart", icon="📈"),
    st.Page(page_sentiment, title="News & Sentiment", icon="📰"),
    st.Page(page_backtest, title="Backtest Lab", icon="📊"),
    st.Page(page_copilot, title="Options Co-Pilot", icon="🦅"),
]

nav = st.navigation(pages)

with st.sidebar:
    st.markdown("### 🎯 Active Asset")
    st.selectbox("Asset", list(asset_mapping.keys()), key="asset_select", label_visibility="collapsed")
    st.caption("All analysis pages follow this selection.")

nav.run()