from fastapi import FastAPI
import requests
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

app = FastAPI(title="Trading-Grade Forecast Engine")

FINNHUB_API_KEY = "d8sjampr01qh5rere5ogd8sjampr01qh5rere5p0"
BASE_URL = "https://finnhub.io/api/v1"


# -----------------------------
# PRICE HISTORY (CRITICAL)
# -----------------------------
def get_candles(symbol: str):
    url = f"{BASE_URL}/stock/candle"

    params = {
        "symbol": symbol,
        "resolution": "60",  # hourly candles
        "from": 1700000000,   # fixed demo timestamps
        "to": 1703000000,
        "token": FINNHUB_API_KEY
    }

    r = requests.get(url, params=params)
    data = r.json()

    if data.get("s") != "ok":
        return None

    df = pd.DataFrame({
        "c": data["c"],
        "h": data["h"],
        "l": data["l"],
        "o": data["o"],
        "v": data["v"]
    })

    return df


# -----------------------------
# NEWS SENTIMENT
# -----------------------------
def get_news(symbol: str):
    url = f"{BASE_URL}/company-news"
    params = {
        "symbol": symbol,
        "from": "2025-01-01",
        "to": "2026-12-31",
        "token": FINNHUB_API_KEY
    }

    r = requests.get(url, params=params)
    return r.json()[:20]


def sentiment(news):
    pos = ["growth", "beat", "strong", "upgrade", "recovery"]
    neg = ["crash", "weak", "drop", "lawsuit", "risk", "inflation"]

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
# FEATURE ENGINEERING (REAL QUANT STYLE)
# -----------------------------
def build_features(df, news_sentiment):

    df = df.copy()

    # log returns
    df["return"] = np.log(df["c"] / df["c"].shift(1))
    df["volatility"] = df["return"].rolling(5).std()

    df = df.dropna()

    features = []

    for i in range(len(df) - 1):
        features.append([
            df["return"].iloc[i],
            df["volatility"].iloc[i],
            df["v"].iloc[i],  # volume
            news_sentiment
        ])

    X = np.array(features)

    # target = next return
    y = df["return"].iloc[1:].values

    return X, y


# -----------------------------
# MODEL (REALISTIC APPROACH)
# -----------------------------
@app.get("/forecast")
def forecast(symbol: str):

    df = get_candles(symbol)
    if df is None or len(df) < 50:
        return {"error": "not enough data"}

    news = get_news(symbol)
    news_sentiment = sentiment(news)

    X, y = build_features(df, news_sentiment)

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=6,
        random_state=42
    )

    model.fit(X, y)

    latest_features = X[-1].reshape(1, -1)

    pred_return = model.predict(latest_features)[0]

    direction = "bullish" if pred_return > 0 else "bearish"

    return {
        "symbol": symbol,
        "predicted_return": float(pred_return),
        "direction": direction,
        "news_sentiment": news_sentiment,
        "volatility_proxy": float(X[-1][1])
    }


# -----------------------------
# SEARCH
# -----------------------------
@app.get("/search")
def search(query: str):
    url = f"{BASE_URL}/search"
    r = requests.get(url, params={"q": query, "token": FINNHUB_API_KEY})
    data = r.json()

    return data.get("result", [])[:10]
