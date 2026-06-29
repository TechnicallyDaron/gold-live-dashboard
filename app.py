import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
load_dotenv()
import plotly.graph_objects as go
import anthropic
from datetime import datetime, timedelta

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Gold Quantitative Intelligence Dashboard",
    page_icon="🥇",
    layout="wide"
)

st.title("🥇 Gold Quantitative Intelligence Dashboard")
st.caption(f"Algorithmic Inefficiency & Mean Reversion Tracker · Updated: {datetime.now().strftime('%B %d, %Y %I:%M %p')}")

with st.expander("📖 How This Dashboard Works (ICT Translation Manual)"):
    st.markdown("""
    ### 1. Volatility Baseline (20 EMA) = Institutional Equilibrium
    Tracks the fair value anchor point of the market. Price targets look to return here to balance structural inefficiencies.
    
    ### 2. Upper & Lower Bands = Premium & Discount Arrays
    Tracks when price expands $\pm2.0$ standard deviations away from fair value. Punching below the Lower Band indicates an oversold **Discount Array** optimal for long entries.
    
    ### 3. Macro Trend Line (200 EMA) = Higher Timeframe (HTF) Bias
    Ensures we only trade in alignment with institutional order flow. If price is above the 200 EMA, we *only* buy discount dips and completely disable risky counter-trend shorts.
    """)

# ── Section 1: Live Gold Price Data & Volatility Model ───────
st.header("📈 Volatility Expansion & Mean Reversion")
st.caption("Tracking statistical price extensions outside standard deviation limits (Institutional Inefficiencies)")

@st.cache_data(ttl=5) # Reduced cache to allow real-time ticker stream updates
def load_gold_data():
    end = datetime.today()
    start = end - timedelta(days=1825) # 5 year data lookup to build stable long-term indicators
    gold = yf.download("GC=F", start=start, end=end, auto_adjust=True)
    
    if isinstance(gold.columns, pd.MultiIndex):
        gold.columns = gold.columns.get_level_values(0)
        
    gold = gold[["Open", "High", "Low", "Close"]].copy()
    gold.columns = ["Open", "High", "Low", "Gold_Price"]
    gold = gold.astype(float)
    
    # Short-term Volatility Baseline (20-period EMA)
    gold["Baseline"] = gold["Gold_Price"].ewm(span=20, adjust=False).mean()
    
    # Volatility Bands (2 Standard Deviations)
    gold["Std_Dev"] = gold["Gold_Price"].rolling(20).std()
    gold["Upper_Band"] = gold["Baseline"] + (gold["Std_Dev"] * 2.0)
    gold["Lower_Band"] = gold["Baseline"] - (gold["Std_Dev"] * 2.0)
    
    # Macro Trend Filter (200-period EMA for Higher Timeframe Bias)
    gold["Macro_Filter"] = gold["Gold_Price"].ewm(span=200, adjust=False).mean()
    
    return gold

with st.spinner("Fetching live market data and calculating volatility models..."):
    gold = load_gold_data()

# Limit the dashboard display view to the last 2 years for sharp chart resolution
gold_display = gold.tail(500).copy()

current_price = float(gold_display["Gold_Price"].iloc[-1])
prev_price = float(gold_display["Gold_Price"].iloc[-2])
price_change = current_price - prev_price
price_change_pct = (price_change / prev_price) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Price", f"${current_price:,.2f}/oz", f"{price_change:+.2f} ({price_change_pct:+.2f}%)")
col2.metric("Volatility Baseline (20 EMA)", f"${float(gold_display['Baseline'].iloc[-1]):,.2f}")
col3.metric("Macro Trend Line (200 EMA)", f"${float(gold_display['Macro_Filter'].iloc[-1]):,.2f}")
col4.metric("Market State", "BULLISH BIAS" if current_price > gold_display['Macro_Filter'].iloc[-1] else "BEARISH BIAS")

# ── INTERACTIVE PLOTLY CHART (ISOLATED LIVE STREAMING LAYER) ──
st.subheader("Live Market Feed")

# Using st.fragment keeps the loop entirely trapped in this block!
@st.fragment(run_every=10)
def render_live_chart():
    st.caption("This chart element automatically updates every 10 seconds without refreshing the AI memo or text.")
    gold_live = load_gold_data()
    valid_plot = gold_live.tail(500).dropna().copy()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Gold_Price"], mode='lines', name='Gold Price', line=dict(color='#FFD700', width=2.5)))
    fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Baseline"], mode='lines', name='20 EMA Baseline (Mean)', line=dict(color='#00BFFF', width=1.5, dash='dash')))
    fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Macro_Filter"], mode='lines', name='200 EMA Macro Trend (HTF)', line=dict(color='#A9A9A9', width=2, dash='solid')))
    fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Upper_Band"], mode='lines', name='Upper Band (Premium Zone)', line=dict(color='#FF6347', width=1, dash='dot')))
    fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Lower_Band"], mode='lines', name='Lower Band (Discount Zone)', line=dict(color='#32CD32', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.01)'))
    
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#1a1a1a", plot_bgcolor="#1a1a1a",
        margin=dict(l=20, r=20, t=20, b=20), height=550, hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickprefix="$", tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.components.v1.html(fig.to_html(include_plotlyjs='cdn', full_html=False), height=550)

# Run the isolated chart fragment
render_live_chart()


# ── Section 2: AI News Sentiment Analysis ─────────────────────
st.header("📰 Gold Market Sentiment")

import requests
from bs4 import BeautifulSoup

@st.cache_data(ttl=1800)
def fetch_gold_headlines():
    url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F&region=US&lang=en-US"
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
    except Exception as e:
        return [f"Could not fetch headlines: {e}"]

with st.spinner("Scanning market news..."):
    headlines = fetch_gold_headlines()

headline_text = "\n".join(headlines) if headlines else "No headlines available."

if headlines:
    st.subheader("Latest Headlines")
    for h in headlines:
        st.markdown(f"- {h}")

    with st.spinner("Analyzing market sentiment..."):
        api_key = os.getenv("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY", None)
        client = anthropic.Anthropic(api_key=api_key)
        
        sentiment_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""You are a gold market analyst. Analyze these recent gold market headlines and return:
1. Overall sentiment: Bullish, Bearish, or Neutral
2. Sentiment score: -10 to +10
3. A 2-3 sentence summary of what the news signals for gold price direction

Headlines:
{headline_text}

Be concise and direct."""
            }]
        )
        sentiment_text = sentiment_response.content[0].text
        st.markdown(sentiment_text)


# ── Section 3: AI Generated Investment Memo ──────────────────
st.header("🤖 AI Investment Memo")

with st.spinner("Generating investment memo..."):
    current_price_val = float(current_price)
    baseline_val = float(gold_display['Baseline'].dropna().iloc[-1])
    high_val = float(gold_display['Gold_Price'].max())

    memo_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""You are a senior quantitative gold market analyst writing an institutional investment memo.

Current Market Data:
- Gold Price: ${current_price_val:,.2f}/oz
- 20-Day Exponential Baseline: ${baseline_val:,.2f}
- 52-Week High: ${high_val:,.2f}
- Technical Position: {"Premium Expansion (Overextended)" if current_price_val > gold_display['Upper_Band'].iloc[-1] else "Discount Expansion (Undervalued)" if current_price_val < gold_display['Lower_Band'].iloc[-1] else "Mean-Reverting Equilibrium"}

Recent News Sentiment: Neutral-to-Bullish (+3/10)
Key Headlines: {headline_text}

Write a concise investment memo with these sections:
1. Market Position (2 sentences evaluating price layout vs statistical bands)
2. Key Drivers (3 bullet points on macro triggers)
3. Bias & Price Outlook (your short-term directional call regarding mean reversion)
4. Primary Risk (1 sentence on threat to thesis)

Be direct, quantitative, and use numbers."""
        }]
    )
    memo_text = memo_response.content[0].text
    memo_text = memo_text.replace("$", "\\$")
    st.markdown(memo_text)


# ── Section 4: Quantitative Inefficiency Backtest (Optimized) ──
st.header("📊 Optimized Strategy Backtest: Volatility Expansion Reversion")
st.caption("Institutional Engine: Uses a 200 EMA Macro Trend Filter to ensure we only trade with the Higher Timeframe Bias and enforces a strict 2.5% Stop Loss.")

valid = gold.dropna(subset=["Upper_Band", "Lower_Band", "Baseline", "Macro_Filter"]).copy()

position = 0  # 0 = cash, 1 = long, -1 = short
entry_price = 0
total_strategy_return = 0
trades = []

STOP_LOSS_PCT = 0.025  # 2.5% Maximum Loss Limit

for date, row in valid.iterrows():
    current_val = float(row["Gold_Price"])
    baseline_val = float(row["Baseline"])
    macro_val = float(row["Macro_Filter"])
    upper_val = float(row["Upper_Band"])
    lower_val = float(row["Lower_Band"])
    
    if position == 1:
        if current_val <= entry_price * (1 - STOP_LOSS_PCT):
            trade_return = -STOP_LOSS_PCT
            total_strategy_return += trade_return
            trades.append({"Type": "Long (Stop Loss Hit)", "Entry Date": entry_date.strftime("%Y-%m-%d"), "Entry Price": f"${entry_price:,.2f}", "Exit Price": f"${current_val:,.2f}", "Return": f"{trade_return*100:+.2f}%"})
            position = 0
        elif current_val >= baseline_val:
            trade_return = (current_val - entry_price) / entry_price
            total_strategy_return += trade_return
            trades.append({"Type": "Long (Discount Fill)", "Entry Date": entry_date.strftime("%Y-%m-%d"), "Entry Price": f"${entry_price:,.2f}", "Exit Price": f"${current_val:,.2f}", "Return": f"{trade_return*100:+.2f}%"})
            position = 0
            
    elif position == -1:
        if current_val >= entry_price * (1 + STOP_LOSS_PCT):
            trade_return = -STOP_LOSS_PCT
            total_strategy_return += trade_return
            trades.append({"Type": "Short (Stop Loss Hit)", "Entry Date": entry_date.strftime("%Y-%m-%d"), "Entry Price": f"${entry_price:,.2f}", "Exit Price": f"${current_val:,.2f}", "Return": f"{trade_return*100:+.2f}%"})
            position = 0
        elif current_val <= baseline_val:
            trade_return = (entry_price - current_val) / entry_price
            total_strategy_return += trade_return
            trades.append({"Type": "Short (Premium Burn)", "Entry Date": entry_date.strftime("%Y-%m-%d"), "Entry Price": f"${entry_price:,.2f}", "Exit Price": f"${current_val:,.2f}", "Return": f"{trade_return*100:+.2f}%"})
            position = 0

    if position == 0:
        if current_val < lower_val and current_val > macro_val:
            position = 1
            entry_price = current_val
            entry_date = date
        elif current_val > upper_val and current_val < macro_val:
            position = -1
            entry_price = current_val
            entry_date = date

buy_hold_return = (float(valid["Gold_Price"].iloc[-1]) - float(valid["Gold_Price"].iloc[0])) / float(valid["Gold_Price"].iloc[0])

col1, col2, col3 = st.columns(3)
col1.metric("Optimized Strategy Return", f"{total_strategy_return*100:+.2f}%")
col2.metric("Buy & Hold Benchmark", f"{buy_hold_return*100:+.2f}%")
col3.metric("Total Inefficiencies Captured", len(trades))

if trades:
    st.subheader("Captured Market Inefficiencies Log")
    st.dataframe(pd.DataFrame(trades), use_container_width=True)
else:
    st.info("No inefficiencies matched the optimized trend parameters within this timeframe.")
