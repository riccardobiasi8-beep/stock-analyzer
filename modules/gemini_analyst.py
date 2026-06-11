import requests
import json

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


def _call_gemini(prompt: str, api_key: str, max_tokens: int = 800) -> str:
    """Call Gemini API and return text response."""
    response = requests.post(
        f"{GEMINI_URL}?key={api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": max_tokens,
            },
            "tools": [{"google_search_retrieval": {}}]
        },
        timeout=25
    )
    result = response.json()

    # Debug: handle all possible response structures
    if "error" in result:
        raise Exception(f"Gemini API error: {result['error'].get('message', result['error'])}")

    candidates = result.get("candidates", [])
    if not candidates:
        # Check for prompt feedback (safety block)
        feedback = result.get("promptFeedback", {})
        block_reason = feedback.get("blockReason", "unknown")
        raise Exception(f"Nessuna risposta da Gemini (bloccato: {block_reason})")

    candidate = candidates[0]
    # Check finish reason
    finish_reason = candidate.get("finishReason", "")
    if finish_reason == "SAFETY":
        raise Exception("Risposta bloccata dai filtri di sicurezza Gemini")

    content = candidate.get("content", {})
    parts = content.get("parts", [])
    if not parts:
        raise Exception("Risposta Gemini vuota")

    return parts[0].get("text", "").strip()


def analyze_stock(data: dict, api_key: str) -> str:
    """
    Generate a short AI summary of the stock — shown above the chart.
    Focuses on fundamentals + technicals + verdict.
    """
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
    """
    Gemini reasons about realistic time to reach target price.
    This is the qualitative reasoning that pure math can't do well.
    """
    upside = data.get('upside_pct', 0) or 0
    beta = data.get('beta', 1.0) or 1.0
    sector = data.get('sector', 'N/A')
    next_earnings = None

    # Try to get next earnings from sentiment data
    try:
        next_earnings = data.get('next_earnings_date')
    except Exception:
        pass

    prompt = f"""Sei un analista quantitativo esperto. Stima in modo REALISTICO il tempo necessario affinché {data['name']} ({data['ticker']}) raggiunga il target price.

DATI OGGETTIVI:
- Prezzo attuale: {data.get('current_price')} {data.get('currency','USD')}
- Target price: {data.get('target_price')} {data.get('currency','USD')}
- Upside necessario: {upside:.1f}%
- Settore: {sector}
- Beta (volatilità vs mercato): {beta}
- RSI attuale: {data.get('rsi','N/A')}
- MACD: {'bullish' if data.get('macd',0) and data.get('macd_signal',0) and float(data.get('macd',0)) > float(data.get('macd_signal',0)) else 'bearish'}
- Posizione vs MA50: {'sopra' if data.get('ma50') and data.get('current_price',0) > data.get('ma50',0) else 'sotto'}
- Posizione vs MA200: {'sopra' if data.get('ma200') and data.get('current_price',0) > data.get('ma200',0) else 'sotto'}
- Consensus analisti: {data.get('n_analysts',0)} analisti, target medio {data.get('analyst_target','N/A')}
- ATR (volatilità giornaliera): {data.get('atr','N/A')} {data.get('currency','USD')}
- P/E: {data.get('pe','N/A')} | Crescita ricavi: {data.get('revenue_growth','N/A')}%
- Prossimi earnings: {next_earnings or 'non disponibile'}

RAGIONA così:
1. Quanto è grande il movimento richiesto ({upside:.1f}%) rispetto alla volatilità storica del titolo (ATR)?
2. Questo settore ({sector}) con beta {beta} si muove velocemente o lentamente? (utility=lento, tech growth=rapido, ciclici=dipende dal ciclo)
3. Ci sono catalizzatori imminenti (earnings, piano industriale, macro) che potrebbero accelerare o rallentare il movimento?
4. Applica la "regola della prudenza": i mercati impiegano sempre più tempo di quanto si stima inizialmente

Rispondi con:
- UNA stima del tempo più probabile (es. "6-9 mesi") con range minimo/massimo
- 2-3 frasi di motivazione specifica per questo titolo
- UN catalizzatore chiave da monitorare

Massimo 100 parole. Sii specifico, non generico."""

    try:
        return _call_gemini(prompt, api_key, 400)
    except Exception as e:
        import traceback; print(f"Gemini reason_time error: {e}\n{traceback.format_exc()}")
        return None


def analyze_sentiment_narrative(data: dict, sent: dict, api_key: str) -> str:
    """
    Gemini generates a narrative analysis of all sentiment data.
    Like the analysis Gemini gave on STM — specific, motivated, with paradox explanations.
    """
    an = sent.get("analyst", {})
    sh = sent.get("short", {})
    ea = sent.get("earnings", {})
    op = sent.get("options", {})
    ins = sent.get("insider", {})
    nw = sent.get("news", {})

    prompt = f"""Sei un analista finanziario senior di Wall Street. Analizza il sentiment di mercato su {data['name']} ({data['ticker']}) e scrivi un briefing professionale in italiano.

DATI SENTIMENT:
- Prezzo: {data.get('current_price')} {data.get('currency','USD')}
- Consensus: {an.get('consensus_label','N/A')} | {an.get('n_analysts',0)} analisti | Target medio: {an.get('target_mean','N/A')} | Upside da consensus: {an.get('upside','N/A')}%
- Short Interest: {sh.get('short_pct','N/A')}% | Days to cover: {sh.get('short_ratio','N/A')} | Variazione mese: {sh.get('change_pct','N/A')}%
- Earnings ultimi 4 trimestri: {ea.get('surprises','N/A')} | Media sorpresa: {ea.get('avg_surprise','N/A')}%
- Prossimi earnings: {ea.get('next_earnings','non disponibile')}
- Put/Call ratio: {op.get('put_call_ratio','N/A')} | Call vol: {op.get('calls_volume','N/A')} | Put vol: {op.get('puts_volume','N/A')}
- Insider: {ins.get('label','N/A')} | Acquisti: {ins.get('buys',0)} | Vendite: {ins.get('sells',0)}
- News sentiment: {nw.get('label','N/A')} (score: {nw.get('score','N/A')})

Scrivi 4 paragrafi brevi (massimo 250 parole totali):
1. **Il consensus e il paradosso** — se c'è contraddizione tra giudizio BUY/SELL e upside, spiegala con logica di mercato reale
2. **Opzioni e short interest** — cosa dicono sul posizionamento istituzionale reale
3. **Earnings e catalyst** — analizza il pattern e indica la data chiave da monitorare
4. **Verdetto sentiment** — una frase finale sul posizionamento complessivo del mercato

Sii specifico con i numeri. Spiega i paradossi come farebbe un analista senior."""

    try:
        return _call_gemini(prompt, api_key, 600)
    except Exception as e:
        import traceback; print(f"Gemini sentiment error: {e}\n{traceback.format_exc()}")
        return None


def validate_and_flag(data: dict, api_key: str) -> dict:
    """
    Gemini validates data consistency — flags anomalies but does NOT invent numbers.
    Returns dict with 'flags' list and 'reliability' score.
    """
    prompt = f"""Sei un analista finanziario. Verifica la COERENZA INTERNA di questi dati per {data['name']} ({data['ticker']}, settore: {data.get('sector','N/A')}).

DATI DA VERIFICARE:
- P/E: {data.get('pe')} | P/B: {data.get('pb')} | EV/EBITDA: {data.get('ev_ebitda')}
- ROE: {data.get('roe')}% | Margine netto: {data.get('profit_margin')}% | Crescita ricavi: {data.get('revenue_growth')}%
- Debt/Equity: {data.get('debt_equity')} | Beta: {data.get('beta')} | Dividend yield: {data.get('dividend_yield')}%
- Prezzo: {data.get('current_price')} | Fair value: {data.get('fair_value')} | Target: {data.get('target_price')}

VERIFICA SOLO la coerenza logica. Per esempio:
- ROE molto alto (>50%) con margini bassi è impossibile — uno dei due è sbagliato
- P/E di 500 per un'azienda con EPS positivo è anomalo
- Dividend yield del 15%+ per una growth tech è impossibile
- Debt/equity negativo non esiste

Rispondi SOLO con JSON:
{{
  "flags": [
    {{"field": "nome_campo", "issue": "descrizione problema in italiano", "severity": "alta|media"}}
  ],
  "reliability_score": <0-100>,
  "note": "<una frase in italiano sul livello di affidabilità complessivo>"
}}

Se non ci sono anomalie, restituisci flags: []
NON inventare valori corretti. Solo segnala problemi di coerenza."""

    try:
        raw = _call_gemini(prompt, api_key, 400)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        result = json.loads(raw)
        return {
            "flags": result.get("flags", []),
            "reliability_score": result.get("reliability_score", 100),
            "note": result.get("note", "")
        }
    except Exception as e:
        return {"flags": [], "reliability_score": 100, "note": ""}
