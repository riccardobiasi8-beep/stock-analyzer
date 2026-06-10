import yfinance as yf
import pandas as pd
from modules.analyzer import get_stock_data
import streamlit as st

# --- Tickers disponibili su Trade Republic ---
# US S&P500 large cap (subset rappresentativo, disponibili su TR via listing europeo)
SP500_TOP = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B",
    "LLY", "AVGO", "JPM", "UNH", "XOM", "V", "MA", "PG", "JNJ", "HD",
    "MRK", "ABBV", "CVX", "COST", "PEP", "KO", "WMT", "CRM", "BAC",
    "ACN", "MCD", "TMO", "CSCO", "ABT", "NFLX", "ADBE", "AMD", "TXN",
    "NEE", "PM", "DHR", "QCOM", "UNP", "RTX", "HON", "IBM", "GE",
    "SBUX", "AMAT", "CAT", "INTU", "NOW", "AMGN", "PFE", "GILD",
    "DE", "PYPL", "DIS", "BKNG", "PANW", "LRCX", "ADI", "MELI",
    "INTC", "F", "GM", "T", "VZ", "WFC", "GS", "MS", "C", "AXP",
    "SHOP", "UBER", "LYFT", "SNAP", "PINS", "RBLX", "PLTR", "SOFI",
]

# DAX (Germania - Xetra, tutti disponibili su TR)
DAX = [
    "ADS.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE", "CBK.DE",
    "CON.DE", "1COV.DE", "DTE.DE", "EOAN.DE", "FRE.DE", "HEI.DE",
    "HEN3.DE", "IFX.DE", "MBG.DE", "MRK.DE", "MTX.DE", "MUV2.DE",
    "P911.DE", "RWE.DE", "SAP.DE", "SIE.DE", "SY1.DE", "VOW3.DE",
    "VNA.DE", "ZAL.DE", "DBK.DE", "DHL.DE", "ENR.DE", "DHER.DE",
    "AIR.DE", "BEI.DE", "SHL.DE", "DPW.DE",
]

# FTSE MIB (Italia - Borsa Italiana, disponibili su TR)
FTSE_MIB = [
    "A2A.MI", "AMP.MI", "ATL.MI", "AZM.MI", "BAMI.MI", "BGN.MI",
    "BPE.MI", "BPSO.MI", "BZU.MI", "CPR.MI", "CNHI.MI", "DIA.MI",
    "ENEL.MI", "ENI.MI", "ERG.MI", "FCA.MI", "FCT.MI", "FHI.MI",
    "G.MI", "HER.MI", "INW.MI", "ISP.MI", "ITALGAS.MI", "LDO.MI",
    "MB.MI", "MONC.MI", "NEXI.MI", "PIRC.MI", "PRY.MI", "PST.MI",
    "REC.MI", "RACE.MI", "SPM.MI", "SRG.MI", "STM.MI", "TEN.MI",
    "TIT.MI", "TRN.MI", "UCG.MI", "UNI.MI",
]

# Euro Stoxx 50 (altri mercati europei)
EUROSTOXX = [
    "ASML.AS", "INGA.AS", "PHIA.AS", "AD.AS", "HEIA.AS",
    "MC.PA", "OR.PA", "SAN.PA", "BNP.PA", "ACA.PA", "CS.PA",
    "STLAM.MI", "NOVOB.CO",
    "SIE.DE", "ALV.DE", "SAP.DE", "MUV2.DE",
    "IBE.MC", "SAN.MC", "ITX.MC",
    "NESN.SW", "ROG.SW", "NOVN.SW",
]

ALL_TICKERS = list(set(SP500_TOP + DAX + FTSE_MIB + EUROSTOXX))

MARKET_GROUPS = {
    "🇺🇸 S&P 500 (US)": SP500_TOP,
    "🇩🇪 DAX (Germania)": DAX,
    "🇮🇹 FTSE MIB (Italia)": FTSE_MIB,
    "🌍 Euro Stoxx (Europa)": EUROSTOXX,
    "🌐 Tutti i mercati": ALL_TICKERS,
}


def run_screener(tickers: list, min_score: int = 60, max_results: int = 20) -> pd.DataFrame:
    """
    Screen a list of tickers and return those with score >= min_score.
    Shows a progress bar in Streamlit.
    """
    results = []
    progress = st.progress(0, text="Analisi in corso...")
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        progress.progress((i + 1) / total, text=f"Analisi {ticker}... ({i+1}/{total})")
        data = get_stock_data(ticker, period="6mo")
        if "error" not in data:
            results.append({
                "Ticker": data["ticker"],
                "Nome": data["name"],
                "Settore": data["sector"],
                "Prezzo": data["current_price"],
                "Valuta": data["currency"],
                "Entry": data["entry_price"],
                "Target": data["target_price"],
                "Stop Loss": data["stop_loss"],
                "Upside %": data["upside_pct"],
                "Fair Value": data["fair_value"],
                "Segnale": data["signal"],
                "Score": data["score"],
                "RSI": data["rsi"],
                "P/E": data["pe"],
                "P/B": data["pb"],
            })

    progress.empty()

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df[df["Score"] >= min_score].sort_values("Score", ascending=False)
    return df.head(max_results)
