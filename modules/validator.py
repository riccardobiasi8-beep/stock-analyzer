import json
import requests


def validate_stock_data(data: dict, gemini_key: str) -> dict:
    """
    Uses Gemini to:
    1. Estimate missing fields with reasoning
    2. Correct anomalous values with reasoning
    3. Validate calculated metrics (target, stop, fair value)
    Returns data with corrections + per-field reasoning for tooltips.
    """
    if not gemini_key:
        return {**data, "validation": {
            "status": "skipped", "issues": [], "score": None,
            "corrected_fields": [], "field_reasoning": {},
            "reliability": "N/A", "summary": ""
        }}

    missing = [k for k in ["pe","pb","ev_ebitda","roe","profit_margin",
               "revenue_growth","debt_equity","beta","dividend_yield"]
               if data.get(k) is None]
    available = [k for k in ["pe","pb","ev_ebitda","roe","profit_margin",
                 "revenue_growth","debt_equity","beta","dividend_yield"]
                 if data.get(k) is not None]

    sector = data.get('sector','N/A') or 'N/A'
    sector_note = ""
    if sector in [None, 'N/A', '']:
        sector_note = f"""NOTA IMPORTANTE: Settore non disponibile da Yahoo Finance.
Identifica il settore dal ticker {data.get('ticker','?')} e nome {data.get('name','?')}.
Esempi: ticker .F=Francoforte, .MI=Milano, .PA=Parigi, .L=Londra.
Usa la tua conoscenza del mercato per identificare settore e applicare stime appropriate."""

    prompt = f"""Sei un analista finanziario senior di Goldman Sachs con accesso a Google Search.

STEP 1 — CERCA I DATI REALI:
Cerca su Google i dati fondamentali aggiornati per {data.get('name','?')} ({data.get('ticker','?')}).
Query suggerite:
- "{data.get('ticker','?')} P/E ratio 2024 2025"
- "{data.get('name','?')} ROE profit margin annual report"
- "{data.get('ticker','?')} fundamental data Yahoo Finance"
- "{data.get('name','?')} settore industria borsa"

DATI GIÀ DISPONIBILI (da Yahoo Finance, potrebbero essere incompleti):
- Settore: {sector} | Industria: {data.get('industry','N/A')}
- Prezzo: {data.get('current_price')} {data.get('currency','USD')} | Market cap: {data.get('market_cap')}
- P/E: {data.get('pe')} | P/B: {data.get('pb')} | EV/EBITDA: {data.get('ev_ebitda')}
- ROE: {data.get('roe')}% | Margine netto: {data.get('profit_margin')}% | Crescita ricavi: {data.get('revenue_growth')}%
- Debt/Equity: {data.get('debt_equity')} | Beta: {data.get('beta')} | Dividend yield: {data.get('dividend_yield')}%
- RSI: {data.get('rsi')}
- Target calcolato: {data.get('target_price')} | Stop calcolato: {data.get('stop_loss')} | Fair Value: {data.get('fair_value')}
- Consensus analisti: {data.get('analyst_target')} ({data.get('n_analysts',0)} analisti) | Upside: {data.get('upside_pct')}%
- ATR: {data.get('atr')} | Tempo stimato: {data.get('time_label')}

{sector_note}
CAMPI MANCANTI ({len(missing)} su 9): {missing if missing else 'nessuno'}
CAMPI DISPONIBILI: {available if available else 'nessuno — cerca tutto su Google'}

STEP 2 — COMPILA I DATI:
Usa i dati trovati su Google per compilare i campi mancanti con valori REALI.
Solo se non trovi dati reali, usa stime basate sul settore.

STEP 3 — CORREGGI ANOMALIE:
- ROE >150% o <-150%: errore di scala Yahoo, dividi per 100
- Dividend yield >20%: errore di scala, dividi per 10
- P/E <0 con azienda redditizia: usa valore assoluto
- Verifica che target e stop loss siano ragionevoli

Rispondi SOLO con JSON valido:
{{
  "validation_score": <0-100>,
  "corrections": {{
    "pe": <numero reale trovato o stimato, null se già ok>,
    "pb": <numero o null>,
    "ev_ebitda": <numero o null>,
    "roe": <numero percentuale es. 14.5 per 14.5%, null se ok>,
    "profit_margin": <numero percentuale, null se ok>,
    "revenue_growth": <numero percentuale, null se ok>,
    "debt_equity": <numero o null>,
    "beta": <numero o null>,
    "dividend_yield": <numero percentuale, null se ok>,
    "rsi": <numero o null>,
    "fair_value": <numero o null>,
    "target_price": <numero o null>,
    "stop_loss": <numero o null>,
    "upside_pct": <numero o null>
  }},
  "field_reasoning": {{
    "pe": "<trovato X su Google / stimato X perché...>",
    "pb": null,
    "ev_ebitda": null,
    "roe": "<spiegazione>",
    "profit_margin": null,
    "revenue_growth": null,
    "debt_equity": "<spiegazione>",
    "beta": "<spiegazione>",
    "dividend_yield": "<spiegazione>",
    "rsi": null,
    "fair_value": "<spiegazione>",
    "target_price": "<spiegazione>",
    "stop_loss": null,
    "upside_pct": null
  }},
  "data_reliability": "<Alta|Media|Bassa>",
  "summary": "<frase italiana: dati trovati su Google + correzioni applicate>"
}}

"""

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1200},
                "tools": [{"google_search_retrieval": {}}]
            },
            timeout=30
        )

        result = response.json()
        if "error" in result:
            raise Exception(result["error"].get("message", "Gemini error"))
        candidates = result.get("candidates", [])
        if not candidates:
            raise Exception("Nessuna risposta da Gemini")

        finish_reason = candidates[0].get("finishReason", "")
        if finish_reason == "SAFETY":
            raise Exception("Risposta bloccata da filtri sicurezza")

        raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        validation = json.loads(raw_text)

        # Apply corrections to data
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
                num_val = float(corrected_val)
                if original is None or abs(num_val - float(original)) > 0.001:
                    corrected_data[data_key] = round(num_val, 2)
                    corrected_fields.append(f"{data_key}: {original} → {round(num_val, 2)}")
            except (TypeError, ValueError):
                pass

        # Recalculate upside if target was corrected
        corrected_keys = [c.split(":")[0].strip() for c in corrected_fields]
        if "target_price" in corrected_keys:
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
            "issues": [r for r in field_reasoning.values() if r],
            "corrected_fields": corrected_fields,
            "field_reasoning": {k: v for k, v in field_reasoning.items() if v},
            "summary": validation.get("summary", ""),
        }

        return corrected_data

    except Exception as e:
        import traceback
        print(f"[Validator error] {e}\n{traceback.format_exc()}")
        return {
            **data,
            "validation": {
                "status": "error",
                "score": None,
                "reliability": "N/A",
                "issues": [f"Errore validazione: {str(e)}"],
                "corrected_fields": [],
                "field_reasoning": {},
                "summary": "Validazione non disponibile",
            }
        }
