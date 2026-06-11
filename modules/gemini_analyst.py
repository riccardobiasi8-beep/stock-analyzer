import requests
import json
import html

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

GEMINI_ENDPOINTS = [
    ("gemini-2.0-flash-lite", "v1beta"),
    ("gemini-2.0-flash-lite-001", "v1beta"),
    ("gemini-2.0-flash", "v1beta"),
    ("gemini-2.5-flash-lite", "v1beta"),
    ("gemini-2.5-flash", "v1beta"),
]
GEMINI_BASE = "https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent"


def _call_gemini(prompt: str, api_key: str, max_tokens: int = 1000, use_search: bool = False) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_tokens}
    }
    if use_search:
        payload["tools"] = [{"google_search_retrieval": {}}]

    last_error = None
    for model, version in GEMINI_ENDPOINTS:
        try:
            resp = requests.post(
                f"{GEMINI_BASE.format(version=version, model=model)}?key={api_key}",
                headers={"Content-Type": "application/json"},
                json=payload, timeout=30
            )
            result = resp.json()
            if "error" in result:
                last_error = result["error"].get("message", "error")
                print(f"[Gemini] {model} failed: {last_error[:80]}")
                continue
            candidates = result.get("candidates", [])
            if not candidates:
                last_error = "no candidates"
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                last_error = "empty parts"
                continue
            print(f"[Gemini] OK: {model}/{version}")
            return parts[0].get("text", "").strip()
        except Exception as e:
            last_error = str(e)
            print(f"[Gemini] {model} exception: {str(e)[:60]}")
            continue
    raise Exception(f"Tutti i modelli falliti: {last_error}")


def _call_groq(prompt: str, api_key: str, max_tokens: int = 800) -> str:
    resp = requests.post(
        GROQ_URL,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        json={"model": GROQ_MODEL, "max_tokens": max_tokens, "temperature": 0.2,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=20
    )
    result = resp.json()
    if "error" in result:
        raise Exception(result["error"].get("message", "Groq error"))
    return result["choices"][0]["message"]["content"].strip()


def _call_ai(prompt: str, gemini_key: str, groq_key: str, max_tokens: int = 800) -> str:
    """Try Gemini first, fallback to Groq if quota exceeded."""
    try:
        return _call_gemini(prompt, gemini_key, max_tokens)
    except Exception as e:
        if groq_key and any(k in str(e).lower() for k in ["quota", "rate", "falliti", "429"]):
            print(f"[Gemini→Groq] Switching to Groq: {str(e)[:60]}")
            return _call_groq(prompt, groq_key, max_tokens)
        raise


def analyze_stock(data: dict, api_key: str, groq_key: str = "") -> str:
    """Summary sopra il grafico — usa dati ESATTI dalla scheda."""
    signal = data.get("signal", "HOLD")
    score = data.get("score", 50)
    verdict = "BUY" if "BUY" in signal else ("AVOID" if "AVOID" in signal or "SELL" in signal else "HOLD")
    rsi = data.get("rsi", 50) or 50
    price = data.get("current_price", 0) or 0
    fair_value = data.get("fair_value")
    entry = data.get("entry_price")
    target = data.get("target_price")
    stop = data.get("stop_loss")
    upside = data.get("upside_pct")
    cur = data.get("currency", "USD")
    # RSI interpretation
    if rsi >= 70: rsi_desc = f"ipercomprato ({rsi}, >70)"
    elif rsi <= 30: rsi_desc = f"ipervenduto ({rsi}, <30)"
    else: rsi_desc = f"neutro ({rsi}, range normale 30-70)"
    # Build entry string
    is_avoid = "AVOID" in signal or "SELL" in signal or score < 45
    if is_avoid:
        entry_str = "Entry: nessun ingresso (AVOID)"
        target_str = f"Downside target:{target} {cur}" if target else "Downside target: ribassista"
        stop_str = f"Stop rimbalzo:{stop} {cur}" if stop else ""
    else:
        entry_str = f"Entry:{entry} {cur}" if entry else "Entry: attendi segnale"
        target_str = f"Target:{target} {cur}" if target else "Target: da definire"
        stop_str = f"Stop Loss:{stop} {cur}" if stop else ""
    fv_note = ""
    if fair_value and price and upside:
        if verdict == "HOLD" and upside > 15:
            fv_note = (f"IMPORTANTE: nonostante un upside teorico del +{upside}% verso il Fair Value {fair_value} {cur}, "
                       f"il basso score ({score}/100) impone HOLD. Spiega nel testo PERCHE lo score e basso "
                       f"(es. RSI, fondamentali deboli, trend negativo) e giustifica la prudenza.")
        elif price > (fair_value or 0) * 1.05:
            fv_note = f"Prezzo sopra Fair Value {fair_value} {cur} = sopravvalutato."
    prompt = (
        f"Analista finanziario. Analizza {data['name']} ({data['ticker']}) in italiano, 3 frasi.\n"
        f"Fondamentali: P/E {data.get('pe','N/A')}, ROE {data.get('roe','N/A')}%, margine {data.get('profit_margin','N/A')}%\n"
        f"Tecnica: RSI={rsi_desc}. Prezzo {'sopra' if data.get('ma50') and price>(data.get('ma50') or 0) else 'sotto'} MA50. Score {score}/100.\n"
        f"{fv_note}\n"
        f"Dati ESATTI da usare nel testo: {entry_str}. {target_str}. {stop_str}.\n"
        f"Verdetto sistema: {verdict}. USA QUESTI NUMERI ESATTI, non arrotondarli diversamente.\n"
        f"REGOLE OBBLIGATORIE:\n"
        f"- Verdetto finale DEVE essere {verdict}\n"
        f"- RSI tra 30-70 e neutro, non scrivere ipervenduto/ipercomprato\n"
        f"- Se HOLD: NON dire di comprare subito. Dire di ATTENDERE{' un ingresso a '+str(entry)+' '+cur if entry else 'segnali migliori'}.\n"
        f"- Se AVOID: usa SOLO i termini 'downside target' e 'stop rimbalzo' (non Target/Stop Loss). Non citare Entry. Non suggerire acquisto.\n"
        f"- Usa i numeri esatti forniti sopra, non inventarne altri"
    )
    try:
        return _call_ai(prompt, api_key, groq_key, 350)
    except Exception as e:
        print(f"Gemini analyze_stock error: {e}")
        return None

def reason_time_to_target(data: dict, api_key: str, groq_key: str = "") -> str:
    """Stima temporale ragionata."""
    upside = data.get('upside_pct', 0) or 0
    upside_str = f"{upside:.1f}"
    prompt = f"""Analista quantitativo. Stima tempo realistico per {data['name']} ({data['ticker']}) a raggiungere target.
Prezzo:{data.get('current_price')} | Target:{data.get('target_price')} | Upside:{upside_str}%
Settore:{data.get('sector','N/A')} | Beta:{data.get('beta','N/A')} | ATR:{data.get('atr','N/A')}
Earnings:{data.get('next_earnings_date','N/A')}
Rispondi in italiano: stima (es "6-9 mesi"), motivazione 2 frasi, 1 catalizzatore. Max 80 parole."""
    try:
        return _call_ai(prompt, api_key, groq_key, 300)
    except Exception as e:
        print(f"Gemini reason_time error: {e}")
        return None


def analyze_sentiment_narrative(data: dict, sent: dict, api_key: str, groq_key: str = "") -> str:
    """Analisi narrativa sentiment."""
    an = sent.get("analyst", {})
    sh = sent.get("short", {})
    ea = sent.get("earnings", {})
    op = sent.get("options", {})
    prompt = (
        f"Analista senior Wall Street. Briefing su {data['name']} ({data['ticker']}) in italiano max 200 parole.\n"
        f"Consensus:{an.get('consensus_label','N/A')} {an.get('n_analysts',0)} analisti target:{an.get('target_mean','N/A')} upside:{an.get('upside','N/A')}%\n"
        f"Short:{sh.get('short_pct','N/A')}% Put/Call:{op.get('put_call_ratio','N/A')} Earnings media:{ea.get('avg_surprise','N/A')}% prossimi:{ea.get('next_earnings','N/A')}\n"
        "4 punti: consensus/paradosso, opzioni/short, earnings/catalyst, verdetto."
    )
    try:
        return _call_ai(prompt, api_key, groq_key, 500)
    except Exception as e:
        print(f"Gemini sentiment error: {e}")
        return None


def validate_and_flag(data: dict, api_key: str) -> dict:
    return {"flags": [], "reliability_score": 100, "note": ""}
