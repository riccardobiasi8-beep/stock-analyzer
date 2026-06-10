import requests
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()


def get_fear_greed() -> dict:
    """Fetch CNN Fear & Greed Index."""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        score = data["fear_and_greed"]["score"]
        rating = data["fear_and_greed"]["rating"]
        return {
            "score": round(score),
            "rating": rating.replace("_", " ").title(),
            "error": None
        }
    except Exception as e:
        return {"score": None, "rating": "N/A", "error": str(e)}


def get_news_sentiment(ticker: str) -> dict:
    """Get sentiment from Yahoo Finance news for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news

        if not news:
            return {"score": 0, "label": "Neutro", "articles": []}

        scores = []
        articles = []
        for item in news[:8]:
            title = item.get("title", "")
            if not title:
                continue
            vs = analyzer.polarity_scores(title)
            scores.append(vs["compound"])
            articles.append({
                "title": title,
                "score": round(vs["compound"], 2),
                "url": item.get("link", "#"),
                "publisher": item.get("publisher", ""),
            })

        avg = sum(scores) / len(scores) if scores else 0

        if avg >= 0.05:
            label = "😊 Positivo"
        elif avg <= -0.05:
            label = "😟 Negativo"
        else:
            label = "😐 Neutro"

        return {
            "score": round(avg, 3),
            "label": label,
            "articles": articles,
        }

    except Exception as e:
        return {"score": 0, "label": "N/A", "articles": [], "error": str(e)}


def get_macro_context() -> dict:
    """Simple macro context: VIX level + market breadth."""
    try:
        vix = yf.Ticker("^VIX")
        vix_price = vix.history(period="1d")["Close"].iloc[-1]

        if vix_price < 15:
            vix_label = "😌 Bassa volatilità — mercato tranquillo"
            vix_color = "green"
        elif vix_price < 25:
            vix_label = "😐 Volatilità moderata"
            vix_color = "orange"
        else:
            vix_label = "😰 Alta volatilità — mercato nervoso"
            vix_color = "red"

        return {
            "vix": round(float(vix_price), 1),
            "vix_label": vix_label,
            "vix_color": vix_color,
        }
    except Exception as e:
        return {"vix": None, "vix_label": "N/A", "vix_color": "gray", "error": str(e)}
