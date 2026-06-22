import streamlit as st
import requests
import pandas as pd
import numpy as np

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Forecast AI Pro", layout="wide")

FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", None)
BASE_URL = "https://finnhub.io/api/v1"

# -----------------------------
# SAFETY CHECK
# -----------------------------
if not FINNHUB_API_KEY:
    st.error("Missing API key. Set FINNHUB_API_KEY in Streamlit Cloud Secrets.")
    st.stop()

# -----------------------------
# SAFE REQUEST WRAPPER
# -----------------------------
def safe_get(url, params):
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# STOCK SEARCH
# -----------------------------
def search_stocks(query):
    data = safe_get(
        f"{BASE_URL}/search",
        {"q": query, "token": FINNHUB_API_KEY}
    )

    if not data or "result" not in data:
        return []

    return data["result"][:10]

# -----------------------------
# PRICE DATA
# -----------------------------
def get_price(symbol):
    data = safe_get(
        f"{BASE_URL}/quote",
        {"symbol": symbol, "token": FINNHUB_API_KEY}
    )

    if not data or "c" not in data:
        return None

    return data

# -----------------------------
# NEWS SENTIMENT (SAFE + SIMPLE)
# -----------------------------
def get_news(symbol):
    data = safe_get(
        f"{BASE_URL}/company-news",
        {
            "symbol": symbol,
            "from": "2025-01-01",
            "to": "2026-12-31",
            "token": FINNHUB_API_KEY
        }
    )

    if isinstance(data, dict) and "error" in data:
        return []

    return data[:15] if isinstance(data, list) else []


def sentiment(news):
    if not news:
        return 0

    pos = ["growth", "beat", "strong", "upgrade", "recovery", "profit"]
    neg = ["crash", "weak", "drop", "risk", "inflation", "loss"]

    score = 0

    for n in news:
        text = n.get("headline", "").lower()

        for p in pos:
            if p in text:
                score += 1

        for m in neg:
            if m in text:
                score -= 1

    return score

# -----------------------------
# SIMPLE FORECAST MODEL (STABLE)
# -----------------------------
def forecast(price, sent):
    try:
        change = (price["c"] or 0) - (price["pc"] or 0)
        return change * 0.7 + sent * 0.3
    except:
        return 0.0

# -----------------------------
# UI
# -----------------------------
st.title("📊 Forecast AI Pro (Trading Style)")

query = st.text_input("Search global stock (Apple, Tesla, SAP, etc.)")

if not query:
    st.info("Enter a stock name to start.")
    st.stop()

# SEARCH
results = search_stocks(query)

if not results:
    st.warning("No results found.")
    st.stop()

symbols = [r.get("symbol") for r in results if r.get("symbol")]

symbol = st.selectbox("Select stock", symbols)

# PRICE
price = get_price(symbol)

if not price:
    st.error("No price data available.")
    st.stop()

# NEWS + SENTIMENT
news = get_news(symbol)
sent = sentiment(news)

# FORECAST
pred = forecast(price, sent)

# -----------------------------
# DASHBOARD
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Price", price.get("c", 0))
col2.metric("Change", round((price.get("c", 0) - price.get("pc", 0)), 2))
col3.metric("Sentiment", sent)

st.divider()

st.subheader("📈 Forecast Signal")

if pred > 0:
    st.success(f"Bullish signal (+{round(pred,2)})")
else:
    st.error(f"Bearish signal ({round(pred,2)})")

st.subheader("📰 News")

if news:
    for n in news[:10]:
        st.write("•", n.get("headline", ""))
else:
    st.write("No news available.")
    
