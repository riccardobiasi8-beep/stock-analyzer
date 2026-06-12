"""
Data Enricher — cascata fonti gratuite per completare dati mancanti da Yahoo.
Tier 1: yfinance bilanci grezzi (sempre gratis)
Tier 2: Alpha Vantage (25 req/giorno gratis)
"""
import requests
import traceback


# ── Tier 1: yfinance bilanci grezzi ──────────────────────────────────────────

def enrich_from_yfinance_statements(ticker_obj, data: dict) -> dict:
    """Calcola fondamentali direttamente dai bilanci yfinance."""
    try:
        info = ticker_obj.info or {}
        fin = ticker_obj.financials
        bal = ticker_obj.balance_sheet
        price = data.get('current_price') or 1

        def _get(df, *keys):
            if df is None or df.empty:
                return None
            for k in keys:
                try:
                    row = df.loc[k]
                    val = row.iloc[0]
                    if val is not None and str(val) not in ('nan', 'None'):
                        return float(val)
                except Exception:
                    continue
            return None

        # ROE = Net Income / Stockholders Equity
        if data.get('roe') is None:
            net_income = _get(fin, 'Net Income', 'NetIncome')
            equity = _get(bal, 'Stockholders Equity', 'StockholdersEquity',
                         'Total Stockholder Equity')
            if net_income and equity and equity != 0:
                data['roe'] = round(net_income / equity * 100, 2)

        # Profit Margin = Net Income / Revenue
        if data.get('profit_margin') is None:
            net_income = _get(fin, 'Net Income', 'NetIncome')
            revenue = _get(fin, 'Total Revenue', 'TotalRevenue')
            if net_income and revenue and revenue != 0:
                data['profit_margin'] = round(net_income / revenue * 100, 2)

        # Revenue Growth YoY
        if data.get('revenue_growth') is None:
            try:
                if fin is not None and not fin.empty and fin.shape[1] >= 2:
                    r0 = float(fin.loc['Total Revenue'].iloc[0])
                    r1 = float(fin.loc['Total Revenue'].iloc[1])
                    if r1 and r1 != 0:
                        data['revenue_growth'] = round((r0 - r1) / abs(r1) * 100, 2)
            except Exception:
                pass

        # Debt/Equity
        if data.get('debt_equity') is None:
            total_debt = _get(bal, 'Total Debt', 'TotalDebt',
                             'Long Term Debt', 'LongTermDebt')
            equity = _get(bal, 'Stockholders Equity', 'StockholdersEquity')
            if total_debt is not None and equity and equity != 0:
                data['debt_equity'] = round(total_debt / equity, 2)

        # P/E from EPS
        if data.get('pe') is None:
            eps = info.get('trailingEps') or info.get('forwardEps')
            if eps and eps > 0 and price > 0:
                data['pe'] = round(price / eps, 1)

        # P/B from book value
        if data.get('pb') is None:
            bvps = info.get('bookValue')
            if bvps and bvps > 0 and price > 0:
                data['pb'] = round(price / bvps, 2)

        # Beta
        if data.get('beta') is None:
            beta = info.get('beta')
            if beta:
                data['beta'] = round(float(beta), 2)

        # Dividend Yield
        if data.get('dividend_yield') is None:
            dy = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
            if dy:
                data['dividend_yield'] = round(float(dy) * 100, 2)

        filled = [k for k in ['pe','pb','roe','profit_margin','revenue_growth',
                               'debt_equity','beta','dividend_yield'] if data.get(k) is not None]
        if filled:
            print(f"[Enricher T1] Filled from statements: {filled}")

    except Exception as e:
        print(f"[Enricher T1] Error: {e}")

    return data


# ── Tier 2: Alpha Vantage ─────────────────────────────────────────────────────

def enrich_from_alpha_vantage(ticker_sym: str, data: dict, av_key: str) -> dict:
    """Fill missing fields from Alpha Vantage (25 req/day free)."""
    if not av_key:
        return data

    missing = [k for k in ['pe','pb','ev_ebitda','roe','profit_margin',
                            'revenue_growth','debt_equity','beta','dividend_yield']
               if data.get(k) is None]
    if not missing:
        print("[Enricher T2] All fields present, skipping AV")
        return data

    try:
        # Alpha Vantage works better without exchange suffix for most tickers
        sym = ticker_sym.split('.')[0] if '.' in ticker_sym else ticker_sym

        url = (f"https://www.alphavantage.co/query"
               f"?function=OVERVIEW&symbol={sym}&apikey={av_key}")
        r = requests.get(url, timeout=12)

        if r.status_code != 200:
            print(f"[Enricher T2] AV HTTP {r.status_code}")
            return data

        d = r.json()

        # AV returns {"Information": "..."} when rate limited
        if 'Information' in d or 'Note' in d:
            print(f"[Enricher T2] AV rate limited: {d.get('Information') or d.get('Note','')[:60]}")
            return data

        if not d or 'Symbol' not in d:
            print(f"[Enricher T2] AV no data for {sym}")
            return data

        def _safe(key, multiplier=1.0, as_pct=False):
            v = d.get(key)
            if v and v not in ('None', '-', '', 'N/A', '0'):
                try:
                    val = float(v) * multiplier
                    if as_pct and abs(val) <= 1.0:
                        val = val * 100  # convert decimal to percent
                    return round(val, 2)
                except Exception:
                    pass
            return None

        av_map = {
            'pe':             _safe('PERatio'),
            'pb':             _safe('PriceToBookRatio'),
            'ev_ebitda':      _safe('EVToEBITDA'),
            'roe':            _safe('ReturnOnEquityTTM', as_pct=True),
            'profit_margin':  _safe('ProfitMargin', as_pct=True),
            'beta':           _safe('Beta'),
            'dividend_yield': _safe('DividendYield', as_pct=True),
            'revenue_growth': _safe('QuarterlyRevenueGrowthYOY', as_pct=True),
        }

        filled = []
        for field, val in av_map.items():
            if data.get(field) is None and val is not None:
                data[field] = val
                filled.append(f"{field}={val}")

        if filled:
            print(f"[Enricher T2] AV filled: {filled}")
        else:
            print(f"[Enricher T2] AV: no new fields filled")

    except Exception as e:
        print(f"[Enricher T2] Error: {e}")

    return data


# ── Main entry point ──────────────────────────────────────────────────────────

def enrich_stock_data(ticker_obj, ticker_sym: str, data: dict,
                      fmp_key: str = "", av_key: str = "") -> dict:
    """
    Run enrichment tiers in order, stop when all fields are filled.
    fmp_key is accepted but ignored (not implemented — use AV only).
    """
    fields = ['pe','pb','ev_ebitda','roe','profit_margin',
              'revenue_growth','debt_equity','beta','dividend_yield']

    def _missing():
        return [k for k in fields if data.get(k) is None]

    before = _missing()
    if not before:
        return data

    print(f"[Enricher] {ticker_sym} — missing before: {before}")

    # Tier 1: yfinance statements (always free, no API key needed)
    data = enrich_from_yfinance_statements(ticker_obj, data)

    # Tier 2: Alpha Vantage (25/day free)
    if _missing() and av_key:
        data = enrich_from_alpha_vantage(ticker_sym, data, av_key)

    after = _missing()
    print(f"[Enricher] {ticker_sym} — still missing after: {after}")
    return data
