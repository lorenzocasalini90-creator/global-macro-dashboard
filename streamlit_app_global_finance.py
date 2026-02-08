import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from pandas.tseries.offsets import DateOffset
import html  # <-- IMPORTANT: escaping

# ============================================================
# SAFE HTML ESCAPE
# ============================================================

def h(x) -> str:
    """Escape user/content strings for safe HTML insertion."""
    if x is None:
        return ""
    return html.escape(str(x), quote=True)

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
    --card2:#0c1324;
    --border:rgba(255,255,255,0.10);
    --muted:rgba(255,255,255,0.70);
    --text:rgba(255,255,255,0.94);

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

  button[data-baseweb="tab"]{
    color: rgba(255,255,255,0.92) !important;
    font-weight: 700 !important;
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

  .stButton > button{
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: rgba(255,255,255,0.95) !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
  }
  .stButton > button:hover{
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
  }

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

  .card{
    background: linear-gradient(180deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.03) 100%);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 16px 16px 14px 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  }
  .cardTitle{ font-size: 0.95rem; color: var(--muted); margin-bottom: 6px; }
  .cardValue{ font-size: 2.1rem; font-weight: 780; line-height: 1.05; color: var(--text); }
  .cardSub{ margin-top: 8px; font-size: 0.98rem; color: var(--muted); }

  .grid3{ display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
  .grid2{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }

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

  .section{
    background: rgba(255,255,255,0.025);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 14px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.20);
    margin-bottom: 14px;
  }
  .sectionHead{ display:flex; align-items:baseline; justify-content:space-between; gap: 12px; margin-bottom: 10px; }
  .sectionTitle{ font-size: 1.15rem; font-weight: 800; color: rgba(255,255,255,0.96); }
  .sectionDesc{ font-size: 0.95rem; color: var(--muted); margin-top: 2px; }

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
    min-height: 152px;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
  }
  .wbName{ font-size: 0.98rem; font-weight: 800; color: rgba(255,255,255,0.96); margin-bottom: 2px; }
  .wbMeta{ font-size: 0.86rem; color: var(--muted); margin-bottom: 8px; }
  .wbRow{ display:flex; align-items:baseline; justify-content:space-between; gap: 10px; }
  .wbVal{ font-size: 1.65rem; font-weight: 850; letter-spacing:-0.01em; }
  .wbSmall{ font-size: 0.88rem; color: var(--muted); }
  .wbFoot{ display:flex; align-items:center; justify-content:space-between; gap: 10px; margin-top: 10px; }

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

  .stDataFrame { border: 1px solid var(--border); border-radius: 12px; overflow:hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# META (UNCHANGED CONTENT; NOW SAFE-RENDERED)
# ============================================================

INDICATOR_META = {
    "real_10y": {
        "label": "US 10Y TIPS Real Yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DFII10",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.35,
        "hot_threshold_1q": 0.45,
        "expander": {
            "what": "Real yield (10Y TIPS): the real price of money/time.",
            "reference": "<0% very easy; 0–2% neutral; >2% restrictive (heuristics).",
            "interpretation": "- Higher real yields tighten financial conditions; pressure long-duration assets.\n- Lower real yields typically support risk assets and duration.",
            "bridge": "Higher real yields raise real funding constraints across the system.",
        },
    },
    "nominal_10y": {
        "label": "US 10Y Nominal Yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DGS10",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.35,
        "hot_threshold_1q": 0.45,
        "expander": {
            "what": "Nominal 10Y Treasury yield: benchmark discount rate and broad tightening proxy.",
            "reference": "Fast upside moves often behave like tightening (heuristics).",
            "interpretation": "- Yield up fast = pressure on equities and existing bonds.\n- Yield down can support duration and (sometimes) equities depending on growth/inflation mix.",
            "bridge": "Higher yields mean the market demands more compensation (inflation and/or term premium).",
        },
    },
    "yield_curve_10_2": {
        "label": "US Yield Curve (10Y–2Y)",
        "unit": "pp",
        "direction": +1,
        "source": "FRED DGS10 - DGS2",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.35,
        "hot_threshold_1q": 0.45,
        "expander": {
            "what": "10Y–2Y slope: cycle / recession-probability proxy.",
            "reference": "<0 inverted (late-cycle); >0 normal (heuristics).",
            "interpretation": "- Deep/persistent inversion = late-cycle risk.\n- Steepening back above 0 = normalization (often after easing).",
            "bridge": "Inversion = policy tight vs cycle, raising deleveraging risk.",
        },
    },
    "breakeven_10y": {
        "label": "10Y Breakeven Inflation",
        "unit": "%",
        "direction": -1,
        "source": "FRED T10YIE",
        "scale": 1.0,
        "ref_line": 2.5,
        "scoring_mode": "z5y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.20,
        "hot_threshold_1q": 0.25,
        "expander": {
            "what": "Market-implied inflation expectations (10Y).",
            "reference": "~2–3% anchored; materially >3% = sticky risk (heuristics).",
            "interpretation": "- Higher breakevens reduce easing room.\n- Lower/anchoring supports duration and risk budgeting.",
            "bridge": "Higher expected inflation raises the odds of inflation-tolerant policy in stress.",
        },
    },
    "cpi_yoy": {
        "label": "US CPI YoY",
        "unit": "%",
        "direction": -1,
        "source": "FRED CPIAUCSL (computed YoY)",
        "scale": 1.0,
        "ref_line": 3.0,
        "scoring_mode": "z5y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.20,
        "hot_threshold_1q": 0.30,
        "expander": {
            "what": "Headline inflation YoY (proxy).",
            "reference": "2% is target; >3–4% persistent = sticky risk (heuristics).",
            "interpretation": "- Disinflation supports duration and often equities.\n- Re-acceleration pushes 'higher-for-longer' risks.",
            "bridge": "Persistent inflation becomes the binding policy constraint.",
        },
    },
    "unemployment_rate": {
        "label": "US Unemployment Rate",
        "unit": "%",
        "direction": -1,
        "source": "FRED UNRATE",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.20,
        "hot_threshold_1q": 0.25,
        "expander": {
            "what": "Labor slack proxy.",
            "reference": "Rapid rises often coincide with growth downshift (heuristics).",
            "interpretation": "- Unemployment rising quickly tends to be risk-off.\n- Stable unemployment is typically benign.",
            "bridge": "Slack + high debt raises pressure for policy support (fiscal/monetary).",
        },
    },
    "usd_index": {
        "label": "USD Index (DXY / Broad Proxy)",
        "unit": "",
        "direction": -1,
        "source": "yfinance DX-Y.NYB (fallback FRED DTWEXBGS)",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "move_mode": "pct",
        "hot_threshold_30d": 2.5,
        "hot_threshold_1q": 3.5,
        "expander": {
            "what": "USD strength proxy. If DXY is unavailable, uses broad trade-weighted USD index.",
            "reference": "USD up = tighter global conditions (heuristics).",
            "interpretation": "- USD stronger tightens global funding.\n- USD weaker loosens conditions.",
            "bridge": "Stronger USD increases global funding stress where liabilities are USD-linked.",
        },
    },
    "hy_oas": {
        "label": "US High Yield OAS",
        "unit": "pp",
        "direction": -1,
        "source": "FRED BAMLH0A0HYM2",
        "scale": 1.0,
        "ref_line": 4.5,
        "scoring_mode": "z5y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.60,
        "hot_threshold_1q": 0.80,
        "expander": {
            "what": "High-yield credit spread: credit stress / default premium proxy.",
            "reference": "<4% often benign; >6–7% stress (heuristics).",
            "interpretation": "- Spreads widening = risk-off.\n- Tight spreads = risk appetite.",
            "bridge": "Credit stress can accelerate non-linear deleveraging dynamics.",
        },
    },
    "vix": {
        "label": "VIX",
        "unit": "",
        "direction": -1,
        "source": "yfinance ^VIX",
        "scale": 1.0,
        "ref_line": 20.0,
        "scoring_mode": "z5y",
        "move_mode": "pct",
        "hot_threshold_30d": 25.0,
        "hot_threshold_1q": 30.0,
        "expander": {
            "what": "Equity implied volatility (S&P 500).",
            "reference": "<15 low; 15–25 normal; >25 stress (heuristics).",
            "interpretation": "- Higher vol tightens conditions through risk premia.\n- Lower vol often supports risk-taking.",
            "bridge": "Vol spikes tighten conditions even without rate hikes.",
        },
    },
    "spy_trend": {
        "label": "SPY Trend (SPY / 200D MA)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance SPY",
        "scale": 1.0,
        "ref_line": 1.0,
        "scoring_mode": "z5y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.03,
        "hot_threshold_1q": 0.04,
        "expander": {
            "what": "Simple trend proxy: SPY vs 200-day moving average.",
            "reference": ">1 = uptrend; <1 = downtrend (heuristics).",
            "interpretation": "- Above 1 supports risk-on behavior.\n- Below 1 signals risk-off trend regime.",
            "bridge": "Trend down + credit stress up is a common deleveraging signature.",
        },
    },
    "hyg_lqd_ratio": {
        "label": "Credit Risk Appetite (HYG / LQD)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance HYG, LQD",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.02,
        "hot_threshold_1q": 0.03,
        "expander": {
            "what": "High yield vs investment grade ratio: credit risk appetite proxy.",
            "reference": "Ratio up = more HY appetite; down = flight to quality.",
            "interpretation": "- Rising ratio is typically risk-on.\n- Falling ratio indicates quality bid / caution.",
            "bridge": "Flight-to-quality signals tightening funding constraints.",
        },
    },
    "fed_balance_sheet": {
        "label": "Fed Balance Sheet (WALCL)",
        "unit": "bn USD",
        "direction": +1,
        "source": "FRED WALCL (millions -> bn)",
        "scale": 1.0 / 1000.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "move_mode": "pct",
        "hot_threshold_30d": 1.0,
        "hot_threshold_1q": 1.5,
        "expander": {
            "what": "Total Fed assets: system liquidity proxy.",
            "reference": "Expansion (QE) often supports risk assets; contraction (QT) drains (heuristics).",
            "interpretation": "- Balance sheet up = tailwind.\n- Balance sheet down = headwind.",
            "bridge": "Liquidity plumbing determines whether flows support or drain risk assets.",
        },
    },
    "rrp": {
        "label": "Fed Overnight RRP",
        "unit": "bn USD",
        "direction": -1,
        "source": "FRED RRPONTSYD",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "move_mode": "pct",
        "hot_threshold_30d": 25.0,
        "hot_threshold_1q": 35.0,
        "expander": {
            "what": "Overnight reverse repo usage: cash parked in risk-free facility.",
            "reference": "High RRP = liquidity 'stuck'; falling RRP can release marginal liquidity (heuristics).",
            "interpretation": "- RRP up = less marginal liquidity for risk.\n- RRP down = potential tailwind.",
            "bridge": "RRP declines can act as a tactical liquidity release valve.",
        },
    },
    "interest_payments": {
        "label": "US Federal Interest Payments (Quarterly)",
        "unit": "bn USD",
        "direction": -1,
        "source": "FRED A091RC1Q027SBEA",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "move_mode": "pct",
        "hot_threshold_30d": 2.0,
        "hot_threshold_1q": 3.0,
        "expander": {
            "what": "Government interest expense: debt-service pressure proxy.",
            "reference": "Rising/accelerating debt service reduces policy flexibility (heuristics).",
            "interpretation": "- Persistent rise increases policy constraint.\n- Stabilization reduces constraint.",
            "bridge": "Debt service pressure increases incentives for funding-friendly policy outcomes.",
        },
    },
    "federal_receipts": {
        "label": "US Federal Current Receipts (Quarterly)",
        "unit": "bn USD",
        "direction": +1,
        "source": "FRED FGRECPT",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "move_mode": "pct",
        "hot_threshold_30d": 2.0,
        "hot_threshold_1q": 3.0,
        "expander": {
            "what": "Government receipts: supports debt-service capacity.",
            "reference": "Used to compute interest/receipts sustainability proxy.",
            "interpretation": "- Receipts up improves capacity (all else equal).\n- Receipts down tightens constraint.",
            "bridge": "Higher receipts reduce the binding nature of debt service.",
        },
    },
    "interest_to_receipts": {
        "label": "Debt Service Stress (Interest / Receipts)",
        "unit": "ratio",
        "direction": -1,
        "source": "Derived",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.008,
        "hot_threshold_1q": 0.010,
        "expander": {
            "what": "Sustainability proxy: share of receipts consumed by interest expense.",
            "reference": "High and rising = constraint becomes political (heuristics).",
            "interpretation": "- Higher ratio signals tighter fiscal policy constraint.\n- Lower ratio signals more room.",
            "bridge": "Higher debt service increases incentives for inflation-tolerant or funding-friendly policy.",
        },
    },
    "deficit_gdp": {
        "label": "Federal Surplus/Deficit (% of GDP)",
        "unit": "%",
        "direction": -1,
        "source": "FRED FYFSGDA188S",
        "scale": 1.0,
        "ref_line": -3.0,
        "scoring_mode": "pct20y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.50,
        "hot_threshold_1q": 0.70,
        "expander": {
            "what": "Fiscal balance (% of GDP). Negative = deficit.",
            "reference": "Persistent large deficits increase Treasury supply pressure (heuristics).",
            "interpretation": "- More negative implies more supply/funding pressure.\n- Improvement reduces pressure.",
            "bridge": "Supply pressure can show up as higher term premium and weaker duration hedge behavior.",
        },
    },
    "term_premium_10y": {
        "label": "US 10Y Term Premium (ACM)",
        "unit": "%",
        "direction": -1,
        "source": "FRED ACMTP10",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.30,
        "hot_threshold_1q": 0.35,
        "expander": {
            "what": "Term premium: compensation required to hold nominal duration.",
            "reference": "Rising term premium makes long nominal bonds less reliable as a hedge (heuristics).",
            "interpretation": "- Term premium up increases duration risk.\n- Term premium down restores hedge quality.",
            "bridge": "If term premium rises from supply/funding, duration may stop hedging equity drawdowns.",
        },
    },
    "current_account_gdp": {
        "label": "US Current Account Balance (% of GDP)",
        "unit": "%",
        "direction": +1,
        "source": "FRED USAB6BLTT02STSAQ",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "pct20y",
        "move_mode": "abs",
        "hot_threshold_30d": 0.35,
        "hot_threshold_1q": 0.50,
        "expander": {
            "what": "External funding constraint proxy. Negative = reliance on foreign capital.",
            "reference": "More negative implies higher vulnerability during USD tightening (heuristics).",
            "interpretation": "- More negative increases dependence on external funding.\n- Moving toward 0 reduces constraint.",
            "bridge": "External deficits increase vulnerability when global USD funding tightens.",
        },
    },
    "gold": {
        "label": "Gold (GLD)",
        "unit": "",
        "direction": -1,
        "source": "yfinance GLD",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "move_mode": "pct",
        "hot_threshold_30d": 6.0,
        "hot_threshold_1q": 8.0,
        "expander": {
            "what": "Gold: hedge demand proxy (policy/inflation/tail risk).",
            "reference": "Breakouts often reflect hedge demand rather than growth optimism (heuristics).",
            "interpretation": "- Gold up can signal hedge demand.\n- Gold down in equity bull may reflect clean risk-on.",
            "bridge": "Gold can hedge environments where real returns are compressed or policy turns funding-friendly.",
        },
    },
}

BLOCKS = {
    "price_of_time": {
        "name": "1) Price of Time",
        "weight": 0.20,
        "indicators": ["real_10y", "nominal_10y", "yield_curve_10_2"],
        "desc": "Rates / curve: the price of time and late-cycle signal.",
        "group": "Market Thermometers",
    },
    "macro": {
        "name": "2) Macro Cycle",
        "weight": 0.15,
        "indicators": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],
        "desc": "Inflation and growth constraint on policy reaction.",
        "group": "Market Thermometers",
    },
    "conditions": {
        "name": "3) Conditions & Stress",
        "weight": 0.20,
        "indicators": ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"],
        "desc": "Fast regime: USD, credit stress, vol, trend, risk appetite.",
        "group": "Market Thermometers",
    },
    "plumbing": {
        "name": "4) Liquidity / Plumbing",
        "weight": 0.15,
        "indicators": ["fed_balance_sheet", "rrp"],
        "desc": "System liquidity tailwind vs drain for risk assets.",
        "group": "Market Thermometers",
    },
    "policy_link": {
        "name": "5) Fiscal / Policy Constraint",
        "weight": 0.20,
        "indicators": ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"],
        "desc": "Debt service, deficit dynamics, and the funding constraint signal.",
        "group": "Structural Constraints",
    },
    "external": {
        "name": "6) External Balance",
        "weight": 0.10,
        "indicators": ["current_account_gdp"],
        "desc": "External funding reliance and vulnerability in USD tightening.",
        "group": "Structural Constraints",
    },
    "gold_block": {
        "name": "7) Gold",
        "weight": 0.00,
        "indicators": ["gold"],
        "desc": "Policy / tail-risk hedge demand confirmation.",
        "group": "Structural Constraints",
    },
}

# ============================================================
# FETCHERS
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
        s = pd.Series(vals, index=idx).replace({".": np.nan}).astype(float).sort_index()
        return s
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

def pill_html(status: str, with_semaphore: bool = True) -> str:
    sem = f"{semaphore(status)} " if with_semaphore else ""
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
# ALERTS (same logic)
# ============================================================

ALERT_NEAR_BAND = 4.0

def bucket_from_score(score: float) -> str:
    return classify_status(score)

def score_at_or_before(series: pd.Series, meta: dict, dt) -> float:
    if series is None or series.dropna().shape[0] < 20:
        return np.nan
    ss = series.dropna()
    ss_prev = ss[ss.index <= dt]
    if ss_prev.shape[0] < 20:
        return np.nan
    score_prev, _, _ = compute_indicator_score(ss_prev, meta["direction"], scoring_mode=meta.get("scoring_mode", "z5y"))
    return score_prev

def compute_flags(series: pd.Series, score_now: float, meta: dict) -> dict:
    if series is None or series.dropna().empty or np.isnan(score_now):
        return {"window": "n/a", "days": None, "move": np.nan, "move_mode": meta.get("move_mode", "pct"),
                "breach": False, "near": False, "hot": False, "attention": 0.0,
                "prev_bucket": "n/a", "now_bucket": "n/a", "threshold": 0.0}

    freq = infer_frequency_days(series)
    days = 90 if freq >= 20 else 30
    window = "1Q" if days == 90 else "30d"

    last_dt = series.dropna().index.max()
    prev_dt = last_dt - timedelta(days=days)

    score_prev = score_at_or_before(series, meta, prev_dt)

    now_b = bucket_from_score(score_now)
    prev_b = bucket_from_score(score_prev)
    breach = (now_b != prev_b) and (now_b != "n/a") and (prev_b != "n/a")

    near = (abs(score_now - 40) <= ALERT_NEAR_BAND) or (abs(score_now - 60) <= ALERT_NEAR_BAND)

    move_mode = meta.get("move_mode", "pct")
    move_val = value_change_over_days(series, days, mode=move_mode)

    thr = meta.get("hot_threshold_1q", 0.0) if days == 90 else meta.get("hot_threshold_30d", 0.0)
    hot = (not np.isnan(move_val)) and (abs(move_val) >= float(thr)) and (thr > 0)

    prox = max(0.0, 20.0 - min(abs(score_now - 40), abs(score_now - 60))) / 20.0
    mv = 0.0 if (np.isnan(move_val) or thr <= 0) else min(1.0, abs(move_val) / (2.0 * thr))
    attention = float(np.clip(0.52 * prox + 0.33 * mv + (0.15 if breach else 0.0), 0.0, 1.0))

    return {"window": window, "days": days, "move": move_val, "move_mode": move_mode,
            "breach": breach, "near": near, "hot": hot, "attention": attention,
            "prev_bucket": prev_b, "now_bucket": now_b, "threshold": thr}

def build_alerts(indicators: dict, indicator_scores: dict) -> dict:
    breaches, hot_moves, near_threshold, missing = [], [], [], []
    for k, meta in INDICATOR_META.items():
        s = indicators.get(k, pd.Series(dtype=float))
        sc_now = indicator_scores.get(k, {}).get("score", np.nan)
        if s is None or s.empty or np.isnan(sc_now):
            missing.append((k, meta["label"], {}))
            continue
        f = compute_flags(s, sc_now, meta)
        if f["breach"]:
            breaches.append((k, meta["label"], f))
        if f["hot"]:
            hot_moves.append((k, meta["label"], f))
        if f["near"]:
            near_threshold.append((k, meta["label"], f))

    breaches.sort(key=lambda x: x[2]["attention"], reverse=True)
    hot_moves.sort(key=lambda x: x[2]["attention"], reverse=True)
    near_threshold.sort(key=lambda x: x[2]["attention"], reverse=True)

    return {"breaches": breaches[:10], "hot_moves": hot_moves[:10], "near_threshold": near_threshold[:10], "missing": missing[:10]}

def fmt_move(move: float, move_mode: str, unit_hint: str) -> str:
    if np.isnan(move):
        return "n/a"
    if move_mode == "abs":
        if unit_hint in ("%", "pp"):
            return f"{move:+.2f}{unit_hint}"
        if unit_hint == "ratio":
            return f"{move:+.3f}"
        return f"{move:+.2f}"
    return f"{move:+.1f}%"

# ============================================================
# PLOTTING
# ============================================================

def plot_premium(series: pd.Series, title: str, ref_line=None, height: int = 320):
    s = series.dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", line=dict(width=2), name=title))
    if ref_line is not None:
        fig.add_hline(y=float(ref_line), line_width=1, line_dash="dot", opacity=0.7)
    fig.add_annotation(xref="paper", yref="paper", x=0.01, y=0.98, text=f"<b>{h(title)}</b>",
                       showarrow=False, align="left", font=dict(size=14, color="rgba(255,255,255,0.95)"))
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
# OPERATING LINES (kept)
# ============================================================

def operating_lines(block_scores: dict, indicator_scores: dict):
    gs = block_scores.get("GLOBAL", {}).get("score", np.nan)

    def _sg(x):
        return 0.0 if np.isnan(x) else float(x)

    cond = _sg(block_scores.get("conditions", {}).get("score", np.nan))
    macro = _sg(block_scores.get("macro", {}).get("score", np.nan))
    pot = _sg(block_scores.get("price_of_time", {}).get("score", np.nan))
    policy = _sg(block_scores.get("policy_link", {}).get("score", np.nan))

    if not np.isnan(gs):
        if gs >= 60 and cond >= 55:
            equity = "Increase (measured) — risk budget OK, watch credit"
        elif gs <= 40 or cond <= 40:
            equity = "Reduce — defense/quality first"
        else:
            equity = "Neutral — moderate sizing"
    else:
        equity = "n/a"

    termp = _sg(indicator_scores.get("term_premium_10y", {}).get("score", np.nan))
    infl = _sg(indicator_scores.get("cpi_yoy", {}).get("score", np.nan))

    if termp <= 40 and infl <= 45:
        duration = "Short/neutral — avoid long nominals; prefer quality / TIPS tilt"
    elif pot <= 40 and infl <= 45 and termp >= 55:
        duration = "Long (hedge) — disinflation + duration hedge looks cleaner"
    else:
        duration = "Neutral — balance term-premium risk vs cycle"

    hy = _sg(indicator_scores.get("hy_oas", {}).get("score", np.nan))
    hyg = _sg(indicator_scores.get("hyg_lqd_ratio", {}).get("score", np.nan))
    ds = _sg(indicator_scores.get("interest_to_receipts", {}).get("score", np.nan))

    if hy <= 40 or hyg <= 40 or ds <= 40:
        credit = "IG > HY — reduce default / funding risk"
    elif hy >= 60 and hyg >= 60 and policy >= 50:
        credit = "Opportunistic HY — only with sizing discipline"
    else:
        credit = "Neutral — quality + selectivity"

    usd = _sg(indicator_scores.get("usd_index", {}).get("score", np.nan))
    gold = _sg(indicator_scores.get("gold", {}).get("score", np.nan))

    if policy <= 40 and (macro <= 55):
        hedges = "Gold / real-asset tilt — policy constraint risk"
    elif usd <= 40 and cond <= 45:
        hedges = "USD / cash-like — funding stress hedge"
    elif gold <= 40:
        hedges = "Keep a small gold sleeve — hedge demand rising"
    else:
        hedges = "Light mix — cash-like + tactical gold"

    return equity, duration, credit, hedges

# ============================================================
# WALLBOARD TILE (FIX: escape any text injected into HTML)
# ============================================================

def wallboard_tile(key: str, series: pd.Series, indicator_scores: dict, show_guides: bool):
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

    # THIS WAS THE BREAKER: contains "<0%" etc. -> must escape
    ref_note = h(meta["expander"].get("reference", "—"))

    st.markdown(
        f"""
        <div class="wbTile">
          <div>
            <div class="wbName">{label}</div>
            <div class="wbMeta">{source}</div>

            <div class="wbRow">
              <div class="wbVal">{latest_txt}</div>
              <div>{pill_html(status, with_semaphore=True)}</div>
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
        """,
        unsafe_allow_html=True,
    )

    if show_guides:
        with st.expander(f"Indicator guide — {meta['label']}", expanded=False):
            exp = meta["expander"]
            st.markdown(f"**What it is:** {exp.get('what','')}")
            st.markdown(f"**Reference levels / thresholds:** {exp.get('reference','')}")
            st.markdown("**How to read it:**")
            st.markdown(exp.get("interpretation", ""))
            st.markdown(f"**Why it matters (policy/funding link):** {exp.get('bridge','')}")

# ============================================================
# REPORT PROMPT (unchanged)
# ============================================================

REPORT_PROMPT = "..."  # keep your existing string here (omitted for brevity)

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
    show_guides_wallboard = st.sidebar.toggle("Wallboard: show indicator guides (expanders)", value=False)
    wallboard_focus = st.sidebar.selectbox(
        "Wallboard focus",
        ["All groups", "Market Thermometers only", "Structural Constraints only"],
        index=0
    )
    show_alerts = st.sidebar.toggle("Show Alerts bar", value=True)

    today = datetime.now(timezone.utc).date()
    start_date = (today - DateOffset(years=years_back)).date().isoformat()
    st.sidebar.markdown(f"**Start date:** {start_date}")

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
        # derived yield curve
        if not fred["nominal_10y"].empty and not fred["dgs2"].empty:
            yc = fred["nominal_10y"].to_frame("10y").join(fred["dgs2"].to_frame("2y"), how="inner")
            indicators["yield_curve_10_2"] = (yc["10y"] - yc["2y"]).dropna()
        else:
            indicators["yield_curve_10_2"] = pd.Series(dtype=float)

        # CPI YoY
        indicators["cpi_yoy"] = (fred["cpi_index"].pct_change(12) * 100.0).dropna() if not fred["cpi_index"].empty else pd.Series(dtype=float)

        # direct
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

        # derived interest/receipts
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

    # scores
    indicator_scores = {}
    for key, meta in INDICATOR_META.items():
        series = indicators.get(key, pd.Series(dtype=float))
        mode = meta.get("scoring_mode", "z5y")
        score, sig, latest = compute_indicator_score(series, meta["direction"], scoring_mode=mode)
        indicator_scores[key] = {"score": score, "signal": sig, "latest": latest, "status": classify_status(score), "mode": mode}

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

    tabs = st.tabs(["Overview", "Wallboard", "Deep dive", "What changed", "Report generation"])

    with tabs[0]:
        st.markdown("<div class='muted'>Overview.</div>", unsafe_allow_html=True)
        # (keep your previous overview body; not repeated here to keep the fix focused)

    with tabs[1]:
        st.markdown("## Wallboard")
        st.markdown("<div class='muted'>No broken tiles: all reference text is HTML-escaped.</div>", unsafe_allow_html=True)

        # group renderer
        def render_group(title: str, desc: str, keys: list[str]):
            st.markdown(
                f"""
                <div class="section">
                  <div class="sectionHead">
                    <div>
                      <div class="sectionTitle">{h(title)}</div>
                      <div class="sectionDesc">{h(desc)}</div>
                    </div>
                  </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown("<div class='wbGrid'>", unsafe_allow_html=True)

            for k in keys:
                s = indicators.get(k, pd.Series(dtype=float))
                if s is None or s.empty:
                    meta = INDICATOR_META[k]
                    st.markdown(
                        f"""
                        <div class="wbTile" style="opacity:0.85;">
                          <div>
                            <div class="wbName">{h(meta["label"])}</div>
                            <div class="wbMeta">{h(meta["source"])}</div>
                            <div class="wbRow">
                              <div class="wbVal">Missing</div>
                              <div>{pill_html("n/a", with_semaphore=True)}</div>
                            </div>
                            <div class="wbSmall" style="margin-top:10px;">
                              No data available for this series in the selected history window.
                            </div>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    wallboard_tile(k, s, indicator_scores, show_guides_wallboard)

            st.markdown("</div></div>", unsafe_allow_html=True)

        market_groups = [
            ("Price of Time", "Rates and curve: the price of time and late-cycle signal.", ["real_10y", "nominal_10y", "yield_curve_10_2"]),
            ("Macro Cycle", "Inflation and growth: policy constraint and cycle pressure.", ["breakeven_10y", "cpi_yoy", "unemployment_rate"]),
            ("Conditions & Stress", "Fast regime: USD, credit stress, vol, trend, risk appetite.", ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"]),
            ("Liquidity / Plumbing", "System liquidity: tailwind vs drain for risk assets.", ["fed_balance_sheet", "rrp"]),
        ]
        structural_groups = [
            ("Fiscal / Policy Constraint", "Debt service, deficit dynamics, and funding constraint signal.",
             ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"]),
            ("External Balance & Gold", "External funding reliance + hedge demand confirmation.", ["current_account_gdp", "gold"]),
        ]

        if wallboard_focus in ["All groups", "Market Thermometers only"]:
            for t, d, ks in market_groups:
                render_group(t, d, ks)

        if wallboard_focus in ["All groups", "Structural Constraints only"]:
            for t, d, ks in structural_groups:
                render_group(t, d, ks)

    with tabs[2]:
        st.markdown("## Deep dive")
        # keep as you had; charts are safe because we escape title in annotation already.

    with tabs[3]:
        st.markdown("## What changed")
        # keep as you had; Streamlit markdown (not HTML) is safe.

    with tabs[4]:
        st.markdown("## Report generation")
        st.info("Insert your previous Report generation block here unchanged (prompt+payload).")

if __name__ == "__main__":
    main()
