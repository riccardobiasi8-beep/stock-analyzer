import requests
import json

GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest",
    "gemini-pro",
]
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _call_gemini(prompt: str, api_key: str, max_tokens: int = 800, use_search: bool = False) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_tokens}
    }
    if use_search:
        payload["tools"] = [{"google_search_retrieval": {}}]

    last_error = None
    for model in GEMINI_MODELS:
        try:
            response = requests.post(
                f"{GEMINI_BASE.format(model=model)}?key={api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=25
            )
            result = response.json()
            if "error" in result:
                last_error = result["error"].get("message", "error")
                print(f"[Gemini] Model {model} failed: {last_error[:80]}")
                continue
            candidates = result.get("candidates", [])
            if not candidates:
                last_error = "no candidates"
                continue
            if candidates[0].get("finishReason") == "SAFETY":
                raise Exception("Bloccato da filtri sicurezza")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                last_error = "empty parts"
                continue
            print(f"[Gemini] OK with model: {model}")
            return parts[0].get("text", "").strip()
        except Exception as e:
            if "SAFETY" in str(e):
                raise
            last_error = str(e)
            print(f"[Gemini] Model {model} exception: {last_error[:80]}")
            continue
    raise Exception(f"Tutti i modelli falliti. Ultimo: {last_error}")


def analyze_stock(data: dict, api_key: str) -> str:
    prompt = f"""Sei un analista finanziario senior. Analizza {data['name']} ({data['ticker']}) in italiano.
Scrivi massimo 3 frasi concise:
1. Fondamentali: P/E {data.get('pe','N/A')}, P/B {data.get('pb','N/A')}, ROE {data.get('roe','N/A')}%, margine {data.get('profit_margin','N/A')}%, crescita ricavi {data.get('revenue_growth','N/A')}%
2. Tecnica: RSI {data.get('rsi','N/A')}, MACD {'bullish' if data.get('macd',0) and data.get('macd_signal',0) and data.get('macd',0) > data.get('macd_signal',0) else 'bearish'}, prezzo {'sopra' if data.get('ma50') and data.get('current_price',0) > data.get('ma50',0) else 'sotto'} MA50
3. Verdetto secco: BUY/HOLD/AVOID. Entry: {data.get('entry_price')}. Target: {data.get('target_price')}. Stop: {data.get('stop_loss')}.
Sii diretto, usa i numeri, niente giri di parole."""
    try:
        return _call_gemini(prompt, api_key, 300)
    except Exception as e:
        import traceback; print(f"Gemini analyze_stock error: {e}\n{traceback.format_exc()}")
        return None


def reason_time_to_target(data: dict, api_key: str) -> str:
    upside = data.get('upside_pct', 0) or 0
    beta = data.get('beta', 1.0) or 1.0
    sector = data.get('sector', 'N/A')
    next_earnings = data.get('next_earnings_date')

    prompt = f"""Sei un analista quantitativo esperto. Stima il tempo realistico affinché {data['name']} ({data['ticker']}) raggiunga il target.

DATI:
- Prezzo: {data.get('current_price')} {data.get('currency','USD')} | Target: {data.get('target_price')} | Upside: {upside:.1f}%
- Settore: {sector} | Beta: {beta} | RSI: {data.get('rsi','N/A')}
- ATR: {data.get('atr','N/A')} | Analisti: {data.get('n_analysts',0)} | Prossimi earnings: {next_earnings or 'N/A'}
- MA50: {'sopra' if data.get('ma50') and data.get('current_price',0) > data.get('ma50',0) else 'sotto'} | MA200: {'sopra' if data.get('ma200') and data.get('current_price',0) > data.get('ma200',0) else 'sotto'}

Rispondi in italiano con:
- Stima tempo (es. "6-9 mesi")
- 2-3 frasi motivazione specifica
- 1 catalizzatore chiave

Max 100 parole."""
    try:
        return _call_gemini(prompt, api_key, 400)
    except Exception as e:
        import traceback; print(f"Gemini reason_time error: {e}\n{traceback.format_exc()}")
        return None


def analyze_sentiment_narrative(data: dict, sent: dict, api_key: str) -> str:
    an = sent.get("analyst", {})
    sh = sent.get("short", {})
    ea = sent.get("earnings", {})
    op = sent.get("options", {})
    ins = sent.get("insider", {})
    nw = sent.get("news", {})

    prompt = f"""Analista finanziario senior Wall Street. Briefing professionale in italiano su {data['name']} ({data['ticker']}).

DATI SENTIMENT:
- Prezzo: {data.get('current_price')} {data.get('currency','USD')}
- Consensus: {an.get('consensus_label','N/A')} | {an.get('n_analysts',0)} analisti | Target: {an.get('target_mean','N/A')} | Upside: {an.get('upside','N/A')}%
- Short: {sh.get('short_pct','N/A')}% | Days to cover: {sh.get('short_ratio','N/A')}
- Earnings media sorpresa: {ea.get('avg_surprise','N/A')}% | Prossimi: {ea.get('next_earnings','N/A')}
- Put/Call: {op.get('put_call_ratio','N/A')} | Insider: {ins.get('label','N/A')}
- News: {nw.get('label','N/A')}

4 paragrafi brevi (max 250 parole):
1. **Consensus e paradosso**
2. **Opzioni e short interest**
3. **Earnings e catalyst**
4. **Verdetto sentiment**"""
    try:
        return _call_gemini(prompt, api_key, 600)
    except Exception as e:
        import traceback; print(f"Gemini sentiment error: {e}\n{traceback.format_exc()}")
        return None


def validate_and_flag(data: dict, api_key: str) -> dict:
    prompt = f"""Verifica coerenza dati per {data.get('name','?')} ({data.get('ticker','?')}, settore: {data.get('sector','N/A')}).
P/E:{data.get('pe')} P/B:{data.get('pb')} ROE:{data.get('roe')}% Margine:{data.get('profit_margin')}%
Debt/Equity:{data.get('debt_equity')} Beta:{data.get('beta')} Dividend:{data.get('dividend_yield')}%

Rispondi SOLO con JSON: {{"flags":[],"reliability_score":100,"note":""}}"""
    try:
        raw = _call_gemini(prompt, api_key, 300)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        result = json.loads(raw)
        return {"flags": result.get("flags", []), "reliability_score": result.get("reliability_score", 100), "note": result.get("note", "")}
    except Exception:
        return {"flags": [], "reliability_score": 100, "note": ""}
