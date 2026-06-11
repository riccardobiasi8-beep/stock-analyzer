import json
import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def _call_gemini(prompt: str, api_key: str, max_tokens: int = 1200, use_search: bool = False) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens}
    }
    if use_search:
        payload["tools"] = [{"google_search_retrieval": {}}]
    
    response = requests.post(
        f"{GEMINI_URL}?key={api_key}",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=30
    )
    result = response.json()
    if "error" in result:
        raise Exception(result["error"].get("message", "Gemini error"))
    candidates = result.get("candidates", [])
    if not candidates:
        raise Exception("Nessuna risposta da Gemini")
    if candidates[0].get("finishReason") == "SAFETY":
        raise Exception("Bloccato da filtri sicurezza")
    return candidates[0]["content"]["parts"][0]["text"].strip()


def validate_stock_data(data: dict, gemini_key: str) -> dict:
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

    try:
        # ── STEP 1: Search for real data ────────────────────────────────
        if missing:
            search_prompt = f"""Search Google for current financial data for {name} ({ticker}).
I need these specific metrics: {', '.join(missing)}
Also find: sector, P/E ratio, ROE, profit margin, debt/equity, beta, dividend yield.
Return a summary of the real data you find. Be specific with numbers."""

            try:
                search_result = _call_gemini(search_prompt, gemini_key, 600, use_search=True)
            except Exception:
                search_result = f"Ticker {ticker}, nome {name}, prezzo {price} {currency}, settore {sector}"
        else:
            search_result = f"Dati già disponibili da Yahoo Finance per {ticker}"

        # ── STEP 2: Validate and format as JSON ─────────────────────────
        json_prompt = f"""Sei un analista finanziario. Hai cercato dati per {name} ({ticker}).

RISULTATI RICERCA:
{search_result}

DATI YAHOO FINANCE (potrebbero essere incompleti/errati):
- Prezzo: {price} {currency} | Settore: {sector}
- P/E: {data.get('pe')} | P/B: {data.get('pb')} | EV/EBITDA: {data.get('ev_ebitda')}
- ROE: {data.get('roe')}% | Margine netto: {data.get('profit_margin')}% | Crescita ricavi: {data.get('revenue_growth')}%
- Debt/Equity: {data.get('debt_equity')} | Beta: {data.get('beta')} | Dividend yield: {data.get('dividend_yield')}%
- Target: {data.get('target_price')} | Stop: {data.get('stop_loss')} | Fair Value: {data.get('fair_value')}

REGOLE CORREZIONE:
- ROE da Yahoo è in decimali (0.142 = 14.2%) — se già convertito in % non dividere
- Dividend yield da Yahoo è in decimali (0.005 = 0.5%) — controlla scala
- P/E anomalo (>500 o negativo): correggi
- Se un campo era None/mancante: fornisci il valore trovato in ricerca o stima dal settore

Rispondi SOLO con questo JSON (nessun testo fuori):
{{
  "validation_score": <0-100>,
  "corrections": {{
    "pe": <numero o null se già corretto>,
    "pb": <numero o null>,
    "ev_ebitda": <numero o null>,
    "roe": <numero percentuale es. 14.2, null se ok>,
    "profit_margin": <numero percentuale, null se ok>,
    "revenue_growth": <numero percentuale, null se ok>,
    "debt_equity": <numero o null>,
    "beta": <numero o null>,
    "dividend_yield": <numero percentuale, null se ok>,
    "rsi": null,
    "fair_value": <numero o null>,
    "target_price": <numero o null>,
    "stop_loss": <numero o null>,
    "upside_pct": <numero o null>
  }},
  "field_reasoning": {{
    "pe": "<spiegazione o null>",
    "pb": null,
    "ev_ebitda": null,
    "roe": "<spiegazione o null>",
    "profit_margin": null,
    "revenue_growth": null,
    "debt_equity": "<spiegazione o null>",
    "beta": "<spiegazione o null>",
    "dividend_yield": "<spiegazione o null>",
    "fair_value": null,
    "target_price": null,
    "stop_loss": null,
    "upside_pct": null
  }},
  "data_reliability": "<Alta|Media|Bassa>",
  "summary": "<frase italiana con i dati trovati e corretti>"
}}"""

        raw = _call_gemini(json_prompt, gemini_key, 1000, use_search=False)

        print(f"[Validator RAW] {ticker}: {repr(raw[:500])}")

        # Clean JSON
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        # Fix common JSON issues
        raw = raw.strip()
        print(f"[Validator CLEAN] {ticker}: {repr(raw[:300])}")

        validation = json.loads(raw)
        print(f"[Validator PARSED] corrections: {validation.get('corrections', {})}")

        # ── Apply corrections ────────────────────────────────────────────
        corrected_data = dict(data)
        corrections = validation.get("corrections", {})
        field_reasoning = validation.get("field_reasoning", {})

        field_map = {
            "pe": "pe", "pb": "pb", "ev_ebitda": "ev_ebitda",
            "roe": "roe", "profit_margin": "profit_margin",
            "revenue_growth": "revenue_growth", "debt_equity": "debt_equity",
            "beta": "beta", "dividend_yield": "dividend_yield",
            "rsi": "rsi", "fair_value": "fair_value",
            "target_price": "target_price", "stop_loss": "stop_loss",
            "upside_pct": "upside_pct"
        }

        corrected_fields = []
        for key, data_key in field_map.items():
            corrected_val = corrections.get(key)
            if corrected_val is None:
                continue
            original = corrected_data.get(data_key)
            try:
                num_val = round(float(corrected_val), 2)
                if original is None or abs(num_val - float(original)) > 0.001:
                    corrected_data[data_key] = num_val
                    corrected_fields.append(f"{data_key}: {original} → {num_val}")
            except (TypeError, ValueError):
                pass

        # Recalculate upside if target changed
        if any("target_price" in c for c in corrected_fields):
            tp = corrected_data.get("target_price")
            cp = corrected_data.get("current_price")
            if tp and cp and cp > 0:
                new_upside = round((tp - cp) / cp * 100, 1)
                corrected_data["upside_pct"] = new_upside
                corrected_data["upside_net_pct"] = round(new_upside * 0.74, 1)

        corrected_data["validation"] = {
            "status": "completed",
            "score": validation.get("validation_score", 100),
            "reliability": validation.get("data_reliability", "Media"),
            "issues": [v for v in field_reasoning.values() if v],
            "corrected_fields": corrected_fields,
            "field_reasoning": {k: v for k, v in field_reasoning.items() if v},
            "summary": validation.get("summary", ""),
        }

        print(f"[Validator] {ticker}: {len(corrected_fields)} corrections: {corrected_fields}")
        return corrected_data

    except Exception as e:
        import traceback
        print(f"[Validator error] {ticker}: {e}\n{traceback.format_exc()}")
        return {
            **data,
            "validation": {
                "status": "error",
                "score": None,
                "reliability": "N/A",
                "issues": [str(e)],
                "corrected_fields": [],
                "field_reasoning": {},
                "summary": f"Errore validazione: {str(e)[:100]}",
            }
        }
