import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from pandas.tseries.offsets import DateOffset

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Global Finance | Macro Overview (Dalio-enhanced)",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# PREMIUM CSS (FIXED: expander white bar, button readability, table wrapping, consistent cards)
# =========================
st.markdown(
    """
<style>
  :root{
    --bg:#0b0f19;
    --card:#0f1629;
    --card2:#0c1324;
    --border:rgba(255,255,255,0.10);
    --muted:rgba(255,255,255,0.65);
    --text:rgba(255,255,255,0.92);
    --accent:rgba(99,102,241,1);
    --good:rgba(34,197,94,1);
    --warn:rgba(245,158,11,1);
    --bad:rgba(239,68,68,1);
  }

  .stApp {
    background: radial-gradient(1200px 700px at 20% 0%, #121a33 0%, #0b0f19 45%, #0b0f19 100%);
    color: var(--text);
  }
  .block-container { padding-top: 1.0rem; padding-bottom: 2.0rem; }

  h1, h2, h3, h4 { color: var(--text); letter-spacing: -0.02em; }
  .muted { color: var(--muted); }

  /* Pills */
  .pill {
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding: 5px 11px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: rgba(255,255,255,0.04);
    font-size: 0.88rem;
    color: var(--text);
    white-space: nowrap;
  }
  .pill.good { border-color: rgba(34,197,94,0.45); background: rgba(34,197,94,0.12); }
  .pill.warn { border-color: rgba(245,158,11,0.45); background: rgba(245,158,11,0.12); }
  .pill.bad  { border-color: rgba(239,68,68,0.45);  background: rgba(239,68,68,0.12); }
  .dot{
    width: 12px; height: 12px; border-radius: 999px; display:inline-block;
    box-shadow: 0 0 0 3px rgba(255,255,255,0.06) inset, 0 8px 18px rgba(0,0,0,0.35);
  }
  .dot.good{ background: var(--good); }
  .dot.warn{ background: var(--warn); }
  .dot.bad{ background: var(--bad); }

  /* Cards */
  .section-card {
    background: rgba(255,255,255,0.035);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 14px 14px 12px 14px;
    box-shadow: 0 10px 26px rgba(0,0,0,0.22);
    margin-bottom: 12px;
  }

  /* KPI tiles (overview) */
  .kpi-grid {
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }
  .kpi-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.03) 100%);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 16px 16px 14px 16px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.26);
  }
  .kpi-title { font-size: 0.98rem; color: var(--muted); margin-bottom: 7px; }
  .kpi-value { font-size: 2.25rem; font-weight: 800; line-height: 1.05; color: var(--text); }
  .kpi-sub { margin-top: 7px; font-size: 0.98rem; color: var(--muted); }

  /* Deep-dive indicator tile */
  .tile-title { font-size: 1.03rem; font-weight: 700; margin-bottom: 2px; }
  .tile-meta { color: var(--muted); font-size: 0.88rem; margin-bottom: 8px; }
  .tile-toprow {
    display:flex; align-items:flex-start; justify-content:space-between; gap: 12px;
    margin-bottom: 8px;
  }
  .tiny { font-size: 0.88rem; color: var(--muted); }

  /* Wallboard */
  .wb-hero {
    background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.025) 100%);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 18px;
    box-shadow: 0 14px 38px rgba(0,0,0,0.30);
    margin-bottom: 14px;
  }
  .wb-card{
    background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 14px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.24);
    min-height: 250px;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
  }
  .wb-card h4{
    margin: 0 0 6px 0;
    font-size: 1.05rem;
  }
  .wb-source{ color: var(--muted); font-size: 0.88rem; margin-bottom: 10px; }
  .wb-value{ font-size: 2.05rem; font-weight: 850; letter-spacing:-0.02em; }
  .wb-line{ color: var(--muted); font-size: 0.95rem; }

  /* Expander white bar FIX */
  details {
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    background: rgba(255,255,255,0.03) !important;
    overflow: hidden;
  }
  summary {
    background: rgba(255,255,255,0.06) !important;
    color: rgba(255,255,255,0.92) !important;
    padding: 12px 14px !important;
    font-weight: 700 !important;
  }
  details[open] summary {
    background: rgba(255,255,255,0.07) !important;
    border-bottom: 1px solid rgba(255,255,255,0.09) !important;
  }
  summary::marker { color: rgba(255,255,255,0.75) !important; }
  summary:hover { filter: brightness(1.07); }

  /* Buttons readable */
  .stButton>button {
    background: rgba(99,102,241,0.18) !important;
    color: rgba(255,255,255,0.92) !important;
    border: 1px solid rgba(99,102,241,0.35) !important;
    border-radius: 12px !important;
    padding: 0.55rem 0.9rem !important;
    font-weight: 700 !important;
  }
  .stButton>button:hover { filter: brightness(1.12); }

  /* Dataframe readability: allow wrapping */
  .stDataFrame { border: 1px solid var(--border); border-radius: 14px; overflow:hidden; }
  div[data-testid="stDataFrame"] * { color: rgba(255,255,255,0.88) !important; }
  div[data-testid="stDataFrame"] td div { white-space: normal !important; line-height: 1.25 !important; }

  /* Tabs */
  button[data-baseweb="tab"] { color: var(--muted) !important; }
  button[data-baseweb="tab"][aria-selected="true"]{ color: var(--text) !important; }

  hr { border-color: rgba(255,255,255,0.10); }

  /* Mobile tweaks */
  @media (max-width: 900px){
    .kpi-grid { grid-template-columns: 1fr; }
    .wb-card { min-height: 235px; }
  }
</style>
    """,
    unsafe_allow_html=True,
)

# =========================
# CONFIG: INDICATORS & BLOCKS
# =========================
INDICATOR_META = {
    "real_10y": {
        "label": "US 10Y TIPS Real Yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DFII10",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Real yield (10Y TIPS): the 'price of time' net of inflation expectations.",
            "reference": "<0% very easy; 0–2% neutral; >2% restrictive (heuristics).",
            "interpretation": (
                "- **Real yield up** → headwind for equities (esp. growth) and long duration.\n"
                "- **Real yield down** → tailwind for risk assets; duration hedges improve."
            ),
            "dalio_bridge": "Higher real yields tighten the funding constraint across the system.",
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
        "expander": {
            "what": "Nominal Treasury yield: broad discount-rate / financial-conditions proxy.",
            "reference": "Fast moves higher often behave like tightening.",
            "interpretation": (
                "- **Up fast** → pressure on equities and existing bonds.\n"
                "- **Down** → supports duration; equities depend on growth/inflation context."
            ),
            "dalio_bridge": "Yield up = market demands more compensation (inflation and/or term premium).",
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
        "expander": {
            "what": "10Y–2Y slope: cycle / recession-risk proxy.",
            "reference": "<0 inverted (late cycle); >0 normal (heuristics).",
            "interpretation": (
                "- **Deeply negative** and persistent → higher recession risk / risk-off.\n"
                "- **Re-steepening** → cycle normalization (watch the reason)."
            ),
            "dalio_bridge": "Inversion = policy restrictive vs cycle → higher deleveraging probability.",
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
        "expander": {
            "what": "Market-implied inflation expectations: nominals vs TIPS.",
            "reference": "~2–3% anchored; well >3% = sticky risk (heuristics).",
            "interpretation": (
                "- **Up** → higher odds of restrictive policy longer.\n"
                "- **Down to target** → more room for easing."
            ),
            "dalio_bridge": "Higher inflation expectations raise the chance of financial repression in stress.",
        },
    },
    "cpi_yoy": {
        "label": "US CPI YoY",
        "unit": "%",
        "direction": -1,
        "source": "FRED CPIAUCSL (YoY computed)",
        "scale": 1.0,
        "ref_line": 3.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Headline inflation YoY (proxy).",
            "reference": "2% target; >3–4% persistent = sticky (heuristics).",
            "interpretation": (
                "- **Disinflation** → supports duration and often equities.\n"
                "- **Re-acceleration** → higher-for-longer risk."
            ),
            "dalio_bridge": "Sticky inflation is the key policy constraint (less room to 'rescue' credit).",
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
        "expander": {
            "what": "Labor slack proxy (cycle).",
            "reference": "Fast rises are often associated with slowdowns/recessions.",
            "interpretation": (
                "- **Up fast** → recession risk (risk-off).\n"
                "- **Stable** → healthier macro backdrop."
            ),
            "dalio_bridge": "Slack up + high debt increases pressure for supportive policy (fiscal dominance risk).",
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
        "expander": {
            "what": "USD strength proxy. If DXY is missing, uses broad USD index from FRED.",
            "reference": "Stronger USD = tighter global conditions (heuristic).",
            "interpretation": (
                "- **USD up** → global tightening / pressure on risk.\n"
                "- **USD down** → easier conditions."
            ),
            "dalio_bridge": "USD up = global funding stress rises (USD debt becomes heavier).",
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
        "expander": {
            "what": "HY credit spread (OAS): default/funding stress thermometer.",
            "reference": "<4% often benign; >6–7% stress (heuristics).",
            "interpretation": (
                "- **Up** → risk-off.\n"
                "- **Down** → risk appetite."
            ),
            "dalio_bridge": "Credit stress accelerates deleveraging non-linearly.",
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
        "expander": {
            "what": "Equity implied volatility (S&P 500).",
            "reference": "<15 low; 15–25 normal; >25 stress (heuristics).",
            "interpretation": (
                "- **Up** → risk-off.\n"
                "- **Down** → risk-on."
            ),
            "dalio_bridge": "Vol up tightens conditions even without rate hikes (risk premia up).",
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
        "expander": {
            "what": "Trend proxy: SPY vs 200-day moving average.",
            "reference": ">1 bull trend; <1 downtrend (heuristics).",
            "interpretation": (
                "- **>1** → risk-on support.\n"
                "- **<1** → risk-off regime."
            ),
            "dalio_bridge": "Trend down + credit stress up is typical deleveraging setup.",
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
        "expander": {
            "what": "HY vs IG ratio: credit risk appetite proxy.",
            "reference": "Up = more HY appetite; down = flight to quality.",
            "interpretation": (
                "- **Up** → risk-on.\n"
                "- **Down** → risk-off."
            ),
            "dalio_bridge": "Flight-to-quality signals tightening funding constraints.",
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
        "expander": {
            "what": "Fed total assets: system liquidity proxy.",
            "reference": "QE expansion supports risk; QT drains (heuristic).",
            "interpretation": (
                "- **Up** → more liquidity (tailwind).\n"
                "- **Down** → drain (headwind)."
            ),
            "dalio_bridge": "Plumbing determines whether flows support or drain risk assets.",
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
        "expander": {
            "what": "RRP: liquidity parked risk-free; falling RRP can release marginal liquidity.",
            "reference": "Higher = more cash 'stuck'; lower = potentially more liquidity in markets.",
            "interpretation": (
                "- **RRP up** → less fuel for risk.\n"
                "- **RRP down** → supports risk tactically."
            ),
            "dalio_bridge": "RRP down often releases marginal liquidity (short-term risk support).",
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
        "expander": {
            "what": "Federal interest outlays (payments).",
            "reference": "Stress rises when the trend accelerates into a political constraint.",
            "interpretation": (
                "- **Up persistently** → higher fiscal-dominance / repression odds.\n"
                "- **Down** → constraint eases."
            ),
            "dalio_bridge": "Debt service up increases incentives for financial repression.",
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
        "expander": {
            "what": "Federal receipts (revenues).",
            "reference": "Used for interest/receipts sustainability ratio.",
            "interpretation": (
                "- **Receipts up** (vs interest) → sustainability improves.\n"
                "- **Receipts down** → constraint tightens."
            ),
            "dalio_bridge": "Interest/receipts rising is the key 'squeezing' mechanism.",
        },
    },
    "interest_to_receipts": {
        "label": "Debt Service Stress (Interest / Receipts)",
        "unit": "ratio",
        "direction": -1,
        "source": "Derived: Interest / Receipts",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Sustainability proxy: share of receipts absorbed by interest.",
            "reference": "High + rising = political/fiscal constraint (heuristic).",
            "interpretation": (
                "- **Up** → increases odds of funding-oriented policy.\n"
                "- **Down** → more anti-inflation policy room."
            ),
            "dalio_bridge": "Higher debt service raises incentives to compress real rates (repression).",
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
        "expander": {
            "what": "Federal balance as % of GDP (negative = deficit).",
            "reference": "Persistent large deficits imply persistent Treasury supply (heuristic).",
            "interpretation": (
                "- **More negative** → supply pressure → term premium risk.\n"
                "- **Improving** → pressure eases."
            ),
            "dalio_bridge": "Deficits raise supply → term premium → duration suffers.",
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
        "expander": {
            "what": "Term premium: compensation for holding nominal duration.",
            "reference": "Higher term premium makes long nominals less reliable as a hedge (heuristic).",
            "interpretation": (
                "- **Up** → long nominal bonds become 'toxic'.\n"
                "- **Down** → duration hedges improve."
            ),
            "dalio_bridge": "If term premium rises from funding/supply, duration stops protecting.",
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
        "expander": {
            "what": "External balance (% of GDP). Negative = reliance on foreign capital.",
            "reference": "Persistent deficit = vulnerability when USD funding tightens (heuristic).",
            "interpretation": (
                "- **More negative** → external constraint rises.\n"
                "- **Toward 0 / positive** → constraint eases."
            ),
            "dalio_bridge": "Current-account deficits imply foreign funding reliance → vulnerability in tightening.",
        },
    },

    "world_equity": {
        "label": "Global Equities (URTH)",
        "unit": "",
        "direction": +1,
        "source": "yfinance URTH",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Non-US confirmation: global equity trend proxy.",
            "reference": "Trend/drawdown confirms whether regime is global or US-only.",
            "interpretation": "- **Up** confirms risk-on; **down** confirms broader risk-off.",
            "dalio_bridge": "Cross-asset confirmation helps separate local vs structural regimes.",
        },
    },
    "duration_proxy_tlt": {
        "label": "Long Duration (TLT)",
        "unit": "",
        "direction": -1,
        "source": "yfinance TLT",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Long Treasury duration proxy (classic hedge).",
            "reference": "Rallies often accompany easing expectations / flight-to-quality.",
            "interpretation": "- **Up** often signals risk-off/easing; **down** with yields up is headwind.",
            "dalio_bridge": "If TLT fails in stress, inflationary deleveraging / term-premium risk may be rising.",
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
        "expander": {
            "what": "Gold hedge demand proxy (inflation/systemic/policy).",
            "reference": "Breakouts often reflect hedging demand.",
            "interpretation": "- **Up** = hedge demand; **down** in equity bull = cleaner risk-on.",
            "dalio_bridge": "Gold tends to help when policy shifts toward repression / tolerated inflation.",
        },
    },
}

BLOCKS = {
    "price_of_time": {
        "name": "Price of Time",
        "subtitle": "Real/nominal rates and curve shape (monetary stance).",
        "weight": 0.20,
        "indicators": ["real_10y", "nominal_10y", "yield_curve_10_2"],
    },
    "macro": {
        "name": "Macro Cycle",
        "subtitle": "Inflation and growth constraints.",
        "weight": 0.15,
        "indicators": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],
    },
    "conditions": {
        "name": "Conditions & Stress",
        "subtitle": "USD, credit stress, vol, trend, risk appetite.",
        "weight": 0.20,
        "indicators": ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"],
    },
    "plumbing": {
        "name": "Liquidity / Plumbing",
        "subtitle": "System liquidity tailwind vs drain.",
        "weight": 0.15,
        "indicators": ["fed_balance_sheet", "rrp"],
    },
    "debt_fiscal": {
        "name": "Debt & Fiscal (Dalio)",
        "subtitle": "Debt sustainability, fiscal dominance, term premium.",
        "weight": 0.20,
        "indicators": ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"],
    },
    "external": {
        "name": "External Balance",
        "subtitle": "Who funds who: foreign funding constraint.",
        "weight": 0.10,
        "indicators": ["current_account_gdp"],
    },
    "cross": {
        "name": "Cross-Asset Confirmation",
        "subtitle": "Non-weighted confirmation layer.",
        "weight": 0.00,
        "indicators": ["world_equity", "duration_proxy_tlt", "gold"],
    },
}

WALLBOARD_GROUPS = {
    "Market Thermometers": {
        "desc": "Fast-moving regime signals: rates, USD, credit stress, vol, trend, risk appetite.",
        "keys": ["real_10y", "usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"],
    },
    "Liquidity / Plumbing": {
        "desc": "Liquidity tailwind vs drain for risk assets.",
        "keys": ["fed_balance_sheet", "rrp"],
    },
    "Structural Constraints (Dalio)": {
        "desc": "Debt sustainability, term premium, and external funding constraint.",
        "keys": ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "current_account_gdp"],
    },
    "Cross Confirmation": {
        "desc": "Confirmation layer (non-weighted).",
        "keys": ["world_equity", "duration_proxy_tlt", "gold"],
    },
}

# =========================
# DATA: FETCHERS
# =========================
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
        r = requests.get(url, params=params, timeout=14)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        if not obs:
            return pd.Series(dtype=float)
        idx = pd.to_datetime([o["date"] for o in obs])
        vals = []
        for o in obs:
            v = o.get("value", np.nan)
            try:
                vals.append(float(v))
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
    out = {}
    for t in tickers:
        out[t] = fetch_yf_one(t, start_date)
    return out

# =========================
# SCORING + DELTAS
# =========================
def pct_change_over_days(series: pd.Series, days: int) -> float:
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
    past_val = past.iloc[-1]
    curr_val = s.iloc[-1]
    if pd.isna(past_val) or pd.isna(curr_val) or past_val == 0:
        return np.nan
    return (curr_val / past_val - 1.0) * 100.0

def rolling_percentile_last(hist: pd.Series, latest: float) -> float:
    h = hist.dropna()
    if len(h) < 10 or pd.isna(latest):
        return np.nan
    return float((h <= latest).mean())

def compute_indicator_score(series: pd.Series, direction: int, scoring_mode: str = "z5y"):
    if series is None or series.empty:
        return np.nan, np.nan, np.nan
    s = series.dropna()
    if len(s) < 20:
        return np.nan, np.nan, float(s.iloc[-1]) if len(s) else np.nan

    latest = float(s.iloc[-1])
    end = s.index.max()

    if scoring_mode == "pct20y":
        start = end - DateOffset(years=20)
        hist = s[s.index >= start]
        if len(hist) < 20:
            hist = s
        p = rolling_percentile_last(hist, latest)  # 0..1
        sig = (p - 0.5) * 4.0  # map to ~[-2,+2]
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
    if status == "risk_on":
        return "Risk-on"
    if status == "risk_off":
        return "Risk-off"
    if status == "neutral":
        return "Neutral"
    return "n/a"

def status_pill_html(status: str) -> str:
    if status == "risk_on":
        return "<span class='pill good'><span class='dot good'></span>Risk-on</span>"
    if status == "risk_off":
        return "<span class='pill bad'><span class='dot bad'></span>Risk-off</span>"
    if status == "neutral":
        return "<span class='pill warn'><span class='dot warn'></span>Neutral</span>"
    return "<span class='pill'><span class='dot warn'></span>n/a</span>"

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
        return f"{v:.1f} bn USD"
    if unit == "":
        return f"{v:.2f}"
    return f"{v:.2f} {unit}"

# =========================
# INSIGHT TITLES (cheap, local heuristics)
# =========================
def insight_title(key: str, series: pd.Series, latest: float, meta: dict, horizon_days: int) -> str:
    d = pct_change_over_days(series, horizon_days)
    d_txt = "" if np.isnan(d) else ("rising" if d > 0 else "falling" if d < 0 else "flat")

    ref = meta.get("ref_line", None)
    above = None
    if ref is not None and not (isinstance(ref, float) and np.isnan(ref)):
        try:
            above = float(latest) > float(ref)
        except Exception:
            above = None

    if key in ("real_10y", "nominal_10y"):
        if above is True:
            return f"Tightening bias: yields above reference ({d_txt})"
        if above is False:
            return f"Easier backdrop: yields below reference ({d_txt})"
        return f"Rates pulse: {d_txt} over ~{horizon_days}d"

    if key == "yield_curve_10_2":
        if above is False:
            return f"Inversion risk: curve below 0 ({d_txt})"
        if above is True:
            return f"Curve normalizing: slope above 0 ({d_txt})"
        return f"Curve signal: {d_txt} over ~{horizon_days}d"

    if key in ("hy_oas",):
        return f"Credit stress is {d_txt} (spreads)"

    if key in ("usd_index",):
        return f"Global conditions: USD is {d_txt}"

    if key in ("vix",):
        if above is True:
            return f"Stress elevated: vol above 20 ({d_txt})"
        if above is False:
            return f"Vol contained: below 20 ({d_txt})"
        return f"Vol regime: {d_txt}"

    if key in ("spy_trend",):
        if above is True:
            return f"Trend supportive: above 200D ({d_txt})"
        if above is False:
            return f"Trend weak: below 200D ({d_txt})"
        return f"Trend check: {d_txt}"

    if key in ("fed_balance_sheet",):
        return f"Liquidity impulse: balance sheet {d_txt}"

    if key in ("rrp",):
        return f"Liquidity release: RRP {d_txt}"

    if key in ("interest_to_receipts", "interest_payments", "deficit_gdp", "term_premium_10y", "current_account_gdp"):
        return f"Constraint signal: {d_txt} vs longer history"

    if key in ("gold",):
        return f"Hedge demand: gold {d_txt}"

    if key in ("world_equity",):
        return f"Global risk tone: {d_txt}"

    if key in ("duration_proxy_tlt",):
        return f"Duration tone: {d_txt}"

    return f"Signal update: {d_txt}"

# =========================
# PLOTTING (Deep Dive + Sparklines)
# =========================
def plot_premium(series: pd.Series, title_text: str, ref_line=None, height: int = 310):
    s = series.dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", line=dict(width=2)))

    if ref_line is not None:
        try:
            fig.add_hline(y=float(ref_line), line_width=1, line_dash="dot", opacity=0.7)
        except Exception:
            pass

    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.01, y=0.99,
        xanchor="left", yanchor="top",
        text=f"<b>{title_text}</b>",
        showarrow=False,
        font=dict(color="rgba(255,255,255,0.93)", size=14),
        bgcolor="rgba(0,0,0,0.15)",
        bordercolor="rgba(255,255,255,0.10)",
        borderwidth=1,
        borderpad=6,
    )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=18, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)", zeroline=False),
        showlegend=False,
        font=dict(color="rgba(255,255,255,0.86)"),
    )
    return fig

def plot_sparkline(series: pd.Series, height: int = 95):
    s = series.dropna()
    if len(s) > 180:
        s = s.iloc[-180:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", line=dict(width=2)))
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig

# =========================
# TILES
# =========================
def render_deep_dive_tile(key: str, series: pd.Series, indicator_scores: dict, horizon_days: int):
    meta = INDICATOR_META[key]
    info = indicator_scores.get(key, {})
    score = info.get("score", np.nan)
    status = info.get("status", "n/a")
    latest = info.get("latest", np.nan)

    d7 = pct_change_over_days(series, 7)
    d30 = pct_change_over_days(series, 30)
    d1y = pct_change_over_days(series, 365)

    score_txt = "n/a" if np.isnan(score) else f"{score:.1f}"
    latest_txt = fmt_value(latest, meta["unit"], meta.get("scale", 1.0))

    mode = meta.get("scoring_mode", "z5y")
    mode_badge = "<span class='pill'>z5y</span>" if mode == "z5y" else "<span class='pill'>pct20y</span>"

    t = insight_title(key, series, latest, meta, horizon_days=horizon_days)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='tile-toprow'>
          <div>
            <div class='tile-title'>{meta["label"]}</div>
            <div class='tile-meta'>Source: {meta["source"]}</div>
          </div>
          <div style='text-align:right'>
            <div>{mode_badge}<span class='pill'>Latest: {latest_txt}</span>{status_pill_html(status)}</div>
            <div class='tiny'>Score: {score_txt} · Δ30d: {("n/a" if np.isnan(d30) else f"{d30:+.1f}%")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("Definition & how to read", expanded=False):
        exp = meta["expander"]
        st.markdown(f"**What it is:** {exp['what']}")
        st.markdown(f"**Reference levels:** {exp['reference']}")
        st.markdown("**Bidirectional interpretation:**")
        st.markdown(exp["interpretation"])
        st.markdown(f"**Dalio bridge:** {exp.get('dalio_bridge','')}")
        st.markdown(
            f"**What changed:** "
            f"{'n/a' if np.isnan(d7) else f'{d7:+.1f}%'} (7d), "
            f"{'n/a' if np.isnan(d30) else f'{d30:+.1f}%'} (30d), "
            f"{'n/a' if np.isnan(d1y) else f'{d1y:+.1f}%'} (1Y)"
        )

    fig = plot_premium(series, title_text=t, ref_line=meta.get("ref_line", None), height=310)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
        key=f"deep_{key}_{horizon_days}"
    )
    st.markdown("</div>", unsafe_allow_html=True)

def wallboard_card(ind_key: str, series: pd.Series, indicator_scores: dict, instance_id: str = "0"):
    meta = INDICATOR_META[ind_key]
    info = indicator_scores.get(ind_key, {})
    score = info.get("score", np.nan)
    status = info.get("status", "n/a")
    latest = info.get("latest", np.nan)

    latest_txt = fmt_value(latest, meta["unit"], meta.get("scale", 1.0))
    score_txt = "n/a" if np.isnan(score) else f"{score:.0f}"
    d30 = pct_change_over_days(series, 30)
    d30_txt = "n/a" if np.isnan(d30) else f"{d30:+.1f}%"

    st.markdown("<div class='wb-card'>", unsafe_allow_html=True)
    st.markdown(f"<h4>{meta['label']}</h4>", unsafe_allow_html=True)
    st.markdown(f"<div class='wb-source'>{meta['source']}</div>", unsafe_allow_html=True)

    if series is not None and not series.dropna().empty:
        st.plotly_chart(
            plot_sparkline(series, height=95),
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"spark_{ind_key}_{instance_id}"
        )
    else:
        st.markdown("<div class='wb-line'>Missing data</div>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="display:flex; align-items:flex-end; justify-content:space-between; gap:10px; margin-top:10px;">
          <div>
            <div class="wb-value">{latest_txt}</div>
            <div class="wb-line">Δ30d: <b>{d30_txt}</b></div>
          </div>
          <div style="text-align:right;">
            {status_pill_html(status)}
            <div class="wb-line" style="margin-top:8px;">Score: <b>{score_txt}</b></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# ETF OPERATING LINES
# =========================
def operating_lines(block_scores: dict, indicator_scores: dict):
    gs = block_scores.get("GLOBAL", {}).get("score", np.nan)

    def _sg(x):
        if np.isnan(x): return np.nan
        return float(x)

    cond = _sg(block_scores.get("conditions", {}).get("score", np.nan))
    pot = _sg(block_scores.get("price_of_time", {}).get("score", np.nan))
    macro = _sg(block_scores.get("macro", {}).get("score", np.nan))
    debt = _sg(block_scores.get("debt_fiscal", {}).get("score", np.nan))

    if np.isnan(gs) or np.isnan(cond):
        equity = "n/a"
    elif gs >= 60 and cond >= 55:
        equity = "↑ Increase — risk budget can rise (still watch credit)"
    elif gs <= 40 or cond <= 40:
        equity = "↓ Reduce — prioritize defense/quality"
    else:
        equity = "→ Neutral — moderate sizing"

    termp = _sg(indicator_scores.get("term_premium_10y", {}).get("score", np.nan))
    infl = _sg(indicator_scores.get("cpi_yoy", {}).get("score", np.nan))

    if not np.isnan(termp) and termp <= 40 and (not np.isnan(infl) and infl <= 45):
        duration = "Short/Neutral — avoid long nominals; prefer quality/TIPS tilt"
    elif (not np.isnan(pot) and pot <= 40) and (not np.isnan(infl) and infl <= 45) and (not np.isnan(termp) and termp >= 55):
        duration = "Long (hedge) — disinflation + duration hedge improves"
    else:
        duration = "Neutral — balance term-premium risk vs cycle"

    hy = _sg(indicator_scores.get("hy_oas", {}).get("score", np.nan))
    hyg = _sg(indicator_scores.get("hyg_lqd_ratio", {}).get("score", np.nan))
    ds = _sg(indicator_scores.get("interest_to_receipts", {}).get("score", np.nan))

    if (not np.isnan(hy) and hy <= 40) or (not np.isnan(hyg) and hyg <= 40) or (not np.isnan(ds) and ds <= 40):
        credit = "IG > HY — reduce default/funding risk"
    elif (not np.isnan(hy) and hy >= 60) and (not np.isnan(hyg) and hyg >= 60) and (np.isnan(ds) or ds >= 50):
        credit = "Selective HY — opportunistic sizing"
    else:
        credit = "Neutral — quality bias with selectivity"

    usd = _sg(indicator_scores.get("usd_index", {}).get("score", np.nan))
    if (not np.isnan(debt) and debt <= 40) and (not np.isnan(infl) and infl >= 55):
        hedges = "Gold / real-asset tilt — repression/inflation risk"
    elif (not np.isnan(usd) and usd <= 40) and (not np.isnan(cond) and cond <= 45):
        hedges = "USD / cash-like — funding stress"
    else:
        hedges = "Light mix — cash-like + tactical gold"

    return equity, duration, credit, hedges

# =========================
# MAIN
# =========================
def main():
    st.title("Global Finance | Macro Overview (Dalio-enhanced)")
    st.markdown(
        "<div class='muted'>Macro-first dashboard: keeps market thermometers, adds Dalio-style structural constraints (debt/fiscal dominance/external balance) to track regime shifts.</div>",
        unsafe_allow_html=True
    )

    st.sidebar.header("Settings")
    layout_mode = st.sidebar.selectbox(
        "Layout mode",
        ["Auto (responsive)", "Wallboard (55\")", "Compact (mobile)"],
        index=1
    )

    years_back = st.sidebar.slider("History window (years)", 5, 30, 15)
    today = datetime.now(timezone.utc).date()
    start_date = (today - DateOffset(years=years_back)).date().isoformat()
    st.sidebar.markdown(f"**Start date:** {start_date}")

    horizon_days = st.sidebar.selectbox("Insight horizon for chart titles", [30, 90, 180], index=0)

    if st.sidebar.button("🔄 Refresh data (clear cache)"):
        st.cache_data.clear()
        st.rerun()

    fred_key = get_fred_api_key()
    if fred_key is None:
        st.sidebar.error("⚠️ Missing `FRED_API_KEY` in Streamlit secrets.")

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
        if ip is not None and fr is not None and (not ip.empty) and (not fr.empty):
            join = ip.to_frame("interest").join(fr.to_frame("receipts"), how="inner").dropna()
            join = join[join["receipts"] != 0]
            indicators["interest_to_receipts"] = (join["interest"] / join["receipts"]).dropna()
        else:
            indicators["interest_to_receipts"] = pd.Series(dtype=float)

        yf_map = fetch_yf_many(["DX-Y.NYB", "^VIX", "SPY", "HYG", "LQD", "URTH", "TLT", "GLD"], start_date)

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

        indicators["world_equity"] = yf_map.get("URTH", pd.Series(dtype=float))
        indicators["duration_proxy_tlt"] = yf_map.get("TLT", pd.Series(dtype=float))
        indicators["gold"] = yf_map.get("GLD", pd.Series(dtype=float))

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
        bstatus = classify_status(bscore)
        block_scores[bkey] = {"score": bscore, "status": bstatus}

        if bkey != "cross" and binfo["weight"] > 0 and not np.isnan(bscore):
            global_score += bscore * binfo["weight"]
            w_used += binfo["weight"]

    global_score = (global_score / w_used) if w_used > 0 else np.nan
    global_status = classify_status(global_score)
    block_scores["GLOBAL"] = {"score": global_score, "status": global_status}

    latest_points = [s.index.max() for s in indicators.values() if s is not None and not s.empty]
    data_max_date = max(latest_points) if latest_points else None

    st.markdown(
        f"""
<div class="section-card">
  <div class="tiny">
    <b>Regime legend:</b>
    {status_pill_html("risk_on")} = easing / risk appetite dominates (higher equity beta tolerable) ·
    {status_pill_html("neutral")} = mixed signals (moderate sizing) ·
    {status_pill_html("risk_off")} = tightening / stress dominates (favor quality, reduce beta).
  </div>
</div>
        """,
        unsafe_allow_html=True
    )

    tabs = st.tabs(["Overview", "Wallboard", "Deep Dive", "What changed", "Report"])

    with tabs[0]:
        left, right = st.columns([2.2, 1.0])

        with left:
            st.markdown("### Executive Snapshot")
            gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
            eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)

            def block_line(bkey: str):
                sc = block_scores.get(bkey, {}).get("score", np.nan)
                stt = block_scores.get(bkey, {}).get("status", "n/a")
                sc_txt = "n/a" if np.isnan(sc) else f"{sc:.1f}"
                return f"{BLOCKS[bkey]['name']}: {status_pill_html(stt)} <b>({sc_txt})</b>"

            thermo_lines = [block_line(k) for k in ["price_of_time", "macro", "conditions", "plumbing"]]
            struct_lines = [block_line(k) for k in ["debt_fiscal", "external"]]

            st.markdown(
                f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-title">Global Score (0–100) — 6 core blocks</div>
    <div class="kpi-value">{gs_txt}</div>
    <div class="kpi-sub">{status_pill_html(global_status)}</div>
    <div class="kpi-sub">
      <b>Equity:</b> {eq_line}<br/>
      <b>Duration:</b> {dur_line}<br/>
      <b>Credit:</b> {cr_line}<br/>
      <b>Hedges:</b> {hdg_line}
    </div>
  </div>

  <div class="kpi-card">
    <div class="kpi-title">Block scores — name → regime → score</div>
    <div class="kpi-sub"><b>Market thermometers</b><br/>{'<br/>'.join(thermo_lines)}</div>
    <hr/>
    <div class="kpi-sub"><b>Structural constraints</b><br/>{'<br/>'.join(struct_lines)}</div>
  </div>

  <div class="kpi-card">
    <div class="kpi-title">Dalio bridges (one-liners)</div>
    <div class="kpi-sub">
      1) <b>Deficit ↑ → supply ↑ → term premium ↑ → duration suffers</b><br/>
      2) <b>Term premium ↑ + USD ↑ → global tightening → risk-off</b><br/>
      3) <b>Debt service ↑ → political pressure → repression risk</b><br/>
      4) <b>Repression → compressed real rates → real assets hedge</b><br/>
      5) <b>External deficits → foreign funding reliance → vulnerability</b>
    </div>
  </div>
</div>
                """,
                unsafe_allow_html=True
            )

        with right:
            st.markdown("### Info")
            now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='tiny'>Now: <b>{now_utc}</b></div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='tiny'>Latest datapoint: <b>{('n/a' if data_max_date is None else str(pd.to_datetime(data_max_date).date()))}</b></div>",
                unsafe_allow_html=True
            )
            st.markdown(f"<div class='tiny'>Layout mode: <b>{layout_mode}</b></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("How scoring works (clear & investor-friendly)", expanded=False):
                st.markdown(
                    """
**What the score means (0–100):** a normalized “risk regime” signal.

- **Market thermometers (z5y):** fast-moving series (rates, USD, spreads, vol, trend).  
  We compute a **5Y z-score**, clamp to **[-2,+2]**, then map to **0–100**.
- **Structural constraints (pct20y):** slower constraints (debt service, deficit, term premium, external balance).  
  We compute a **~20Y percentile**, map it to **[-2,+2]**, then to **0–100**.
- **Thresholds:**  
  - **>60 = Risk-on** (easier conditions / risk appetite dominates)  
  - **40–60 = Neutral** (mixed signals)  
  - **<40 = Risk-off** (tightening / stress dominates)

**How to use it (ETF lens):**  
Global score sets the *risk budget*, while **Debt/Fiscal + Term premium** tells you whether long nominal duration is a *reliable hedge* or a *funding risk*.
                    """.strip()
                )

    with tabs[1]:
        st.markdown("## Wallboard (grouped, consistent)")
        gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
        eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)

        thermo_keys = ["price_of_time", "macro", "conditions", "plumbing"]
        struct_keys = ["debt_fiscal", "external"]

        def block_line_plain(bkey: str):
            sc = block_scores.get(bkey, {}).get("score", np.nan)
            stt = block_scores.get(bkey, {}).get("status", "n/a")
            sc_txt = "n/a" if np.isnan(sc) else f"{sc:.1f}"
            return f"{BLOCKS[bkey]['name']}: {status_label(stt)} ({sc_txt})"

        st.markdown("<div class='wb-hero'>", unsafe_allow_html=True)
        c1, c2 = st.columns([1.15, 1.0])
        with c1:
            st.markdown("<div class='tiny' style='color:rgba(255,255,255,0.75)'>Global Score</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:3.2rem; font-weight:900; line-height:1.0'>{gs_txt}</div>", unsafe_allow_html=True)
            st.markdown(status_pill_html(global_status), unsafe_allow_html=True)

            st.markdown("<div class='tiny' style='margin-top:10px; color:rgba(255,255,255,0.75)'><b>Block summary (name → regime → score)</b></div>", unsafe_allow_html=True)
            st.markdown("<div class='tiny' style='margin-top:6px'><b>Market thermometers</b></div>", unsafe_allow_html=True)
            st.markdown("<div class='tiny'>" + "<br/>".join([block_line_plain(k) for k in thermo_keys]) + "</div>", unsafe_allow_html=True)

            st.markdown("<div class='tiny' style='margin-top:12px'><b>Structural constraints</b></div>", unsafe_allow_html=True)
            st.markdown("<div class='tiny'>" + "<br/>".join([block_line_plain(k) for k in struct_keys]) + "</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='tiny' style='color:rgba(255,255,255,0.75)'><b>Operating lines (ETF)</b></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
<div class="tiny" style="margin-top:6px; line-height:1.65">
<b>Equity</b>: {eq_line}<br/>
<b>Duration</b>: {dur_line}<br/>
<b>Credit</b>: {cr_line}<br/>
<b>Hedges</b>: {hdg_line}
</div>
                """,
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

        if layout_mode == "Wallboard (55\")":
            cols = 4
        elif layout_mode == "Compact (mobile)":
            cols = 2
        else:
            cols = 3

        for gname, ginfo in WALLBOARD_GROUPS.items():
            st.markdown(f"### {gname}")
            st.markdown(f"<div class='muted'>{ginfo['desc']}</div>", unsafe_allow_html=True)

            keys = ginfo["keys"]
            rows = [keys[i:i+cols] for i in range(0, len(keys), cols)]
            for r_i, r in enumerate(rows):
                c = st.columns(cols)
                for idx in range(cols):
                    if idx < len(r):
                        k = r[idx]
                        s = indicators.get(k, pd.Series(dtype=float))
                        with c[idx]:
                            if s is None or s.empty:
                                st.markdown("<div class='wb-card'>", unsafe_allow_html=True)
                                st.markdown(f"<h4>{INDICATOR_META[k]['label']}</h4>", unsafe_allow_html=True)
                                st.markdown(f"<div class='wb-source'>{INDICATOR_META[k]['source']}</div>", unsafe_allow_html=True)
                                st.markdown("<div class='wb-line'><b>Missing:</b> no data available</div>", unsafe_allow_html=True)
                                st.markdown("</div>", unsafe_allow_html=True)
                            else:
                                # instance_id ensures uniqueness even if same chart appears elsewhere
                                wallboard_card(k, s, indicator_scores, instance_id=f"group_{gname}_{r_i}_{idx}")
                    else:
                        with c[idx]:
                            st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)

        with st.expander("Show all indicators (still readable when expanded)", expanded=False):
            cols2 = 3 if layout_mode != "Compact (mobile)" else 2
            all_keys = list(INDICATOR_META.keys())
            rows = [all_keys[i:i+cols2] for i in range(0, len(all_keys), cols2)]
            for r_i, r in enumerate(rows):
                c = st.columns(cols2)
                for i, k in enumerate(r):
                    with c[i]:
                        s = indicators.get(k, pd.Series(dtype=float))
                        if s is None or s.empty:
                            st.caption(f"{INDICATOR_META[k]['label']} — missing")
                        else:
                            wallboard_card(k, s, indicator_scores, instance_id=f"all_{r_i}_{i}")

    with tabs[2]:
        st.markdown("## Deep Dive (charts)")

        if layout_mode == "Wallboard (55\")":
            per_row = 2
        elif layout_mode == "Compact (mobile)":
            per_row = 1
        else:
            per_row = 2

        for bkey in ["price_of_time", "macro", "conditions", "plumbing", "debt_fiscal", "external", "cross"]:
            b = BLOCKS[bkey]
            st.markdown(f"### {b['name']}")
            st.markdown(f"<div class='muted'>{b['subtitle']}</div>", unsafe_allow_html=True)

            bscore = block_scores[bkey]["score"]
            bstatus = block_scores[bkey]["status"]
            bscore_txt = "n/a" if np.isnan(bscore) else f"{bscore:.1f}"
            st.markdown(
                f"<div class='section-card'><div class='tiny'>Block score: <b>{bscore_txt}</b> {status_pill_html(bstatus)}</div></div>",
                unsafe_allow_html=True
            )

            keys = b["indicators"]
            rows = [keys[i:i+per_row] for i in range(0, len(keys), per_row)]
            for r in rows:
                cols = st.columns(per_row)
                for i, k in enumerate(r):
                    with cols[i]:
                        s = indicators.get(k, pd.Series(dtype=float))
                        if s is None or s.empty:
                            st.warning(f"Missing data for {INDICATOR_META[k]['label']}.")
                        else:
                            render_deep_dive_tile(k, s, indicator_scores, horizon_days=horizon_days)

    with tabs[3]:
        st.markdown("## What changed — Δ 7d / 30d / 1Y")
        st.markdown(
            "<div class='muted'>Use this table to spot *drivers* of the score change. "
            "Δ columns tell you momentum; Score/Regime tell you what that implies for risk.</div>",
            unsafe_allow_html=True
        )

        with st.expander("Column guide (why each column matters)", expanded=False):
            st.markdown(
                """
- **Δ 7d / Δ 30d / Δ 1Y**: short/medium/long momentum (what is *accelerating* vs what is structural).
- **Score**: normalized risk signal (0–100) after direction + scaling.
- **Regime**: quick interpretation: Risk-on / Neutral / Risk-off.
- **Scoring**: `z5y` = market thermometers; `pct20y` = structural constraints.
                """.strip()
            )

        rows = []
        for key, meta in INDICATOR_META.items():
            s = indicators.get(key, pd.Series(dtype=float))
            if s is None or s.empty:
                continue
            d7 = pct_change_over_days(s, 7)
            d30 = pct_change_over_days(s, 30)
            d1y = pct_change_over_days(s, 365)
            rows.append(
                {
                    "Indicator": meta["label"],
                    "Scoring": meta.get("scoring_mode", "z5y"),
                    "Δ 7d (%)": None if np.isnan(d7) else round(d7, 2),
                    "Δ 30d (%)": None if np.isnan(d30) else round(d30, 2),
                    "Δ 1Y (%)": None if np.isnan(d1y) else round(d1y, 2),
                    "Score": None if np.isnan(indicator_scores[key]["score"]) else round(indicator_scores[key]["score"], 1),
                    "Regime": status_label(indicator_scores[key]["status"]),
                }
            )

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Indicator": st.column_config.TextColumn("Indicator", width="large", help="The metric being monitored."),
                    "Scoring": st.column_config.TextColumn("Scoring", width="small", help="z5y = fast thermometers; pct20y = structural constraints."),
                    "Δ 7d (%)": st.column_config.NumberColumn("Δ 7d (%)", format="%.2f", width="small", help="Short-term momentum (tactical drivers)."),
                    "Δ 30d (%)": st.column_config.NumberColumn("Δ 30d (%)", format="%.2f", width="small", help="1-month momentum (regime drift)."),
                    "Δ 1Y (%)": st.column_config.NumberColumn("Δ 1Y (%)", format="%.2f", width="small", help="Longer trend (structural drift)."),
                    "Score": st.column_config.NumberColumn("Score", format="%.1f", width="small", help="Normalized risk signal (0–100)."),
                    "Regime": st.column_config.TextColumn("Regime", width="small", help="Quick interpretation of the score."),
                }
            )

            st.markdown(
                "<div class='section-card'><div class='tiny'>"
                "<b>How to use this:</b> start from the indicators with the biggest Δ30d (or Δ7d for tactical moves), "
                "then check whether they are <b>thermometers</b> (z5y) or <b>constraints</b> (pct20y). "
                "Constraints moving can signal a regime shift even if thermometers look calm.</div></div>",
                unsafe_allow_html=True
            )
        else:
            st.info("Not enough data to compute deltas yet.")

    with tabs[4]:
        st.markdown("## Report (optional) — Payload for ChatGPT")
        st.markdown(
            "<div class='muted'>Copy/paste payload into an AI chat to generate a multi-page narrative (with smarter titles/interpretation) "
            "without adding paid APIs inside this dashboard.</div>",
            unsafe_allow_html=True
        )

        generate_payload = st.button("Generate payload", key="btn_generate_payload")

        if generate_payload:
            payload_lines = []
            payload_lines.append("macro_regime_payload_dalio:")
            payload_lines.append(f"  generated_at_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            payload_lines.append(f"  global_score: {0.0 if np.isnan(global_score) else round(global_score, 1)}")
            payload_lines.append(f"  global_status: {status_label(global_status)}")
            payload_lines.append('  scoring_notes: "market thermometers use z5y; structural constraints use pct20y"')

            payload_lines.append("  blocks:")
            for bkey, binfo in BLOCKS.items():
                if bkey == "cross":
                    continue
                bscore = block_scores[bkey]["score"]
                bstatus = block_scores[bkey]["status"]
                payload_lines.append(f'    - key: "{bkey}"')
                payload_lines.append(f'      name: "{binfo["name"]}"')
                payload_lines.append(f"      weight: {binfo['weight']}")
                payload_lines.append(f"      score: {0.0 if np.isnan(bscore) else round(bscore, 1)}")
                payload_lines.append(f'      status: "{status_label(bstatus)}"')

            payload_lines.append("  operating_lines:")
            eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)
            payload_lines.append(f'    equity_risk_budget: "{eq_line}"')
            payload_lines.append(f'    duration_stance: "{dur_line}"')
            payload_lines.append(f'    credit_stance: "{cr_line}"')
            payload_lines.append(f'    hedges: "{hdg_line}"')

            payload_lines.append("  indicators:")
            for key, meta in INDICATOR_META.items():
                s_info = indicator_scores.get(key, {})
                score = s_info.get("score", np.nan)
                status = s_info.get("status", "n/a")
                latest = s_info.get("latest", np.nan)
                series = indicators.get(key, pd.Series(dtype=float))
                d30 = pct_change_over_days(series, 30)
                mode = meta.get("scoring_mode", "z5y")

                payload_lines.append(f'    - name: "{meta["label"]}"')
                payload_lines.append(f'      key: "{key}"')
                payload_lines.append(f'      scoring_mode: "{mode}"')
                payload_lines.append(f'      latest_value: "{fmt_value(latest, meta["unit"], meta.get("scale", 1.0))}"')
                payload_lines.append(f"      score: {0.0 if np.isnan(score) else round(score, 1)}")
                payload_lines.append(f'      status: "{status_label(status)}"')
                payload_lines.append(f"      delta_30d_pct: {0.0 if np.isnan(d30) else round(d30, 2)}")

            payload_text = "\n".join(payload_lines)
            st.code(payload_text, language="yaml")

            st.markdown("**Suggested prompt (Dalio-aware, multi-page):**")
            st.code(
                """
You are a multi-asset macro strategist. You receive the YAML payload above from a Dalio-enhanced macro dashboard.

Tasks:
1) Reconstruct the regime. Explicitly separate:
   - Market thermometers (rates/USD/spreads/VIX/trend/liquidity; z5y)
   - Structural constraints (debt service/deficit/term premium/external balance; pct20y)
2) Explain whether there is a risk of a structural regime shift:
   - fiscal dominance / financial repression
   - inflationary deleveraging vs deflationary deleveraging
3) Produce an ETF-implementable plan:
   - Equity exposure (risk budget)
   - Duration (short/neutral/long; nominal vs TIPS)
   - Credit (IG vs HY)
   - Hedges (USD, gold, cash-like)
4) Provide 3–5 triggers to monitor over the next 2–6 weeks (heuristic thresholds).

Style: concrete, prudent, implementable. Use chart-title style “so-what” headings for each indicator section.
                """.strip(),
                language="markdown"
            )

if __name__ == "__main__":
    main()
