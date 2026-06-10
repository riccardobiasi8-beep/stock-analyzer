import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from modules.analyzer import get_stock_data
from modules.screener import run_screener, MARKET_GROUPS
from modules.sentiment import get_fear_greed, get_news_sentiment, get_macro_context

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
        ticker_input = st.text_input(
            "Ticker",
            placeholder="es. AAPL · NVDA · ENI.MI · SAP.DE · RACE.MI",
            label_visibility="collapsed",
        ).upper().strip()
    with col_period:
        period = st.selectbox("Periodo", ["6mo", "1y", "2y", "5y"], index=1, label_visibility="collapsed")

    if ticker_input:
        with st.spinner(f"Carico dati per {ticker_input}..."):
            data = get_stock_data(ticker_input, period=period)

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
                sentiment = get_news_sentiment(ticker_input)
                st.subheader(f"Sentiment news: {sentiment['label']} (score: {sentiment['score']})")
                for art in sentiment["articles"]:
                    color = "#00d09c" if art["score"] > 0.05 else ("#ff4d6d" if art["score"] < -0.05 else "#8892a4")
                    st.markdown(f"<span style='color:{color}'>●</span> [{art['title']}]({art['url']}) · *{art['publisher']}*",
                                unsafe_allow_html=True)


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

        if df.empty:
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

          styled = df.style.map(color_signal, subset=["Segnale"]) \
                 .map(color_score, subset=["Score"])
        
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
