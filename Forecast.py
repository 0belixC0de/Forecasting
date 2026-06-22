import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="Forecast AI Pro", layout="wide")

# -----------------------------
# API KEY (SAFE)
# -----------------------------
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", None)

if not FINNHUB_API_KEY:
    st.error("Missing API key. Add it in .streamlit/secrets.toml")
    st.stop()

BASE_URL = "https://finnhub.io/api/v1"


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
# SEARCH STOCKS
# -----------------------------
def search_stocks(query):
    url = f"{BASE_URL}/search"
    data = safe_get(url, {"q": query, "token": FINNHUB_API_KEY})

    if not data or "result" not in data:
        return []

    return data["result"][:10]


# -----------------------------
# PRICE DATA
# -----------------------------
def get_price(symbol):
    url = f"{BASE_URL}/quote"
    data = safe_get(url, {"symbol": symbol, "token": FINNHUB_API_KEY})

    if not data:
        return None

    return data


# -----------------------------
# NEWS SENTIMENT (SAFE)
# -----------------------------
def get_news(symbol):
    url = f"{BASE_URL}/company-news"
    data = safe_get(url, {
        "symbol": symbol,
        "from": "2025-01-01",
        "to": "2026-12-31",
        "token": FINNHUB_API_KEY
    })

    if isinstance(data, dict) and "error" in data:
        return []

    return data[:20] if data else []


def sentiment(news):
    if not news:
        return 0

    pos = ["growth", "beat", "strong", "upgrade", "recovery"]
    neg = ["crash", "weak", "drop", "risk", "inflation"]

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
# FORECAST (SAFE MODEL)
# -----------------------------
def forecast_model(price, sentiment_score):
    try:
        features = np.array([
            price.get("c", 0),
            price.get("h", 0),
            price.get("l", 0),
            price.get("pc", 0),
            sentiment_score
        ]).reshape(1, -1)

        # simple heuristic model (stable, no crash ML)
        prediction = (
            (price.get("c", 0) - price.get("pc", 0)) * 0.5 +
            sentiment_score * 0.2
        )

        return float(prediction)

    except:
        return 0.0


# -----------------------------
# UI
# -----------------------------
st.title("📊 Forecast AI Pro (Trading View)")

query = st.text_input("Search stock (e.g. Apple, Tesla, SAP)")

if query:
    results = search_stocks(query)

    if not results:
        st.warning("No results found")
        st.stop()

    symbols = [r["symbol"] for r in results]

    symbol = st.selectbox("Select stock", symbols)

    price = get_price(symbol)
    news = get_news(symbol)

    if not price:
        st.error("Price data not available")
        st.stop()

    sent = sentiment(news)
    pred = forecast_model(price, sent)

    # -----------------------------
    # DISPLAY
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    col1.metric("Price", price.get("c"))
    col2.metric("Change", round(price.get("c", 0) - price.get("pc", 0), 2))
    col3.metric("Sentiment", sent)

    st.subheader("Forecast Signal")

    if pred > 0:
        st.success(f"Bullish signal (+{round(pred,2)})")
    else:
        st.error(f"Bearish signal ({round(pred,2)})")

    st.subheader("News")
    for n in news[:10]:
        st.write("•", n.get("headline", ""))
        
