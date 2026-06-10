import json
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def validate_stock_data(data: dict, groq_key: str) -> dict:
    """
    Passes raw stock data through Groq for validation and anomaly correction.
    Returns cleaned data with validation report.
    """
    if not groq_key:
        return {**data, "validation": {"status": "skipped", "issues": [], "score": None}}

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

REGOLE DI VALIDAZIONE:
1. P/E: valido 0-100 per aziende normali, 100-500 solo per aziende in recovery. Se negativo o >500 → anomalia
2. P/B: valido 0.1-20. Se <0 o >50 → anomalia
3. ROE: valido -50% a +80%. Se >100% o <-100% → probabile errore dati
4. Margine netto: valido -30% a +50% per la maggior parte dei settori
5. Debt/Equity: valido 0-5 per aziende normali, banche possono avere valori più alti
6. Beta: valido 0.1-4.0. Se <0 o >5 → anomalia
7. Dividend yield: valido 0-15%. Se >20% → sospetto, verifica
8. RSI: deve essere 0-100. Fuori range → anomalia
9. Fair Value: non deve essere >3x il prezzo attuale né <0.2x
10. Upside %: se >200% o <-80% con consensus analisti disponibile → ricalcola dal consensus
11. Crescita ricavi: valido -50% a +100%. Fuori range → sospetto

Rispondi SOLO con un JSON valido in questo formato esatto (nessun testo fuori dal JSON):
{{
  "validation_score": <numero 0-100 che indica qualità generale dei dati>,
  "issues_found": [<lista stringhe che descrivono anomalie trovate>],
  "corrections": {{
    "pe": <valore corretto o null se ok o "N/A" se anomalia>,
    "pb": <valore corretto o null se ok o "N/A" se anomalia>,
    "ev_ebitda": <valore corretto o null se ok>,
    "roe": <valore corretto o null se ok>,
    "profit_margin": <valore corretto o null se ok>,
    "revenue_growth": <valore corretto o null se ok>,
    "debt_equity": <valore corretto o null se ok>,
    "beta": <valore corretto o null se ok>,
    "dividend_yield": <valore corretto o null se ok>,
    "rsi": <valore corretto o null se ok>,
    "fair_value": <valore corretto o null se ok>,
    "target_price": <valore corretto o null se ok>,
    "upside_pct": <valore corretto o null se ok>
  }},
  "data_reliability": "<Alta|Media|Bassa>",
  "summary": "<una frase in italiano che riassume la qualità dei dati>"
}}

Usa null per i campi senza anomalie. Usa "N/A" solo per anomalie gravi che rendono il dato inutilizzabile."""

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {groq_key}"
            },
            json={
                "model": GROQ_MODEL,
                "max_tokens": 800,
                "temperature": 0.1,  # low temperature for factual validation
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )

        result = response.json()
        raw_text = result["choices"][0]["message"]["content"].strip()

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
            if corrected_val is not None:  # null = no correction needed
                original = corrected_data.get(data_key)
                if corrected_val == "N/A":
                    corrected_data[data_key] = None
                    corrected_fields.append(f"{data_key}: {original} → N/A")
                elif corrected_val != original:
                    corrected_data[data_key] = corrected_val
                    corrected_fields.append(f"{data_key}: {original} → {corrected_val}")

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
