import requests
import pandas as pd
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()


# ══════════════════════════════════════════════════════════════════════════════
# MACRO
# ══════════════════════════════════════════════════════════════════════════════

def get_fear_greed() -> dict:
    """Fetch Fear & Greed Index with multiple fallbacks."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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
                return {"score": round(float(score)), "rating": rating.replace("_", " ").title(), "error": None}
        except Exception:
            continue

    # Fallback: stima da VIX + SPY
    try:
        import yfinance as yf
        vix = float(yf.Ticker("^VIX").history(period="1d")["Close"].iloc[-1])
        spy_data = yf.Ticker("SPY").history(period="5d")["Close"]
        spy_change = (spy_data.iloc[-1] - spy_data.iloc[0]) / spy_data.iloc[0] * 100
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


def get_macro_context() -> dict:
    """VIX level."""
    try:
        vix = yf.Ticker("^VIX")
        vix_price = vix.history(period="1d")["Close"].iloc[-1]
        if vix_price < 15: vix_label = "😌 Bassa volatilità — mercato tranquillo"; vix_color = "green"
        elif vix_price < 25: vix_label = "😐 Volatilità moderata"; vix_color = "orange"
        else: vix_label = "😰 Alta volatilità — mercato nervoso"; vix_color = "red"
        return {"vix": round(float(vix_price), 1), "vix_label": vix_label, "vix_color": vix_color}
    except Exception as e:
        return {"vix": None, "vix_label": "N/A", "vix_color": "gray", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# NEWS SENTIMENT
# ══════════════════════════════════════════════════════════════════════════════

def get_news_sentiment(ticker: str) -> dict:
    """Sentiment from Yahoo Finance news — handles both old and new yfinance formats."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news:
            return {"score": 0, "label": "Neutro", "articles": []}

        scores = []
        articles = []
        for item in news[:10]:
            # yfinance >= 0.2.40 wraps content in "content" key
            if "content" in item and isinstance(item["content"], dict):
                inner = item["content"]
                title = inner.get("title", "")
                url = inner.get("canonicalUrl", {}).get("url", "#") if isinstance(inner.get("canonicalUrl"), dict) else inner.get("clickThroughUrl", {}).get("url", "#")
                publisher = inner.get("provider", {}).get("displayName", "") if isinstance(inner.get("provider"), dict) else ""
            else:
                title = item.get("title", "")
                url = item.get("link", item.get("url", "#"))
                publisher = item.get("publisher", item.get("source", ""))

            if not title:
                continue

            vs = analyzer.polarity_scores(title)
            scores.append(vs["compound"])
            articles.append({
                "title": title,
                "score": round(vs["compound"], 2),
                "url": url or "#",
                "publisher": publisher or "",
            })

        avg = sum(scores) / len(scores) if scores else 0
        if avg >= 0.05: label = "😊 Positivo"
        elif avg <= -0.05: label = "😟 Negativo"
        else: label = "😐 Neutro"
        return {"score": round(avg, 3), "label": label, "articles": articles}
    except Exception as e:
        return {"score": 0, "label": "N/A", "articles": [], "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# ANALYST CONSENSUS
# ══════════════════════════════════════════════════════════════════════════════

def get_analyst_consensus(ticker: str) -> dict:
    """Analyst ratings and price targets from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        current = info.get("currentPrice") or info.get("regularMarketPrice")
        rec = info.get("recommendationKey", "").replace("_", " ").title()
        n_analysts = info.get("numberOfAnalystOpinions", 0)

        # Recommendation ratings breakdown
        try:
            recs = stock.recommendations
            if recs is not None and not recs.empty:
                latest = recs.tail(5)
                strong_buy = int(latest.get("strongBuy", pd.Series([0])).sum()) if hasattr(latest, 'get') else 0
                buy = int(latest.get("buy", pd.Series([0])).sum()) if hasattr(latest, 'get') else 0
                hold = int(latest.get("hold", pd.Series([0])).sum()) if hasattr(latest, 'get') else 0
                sell = int(latest.get("sell", pd.Series([0])).sum()) if hasattr(latest, 'get') else 0
                strong_sell = int(latest.get("strongSell", pd.Series([0])).sum()) if hasattr(latest, 'get') else 0
            else:
                strong_buy = buy = hold = sell = strong_sell = 0
        except Exception:
            strong_buy = buy = hold = sell = strong_sell = 0

        upside = None
        if target_mean and current:
            upside = round((target_mean - current) / current * 100, 1)

        # Sentiment label
        if rec in ["Strong Buy", "Buy"]: consensus_label = "🟢 Buy"
        elif rec in ["Hold", "Neutral"]: consensus_label = "🟡 Hold"
        elif rec in ["Sell", "Strong Sell", "Underperform"]: consensus_label = "🔴 Sell"
        else: consensus_label = "⚪ N/A"

        return {
            "recommendation": rec or "N/A",
            "consensus_label": consensus_label,
            "n_analysts": n_analysts,
            "target_mean": round(target_mean, 2) if target_mean else None,
            "target_high": round(target_high, 2) if target_high else None,
            "target_low": round(target_low, 2) if target_low else None,
            "upside": upside,
            "strong_buy": strong_buy,
            "buy": buy,
            "hold": hold,
            "sell": sell,
            "strong_sell": strong_sell,
        }
    except Exception as e:
        return {"recommendation": "N/A", "consensus_label": "⚪ N/A", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# SHORT INTEREST
# ══════════════════════════════════════════════════════════════════════════════

def get_short_interest(ticker: str) -> dict:
    """Short interest data from Yahoo Finance."""
    try:
        info = yf.Ticker(ticker).info
        short_pct = info.get("shortPercentOfFloat")
        short_ratio = info.get("shortRatio")  # days to cover
        shares_short = info.get("sharesShort")
        shares_short_prior = info.get("sharesShortPriorMonth")

        change_pct = None
        if shares_short and shares_short_prior and shares_short_prior > 0:
            change_pct = round((shares_short - shares_short_prior) / shares_short_prior * 100, 1)

        # Interpret
        if short_pct is None:
            label = "N/A"
            color = "gray"
        elif short_pct > 0.20:
            label = "🔴 Alto — mercato scommette al ribasso"
            color = "red"
        elif short_pct > 0.10:
            label = "🟡 Moderato"
            color = "orange"
        else:
            label = "🟢 Basso — poca pressione ribassista"
            color = "green"

        return {
            "short_pct": round(short_pct * 100, 1) if short_pct else None,
            "short_ratio": round(short_ratio, 1) if short_ratio else None,
            "change_pct": change_pct,
            "label": label,
            "color": color,
        }
    except Exception as e:
        return {"short_pct": None, "label": "N/A", "color": "gray", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# INSIDER TRADING
# ══════════════════════════════════════════════════════════════════════════════

def get_insider_activity(ticker: str) -> dict:
    """Insider buying/selling from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        insider = stock.insider_transactions

        if insider is None or insider.empty:
            return {"label": "N/A", "transactions": [], "net_sentiment": 0}

        import pandas as pd
        recent = insider.head(10)
        transactions = []
        buys = 0
        sells = 0

        for _, row in recent.iterrows():
            try:
                shares = row.get("Shares", 0) or 0
                value = row.get("Value", 0) or 0
                text = str(row.get("Text", "") or row.get("Transaction", "")).lower()
                insider_name = str(row.get("Insider", "") or row.get("Name", ""))
                date = str(row.get("Start Date", "") or row.get("Date", ""))[:10]

                is_buy = any(w in text for w in ["purchase", "buy", "acqui"])
                is_sell = any(w in text for w in ["sale", "sell", "sold"])

                if is_buy:
                    buys += 1
                    direction = "🟢 Acquisto"
                elif is_sell:
                    sells += 1
                    direction = "🔴 Vendita"
                else:
                    direction = "⚪ Altro"

                transactions.append({
                    "name": insider_name[:30],
                    "direction": direction,
                    "shares": int(shares) if shares else 0,
                    "value": int(value) if value else 0,
                    "date": date,
                })
            except Exception:
                continue

        total = buys + sells
        if total == 0:
            label = "😐 Nessuna attività recente"
            net = 0
        elif buys > sells * 2:
            label = "🟢 Insider stanno comprando"
            net = 1
        elif sells > buys * 2:
            label = "🔴 Insider stanno vendendo"
            net = -1
        else:
            label = "😐 Attività mista"
            net = 0

        return {
            "label": label,
            "buys": buys,
            "sells": sells,
            "net_sentiment": net,
            "transactions": transactions[:6],
        }
    except Exception as e:
        return {"label": "N/A", "transactions": [], "net_sentiment": 0, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# EARNINGS SURPRISE
# ══════════════════════════════════════════════════════════════════════════════

def get_earnings_surprise(ticker: str) -> dict:
    """Last earnings vs estimates."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        eps_actual = info.get("trailingEps")
        eps_estimate = info.get("epsForward")
        earnings_growth = info.get("earningsGrowth")
        revenue_growth = info.get("revenueGrowth")
        next_earnings = info.get("earningsTimestamp")

        # Try earnings history
        try:
            hist = stock.earnings_history
            if hist is not None and not hist.empty:
                last = hist.tail(4)
                surprises = []
                for _, row in last.iterrows():
                    actual = row.get("epsActual", 0)
                    estimate = row.get("epsEstimate", 0)
                    if estimate and estimate != 0:
                        surprise_pct = (actual - estimate) / abs(estimate) * 100
                        surprises.append(round(surprise_pct, 1))
                avg_surprise = round(sum(surprises) / len(surprises), 1) if surprises else None
            else:
                avg_surprise = None
                surprises = []
        except Exception:
            avg_surprise = None
            surprises = []

        # Label
        if avg_surprise is None:
            label = "N/A"
            color = "gray"
        elif avg_surprise > 5:
            label = f"🟢 Batte le stime in media del +{avg_surprise}%"
            color = "green"
        elif avg_surprise > 0:
            label = f"🟡 Leggermente sopra le stime (+{avg_surprise}%)"
            color = "orange"
        elif avg_surprise > -5:
            label = f"🟡 Leggermente sotto le stime ({avg_surprise}%)"
            color = "orange"
        else:
            label = f"🔴 Manca le stime in media del {avg_surprise}%"
            color = "red"

        import datetime
        next_date = None
        if next_earnings:
            try:
                next_date = datetime.datetime.fromtimestamp(next_earnings).strftime("%d/%m/%Y")
            except Exception:
                pass

        return {
            "avg_surprise": avg_surprise,
            "surprises": surprises,
            "label": label,
            "color": color,
            "earnings_growth": round(earnings_growth * 100, 1) if earnings_growth else None,
            "revenue_growth": round(revenue_growth * 100, 1) if revenue_growth else None,
            "next_earnings": next_date,
        }
    except Exception as e:
        return {"avg_surprise": None, "label": "N/A", "color": "gray", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# OPTIONS SENTIMENT (Put/Call Ratio)
# ══════════════════════════════════════════════════════════════════════════════

def get_options_sentiment(ticker: str) -> dict:
    """Put/Call ratio from options chain."""
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations:
            return {"put_call_ratio": None, "label": "N/A", "color": "gray"}

        # Use nearest expiration
        opt = stock.option_chain(expirations[0])
        calls_vol = opt.calls["volume"].fillna(0).sum()
        puts_vol = opt.puts["volume"].fillna(0).sum()

        if calls_vol == 0:
            return {"put_call_ratio": None, "label": "N/A", "color": "gray"}

        ratio = round(puts_vol / calls_vol, 2)

        if ratio < 0.7:
            label = f"🟢 Ratio {ratio} — mercato ottimista (più call che put)"
            color = "green"
        elif ratio < 1.0:
            label = f"🟡 Ratio {ratio} — sentiment neutro/positivo"
            color = "orange"
        elif ratio < 1.3:
            label = f"🟡 Ratio {ratio} — sentiment neutro/negativo"
            color = "orange"
        else:
            label = f"🔴 Ratio {ratio} — mercato pessimista (più put che call)"
            color = "red"

        return {
            "put_call_ratio": ratio,
            "calls_volume": int(calls_vol),
            "puts_volume": int(puts_vol),
            "label": label,
            "color": color,
        }
    except Exception as e:
        return {"put_call_ratio": None, "label": "N/A", "color": "gray", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# REDDIT MENTIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_reddit_mentions(ticker: str) -> dict:
    """Search Reddit for ticker mentions using public API."""
    try:
        headers = {"User-Agent": "StockAnalyzer/1.0"}
        subreddits = ["wallstreetbets", "investing", "stocks"]
        total_mentions = 0
        posts = []

        for sub in subreddits:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={ticker}&sort=new&limit=5&t=week"
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code != 200:
                continue
            data = r.json()
            items = data.get("data", {}).get("children", [])
            for item in items:
                p = item.get("data", {})
                title = p.get("title", "")
                score = p.get("score", 0)
                if ticker.upper() in title.upper() or ticker.split(".")[0].upper() in title.upper():
                    total_mentions += 1
                    sentiment = analyzer.polarity_scores(title)["compound"]
                    posts.append({
                        "title": title[:80],
                        "subreddit": sub,
                        "score": score,
                        "sentiment": round(sentiment, 2),
                        "url": f"https://reddit.com{p.get('permalink', '')}",
                    })

        posts = sorted(posts, key=lambda x: x["score"], reverse=True)[:5]

        if total_mentions == 0:
            label = "😐 Nessuna menzione recente su Reddit"
            color = "gray"
        elif total_mentions >= 5:
            label = f"🔥 {total_mentions} menzioni questa settimana — titolo caldo"
            color = "green"
        else:
            label = f"💬 {total_mentions} menzioni questa settimana"
            color = "orange"

        avg_sentiment = 0
        if posts:
            avg_sentiment = round(sum(p["sentiment"] for p in posts) / len(posts), 2)

        return {
            "mentions": total_mentions,
            "label": label,
            "color": color,
            "avg_sentiment": avg_sentiment,
            "posts": posts,
        }
    except Exception as e:
        return {"mentions": 0, "label": "N/A", "color": "gray", "posts": [], "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE TRENDS
# ══════════════════════════════════════════════════════════════════════════════

def get_google_trends(ticker: str, company_name: str = "") -> dict:
    """Google Trends interest via unofficial endpoint."""
    try:
        query = company_name.split(" ")[0] if company_name else ticker.split(".")[0]
        url = (
            f"https://trends.google.com/trends/api/dailytrends"
            f"?hl=en-US&tz=-60&geo=US&ns=15"
        )
        # Use pytrends-style request
        headers = {"User-Agent": "Mozilla/5.0"}
        # Simple search volume proxy via autocomplete
        suggest_url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}+stock"
        r = requests.get(suggest_url, headers=headers, timeout=5)

        if r.status_code == 200:
            data = r.json()
            suggestions = data[1] if len(data) > 1 else []
            relevant = [s for s in suggestions if query.lower() in s.lower()]
            trending = len(relevant) >= 2

            if trending:
                label = f"📈 '{query}' nelle ricerche trending"
                color = "green"
            else:
                label = f"📊 Interesse normale per '{query}'"
                color = "gray"

            return {
                "query": query,
                "label": label,
                "color": color,
                "suggestions": suggestions[:5],
                "trending": trending,
            }

        return {"query": query, "label": "N/A", "color": "gray", "trending": False}
    except Exception as e:
        return {"query": ticker, "label": "N/A", "color": "gray", "trending": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# SENTIMENT AGGREGATO
# ══════════════════════════════════════════════════════════════════════════════

def get_full_sentiment(ticker: str, company_name: str = "") -> dict:
    """Aggregate all sentiment sources into a single score."""
    news = get_news_sentiment(ticker)
    analyst = get_analyst_consensus(ticker)
    short = get_short_interest(ticker)
    insider = get_insider_activity(ticker)
    earnings = get_earnings_surprise(ticker)
    options = get_options_sentiment(ticker)
    reddit = get_reddit_mentions(ticker)
    trends = get_google_trends(ticker, company_name)

    # Aggregate score 0-100
    score = 50
    weights = 0

    # News sentiment
    if news["score"] != 0:
        score += news["score"] * 15
        weights += 1

    # Analyst consensus
    rec = analyst.get("recommendation", "").lower()
    if "strong buy" in rec: score += 15; weights += 1
    elif "buy" in rec: score += 10; weights += 1
    elif "hold" in rec: score += 0; weights += 1
    elif "sell" in rec or "underperform" in rec: score -= 10; weights += 1

    # Analyst upside
    if analyst.get("upside"):
        if analyst["upside"] > 20: score += 10
        elif analyst["upside"] > 5: score += 5
        elif analyst["upside"] < -10: score -= 10
        weights += 1

    # Short interest
    sp = short.get("short_pct")
    if sp:
        if sp > 20: score -= 12
        elif sp > 10: score -= 5
        else: score += 5
        weights += 1

    # Insider
    net_ins = insider.get("net_sentiment", 0)
    if net_ins == 1: score += 10; weights += 1
    elif net_ins == -1: score -= 8; weights += 1

    # Earnings
    avg_s = earnings.get("avg_surprise")
    if avg_s is not None:
        if avg_s > 5: score += 8
        elif avg_s > 0: score += 3
        elif avg_s < -5: score -= 8
        elif avg_s < 0: score -= 3
        weights += 1

    # Options
    pcr = options.get("put_call_ratio")
    if pcr:
        if pcr < 0.7: score += 8
        elif pcr > 1.3: score -= 8
        weights += 1

    # Reddit
    if reddit.get("mentions", 0) > 3: score += 5; weights += 1

    score = max(0, min(100, round(score)))

    if score >= 65: overall = "🟢 Sentiment Positivo"
    elif score >= 45: overall = "🟡 Sentiment Neutro"
    else: overall = "🔴 Sentiment Negativo"

    return {
        "overall": overall,
        "score": score,
        "news": news,
        "analyst": analyst,
        "short": short,
        "insider": insider,
        "earnings": earnings,
        "options": options,
        "reddit": reddit,
        "trends": trends,
    }
