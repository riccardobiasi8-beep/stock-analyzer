import json
import requests
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


def _call(prompt: str, api_key: str, max_tokens: int = 1000, search: bool = False) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens}
    }
    if search:
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
                print(f"[Validator] {model} failed: {last_error[:80]}")
                # If rate limit, stop trying
                if "quota" in last_error.lower() or "429" in last_error:
                    raise Exception(f"Rate limit: {last_error[:100]}")
                continue
            candidates = result.get("candidates", [])
            if not candidates:
                last_error = "no candidates"
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                last_error = "empty parts"
                continue
            print(f"[Validator] OK: {model}/{version}")
            return parts[0].get("text", "").strip()
        except Exception as e:
            if "Rate limit" in str(e) or "quota" in str(e).lower():
                raise
            last_error = str(e)
            continue
    raise Exception(f"Tutti i modelli falliti: {last_error}")


def _call_groq(prompt: str, api_key: str, max_tokens: int = 1000) -> str:
    """Groq fallback when Gemini quota is exhausted."""
    resp = requests.post(
        GROQ_URL,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        json={"model": GROQ_MODEL, "max_tokens": max_tokens, "temperature": 0.1,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=20
    )
    result = resp.json()
    if "error" in result:
        raise Exception(result["error"].get("message", "Groq error"))
    return result["choices"][0]["message"]["content"].strip()


def validate_stock_data(data: dict, gemini_key: str, groq_key: str = "") -> dict:
    if not gemini_key:
        return {**data, "validation": {
            "status": "skipped", "score": None, "issues": [],
            "corrected_fields": [], "field_reasoning": {},
            "reliability": "N/A", "summary": ""
        }}

    missing = [k for k in ["pe","pb","ev_ebitda","roe","profit_margin",
               "revenue_growth","debt_equity","beta","dividend_yield"]
               if data.get(k) is None]

    ticker = data.get('ticker', '')
    name = data.get('name', ticker)
    sector = data.get('sector') or 'N/A'
    price = data.get('current_price')
    currency = data.get('currency', 'USD')

    prompt = f"""Sei un analista Goldman Sachs. Analizza {name} ({ticker}).
Cerca su Google i dati fondamentali aggiornati se mancano.

DATI YAHOO FINANCE (None = mancante):
Settore:{sector} | Prezzo:{price} {currency} | MarketCap:{data.get('market_cap')}
P/E:{data.get('pe')} | P/B:{data.get('pb')} | EV/EBITDA:{data.get('ev_ebitda')}
ROE:{data.get('roe')}% | Margine:{data.get('profit_margin')}% | Crescita:{data.get('revenue_growth')}%
D/E:{data.get('debt_equity')} | Beta:{data.get('beta')} | Dividend:{data.get('dividend_yield')}%
Target:{data.get('target_price')} | Stop:{data.get('stop_loss')} | FV:{data.get('fair_value')}

CAMPI MANCANTI: {missing if missing else 'nessuno'}

Per i campi mancanti: stima valori reali cercando su Google o usando la tua conoscenza del settore.
Correggi anomalie: ROE>150% dividi per 100, dividend>20% dividi per 10.

Rispondi SOLO con JSON valido (nessun testo fuori):
{{
  "validation_score": <0-100>,
  "corrections": {{
    "pe": <numero o null se ok>,
    "pb": <numero o null>,
    "ev_ebitda": <numero o null>,
    "roe": <numero% o null>,
    "profit_margin": <numero% o null>,
    "revenue_growth": <numero% o null>,
    "debt_equity": <numero o null>,
    "beta": <numero o null>,
    "dividend_yield": <numero% o null>,
    "fair_value": <numero o null>,
    "target_price": <numero o null>,
    "stop_loss": <numero o null>,
    "upside_pct": <numero o null>
  }},
  "field_reasoning": {{
    "pe": "<spiegazione breve o null>",
    "pb": null, "ev_ebitda": null,
    "roe": "<spiegazione o null>",
    "profit_margin": null, "revenue_growth": null,
    "debt_equity": "<spiegazione o null>",
    "beta": "<spiegazione o null>",
    "dividend_yield": "<spiegazione o null>",
    "fair_value": null, "target_price": null,
    "stop_loss": null, "upside_pct": null
  }},
  "data_reliability": "<Alta|Media|Bassa>",
  "summary": "<frase italiana con correzioni applicate>"
}}"""

    try:
        # Try Gemini first, then Groq as fallback
        raw = None
        try:
            try:
                raw = _call(prompt, gemini_key, 900, search=True)
            except Exception as e:
                if "quota" in str(e).lower() or "rate" in str(e).lower():
                    raise  # Let Groq handle it
                raw = _call(prompt, gemini_key, 900, search=False)
        except Exception as gemini_err:
            if groq_key and ("quota" in str(gemini_err).lower() or "rate" in str(gemini_err).lower() or "falliti" in str(gemini_err).lower()):
                print(f"[Validator] Gemini quota/failed, switching to Groq...")
                raw = _call_groq(prompt, groq_key, 900)
            else:
                raise
        if not raw:
            raise Exception("Nessuna risposta da AI")

        print(f"[Validator RAW] {ticker}: {repr(raw[:150])}")

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        validation = json.loads(raw)
        corrections = validation.get("corrections", {})
        field_reasoning = validation.get("field_reasoning", {})

        corrected_data = dict(data)
        corrected_fields = []

        field_map = {
            # Fundamentals — AI can correct these
            "pe":"pe","pb":"pb","ev_ebitda":"ev_ebitda","roe":"roe",
            "profit_margin":"profit_margin","revenue_growth":"revenue_growth",
            "debt_equity":"debt_equity","beta":"beta","dividend_yield":"dividend_yield",
            # Price targets — AI can correct these
            "fair_value":"fair_value","target_price":"target_price",
            "stop_loss":"stop_loss",
            # upside_pct and upside_net_pct are NEVER touched by AI
            # They are always recalculated from target_price/current_price
        }

        for key, data_key in field_map.items():
            val = corrections.get(key)
            if val is None:
                continue
            original = corrected_data.get(data_key)
            try:
                num_val = round(float(val), 2)
                if original is None or abs(num_val - float(original)) > 0.001:
                    corrected_data[data_key] = num_val
                    corrected_fields.append(f"{data_key}: {original} → {num_val}")
            except (TypeError, ValueError):
                pass

        # ALWAYS recalculate upside from target_price/current_price
        # This is the ONLY correct source — AI never sets upside directly
        tp = corrected_data.get("target_price")
        cp = corrected_data.get("current_price")
        if tp and cp and cp > 0:
            new_upside = round((tp - cp) / cp * 100, 2)
            corrected_data["upside_pct"] = new_upside
            corrected_data["upside_net_pct"] = round(new_upside * 0.74, 2)

        print(f"[Validator] {ticker}: {len(corrected_fields)} corrections: {corrected_fields}")

        corrected_data["validation"] = {
            "status": "completed",
            "score": validation.get("validation_score", 100),
            "reliability": validation.get("data_reliability", "Media"),
            "issues": [v for v in field_reasoning.values() if v],
            "corrected_fields": corrected_fields,
            "field_reasoning": {k: v for k, v in field_reasoning.items() if v},
            "summary": validation.get("summary", ""),
        }
        return corrected_data

    except Exception as e:
        import traceback
        print(f"[Validator error] {ticker}: {e}\n{traceback.format_exc()}")
        return {
            **data,
            "validation": {
                "status": "error", "score": None, "reliability": "N/A",
                "issues": [str(e)], "corrected_fields": [],
                "field_reasoning": {}, "summary": f"Errore: {str(e)[:100]}",
            }
        }
