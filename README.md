# 📈 Stock Analyzer

App per l'analisi di azioni disponibili su **Trade Republic** e **Revolut**.  
Analisi tecnica, fondamentale, sentiment e screener di titoli sottovalutati.

## Funzionalità

- 🔍 **Analisi titolo** — inserisci qualsiasi ticker e ottieni: grafico candlestick, RSI, MACD, Bollinger Bands, P/E, P/B, fair value DCF, entry price, target price, stop loss, segnale Buy/Hold/Sell
- 🎯 **Screener** — scansiona S&P500, DAX, FTSE MIB, Euro Stoxx e trova le azioni più scontate
- 🌡️ **Sentiment** — Fear & Greed Index, VIX, sentiment news per ticker

## Mercati coperti

| Mercato | Titoli |
|---|---|
| 🇺🇸 S&P 500 (US) | ~70 large cap disponibili su TR |
| 🇩🇪 DAX + MDAX (Germania) | ~35 titoli Xetra |
| 🇮🇹 FTSE MIB (Italia) | 40 titoli Borsa Italiana |
| 🌍 Euro Stoxx 50 (Europa) | ~50 titoli |

## Deploy su Streamlit Cloud

1. Fai fork di questo repo su GitHub
2. Vai su [streamlit.io/cloud](https://streamlit.io/cloud)
3. "New app" → seleziona il repo → `app.py` → Deploy

## Note

- Dati con ~15 minuti di delay (Yahoo Finance gratuito)
- Non è consulenza finanziaria — usa i segnali come supporto alle tue decisioni
