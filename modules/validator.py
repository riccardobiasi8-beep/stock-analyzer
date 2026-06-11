import json
import requests

# Uses Gemini for validation


def validate_stock_data(data: dict, gemini_key: str) -> dict:
    """
    Passes raw stock data through Groq for validation and anomaly correction.
    Returns cleaned data with validation report.
    """
    if not gemini_key:
        return {**data, "validation": {"status": "skipped", "issues": [], "score": None, "corrected_fields": [], "reliability": "N/A", "summary": ""}}

    # Build validation prompt with all extracted data
    prompt = f"""Sei un analista finanziario senior. Ti fornisco dati estratti da Yahoo Finance per {data.get('name', '?')} ({data.get('ticker', '?')}).

Il tuo compito è VALIDARE ogni campo e CORREGGERE le anomalie.

DATI ESTRATTI:
- Prezzo attuale: {data.get('current_price')} {data.get('currency', 'USD')}
- P/E ratio: {data.get('pe')}
- P/B ratio: {data.get('pb')}
- EV/EBITDA: {data.get('ev_ebitda')}
- ROE: {data.get('roe')}%
- Margine netto: {data.get('profit_margin')}%
- Crescita ricavi: {data.get('revenue_growth')}%
- Debt/Equity: {data.get('debt_equity')}
- Beta: {data.get('beta')}
- Dividend yield: {data.get('dividend_yield')}%
- Market cap: {data.get('market_cap')}
- RSI: {data.get('rsi')}
- Fair Value (calcolato): {data.get('fair_value')}
- Target price (calcolato): {data.get('target_price')}
- Consensus analisti target: {data.get('analyst_target')}
- N. analisti: {data.get('n_analysts', 0)}
- Upside %: {data.get('upside_pct')}%
- Settore: {data.get('sector')}
- Industria: {data.get('industry')}

REGOLE DI VALIDAZIONE E CORREZIONE:
1. P/E: valido 0-100 per aziende normali, 100-500 solo per aziende in recovery con EPS vicino a zero.
   - Se P/E > 500 o negativo: STIMA il P/E corretto usando (Prezzo / EPS forward) se disponibile, oppure usa la media di settore
   - Per STM/semiconduttori in ciclo down: P/E 30-60 è normale
2. P/B: valido 0.1-20. Se <0: usa valore assoluto. Se >50: anomalia, stima da settore
3. ROE: valido -50% a +80%. Se >100% o <-100%: correggi dividendo per 100 (probabilmente errore di scala)
4. Margine netto: valido -30% a +50%. Se fuori range: correggi dividendo per 100
5. Debt/Equity: per aziende tech/industriali valido 0-3. Per banche può essere 10-20 (normale).
   - Se appare NULL o mancante per azienda con dati finanziari: stima dalla media settore
6. Beta: valido 0.1-4.0. Se mancante: stima dal settore (tech=1.3, utility=0.5, banche=1.0)
7. Dividend yield: valido 0-15%. Se >20%: probabilmente errore, correggi dividendo per 10
8. RSI: deve essere 0-100. Se fuori range: null
9. Fair Value: non deve essere >2x il prezzo attuale né <0.3x. Se anomalo: usa consensus analisti
10. Upside %: ricalcola sempre come (target - prezzo) / prezzo * 100

IMPORTANTE: Per ogni campo anomalo NON mettere "N/A" — invece STIMA il valore corretto più plausibile
basandoti su: settore={data.get('sector')}, prezzo={data.get('current_price')}, EPS stimabile dagli altri dati.
Usa "N/A" SOLO se è impossibile stimare qualsiasi valore ragionevole.

Rispondi SOLO con un JSON valido in questo formato esatto (nessun testo fuori dal JSON):
{{
  "validation_score": <numero 0-100 che indica qualità generale dei dati>,
  "issues_found": [<lista stringhe che descrivono anomalie trovate e come le hai corrette>],
  "corrections": {{
    "pe": <numero corretto, o null se già ok, MAI "N/A" a meno che impossibile stimare>,
    "pb": <numero corretto o null>,
    "ev_ebitda": <numero corretto o null>,
    "roe": <numero corretto o null>,
    "profit_margin": <numero corretto o null>,
    "revenue_growth": <numero corretto o null>,
    "debt_equity": <numero corretto o null se impossibile stimare>,
    "beta": <numero corretto o null>,
    "dividend_yield": <numero corretto o null>,
    "rsi": <numero corretto o null>,
    "fair_value": <numero corretto o null>,
    "target_price": <numero corretto o null>,
    "upside_pct": <numero corretto o null>
  }},
  "data_reliability": "<Alta|Media|Bassa>",
  "summary": "<una frase in italiano che riassume anomalie trovate e correzioni applicate>"
}}

Usa null per campi già corretti. Fornisci numeri stimati per anomalie, non stringhe "N/A"."""

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 800}
            },
            timeout=25
        )

        result = response.json()
        if "error" in result:
            raise Exception(result["error"].get("message", "Gemini error"))
        candidates = result.get("candidates", [])
        if not candidates:
            raise Exception("Nessuna risposta da Gemini")
        raw_text = candidates[0]["content"]["parts"][0]["text"].strip()

        # Clean JSON if wrapped in markdown
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        validation = json.loads(raw_text)

        # Apply corrections to data
        corrected_data = dict(data)
        corrections = validation.get("corrections", {})

        field_map = {
            "pe": "pe", "pb": "pb", "ev_ebitda": "ev_ebitda",
            "roe": "roe", "profit_margin": "profit_margin",
            "revenue_growth": "revenue_growth", "debt_equity": "debt_equity",
            "beta": "beta", "dividend_yield": "dividend_yield",
            "rsi": "rsi", "fair_value": "fair_value",
            "target_price": "target_price", "upside_pct": "upside_pct"
        }

        corrected_fields = []
        for key, data_key in field_map.items():
            corrected_val = corrections.get(key)
            if corrected_val is None:
                continue  # null = no correction needed
            original = corrected_data.get(data_key)
            if corrected_val == "N/A":
                corrected_data[data_key] = None
                corrected_fields.append(f"{data_key}: {original} → N/A (non stimabile)")
            else:
                # Try to convert to float
                try:
                    num_val = float(corrected_val)
                    if num_val != original:
                        corrected_data[data_key] = round(num_val, 2)
                        corrected_fields.append(f"{data_key}: {original} → {round(num_val, 2)}")
                except (TypeError, ValueError):
                    pass  # ignore non-numeric corrections

        # Recalculate upside if target was corrected
        if "target_price" in [c.split(":")[0] for c in corrected_fields]:
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
            "issues": validation.get("issues_found", []),
            "corrected_fields": corrected_fields,
            "summary": validation.get("summary", ""),
        }

        return corrected_data

    except Exception as e:
        # Never block the app if validation fails
        return {
            **data,
            "validation": {
                "status": "error",
                "score": None,
                "reliability": "N/A",
                "issues": [f"Errore validazione: {str(e)}"],
                "corrected_fields": [],
                "summary": "Validazione non disponibile",
            }
        }
        
