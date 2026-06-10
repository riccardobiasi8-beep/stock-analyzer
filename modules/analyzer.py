import yfinance as yf
import pandas as pd
import numpy as np

def get_stock_data(ticker: str, period: str = "1y") -> dict:
    """Fetch all data for a given ticker."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        info = stock.info

        if hist.empty:
            return {"error": f"Nessun dato trovato per {ticker}"}

        # --- Technical indicators ---
        close = hist["Close"]

        # Moving averages
        hist["MA20"] = close.rolling(20).mean()
        hist["MA50"] = close.rolling(50).mean()
        hist["MA200"] = close.rolling(200).mean()

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        hist["RSI"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        hist["MACD"] = ema12 - ema26
        hist["MACD_signal"] = hist["MACD"].ewm(span=9).mean()

        # Bollinger Bands
        hist["BB_mid"] = close.rolling(20).mean()
        std = close.rolling(20).std()
        hist["BB_upper"] = hist["BB_mid"] + 2 * std
        hist["BB_lower"] = hist["BB_mid"] - 2 * std

        # Support & Resistance (last 3 months)
        recent = hist.tail(63)
        support = float(recent["Low"].min())
        resistance = float(recent["High"].max())

        # --- Current values ---
        current_price = float(close.iloc[-1])
        rsi_val = float(hist["RSI"].iloc[-1])
        macd_val = float(hist["MACD"].iloc[-1])
        macd_sig = float(hist["MACD_signal"].iloc[-1])
        ma20 = float(hist["MA20"].iloc[-1]) if not pd.isna(hist["MA20"].iloc[-1]) else None
        ma50 = float(hist["MA50"].iloc[-1]) if not pd.isna(hist["MA50"].iloc[-1]) else None
        ma200 = float(hist["MA200"].iloc[-1]) if not pd.isna(hist["MA200"].iloc[-1]) else None
        bb_upper = float(hist["BB_upper"].iloc[-1])
        bb_lower = float(hist["BB_lower"].iloc[-1])

        # --- Fundamentals ---
        pe = info.get("trailingPE", None)
        pb = info.get("priceToBook", None)
        ev_ebitda = info.get("enterpriseToEbitda", None)
        roe = info.get("returnOnEquity", None)
        profit_margin = info.get("profitMargins", None)
        revenue_growth = info.get("revenueGrowth", None)
        debt_equity = info.get("debtToEquity", None)
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        name = info.get("longName", ticker)
        currency = info.get("currency", "USD")
        market_cap = info.get("marketCap", None)
        analyst_target = info.get("targetMeanPrice", None)
        dividend_yield = info.get("dividendYield", None)
        beta = info.get("beta", None)

        # --- DCF Fair Value (simplified) ---
        eps = info.get("trailingEps", None)
        growth_rate = revenue_growth if revenue_growth else 0.05
        growth_rate = min(max(growth_rate, 0.0), 0.30)
        discount_rate = 0.10
        fair_value = None
        if eps and eps > 0:
            projected_eps = eps * (1 + growth_rate) ** 5
            terminal_value = projected_eps * 15
            fair_value = terminal_value / (1 + discount_rate) ** 5

        # --- Entry / Target / Stop ---
        entry_price = None
        target_price = None
        stop_loss = None

        if ma50 and rsi_val < 50:
            entry_price = round(current_price * 0.98, 2)  # slight dip entry
        else:
            entry_price = round(current_price, 2)

        if fair_value and fair_value > current_price:
            target_price = round(fair_value, 2)
        elif analyst_target and analyst_target > current_price:
            target_price = round(analyst_target, 2)
        elif resistance > current_price:
            target_price = round(resistance, 2)
        else:
            target_price = round(current_price * 1.15, 2)

        stop_loss = round(current_price * 0.92, 2)  # 8% stop loss

        # --- Composite score (0-100) ---
        score = 50  # neutral base

        # Technical signals
        if rsi_val < 35: score += 15
        elif rsi_val < 45: score += 8
        elif rsi_val > 70: score -= 15
        elif rsi_val > 60: score -= 8

        if macd_val > macd_sig: score += 10
        else: score -= 5

        if ma50 and current_price > ma50: score += 8
        else: score -= 8

        if ma200 and current_price > ma200: score += 7
        else: score -= 7

        if current_price < bb_lower: score += 10
        elif current_price > bb_upper: score -= 10

        # Fundamental signals
        if pe and 5 < pe < 20: score += 10
        elif pe and pe > 40: score -= 10

        if pb and pb < 1.5: score += 8
        elif pb and pb > 5: score -= 5

        if fair_value and fair_value > current_price * 1.1: score += 12
        elif fair_value and fair_value < current_price * 0.9: score -= 12

        if roe and roe > 0.15: score += 5
        if profit_margin and profit_margin > 0.10: score += 5
        if revenue_growth and revenue_growth > 0.10: score += 5
        if debt_equity and debt_equity > 2: score -= 8

        score = max(0, min(100, score))

        # --- Signal label ---
        if score >= 65:
            signal = "🟢 BUY"
        elif score >= 45:
            signal = "🟡 HOLD"
        else:
            signal = "🔴 SELL / AVOID"

        # Upside potential
        upside = ((target_price - current_price) / current_price * 100) if target_price else None

        return {
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "currency": currency,
            "market_cap": market_cap,
            "current_price": current_price,
            "entry_price": entry_price,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "upside_pct": round(upside, 1) if upside else None,
            "fair_value": round(fair_value, 2) if fair_value else None,
            "analyst_target": analyst_target,
            "signal": signal,
            "score": round(score),
            "rsi": round(rsi_val, 1),
            "macd": round(macd_val, 4),
            "macd_signal": round(macd_sig, 4),
            "ma20": round(ma20, 2) if ma20 else None,
            "ma50": round(ma50, 2) if ma50 else None,
            "ma200": round(ma200, 2) if ma200 else None,
            "bb_upper": round(bb_upper, 2),
            "bb_lower": round(bb_lower, 2),
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "pe": round(pe, 1) if pe else None,
            "pb": round(pb, 2) if pb else None,
            "ev_ebitda": round(ev_ebitda, 1) if ev_ebitda else None,
            "roe": round(roe * 100, 1) if roe else None,
            "profit_margin": round(profit_margin * 100, 1) if profit_margin else None,
            "revenue_growth": round(revenue_growth * 100, 1) if revenue_growth else None,
            "debt_equity": round(debt_equity, 2) if debt_equity else None,
            "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield else None,
            "beta": round(beta, 2) if beta else None,
            "hist": hist,
            "support": round(support, 2),
            "resistance": round(resistance, 2),
        }

    except Exception as e:
        return {"error": str(e)}


def get_sector_pe(sector: str) -> float:
    """Approximate average P/E by sector."""
    sector_pe = {
        "Technology": 28,
        "Healthcare": 22,
        "Financial Services": 14,
        "Consumer Cyclical": 20,
        "Consumer Defensive": 22,
        "Energy": 12,
        "Utilities": 18,
        "Industrials": 20,
        "Basic Materials": 15,
        "Real Estate": 25,
        "Communication Services": 20,
    }
    return sector_pe.get(sector, 18)
