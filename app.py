import yfinance as yf
import pandas as pd
import numpy as np

def _try_ticker_variants(ticker: str):
    """Try ticker and common variants across exchanges."""
    variants = [ticker]
    base = ticker.split(".")[0]
    if "." not in ticker:
        # US ticker — prova anche listing europei
        variants += [f"{base}.MI", f"{base}.DE", f"{base}.PA", f"{base}.AS", f"{base}.L"]
    variants += [base]  # solo base come fallback
    return variants


def get_stock_data(ticker: str, period: str = "1y") -> dict:
    """Fetch all data for a given ticker, trying variants if needed."""
    try:
        # Try ticker and variants
        hist = pd.DataFrame()
        info = {}
        used_ticker = ticker

        for variant in _try_ticker_variants(ticker):
            try:
                stock = yf.Ticker(variant)
                h = stock.history(period="2y")
                if not h.empty and len(h) > 10:
                    hist = h
                    info = stock.info
                    used_ticker = variant
                    break
            except Exception:
                continue

        if hist.empty:
            return {"error": f"Nessun dato trovato per {ticker} — prova a inserire il ticker esatto (es. STM.MI, STM.PA, STM)"}

        ticker = used_ticker  # usa il ticker che ha funzionato

        # --- Technical indicators ---
        close = hist["Close"].astype(float)

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
        # Multiple fallbacks for current price
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if current_price is None:
            current_price = float(close.iloc[-1])
        current_price = round(float(current_price), 2)
        def safe_float(val):
            try:
                v = float(val)
                return None if (v != v) else v  # NaN check
            except:
                return None

        rsi_val = safe_float(hist["RSI"].iloc[-1]) or 50.0
        macd_val = safe_float(hist["MACD"].iloc[-1]) or 0.0
        macd_sig = safe_float(hist["MACD_signal"].iloc[-1]) or 0.0
        ma20 = safe_float(hist["MA20"].iloc[-1])
        ma50 = safe_float(hist["MA50"].iloc[-1])
        ma200 = safe_float(hist["MA200"].iloc[-1])
        bb_upper = safe_float(hist["BB_upper"].iloc[-1]) or current_price * 1.02
        bb_lower = safe_float(hist["BB_lower"].iloc[-1]) or current_price * 0.98

        # --- Fundamentals (multiple fallbacks for non-US tickers) ---
        def get_info(*keys, default=None):
            for k in keys:
                v = info.get(k)
                if v is not None and v != "" and v == v:  # not None, not NaN
                    try:
                        f = float(v)
                        if f != 0 or k in ["dividendYield"]:
                            return f
                    except (TypeError, ValueError):
                        return v
            return default

        pe = get_info("trailingPE", "forwardPE")
        pb = get_info("priceToBook")
        ev_ebitda = get_info("enterpriseToEbitda")
        roe = get_info("returnOnEquity")
        profit_margin = get_info("profitMargins", "netMargins")
        revenue_growth = get_info("revenueGrowth", "earningsGrowth")
        debt_equity = get_info("debtToEquity")
        dividend_yield = get_info("dividendYield", "trailingAnnualDividendYield")
        beta = get_info("beta")
        market_cap = info.get("marketCap") or info.get("enterpriseValue")
        analyst_target = get_info("targetMeanPrice", "targetMedianPrice")
        sector = info.get("sector") or info.get("categoryName") or "N/A"
        industry = info.get("industry") or info.get("fundFamily") or "N/A"
        name = info.get("longName") or info.get("shortName") or ticker
        currency = info.get("currency") or info.get("financialCurrency") or "USD"

        # Sanity check: filter out absurd values
        if pe and (pe < 0 or pe > 500): pe = None
        if pb and pb < 0: pb = None
        if roe and abs(roe) > 5: roe = None  # >500% ROE is a data error
        if debt_equity and debt_equity < 0: debt_equity = None

        # --- DCF Fair Value (simplified, capped) ---
        eps = info.get("trailingEps", None)
        forward_eps = info.get("forwardEps", None)
        growth_rate = revenue_growth if revenue_growth else 0.05
        growth_rate = min(max(growth_rate, 0.0), 0.20)  # cap at 20% — more realistic
        discount_rate = 0.10
        fair_value = None
        if eps and eps > 0:
            projected_eps = eps * (1 + growth_rate) ** 5
            terminal_value = projected_eps * 15
            fair_value = terminal_value / (1 + discount_rate) ** 5
            # Cap DCF: max 3x current price (avoids absurd values like freenet)
            fair_value = min(fair_value, current_price * 3.0)

        # --- Sector average P/E for relative valuation ---
        sector_pe_avg = {
            "Technology": 28, "Healthcare": 22, "Financial Services": 14,
            "Consumer Cyclical": 20, "Consumer Defensive": 22, "Energy": 12,
            "Utilities": 18, "Industrials": 20, "Basic Materials": 15,
            "Real Estate": 25, "Communication Services": 16,
        }.get(sector, 18)

        # Relative valuation: what price would match sector avg P/E?
        relative_value = None
        if eps and eps > 0 and pe:
            relative_value = round(eps * sector_pe_avg, 2)
            relative_value = min(relative_value, current_price * 2.5)

        # --- Multi-source target price (realistic weighted average) ---
        targets = []
        weights = []

        # 1. Analyst consensus — highest weight (most reliable)
        if analyst_target and analyst_target > 0:
            # Sanity: analyst target must be within ±60% of current price
            if 0.4 * current_price < analyst_target < 2.0 * current_price:
                targets.append(analyst_target)
                weights.append(0.45)

        # 2. Technical resistance (52-week high area)
        hist_52w = hist.tail(252)
        high_52w = float(hist_52w["High"].max())
        if high_52w > current_price:
            targets.append(high_52w)
            weights.append(0.20)

        # 3. Relative valuation vs sector P/E
        if relative_value and relative_value > current_price * 0.8:
            rel_capped = min(relative_value, current_price * 1.5)
            targets.append(rel_capped)
            weights.append(0.20)

        # 4. DCF (capped, lower weight since very sensitive to assumptions)
        if fair_value and fair_value > current_price:
            dcf_capped = min(fair_value, current_price * 1.5)
            targets.append(dcf_capped)
            weights.append(0.15)

        # 5. Fallback: modest technical upside
        if not targets:
            targets.append(current_price * 1.12)
            weights.append(1.0)

        # Weighted average target
        total_w = sum(weights)
        target_price = round(sum(t * w for t, w in zip(targets, weights)) / total_w, 2)

        # Final sanity: target must be between +5% and +50% of current price
        target_price = max(target_price, round(current_price * 1.05, 2))
        target_price = min(target_price, round(current_price * 1.50, 2))

        # --- Entry / Stop ---
        entry_price = round(current_price * 0.98 if rsi_val < 50 else current_price, 2)

        # Dynamic stop loss: based on ATR (volatility) not fixed 8%
        try:
            atr_stop = float((hist["High"] - hist["Low"]).tail(14).mean())
            stop_loss = round(current_price - (atr_stop * 2), 2)
            # Min stop: 5%, Max stop: 12%
            stop_loss = max(stop_loss, round(current_price * 0.88, 2))
            stop_loss = min(stop_loss, round(current_price * 0.95, 2))
        except:
            stop_loss = round(current_price * 0.92, 2)

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

        # --- Upside & Guadagno netto ---
        upside = ((target_price - current_price) / current_price * 100) if target_price else None
        upside_net = round(upside * 0.74, 1) if upside else None  # al netto 26% capital gain Italia

        # --- Stima tempo al target ---
        # Calcola ATR (Average True Range) su 20 giorni = volatilità giornaliera media
        atr = None
        daily_move_pct = None
        try:
            high_low = hist["High"] - hist["Low"]
            atr_20 = float(high_low.tail(20).mean())
            atr = round(atr_20, 2)
            daily_move_pct = (atr_20 / current_price) * 100  # % movimento giornaliero medio
        except Exception:
            pass

        # Stima giorni lavorativi al target
        estimated_days = None
        estimated_months = None
        time_label = None
        annualized_return = None

        if upside and upside > 0 and daily_move_pct and daily_move_pct > 0:
            # Aggiusta per beta (titoli più volatili si muovono più velocemente)
            beta_factor = min(max(beta if beta else 1.0, 0.3), 3.0)
            # Efficienza del movimento: non tutti i giorni vanno nella direzione giusta
            # In media un titolo percorre ~40-60% del suo potenziale ATR nella direzione desiderata
            effective_daily_pct = daily_move_pct * 0.45 * beta_factor
            effective_daily_pct = max(effective_daily_pct, 0.05)  # minimo 0.05%/giorno

            estimated_days = int(upside / effective_daily_pct)
            estimated_days = max(5, min(estimated_days, 500))  # cap tra 1 settimana e 2 anni

            # Converti in mesi lavorativi (21 giorni = 1 mese)
            estimated_months = round(estimated_days / 21, 1)

            # Label descrittiva
            if estimated_months <= 1:
                time_label = f"~{estimated_days} giorni lavorativi (breve termine)"
                time_category = "🔵 Breve (< 1 mese)"
            elif estimated_months <= 3:
                time_label = f"~{round(estimated_months, 0):.0f} mesi (breve/medio)"
                time_category = "🟢 Breve/Medio (1-3 mesi)"
            elif estimated_months <= 6:
                time_label = f"~{round(estimated_months, 0):.0f} mesi (medio termine)"
                time_category = "🟡 Medio (3-6 mesi)"
            elif estimated_months <= 12:
                time_label = f"~{round(estimated_months, 0):.0f} mesi (lungo termine)"
                time_category = "🟠 Lungo (6-12 mesi)"
            else:
                time_label = f"~{round(estimated_months/12, 1):.1f} anni (molto lungo)"
                time_category = "🔴 Molto lungo (> 1 anno)"

            # Rendimento annualizzato
            if estimated_months > 0:
                annualized_return = round(upside / (estimated_months / 12), 1)
                annualized_return = min(annualized_return, 999)  # cap
        else:
            time_category = "N/A"
            time_label = "N/A"

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
            "upside_net_pct": upside_net,
            "time_label": time_label,
            "time_category": time_category,
            "estimated_months": estimated_months,
            "annualized_return": annualized_return,
            "atr": atr,
            "daily_move_pct": round(daily_move_pct, 2) if daily_move_pct else None,
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
