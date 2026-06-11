import requests
import json
import html

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


def analyze_stock(data: dict, api_key: str) -> str:
    """Summary sopra il grafico."""
    prompt = f"""Analista finanziario senior. Analizza {data['name']} ({data['ticker']}) in italiano in 3 frasi max:
1. Fondamentali: P/E {data.get('pe','N/A')}, ROE {data.get('roe','N/A')}%, margine {data.get('profit_margin','N/A')}%
2. Tecnica: RSI {data.get('rsi','N/A')}, prezzo {'sopra' if data.get('ma50') and data.get('current_price',0) > data.get('ma50',0) else 'sotto'} MA50
3. Verdetto: BUY/HOLD/AVOID. Entry:{data.get('entry_price')}. Target:{data.get('target_price')}. Stop:{data.get('stop_loss')}."""
    try:
        return _call_gemini(prompt, api_key, 250)
    except Exception as e:
        print(f"Gemini analyze_stock error: {e}")
        return None


def reason_time_to_target(data: dict, api_key: str) -> str:
    """Stima temporale ragionata."""
    upside = data.get('upside_pct', 0) or 0
    prompt = f"""Analista quantitativo. Stima tempo realistico per {data['name']} ({data['ticker']}) a raggiungere target.
Prezzo:{data.get('current_price')} | Target:{data.get('target_price')} | Upside:{upside:.1f}%
Settore:{data.get('sector','N/A')} | Beta:{data.get('beta','N/A')} | ATR:{data.get('atr','N/A')}
Earnings:{data.get('next_earnings_date','N/A')}
Rispondi in italiano: stima (es "6-9 mesi"), motivazione 2 frasi, 1 catalizzatore. Max 80 parole."""
    try:
        return _call_gemini(prompt, api_key, 300)
    except Exception as e:
        print(f"Gemini reason_time error: {e}")
        return None


def analyze_sentiment_narrative(data: dict, sent: dict, api_key: str) -> str:
    """Analisi narrativa sentiment."""
    an = sent.get("analyst", {})
    sh = sent.get("short", {})
    ea = sent.get("earnings", {})
    op = sent.get("options", {})
    prompt = f"""Analista senior Wall Street. Briefing su {data['name']} ({data['ticker']}) in italiano max 200 parole.
Consensus:{an.get('consensus_label','N/A')} {an.get('n_analysts',0)} analisti target:{an.get('target_mean','N/A')} upside:{an.get('upside','N/A')}%
Short:{sh.get('short_pct','N/A')}% Put/Call:{op.get('put_call_ratio','N/A')} Earnings media:{ea.get('avg_surprise','N/A')}% prossimi:{ea.get('next_earnings','N/A')}
4 punti: consensus/paradosso, opzioni/short, earnings/catalyst, verdetto."""
    try:
        return _call_gemini(prompt, api_key, 500)
    except Exception as e:
        print(f"Gemini sentiment error: {e}")
        return None


def validate_and_flag(data: dict, api_key: str) -> dict:
    return {"flags": [], "reliability_score": 100, "note": ""}
