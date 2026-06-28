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

---

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
