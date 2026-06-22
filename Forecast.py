import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="TradeAI", layout="wide")

# -----------------------------
# API KEY
# -----------------------------
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY")
BASE_URL = "https://finnhub.io/api/v1"

if not FINNHUB_API_KEY:
    st.error("Missing API key")
    st.stop()


# -----------------------------
# API HELPERS
# -----------------------------
def get_json(url, params):
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except:
        return None


# -----------------------------
# SEARCH
# -----------------------------
def search(q):
    data = get_json(f"{BASE_URL}/search", {"q": q, "token": FINNHUB_API_KEY})
    if not data:
        return []
    return data.get("result", [])[:8]


# -----------------------------
# PRICE + CANDLES
# -----------------------------
def get_quote(symbol):
    return get_json(f"{BASE_URL}/quote", {
        "symbol": symbol,
        "token": FINNHUB_API_KEY
    })


def get_candles(symbol):
    data = get_json(f"{BASE_URL}/stock/candle", {
        "symbol": symbol,
        "resolution": "D",
        "from": 1600000000,
        "to": 1700000000,
        "token": FINNHUB_API_KEY
    })

    if not data or data.get("s") != "ok":
        return None

    df = pd.DataFrame({
        "open": data["o"],
        "high": data["h"],
        "low": data["l"],
        "close": data["c"],
        "volume": data["v"]
    })

    return df


# -----------------------------
# NEWS SENTIMENT
# -----------------------------
def get_news(symbol):
    data = get_json(f"{BASE_URL}/company-news", {
        "symbol": symbol,
        "from": "2025-01-01",
        "to": "2026-12-31",
        "token": FINNHUB_API_KEY
    })

    if not data:
        return []

    return data[:15]


def sentiment(news):
    if not news:
        return 0

    pos = ["growth", "beat", "strong", "upgrade", "recovery", "profit"]
    neg = ["drop", "crash", "weak", "risk", "inflation", "loss"]

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
# FORECAST ENGINE (REAL MATH SIGNAL)
# -----------------------------
def forecast(df, sent):
    close = df["close"]

    log_return = np.log(close / close.shift(1)).fillna(0)

    ma_short = close.rolling(5).mean()
    ma_long = close.rolling(20).mean()

    trend = (ma_short.iloc[-1] - ma_long.iloc[-1]) / ma_long.iloc[-1]

    volatility = log_return.rolling(10).std().iloc[-1]

    score = (
        trend * 2.5 +
        sent * 0.8 -
        volatility * 1.5
    )

    return score, trend, volatility


# -----------------------------
# CHART
# -----------------------------
def plot_chart(df):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Price"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["close"].rolling(10).mean(),
        name="MA 10"
    ))

    fig.layout.update(
        height=500,
        margin=dict(l=10, r=10, t=30, b=10),
        template="plotly_dark"
    )

    return fig


# -----------------------------
# UI (TRADE REPUBLIC STYLE)
# -----------------------------
st.markdown("# 📈 TradeAI")

query = st.text_input("Search stocks")

if not query:
    st.info("Search a stock to start")
    st.stop()

results = search(query)

if not results:
    st.warning("No results")
    st.stop()

symbols = [r["symbol"] for r in results if "symbol" in r]
symbol = st.selectbox("Select asset", symbols)

quote = get_quote(symbol)
df = get_candles(symbol)
news = get_news(symbol)

if quote is None or df is None:
    st.error("No market data available")
    st.stop()

sent = sentiment(news)
score, trend, vol = forecast(df, sent)

# -----------------------------
# HEADER (TR STYLE)
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Price", quote["c"])
col2.metric("Daily Change", round(quote["c"] - quote["pc"], 2))
col3.metric("Signal Score", round(score, 3))


# -----------------------------
# SIGNAL BLOCK
# -----------------------------
if score > 0:
    st.success("🟢 Bullish Bias")
else:
    st.error("🔴 Bearish Bias")


# -----------------------------
# CHART
# -----------------------------
st.plotly_chart(plot_chart(df), use_container_width=True)


# -----------------------------
# NEWS
# -----------------------------
st.subheader("News")
for n in news[:10]:
    st.write("•", n.get("headline"))
    
