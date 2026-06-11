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
                if v is not None and v != "":
                    try:
                        f = float(v)
                        # Filter NaN/Inf
                        import math
                        if math.isnan(f) or math.isinf(f):
                            continue
                        if f != 0 or k in ["dividendYield"]:
                            return round(f, 4)
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
        currency = info.get("currency") or info.get("financialCurrency") or ""
        if not currency:
            if any(s in ticker for s in [".MI", ".PA", ".DE", ".AS", ".BR", ".MC", ".F", ".L"]):
                currency = "EUR" if ".L" not in ticker else "GBP"
            elif ".KS" in ticker or ".KQ" in ticker:
                currency = "KRW"
            elif ".T" in ticker or ".JP" in ticker:
                currency = "JPY"
            elif ".HK" in ticker:
                currency = "HKD"
            else:
                currency = "USD"

        # Fix current_price if NaN — use last valid close
        import math as _math
        if current_price is None or _math.isnan(current_price):
            try:
                current_price = round(float(hist["Close"].dropna().iloc[-1]), 2)
            except Exception:
                return {"error": f"Prezzo non disponibile per {ticker}"}

        # Sanity check: filter out absurd values BEFORE passing to Gemini
        # (Gemini will re-estimate these)
        if pe and (pe < 0 or pe > 500): pe = None
        # FIX 4: P/E impossibile se azienda in perdita (margine negativo)
        if profit_margin is not None and profit_margin < 0:
            pe = None  # utili negativi → P/E non calcolabile
        if pb and pb < 0: pb = abs(pb)
        if roe and abs(roe) > 5: roe = None       # Yahoo returns ROE as decimal, >5 = >500% anomaly
        if profit_margin and abs(profit_margin) > 2: profit_margin = None  # >200% impossible
        if debt_equity and debt_equity < 0: debt_equity = None
        if dividend_yield and dividend_yield > 0.5: dividend_yield = None  # >50% impossible

        # ══════════════════════════════════════════════════════════════════
        # FAIR VALUE — 3 PILASTRI PROFESSIONALI
        # ══════════════════════════════════════════════════════════════════

        eps = info.get("trailingEps")
        forward_eps = info.get("forwardEps") or eps
        analyst_target = get_info("targetMeanPrice", "targetMedianPrice")
        analyst_high = get_info("targetHighPrice")
        analyst_low = get_info("targetLowPrice")
        n_analysts = info.get("numberOfAnalystOpinions", 0) or 0

        # ── PILASTRO 1: Consensus analisti (peso 50%) ─────────────────────
        # Usiamo il target mediano se disponibile, altrimenti la media
        # Solo se basato su almeno 3 analisti e entro range ragionevole
        pillar1_consensus = None
        try:
            if analyst_target and float(n_analysts) >= 3:
                at = float(analyst_target)
                # Sanity: deve essere entro -40%/+100% dal prezzo attuale
                if 0.6 * current_price < at < 2.0 * current_price:
                    pillar1_consensus = at
        except Exception:
            pass

        # ── PILASTRO 2: Multipli comparabili settore (peso 30%) ──────────
        # P/E medio settore × EPS forward (più conservativo del trailing)
        sector_pe_map = {
            "Technology": 25, "Healthcare": 20, "Financial Services": 12,
            "Consumer Cyclical": 18, "Consumer Defensive": 20, "Energy": 11,
            "Utilities": 16, "Industrials": 18, "Basic Materials": 13,
            "Real Estate": 22, "Communication Services": 14,
        }
        sector_pe_avg = sector_pe_map.get(str(sector), 16)
        pillar2_multiples = None
        try:
            use_eps = float(forward_eps) if forward_eps and float(forward_eps) > 0 else (
                      float(eps) if eps and float(eps) > 0 else None)
            if use_eps:
                pillar2_multiples = round(use_eps * sector_pe_avg, 2)
                # Sanity: non più di +80% dal prezzo attuale
                pillar2_multiples = min(pillar2_multiples, current_price * 1.80)
                if pillar2_multiples < current_price * 0.5:
                    pillar2_multiples = None  # anomalia dati
        except Exception:
            pillar2_multiples = None

        # ── PILASTRO 3: DCF conservativo (peso 20%) ───────────────────────
        # Growth rate: min tra storico e 3% per aziende mature (max 8%)
        # WACC: 8% aziende stabili, 10% medie, 12% rischiose (beta > 1.5)
        pillar3_dcf = None
        try:
            use_eps_dcf = float(forward_eps) if forward_eps and float(forward_eps) > 0 else (
                          float(eps) if eps and float(eps) > 0 else None)
            if use_eps_dcf:
                hist_growth = float(revenue_growth) if revenue_growth else 0.02
                # Conservativo: cap al 8%, floor a 0%
                conservative_growth = min(max(hist_growth * 0.6, 0.0), 0.08)

                # WACC basato su beta
                beta_val = float(beta) if beta else 1.0
                if beta_val < 0.8:
                    wacc = 0.08
                elif beta_val < 1.2:
                    wacc = 0.09
                elif beta_val < 1.5:
                    wacc = 0.10
                else:
                    wacc = 0.12

                # DCF 5 anni + terminal value (P/E exit 14x per sicurezza)
                projected = use_eps_dcf
                dcf_sum = 0
                for y in range(1, 6):
                    projected *= (1 + conservative_growth)
                    dcf_sum += projected / (1 + wacc) ** y
                terminal = (projected * 12) / (1 + wacc) ** 5
                pillar3_dcf = round(dcf_sum + terminal, 2)
                # Cap: non più di +60% dal prezzo attuale
                pillar3_dcf = min(pillar3_dcf, current_price * 1.60)
                if pillar3_dcf < current_price * 0.4:
                    pillar3_dcf = None
        except Exception:
            pillar3_dcf = None

        # ── Fair Value zona ragionevole (media ponderata dei 3 pilastri) ──
        fv_components = []
        fv_weights = []
        if pillar1_consensus:
            fv_components.append(pillar1_consensus)
            fv_weights.append(0.50)
        if pillar2_multiples:
            fv_components.append(pillar2_multiples)
            fv_weights.append(0.30)
        if pillar3_dcf:
            fv_components.append(pillar3_dcf)
            fv_weights.append(0.20)

        if fv_components:
            total_w = sum(fv_weights)
            fair_value = round(sum(v * w for v, w in zip(fv_components, fv_weights)) / total_w, 2)
        else:
            fair_value = None

        # ── Target price = Fair Value con guardrail realistici ────────────
        try:
            if fair_value:
                target_price = fair_value
                # Guardrail: tra +5% e +40% dal prezzo attuale
                target_price = max(target_price, round(current_price * 1.05, 2))
                target_price = min(target_price, round(current_price * 1.40, 2))
            else:
                # Fallback tecnico: massimo 52 settimane
                high_52w = float(hist.tail(252)["High"].max())
                target_price = round(max(high_52w, current_price * 1.08), 2)
                target_price = min(target_price, round(current_price * 1.40, 2))
        except Exception:
            target_price = round(current_price * 1.10, 2)

        # ── Stop loss dinamico (ATR-based) ────────────────────────────────
        try:
            atr_stop = float((hist["High"] - hist["Low"]).tail(14).mean())
            stop_loss = round(current_price - (atr_stop * 2), 2)
            stop_loss = max(stop_loss, round(current_price * 0.88, 2))
            stop_loss = min(stop_loss, round(current_price * 0.95, 2))
        except Exception:
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

        # ── Entry price (dipende dallo score) ─────────────────────────────
        if score >= 65:  # BUY
            entry_price = round(current_price * 0.98 if rsi_val < 50 else current_price, 2)
        elif score >= 45:  # HOLD — entry solo se già sotto MA50
            if ma50 and current_price < ma50 * 0.97:
                entry_price = round(current_price * 0.97, 2)
            else:
                entry_price = None  # attendere segnale migliore
        else:  # AVOID
            entry_price = None

        # --- RSI label (correct thresholds) ---
        if rsi_val >= 70:
            rsi_label = "Ipercomprato"
        elif rsi_val <= 30:
            rsi_label = "Ipervenduto"
        elif rsi_val >= 55:
            rsi_label = "Forza"
        elif rsi_val <= 45:
            rsi_label = "Debolezza"
        else:
            rsi_label = "Neutro"

        # --- Signal label ---
        if score >= 65:
            signal = "🟢 BUY"
        elif score >= 50:
            signal = "🟡 HOLD"
        else:
            signal = "🔴 SELL / AVOID"

        # ══════════════════════════════════════════════════════════════════
        # MODELLO PREVISIONALE TEMPORALE — 4 METODI PROFESSIONALI
        # ══════════════════════════════════════════════════════════════════

        # Upside SEMPRE da current_price verso target_price — 2 decimali fissi
        upside = round((target_price - current_price) / current_price * 100, 2) if target_price else None
        upside_net = round(upside * 0.74, 2) if upside is not None else None

        atr = None
        estimated_days = None
        estimated_months = None
        time_label = "N/A"
        time_category = "N/A"
        annualized_return = None
        time_method = "N/A"
        time_detail = ""

        try:
            # ── METODO 1: ATR × Regola del 3 ─────────────────────────────
            # Giorni minimi = distanza_target / ATR × fattore_ritracciamento
            # Poi si moltiplica per 3 (regola d'oro)
            high_low = hist["High"] - hist["Low"]
            atr_14 = float(high_low.tail(14).mean())
            atr = round(atr_14, 2)

            distance = target_price - entry_price if target_price and entry_price else 0

            if distance > 0 and atr_14 > 0:
                # Giorni minimi teorici (formula ATR)
                raw_days = distance / atr_14
                # Moltiplicatore ritracciamento: 3x per titoli stabili, 2x per volatili
                beta_val = float(beta) if beta else 1.0
                if beta_val < 0.8:
                    retrace_factor = 4.0   # titoli lenti (utility, telecom): ×4
                elif beta_val < 1.2:
                    retrace_factor = 3.0   # titoli medi: ×3 (regola d'oro)
                elif beta_val < 1.8:
                    retrace_factor = 2.5   # titoli ciclici
                else:
                    retrace_factor = 2.0   # titoli molto volatili

                atr_days = raw_days * retrace_factor
                atr_months = atr_days / 21

                # ── METODO 2: Velocità storica (Beta + tipo titolo) ───────
                # Rendimento annuo atteso per tipologia
                if beta_val < 0.6:
                    annual_expected_pct = 8.0    # utility/telecom: 8-12% annuo
                elif beta_val < 0.9:
                    annual_expected_pct = 12.0
                elif beta_val < 1.3:
                    annual_expected_pct = 18.0   # mercato medio
                elif beta_val < 1.8:
                    annual_expected_pct = 25.0   # ciclici
                else:
                    annual_expected_pct = 35.0   # growth/high beta

                velocity_months = (upside / annual_expected_pct) * 12 if upside else None

                # ── METODO 3: Catalizzatore fondamentale ─────────────────
                # Stima basata su quante trimestrali servono per giustificare il target
                if upside:
                    if upside < 10:
                        catalyst_months = 3     # una trimestrale positiva
                    elif upside < 25:
                        catalyst_months = 6     # due trimestrali positive
                    elif upside < 40:
                        catalyst_months = 12    # anno pieno
                    else:
                        catalyst_months = 18    # ciclo lungo
                else:
                    catalyst_months = 12

                # ── MEDIA PONDERATA DEI 3 METODI ─────────────────────────
                # ATR = 40%, velocità storica = 35%, catalizzatore = 25%
                methods = []
                mw = []
                if atr_months:
                    methods.append(atr_months)
                    mw.append(0.40)
                if velocity_months:
                    methods.append(velocity_months)
                    mw.append(0.35)
                methods.append(float(catalyst_months))
                mw.append(0.25)

                total_mw = sum(mw)
                estimated_months_raw = sum(m * w for m, w in zip(methods, mw)) / total_mw

                # ── METODO 4: Regola del 3 applicata alla categoria ───────
                # Corregge l'ottimismo algoritmico
                if estimated_months_raw <= 1:
                    estimated_months = round(estimated_months_raw * 3, 1)
                    correction_note = "×3 (regola prudenza)"
                elif estimated_months_raw <= 3:
                    estimated_months = round(estimated_months_raw * 2.5, 1)
                    correction_note = "×2.5 (regola prudenza)"
                elif estimated_months_raw <= 12:
                    estimated_months = round(estimated_months_raw * 2.0, 1)
                    correction_note = "×2 (regola prudenza)"
                else:
                    estimated_months = round(estimated_months_raw * 1.5, 1)
                    correction_note = "×1.5 (regola prudenza)"

                # ── FLOOR MINIMO PER SETTORE ──────────────────────────────
                # Ogni settore ha un tempo minimo realistico basato sulla sua natura
                sector_floor = {
                    "Financial Services": 6,      # banche: almeno 2 trimestrali
                    "Utilities": 9,               # utility: crescita lenta
                    "Real Estate": 9,             # REIT: ciclo lungo
                    "Consumer Defensive": 6,      # staples: lenti
                    "Healthcare": 6,              # pharma: dipende da pipeline
                    "Industrials": 6,             # industriali: ciclo medio
                    "Energy": 5,                  # energy: volatile ma può muoversi
                    "Basic Materials": 4,
                    "Communication Services": 5,
                    "Consumer Cyclical": 4,
                    "Technology": 3,              # tech: può muoversi veloce
                }.get(str(sector), 4)

                # Applica il floor: il tempo non può essere inferiore al minimo di settore
                estimated_months = max(estimated_months, float(sector_floor))

                # Cap: max 4 anni
                estimated_months = min(estimated_months, 48.0)
                estimated_days = int(estimated_months * 21)

                # Dettaglio metodologia
                time_detail = (
                    f"ATR({round(atr_months,1)}m) + "
                    f"Velocità({round(velocity_months,1) if velocity_months else '?'}m) + "
                    f"Catalizzatore({catalyst_months}m) → {correction_note} "
                    f"[floor settore: {sector_floor}m]"
                )

                # Label finale
                if estimated_months <= 3:
                    time_label = f"~{round(estimated_months,0):.0f} mesi"
                    time_category = "🟢 Breve (< 3 mesi)"
                elif estimated_months <= 6:
                    time_label = f"~{round(estimated_months,0):.0f} mesi"
                    time_category = "🟡 Medio (3-6 mesi)"
                elif estimated_months <= 12:
                    time_label = f"~{round(estimated_months,0):.0f} mesi"
                    time_category = "🟠 Lungo (6-12 mesi)"
                elif estimated_months <= 24:
                    time_label = f"~{round(estimated_months/12,1):.1f} anni"
                    time_category = "🔴 Lungo (1-2 anni)"
                else:
                    time_label = f"~{round(estimated_months/12,1):.1f} anni"
                    time_category = "⛔ Molto lungo (> 2 anni)"

                # Rendimento annualizzato calcolato dopo (vedi sezione CAGR)
                pass  # placeholder

        except Exception:
            time_label = "N/A"
            time_category = "N/A"
            time_detail = ""

        # ══════════════════════════════════════════════════════════════════
        # REGOLE DI COERENZA FINALE
        # ══════════════════════════════════════════════════════════════════

        # REGOLA 1: Se AVOID/SELL → niente target rialzista, mostra downside
        is_avoid = score < 50
        is_hold = 50 <= score < 65

        if is_avoid:
            entry_price = None
            # FIX 9: Fair value nascosto per AVOID con fondamentali pessimi
            if pe and pe > 100:
                fair_value = None  # P/E eccessivo → FV non affidabile
            # Downside target: 52-week low o -15%
            try:
                low_52w = float(hist.tail(252)["Low"].min())
                target_price = round(max(low_52w, current_price * 0.85), 2)
            except Exception:
                target_price = round(current_price * 0.88, 2)
            upside = round((target_price - current_price) / current_price * 100, 2)  # negativo
            upside_net = round(upside * 0.74, 2)
            stop_loss = round(current_price * 1.05, 2)  # stop su rimbalzo

        # FIX 5: HOLD → congela tutti i campi operativi
        elif is_hold:
            entry_price = None
            # Mantieni target e FV per riferimento ma senza entry

        # REGOLA 2: BUY con prezzo > fair value → declassa
        elif fair_value and current_price > fair_value * 1.05 and score < 80:
            if signal == "🟢 BUY":
                signal = "🟡 HOLD"
                score = min(score, 64)
                is_hold = True
                entry_price = None

        # Rendimento annualizzato — deterministico, NON generato dall'AI
        # IMPORTANTE: sincronizza estimated_months con il valore visualizzato nel time_label
        # così CAGR e label mostrano lo stesso orizzonte temporale
        try:
            annualized_return = None
            if not is_avoid and not is_hold and estimated_months and estimated_months > 0 and upside is not None and target_price and current_price:
                # Arrotonda mesi al valore visualizzato nel label (evita drift)
                if estimated_months < 12.0:
                    # Label mostra mesi interi → arrotonda a intero
                    months_sync = round(estimated_months)
                else:
                    # Label mostra X.X anni → arrotonda a 1 decimale di anni poi riconverti
                    years_display = round(estimated_months / 12.0, 1)
                    months_sync = years_display * 12.0

                if months_sync < 12.0:
                    # Tasso lineare: (upside / mesi) * 12
                    annualized_return = round((upside / months_sync) * 12.0, 2)
                else:
                    # CAGR: usa anni sincronizzati col label
                    years_sync = months_sync / 12.0
                    annualized_return = round((pow(target_price / current_price, 1.0 / years_sync) - 1) * 100, 2)
                annualized_return = min(annualized_return, 200.0)
        except Exception:
            annualized_return = None

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
            "upside_pct": round(upside, 2) if upside is not None else None,
            "upside_net_pct": round(upside * 0.74, 2) if upside is not None else None,
            "time_label": time_label,
            "time_category": time_category,
            "estimated_months": estimated_months,
            "annualized_return": annualized_return,
            "atr": atr,
            "time_detail": time_detail if 'time_detail' in dir() else "",
            "fair_value": round(fair_value, 2) if fair_value else None,
            "fv_consensus": round(pillar1_consensus, 2) if pillar1_consensus else None,
            "fv_multiples": round(pillar2_multiples, 2) if pillar2_multiples else None,
            "fv_dcf": round(pillar3_dcf, 2) if pillar3_dcf else None,
            "n_analysts": int(n_analysts) if n_analysts else 0,
            "analyst_target": analyst_target,
            "signal": signal,
            "score": round(score),
            "is_avoid": is_avoid,
            "is_hold": is_hold,
            "rsi": round(rsi_val, 1),
            "rsi_label": rsi_label,
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
