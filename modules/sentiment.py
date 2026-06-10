import requests
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()


def get_fear_greed() -> dict:
    """Fetch Fear & Greed Index with multiple fallbacks."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Try CNN primary URL
    urls = [
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                score = data["fear_and_greed"]["score"]
                rating = data["fear_and_greed"]["rating"]
                return {
                    "score": round(float(score)),
                    "rating": rating.replace("_", " ").title(),
                    "error": None
                }
        except Exception:
            continue

    # Fallback: derive sentiment from VIX and market data
    try:
        import yfinance as yf
        vix = float(yf.Ticker("^VIX").history(period="1d")["Close"].iloc[-1])
        spy_data = yf.Ticker("SPY").history(period="5d")["Close"]
        spy_change = (spy_data.iloc[-1] - spy_data.iloc[0]) / spy_data.iloc[0] * 100

        # Approximate F&G from VIX + SPY momentum
        score = 50
        if vix < 15: score += 20
        elif vix < 20: score += 10
        elif vix > 30: score -= 20
        elif vix > 25: score -= 10
        if spy_change > 2: score += 15
        elif spy_change > 0.5: score += 8
        elif spy_change < -2: score -= 15
        elif spy_change < -0.5: score -= 8
        score = max(5, min(95, score))

        if score <= 25: rating = "Extreme Fear"
        elif score <= 45: rating = "Fear"
        elif score <= 55: rating = "Neutral"
        elif score <= 75: rating = "Greed"
        else: rating = "Extreme Greed"

        return {"score": round(score), "rating": f"{rating} (stima)", "error": None}
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
