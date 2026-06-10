import yfinance as yf
import pandas as pd
import time
from modules.analyzer import get_stock_data
import streamlit as st

# ── S&P 500 — 451 titoli ──────────────────────────────────────────────────────
SP500_FULL = [
    # Mega cap / Tech
    "AAPL","MSFT","NVDA","AMZN","GOOGL","GOOG","META","TSLA","AVGO","ORCL",
    "AMD","INTC","QCOM","TXN","ADI","AMAT","LRCX","KLAC","MCHP","MRVL",
    "ADBE","CRM","NOW","INTU","SNOW","PANW","CRWD","FTNT","CDNS","SNPS",
    "SHOP","UBER","ABNB","DASH","RBLX","PLTR","COIN","SOFI",
    "NFLX","DIS","CMCSA","WBD","PARA","LYV","SPOT","TTWO","EA",
    # Financials
    "JPM","BAC","WFC","GS","MS","C","AXP","BLK","SCHW","USB",
    "PNC","TFC","COF","DFS","SYF","ALLY","MTB","CFG","HBAN","KEY",
    "FITB","RF","ZION","CMA","NTRS","STT","BK","TROW","IVZ","AMG",
    "BX","KKR","APO","CG","ARES","FDS","MSCI","SPGI","MCO",
    "ICE","CME","CBOE",
    # Healthcare
    "UNH","JNJ","LLY","MRK","ABBV","PFE","AMGN","GILD","BIIB","MRNA",
    "REGN","VRTX","BMY","NVO","NBIX","ALNY",
    "TMO","ABT","DHR","SYK","MDT","BSX","ISRG","EW","DXCM","IDXX",
    "ZTS","MTD","WST","BAX","BDX","COO","HOLX","HSIC",
    "CI","ELV","CVS","HCA","MOH","CNC","HUM","WBA","MCK","ABC","CAH",
    # Consumer Staples
    "PG","KO","PEP","WMT","COST","MCD","SBUX","NKE","TGT","DG",
    "DLTR","KR","SYY","HSY","K","GIS","CPB","HRL","MKC","SJM",
    "CAG","ADM","BG","MOS","CF",
    "PM","MO",
    # Consumer Discretionary
    "HD","LOW","TJX","ROST","BURL","ANF","AEO","PVH","RL","TPR",
    "LULU","ONON","F","GM","RACE",
    "MAR","HLT","H","WH","CHH","RCL","CCL","NCLH",
    "BKNG","EXPE","LVS","MGM","WYNN","CZR",
    "YUM","QSR","DPZ","CMG","WEN",
    "ETSY","W","CHWY",
    # Energy
    "XOM","CVX","COP","EOG","PXD","DVN","MPC","PSX","VLO","HES",
    "OXY","SLB","HAL","BKR","NOV","HP",
    "MRO","APA","FANG","CTRA","OVV","SM","RRC","SWN","EQT",
    "KMI","WMB","OKE","LNG","ET","EPD","MMP","TRGP",
    # Industrials
    "GE","HON","CAT","DE","RTX","LMT","NOC","GD","BA","TDG",
    "UPS","FDX","DAL","UAL","AAL","LUV","ALK",
    "UNP","CSX","NSC","WAB",
    "MMM","EMR","ETN","ROK","AME","ROP","IEX","XYL",
    "PWR","FLR","STLD","VMC","MLM","CRH",
    "PCAR","CMI","TEX","AGCO","CNHI",
    # Utilities
    "NEE","DUK","SO","D","AEP","EXC","SRE","XEL","WEC","ES",
    "ETR","FE","PPL","CMS","NI","AES","PNW","EVRG",
    "AWK",
    # Real Estate
    "AMT","PLD","EQIX","CCI","SPG","O","WELL","PSA","EQR","AVB",
    "VTR","BXP","SLG","VNO","KIM","REG","FRT","NNN","WPC",
    "DLR","SBAC","IRM","EXR","CUBE",
    # Materials
    "LIN","APD","ECL","DD","DOW","PPG","SHW","RPM",
    "NEM","AEM","FCX","AA","NUE","STLD","X","CLF","RS","CMC",
    "LYB","CE","EMN","HUN",
    # Telecom
    "T","VZ","TMUS",
    # Other
    "V","MA","PYPL","BRK-B","UNP","F","GM",
    "SNAP","PINS","MELI",
]
SP500_FULL = list(dict.fromkeys([t for t in SP500_FULL if t]))

# ── DAX 40 + MDAX — 80 titoli ─────────────────────────────────────────────────
DAX_FULL = [
    # DAX 40
    "ADS.DE","AIR.DE","ALV.DE","BAS.DE","BAYN.DE","BEI.DE","BMW.DE",
    "CBK.DE","CON.DE","1COV.DE","DBK.DE","DHL.DE","DTE.DE","DHER.DE",
    "EOAN.DE","ENR.DE","FRE.DE","FME.DE","HEI.DE","HEN3.DE",
    "IFX.DE","MBG.DE","MRK.DE","MTX.DE","MUV2.DE","P911.DE","PAH3.DE",
    "PUM.DE","RWE.DE","SAP.DE","SHL.DE","SIE.DE","SY1.DE",
    "VNA.DE","VOW3.DE","ZAL.DE","DPW.DE","SMHN.DE","DTG.DE","QIAGEN.DE",
    # MDAX
    "AFX.DE","BOSS.DE","CARL.DE","EVD.DE","G1A.DE","GXI.DE","HAB.DE",
    "HFG.DE","HOT.DE","KGX.DE","LEG.DE","LXS.DE","MBB.DE","MDG1.DE",
    "NDA.DE","NDX1.DE","PSAN.DE","PBB.DE","RRTL.DE","S92.DE",
    "SDF.DE","SGL.DE","TLX.DE","TUI1.DE","UTDI.DE","VBK.DE",
    "WAF.DE","WCH.DE","O2D.DE","NOEJ.DE","FNTN.DE","BC8.DE",
    "BNR.DE","CSAG.DE","DWNI.DE","EVT.DE","FCHN.DE","GBF.DE",
    "HNR1.DE","HHFA.DE","INH.DE","JEN.DE","KWS.DE","MANZ.DE",
]
DAX_FULL = list(dict.fromkeys(DAX_FULL))

# ── FTSE MIB + Mid Cap Italia — 83 titoli ────────────────────────────────────
FTSE_MIB_FULL = [
    # FTSE MIB 40
    "A2A.MI","AMP.MI","ATL.MI","AZM.MI","BAMI.MI","BGN.MI","BPE.MI",
    "BZU.MI","CPR.MI","CNHI.MI","DIA.MI","ENEL.MI","ENI.MI",
    "ERG.MI","FCT.MI","FHI.MI","G.MI","HER.MI","INW.MI",
    "ISP.MI","ITALGAS.MI","LDO.MI","MB.MI","MONC.MI","NEXI.MI",
    "PIRC.MI","PRY.MI","PST.MI","REC.MI","RACE.MI","SPM.MI","SRG.MI",
    "STM.MI","TEN.MI","TIT.MI","TRN.MI","UCG.MI","UNI.MI","STLAM.MI",
    "BPSO.MI",
    # Mid cap
    "AGL.MI","ANIM.MI","BE.MI","BMED.MI","BMPS.MI","BRE.MI",
    "CLN.MI","CML.MI","ELN.MI","EXO.MI","FILA.MI","IGD.MI",
    "IREN.MI","JUV.MI","MAPS.MI","MARR.MI","MFB.MI","MIL.MI",
    "OVS.MI","PRI.MI","SOL.MI","SFER.MI","TBS.MI","TIP.MI",
    "TOD.MI","TXT.MI","VIS.MI","CVAL.MI","DMWN.MI","GEO.MI",
    "IPC.MI","KRE.MI","MFT.MI","PGTL.MI","SES.MI","WKD.MI",
    "CIR.MI","ENAV.MI","FNM.MI","HRAIL.MI","ITM.MI","SAFE.MI",
]
FTSE_MIB_FULL = list(dict.fromkeys(FTSE_MIB_FULL))

# ── Europa — Olanda, Francia, Spagna, Svizzera, Danimarca, Belgio, Svezia, UK ─
EUROSTOXX_FULL = [
    # Olanda
    "ASML.AS","INGA.AS","PHIA.AS","AD.AS","HEIA.AS","NN.AS","RAND.AS",
    "AGN.AS","AKZA.AS","DSM.AS","IMCD.AS","WKL.AS","URW.AS",
    # Francia
    "MC.PA","OR.PA","SAN.PA","BNP.PA","ACA.PA","CS.PA","ENGI.PA",
    "AI.PA","AIR.PA","BN.PA","CAP.PA","DG.PA","DSY.PA",
    "HO.PA","KER.PA","LR.PA","ML.PA","ORA.PA","PUB.PA","RI.PA",
    "RNO.PA","SGO.PA","STLA.PA","STM.PA","SU.PA","TTE.PA","VIE.PA",
    # Spagna
    "IBE.MC","SAN.MC","ITX.MC","BBVA.MC","TEF.MC","REP.MC","AMS.MC",
    "ANA.MC","BKT.MC","ELE.MC","ENG.MC","FER.MC",
    "GRF.MC","IAG.MC","MAP.MC","MEL.MC","MTS.MC","NTGY.MC","RED.MC",
    "SAB.MC","SGRE.MC",
    # Svizzera
    "NESN.SW","ROG.SW","NOVN.SW","ABBN.SW","ADEN.SW","CSGN.SW",
    "GEBN.SW","GIVN.SW","HOLN.SW","LOGN.SW","LONN.SW","PGHN.SW",
    "SCMN.SW","SGSN.SW","SIKA.SW","SLHN.SW","UBSG.SW",
    "UHRN.SW","VACN.SW","ZURN.SW","ALC.SW","BALN.SW",
    # Danimarca
    "NOVOB.CO","CARL-B.CO","COLO-B.CO","DANSKE.CO","DSV.CO",
    "GN.CO","ISS.CO","MAERSK-B.CO","NZYM-B.CO","ORSTED.CO",
    "PNDORA.CO","RBREW.CO","TRYG.CO","VWS.CO",
    # Belgio
    "ABI.BR","AGS.BR","ACKB.BR","BEFB.BR","COLR.BR",
    "GBLB.BR","KBC.BR","LOTB.BR","PROX.BR","SOLB.BR","UCB.BR",
    # Svezia
    "ASSA-B.ST","ATCO-A.ST","ERIC-B.ST","ESSITY-B.ST",
    "EVO.ST","GETI-B.ST","HM-B.ST","INVE-B.ST","NDA-SE.ST",
    "SAND.ST","SCA-B.ST","SEB-A.ST","SKA-B.ST","SKF-B.ST",
    "SWED-A.ST","TEL2-B.ST","TELIA.ST","VOLV-B.ST",
    # UK
    "SHEL.L","BP.L","HSBA.L","LLOY.L","BARC.L","RIO.L","BHP.L",
    "AZN.L","GSK.L","ULVR.L","DGE.L","REL.L","VOD.L","BT-A.L",
    "NG.L","SSE.L","NWG.L","STAN.L","GLEN.L","AAL.L","ABF.L",
    "AHT.L","ANTO.L","AUTO.L","AV.L","BA.L","BATS.L",
    "BNZL.L","CCH.L","CPG.L","CRDA.L","CRH.L","EZJ.L",
    "FERG.L","FLTR.L","FRES.L","HIK.L","HL.L","HLMA.L","HLN.L",
    "IHG.L","IMB.L","ITV.L","JD.L","KGF.L","LAND.L","LGEN.L",
    "MKS.L","MNDI.L","MNG.L","MTO.L","NXT.L","OCDO.L","PHNX.L",
    "PRU.L","PSN.L","RKT.L","RMV.L","RR.L","SBRY.L",
    "SGRO.L","SKG.L","SMDS.L","SN.L","TSCO.L","UU.L","WPP.L",
]
EUROSTOXX_FULL = list(dict.fromkeys(EUROSTOXX_FULL))

ALL_TICKERS = list(dict.fromkeys(SP500_FULL + DAX_FULL + FTSE_MIB_FULL + EUROSTOXX_FULL))

MARKET_GROUPS = {
    "🇺🇸 S&P 500 (US)": SP500_FULL,
    "🇩🇪 DAX + MDAX (Germania)": DAX_FULL,
    "🇮🇹 FTSE MIB + Mid Cap (Italia)": FTSE_MIB_FULL,
    "🌍 Europa (FR/ES/CH/DK/BE/SE/UK)": EUROSTOXX_FULL,
    "🌐 Tutti i mercati": ALL_TICKERS,
}


def run_screener(tickers: list, min_score: int = 60, max_results: int = 20) -> pd.DataFrame:
    """Screen tickers and return those with score >= min_score."""
    results = []
    progress = st.progress(0, text="Analisi in corso...")
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        progress.progress((i + 1) / total, text=f"Analisi {ticker}... ({i+1}/{total})")
        try:
            data = get_stock_data(ticker, period="1y")
            time.sleep(0.3)
        except Exception:
            time.sleep(1)
            continue
        if "error" not in data and data.get("current_price"):
            results.append({
                "Ticker": data["ticker"],
                "Nome": data["name"],
                "Settore": data["sector"],
                "Prezzo": data["current_price"],
                "Valuta": data["currency"],
                "Entry": data["entry_price"],
                "Target": data["target_price"],
                "Stop Loss": data["stop_loss"],
                "Upside % lordo": data.get("upside_pct"),
                "Upside % netto": data.get("upside_net_pct"),
                "Tempo stimato": data.get("time_category", "N/A"),
                "Rend. annualizzato": data.get("annualized_return"),
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
