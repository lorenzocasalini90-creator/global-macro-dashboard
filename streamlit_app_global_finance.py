import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from pandas.tseries.offsets import DateOffset
import html as _html

# ============================================================
# SAFE HTML ESCAPE (for any string injected into HTML)
# ============================================================

def h(x) -> str:
    if x is None:
        return ""
    return _html.escape(str(x), quote=True)

# ============================================================
# HTML RENDER (ROBUST: avoids "HTML printed as text")
# ============================================================

def render_html(fragment: str, height: int | None = None, scrolling: bool = False):
    """
    Robust HTML renderer. Using components.html prevents Streamlit
    from accidentally escaping HTML in some contexts.
    """
    frag = fragment.strip()
    doc = f"""
    <div class="stHtmlRoot">
      {frag}
    </div>
    """
    components.html(doc, height=height or 180, scrolling=scrolling)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Global finance | Macro overview",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>
  :root{
    --bg:#0b0f19;
    --card:#0f1629;
    --border:rgba(255,255,255,0.10);
    --muted:rgba(255,255,255,0.72);
    --text:rgba(255,255,255,0.95);

    --good:rgba(34,197,94,1);
    --warn:rgba(245,158,11,1);
    --bad:rgba(239,68,68,1);

    --accent:rgba(244,63,94,1);
    --accentSoft:rgba(244,63,94,0.18);
  }

  .stApp {
    background: radial-gradient(1200px 700px at 20% 0%, #121a33 0%, #0b0f19 45%, #0b0f19 100%);
    color: var(--text);
  }

  .block-container { padding-top: 1.0rem; padding-bottom: 2.0rem; }
  h1, h2, h3, h4 { color: var(--text); letter-spacing: -0.02em; }
  .muted { color: var(--muted); }

  /* Tabs */
  button[data-baseweb="tab"]{
    color: rgba(255,255,255,0.92) !important;
    font-weight: 750 !important;
    background: rgba(255,255,255,0.04) !important;
    border-radius: 10px !important;
    margin-right: 6px !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
  }
  button[data-baseweb="tab"][aria-selected="true"]{
    color: rgba(255,255,255,0.98) !important;
    background: var(--accentSoft) !important;
    border: 1px solid rgba(244,63,94,0.55) !important;
  }

  /* Buttons */
  .stButton > button{
    background: rgba(255,255,255,0.10) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: rgba(255,255,255,0.95) !important;
    border-radius: 12px !important;
    font-weight: 800 !important;
  }
  .stButton > button:hover{
    background: rgba(255,255,255,0.14) !important;
    border: 1px solid rgba(255,255,255,0.26) !important;
  }

  /* Expander */
  div[data-testid="stExpander"]{
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    background: rgba(255,255,255,0.03) !important;
    overflow: hidden !important;
  }
  div[data-testid="stExpander"] summary{
    background: rgba(255,255,255,0.05) !important;
    color: rgba(255,255,255,0.92) !important;
    padding: 10px 12px !important;
  }

  /* Cards */
  .card{
    background: linear-gradient(180deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.03) 100%);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 16px 16px 14px 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  }
  .cardTitle{ font-size: 0.95rem; color: var(--muted); margin-bottom: 6px; }
  .cardValue{ font-size: 2.1rem; font-weight: 820; line-height: 1.05; color: var(--text); }
  .cardSub{ margin-top: 8px; font-size: 0.98rem; color: var(--muted); }

  .grid3{ display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
  .grid2{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
  @media (max-width: 1100px){
    .grid3{ grid-template-columns: repeat(1, minmax(0, 1fr)); }
    .grid2{ grid-template-columns: repeat(1, minmax(0, 1fr)); }
  }

  /* Pills */
  .pill{
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding: 5px 12px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: rgba(255,255,255,0.04);
    font-size: 0.88rem;
    color: var(--text);
    white-space: nowrap;
  }
  .dot{ width: 11px; height: 11px; border-radius: 999px; display:inline-block; }
  .pill.good{ border-color: rgba(34,197,94,0.45); background: rgba(34,197,94,0.12); }
  .pill.warn{ border-color: rgba(245,158,11,0.45); background: rgba(245,158,11,0.12); }
  .pill.bad { border-color: rgba(239,68,68,0.45); background: rgba(239,68,68,0.12); }

  /* Section wrapper */
  .section{
    background: rgba(255,255,255,0.025);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 14px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.20);
    margin-bottom: 14px;
  }
  .sectionHead{ display:flex; align-items:baseline; justify-content:space-between; gap: 12px; margin-bottom: 10px; flex-wrap:wrap; }
  .sectionTitle{ font-size: 1.15rem; font-weight: 860; color: rgba(255,255,255,0.96); }
  .sectionDesc{ font-size: 0.95rem; color: var(--muted); margin-top: 2px; }

  /* Wallboard tiles grid */
  .wbGrid{
    display:grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }
  @media (max-width: 1200px){
    .wbGrid{ grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  @media (max-width: 700px){
    .wbGrid{ grid-template-columns: repeat(1, minmax(0, 1fr)); }
  }

  .wbTile{
    background: rgba(255,255,255,0.028);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 14px 14px 12px 14px;
    box-shadow: 0 10px 26px rgba(0,0,0,0.18);
    min-height: 156px;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
  }
  .wbName{ font-size: 0.98rem; font-weight: 860; color: rgba(255,255,255,0.96); margin-bottom: 2px; }
  .wbMeta{ font-size: 0.86rem; color: var(--muted); margin-bottom: 8px; }
  .wbRow{ display:flex; align-items:baseline; justify-content:space-between; gap: 10px; }
  .wbVal{ font-size: 1.65rem; font-weight: 900; letter-spacing:-0.01em; }
  .wbSmall{ font-size: 0.88rem; color: var(--muted); }
  .wbFoot{ display:flex; align-items:center; justify-content:space-between; gap: 10px; margin-top: 10px; }

  /* Score bar */
  .barWrap{
    height: 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.08);
    position: relative;
    overflow:hidden;
  }
  .barFill{
    height: 100%;
    border-radius: 999px;
    background: rgba(255,255,255,0.14);
    width: 100%;
    opacity: 0.55;
  }
  .barMark{
    position:absolute;
    top:-4px;
    width: 3px;
    height: 18px;
    border-radius: 2px;
    background: rgba(255,255,255,0.92);
    box-shadow: 0 0 0 2px rgba(0,0,0,0.20);
  }

  .alertRow{
    display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;
    padding: 10px 12px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.03);
    margin-bottom: 8px;
  }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# META
# ============================================================

INDICATOR_META = {
    "real_10y": {"label": "US 10Y TIPS Real Yield","unit": "%","direction": -1,"source": "FRED DFII10","scale": 1.0,"ref_line": 0.0,"scoring_mode": "z5y","move_mode": "abs","hot_threshold_30d": 0.25,"hot_threshold_1q": 0.35,
        "expander": {"what": "Real yield (10Y TIPS): the real price of money/time.","reference": "<0% very easy; 0–2% neutral; >2% restrictive (heuristics).","interpretation": "- Higher real yields tighten financial conditions; pressure long-duration assets.\n- Lower real yields typically support risk assets and duration.","bridge": "Higher real yields raise real funding constraints across the system."}},
    "nominal_10y": {"label": "US 10Y Nominal Yield","unit": "%","direction": -1,"source": "FRED DGS10","scale": 1.0,"ref_line": None,"scoring_mode": "z5y","move_mode": "abs","hot_threshold_30d": 0.25,"hot_threshold_1q": 0.35,
        "expander": {"what": "Nominal 10Y Treasury yield: benchmark discount rate and broad tightening proxy.","reference": "Fast upside moves often behave like tightening (heuristics).","interpretation": "- Yield up fast = pressure on equities and existing bonds.\n- Yield down can support duration and (sometimes) equities depending on growth/inflation mix.","bridge": "Higher yields mean the market demands more compensation (inflation and/or term premium)."}},
    "yield_curve_10_2": {"label": "US Yield Curve (10Y–2Y)","unit": "pp","direction": +1,"source": "FRED DGS10 - DGS2","scale": 1.0,"ref_line": 0.0,"scoring_mode": "z5y","move_mode": "abs","hot_threshold_30d": 0.25,"hot_threshold_1q": 0.35,
        "expander": {"what": "10Y–2Y slope: cycle / recession-probability proxy.","reference": "<0 inverted (late-cycle); >0 normal (heuristics).","interpretation": "- Deep/persistent inversion = late-cycle risk.\n- Steepening back above 0 = normalization (often after easing).","bridge": "Inversion = policy tight vs cycle, raising deleveraging risk."}},
    "breakeven_10y": {"label": "10Y Breakeven Inflation","unit": "%","direction": -1,"source": "FRED T10YIE","scale": 1.0,"ref_line": 2.5,"scoring_mode": "z5y","move_mode": "abs","hot_threshold_30d": 0.12,"hot_threshold_1q": 0.18,
        "expander": {"what": "Market-implied inflation expectations (10Y).","reference": "~2–3% anchored; materially >3% = sticky risk (heuristics).","interpretation": "- Higher breakevens reduce easing room.\n- Lower/anchoring supports duration and risk budgeting.","bridge": "Higher expected inflation raises the odds of inflation-tolerant policy in stress."}},
    "cpi_yoy": {"label": "US CPI YoY","unit": "%","direction": -1,"source": "FRED CPIAUCSL (computed YoY)","scale": 1.0,"ref_line": 3.0,"scoring_mode": "z5y","move_mode": "abs","hot_threshold_30d": 0.15,"hot_threshold_1q": 0.25,
        "expander": {"what": "Headline inflation YoY (proxy).","reference": "2% is target; >3–4% persistent = sticky risk (heuristics).","interpretation": "- Disinflation supports duration and often equities.\n- Re-acceleration pushes 'higher-for-longer' risks.","bridge": "Persistent inflation becomes the binding policy constraint."}},
    "unemployment_rate": {"label": "US Unemployment Rate","unit": "%","direction": -1,"source": "FRED UNRATE","scale": 1.0,"ref_line": None,"scoring_mode": "z5y","move_mode": "abs","hot_threshold_30d": 0.20,"hot_threshold_1q": 0.30,
        "expander": {"what": "Labor slack proxy.","reference": "Rapid rises often coincide with growth downshift (heuristics).","interpretation": "- Unemployment rising quickly tends to be risk-off.\n- Stable unemployment is typically benign.","bridge": "Slack + high debt raises pressure for policy support (fiscal/monetary)."}},
    "usd_index": {"label": "USD Index (DXY / Broad Proxy)","unit": "","direction": -1,"source": "yfinance DX-Y.NYB (fallback FRED DTWEXBGS)","scale": 1.0,"ref_line": None,"scoring_mode": "z5y","move_mode": "pct","hot_threshold_30d": 2.5,"hot_threshold_1q": 3.5,
        "expander": {"what": "USD strength proxy. If DXY is unavailable, uses broad trade-weighted USD index.","reference": "USD up = tighter global conditions (heuristics).","interpretation": "- USD stronger tightens global funding.\n- USD weaker loosens conditions.","bridge": "Stronger USD increases global funding stress where liabilities are USD-linked."}},
    "hy_oas": {"label": "US High Yield OAS","unit": "pp","direction": -1,"source": "FRED BAMLH0A0HYM2","scale": 1.0,"ref_line": 4.5,"scoring_mode": "z5y","move_mode": "abs","hot_threshold_30d": 0.50,"hot_threshold_1q": 0.80,
        "expander": {"what": "High-yield credit spread: credit stress / default premium proxy.","reference": "<4% often benign; >6–7% stress (heuristics).","interpretation": "- Spreads widening = risk-off.\n- Tight spreads = risk appetite.","bridge": "Credit stress can accelerate non-linear deleveraging dynamics."}},
    "vix": {"label": "VIX","unit": "","direction": -1,"source": "yfinance ^VIX","scale": 1.0,"ref_line": 20.0,"scoring_mode": "z5y","move_mode": "pct","hot_threshold_30d": 25.0,"hot_threshold_1q": 30.0,
        "expander": {"what": "Equity implied volatility (S&P 500).","reference": "<15 low; 15–25 normal; >25 stress (heuristics).","interpretation": "- Higher vol tightens conditions through risk premia.\n- Lower vol often supports risk-taking.","bridge": "Vol spikes tighten conditions even without rate hikes."}},
    "spy_trend": {"label": "SPY Trend (SPY / 200D MA)","unit": "ratio","direction": +1,"source": "yfinance SPY","scale": 1.0,"ref_line": 1.0,"scoring_mode": "z5y","move_mode": "abs","hot_threshold_30d": 0.03,"hot_threshold_1q": 0.04,
        "expander": {"what": "Simple trend proxy: SPY vs 200-day moving average.","reference": ">1 = uptrend; <1 = downtrend (heuristics).","interpretation": "- Above 1 supports risk-on behavior.\n- Below 1 signals risk-off trend regime.","bridge": "Trend down + credit stress up is a common deleveraging signature."}},
    "hyg_lqd_ratio": {"label": "Credit Risk Appetite (HYG / LQD)","unit": "ratio","direction": +1,"source": "yfinance HYG, LQD","scale": 1.0,"ref_line": None,"scoring_mode": "z5y","move_mode": "abs","hot_threshold_30d": 0.02,"hot_threshold_1q": 0.03,
        "expander": {"what": "High yield vs investment grade ratio: credit risk appetite proxy.","reference": "Ratio up = more HY appetite; down = flight to quality.","interpretation": "- Rising ratio is typically risk-on.\n- Falling ratio indicates quality bid / caution.","bridge": "Flight-to-quality signals tightening funding constraints."}},
    "fed_balance_sheet": {"label": "Fed Balance Sheet (WALCL)","unit": "bn USD","direction": +1,"source": "FRED WALCL (millions -> bn)","scale": 1.0/1000.0,"ref_line": None,"scoring_mode": "z5y","move_mode": "pct","hot_threshold_30d": 1.0,"hot_threshold_1q": 1.5,
        "expander": {"what": "Total Fed assets: system liquidity proxy.","reference": "Expansion (QE) often supports risk assets; contraction (QT) drains (heuristics).","interpretation": "- Balance sheet up = tailwind.\n- Balance sheet down = headwind.","bridge": "Liquidity plumbing determines whether flows support or drain risk assets."}},
    "rrp": {"label": "Fed Overnight RRP","unit": "bn USD","direction": -1,"source": "FRED RRPONTSYD","scale": 1.0,"ref_line": 0.0,"scoring_mode": "z5y","move_mode": "pct","hot_threshold_30d": 25.0,"hot_threshold_1q": 35.0,
        "expander": {"what": "Overnight reverse repo usage: cash parked in risk-free facility.","reference": "High RRP = liquidity 'stuck'; falling RRP can release marginal liquidity (heuristics).","interpretation": "- RRP up = less marginal liquidity for risk.\n- RRP down = potential tailwind.","bridge": "RRP declines can act as a tactical liquidity release valve."}},
    "interest_payments": {"label": "US Federal Interest Payments (Quarterly)","unit": "bn USD","direction": -1,"source": "FRED A091RC1Q027SBEA","scale": 1.0,"ref_line": None,"scoring_mode": "pct20y","move_mode": "pct","hot_threshold_30d": 2.0,"hot_threshold_1q": 3.0,
        "expander": {"what": "Government interest expense: debt-service pressure proxy.","reference": "Rising/accelerating debt service reduces policy flexibility (heuristics).","interpretation": "- Persistent rise increases policy constraint.\n- Stabilization reduces constraint.","bridge": "Debt service pressure increases incentives for funding-friendly policy outcomes."}},
    "federal_receipts": {"label": "US Federal Current Receipts (Quarterly)","unit": "bn USD","direction": +1,"source": "FRED FGRECPT","scale": 1.0,"ref_line": None,"scoring_mode": "pct20y","move_mode": "pct","hot_threshold_30d": 2.0,"hot_threshold_1q": 3.0,
        "expander": {"what": "Government receipts: supports debt-service capacity.","reference": "Used to compute interest/receipts sustainability proxy.","interpretation": "- Receipts up improves capacity (all else equal).\n- Receipts down tightens constraint.","bridge": "Higher receipts reduce the binding nature of debt service."}},
    "interest_to_receipts": {"label": "Debt Service Stress (Interest / Receipts)","unit": "ratio","direction": -1,"source": "Derived","scale": 1.0,"ref_line": None,"scoring_mode": "pct20y","move_mode": "abs","hot_threshold_30d": 0.008,"hot_threshold_1q": 0.010,
        "expander": {"what": "Sustainability proxy: share of receipts consumed by interest expense.","reference": "High and rising = constraint becomes political (heuristics).","interpretation": "- Higher ratio signals tighter fiscal policy constraint.\n- Lower ratio signals more room.","bridge": "Higher debt service increases incentives for inflation-tolerant or funding-friendly policy."}},
    "deficit_gdp": {"label": "Federal Surplus/Deficit (% of GDP)","unit": "%","direction": -1,"source": "FRED FYFSGDA188S","scale": 1.0,"ref_line": -3.0,"scoring_mode": "pct20y","move_mode": "abs","hot_threshold_30d": 0.5,"hot_threshold_1q": 0.7,
        "expander": {"what": "Fiscal balance (% of GDP). Negative = deficit.","reference": "Persistent large deficits increase Treasury supply pressure (heuristics).","interpretation": "- More negative implies more supply/funding pressure.\n- Improvement reduces pressure.","bridge": "Supply pressure can show up as higher term premium and weaker duration hedge behavior."}},
    "term_premium_10y": {"label": "US 10Y Term Premium (ACM)","unit": "%","direction": -1,"source": "FRED ACMTP10","scale": 1.0,"ref_line": None,"scoring_mode": "pct20y","move_mode": "abs","hot_threshold_30d": 0.25,"hot_threshold_1q": 0.35,
        "expander": {"what": "Term premium: compensation required to hold nominal duration.","reference": "Rising term premium makes long nominal bonds less reliable as a hedge (heuristics).","interpretation": "- Term premium up increases duration risk.\n- Term premium down restores hedge quality.","bridge": "If term premium rises from supply/funding, duration may stop hedging equity drawdowns."}},
    "current_account_gdp": {"label": "US Current Account Balance (% of GDP)","unit": "%","direction": +1,"source": "FRED USAB6BLTT02STSAQ","scale": 1.0,"ref_line": 0.0,"scoring_mode": "pct20y","move_mode": "abs","hot_threshold_30d": 0.35,"hot_threshold_1q": 0.50,
        "expander": {"what": "External funding constraint proxy. Negative = reliance on foreign capital.","reference": "More negative implies higher vulnerability during USD tightening (heuristics).","interpretation": "- More negative increases dependence on external funding.\n- Moving toward 0 reduces constraint.","bridge": "External deficits increase vulnerability when global USD funding tightens."}},
    "gold": {"label": "Gold (GLD)","unit": "","direction": -1,"source": "yfinance GLD","scale": 1.0,"ref_line": None,"scoring_mode": "z5y","move_mode": "pct","hot_threshold_30d": 6.0,"hot_threshold_1q": 8.0,
        "expander": {"what": "Gold: hedge demand proxy (policy/inflation/tail risk).","reference": "Breakouts often reflect hedge demand rather than growth optimism (heuristics).","interpretation": "- Gold up can signal hedge demand.\n- Gold down in equity bull may reflect clean risk-on.","bridge": "Gold can hedge environments where real returns are compressed or policy turns funding-friendly."}},
}

BLOCKS = {
    "price_of_time": {"name": "1) Price of Time","weight": 0.20,"indicators": ["real_10y", "nominal_10y", "yield_curve_10_2"],"desc": "Rates / curve: the price of time and late-cycle signal.","group": "Market Thermometers"},
    "macro": {"name": "2) Macro Cycle","weight": 0.15,"indicators": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],"desc": "Inflation and growth constraint on policy reaction.","group": "Market Thermometers"},
    "conditions": {"name": "3) Conditions & Stress","weight": 0.20,"indicators": ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"],"desc": "Fast regime: USD, credit stress, vol, trend, risk appetite.","group": "Market Thermometers"},
    "plumbing": {"name": "4) Liquidity / Plumbing","weight": 0.15,"indicators": ["fed_balance_sheet", "rrp"],"desc": "System liquidity tailwind vs drain for risk assets.","group": "Market Thermometers"},
    "policy_link": {"name": "5) Fiscal / Policy Constraint","weight": 0.20,"indicators": ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"],"desc": "Debt service, deficit dynamics, and the funding constraint signal.","group": "Structural Constraints"},
    "external": {"name": "6) External Balance","weight": 0.10,"indicators": ["current_account_gdp"],"desc": "External funding reliance and vulnerability in USD tightening.","group": "Structural Constraints"},
    "gold_block": {"name": "7) Gold","weight": 0.00,"indicators": ["gold"],"desc": "Policy / tail-risk hedge demand confirmation.","group": "Structural Constraints"},
}

# ============================================================
# DATA FETCHERS
# ============================================================

def get_fred_api_key():
    try:
        return st.secrets["FRED_API_KEY"]
    except Exception:
        return None

@st.cache_data(ttl=3600)
def fetch_fred_series(series_id: str, start_date: str) -> pd.Series:
    api_key = get_fred_api_key()
    if api_key is None:
        return pd.Series(dtype=float)

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        data = r.json().get("observations", [])
        if not data:
            return pd.Series(dtype=float)
        idx = pd.to_datetime([o["date"] for o in data])
        vals = []
        for o in data:
            try:
                vals.append(float(o["value"]))
            except Exception:
                vals.append(np.nan)
        return pd.Series(vals, index=idx).replace({".": np.nan}).astype(float).sort_index()
    except Exception:
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600)
def fetch_yf_one(ticker: str, start_date: str) -> pd.Series:
    try:
        df = yf.Ticker(ticker).history(start=start_date, auto_adjust=True)
        if df is None or df.empty:
            return pd.Series(dtype=float)
        col = "Close"
        if "Adj Close" in df.columns:
            col = "Adj Close"
        s = df[col].dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None) if getattr(s.index, "tz", None) else pd.to_datetime(s.index)
        return s
    except Exception:
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600)
def fetch_yf_many(tickers: list[str], start_date: str) -> dict:
    return {t: fetch_yf_one(t, start_date) for t in tickers}

# ============================================================
# SCORING
# ============================================================

def rolling_percentile_last(hist: pd.Series, latest: float) -> float:
    hst = hist.dropna()
    if len(hst) < 10 or pd.isna(latest):
        return np.nan
    return float((hst <= latest).mean())

def compute_indicator_score(series: pd.Series, direction: int, scoring_mode: str = "z5y"):
    if series is None or series.empty:
        return np.nan, np.nan, np.nan
    s = series.dropna()
    if len(s) < 20:
        return np.nan, np.nan, (np.nan if s.empty else float(s.iloc[-1]))

    latest = float(s.iloc[-1])
    end = s.index.max()

    if scoring_mode == "pct20y":
        start = end - DateOffset(years=20)
        hist = s[s.index >= start]
        if len(hist) < 20:
            hist = s
        p = rolling_percentile_last(hist, latest)
        sig = (p - 0.5) * 4.0
    else:
        start = end - DateOffset(years=5)
        hist = s[s.index >= start]
        if len(hist) < 10:
            hist = s
        mean = float(hist.mean())
        std = float(hist.std())
        sig = 0.0 if (std == 0 or np.isnan(std)) else (latest - mean) / std

    raw = float(direction) * float(sig)
    raw = float(np.clip(raw, -2.0, 2.0))
    score = (raw + 2.0) / 4.0 * 100.0
    return score, sig, latest

def classify_status(score: float) -> str:
    if np.isnan(score):
        return "n/a"
    if score > 60:
        return "risk_on"
    if score < 40:
        return "risk_off"
    return "neutral"

def status_label(status: str) -> str:
    return {"risk_on": "Risk-on", "risk_off": "Risk-off", "neutral": "Neutral"}.get(status, "n/a")

def semaphore(status: str) -> str:
    return {"risk_on": "🟢", "risk_off": "🔴", "neutral": "🟡"}.get(status, "⚪")

def pill_html(status: str, show_sem: bool = True) -> str:
    sem = f"{semaphore(status)} " if show_sem else ""
    if status == "risk_on":
        return f"<span class='pill good'><span class='dot' style='background:var(--good)'></span>{h(sem)}Risk-on</span>"
    if status == "risk_off":
        return f"<span class='pill bad'><span class='dot' style='background:var(--bad)'></span>{h(sem)}Risk-off</span>"
    if status == "neutral":
        return f"<span class='pill warn'><span class='dot' style='background:var(--warn)'></span>{h(sem)}Neutral</span>"
    return f"<span class='pill'><span class='dot' style='background:rgba(255,255,255,0.5)'></span>{h(sem)}n/a</span>"

def fmt_value(val, unit: str, scale: float = 1.0):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "n/a"
    try:
        v = float(val) * float(scale)
    except Exception:
        return "n/a"
    if unit in ("%", "pp"):
        return f"{v:.2f}{unit}"
    if unit == "ratio":
        return f"{v:.3f}"
    if unit == "bn USD":
        return f"{v:.1f} bn"
    if unit == "":
        return f"{v:.2f}"
    return f"{v:.2f} {unit}"

def infer_frequency_days(s: pd.Series) -> float:
    if s is None or s.dropna().shape[0] < 10:
        return 1.0
    idx = pd.to_datetime(s.dropna().index)
    diffs = np.diff(idx.values).astype("timedelta64[D]").astype(int)
    return float(np.median(diffs)) if len(diffs) else 1.0

def value_change_over_days(series: pd.Series, days: int, mode: str = "pct") -> float:
    if series is None or series.empty:
        return np.nan
    s = series.dropna()
    if s.empty:
        return np.nan
    last_date = s.index.max()
    target_date = last_date - timedelta(days=days)
    past = s[s.index <= target_date]
    if past.empty:
        return np.nan
    past_val = float(past.iloc[-1])
    curr_val = float(s.iloc[-1])
    if np.isnan(past_val) or np.isnan(curr_val):
        return np.nan
    if mode == "abs":
        return curr_val - past_val
    if past_val == 0:
        return np.nan
    return (curr_val / past_val - 1.0) * 100.0

def recent_trend(series: pd.Series) -> dict:
    if series is None or series.dropna().shape[0] < 10:
        return {"window_label": "n/a", "delta_pct": np.nan, "arrow": "→", "days": None}
    freq = infer_frequency_days(series)
    days = 90 if freq >= 20 else 30
    label = "1Q" if days == 90 else "30d"
    d = value_change_over_days(series, days, mode="pct")
    if np.isnan(d):
        return {"window_label": label, "delta_pct": np.nan, "arrow": "→", "days": days}
    arrow = "↑" if d > 0.25 else ("↓" if d < -0.25 else "→")
    return {"window_label": label, "delta_pct": d, "arrow": arrow, "days": days}

def score_bar_html(score: float) -> str:
    pos = 50 if np.isnan(score) else int(np.clip(score, 0, 100))
    return f"""
      <div class="barWrap">
        <div class="barFill"></div>
        <div class="barMark" style="left: calc({pos}% - 2px);"></div>
      </div>
    """

# ============================================================
# ALERTS / WATCHLIST
# ============================================================

ALERT_NEAR_BAND = 4.0
ALERT_BREACH_LOOKBACK = 30

def bucket(score: float) -> str:
    return classify_status(score)

def score_at_or_before(series: pd.Series, meta: dict, dt) -> float:
    s = series.dropna()
    if s.shape[0] < 20:
        return np.nan
    s2 = s[s.index <= dt]
    if s2.shape[0] < 20:
        return np.nan
    sc, _, _ = compute_indicator_score(s2, meta["direction"], scoring_mode=meta.get("scoring_mode", "z5y"))
    return sc

def compute_flags(series: pd.Series, score_now: float, meta: dict) -> dict:
    if series is None or series.dropna().empty or np.isnan(score_now):
        return {"near": False, "breach": False, "hot": False, "window": "n/a", "move": np.nan, "move_mode": "pct", "thr": 0.0}

    freq = infer_frequency_days(series)
    days = 90 if freq >= 20 else 30
    window = "1Q" if days == 90 else "30d"

    last_dt = series.dropna().index.max()
    prev_dt = last_dt - timedelta(days=ALERT_BREACH_LOOKBACK)
    sc_prev = score_at_or_before(series, meta, prev_dt)

    breach = False
    if not np.isnan(sc_prev):
        breach = (bucket(score_now) != bucket(sc_prev)) and (bucket(score_now) != "n/a") and (bucket(sc_prev) != "n/a")

    near = (abs(score_now - 40) <= ALERT_NEAR_BAND) or (abs(score_now - 60) <= ALERT_NEAR_BAND)

    move_mode = meta.get("move_mode", "pct")
    move_val = value_change_over_days(series, days, mode=move_mode)
    thr = meta.get("hot_threshold_1q", 0.0) if days == 90 else meta.get("hot_threshold_30d", 0.0)
    hot = (not np.isnan(move_val)) and (thr > 0) and (abs(move_val) >= float(thr))

    return {"near": near, "breach": breach, "hot": hot, "window": window, "move": move_val, "move_mode": move_mode, "thr": thr}

def build_watchlist(indicators: dict, indicator_scores: dict) -> pd.DataFrame:
    rows = []
    for key, meta in INDICATOR_META.items():
        s = indicators.get(key, pd.Series(dtype=float))
        sc_now = indicator_scores.get(key, {}).get("score", np.nan)
        st_now = indicator_scores.get(key, {}).get("status", "n/a")
        if s is None or s.empty or np.isnan(sc_now):
            continue

        tr = recent_trend(s)
        flags = compute_flags(s, sc_now, meta)

        prox = max(0.0, 20.0 - min(abs(sc_now - 40), abs(sc_now - 60))) / 20.0
        hot_bonus = 0.25 if flags["hot"] else 0.0
        breach_bonus = 0.25 if flags["breach"] else 0.0
        attn = float(np.clip(0.55 * prox + hot_bonus + breach_bonus, 0, 1))

        rows.append({
            "Key": key,
            "Indicator": meta["label"],
            "Regime": f"{semaphore(st_now)} {status_label(st_now)}",
            "Score": round(sc_now, 1),
            "TrendWin": tr["window_label"],
            "Trend%": (np.nan if np.isnan(tr["delta_pct"]) else round(tr["delta_pct"], 2)),
            "HotMove": "HOT" if flags["hot"] else "",
            "NearThreshold": "NEAR" if flags["near"] else "",
            "RegimeShift": "SHIFT" if flags["breach"] else "",
            "Attention": round(attn, 2),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["Attention", "RegimeShift", "HotMove", "NearThreshold"], ascending=[False, False, False, False])

# ============================================================
# PLOTTING
# ============================================================

def plot_premium(series: pd.Series, title: str, ref_line=None, height: int = 320):
    s = series.dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", line=dict(width=2), name=title))
    if ref_line is not None:
        fig.add_hline(y=float(ref_line), line_width=1, line_dash="dot", opacity=0.7)

    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.01, y=0.98,
        text=f"<b>{h(title)}</b>",
        showarrow=False,
        align="left",
        font=dict(size=14, color="rgba(255,255,255,0.95)")
    )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=22, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        showlegend=False,
        font=dict(color="rgba(255,255,255,0.88)"),
    )
    return fig

# ============================================================
# WALLBOARD TILE (HTML fragment returned)
# ============================================================

def wallboard_tile_fragment(key: str, series: pd.Series, indicator_scores: dict) -> str:
    meta = INDICATOR_META[key]
    sc = indicator_scores.get(key, {})
    score = sc.get("score", np.nan)
    status = sc.get("status", "n/a")
    latest = sc.get("latest", np.nan)

    latest_txt = h(fmt_value(latest, meta["unit"], meta.get("scale", 1.0)))
    label = h(meta["label"])
    source = h(meta["source"])

    tr = recent_trend(series)
    wlab = h(tr["window_label"])
    d = tr["delta_pct"]
    arrow = h(tr["arrow"])
    d_txt = "n/a" if np.isnan(d) else f"{d:+.1f}%"
    d_txt = h(d_txt)

    ref_line = meta.get("ref_line", None)
    ref_txt = "—" if ref_line is None else str(ref_line)
    ref_txt = h(ref_txt)

    ref_note = h(meta["expander"].get("reference", "—"))

    return f"""
    <div class="wbTile">
      <div>
        <div class="wbName">{label}</div>
        <div class="wbMeta">{source}</div>

        <div class="wbRow">
          <div class="wbVal">{latest_txt}</div>
          <div>{pill_html(status, show_sem=True)}</div>
        </div>

        <div style="margin-top:10px;">
          {score_bar_html(score)}
          <div class="wbFoot">
            <div class="wbSmall">Score: <b>{("n/a" if np.isnan(score) else f"{int(round(score))}")}</b></div>
            <div class="wbSmall">Trend ({wlab}): <b>{arrow} {d_txt}</b></div>
          </div>
        </div>

        <div class="wbSmall" style="margin-top:8px;">
          Reference: <b>{ref_txt}</b> · {ref_note}
        </div>
      </div>
    </div>
    """

# ============================================================
# MAIN
# ============================================================

def main():
    st.title("Global finance | Macro overview")

    st.sidebar.header("Settings")
    if st.sidebar.button("🔄 Refresh data (clear cache)"):
        st.cache_data.clear()
        st.rerun()

    years_back = st.sidebar.slider("History (years)", 5, 30, 15)
    show_guides = st.sidebar.toggle("Wallboard: show indicator guides", value=False)
    show_alerts = st.sidebar.toggle("Show alerts (thresholds / shifts / hot moves)", value=True)

    wallboard_filter = st.sidebar.selectbox(
        "Wallboard filter",
        [
            "All",
            "Market Thermometers",
            "Structural Constraints",
            "Price of Time",
            "Macro Cycle",
            "Conditions & Stress",
            "Liquidity / Plumbing",
            "Fiscal / Policy Constraint",
            "External Balance & Gold",
        ],
        index=0
    )

    today = datetime.now(timezone.utc).date()
    start_date = (today - DateOffset(years=years_back)).date().isoformat()

    if get_fred_api_key() is None:
        st.sidebar.error("⚠️ Missing `FRED_API_KEY` in secrets.")

    with st.spinner("Loading data (FRED + yfinance)..."):
        fred = {
            "real_10y": fetch_fred_series("DFII10", start_date),
            "nominal_10y": fetch_fred_series("DGS10", start_date),
            "dgs2": fetch_fred_series("DGS2", start_date),
            "breakeven_10y": fetch_fred_series("T10YIE", start_date),
            "cpi_index": fetch_fred_series("CPIAUCSL", start_date),
            "unemployment_rate": fetch_fred_series("UNRATE", start_date),
            "hy_oas": fetch_fred_series("BAMLH0A0HYM2", start_date),
            "usd_fred": fetch_fred_series("DTWEXBGS", start_date),
            "fed_balance_sheet": fetch_fred_series("WALCL", start_date),
            "rrp": fetch_fred_series("RRPONTSYD", start_date),
            "interest_payments": fetch_fred_series("A091RC1Q027SBEA", start_date),
            "federal_receipts": fetch_fred_series("FGRECPT", start_date),
            "deficit_gdp": fetch_fred_series("FYFSGDA188S", start_date),
            "term_premium_10y": fetch_fred_series("ACMTP10", start_date),
            "current_account_gdp": fetch_fred_series("USAB6BLTT02STSAQ", start_date),
        }

        indicators = {}

        if not fred["nominal_10y"].empty and not fred["dgs2"].empty:
            yc = fred["nominal_10y"].to_frame("10y").join(fred["dgs2"].to_frame("2y"), how="inner")
            indicators["yield_curve_10_2"] = (yc["10y"] - yc["2y"]).dropna()
        else:
            indicators["yield_curve_10_2"] = pd.Series(dtype=float)

        if not fred["cpi_index"].empty:
            indicators["cpi_yoy"] = (fred["cpi_index"].pct_change(12) * 100.0).dropna()
        else:
            indicators["cpi_yoy"] = pd.Series(dtype=float)

        indicators["real_10y"] = fred["real_10y"]
        indicators["nominal_10y"] = fred["nominal_10y"]
        indicators["breakeven_10y"] = fred["breakeven_10y"]
        indicators["unemployment_rate"] = fred["unemployment_rate"]
        indicators["hy_oas"] = fred["hy_oas"]
        indicators["fed_balance_sheet"] = fred["fed_balance_sheet"]
        indicators["rrp"] = fred["rrp"]
        indicators["interest_payments"] = fred["interest_payments"]
        indicators["federal_receipts"] = fred["federal_receipts"]
        indicators["deficit_gdp"] = fred["deficit_gdp"]
        indicators["term_premium_10y"] = fred["term_premium_10y"]
        indicators["current_account_gdp"] = fred["current_account_gdp"]

        ip = indicators.get("interest_payments", pd.Series(dtype=float))
        fr = indicators.get("federal_receipts", pd.Series(dtype=float))
        if (ip is not None and fr is not None) and (not ip.empty) and (not fr.empty):
            join = ip.to_frame("interest").join(fr.to_frame("receipts"), how="inner").dropna()
            join = join[join["receipts"] != 0]
            indicators["interest_to_receipts"] = (join["interest"] / join["receipts"]).dropna()
        else:
            indicators["interest_to_receipts"] = pd.Series(dtype=float)

        yf_map = fetch_yf_many(["DX-Y.NYB", "^VIX", "SPY", "HYG", "LQD", "GLD"], start_date)

        dxy = yf_map.get("DX-Y.NYB", pd.Series(dtype=float))
        if dxy is None or dxy.empty:
            dxy = fred["usd_fred"]
        indicators["usd_index"] = dxy

        indicators["vix"] = yf_map.get("^VIX", pd.Series(dtype=float))

        spy = yf_map.get("SPY", pd.Series(dtype=float))
        if spy is not None and not spy.empty:
            ma200 = spy.rolling(200).mean()
            indicators["spy_trend"] = (spy / ma200).dropna()
        else:
            indicators["spy_trend"] = pd.Series(dtype=float)

        hyg = yf_map.get("HYG", pd.Series(dtype=float))
        lqd = yf_map.get("LQD", pd.Series(dtype=float))
        if hyg is not None and lqd is not None and (not hyg.empty) and (not lqd.empty):
            joined = hyg.to_frame("HYG").join(lqd.to_frame("LQD"), how="inner").dropna()
            indicators["hyg_lqd_ratio"] = (joined["HYG"] / joined["LQD"]).dropna()
        else:
            indicators["hyg_lqd_ratio"] = pd.Series(dtype=float)

        indicators["gold"] = yf_map.get("GLD", pd.Series(dtype=float))

    indicator_scores = {}
    for key, meta in INDICATOR_META.items():
        series = indicators.get(key, pd.Series(dtype=float))
        mode = meta.get("scoring_mode", "z5y")
        score, sig, latest = compute_indicator_score(series, meta["direction"], scoring_mode=mode)
        indicator_scores[key] = {
            "score": score,
            "signal": sig,
            "latest": latest,
            "status": classify_status(score),
            "mode": mode
        }

    block_scores = {}
    global_score = 0.0
    w_used = 0.0
    for bkey, binfo in BLOCKS.items():
        vals = []
        for ikey in binfo["indicators"]:
            sc = indicator_scores.get(ikey, {}).get("score", np.nan)
            if not np.isnan(sc):
                vals.append(sc)
        bscore = float(np.mean(vals)) if vals else np.nan
        block_scores[bkey] = {"score": bscore, "status": classify_status(bscore)}
        if binfo["weight"] > 0 and not np.isnan(bscore):
            global_score += bscore * binfo["weight"]
            w_used += binfo["weight"]

    global_score = (global_score / w_used) if w_used > 0 else np.nan
    global_status = classify_status(global_score)
    block_scores["GLOBAL"] = {"score": global_score, "status": global_status}

    watch_df = build_watchlist(indicators, indicator_scores)

    tabs = st.tabs(["Overview", "Wallboard", "Deep dive", "What changed"])

    # -------------------------
    # Overview
    # -------------------------
    with tabs[0]:
        st.markdown("<div class='muted'>Immediate regime view + alerts.</div>", unsafe_allow_html=True)

        gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"

        if show_alerts and not watch_df.empty:
            top_hot = watch_df[
                (watch_df["HotMove"] == "HOT")
                | (watch_df["RegimeShift"] == "SHIFT")
                | (watch_df["NearThreshold"] == "NEAR")
            ].head(6)
            if not top_hot.empty:
                st.markdown("### Alerts (need attention)")
                rows = []
                for _, r in top_hot.iterrows():
                    rows.append(
                        f"""
                        <div class="alertRow">
                          <div><b>{h(r['Indicator'])}</b> · {h(r['Regime'])}</div>
                          <div class="wbSmall">
                            Score <b>{h(r['Score'])}</b> · Trend({h(r['TrendWin'])}) <b>{h(r['Trend%'])}%</b>
                            &nbsp;&nbsp;{h(r['RegimeShift'])} {h(r['NearThreshold'])} {h(r['HotMove'])}
                          </div>
                        </div>
                        """
                    )
                render_html("".join(rows), height=60 + 54 * len(rows))

        render_html(
            f"""
            <div class="grid2">
              <div class="card">
                <div class="cardTitle">Global Score (0–100) — core blocks</div>
                <div class="cardValue">{h(gs_txt)}</div>
                <div class="cardSub">{pill_html(global_status, show_sem=True)}</div>
                <div class="cardSub">{score_bar_html(global_score)}</div>
              </div>

              <div class="card">
                <div class="cardTitle">Block scorecard</div>
                <div class="cardSub">
                  🟡 1) Price of Time: <b>{h(status_label(block_scores['price_of_time']['status']))}</b> ({h('n/a' if np.isnan(block_scores['price_of_time']['score']) else round(block_scores['price_of_time']['score'],1))})<br/>
                  🟡 2) Macro Cycle: <b>{h(status_label(block_scores['macro']['status']))}</b> ({h('n/a' if np.isnan(block_scores['macro']['score']) else round(block_scores['macro']['score'],1))})<br/>
                  🟢 3) Conditions & Stress: <b>{h(status_label(block_scores['conditions']['status']))}</b> ({h('n/a' if np.isnan(block_scores['conditions']['score']) else round(block_scores['conditions']['score'],1))})<br/>
                  🟡 4) Liquidity / Plumbing: <b>{h(status_label(block_scores['plumbing']['status']))}</b> ({h('n/a' if np.isnan(block_scores['plumbing']['score']) else round(block_scores['plumbing']['score'],1))})<br/>
                  <br/>
                  🔴 5) Fiscal / Policy Constraint: <b>{h(status_label(block_scores['policy_link']['status']))}</b> ({h('n/a' if np.isnan(block_scores['policy_link']['score']) else round(block_scores['policy_link']['score'],1))})<br/>
                  🔴 6) External Balance: <b>{h(status_label(block_scores['external']['status']))}</b> ({h('n/a' if np.isnan(block_scores['external']['score']) else round(block_scores['external']['score'],1))})<br/>
                  🔴 7) Gold: <b>{h(status_label(block_scores['gold_block']['status']))}</b> ({h('n/a' if np.isnan(block_scores['gold_block']['score']) else round(block_scores['gold_block']['score'],1))})
                </div>
              </div>
            </div>
            """,
            height=260
        )

    # -------------------------
    # Wallboard
    # -------------------------
    with tabs[1]:
        st.markdown("## Wallboard")
        st.markdown("<div class='muted'>Tiles rendered via components.html (no HTML-as-text).</div>", unsafe_allow_html=True)

        groups = [
            ("Price of Time", "Rates and curve: the price of time and late-cycle signal.", ["real_10y", "nominal_10y", "yield_curve_10_2"], "Market Thermometers"),
            ("Macro Cycle", "Inflation and growth: policy constraint and cycle pressure.", ["breakeven_10y", "cpi_yoy", "unemployment_rate"], "Market Thermometers"),
            ("Conditions & Stress", "Fast regime: USD, credit stress, vol, trend, risk appetite.", ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"], "Market Thermometers"),
            ("Liquidity / Plumbing", "System liquidity: tailwind vs drain for risk assets.", ["fed_balance_sheet", "rrp"], "Market Thermometers"),
            ("Fiscal / Policy Constraint", "Debt service, deficit dynamics, and funding constraint signal.", ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"], "Structural Constraints"),
            ("External Balance & Gold", "External funding reliance + hedge demand confirmation.", ["current_account_gdp", "gold"], "Structural Constraints"),
        ]

        def want_group(title: str, group_type: str) -> bool:
            if wallboard_filter == "All":
                return True
            if wallboard_filter == "Market Thermometers":
                return group_type == "Market Thermometers"
            if wallboard_filter == "Structural Constraints":
                return group_type == "Structural Constraints"
            return wallboard_filter == title

        for title, desc, keys, gtype in groups:
            if not want_group(title, gtype):
                continue

            tiles = []
            for k in keys:
                s = indicators.get(k, pd.Series(dtype=float))
                if s is None or s.empty:
                    meta = INDICATOR_META[k]
                    tiles.append(
                        f"""
                        <div class="wbTile" style="opacity:0.85;">
                          <div>
                            <div class="wbName">{h(meta["label"])}</div>
                            <div class="wbMeta">{h(meta["source"])}</div>
                            <div class="wbRow">
                              <div class="wbVal">Missing</div>
                              <div>{pill_html("n/a", show_sem=True)}</div>
                            </div>
                            <div class="wbSmall" style="margin-top:10px;">
                              No data available for this series in the selected history window.
                            </div>
                          </div>
                        </div>
                        """
                    )
                else:
                    tiles.append(wallboard_tile_fragment(k, s, indicator_scores))

            render_html(
                f"""
                <div class="section">
                  <div class="sectionHead">
                    <div>
                      <div class="sectionTitle">{h(title)}</div>
                      <div class="sectionDesc">{h(desc)}</div>
                    </div>
                  </div>
                  <div class="wbGrid">
                    {''.join(tiles)}
                  </div>
                </div>
                """,
                height=220 + 190 * ((len(tiles) + 3) // 4)
            )

            if show_guides:
                with st.expander(f"Indicator guides — {title}", expanded=False):
                    for k in keys:
                        meta = INDICATOR_META[k]
                        exp = meta["expander"]
                        st.markdown(f"### {meta['label']}")
                        st.markdown(f"**What it is:** {exp.get('what','')}")
                        st.markdown(f"**Reference levels / thresholds:** {exp.get('reference','')}")
                        st.markdown("**How to read it:**")
                        st.markdown(exp.get("interpretation", ""))
                        st.markdown(f"**Why it matters (policy/funding link):** {exp.get('bridge','')}")
                        st.markdown("---")

    # -------------------------
    # Deep dive
    # -------------------------
    with tabs[2]:
        st.markdown("## Deep dive")
        group = st.selectbox(
            "Select section",
            ["Price of Time", "Macro Cycle", "Conditions & Stress", "Liquidity / Plumbing", "Fiscal / Policy Constraint", "External Balance & Gold"],
            index=0
        )
        group_map = {
            "Price of Time": ["real_10y", "nominal_10y", "yield_curve_10_2"],
            "Macro Cycle": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],
            "Conditions & Stress": ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"],
            "Liquidity / Plumbing": ["fed_balance_sheet", "rrp"],
            "Fiscal / Policy Constraint": ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"],
            "External Balance & Gold": ["current_account_gdp", "gold"],
        }

        for k in group_map[group]:
            meta = INDICATOR_META[k]
            s = indicators.get(k, pd.Series(dtype=float))
            if s is None or s.empty:
                st.warning(f"Missing data: {meta['label']}")
                continue
            fig = plot_premium(s, meta["label"], ref_line=meta.get("ref_line", None), height=340)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"deep_{k}")

    # -------------------------
    # What changed
    # -------------------------
    with tabs[3]:
        st.markdown("## What changed")
        st.markdown("<div class='muted'>Hot movers + regime shifts + near-threshold items singled out.</div>", unsafe_allow_html=True)

        if watch_df.empty:
            st.info("No sufficient data to compute changes.")
            return

        hot = watch_df[(watch_df["HotMove"] == "HOT") | (watch_df["RegimeShift"] == "SHIFT") | (watch_df["NearThreshold"] == "NEAR")].head(10)
        if not hot.empty:
            cards = []
            for _, r in hot.iterrows():
                cards.append(
                    f"""
                    <div class="card" style="margin-bottom:10px;">
                      <div class="cardTitle">{h(r["Indicator"])}</div>
                      <div class="cardSub">
                        {h(r["Regime"])} · Score: <b>{h(r["Score"])}</b> · Trend({h(r["TrendWin"])}): <b>{h(r["Trend%"])}</b>%
                        &nbsp;&nbsp;{h(r["RegimeShift"])} {h(r["NearThreshold"])} {h(r["HotMove"])}
                      </div>
                    </div>
                    """
                )
            render_html("".join(cards), height=140 + 90 * len(cards), scrolling=True)

        st.markdown("### Full table")
        st.dataframe(watch_df.drop(columns=["Key"]).reset_index(drop=True), use_container_width=True)

if __name__ == "__main__":
    main()
