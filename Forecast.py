import streamlit as st
import requests
import pandas as pd
import numpy as np
import time
import plotly.graph_objects as go

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="TradeAI Pro", layout="wide")

FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", None)
BASE_URL = "https://finnhub.io/api/v1"

if not FINNHUB_API_KEY:
    st.error("Missing API key (FINNHUB_API_KEY in Streamlit secrets)")
    st.stop()


# -----------------------------
# SAFE API CALL
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
def search_symbols(q):
    data = get_json(f"{BASE_URL}/search", {
        "q": q,
        "token": FINNHUB_API_KEY
    })

    if not data or "result" not in data:
        return []

    return data["result"][:10]


# -----------------------------
# LIVE QUOTE
# -----------------------------
def get_quote(symbol):
    data = get_json(f"{BASE_URL}/quote", {
        "symbol": symbol,
        "token": FINNHUB_API_KEY
    })

    if not data or "c" not in data:
        return None

    return data


# -----------------------------
# CANDLES (FIXED + RELIABLE)
# -----------------------------
def get_candles(symbol):
    to_ts = int(time.time())
    from_ts = to_ts - 60 * 60 * 24 * 120  # last 120 days

    data = get_json(f"{BASE_URL}/stock/candle", {
        "symbol": symbol,
        "resolution": "D",
        "from": from_ts,
        "to": to_ts,
        "token": FINNHUB_API_KEY
    })

    if not data or data.get("s") != "ok":
        return None

    df = pd.DataFrame({
        "open": data.get("o", []),
        "high": data.get("h", []),
        "low": data.get("l", []),
        "close": data.get("c", []),
        "volume": data.get("v", [])
    })

    if df.empty:
        return None

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

    if not data or isinstance(data, dict):
        return []

    return data[:12]


def sentiment(news):
    if not news:
        return 0

    pos = ["growth", "beat", "strong", "upgrade", "profit", "recovery"]
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
# FORECAST MODEL (STABLE SIGNAL ENGINE)
# -----------------------------
def forecast(df, sent):
    close = df["close"]

    returns = np.log(close / close.shift(1)).fillna(0)

    ma_short = close.rolling(5).mean().iloc[-1]
    ma_long = close.rolling(20).mean().iloc[-1]

    trend = (ma_short - ma_long) / ma_long if ma_long else 0
    vol = returns.rolling(10).std().iloc[-1]

    score = (trend * 2.0) + (sent * 0.7) - (vol * 1.2)

    return score, trend, vol


# -----------------------------
# CHART
# -----------------------------
def chart(df):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Price"
    ))

    fig.add_trace(go.Scatter(
        y=df["close"].rolling(10).mean(),
        name="MA10"
    ))

    fig.update_layout(
        height=500,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=30, b=10)
    )

    return fig


# -----------------------------
# UI (TRADING STYLE)
# -----------------------------
st.title("📈 TradeAI Pro")

query = st.text_input("Search stocks (Apple, Tesla, SAP...)")

if not query:
    st.info("Enter a stock name to begin")
    st.stop()

results = search_symbols(query)

if not results:
    st.warning("No matches found")
    st.stop()

symbols = [r["symbol"] for r in results if r.get("symbol")]

symbol = st.selectbox("Select asset", symbols)

quote = get_quote(symbol)
df = get_candles(symbol)
news = get_news(symbol)

# -----------------------------
# SAFE CHECKS (IMPORTANT FIX)
# -----------------------------
if quote is None:
    st.error("Price data not available")
    st.stop()

if df is None:
    st.warning("No historical data — showing price only")

# -----------------------------
# SENTIMENT + FORECAST
# -----------------------------
sent = sentiment(news)

if df is not None:
    score, trend, vol = forecast(df, sent)
else:
    score, trend, vol = sent, 0, 0

# -----------------------------
# HEADER METRICS
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Price", quote["c"])
col2.metric("Change", round(quote["c"] - quote["pc"], 2))
col3.metric("Signal Score", round(score, 3))

# -----------------------------
# SIGNAL
# -----------------------------
if score > 0:
    st.success("🟢 Bullish bias")
else:
    st.error("🔴 Bearish bias")

# -----------------------------
# CHART
# -----------------------------
if df is not None:
    st.plotly_chart(chart(df), use_container_width=True)
else:
    st.info("Chart not available for this asset")

# -----------------------------
# NEWS
# -----------------------------
st.subheader("News")

if news:
    for n in news:
        st.write("•", n.get("headline"))
else:
    st.write("No news available")
    
