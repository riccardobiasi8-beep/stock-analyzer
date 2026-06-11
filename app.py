import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from modules.analyzer import get_stock_data
from modules.screener import run_screener, MARKET_GROUPS
from modules.sentiment import get_fear_greed, get_news_sentiment, get_macro_context, get_full_sentiment
from modules.validator import validate_stock_data
from modules.gemini_analyst import analyze_stock, reason_time_to_target, analyze_sentiment_narrative, validate_and_flag
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

# ── Custom CSS — Apple Borsa identical ────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*{font-family:'Inter',-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif;box-sizing:border-box}
header[data-testid="stHeader"]{background:#000000!important;border-bottom:none!important}
#MainMenu{display:none!important}
header{visibility:hidden!important;height:0!important}
.stDeployButton{display:none!important}
[data-testid="stToolbar"]{display:none!important}
[data-testid="stDecoration"]{display:none!important}
[data-testid="stStatusWidget"]{display:none!important}
.stApp,.stApp>div{background:#000000!important}
.main .block-container{padding:1.5rem 1.8rem!important;max-width:1200px!important}
section[data-testid="stSidebar"]{background:#1c1c1e!important;border-right:0.5px solid #2c2c2e!important}
section[data-testid="stSidebar"] *{color:#ebebf5!important}
section[data-testid="stSidebar"] .stCaption{color:#636366!important}
h1{font-size:1.7rem!important;font-weight:700!important;letter-spacing:-0.03em!important;color:#ffffff!important}
h2{font-size:1.1rem!important;font-weight:600!important;color:#ffffff!important}
h3{font-size:0.95rem!important;font-weight:600!important;color:#ffffff!important}
p,.stMarkdown p{color:#8e8e93!important;line-height:1.5!important}
.stCaption{color:#48484a!important;font-size:0.75rem!important}
[data-testid="metric-container"]{background:#1c1c1e!important;border:0.5px solid #2c2c2e!important;border-radius:12px!important;padding:14px 16px!important}
[data-testid="metric-container"] label{color:#48484a!important;font-size:0.65rem!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:0.08em!important}
[data-testid="stMetricValue"]{color:#ffffff!important;font-size:1.35rem!important;font-weight:600!important;letter-spacing:-0.02em!important}
[data-testid="stMetricDelta"]{font-size:0.78rem!important;font-weight:500!important}
[data-testid="stMetricDelta"] svg{display:none!important}
.stTextInput input{background:#1c1c1e!important;border:0.5px solid #38383a!important;border-radius:10px!important;color:#ffffff!important;font-size:0.95rem!important;padding:10px 14px!important}
.stTextInput input::placeholder{color:#3a3a3c!important}
.stTextInput input:focus{border-color:#30d158!important;box-shadow:0 0 0 3px rgba(48,209,88,0.12)!important;outline:none!important}
[data-baseweb="select"]>div{background:#1c1c1e!important;border:0.5px solid #38383a!important;border-radius:10px!important}
[data-baseweb="select"] span,[data-baseweb="select"] div,[data-baseweb="select"] input{color:#ffffff!important}
[data-baseweb="popover"],[data-baseweb="menu"]{background:#1c1c1e!important;border:0.5px solid #38383a!important;border-radius:10px!important}
[data-baseweb="option"]{background:#1c1c1e!important;color:#ebebf5!important;padding:10px 14px!important}
[data-baseweb="option"]:hover,[data-baseweb="option"][aria-selected="true"]{background:#2c2c2e!important;color:#ffffff!important}
[data-testid="stSlider"]>div>div>div{background:#2c2c2e!important}
.stSlider p{color:#ffffff!important;font-weight:600!important}
.stButton>button{background:#1c1c1e!important;color:#ffffff!important;border:0.5px solid #38383a!important;border-radius:10px!important;font-size:0.85rem!important;font-weight:500!important;padding:9px 20px!important;transition:background 0.15s!important;width:100%!important}
.stButton>button:hover{background:#2c2c2e!important}
.stButton>button[kind="primary"]{background:#30d158!important;border:none!important;color:#000000!important;font-weight:600!important}
.stButton>button[kind="primary"]:hover{background:#25a244!important}
.stButton>button *{color:inherit!important}
.stTabs [data-baseweb="tab-list"]{background:#1c1c1e!important;border-radius:10px!important;padding:3px!important;border:0.5px solid #2c2c2e!important;gap:2px!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;border-radius:7px!important;padding:6px 16px!important;font-size:0.82rem!important;font-weight:500!important;color:#48484a!important}
.stTabs [aria-selected="true"]{background:#2c2c2e!important;color:#ffffff!important}
[data-testid="stVerticalBlockBorderWrapper"]{border:0.5px solid #2c2c2e!important;border-radius:12px!important;background:#1c1c1e!important}
.stDataFrame{border-radius:12px!important;overflow:hidden!important}
[data-testid="stDataFrame"]{border:0.5px solid #2c2c2e!important;border-radius:12px!important}
[data-testid="stDataFrame"] th{background:#1c1c1e!important;color:#48484a!important;font-size:0.68rem!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:0.06em!important;padding:9px 12px!important;border-bottom:0.5px solid #2c2c2e!important}
[data-testid="stDataFrame"] td{background:#000000!important;color:#ebebf5!important;font-size:0.82rem!important;padding:8px 12px!important;border-bottom:0.5px solid #1c1c1e!important}
.stProgress>div>div>div{background:#30d158!important;border-radius:2px!important}
.stProgress>div>div{background:#2c2c2e!important;border-radius:2px!important}
.stAlert{border-radius:10px!important;border:none!important}
.stSuccess{background:rgba(48,209,88,0.12)!important}
.stSuccess p,.stSuccess span{color:#30d158!important}
.stInfo{background:rgba(10,132,255,0.12)!important}
.stInfo p,.stInfo span{color:#0a84ff!important}
.stWarning{background:rgba(255,159,10,0.12)!important}
.stWarning p,.stWarning span{color:#ff9f0a!important}
.stError{background:rgba(255,69,58,0.12)!important}
.stError p,.stError span{color:#ff453a!important}
hr{border:none!important;border-top:0.5px solid #2c2c2e!important;margin:1.2rem 0!important}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#38383a;border-radius:2px}
.stRadio label{color:#ebebf5!important;font-size:0.85rem!important;font-weight:400!important;text-transform:none!important;letter-spacing:0!important}
.stSpinner>div{border-top-color:#30d158!important}
[data-testid="stExpander"]{border:0.5px solid #2c2c2e!important;border-radius:10px!important;background:#1c1c1e!important}
[data-testid="stExpander"] summary{color:#8e8e93!important}
[data-testid="stExpander"] summary:hover{color:#ffffff!important}
</style>
""", unsafe_allow_html=True)

from plotly.subplots import make_subplots

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
    st.markdown("<div style='padding:6px 0 12px'><div style='font-size:1rem;font-weight:700;color:#ffffff;letter-spacing:-0.02em'>Stock Analyzer</div><div style='font-size:0.7rem;color:#444;margin-top:2px;letter-spacing:0.04em'>Yahoo Finance · 15min delay</div></div>", unsafe_allow_html=True)
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

    col_input, _ = st.columns([3, 1])
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

    period = "2y"  # always fetch 2y, filtered in chart by per_sel

    # Fetch solo se ticker è diverso dall'ultimo o dati assenti
    if ticker_input:
        _gkey = st.secrets.get("GEMINI_API_KEY", "")
        
        if ticker_input != st.session_state.last_ticker or st.session_state.last_data is None:
            with st.spinner(f"Carico dati per {ticker_input}..."):
                data = get_stock_data(ticker_input, period=period)
            
            if data and "error" not in data and _gkey:
                _val_placeholder = st.empty()
                _val_status_prev = data.get("validation", {}).get("status")
                if _val_status_prev not in ["completed"]:
                    _val_placeholder.info("🔍 Gemini sta validando i dati...")
                    try:
                        data = validate_stock_data(data, _gkey, st.secrets.get("GROQ_API_KEY",""))
                        _val_status = data.get("validation", {}).get("status")
                        _n_corr = len(data.get("validation", {}).get("corrected_fields", []))
                        _summary = data.get("validation", {}).get("summary", "")
                        if _val_status == "completed" and _n_corr > 0:
                            _val_placeholder.success(f"✅ Gemini: {_n_corr} correzioni — {_summary}")
                        elif _val_status == "completed":
                            _val_placeholder.success(f"✅ Dati validati — {_summary or 'nessuna anomalia'}")
                        elif _val_status == "error":
                            _err = data.get("validation", {}).get("issues", [""])[0]
                            if "quota" in _err.lower() or "rate" in _err.lower():
                                _val_placeholder.warning("⏳ Quota Gemini esaurita — i dati vengono mostrati senza validazione AI. Si resetta a mezzanotte UTC.")
                            else:
                                _val_placeholder.warning(f"⚠️ Validazione non disponibile")
                        else:
                            _val_placeholder.empty()
                        import time; time.sleep(1.5)
                        _val_placeholder.empty()
                    except Exception as _ve:
                        _val_placeholder.empty()
                        print(f"[App Validator Exception] {_ve}")

            st.session_state.last_data = data
            st.session_state.last_ticker = ticker_input
            st.session_state.last_period = period

        else:
            data = st.session_state.last_data
            # Re-validate if previous run had no validation or errored
            if _gkey and data and "error" not in data:
                _val = data.get("validation", {})
                if _val.get("status") in [None, "skipped", "error"]:
                    with st.spinner("🔍 Validazione dati con Gemini..."):
                        try:
                            data = validate_stock_data(data, _gkey, st.secrets.get("GROQ_API_KEY",""))
                            st.session_state.last_data = data
                        except Exception as _ve2:
                            print(f"[Validator retry error] {_ve2}")
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
            def fmt(v, cur=""): return f"{v:,.2f} {cur}".strip() if v else "—"

            # ── Apple-style header ──
            cur = data['currency']
            price = data['current_price']
            chg_1d = None
            chg_1d_pct = None
            try:
                import math
                h1d = data["hist"]["Close"].dropna()
                if len(h1d) >= 2:
                    v1 = float(h1d.iloc[-1])
                    v2 = float(h1d.iloc[-2])
                    if not math.isnan(v1) and not math.isnan(v2) and v2 != 0:
                        chg_1d = round(v1 - v2, 2)
                        chg_1d_pct = round(chg_1d / v2 * 100, 2)
            except Exception:
                chg_1d = chg_1d_pct = None

            chg_color = "#30d158" if (chg_1d or 0) >= 0 else "#ff453a"
            chg_str = f"{'+' if (chg_1d or 0)>=0 else ''}{chg_1d} ({'+' if (chg_1d_pct or 0)>=0 else ''}{chg_1d_pct}%)" if chg_1d is not None else ""
            score = data["score"]
            sig_color = "#30d158" if "BUY" in data["signal"] else ("#ff9f0a" if "HOLD" in data["signal"] else "#ff453a")

            st.markdown(f"""
<div style='padding:4px 0 16px'>
    <div style='font-size:0.78rem;color:#48484a;font-weight:500;text-transform:uppercase;letter-spacing:0.06em'>{data['ticker']} · {data['sector']}</div>
    <div style='font-size:0.95rem;color:#8e8e93;margin:2px 0 8px'>{data['name']}</div>
    <div style='display:flex;align-items:baseline;gap:12px;flex-wrap:wrap'>
        <span style='font-size:2.6rem;font-weight:700;color:#ffffff;letter-spacing:-0.04em;line-height:1'>{price} {cur}</span>
        <span style='font-size:1rem;font-weight:500;color:{chg_color}'>{chg_str}</span>
    </div>
    <div style='display:flex;align-items:center;gap:16px;margin-top:10px;flex-wrap:wrap'>
        <span style='background:{sig_color}22;border:1px solid {sig_color}55;border-radius:6px;padding:3px 10px;font-size:0.8rem;font-weight:600;color:{sig_color}'>{data['signal']}</span>
        <span style='font-size:0.8rem;color:#48484a'>Score {score}/100</span>
        <div style='flex:1;max-width:120px;height:3px;background:#1c1c1e;border-radius:2px'>
            <div style='height:3px;width:{score}%;background:{sig_color};border-radius:2px'></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

            # ── Validation setup + ai_metric helper ──────────────────────
            val = data.get("validation", {})
            _corrected_fields = set()
            _field_reasoning = {}
            if val.get("status") == "completed":
                for c in val.get("corrected_fields", []):
                    _corrected_fields.add(c.split(":")[0].strip())
                _field_reasoning = val.get("field_reasoning", {})
            # Debug
            import sys
            print(f"[DEBUG] validation status: {val.get('status')} | corrected: {val.get('corrected_fields',[])} | _corrected_fields: {_corrected_fields}", file=sys.stderr)

            def ai_metric(label, field_key, value, suffix="", delta=None):
                is_ai = field_key in _corrected_fields
                display_val = f"{value}{suffix}" if value is not None else "N/A"
                if is_ai:
                    st.markdown(
                        f"<div style='background:#1c1c1e;border:0.5px solid #0a84ff44;border-radius:12px;padding:14px 16px'>"
                        f"<div style='font-size:0.65rem;color:#48484a;font-weight:600;text-transform:uppercase;letter-spacing:0.08em'>{label}</div>"
                        f"<div style='font-size:1.25rem;font-weight:600;color:#0a84ff;margin-top:4px'>"
                        f"{display_val} <span style='font-size:0.6rem;background:#0a84ff22;color:#0a84ff;border:1px solid #0a84ff55;border-radius:4px;padding:1px 6px'>ⓘ AI</span>"
                        f"</div></div>",
                        unsafe_allow_html=True)
                else:
                    st.metric(label, display_val, delta=delta)

            # Validation summary badge
            if val.get("status") == "completed":
                v_score = val.get("score", 100)
                v_rel = val.get("reliability", "N/A")
                v_corr = val.get("corrected_fields", [])
                v_issues = val.get("issues", [])
                v_summary = val.get("summary", "")
                v_icon = "✅" if v_score >= 80 else ("⚠️" if v_score >= 60 else "🔴")
                badge = f"{v_icon} Dati validati da AI · {v_rel}"
                if v_corr: badge += f" · {len(v_corr)} correzioni"
                with st.expander(badge):
                    if v_corr:
                        st.markdown("**Correzioni applicate:**")
                        for c in v_corr:
                            parts = c.split("→")
                            if len(parts) == 2:
                                st.markdown(f"<span style='color:#0a84ff'>ⓘ</span> **{parts[0].strip()}** → <span style='color:#0a84ff'>{parts[1].strip()}</span>", unsafe_allow_html=True)
                    if v_issues:
                        st.markdown("**Anomalie rilevate:**")
                        for issue in v_issues:
                            st.markdown(f"⚠️ {issue}")
                    if not v_corr and not v_issues:
                        st.markdown("✅ Tutti i dati nella norma.")
                    if v_summary: st.caption(v_summary)

            # ── AI Summary (Gemini) ───────────────────────────────────────
            gemini_key = st.secrets.get("GEMINI_API_KEY", "")
            _ai_key = gemini_key or st.secrets.get("GEMINI_API_KEY", "")
            _use_gemini = bool(gemini_key)

            if _ai_key:
                ai_cache_key = f"ai_{ticker_input}"
                if ai_cache_key not in st.session_state:
                    with st.spinner("Analisi AI in corso..."):
                        import time as _time
                        _time.sleep(2)  # delay after validation to avoid rate limit
                        try:
                            if _use_gemini:
                                ai_text = analyze_stock(data, gemini_key, st.secrets.get("GROQ_API_KEY",""))
                            else:
                                import requests as req
                                _prompt = f"""Analista finanziario esperto. Analizza {data['name']} ({data['ticker']}) in italiano, max 100 parole.
Dati: Prezzo {price} {cur} | Segnale {data['signal']} score {score}/100 | Entry {data['entry_price']} | Target {data['target_price']} | Stop {data['stop_loss']} | Upside {data['upside_pct']}% | RSI {data['rsi']} | P/E {data['pe']} | Settore {data['sector']}
Scrivi 2 frasi sui fondamentali+tecnica poi verdetto secco: BUY/HOLD/AVOID. Entry: X. Target: Y. Stop: Z."""
                                _r = req.post("https://api.groq.com/openai/v1/chat/completions",
                                    headers={"Content-Type":"application/json","Authorization":f"Bearer {_ai_key}"},
                                    json={"model":"llama-3.3-70b-versatile","max_tokens":200,"messages":[{"role":"user","content":_prompt}]},
                                    timeout=15)
                                ai_text = _r.json()["choices"][0]["message"]["content"]
                            st.session_state[ai_cache_key] = ai_text
                        except Exception as _e:
                            st.session_state[ai_cache_key] = None

                ai_text = st.session_state.get(ai_cache_key)
                if ai_text:
                    import re as _re
                    ai_clean = _re.sub(r'\*\*(.*?)\*\*', r'\1', ai_text).strip()
                    _ac, _bc = st.columns([11, 1])
                    with _ac:
                        st.markdown(f"<div style='background:#1c1c1e;border-left:3px solid {sig_color};padding:13px 16px;border-radius:0 10px 10px 0;font-size:0.84rem;color:#ebebf5;line-height:1.7'>{ai_clean.replace(chr(10),'<br>')}</div>", unsafe_allow_html=True)
                    with _bc:
                        if st.button('↺', key='rigenera_ai', help='Rigenera analisi AI'):
                            del st.session_state[ai_cache_key]
                            st.rerun()

            # ── Tabs ──
            tab1, tab2, tab3, tab4 = st.tabs(["Grafico", "Tecnica", "Fondamentali", "News & Sentiment"])

            with tab1:
                # ── Metriche in cima stile Apple ──
                upside = data.get("upside_pct")
                net_g = data.get("upside_net_pct")
                ann_r = data.get("annualized_return")
                t_label = data.get("time_label","—")
                cur = data['currency']

                # Gemini time reasoning (cached)
                if gemini_key:
                    _time_cache = f"time_{ticker_input}"
                    if _time_cache not in st.session_state:
                        with st.spinner("Gemini analizza i tempi realistici..."):
                            import time as _time2
                            _time2.sleep(3)  # delay to avoid rate limit
                            try:
                                t_reasoning = reason_time_to_target(data, gemini_key, st.secrets.get("GROQ_API_KEY",""))
                                st.session_state[_time_cache] = t_reasoning
                            except Exception:
                                st.session_state[_time_cache] = None
                    _time_reasoning = st.session_state.get(_time_cache)
                else:
                    _time_reasoning = None

                # Grid metriche
                # Grid metriche
                def _cell(label, value, color=None, ai_field=None):
                    if color is None: color = "#ffffff"
                    is_ai = bool(ai_field and ai_field in _corrected_fields)
                    ai_span = "<span style=\"font-size:0.55rem;background:#0a84ff22;color:#0a84ff;border:1px solid #0a84ff55;border-radius:3px;padding:0 4px\">ⓘ AI</span>"
                    badge = " " + ai_span if is_ai else ""
                    vc = "#0a84ff" if is_ai else color
                    bo = "border:0.5px solid #0a84ff44;" if is_ai else ""
                    val_str = str(value) if value else "\u2014"
                    return (
                        f"<div style='background:#000000;padding:11px 14px;{bo}'>"
                        f"<div style='font-size:0.62rem;color:#48484a;font-weight:600;text-transform:uppercase;letter-spacing:0.06em'>{label}{badge}</div>"
                        f"<div style='font-size:0.95rem;font-weight:600;color:{vc};margin-top:2px'>{val_str}</div></div>")

                def _pct(val, avoid=False):
                    """Format percentage: 2 decimals. For AVOID: only minus sign."""
                    if val is None: return "—"
                    v = round(float(val), 2)
                    if avoid:
                        return f"{v:.2f}%" if v < 0 else f"-{abs(v):.2f}%"
                    return f"{v:+.2f}%"
                upside_str = _pct(upside, avoid=is_avoid) if upside is not None else "—"
                netg_str = _pct(net_g, avoid=is_avoid) if net_g is not None else "—"
                annr_str = _pct(ann_r) if (ann_r is not None and not is_hold and not is_avoid) else "—"
                fv_str = fmt(data.get('fair_value'), cur) if data.get('fair_value') else '—'
                is_avoid = data.get('is_avoid', False)
                is_hold = data.get('is_hold', False)
                if is_avoid:
                    _cells = [
                        _cell('Entry', '—'),
                        _cell('Downside target', fmt(data['target_price'], cur), '#ff453a', 'target_price'),
                        _cell('Stop rimbalzo', fmt(data['stop_loss'], cur), '#ff9f0a'),
                        _cell('Fair Value', fv_str, '#ffffff', 'fair_value'),
                        _cell('Downside potenz.', upside_str, '#ff453a', 'upside_pct'),
                        _cell('Netto (-26%)', netg_str, '#ff453a'),
                        _cell('Rend. annuo', '—', '#636366'),
                        _cell('Valutazione', 'EVITA', '#ff453a'),
                    ]
                else:
                    # BUY or HOLD
                    if is_hold:
                        # FIX 5: HOLD — congela tutti i campi operativi
                        _cells = [
                            _cell('Entry', '— (attendi)', '#636366'),
                            _cell('Target', fmt(data['target_price'], cur) if data.get('target_price') else '—', '#636366'),
                            _cell('Stop Loss', '—', '#636366'),
                            _cell('Fair Value', fv_str, '#ffffff', 'fair_value'),
                            _cell('Upside potenz.', upside_str, '#636366', 'upside_pct'),
                            _cell('Netto potenz.', netg_str, '#636366'),
                            _cell('Rend. annuo', '—', '#636366'),
                            _cell('Stato', 'ATTENDI SEGNALE', '#ff9f0a'),
                        ]
                    else:
                        # BUY
                        _cells = [
                            _cell('Entry', fmt(data['entry_price'], cur) if data.get('entry_price') else '—'),
                            _cell('Target', fmt(data['target_price'], cur), '#ff9f0a', 'target_price'),
                            _cell('Stop Loss', fmt(data['stop_loss'], cur), '#ff453a'),
                            _cell('Fair Value', fv_str, '#ffffff', 'fair_value'),
                            _cell('Upside (da prezzo att.)', upside_str, '#30d158', 'upside_pct'),
                            _cell('Netto (-26%)', netg_str, '#30d158'),
                            _cell('Rend. annuo', annr_str, '#bf5af2'),
                            _cell('Tempo al target', t_label[:25] if t_label else '—', '#0a84ff'),
                        ]
                _grid = ''.join(_cells)
                st.markdown(
                    f"<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#2c2c2e;border-radius:12px;overflow:hidden;margin-bottom:12px'>{_grid}</div>",
                    unsafe_allow_html=True)

                # Gemini time reasoning box
                if _time_reasoning and not str(_time_reasoning).startswith("Stima") and not str(_time_reasoning).startswith("Analisi"):
                    import re as _re_t
                    _tr_clean = _re_t.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', str(_time_reasoning))
                    st.markdown(f"<div style='background:#1c1c1e;border-left:3px solid #0a84ff;padding:11px 16px;border-radius:0 10px 10px 0;font-size:0.82rem;color:#ebebf5;line-height:1.65;margin-bottom:8px'>⏱ <b>Stima temporale Gemini:</b> {_tr_clean.replace(chr(10),'<br>')}</div>", unsafe_allow_html=True)

                # Period selector — Apple style pill
                per_sel = st.radio("Periodo", ["1M","3M","6M","1A","2A","5A"], index=3, horizontal=True, label_visibility="collapsed")
                hist = data["hist"]
                import pandas as pd
                cutoff_days = {"1M":21,"3M":63,"6M":126,"1A":252,"2A":504,"5A":1260}
                n_days = cutoff_days.get(per_sel, 252)
                hist_view = hist.tail(n_days)

                close_vals = hist_view["Close"].values
                is_up = len(close_vals) > 0 and close_vals[-1] >= close_vals[0]
                line_color = "#30d158" if is_up else "#ff453a"
                # Apple uses deep green fill — linear gradient approximated with low opacity
                fill_color = "rgba(48,209,88,0.15)" if is_up else "rgba(255,69,58,0.12)"

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    row_heights=[0.82, 0.18], vertical_spacing=0.0,
                    specs=[[{"type":"scatter"}],[{"type":"bar"}]])

                # Main price line — Apple style: smooth, bright green, filled
                fig.add_trace(go.Scatter(
                    x=hist_view.index, y=hist_view["Close"],
                    mode="lines", name="",
                    line=dict(color=line_color, width=2.5, shape="spline", smoothing=0.3),
                    fill="tozeroy", fillcolor=fill_color,
                    hovertemplate="<b>%{y:.2f}</b><br>%{x|%d %b %Y}<extra></extra>",
                ), row=1, col=1)

                # Volume — tiny bars at bottom like Apple
                vol_colors = ["rgba(48,209,88,0.5)" if c >= o else "rgba(255,69,58,0.5)"
                    for c, o in zip(hist_view["Close"], hist_view["Open"])]
                fig.add_trace(go.Bar(
                    x=hist_view.index, y=hist_view["Volume"],
                    marker_color=vol_colors, name="",
                    hovertemplate="%{y:,.0f}<extra></extra>",
                ), row=2, col=1)

                # Target & Stop lines
                if data.get("target_price"):
                    fig.add_hline(y=data["target_price"], line_dash="dot",
                        line_color="rgba(255,159,10,0.6)", line_width=1,
                        annotation_text=f"  {data['target_price']}",
                        annotation_font_color="#ff9f0a", annotation_font_size=11,
                        annotation_position="right", row=1, col=1)
                if data.get("stop_loss"):
                    fig.add_hline(y=data["stop_loss"], line_dash="dot",
                        line_color="rgba(255,69,58,0.5)", line_width=1,
                        annotation_text=f"  {data['stop_loss']}",
                        annotation_font_color="#ff453a", annotation_font_size=11,
                        annotation_position="right", row=1, col=1)

                # Y-axis tick values (Apple shows 3-4 clean values)
                if len(close_vals) > 0:
                    ymin, ymax = float(hist_view["Close"].min()), float(hist_view["Close"].max())
                    yrng = ymax - ymin
                    import numpy as np
                    tick_vals = [round(ymin + yrng*t, 2) for t in [0.1, 0.4, 0.7, 0.95]]

                fig.update_layout(
                    height=400, showlegend=False,
                    paper_bgcolor="#000000", plot_bgcolor="#000000",
                    margin=dict(l=0, r=52, t=4, b=0),
                    font=dict(family="-apple-system,Inter,sans-serif", size=11, color="#636366"),
                    xaxis=dict(
                        showgrid=False, zeroline=False, showline=False,
                        tickfont=dict(size=11, color="#636366"),
                        tickformat="%Y" if n_days > 300 else "%b '%y",
                        nticks=5,
                    ),
                    yaxis=dict(
                        showgrid=True, gridcolor="#1c1c1e", gridwidth=0.5,
                        zeroline=False, showline=False,
                        tickfont=dict(size=11, color="#8e8e93"),
                        side="right",
                        tickvals=tick_vals if len(close_vals) > 0 else None,
                        tickformat=",.0f",
                    ),
                    xaxis2=dict(showgrid=False, zeroline=False, showline=False, showticklabels=False),
                    yaxis2=dict(showgrid=False, zeroline=False, showline=False, showticklabels=False),
                    hoverlabel=dict(
                        bgcolor="#1c1c1e", bordercolor="#38383a",
                        font=dict(size=13, color="#ffffff", family="-apple-system,Inter,sans-serif")
                    ),
                    hovermode="x unified",
                )
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


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
                # Warning se tutti i fondamentali sono N/A
                _fund_fields = ["pe","pb","ev_ebitda","roe","profit_margin","revenue_growth","debt_equity","beta","dividend_yield"]
                _available_funds = [f for f in _fund_fields if data.get(f) is not None]
                if len(_available_funds) == 0:
                    st.warning("⚠️ Yahoo Finance non ha dati fondamentali per questo ticker. Gemini sta stimando i valori in base al settore — i dati mostrati sono stime AI, non dati ufficiali.")
                elif len(_available_funds) < 4:
                    st.info(f"ℹ️ Dati parziali: {len(_available_funds)}/9 campi disponibili da Yahoo Finance. I rimanenti sono stimati da Gemini.")
                # ── Fair Value — 3 Pilastri ──────────────────────────────
                cur = data['currency']
                fv = data.get("fair_value")
                fv_c = data.get("fv_consensus")
                fv_m = data.get("fv_multiples")
                fv_d = data.get("fv_dcf")
                n_an = data.get("n_analysts", 0)

                st.markdown("**📐 Fair Value — Zona di prezzo ragionevole**")
                fv_col1, fv_col2, fv_col3, fv_col4 = st.columns(4)
                fv_color = "#30d158" if fv and fv > data['current_price'] else "#ff9f0a"
                fv_col1.metric(
                    f"Fair Value ({cur})",
                    f"{fv:.2f}" if fv else "N/A",
                    delta=f"+{round((fv-data['current_price'])/data['current_price']*100,1)}%" if fv else None,
                    help="Media ponderata dei 3 pilastri: Consensus 50% + Multipli 30% + DCF 20%"
                )
                fv_col2.metric(
                    f"① Consensus ({n_an} analisti)",
                    f"{fv_c:.2f} {cur}" if fv_c else "N/A",
                    help="Target medio banche d'affari — peso 50%"
                )
                fv_col3.metric(
                    "② Multipli settore",
                    f"{fv_m:.2f} {cur}" if fv_m else "N/A",
                    help="EPS forward × P/E medio settore — peso 30%"
                )
                fv_col4.metric(
                    "③ DCF conservativo",
                    f"{fv_d:.2f} {cur}" if fv_d else "N/A",
                    help="DCF 5 anni, growth cap 8%, WACC 8-12% — peso 20%"
                )
                st.divider()

                # ── Fondamentali ─────────────────────────────────────────
                c1, c2, c3 = st.columns(3)
                with c1:
                    ai_metric("P/E Ratio", "pe", data["pe"])
                    ai_metric("P/B Ratio", "pb", data["pb"])
                    ai_metric("EV/EBITDA", "ev_ebitda", data["ev_ebitda"])
                with c2:
                    ai_metric("ROE", "roe", data["roe"], suffix="%" if data["roe"] else "")
                    ai_metric("Margine Netto", "profit_margin", data["profit_margin"], suffix="%" if data["profit_margin"] else "")
                    ai_metric("Crescita Ricavi", "revenue_growth", data["revenue_growth"], suffix="%" if data["revenue_growth"] else "")
                with c3:
                    ai_metric("Debt/Equity", "debt_equity", data["debt_equity"])
                    ai_metric("Dividend Yield", "dividend_yield", data["dividend_yield"], suffix="%" if data["dividend_yield"] else "")
                    ai_metric("Beta", "beta", data["beta"])
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
    <span style='color:#636366;margin-left:16px'>Score sentiment: <b style='color:#f5f5f7'>{sc}/100</b></span>
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

                # ── Analisi AI del Sentiment (Gemini) ────────────────────
                st.divider()
                _sent_ai_key = gemini_key or st.secrets.get("GEMINI_API_KEY", "")
                if _sent_ai_key:
                    sent_cache_key = f"sent_analysis_{ticker_input}"
                    col_btn, _ = st.columns([2, 5])
                    with col_btn:
                        if st.button("🧠 Analisi AI Sentiment", key="ai_sentiment_btn", type="primary"):
                            if sent_cache_key in st.session_state:
                                del st.session_state[sent_cache_key]

                    if sent_cache_key not in st.session_state:
                        with st.spinner("Gemini analizza il sentiment..."):
                            try:
                                if gemini_key:
                                    _sent_text = analyze_sentiment_narrative(data, sent, gemini_key, st.secrets.get("GROQ_API_KEY",""))
                                else:
                                    import requests as _req
                                    an = sent.get("analyst", {})
                                    sh = sent.get("short", {})
                                    ea = sent.get("earnings", {})
                                    op = sent.get("options", {})
                                    ins = sent.get("insider", {})
                                    nw = sent.get("news", {})
                                    _prompt = f"""Analista finanziario senior. Analizza sentiment {data['name']} ({data['ticker']}) in italiano 250 parole.
Consensus: {an.get('consensus_label','N/A')} | {an.get('n_analysts',0)} analisti | Target: {an.get('target_mean','N/A')} | Upside: {an.get('upside','N/A')}%
Short: {sh.get('short_pct','N/A')}% | Put/Call: {op.get('put_call_ratio','N/A')} | Earnings media: {ea.get('avg_surprise','N/A')}% | Prossimi: {ea.get('next_earnings','N/A')}
Spiega paradossi consensus, short interest, earnings pattern, data chiave, verdetto finale."""
                                    _r = _req.post("https://api.groq.com/openai/v1/chat/completions",
                                        headers={"Content-Type":"application/json","Authorization":f"Bearer {_sent_ai_key}"},
                                        json={"model":"llama-3.3-70b-versatile","max_tokens":600,"messages":[{"role":"user","content":_prompt}]},
                                        timeout=30)
                                    _sent_text = _r.json()["choices"][0]["message"]["content"]
                                st.session_state[sent_cache_key] = _sent_text
                            except Exception as _e:
                                st.session_state[sent_cache_key] = f"Errore: {_e}"

                    if sent_cache_key in st.session_state:
                        import re as _re2
                        _txt = st.session_state[sent_cache_key] or ""
                        sc_col = "#30d158" if sent.get("score",50) >= 65 else ("#ff9f0a" if sent.get("score",50) >= 45 else "#ff453a")
                        if not _txt:
                            st.caption("Analisi non disponibile — riprova.")
                        else:
                            _txt_html = _re2.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', _txt)
                            st.markdown(f"""<div style='background:#1c1c1e;border-left:3px solid {sc_col};padding:16px 20px;border-radius:0 12px 12px 0;font-size:0.85rem;color:#ebebf5;line-height:1.75'>{_txt_html.replace(chr(10),'<br>')}</div>""", unsafe_allow_html=True)


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

    if st.button("🚀 Avvia Screener", type="primary", width='stretch'):
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

        if df is None or df.empty:
            if st.session_state.screener_df is None:
                st.info("Configura i filtri e clicca Avvia Screener.")
            else:
                st.warning("Nessun titolo trovato. Prova ad abbassare lo score minimo.")
        else:
            def rv(v, d=2):
                try:
                    f = float(v)
                    return None if f != f else round(f, d)
                except: return None

            st.success(f"✅ {len(df)} titoli trovati con score ≥ {min_score}")

            for _, row in df.iterrows():
                sig = str(row.get("Segnale", ""))
                score_val = rv(row.get("Score"), 0) or 0
                ticker = str(row.get("Ticker", ""))
                nome = str(row.get("Nome", ticker))[:40]
                settore = str(row.get("Settore", "—"))
                valuta = str(row.get("Valuta", ""))
                prezzo = rv(row.get("Prezzo"), 2)
                target = rv(row.get("Target"), 2)
                stop = rv(row.get("Stop Loss"), 2)
                entry = rv(row.get("Entry"), 2)
                upside = rv(row.get("Upside % lordo"), 1)
                upside_net = rv(row.get("Upside % netto"), 1)
                ann = rv(row.get("Rend. annualizzato"), 1)
                tempo = str(row.get("Tempo stimato", "—")).replace("🔵","").replace("🟢","").replace("🟡","").replace("🟠","").replace("🔴","").strip()
                pe = rv(row.get("P/E"), 1)
                pb = rv(row.get("P/B"), 2)
                rsi = rv(row.get("RSI"), 1)
                sig_icon = "🟢" if "BUY" in sig else ("🟡" if "HOLD" in sig else "🔴")

                with st.container(border=True):
                    # Header row
                    h1, h2 = st.columns([2, 1])
                    with h1:
                        st.markdown(f"### {sig_icon} {ticker} &nbsp; <span style='font-size:0.85rem;color:#8e8e93;font-weight:400'>{nome}</span>", unsafe_allow_html=True)
                        st.caption(f"{settore}  ·  Score: **{score_val}/100**  ·  {sig}")
                    with h2:
                        if upside and upside > 0:
                            st.metric("Upside lordo", f"+{upside}%", delta=f"netto +{upside_net}%" if upside_net else None)

                    # Price row
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("💰 Prezzo", f"{prezzo} {valuta}" if prezzo else "—")
                    c2.metric("🎯 Target", f"{target} {valuta}" if target else "—")
                    c3.metric("🛡 Stop Loss", f"{stop} {valuta}" if stop else "—")
                    c4.metric("⏱ Tempo", tempo[:20] if tempo else "—")
                    c5.metric("📊 Rend. annuo", f"+{ann}%" if ann else "—")

                    # Expand details
                    with st.expander("Dettagli fondamentali"):
                        d1, d2, d3, d4 = st.columns(4)
                        d1.metric("Entry suggerito", f"{entry} {valuta}" if entry else "—")
                        d2.metric("RSI", f"{rsi}" if rsi else "—")
                        d3.metric("P/E", f"{pe}" if pe else "—")
                        d4.metric("P/B", f"{pb}" if pb else "—")
                        if st.button(f"🔍 Analisi completa di {ticker}", key=f"go_{ticker}", type="primary"):
                            st.session_state.last_ticker = ticker
                            st.session_state.last_data = None
                            st.session_state.page_override = "🔍 Analisi Titolo"
                            st.rerun()

            st.divider()
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Esporta CSV", csv, "screener.csv", "text/csv", width='content')


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
                <div style='display:flex;justify-content:space-between;color:#636366;font-size:0.75rem;margin-top:4px'>
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
                <div style='color:#636366;font-size:0.85rem;margin-top:12px'>
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
                    <span style='color:#636366;font-size:0.85rem'> ({score_val})</span>
                </div>
                """, unsafe_allow_html=True)
                for art in s["articles"][:3]:
                    ac = "#30d158" if art["score"] > 0.05 else ("#ff453a" if art["score"] < -0.05 else "#636366")
                    st.markdown(f"<span style='color:{ac}'>●</span> [{art['title'][:60]}...]({art['url']})",
                                unsafe_allow_html=True)
