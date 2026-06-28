import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
load_dotenv()
import matplotlib.pyplot as plt
import anthropic
from datetime import datetime, timedelta

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Gold Market Intelligence Dashboard",
    page_icon="🥇",
    layout="wide"
)

st.title("🥇 Gold Market Intelligence Dashboard")
st.caption(f"Live analysis powered by Claude AI · Updated: {datetime.now().strftime('%B %d, %Y %I:%M %p')}")

# ── Section 1: Live Gold Price Data ──────────────────────────
st.header("📈 Live Gold Price & Trend")

@st.cache_data(ttl=3600)  # Cache for 1 hour so we don't hammer Yahoo Finance
def load_gold_data():
    end = datetime.today()
    start = end - timedelta(days=365)
    gold = yf.download("GC=F", start=start, end=end, auto_adjust=True)
    gold = gold[["Close"]]
    gold.columns = ["Gold_Price"]
    gold["MA_50"] = gold["Gold_Price"].rolling(50).mean()
    gold["MA_200"] = gold["Gold_Price"].rolling(200).mean()
    return gold

with st.spinner("Fetching live gold price data..."):
    gold = load_gold_data()

# Current price metrics
current_price = gold["Gold_Price"].iloc[-1]
prev_price = gold["Gold_Price"].iloc[-2]
price_change = current_price - prev_price
price_change_pct = (price_change / prev_price) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Price", f"${current_price:,.0f}/oz", f"{price_change:+.0f} ({price_change_pct:+.2f}%)")
col2.metric("50-Day MA", f"${gold['MA_50'].iloc[-1]:,.0f}")
col3.metric("200-Day MA", f"${gold['MA_200'].iloc[-1]:,.0f}")
col4.metric("52-Week High", f"${gold['Gold_Price'].max():,.0f}")

# Chart
fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(gold.index, gold["Gold_Price"], color="#FFD700", linewidth=1.8, label="Gold Price")
ax.plot(gold.index, gold["MA_50"], color="#00BFFF", linewidth=1.5, linestyle="--", label="50-Day MA")
ax.plot(gold.index, gold["MA_200"], color="#FF6347", linewidth=1.5, linestyle="--", label="200-Day MA")
ax.set_facecolor("#1a1a1a")
fig.patch.set_facecolor("#1a1a1a")
ax.tick_params(colors="white")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.legend(fontsize=10)
ax.grid(True, linestyle="--", alpha=0.3)
plt.tight_layout()
st.pyplot(fig)

# ── Section 2: AI News Sentiment Analysis ────────────────────
st.header("📰 Gold Market Sentiment")
st.caption("AI agent scanning recent gold market news and scoring sentiment")

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

with st.spinner("Scanning gold market news..."):
    headlines = fetch_gold_headlines()

if headlines:
    st.subheader("Latest Headlines")
    for h in headlines:
        st.markdown(f"- {h}")

    # Send headlines to Claude for sentiment analysis
    st.subheader("AI Sentiment Analysis")
    with st.spinner("Claude is analyzing market sentiment..."):
        client = anthropic.Anthropic()
        headline_text = "\n".join(headlines)
        sentiment_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""You are a gold market analyst. Analyze these recent gold market headlines and return:
1. Overall sentiment: Bullish, Bearish, or Neutral
2. Sentiment score: -10 (very bearish) to +10 (very bullish)
3. A 2-3 sentence summary of what the news signals for gold price direction

Headlines:
{headline_text}

Be concise and direct. Lead with the sentiment and score."""
            }]
        )
        sentiment_text = sentiment_response.content[0].text
        st.markdown(sentiment_text)

# ── Section 3: AI Generated Investment Memo ──────────────────
st.header("🤖 AI Investment Memo")
st.caption("Claude generates a fresh investment thesis based on live price data and current sentiment")

with st.spinner("Claude is writing the investment memo..."):
    current_price_val = float(current_price.iloc[0]) if hasattr(current_price, 'iloc') else float(current_price)
    ma50_val = float(gold['MA_50'].iloc[-1].iloc[0]) if hasattr(gold['MA_50'].iloc[-1], 'iloc') else float(gold['MA_50'].iloc[-1])
    ma200_val = float(gold['MA_200'].iloc[-1].iloc[0]) if hasattr(gold['MA_200'].iloc[-1], 'iloc') else float(gold['MA_200'].iloc[-1])
    high_val = float(gold['Gold_Price'].max().iloc[0]) if hasattr(gold['Gold_Price'].max(), 'iloc') else float(gold['Gold_Price'].max())

    memo_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""You are a senior gold market analyst writing a concise investment memo.

Current Market Data (as of {datetime.now().strftime('%B %d, %Y')}):
- Gold Price: ${current_price_val:,.0f}/oz
- 50-Day Moving Average: ${ma50_val:,.0f}
- 200-Day Moving Average: ${ma200_val:,.0f}
- 52-Week High: ${high_val:,.0f}
- Price vs 50-Day MA: {"Above" if current_price_val > ma50_val else "Below"}
- Price vs 200-Day MA: {"Above" if current_price_val > ma200_val else "Below"}

Recent News Sentiment: Neutral-to-Bullish (+3/10)
Key Headlines: {headline_text}

Write a concise investment memo with these sections:
1. Market Position (2 sentences on where gold stands technically)
2. Key Drivers (3 bullet points on what's moving gold right now)
3. Bias & Price Outlook (your directional call and reasoning)
4. Primary Risk (1 sentence on the biggest threat to the thesis)

Be direct, specific, and use the actual numbers provided."""
        }]
    )
    memo_text = memo_response.content[0].text
    # Fix dollar sign rendering issue in markdown
    memo_text = memo_text.replace("$", "\\$")
    st.markdown(memo_text)