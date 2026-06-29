# Gold Market Intelligence Dashboard
**Author:** Daron Nyarko  
**Built:** June 2026

---

## Overview

A live AI-powered gold market dashboard built with Python and Streamlit. 
Every time the app loads, an AI agent automatically:

1. Pulls real-time gold price data and renders live charts with moving averages
2. Scrapes current gold market news headlines
3. Runs sentiment analysis on the headlines and scores market direction
4. Generates a fresh investment memo using Claude AI based on live price data and sentiment

## 📊 Algorithmic Methodology: Quantitative vs. Institutional Frameworks

This dashboard utilizes an automated, data-driven **Statistical Volatility & Mean Reversion Engine** to track intraday inefficiencies in the Gold market. For users coming from price action or retail backgrounds (such as ICT/SMC), the mathematical components map directly to institutional delivery concepts:

### 1. Volatility Baseline (20 EMA) = The Institutional Equilibrium
* **Quantitative Definition:** A 20-period Exponential Moving Average that dynamically weights recent daily settlement prices.
* **Institutional Mapping:** This represents **Fair Value (Equilibrium)**. Rather than utilizing static premium/discount ranges, the 20 EMA functions as a fluid anchor point where price is structurally balanced. 

### 2. Upper & Lower Bands = Premium & Discount Arrays
* **Quantitative Definition:** Volatility boundaries set at $\pm2.0$ Standard Deviations away from the 20 EMA baseline.
* **Institutional Mapping:** These limits track automated expansions. 
  * **The Upper Band** represents a **Premium Expansion Zone** where speculative retail buying is overextended.
  * **The Lower Band** represents a **Discount Inefficiency Array** where institutional sell-side liquidity has been swept, leaving a pricing dislocation.

### 3. Macro Trend Line (200 EMA) = Higher Timeframe (HTF) Institutional Order Flow
* **Quantitative Definition:** A long-term technical boundary mapping the broad multi-month directional trend.
* **Institutional Mapping:** This serves as our **Higher Timeframe Bias filter**. To mitigate counter-trend risk and avoid fighting massive corporate capital waves, the algorithm enforces a strict execution rule:
  * **Price above 200 EMA:** Institutional Order Flow is **Bullish**. The engine blocks all short setups and exclusively executes on **Discount Fills** at the lower band.
  * **Price below 200 EMA:** Institutional Order Flow is **Bearish**. The engine blocks all long setups and exclusively executes on **Premium Burns** at the upper band.

### 4. Strategy Target Execution
When a market inefficiency triggers an entry (e.g., dipping into a Discount Array during an HTF uptrend), the algorithm initiates a position. The position is held until price gravitates back to the **20 EMA Baseline**, successfully rebalancing the chart back to Equilibrium. A strict **2.5% Stop Loss** is programmatically enforced to protect capital against runaway expansions.


## Tech Stack

- Python (Streamlit, yfinance, Pandas, Matplotlib, BeautifulSoup)
- Claude API (claude-sonnet-4-6) for sentiment analysis and memo generation
- Data sourced from Yahoo Finance

---

## Setup

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Add your Anthropic API key to a `.env` file: `ANTHROPIC_API_KEY=your-key-here`
4. Run: `streamlit run app.py`

---

## Related Project

This dashboard is an extension of my original static gold market analysis:  
[Gold Market Trend Analysis & Price Forecast](https://github.com/TechnicallyDaron/Gold-Market-Analysis)
