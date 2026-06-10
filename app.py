import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from modules.analyzer import get_stock_data
from modules.screener import run_screener, MARKET_GROUPS
from modules.sentiment import get_fear_greed, get_news_sentiment, get_macro_context, get_full_sentiment
import time

# ── Dizionario ticker → nome (per ricerca per nome) ───────────────────────────
TICKER_DICT = {
    "AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com Inc.", "GOOGL": "Alphabet Inc. (Google)", "META": "Meta Platforms (Facebook)",
    "TSLA": "Tesla Inc.", "BRK-B": "Berkshire Hathaway", "LLY": "Eli Lilly",
    "AVGO": "Broadcom Inc.", "JPM": "JPMorgan Chase", "UNH": "UnitedHealth Group",
    "XOM": "Exxon Mobil", "V": "Visa Inc.", "MA": "Mastercard", "PG": "Procter & Gamble",
    "JNJ": "Johnson & Johnson", "HD": "Home Depot", "MRK": "Merck & Co.",
    "ABBV": "AbbVie Inc.", "CVX": "Chevron Corporation", "COST": "Costco Wholesale",
    "PEP": "PepsiCo Inc.", "KO": "Coca-Cola Company", "WMT": "Walmart Inc.",
    "CRM": "Salesforce Inc.", "BAC": "Bank of America", "ACN": "Accenture",
    "MCD": "McDonald's Corporation", "TMO": "Thermo Fisher Scientific",
    "CSCO": "Cisco Systems", "ABT": "Abbott Laboratories", "NFLX": "Netflix Inc.",
    "ADBE": "Adobe Inc.", "AMD": "Advanced Micro Devices", "TXN": "Texas Instruments",
    "NEE": "NextEra Energy", "PM": "Philip Morris", "DHR": "Danaher Corporation",
    "QCOM": "Qualcomm Inc.", "UNP": "Union Pacific", "RTX": "RTX Corporation",
    "HON": "Honeywell International", "IBM": "IBM Corporation", "GE": "GE Aerospace",
    "SBUX": "Starbucks Corporation", "AMAT": "Applied Materials", "CAT": "Caterpillar Inc.",
    "INTU": "Intuit Inc.", "NOW": "ServiceNow Inc.", "AMGN": "Amgen Inc.",
    "PFE": "Pfizer Inc.", "GILD": "Gilead Sciences", "DE": "Deere & Company",
    "PYPL": "PayPal Holdings", "DIS": "Walt Disney Company", "BKNG": "Booking Holdings",
    "PANW": "Palo Alto Networks", "LRCX": "Lam Research", "ADI": "Analog Devices",
    "MELI": "MercadoLibre", "INTC": "Intel Corporation", "F": "Ford Motor Company",
    "GM": "General Motors", "T": "AT&T Inc.", "VZ": "Verizon Communications",
    "WFC": "Wells Fargo", "GS": "Goldman Sachs", "MS": "Morgan Stanley",
    "C": "Citigroup Inc. (Citi)", "AXP": "American Express", "SHOP": "Shopify Inc.",
    "UBER": "Uber Technologies", "SPOT": "Spotify Technology", "ABNB": "Airbnb Inc.",
    "DASH": "DoorDash Inc.", "COIN": "Coinbase Global", "PLTR": "Palantir Technologies",
    "SNAP": "Snap Inc.", "PINS": "Pinterest Inc.", "RBLX": "Roblox Corporation",
    "ORCL": "Oracle Corporation", "COP": "ConocoPhillips", "OXY": "Occidental Petroleum",
    "BA": "Boeing Company", "LMT": "Lockheed Martin", "NOC": "Northrop Grumman",
    "GD": "General Dynamics", "UPS": "United Parcel Service", "FDX": "FedEx Corporation",
    "DAL": "Delta Air Lines", "UAL": "United Airlines", "AAL": "American Airlines",
    "MAR": "Marriott International", "HLT": "Hilton Worldwide",
    "CVS": "CVS Health", "CI": "Cigna Group", "SYK": "Stryker Corporation",
    "MDT": "Medtronic plc", "BSX": "Boston Scientific", "ISRG": "Intuitive Surgical",
    "REGN": "Regeneron Pharmaceuticals", "VRTX": "Vertex Pharmaceuticals",
    "BIIB": "Biogen Inc.", "MRNA": "Moderna Inc.", "NVO": "Novo Nordisk",
    "BLK": "BlackRock Inc.", "GS": "Goldman Sachs", "SPGI": "S&P Global",
    "NEM": "Newmont Corporation", "FCX": "Freeport-McMoRan",
    # DAX Germany
    "ADS.DE": "Adidas AG", "ALV.DE": "Allianz SE", "BAS.DE": "BASF SE",
    "BAYN.DE": "Bayer AG", "BMW.DE": "BMW AG", "CBK.DE": "Commerzbank AG",
    "CON.DE": "Continental AG", "DTE.DE": "Deutsche Telekom AG",
    "EOAN.DE": "E.ON SE", "FRE.DE": "Fresenius SE", "IFX.DE": "Infineon Technologies",
    "MBG.DE": "Mercedes-Benz Group", "MRK.DE": "Merck KGaA", "MTX.DE": "MTU Aero Engines",
    "MUV2.DE": "Munich Re", "P911.DE": "Porsche AG", "RWE.DE": "RWE AG",
    "SAP.DE": "SAP SE", "SIE.DE": "Siemens AG", "VOW3.DE": "Volkswagen AG",
    "VNA.DE": "Vonovia SE", "ZAL.DE": "Zalando SE", "DBK.DE": "Deutsche Bank AG",
    "DHL.DE": "DHL Group", "ENR.DE": "Siemens Energy", "AIR.DE": "Airbus SE",
    "BEI.DE": "Beiersdorf AG", "SHL.DE": "Siemens Healthineers", "HEN3.DE": "Henkel AG",
    "1COV.DE": "Covestro AG", "DHER.DE": "Delivery Hero", "SY1.DE": "Symrise AG",
    # FTSE MIB Italy
    "A2A.MI": "A2A SpA", "AMP.MI": "Amplifon SpA", "AZM.MI": "Azimut Holding",
    "BAMI.MI": "Banco BPM", "BGN.MI": "Banca Generali", "BPE.MI": "BPER Banca",
    "BZU.MI": "Buzzi SpA", "CNHI.MI": "CNH Industrial", "ENEL.MI": "Enel SpA",
    "ENI.MI": "Eni SpA", "FHI.MI": "Ferrari NV", "G.MI": "Assicurazioni Generali",
    "HER.MI": "Hera SpA", "INW.MI": "Inwit SpA", "ISP.MI": "Intesa Sanpaolo",
    "ITALGAS.MI": "Italgas SpA", "LDO.MI": "Leonardo SpA", "MB.MI": "Mediobanca",
    "MONC.MI": "Moncler SpA", "NEXI.MI": "Nexi SpA", "PRY.MI": "Prysmian SpA",
    "PST.MI": "Poste Italiane", "REC.MI": "Recordati SpA", "RACE.MI": "Ferrari NV",
    "SPM.MI": "Saipem SpA", "SRG.MI": "Snam SpA", "STM.MI": "STMicroelectronics", "STM": "STMicroelectronics (NYSE)",
    "TEN.MI": "Tenaris SA", "TIT.MI": "Telecom Italia", "TRN.MI": "Terna SpA",
    "UCG.MI": "UniCredit SpA", "UNI.MI": "Unipol Gruppo", "STLAM.MI": "Stellantis NV",
    "PIRC.MI": "Pirelli & C.", "DIA.MI": "DiaSorin SpA", "FCT.MI": "Fineco Bank",
    "ERG.MI": "ERG SpA", "CPR.MI": "Cementir Holding",
    # Euro Stoxx
    "ASML.AS": "ASML Holding", "INGA.AS": "ING Groep", "PHIA.AS": "Philips NV",
    "AD.AS": "Ahold Delhaize", "HEIA.AS": "Heineken NV",
    "MC.PA": "LVMH Moët Hennessy", "OR.PA": "L'Oréal SA", "SAN.PA": "Sanofi SA",
    "BNP.PA": "BNP Paribas", "ACA.PA": "Crédit Agricole", "CS.PA": "AXA SA",
    "IBE.MC": "Iberdrola SA", "SAN.MC": "Banco Santander", "ITX.MC": "Inditex (Zara)",
    "NESN.SW": "Nestlé SA", "ROG.SW": "Roche Holding", "NOVN.SW": "Novartis AG",
    "NOVOB.CO": "Novo Nordisk",
}
NAME_TO_TICKER = {v.lower(): k for k, v in TICKER_DICT.items()}

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state init ───────────────────────────────────────────────────────
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = ""
if "last_data" not in st.session_state:
    st.session_state.last_data = None
if "last_period" not in st.session_state:
    st.session_state.last_period = "1y"
if "screener_df" not in st.session_state:
    st.session_state.screener_df = None
if "screener_market" not in st.session_state:
    st.session_state.screener_market = ""

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* { font-family: 'Inter', -apple-system, sans-serif; box-sizing: border-box; }
.stApp { background: #13151a !important; }
.main .block-container { padding: 2rem 2.5rem !important; max-width: 1300px !important; }
section[data-testid="stSidebar"] { background: #181b22 !important; border-right: 1px solid #252830 !important; }
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] div { color: #c4c8d4 !important; }
h1 { font-size: 1.8rem !important; font-weight: 700 !important; letter-spacing: -0.03em !important; color: #eef0f5 !important; }
h2 { font-size: 1.2rem !important; font-weight: 600 !important; color: #eef0f5 !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; color: #eef0f5 !important; }
p, .stMarkdown p { color: #9096a8 !important; line-height: 1.6 !important; }
.stCaption { color: #555a66 !important; font-size: 0.78rem !important; }
label { color: #9096a8 !important; }
[data-testid="metric-container"] { background: #1c1f27 !important; border: 1px solid #252830 !important; border-radius: 14px !important; padding: 18px 20px !important; }
[data-testid="metric-container"] label { color: #555a66 !important; font-size: 0.68rem !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; }
[data-testid="stMetricValue"] { color: #eef0f5 !important; font-size: 1.45rem !important; font-weight: 600 !important; letter-spacing: -0.02em !important; }
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; font-weight: 500 !important; }
[data-testid="stMetricDelta"] svg { display: none !important; }
.stTextInput input { background: #1c1f27 !important; border: 1px solid #252830 !important; border-radius: 10px !important; color: #eef0f5 !important; font-size: 0.95rem !important; padding: 10px 14px !important; }
.stTextInput input::placeholder { color: #3a3f4a !important; }
.stTextInput input:focus { border-color: #4d8eff !important; box-shadow: 0 0 0 3px rgba(77,142,255,0.15) !important; outline: none !important; }
[data-baseweb="select"] > div { background: #1c1f27 !important; border: 1px solid #252830 !important; border-radius: 10px !important; }
[data-baseweb="select"] span, [data-baseweb="select"] div, [data-baseweb="select"] input { color: #eef0f5 !important; }
[data-baseweb="popover"], [data-baseweb="menu"] { background: #1c1f27 !important; border: 1px solid #252830 !important; border-radius: 10px !important; }
[data-baseweb="option"] { background: #1c1f27 !important; color: #c4c8d4 !important; padding: 10px 14px !important; }
[data-baseweb="option"]:hover, [data-baseweb="option"][aria-selected="true"] { background: #24273100 !important; color: #eef0f5 !important; }
[data-testid="stSlider"] > div > div > div { background: #252830 !important; }
.stSlider p { color: #eef0f5 !important; font-weight: 600 !important; }
.stButton > button { background: #4d8eff !important; color: #ffffff !important; border: none !important; border-radius: 10px !important; font-size: 0.88rem !important; font-weight: 600 !important; padding: 11px 24px !important; transition: background 0.15s !important; width: 100% !important; }
.stButton > button:hover { background: #3a7aef !important; }
.stButton > button p, .stButton > button span, .stButton > button div { color: #ffffff !important; font-weight: 600 !important; }
.stTabs [data-baseweb="tab-list"] { background: #1c1f27 !important; border-radius: 10px !important; padding: 4px !important; border: 1px solid #252830 !important; gap: 2px !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; border-radius: 7px !important; padding: 7px 18px !important; font-size: 0.83rem !important; font-weight: 500 !important; color: #555a66 !important; }
.stTabs [aria-selected="true"] { background: #24272e !important; color: #eef0f5 !important; }
.stDataFrame { border-radius: 12px !important; overflow: hidden !important; }
[data-testid="stDataFrame"] { border: 1px solid #252830 !important; border-radius: 12px !important; }
[data-testid="stDataFrame"] th { background: #181b22 !important; color: #555a66 !important; font-size: 0.7rem !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.06em !important; padding: 10px 12px !important; border-bottom: 1px solid #252830 !important; }
[data-testid="stDataFrame"] td { background: #1c1f27 !important; color: #c4c8d4 !important; font-size: 0.84rem !important; padding: 9px 12px !important; border-bottom: 1px solid #202330 !important; }
.stProgress > div > div > div { background: #4d8eff !important; border-radius: 4px !important; }
.stProgress > div > div { background: #252830 !important; border-radius: 4px !important; }
.stAlert { border-radius: 10px !important; }
hr { border: none !important; border-top: 1px solid #252830 !important; margin: 1.5rem 0 !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #252830; border-radius: 3px; }
.stRadio label { color: #c4c8d4 !important; font-size: 0.88rem !important; font-weight: 400 !important; text-transform: none !important; letter-spacing: 0 !important; }
.stSpinner > div { border-top-color: #4d8eff !important; }
</style>
""", unsafe_allow_html=True)
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from modules.analyzer import get_stock_data
from modules.screener import run_screener, MARKET_GROUPS
from modules.sentiment import get_fear_greed, get_news_sentiment, get_macro_context, get_full_sentiment
import time

# ── Dizionario ticker → nome (per ricerca per nome) ───────────────────────────
TICKER_DICT = {
    "AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com Inc.", "GOOGL": "Alphabet Inc. (Google)", "META": "Meta Platforms (Facebook)",
    "TSLA": "Tesla Inc.", "BRK-B": "Berkshire Hathaway", "LLY": "Eli Lilly",
    "AVGO": "Broadcom Inc.", "JPM": "JPMorgan Chase", "UNH": "UnitedHealth Group",
    "XOM": "Exxon Mobil", "V": "Visa Inc.", "MA": "Mastercard", "PG": "Procter & Gamble",
    "JNJ": "Johnson & Johnson", "HD": "Home Depot", "MRK": "Merck & Co.",
    "ABBV": "AbbVie Inc.", "CVX": "Chevron Corporation", "COST": "Costco Wholesale",
    "PEP": "PepsiCo Inc.", "KO": "Coca-Cola Company", "WMT": "Walmart Inc.",
    "CRM": "Salesforce Inc.", "BAC": "Bank of America", "ACN": "Accenture",
    "MCD": "McDonald's Corporation", "TMO": "Thermo Fisher Scientific",
    "CSCO": "Cisco Systems", "ABT": "Abbott Laboratories", "NFLX": "Netflix Inc.",
    "ADBE": "Adobe Inc.", "AMD": "Advanced Micro Devices", "TXN": "Texas Instruments",
    "NEE": "NextEra Energy", "PM": "Philip Morris", "DHR": "Danaher Corporation",
    "QCOM": "Qualcomm Inc.", "UNP": "Union Pacific", "RTX": "RTX Corporation",
    "HON": "Honeywell International", "IBM": "IBM Corporation", "GE": "GE Aerospace",
    "SBUX": "Starbucks Corporation", "AMAT": "Applied Materials", "CAT": "Caterpillar Inc.",
    "INTU": "Intuit Inc.", "NOW": "ServiceNow Inc.", "AMGN": "Amgen Inc.",
    "PFE": "Pfizer Inc.", "GILD": "Gilead Sciences", "DE": "Deere & Company",
    "PYPL": "PayPal Holdings", "DIS": "Walt Disney Company", "BKNG": "Booking Holdings",
    "PANW": "Palo Alto Networks", "LRCX": "Lam Research", "ADI": "Analog Devices",
    "MELI": "MercadoLibre", "INTC": "Intel Corporation", "F": "Ford Motor Company",
    "GM": "General Motors", "T": "AT&T Inc.", "VZ": "Verizon Communications",
    "WFC": "Wells Fargo", "GS": "Goldman Sachs", "MS": "Morgan Stanley",
    "C": "Citigroup Inc. (Citi)", "AXP": "American Express", "SHOP": "Shopify Inc.",
    "UBER": "Uber Technologies", "SPOT": "Spotify Technology", "ABNB": "Airbnb Inc.",
    "DASH": "DoorDash Inc.", "COIN": "Coinbase Global", "PLTR": "Palantir Technologies",
    "SNAP": "Snap Inc.", "PINS": "Pinterest Inc.", "RBLX": "Roblox Corporation",
    "ORCL": "Oracle Corporation", "COP": "ConocoPhillips", "OXY": "Occidental Petroleum",
    "BA": "Boeing Company", "LMT": "Lockheed Martin", "NOC": "Northrop Grumman",
    "GD": "General Dynamics", "UPS": "United Parcel Service", "FDX": "FedEx Corporation",
    "DAL": "Delta Air Lines", "UAL": "United Airlines", "AAL": "American Airlines",
    "MAR": "Marriott International", "HLT": "Hilton Worldwide",
    "CVS": "CVS Health", "CI": "Cigna Group", "SYK": "Stryker Corporation",
    "MDT": "Medtronic plc", "BSX": "Boston Scientific", "ISRG": "Intuitive Surgical",
    "REGN": "Regeneron Pharmaceuticals", "VRTX": "Vertex Pharmaceuticals",
    "BIIB": "Biogen Inc.", "MRNA": "Moderna Inc.", "NVO": "Novo Nordisk",
    "BLK": "BlackRock Inc.", "GS": "Goldman Sachs", "SPGI": "S&P Global",
    "NEM": "Newmont Corporation", "FCX": "Freeport-McMoRan",
    # DAX Germany
    "ADS.DE": "Adidas AG", "ALV.DE": "Allianz SE", "BAS.DE": "BASF SE",
    "BAYN.DE": "Bayer AG", "BMW.DE": "BMW AG", "CBK.DE": "Commerzbank AG",
    "CON.DE": "Continental AG", "DTE.DE": "Deutsche Telekom AG",
    "EOAN.DE": "E.ON SE", "FRE.DE": "Fresenius SE", "IFX.DE": "Infineon Technologies",
    "MBG.DE": "Mercedes-Benz Group", "MRK.DE": "Merck KGaA", "MTX.DE": "MTU Aero Engines",
    "MUV2.DE": "Munich Re", "P911.DE": "Porsche AG", "RWE.DE": "RWE AG",
    "SAP.DE": "SAP SE", "SIE.DE": "Siemens AG", "VOW3.DE": "Volkswagen AG",
    "VNA.DE": "Vonovia SE", "ZAL.DE": "Zalando SE", "DBK.DE": "Deutsche Bank AG",
    "DHL.DE": "DHL Group", "ENR.DE": "Siemens Energy", "AIR.DE": "Airbus SE",
    "BEI.DE": "Beiersdorf AG", "SHL.DE": "Siemens Healthineers", "HEN3.DE": "Henkel AG",
    "1COV.DE": "Covestro AG", "DHER.DE": "Delivery Hero", "SY1.DE": "Symrise AG",
    # FTSE MIB Italy
    "A2A.MI": "A2A SpA", "AMP.MI": "Amplifon SpA", "AZM.MI": "Azimut Holding",
    "BAMI.MI": "Banco BPM", "BGN.MI": "Banca Generali", "BPE.MI": "BPER Banca",
    "BZU.MI": "Buzzi SpA", "CNHI.MI": "CNH Industrial", "ENEL.MI": "Enel SpA",
    "ENI.MI": "Eni SpA", "FHI.MI": "Ferrari NV", "G.MI": "Assicurazioni Generali",
    "HER.MI": "Hera SpA", "INW.MI": "Inwit SpA", "ISP.MI": "Intesa Sanpaolo",
    "ITALGAS.MI": "Italgas SpA", "LDO.MI": "Leonardo SpA", "MB.MI": "Mediobanca",
    "MONC.MI": "Moncler SpA", "NEXI.MI": "Nexi SpA", "PRY.MI": "Prysmian SpA",
    "PST.MI": "Poste Italiane", "REC.MI": "Recordati SpA", "RACE.MI": "Ferrari NV",
    "SPM.MI": "Saipem SpA", "SRG.MI": "Snam SpA", "STM.MI": "STMicroelectronics", "STM": "STMicroelectronics (NYSE)",
    "TEN.MI": "Tenaris SA", "TIT.MI": "Telecom Italia", "TRN.MI": "Terna SpA",
    "UCG.MI": "UniCredit SpA", "UNI.MI": "Unipol Gruppo", "STLAM.MI": "Stellantis NV",
    "PIRC.MI": "Pirelli & C.", "DIA.MI": "DiaSorin SpA", "FCT.MI": "Fineco Bank",
    "ERG.MI": "ERG SpA", "CPR.MI": "Cementir Holding",
    # Euro Stoxx
    "ASML.AS": "ASML Holding", "INGA.AS": "ING Groep", "PHIA.AS": "Philips NV",
    "AD.AS": "Ahold Delhaize", "HEIA.AS": "Heineken NV",
    "MC.PA": "LVMH Moët Hennessy", "OR.PA": "L'Oréal SA", "SAN.PA": "Sanofi SA",
    "BNP.PA": "BNP Paribas", "ACA.PA": "Crédit Agricole", "CS.PA": "AXA SA",
    "IBE.MC": "Iberdrola SA", "SAN.MC": "Banco Santander", "ITX.MC": "Inditex (Zara)",
    "NESN.SW": "Nestlé SA", "ROG.SW": "Roche Holding", "NOVN.SW": "Novartis AG",
    "NOVOB.CO": "Novo Nordisk",
}
NAME_TO_TICKER = {v.lower(): k for k, v in TICKER_DICT.items()}

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state init ───────────────────────────────────────────────────────
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = ""
if "last_data" not in st.session_state:
    st.session_state.last_data = None
if "last_period" not in st.session_state:
    st.session_state.last_period = "1y"
if "screener_df" not in st.session_state:
    st.session_state.screener_df = None
if "screener_market" not in st.session_state:
    st.session_state.screener_market = ""

# ── Custom CSS — Premium Finance Dark ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; box-sizing: border-box; }

/* ── Background ── */
.stApp, .stApp > div { background: #111318 !important; }
.main .block-container { padding: 2rem 2.5rem !important; max-width: 1200px !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: #111111 !important; border-right: 1px solid #2a2d35 !important; }
section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
section[data-testid="stSidebar"] .stCaption { color: #555 !important; font-size: 0.75rem !important; }

/* ── Typography ── */
h1 { font-size: 2rem !important; font-weight: 700 !important; letter-spacing: -0.04em !important; color: #f0f2f5 !important; margin-bottom: 0.25rem !important; }
h2 { font-size: 1.25rem !important; font-weight: 600 !important; letter-spacing: -0.02em !important; color: #f0f2f5 !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; color: #f0f2f5 !important; }
p { color: #9a9da6 !important; line-height: 1.6 !important; }
.stCaption { color: #555 !important; font-size: 0.78rem !important; }
label { color: #9a9da6 !important; font-size: 0.8rem !important; font-weight: 500 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #1e2128 !important;
    border: 1px solid #2a2d35 !important;
    border-radius: 14px !important;
    padding: 18px 20px !important;
    transition: border-color 0.2s !important;
}
[data-testid="metric-container"]:hover { border-color: #2a2a2a !important; }
[data-testid="metric-container"] label {
    color: #555 !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
[data-testid="stMetricValue"] {
    color: #f0f2f5 !important;
    font-size: 1.5rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.025em !important;
}
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; font-weight: 500 !important; }
[data-testid="stMetricDelta"] svg { display: none !important; }

/* ── Input ── */
.stTextInput input {
    background: #1e2128 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 12px !important;
    color: #f0f2f5 !important;
    font-size: 1rem !important;
    padding: 12px 16px !important;
    caret-color: #4c8eff !important;
}
.stTextInput input::placeholder { color: #3a3a3a !important; }
.stTextInput input:focus { border-color: #4c8eff !important; outline: none !important; box-shadow: 0 0 0 3px rgba(10,132,255,0.12) !important; }

/* ── Selectbox ── */
[data-baseweb="select"] > div {
    background: #1e2128 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 12px !important;
    color: #f0f2f5 !important;
}
[data-baseweb="select"] span, [data-baseweb="select"] div { color: #f0f2f5 !important; }
[data-baseweb="popover"] { background: #1a1d24 !important; border: 1px solid #2a2a2a !important; border-radius: 12px !important; }
[data-baseweb="menu"] { background: #1a1d24 !important; }
[data-baseweb="option"] { background: #1a1d24 !important; color: #f0f2f5 !important; }
[data-baseweb="option"]:hover { background: #262930 !important; }

/* ── Slider ── */
[data-testid="stSlider"] > div > div > div { background: #2a2d35 !important; }
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] { background: #4c8eff !important; border: 2px solid #4c8eff !important; }
[data-testid="stSlider"] div[data-testid="stTickBarMin"],
[data-testid="stSlider"] div[data-testid="stTickBarMax"] { color: #555 !important; }
.stSlider p { color: #f0f2f5 !important; font-weight: 600 !important; }

/* ── Button ── */
.stButton > button {
    background: #4c8eff !important;
    color: #f0f2f5 !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    padding: 12px 28px !important;
    letter-spacing: -0.01em !important;
    transition: background 0.15s, transform 0.1s !important;
    width: 100% !important;
}
.stButton > button:hover { background: #0071e3 !important; transform: scale(0.995) !important; }
.stButton > button:active { transform: scale(0.98) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #1e2128 !important;
    border-radius: 12px !important;
    padding: 4px !important;
    border: 1px solid #2a2d35 !important;
    gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 9px !important;
    padding: 8px 20px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    color: #555 !important;
    border: none !important;
    transition: all 0.15s !important;
}
.stTabs [aria-selected="true"] {
    background: #262930 !important;
    color: #f0f2f5 !important;
}

/* ── Progress / spinner ── */
.stProgress > div > div > div { background: #4c8eff !important; }
.stProgress > div > div { background: #2a2d35 !important; border-radius: 4px !important; }

/* ── Info / success / warning / error ── */
.stAlert { border-radius: 12px !important; border: none !important; }
[data-testid="stNotification"] { border-radius: 12px !important; }
div[data-testid="stMarkdownContainer"] p { color: #9a9da6 !important; }

/* ── Dataframe ── */
.stDataFrame { border-radius: 14px !important; overflow: hidden !important; border: 1px solid #2a2d35 !important; }
[data-testid="stDataFrame"] th { background: #1e2128 !important; color: #555 !important; font-size: 0.72rem !important; text-transform: uppercase !important; letter-spacing: 0.06em !important; }
[data-testid="stDataFrame"] td { background: #0d0d0d !important; color: #e0e0e0 !important; font-size: 0.85rem !important; }

/* ── Divider ── */
hr { border: none !important; border-top: 1px solid #2a2d35 !important; margin: 1.5rem 0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3a3a3a; }

/* ── Radio ── */
.stRadio label { color: #e0e0e0 !important; font-size: 0.9rem !important; font-weight: 400 !important; text-transform: none !important; letter-spacing: 0 !important; }
[data-testid="stRadio"] > div > label { padding: 8px 12px !important; border-radius: 8px !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #4c8eff !important; }
</style>
""", unsafe_allow_html=True)
# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='padding:6px 0 12px'><div style='font-size:1rem;font-weight:700;color:#eef0f5;letter-spacing:-0.02em'>Stock Analyzer</div><div style='font-size:0.7rem;color:#444;margin-top:2px;letter-spacing:0.04em'>Yahoo Finance · 15min delay</div></div>", unsafe_allow_html=True)
    st.divider()

    page = st.radio(
        "Sezione",
        ["🔍 Analisi Titolo", "🎯 Screener Scontati", "🌡️ Sentiment Mercato"],
        label_visibility="collapsed",
    )

    st.divider()

    # Macro context in sidebar
    macro = get_macro_context()
    if macro["vix"]:
        st.metric("VIX", macro["vix"], help="Indice di volatilità. >25 = mercato nervoso")
        st.caption(macro["vix_label"])

    fg = get_fear_greed()
    if fg["score"]:
        st.metric("Fear & Greed", f"{fg['score']} — {fg['rating']}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — ANALISI TITOLO
# ══════════════════════════════════════════════════════════════════════════════
if page == "🔍 Analisi Titolo":
    st.title("🔍 Analisi Titolo")
    st.caption("Inserisci un ticker per ottenere analisi tecnica, fondamentale, entry/exit price e sentiment.")

    col_input, col_period = st.columns([3, 1])
    with col_input:
        search_query = st.text_input(
            "Cerca per nome o ticker",
            placeholder="es. STMicroelectronics · Apple · Eni · Ferrari · NVDA · SAP",
            label_visibility="collapsed",
            key="search_input",
        ).strip()

        ticker_input = ""
        if search_query and len(search_query) >= 2:
            # 1. Prima cerca nel dizionario locale (veloce)
            q = search_query.lower()
            local = []
            for t, n in TICKER_DICT.items():
                if q == t.lower():
                    local.insert(0, f"{t} — {n}")  # exact match in cima
                elif q in n.lower() or q in t.lower():
                    local.append(f"{t} — {n}")

            # 2. Poi cerca su Yahoo Finance (copertura totale)
            yahoo_results = []
            try:
                import requests as req
                url = f"https://query2.finance.yahoo.com/v1/finance/search?q={search_query}&quotesCount=8&newsCount=0&listsCount=0"
                headers = {"User-Agent": "Mozilla/5.0"}
                r = req.get(url, headers=headers, timeout=4)
                if r.status_code == 200:
                    data_yf = r.json()
                    for item in data_yf.get("quotes", []):
                        sym = item.get("symbol", "")
                        name_yf = item.get("longname") or item.get("shortname") or ""
                        exch = item.get("exchange", "")
                        typ = item.get("quoteType", "")
                        if sym and name_yf and typ in ["EQUITY", "ETF"]:
                            entry = f"{sym} — {name_yf} [{exch}]"
                            # Evita duplicati con dizionario locale
                            if not any(sym == loc.split(" — ")[0] for loc in local):
                                yahoo_results.append(entry)
            except Exception:
                pass

            # Merge: locali prima, poi Yahoo
            suggestions = local[:5] + yahoo_results[:6]

            if not suggestions:
                # Nessun risultato → prova come ticker diretto
                ticker_input = search_query.upper().strip()
                st.caption(f"🔍 Ticker diretto: **{ticker_input}** — provo a cercarlo su Yahoo Finance")
            elif len(suggestions) == 1:
                ticker_input = suggestions[0].split(" — ")[0].split(" [")[0].strip()
                st.caption(f"✅ {suggestions[0]}")
            else:
                choice = st.selectbox(
                    "Seleziona il titolo",
                    suggestions,
                    label_visibility="collapsed",
                    key="ticker_select",
                )
                ticker_input = choice.split(" — ")[0].split(" [")[0].strip()

    with col_period:
        period_options = ["6mo", "1y", "2y", "5y"]
        default_idx = period_options.index(st.session_state.last_period) if st.session_state.last_period in period_options else 1
        period = st.selectbox("Periodo", period_options, index=default_idx, label_visibility="collapsed")

    # Fetch solo se ticker è diverso dall'ultimo o dati assenti
    if ticker_input:
        if ticker_input != st.session_state.last_ticker or st.session_state.last_data is None:
            with st.spinner(f"Carico dati per {ticker_input}..."):
                data = get_stock_data(ticker_input, period=period)
            st.session_state.last_data = data
            st.session_state.last_ticker = ticker_input
            st.session_state.last_period = period
        else:
            data = st.session_state.last_data
    elif st.session_state.last_data is not None:
        # Mostra ultima analisi quando si torna sulla pagina
        data = st.session_state.last_data
        ticker_input = st.session_state.last_ticker
        st.info(f"📌 Ultima analisi: **{st.session_state.last_ticker}** — cerca un nuovo titolo per aggiornare.")
    else:
        data = None

    if data is not None:
        if "error" in data:
            st.error(f"❌ {data['error']}")
            st.info("💡 Suggerimento: prova il ticker esatto come appare su Yahoo Finance. Esempi: **STM** (NYSE), **ENI.MI** (Milano), **SAP.DE** (Francoforte), **MC.PA** (Parigi)")
        else:
            # ── Header ──
            st.subheader(f"{data['name']} ({data['ticker']})")
            st.caption(f"{data['sector']} · {data['industry']}")

            # ── KPI row ──
            k1, k2, k3, k4, k5 = st.columns(5)
            def fmt(v, cur=""): return f"{v:,.2f} {cur}".strip() if v else "N/A"
            k1.metric("💰 Prezzo", fmt(data['current_price'], data['currency']))
            k2.metric("🎯 Entry suggerito", fmt(data['entry_price'], data['currency']))
            k3.metric("🚀 Target price", fmt(data['target_price'], data['currency']),
                      delta=f"+{data['upside_pct']}%" if data['upside_pct'] else None)
            k4.metric("🛡️ Stop Loss", fmt(data['stop_loss'], data['currency']))
            k5.metric("Fair Value (DCF)", fmt(data['fair_value'], data['currency']) if data['fair_value'] else "N/A")

            # ── Stima tempo + guadagno ──
            if data.get("upside_pct") and data["upside_pct"] > 0:
                tc = data.get("time_category", "N/A")
                tc_color = "#4c8eff" if "Breve" in tc else ("#30d158" if "Medio" in tc and "Lungo" not in tc else ("#ff9f0a" if "Lungo" in tc else ("#ff8c42" if "Molto" in tc else "#636366")))
                ann = data.get("annualized_return")
                net = data.get("upside_net_pct")
                st.markdown(f"""
<div style='background:#1e2128;border-radius:10px;padding:16px;margin:8px 0;display:flex;gap:32px;flex-wrap:wrap;border:1px solid #252830'>
    <div>
        <div style='color:#6b6e77;font-size:0.78rem'>⏱ Tempo stimato al target</div>
        <div style='color:{tc_color};font-weight:700;font-size:1.05rem'>{data.get("time_label","N/A")}</div>
    </div>
    <div>
        <div style='color:#6b6e77;font-size:0.78rem'>📈 Guadagno lordo</div>
        <div style='color:#30d158;font-weight:700;font-size:1.05rem'>+{data['upside_pct']}%</div>
    </div>
    <div>
        <div style='color:#6b6e77;font-size:0.78rem'>💶 Guadagno netto (−26% tasse IT)</div>
        <div style='color:#30d158;font-weight:700;font-size:1.05rem'>+{net}%</div>
    </div>
    {'<div><div style="color:#6b6e77;font-size:0.78rem">📊 Rendimento annualizzato</div><div style="color:#bf5af2;font-weight:700;font-size:1.05rem">+' + str(ann) + '% /anno</div></div>' if ann else ''}
</div>
""", unsafe_allow_html=True)

            # ── Signal ──
            score = data["score"]
            signal_color = "#30d158" if "BUY" in data["signal"] else ("#ff9f0a" if "HOLD" in data["signal"] else "#ff453a")
            st.markdown(f"""
            <div style='background:#1e2128;border-radius:14px;padding:22px 24px;margin:14px 0;border:1px solid {signal_color}44'>
                <span style='font-size:1.6rem;font-weight:800;color:{signal_color}'>{data['signal']}</span>
                <span style='color:#6b6e77;margin-left:20px'>Score composito: <b style='color:#f5f5f7'>{score}/100</b></span>
                <div style='background:#2c2c2e;border-radius:4px;height:8px;margin-top:10px'>
                    <div style='background:{signal_color};width:{score}%;height:5px;border-radius:4px'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Tabs ──
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Grafico", "📐 Tecnica", "💼 Fondamentali", "📰 News"])

            with tab1:
                hist = data["hist"]
                fig = make_subplots(
                    rows=3, cols=1,
                    shared_xaxes=True,
                    row_heights=[0.6, 0.2, 0.2],
                    vertical_spacing=0.03,
                )

                # Candlestick
                fig.add_trace(go.Candlestick(
                    x=hist.index, open=hist["Open"], high=hist["High"],
                    low=hist["Low"], close=hist["Close"], name="Prezzo",
                    increasing_line_color="#30d158", decreasing_line_color="#ff453a",
                ), row=1, col=1)

                # Moving averages
                for ma, color, label in [("MA20", "#4c8eff", "MA20"), ("MA50", "#ff9f0a", "MA50"), ("MA200", "#ff453a", "MA200")]:
                    if ma in hist.columns:
                        fig.add_trace(go.Scatter(x=hist.index, y=hist[ma], name=label,
                                                 line=dict(color=color, width=1.2)), row=1, col=1)

                # Bollinger
                fig.add_trace(go.Scatter(x=hist.index, y=hist["BB_upper"], name="BB Upper",
                                         line=dict(color="#636366", width=0.8, dash="dot")), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist["BB_lower"], name="BB Lower",
                                         line=dict(color="#636366", width=0.8, dash="dot"),
                                         fill="tonexty", fillcolor="rgba(136,146,164,0.05)"), row=1, col=1)

                # Volume
                colors = ["#30d158" if c >= o else "#ff453a"
                          for c, o in zip(hist["Close"], hist["Open"])]
                fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], name="Volume",
                                     marker_color=colors, opacity=0.6), row=2, col=1)

                # RSI
                fig.add_trace(go.Scatter(x=hist.index, y=hist["RSI"], name="RSI",
                                         line=dict(color="#bf5af2", width=1.5)), row=3, col=1)
                fig.add_hline(y=70, line_dash="dot", line_color="#ff453a", row=3, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="#30d158", row=3, col=1)

                fig.update_layout(
                    height=700, template="plotly_dark",
                    paper_bgcolor="#000000", plot_bgcolor="#000000",
                    xaxis_rangeslider_visible=False,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("RSI (14)", data["rsi"],
                              delta="Oversold 🟢" if data["rsi"] < 35 else ("Overbought 🔴" if data["rsi"] > 70 else "Neutro"))
                    st.metric("MACD", data["macd"],
                              delta="↑ Bullish" if data["macd"] > data["macd_signal"] else "↓ Bearish")
                with c2:
                    st.metric("MA 20", f"{data['ma20']}" if data['ma20'] else "N/A")
                    st.metric("MA 50", f"{data['ma50']}" if data['ma50'] else "N/A")
                    st.metric("MA 200", f"{data['ma200']}" if data['ma200'] else "N/A")
                with c3:
                    st.metric("Supporto (3m)", data["support"])
                    st.metric("Resistenza (3m)", data["resistance"])
                    st.metric("BB Upper / Lower", f"{data['bb_upper']} / {data['bb_lower']}")

            with tab3:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("P/E Ratio", data["pe"] if data["pe"] else "N/A")
                    st.metric("P/B Ratio", data["pb"] if data["pb"] else "N/A")
                    st.metric("EV/EBITDA", data["ev_ebitda"] if data["ev_ebitda"] else "N/A")
                with c2:
                    st.metric("ROE", f"{data['roe']}%" if data["roe"] else "N/A")
                    st.metric("Margine Netto", f"{data['profit_margin']}%" if data["profit_margin"] else "N/A")
                    st.metric("Crescita Ricavi", f"{data['revenue_growth']}%" if data["revenue_growth"] else "N/A")
                with c3:
                    st.metric("Debt/Equity", data["debt_equity"] if data["debt_equity"] else "N/A")
                    st.metric("Dividend Yield", f"{data['dividend_yield']}%" if data["dividend_yield"] else "N/A")
                    st.metric("Beta", data["beta"] if data["beta"] else "N/A")
                    mc = data["market_cap"]
                    if mc:
                        if mc > 1e12: mc_str = f"${mc/1e12:.1f}T"
                        elif mc > 1e9: mc_str = f"${mc/1e9:.1f}B"
                        else: mc_str = f"${mc/1e6:.0f}M"
                        st.metric("Market Cap", mc_str)

            with tab4:
                with st.spinner("Carico sentiment completo..."):
                    sent = get_full_sentiment(ticker_input, data.get("name", ""))

                # ── Score globale ──
                sc = sent["score"]
                sc_color = "#30d158" if sc >= 65 else ("#ff9f0a" if sc >= 45 else "#ff453a")
                st.markdown(f"""
<div style='background:#1e2128;border-radius:12px;padding:20px;border:1px solid {sc_color};margin-bottom:20px'>
    <span style='font-size:1.4rem;font-weight:800;color:{sc_color}'>{sent["overall"]}</span>
    <span style='color:#6b6e77;margin-left:16px'>Score sentiment: <b style='color:#f5f5f7'>{sc}/100</b></span>
    <div style='background:#2c2c2e;border-radius:4px;height:8px;margin-top:10px'>
        <div style='background:{sc_color};width:{sc}%;height:5px;border-radius:4px'></div>
    </div>
</div>""", unsafe_allow_html=True)

                s1, s2 = st.columns(2)

                with s1:
                    # Analyst consensus
                    an = sent["analyst"]
                    st.markdown("**📊 Consensus Analisti**")
                    st.markdown(f"{an.get('consensus_label','N/A')} — {an.get('n_analysts',0)} analisti")
                    if an.get("target_mean"):
                        st.markdown(f"Target medio: **{an['target_mean']}** | Range: {an.get('target_low','?')} – {an.get('target_high','?')}")
                        if an.get("upside"):
                            up_col = "#30d158" if an["upside"] > 0 else "#ff453a"
                            st.markdown(f"Upside da consensus: <span style='color:{up_col}'><b>{an['upside']}%</b></span>", unsafe_allow_html=True)
                    st.divider()

                    # Short interest
                    sh = sent["short"]
                    st.markdown("**🩳 Short Interest**")
                    if sh.get("short_pct"):
                        sh_col = "#ff453a" if sh["short_pct"] > 15 else ("#ff9f0a" if sh["short_pct"] > 8 else "#30d158")
                        st.markdown(f"<span style='color:{sh_col}'>{sh['short_pct']}% delle azioni shortate</span>", unsafe_allow_html=True)
                        if sh.get("short_ratio"): st.markdown(f"Days to cover: {sh['short_ratio']} giorni")
                        if sh.get("change_pct"):
                            ch_col = "#ff453a" if sh["change_pct"] > 0 else "#30d158"
                            st.markdown(f"Variazione mese: <span style='color:{ch_col}'>{sh['change_pct']:+.1f}%</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("N/A")
                    st.markdown(sh.get("label",""))
                    st.divider()

                    # Options
                    op = sent["options"]
                    st.markdown("**⚙️ Options Put/Call Ratio**")
                    st.markdown(op.get("label", "N/A"))
                    if op.get("calls_volume"):
                        st.markdown(f"Call vol: {op['calls_volume']:,} · Put vol: {op['puts_volume']:,}")

                with s2:
                    # Insider trading
                    ins = sent["insider"]
                    st.markdown("**👔 Insider Trading (ultimi movimenti)**")
                    st.markdown(ins.get("label","N/A"))
                    if ins.get("transactions"):
                        for tx in ins["transactions"][:4]:
                            v = f"${tx['value']:,}" if tx.get("value") else ""
                            st.markdown(f"<small>{tx['direction']} · {tx['name']} · {tx['date']} {v}</small>", unsafe_allow_html=True)
                    st.divider()

                    # Earnings surprise
                    ea = sent["earnings"]
                    st.markdown("**📈 Earnings Surprise (ultimi 4 trimestri)**")
                    st.markdown(ea.get("label","N/A"))
                    if ea.get("surprises"):
                        cols_ea = st.columns(len(ea["surprises"]))
                        for i, s in enumerate(ea["surprises"]):
                            c = "#30d158" if s > 0 else "#ff453a"
                            cols_ea[i].markdown(f"<div style='text-align:center;color:{c}'><b>{s:+.1f}%</b><br><small>Q{i+1}</small></div>", unsafe_allow_html=True)
                    if ea.get("next_earnings"): st.markdown(f"Prossimi earnings: **{ea['next_earnings']}**")
                    st.divider()

                    # Reddit
                    rd = sent["reddit"]
                    st.markdown("**💬 Reddit Mentions**")
                    st.markdown(rd.get("label","N/A"))
                    if rd.get("posts"):
                        for p in rd["posts"][:3]:
                            rc = "#30d158" if p["sentiment"] > 0.05 else ("#ff453a" if p["sentiment"] < -0.05 else "#636366")
                            st.markdown(f"<span style='color:{rc}'>●</span> <small>[{p['title']}]({p['url']}) r/{p['subreddit']}</small>", unsafe_allow_html=True)

                st.divider()
                # News
                st.markdown("**📰 News recenti**")
                news = sent["news"]
                for art in news.get("articles", []):
                    nc = "#30d158" if art["score"] > 0.05 else ("#ff453a" if art["score"] < -0.05 else "#636366")
                    st.markdown(f"<span style='color:{nc}'>●</span> [{art['title']}]({art['url']}) · *{art['publisher']}*", unsafe_allow_html=True)

            # ── AI Summary ──────────────────────────────────────────────────
            st.divider()
            st.subheader("🤖 Analisi AI — Compra o No?")
            sentiment_for_ai = sent if "sent" in dir() else get_news_sentiment(ticker_input)

            if st.button("Genera analisi AI", type="primary"):
                with st.spinner("Claude sta analizzando il titolo..."):
                    prompt = f"""Sei un analista finanziario esperto. Analizza {data['name']} ({data['ticker']}) e dai un giudizio chiaro su se acquistarlo o no.

Dati:
- Prezzo: {data['current_price']} {data['currency']} | Segnale: {data['signal']} (score: {data['score']}/100)
- Entry: {data['entry_price']} | Target: {data['target_price']} | Stop Loss: {data['stop_loss']} | Upside: {data['upside_pct']}%
- Fair Value DCF: {data['fair_value']}
- RSI: {data['rsi']} | MACD: {data['macd']} vs Signal: {data['macd_signal']}
- P/E: {data['pe']} | P/B: {data['pb']} | EV/EBITDA: {data['ev_ebitda']}
- ROE: {data['roe']}% | Margine netto: {data['profit_margin']}% | Crescita ricavi: {data['revenue_growth']}%
- Debt/Equity: {data['debt_equity']} | Beta: {data['beta']}
- Settore: {data['sector']} — {data['industry']}
- Sentiment news: {sentiment_for_ai.get('news', {}).get('label', 'N/A')}
- Consensus analisti: {sentiment_for_ai.get('analyst', {}).get('consensus_label', 'N/A')} | Target medio: {sentiment_for_ai.get('analyst', {}).get('target_mean', 'N/A')}
- Short interest: {sentiment_for_ai.get('short', {}).get('short_pct', 'N/A')}%
- Insider: {sentiment_for_ai.get('insider', {}).get('label', 'N/A')}
- Earnings surprise medio: {sentiment_for_ai.get('earnings', {}).get('avg_surprise', 'N/A')}%
- Options put/call: {sentiment_for_ai.get('options', {}).get('put_call_ratio', 'N/A')}
- Reddit: {sentiment_for_ai.get('reddit', {}).get('label', 'N/A')}

Scrivi in italiano un'analisi di 150-200 parole strutturata cosi:
1. **Fondamentali**: commenta multipli di valutazione e salute finanziaria
2. **Tecnica**: commenta RSI, MACD, posizione rispetto alle medie mobili
3. **Sentiment**: commenta il sentiment delle notizie recenti
4. **Verdetto**: BUY / HOLD / AVOID con motivazione e livelli entry/target consigliati

Sii diretto e pratico."""

                    try:
                        import requests as req
                        groq_key = st.secrets.get("GROQ_API_KEY", "")
                        if not groq_key:
                            st.error("GROQ_API_KEY non trovata. Aggiungila in Streamlit Secrets.")
                            st.stop()
                        response = req.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {groq_key}"
                            },
                            json={
                                "model": "llama-3.3-70b-versatile",
                                "max_tokens": 1000,
                                "messages": [{"role": "user", "content": prompt}]
                            },
                            timeout=30
                        )
                        result = response.json()
                        ai_text = result["choices"][0]["message"]["content"]
                        signal_color = "#30d158" if "BUY" in data["signal"] else ("#ff9f0a" if "HOLD" in data["signal"] else "#ff453a")
                        st.markdown(f"""
<div style='background:#1e2128;border-radius:12px;padding:24px;border:1px solid {signal_color}44;margin-top:8px;color:#f5f5f7;line-height:1.7'>
{ai_text.replace(chr(10), '<br>')}
</div>
""", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Errore API: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — SCREENER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Screener Scontati":
    st.title("🎯 Screener — Azioni Sottovalutate")
    st.caption("Scansiona i mercati disponibili su Trade Republic e trova le opportunità migliori.")

    col1, col2, col3 = st.columns(3)
    with col1:
        market = st.selectbox("Mercato", list(MARKET_GROUPS.keys()))
    with col2:
        min_score = st.slider("Score minimo", 50, 85, 62)
    with col3:
        max_results = st.slider("Max risultati", 5, 30, 15)

    if st.button("🚀 Avvia Screener", type="primary", use_container_width=True):
        tickers = MARKET_GROUPS[market]
        st.info(f"Analisi di {len(tickers)} titoli in corso — potrebbe richiedere 1-3 minuti...")
        df = run_screener(tickers, min_score=min_score, max_results=max_results)
        st.session_state.screener_df = df
        st.session_state.screener_market = market

    # Restore cached screener results
    df = st.session_state.screener_df
    if df is None:
        df_placeholder = True
    else:
        df_placeholder = False
    if not df_placeholder:

        if df is not None and not df.empty:
            pass
        if df is None or df.empty:
            if st.session_state.screener_df is None:
                st.info("Configura i filtri e clicca Avvia Screener.")
            else:
                st.warning("Nessun titolo trovato con i criteri selezionati. Prova ad abbassare lo score minimo.")
        else:
            def r(v, d=2): return round(v, d) if isinstance(v, (int, float)) and v == v else None
            def fmt(v, suffix=""): return f"{r(v):,.2f}{suffix}" if r(v) is not None else "—"

            n = len(df)
            st.markdown(f"""
<div style='display:flex;align-items:center;gap:12px;margin-bottom:20px'>
    <div style='background:#1c1f27;border:1px solid #252830;border-radius:10px;padding:12px 20px;display:flex;align-items:center;gap:10px'>
        <div style='width:8px;height:8px;border-radius:50%;background:#34c759'></div>
        <span style='color:#eef0f5;font-weight:600;font-size:1rem'>{n} titoli trovati</span>
        <span style='color:#555a66;font-size:0.82rem'>score ≥ {min_score}</span>
    </div>
</div>""", unsafe_allow_html=True)

            for _, row in df.iterrows():
                sig = str(row.get("Segnale", ""))
                score_val = r(row.get("Score", 0), 0) or 0
                sig_color = "#34c759" if "BUY" in sig else ("#ff9f0a" if "HOLD" in sig else "#ff453a")
                sig_bg = "rgba(52,199,89,0.08)" if "BUY" in sig else ("rgba(255,159,10,0.08)" if "HOLD" in sig else "rgba(255,69,58,0.08)")
                upside = r(row.get("Upside % lordo"), 1)
                upside_net = r(row.get("Upside % netto"), 1)
                tempo = str(row.get("Tempo stimato", "—")).replace("🔵","").replace("🟢","").replace("🟡","").replace("🟠","").replace("🔴","").strip()
                ann = r(row.get("Rend. annualizzato"), 1)
                pe = r(row.get("P/E"), 1)
                pb = r(row.get("P/B"), 2)
                rsi = r(row.get("RSI"), 1)
                valuta = row.get("Valuta", "")
                prezzo = r(row.get("Prezzo"), 2)
                entry = r(row.get("Entry"), 2)
                target = r(row.get("Target"), 2)
                stop = r(row.get("Stop Loss"), 2)
                nome = str(row.get("Nome", row.get("Ticker", "")))[:35]
                settore = str(row.get("Settore", "—"))
                ticker = str(row.get("Ticker", ""))

                # Summary card
                st.markdown(f"""
<div style='background:#1c1f27;border:1px solid #252830;border-radius:16px;padding:18px 22px;margin-bottom:10px'>
    <div style='display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px'>

        <div style='display:flex;align-items:center;gap:14px;min-width:200px'>
            <div style='background:{sig_bg};border:1px solid {sig_color}44;border-radius:10px;padding:8px 14px;text-align:center;min-width:60px'>
                <div style='font-size:1.15rem;font-weight:700;color:{sig_color};letter-spacing:-0.02em'>{score_val}</div>
                <div style='font-size:0.6rem;color:{sig_color};font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-top:1px'>score</div>
            </div>
            <div>
                <div style='font-size:1rem;font-weight:700;color:#eef0f5;letter-spacing:-0.01em'>{ticker}</div>
                <div style='font-size:0.78rem;color:#9096a8;margin-top:2px'>{nome}</div>
                <div style='font-size:0.72rem;color:#555a66;margin-top:2px'>{settore}</div>
            </div>
        </div>

        <div style='display:flex;gap:8px;flex-wrap:wrap;align-items:center'>
            <div style='background:#13151a;border-radius:8px;padding:8px 14px;text-align:center;min-width:80px'>
                <div style='font-size:0.65rem;color:#555a66;font-weight:600;text-transform:uppercase;letter-spacing:0.06em'>Prezzo</div>
                <div style='font-size:0.95rem;font-weight:600;color:#eef0f5;margin-top:3px'>{prezzo} {valuta}</div>
            </div>
            <div style='background:#13151a;border-radius:8px;padding:8px 14px;text-align:center;min-width:80px'>
                <div style='font-size:0.65rem;color:#555a66;font-weight:600;text-transform:uppercase;letter-spacing:0.06em'>Target</div>
                <div style='font-size:0.95rem;font-weight:600;color:#eef0f5;margin-top:3px'>{target} {valuta}</div>
            </div>
            <div style='background:#13151a;border-radius:8px;padding:8px 14px;text-align:center;min-width:80px'>
                <div style='font-size:0.65rem;color:#555a66;font-weight:600;text-transform:uppercase;letter-spacing:0.06em'>Stop Loss</div>
                <div style='font-size:0.95rem;font-weight:600;color:#ff453a;margin-top:3px'>{stop} {valuta}</div>
            </div>
            <div style='background:{sig_bg};border-radius:8px;padding:8px 14px;text-align:center;min-width:80px'>
                <div style='font-size:0.65rem;color:#555a66;font-weight:600;text-transform:uppercase;letter-spacing:0.06em'>Upside lordo</div>
                <div style='font-size:0.95rem;font-weight:700;color:{sig_color};margin-top:3px'>+{upside}%</div>
            </div>
            {f'<div style="background:#13151a;border-radius:8px;padding:8px 14px;text-align:center;min-width:80px"><div style="font-size:0.65rem;color:#555a66;font-weight:600;text-transform:uppercase;letter-spacing:0.06em">Netto IT</div><div style="font-size:0.95rem;font-weight:600;color:#34c759;margin-top:3px">+{upside_net}%</div></div>' if upside_net else ''}
            {f'<div style="background:#13151a;border-radius:8px;padding:8px 14px;text-align:center;min-width:90px"><div style="font-size:0.65rem;color:#555a66;font-weight:600;text-transform:uppercase;letter-spacing:0.06em">Rend. annuo</div><div style="font-size:0.95rem;font-weight:600;color:#bf5af2;margin-top:3px">+{ann}%</div></div>' if ann else ''}
        </div>

        <div style='font-size:0.78rem;color:#555a66;align-self:center;white-space:nowrap'>⏱ {tempo}</div>
    </div>
</div>""", unsafe_allow_html=True)

                # Expand per dettagli
                with st.expander(f"📊 Dettagli completi — {ticker}"):
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric("Entry", f"{entry} {valuta}")
                    d2.metric("RSI", f"{rsi}" if rsi else "—")
                    d3.metric("P/E", f"{pe}" if pe else "—")
                    d4.metric("P/B", f"{pb}" if pb else "—")
                    st.markdown(f"**Segnale:** {sig} &nbsp;|&nbsp; **Score:** {score_val}/100 &nbsp;|&nbsp; **Settore:** {settore}", unsafe_allow_html=True)
                    if st.button(f"🔍 Analizza {ticker} in dettaglio", key=f"btn_{ticker}"):
                        st.session_state.last_ticker = ticker
                        st.session_state.last_data = None
                        st.rerun()

            st.divider()
            col_dl, _ = st.columns([1, 3])
            with col_dl:
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Esporta CSV", csv, "screener.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — SENTIMENT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌡️ Sentiment Mercato":
    st.title("🌡️ Sentiment di Mercato")
    st.caption("Panoramica macro — Fear & Greed, VIX, e sentiment sulle notizie.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Fear & Greed Index")
        fg = get_fear_greed()
        if fg["score"]:
            score = fg["score"]
            if score <= 25: color = "#ff453a"; emoji = "😱 Extreme Fear"
            elif score <= 45: color = "#ff9f0a"; emoji = "😟 Fear"
            elif score <= 55: color = "#636366"; emoji = "😐 Neutral"
            elif score <= 75: color = "#4c8eff"; emoji = "😊 Greed"
            else: color = "#30d158"; emoji = "🤑 Extreme Greed"

            st.markdown(f"""
            <div style='background:#1e2128;border-radius:12px;padding:24px;text-align:center;border:1px solid {color}'>
                <div style='font-size:3rem;font-weight:900;color:{color}'>{score}</div>
                <div style='font-size:1.2rem;color:#f5f5f7;margin-top:8px'>{emoji}</div>
                <div style='background:#2c2c2e;border-radius:4px;height:10px;margin-top:16px'>
                    <div style='background:{color};width:{score}%;height:10px;border-radius:4px'></div>
                </div>
                <div style='display:flex;justify-content:space-between;color:#6b6e77;font-size:0.75rem;margin-top:4px'>
                    <span>0 — Paura estrema</span><span>100 — Avidità estrema</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Fear & Greed non disponibile al momento.")

    with col2:
        st.subheader("VIX — Volatilità")
        macro = get_macro_context()
        if macro["vix"]:
            vix = macro["vix"]
            vcolor = "#30d158" if vix < 15 else ("#ff9f0a" if vix < 25 else "#ff453a")
            st.markdown(f"""
            <div style='background:#1e2128;border-radius:12px;padding:24px;text-align:center;border:1px solid {vcolor}'>
                <div style='font-size:3rem;font-weight:900;color:{vcolor}'>{vix}</div>
                <div style='font-size:1.1rem;color:#f5f5f7;margin-top:8px'>{macro["vix_label"]}</div>
                <div style='color:#6b6e77;font-size:0.85rem;margin-top:12px'>
                    VIX &lt;15 = calmo · 15–25 = moderato · &gt;25 = nervoso
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📰 Sentiment News per Ticker")
    tickers_sentiment = st.text_input(
        "Inserisci ticker separati da virgola",
        placeholder="es. AAPL, NVDA, ENI.MI, SAP.DE",
    )

    if tickers_sentiment:
        tickers_list = [t.strip().upper() for t in tickers_sentiment.split(",") if t.strip()]
        cols = st.columns(min(len(tickers_list), 3))
        for i, t in enumerate(tickers_list[:6]):
            with cols[i % 3]:
                with st.spinner(f"News {t}..."):
                    s = get_news_sentiment(t)
                score_val = s["score"]
                sc = "#30d158" if score_val > 0.05 else ("#ff453a" if score_val < -0.05 else "#636366")
                st.markdown(f"""
                <div style='background:#1e2128;border-radius:10px;padding:16px;border:1px solid {sc};margin-bottom:12px'>
                    <b style='color:#f5f5f7'>{t}</b><br>
                    <span style='color:{sc};font-size:1.1rem'>{s['label']}</span>
                    <span style='color:#6b6e77;font-size:0.85rem'> ({score_val})</span>
                </div>
                """, unsafe_allow_html=True)
                for art in s["articles"][:3]:
                    ac = "#30d158" if art["score"] > 0.05 else ("#ff453a" if art["score"] < -0.05 else "#636366")
                    st.markdown(f"<span style='color:{ac}'>●</span> [{art['title'][:60]}...]({art['url']})",
                                unsafe_allow_html=True)
