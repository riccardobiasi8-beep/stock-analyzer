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
    "SPM.MI": "Saipem SpA", "SRG.MI": "Snam SpA", "STM.MI": "STMicroelectronics",
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
    .main { background-color: #0e1117; }
    .metric-card {
        background: #1c1f2e;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        border: 1px solid #2d3147;
    }
    .signal-buy { color: #00d09c; font-size: 1.4rem; font-weight: 700; }
    .signal-hold { color: #f0b429; font-size: 1.4rem; font-weight: 700; }
    .signal-sell { color: #ff4d6d; font-size: 1.4rem; font-weight: 700; }
    .score-bar { height: 8px; border-radius: 4px; margin-top: 6px; }
    h1 { color: #e0e6f0; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 Stock Analyzer")
    st.caption("Dati con ~15 min delay · Yahoo Finance")
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
                st.caption(f"🔍 Ticker diretto: **{ticker_input}**")
            elif len(suggestions) == 1:
                ticker_input = suggestions[0].split(" — ")[0]
                st.caption(f"✅ {suggestions[0]}")
            else:
                choice = st.selectbox(
                    "Seleziona il titolo",
                    suggestions,
                    label_visibility="collapsed",
                    key="ticker_select",
                )
                ticker_input = choice.split(" — ")[0]

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
            st.error(f"❌ {data['error']} — Controlla il ticker e riprova.")
        else:
            # ── Header ──
            st.subheader(f"{data['name']} ({data['ticker']})")
            st.caption(f"{data['sector']} · {data['industry']}")

            # ── KPI row ──
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("💰 Prezzo", f"{data['current_price']} {data['currency']}")
            k2.metric("🎯 Entry suggerito", f"{data['entry_price']} {data['currency']}")
            k3.metric("🚀 Target price", f"{data['target_price']} {data['currency']}",
                      delta=f"+{data['upside_pct']}%" if data['upside_pct'] else None)
            k4.metric("🛡️ Stop Loss", f"{data['stop_loss']} {data['currency']}")
            k5.metric("Fair Value (DCF)", f"{data['fair_value']} {data['currency']}" if data['fair_value'] else "N/A")

            # ── Stima tempo + guadagno ──
            if data.get("upside_pct") and data["upside_pct"] > 0:
                tc = data.get("time_category", "N/A")
                tc_color = "#5b8dee" if "Breve" in tc else ("#00d09c" if "Medio" in tc and "Lungo" not in tc else ("#f0b429" if "Lungo" in tc else ("#ff8c42" if "Molto" in tc else "#8892a4")))
                ann = data.get("annualized_return")
                net = data.get("upside_net_pct")
                st.markdown(f"""
<div style='background:#1c1f2e;border-radius:10px;padding:16px;margin:8px 0;display:flex;gap:32px;flex-wrap:wrap;border:1px solid #2d3147'>
    <div>
        <div style='color:#8892a4;font-size:0.78rem'>⏱ Tempo stimato al target</div>
        <div style='color:{tc_color};font-weight:700;font-size:1.05rem'>{data.get("time_label","N/A")}</div>
    </div>
    <div>
        <div style='color:#8892a4;font-size:0.78rem'>📈 Guadagno lordo</div>
        <div style='color:#00d09c;font-weight:700;font-size:1.05rem'>+{data['upside_pct']}%</div>
    </div>
    <div>
        <div style='color:#8892a4;font-size:0.78rem'>💶 Guadagno netto (−26% tasse IT)</div>
        <div style='color:#00d09c;font-weight:700;font-size:1.05rem'>+{net}%</div>
    </div>
    {'<div><div style="color:#8892a4;font-size:0.78rem">📊 Rendimento annualizzato</div><div style="color:#c77dff;font-weight:700;font-size:1.05rem">+' + str(ann) + '% /anno</div></div>' if ann else ''}
</div>
""", unsafe_allow_html=True)

            # ── Signal ──
            score = data["score"]
            signal_color = "#00d09c" if "BUY" in data["signal"] else ("#f0b429" if "HOLD" in data["signal"] else "#ff4d6d")
            st.markdown(f"""
            <div style='background:#1c1f2e;border-radius:12px;padding:20px;margin:16px 0;border:1px solid {signal_color}'>
                <span style='font-size:1.6rem;font-weight:800;color:{signal_color}'>{data['signal']}</span>
                <span style='color:#8892a4;margin-left:20px'>Score composito: <b style='color:#e0e6f0'>{score}/100</b></span>
                <div style='background:#2d3147;border-radius:4px;height:8px;margin-top:10px'>
                    <div style='background:{signal_color};width:{score}%;height:8px;border-radius:4px'></div>
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
                    increasing_line_color="#00d09c", decreasing_line_color="#ff4d6d",
                ), row=1, col=1)

                # Moving averages
                for ma, color, label in [("MA20", "#5b8dee", "MA20"), ("MA50", "#f0b429", "MA50"), ("MA200", "#ff4d6d", "MA200")]:
                    if ma in hist.columns:
                        fig.add_trace(go.Scatter(x=hist.index, y=hist[ma], name=label,
                                                 line=dict(color=color, width=1.2)), row=1, col=1)

                # Bollinger
                fig.add_trace(go.Scatter(x=hist.index, y=hist["BB_upper"], name="BB Upper",
                                         line=dict(color="#8892a4", width=0.8, dash="dot")), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist["BB_lower"], name="BB Lower",
                                         line=dict(color="#8892a4", width=0.8, dash="dot"),
                                         fill="tonexty", fillcolor="rgba(136,146,164,0.05)"), row=1, col=1)

                # Volume
                colors = ["#00d09c" if c >= o else "#ff4d6d"
                          for c, o in zip(hist["Close"], hist["Open"])]
                fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], name="Volume",
                                     marker_color=colors, opacity=0.6), row=2, col=1)

                # RSI
                fig.add_trace(go.Scatter(x=hist.index, y=hist["RSI"], name="RSI",
                                         line=dict(color="#c77dff", width=1.5)), row=3, col=1)
                fig.add_hline(y=70, line_dash="dot", line_color="#ff4d6d", row=3, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="#00d09c", row=3, col=1)

                fig.update_layout(
                    height=700, template="plotly_dark",
                    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
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
                sc_color = "#00d09c" if sc >= 65 else ("#f0b429" if sc >= 45 else "#ff4d6d")
                st.markdown(f"""
<div style='background:#1c1f2e;border-radius:12px;padding:20px;border:1px solid {sc_color};margin-bottom:20px'>
    <span style='font-size:1.4rem;font-weight:800;color:{sc_color}'>{sent["overall"]}</span>
    <span style='color:#8892a4;margin-left:16px'>Score sentiment: <b style='color:#e0e6f0'>{sc}/100</b></span>
    <div style='background:#2d3147;border-radius:4px;height:8px;margin-top:10px'>
        <div style='background:{sc_color};width:{sc}%;height:8px;border-radius:4px'></div>
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
                            up_col = "#00d09c" if an["upside"] > 0 else "#ff4d6d"
                            st.markdown(f"Upside da consensus: <span style='color:{up_col}'><b>{an['upside']}%</b></span>", unsafe_allow_html=True)
                    st.divider()

                    # Short interest
                    sh = sent["short"]
                    st.markdown("**🩳 Short Interest**")
                    if sh.get("short_pct"):
                        sh_col = "#ff4d6d" if sh["short_pct"] > 15 else ("#f0b429" if sh["short_pct"] > 8 else "#00d09c")
                        st.markdown(f"<span style='color:{sh_col}'>{sh['short_pct']}% delle azioni shortate</span>", unsafe_allow_html=True)
                        if sh.get("short_ratio"): st.markdown(f"Days to cover: {sh['short_ratio']} giorni")
                        if sh.get("change_pct"):
                            ch_col = "#ff4d6d" if sh["change_pct"] > 0 else "#00d09c"
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
                            c = "#00d09c" if s > 0 else "#ff4d6d"
                            cols_ea[i].markdown(f"<div style='text-align:center;color:{c}'><b>{s:+.1f}%</b><br><small>Q{i+1}</small></div>", unsafe_allow_html=True)
                    if ea.get("next_earnings"): st.markdown(f"Prossimi earnings: **{ea['next_earnings']}**")
                    st.divider()

                    # Reddit
                    rd = sent["reddit"]
                    st.markdown("**💬 Reddit Mentions**")
                    st.markdown(rd.get("label","N/A"))
                    if rd.get("posts"):
                        for p in rd["posts"][:3]:
                            rc = "#00d09c" if p["sentiment"] > 0.05 else ("#ff4d6d" if p["sentiment"] < -0.05 else "#8892a4")
                            st.markdown(f"<span style='color:{rc}'>●</span> <small>[{p['title']}]({p['url']}) r/{p['subreddit']}</small>", unsafe_allow_html=True)

                st.divider()
                # News
                st.markdown("**📰 News recenti**")
                news = sent["news"]
                for art in news.get("articles", []):
                    nc = "#00d09c" if art["score"] > 0.05 else ("#ff4d6d" if art["score"] < -0.05 else "#8892a4")
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
                        signal_color = "#00d09c" if "BUY" in data["signal"] else ("#f0b429" if "HOLD" in data["signal"] else "#ff4d6d")
                        st.markdown(f"""
<div style='background:#1c1f2e;border-radius:12px;padding:24px;border:1px solid {signal_color};margin-top:8px;color:#e0e6f0;line-height:1.7'>
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
            st.success(f"✅ Trovati {len(df)} titoli con score ≥ {min_score}")

            # Color score column
            def color_signal(val):
                if "BUY" in str(val): return "color: #00d09c; font-weight: bold"
                if "HOLD" in str(val): return "color: #f0b429"
                return "color: #ff4d6d"

            def color_score(val):
                if isinstance(val, (int, float)):
                    if val >= 65: return "background-color: #003d2e; color: #00d09c"
                    if val >= 50: return "background-color: #2d2200; color: #f0b429"
                    return "background-color: #2d0010; color: #ff4d6d"
                return ""

            styled = df.style.map(color_signal, subset=["Segnale"]).map(color_score, subset=["Score"])

            st.dataframe(styled, use_container_width=True, height=500)

            # Download CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Scarica CSV", csv, "screener_risultati.csv", "text/csv")

            # Quick chart of top 5
            st.subheader("Top 5 per Score")
            top5 = df.head(5)
            import plotly.express as px
            fig = px.bar(
                top5, x="Ticker", y="Score",
                color="Score", color_continuous_scale=["#ff4d6d", "#f0b429", "#00d09c"],
                text="Score", template="plotly_dark",
            )
            fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                              showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)


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
            if score <= 25: color = "#ff4d6d"; emoji = "😱 Extreme Fear"
            elif score <= 45: color = "#f0b429"; emoji = "😟 Fear"
            elif score <= 55: color = "#8892a4"; emoji = "😐 Neutral"
            elif score <= 75: color = "#5b8dee"; emoji = "😊 Greed"
            else: color = "#00d09c"; emoji = "🤑 Extreme Greed"

            st.markdown(f"""
            <div style='background:#1c1f2e;border-radius:12px;padding:24px;text-align:center;border:1px solid {color}'>
                <div style='font-size:3rem;font-weight:900;color:{color}'>{score}</div>
                <div style='font-size:1.2rem;color:#e0e6f0;margin-top:8px'>{emoji}</div>
                <div style='background:#2d3147;border-radius:4px;height:10px;margin-top:16px'>
                    <div style='background:{color};width:{score}%;height:10px;border-radius:4px'></div>
                </div>
                <div style='display:flex;justify-content:space-between;color:#8892a4;font-size:0.75rem;margin-top:4px'>
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
            vcolor = "#00d09c" if vix < 15 else ("#f0b429" if vix < 25 else "#ff4d6d")
            st.markdown(f"""
            <div style='background:#1c1f2e;border-radius:12px;padding:24px;text-align:center;border:1px solid {vcolor}'>
                <div style='font-size:3rem;font-weight:900;color:{vcolor}'>{vix}</div>
                <div style='font-size:1.1rem;color:#e0e6f0;margin-top:8px'>{macro["vix_label"]}</div>
                <div style='color:#8892a4;font-size:0.85rem;margin-top:12px'>
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
                sc = "#00d09c" if score_val > 0.05 else ("#ff4d6d" if score_val < -0.05 else "#8892a4")
                st.markdown(f"""
                <div style='background:#1c1f2e;border-radius:10px;padding:16px;border:1px solid {sc};margin-bottom:12px'>
                    <b style='color:#e0e6f0'>{t}</b><br>
                    <span style='color:{sc};font-size:1.1rem'>{s['label']}</span>
                    <span style='color:#8892a4;font-size:0.85rem'> ({score_val})</span>
                </div>
                """, unsafe_allow_html=True)
                for art in s["articles"][:3]:
                    ac = "#00d09c" if art["score"] > 0.05 else ("#ff4d6d" if art["score"] < -0.05 else "#8892a4")
                    st.markdown(f"<span style='color:{ac}'>●</span> [{art['title'][:60]}...]({art['url']})",
                                unsafe_allow_html=True)
