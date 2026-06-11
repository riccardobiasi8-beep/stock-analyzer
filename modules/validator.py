import json
import requests

# (model, api_version) pairs to try in order
GEMINI_ENDPOINTS = [
    ("gemini-2.0-flash-lite", "v1beta"),
    ("gemini-2.0-flash-lite-001", "v1beta"),
    ("gemini-2.5-flash-lite", "v1beta"),
    ("gemini-2.0-flash", "v1beta"),
    ("gemini-2.5-flash", "v1beta"),
]
GEMINI_BASE = "https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent"


def _call_gemini_validator(prompt: str, api_key: str, max_tokens: int = 1200) -> str:
    last_error = None
    for model, version in GEMINI_ENDPOINTS:
        try:
            response = requests.post(
                f"{GEMINI_BASE.format(version=version, model=model)}?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens}
                },
                timeout=30
            )
            result = response.json()
            if "error" in result:
                last_error = result["error"].get("message", "error")
                print(f"[Validator] {model}/{version} failed: {str(last_error)[:60]}")
                continue
            candidates = result.get("candidates", [])
            if not candidates:
                last_error = "no candidates"
                continue
            if candidates[0].get("finishReason") == "SAFETY":
                raise Exception("SAFETY block")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                continue
            print(f"[Validator] OK: {model}/{version}")
            return parts[0].get("text", "").strip()
        except Exception as e:
            if "SAFETY" in str(e):
                raise
            last_error = str(e)
            continue
    raise Exception(f"Tutti i modelli falliti: {last_error}")


def _call_gemini_search(prompt: str, api_key: str, max_tokens: int = 600) -> str:
    """Search-enabled call — only with models that support it."""
    search_models = ["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest"]
    last_error = None
    for model in search_models:
        try:
            response = requests.post(
                f"{GEMINI_BASE.format(model=model)}?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens},
                    "tools": [{"google_search_retrieval": {}}]
                },
                timeout=30
            )
            result = response.json()
            if "error" in result:
                last_error = result["error"].get("message", "error")
                continue
            candidates = result.get("candidates", [])
            if not candidates:
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                print(f"[Validator Search] OK with model: {model}")
                return parts[0].get("text", "").strip()
        except Exception as e:
            last_error = str(e)
            continue
    # Fallback without search
    return _call_gemini_validator(prompt, api_key, max_tokens)


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
    available = [k for k in ["pe","pb","ev_ebitda","roe","profit_margin",
                 "revenue_growth","debt_equity","beta","dividend_yield"]
                 if data.get(k) is not None]

    ticker = data.get('ticker', '')
    name = data.get('name', ticker)
    sector = data.get('sector') or 'N/A'
    price = data.get('current_price')
    currency = data.get('currency', 'USD')

    try:
        # Step 1: Search for missing data
        search_result = ""
        if missing:
            search_prompt = f"""Search for current financial data for {name} ({ticker}).
Find: {', '.join(missing)}. Also: sector, P/E, ROE, profit margin, debt/equity, beta, dividend yield.
Return specific numbers you find."""
            try:
                search_result = _call_gemini_search(search_prompt, gemini_key, 600)
            except Exception as e:
                search_result = f"Ricerca non disponibile. Usa conoscenza su {name} ({ticker}), settore {sector}."

        # Step 2: Validate and format as JSON
        json_prompt = f"""Analista finanziario Goldman Sachs. Analizza {name} ({ticker}).

RICERCA WEB:
{search_result if search_result else 'Nessun risultato ricerca'}

DATI YAHOO FINANCE:
- Prezzo: {price} {currency} | Settore: {sector}
- P/E: {data.get('pe')} | P/B: {data.get('pb')} | EV/EBITDA: {data.get('ev_ebitda')}
- ROE: {data.get('roe')}% | Margine: {data.get('profit_margin')}% | Crescita: {data.get('revenue_growth')}%
- D/E: {data.get('debt_equity')} | Beta: {data.get('beta')} | Dividend: {data.get('dividend_yield')}%
- Target: {data.get('target_price')} | Stop: {data.get('stop_loss')} | FV: {data.get('fair_value')}

CAMPI MANCANTI: {missing if missing else 'nessuno'}

Fornisci valori per TUTTI i campi mancanti. Correggi anomalie (ROE>150% dividi per 100, dividend>20% dividi per 10).

Rispondi SOLO con JSON valido:
{{
  "validation_score": <0-100>,
  "corrections": {{
    "pe": <numero o null>,
    "pb": <numero o null>,
    "ev_ebitda": <numero o null>,
    "roe": <numero percentuale o null>,
    "profit_margin": <numero percentuale o null>,
    "revenue_growth": <numero percentuale o null>,
    "debt_equity": <numero o null>,
    "beta": <numero o null>,
    "dividend_yield": <numero percentuale o null>,
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
  "summary": "<frase italiana>"
}}"""

        raw = _call_gemini_validator(json_prompt, gemini_key, 1000)
        print(f"[Validator RAW] {ticker}: {repr(raw[:200])}")

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        validation = json.loads(raw)
        print(f"[Validator PARSED] {ticker}: corrections={validation.get('corrections',{})}")

        corrected_data = dict(data)
        corrections = validation.get("corrections", {})
        field_reasoning = validation.get("field_reasoning", {})

        field_map = {
            "pe":"pe","pb":"pb","ev_ebitda":"ev_ebitda","roe":"roe",
            "profit_margin":"profit_margin","revenue_growth":"revenue_growth",
            "debt_equity":"debt_equity","beta":"beta","dividend_yield":"dividend_yield",
            "rsi":"rsi","fair_value":"fair_value","target_price":"target_price",
            "stop_loss":"stop_loss","upside_pct":"upside_pct"
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
                "status": "error", "score": None, "reliability": "N/A",
                "issues": [str(e)], "corrected_fields": [],
                "field_reasoning": {}, "summary": f"Errore: {str(e)[:100]}",
            }
        }
