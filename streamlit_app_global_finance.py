import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from pandas.tseries.offsets import DateOffset


# =========================
# PAGE CONFIG + PREMIUM CSS
# =========================

st.set_page_config(
    page_title="Global Finance | Macro Overview (Dalio-Enhanced)",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root{
        --bg:#0b0f19;
        --card:#0f1629;
        --card2:#0c1324;
        --border:rgba(255,255,255,0.10);
        --border2:rgba(255,255,255,0.18);
        --muted:rgba(255,255,255,0.68);
        --text:rgba(255,255,255,0.94);
        --text2:rgba(255,255,255,0.88);
        --accent:rgba(99,102,241,1);
        --good:rgba(34,197,94,1);
        --warn:rgba(245,158,11,1);
        --bad:rgba(239,68,68,1);
      }

      .stApp {
        background: radial-gradient(1200px 700px at 20% 0%, #121a33 0%, #0b0f19 45%, #0b0f19 100%);
        color: var(--text);
      }
      .block-container { padding-top: 1.1rem; }

      h1, h2, h3, h4 { color: var(--text); letter-spacing: -0.02em; }
      .muted { color: var(--muted); }

      .kpi-grid {
        display:grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
      }
      .kpi-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.03) 100%);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px 16px 12px 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
      }
      .kpi-title { font-size: 0.95rem; color: var(--muted); margin-bottom: 6px; }
      .kpi-value { font-size: 2.0rem; font-weight: 780; line-height: 1.05; color: var(--text); }
      .kpi-sub { margin-top: 6px; font-size: 0.95rem; color: var(--muted); }

      .pill {
        display:inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.04);
        font-size: 0.85rem;
        color: var(--text2);
        margin-right: 8px;
      }
      .pill.good { border-color: rgba(34,197,94,0.42); background: rgba(34,197,94,0.12); }
      .pill.warn { border-color: rgba(245,158,11,0.42); background: rgba(245,158,11,0.12); }
      .pill.bad  { border-color: rgba(239,68,68,0.42);  background: rgba(239,68,68,0.12); }

      .section-card {
        background: rgba(255,255,255,0.035);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 14px 14px 10px 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
        margin-bottom: 12px;
      }

      /* Stronger visual separation for charts */
      .stPlotlyChart > div {
        border: 1px solid var(--border2);
        border-radius: 16px;
        background: rgba(255,255,255,0.022);
        padding: 8px 10px 6px 10px;
        box-shadow: 0 16px 44px rgba(0,0,0,0.30);
      }

      /* Compact tile for wallboard */
      .wb-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.025) 100%);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 12px 12px 10px 12px;
        box-shadow: 0 10px 28px rgba(0,0,0,0.24);
        margin-bottom: 10px;
      }
      .wb-title { font-size: 0.92rem; font-weight: 700; color: var(--text); line-height: 1.2; }
      .wb-meta  { font-size: 0.80rem; color: var(--muted); margin-top: 2px; }
      .wb-row { display:flex; align-items:baseline; justify-content:space-between; gap: 10px; margin-top: 8px; }
      .wb-big { font-size: 1.55rem; font-weight: 820; color: var(--text); letter-spacing: -0.01em; }
      .wb-small { font-size: 0.85rem; color: var(--muted); }

      hr { border-color: var(--border); }
      button[data-baseweb="tab"] { color: var(--muted) !important; }
      button[data-baseweb="tab"][aria-selected="true"]{ color: var(--text) !important; }

      .stDataFrame { border: 1px solid var(--border); border-radius: 12px; overflow:hidden; }
      code { color: rgba(255,255,255,0.88); }

      /* A slightly more compact overall look on very wide screens */
      @media (min-width: 1700px){
        .block-container { padding-left: 1.2rem; padding-right: 1.2rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# INDICATORS & BLOCKS
# =========================

INDICATOR_META = {
    # 1) PRICE OF TIME
    "real_10y": {
        "label": "US 10Y TIPS Real Yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DFII10",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "10Y real yield (TIPS): the price of time net of inflation expectations.",
            "reference": "<0% very easy; 0–2% neutral; >2% restrictive (heuristics).",
            "interpretation": (
                "- **Real yield up** → headwind for equities (especially growth) and long duration.\n"
                "- **Real yield down** → tailwind for risk assets; duration more defensive."
            ),
            "dalio_bridge": "Higher real yields tighten the funding constraint system-wide.",
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
            "what": "10Y Treasury nominal yield: benchmark discount rate and broad financial conditions.",
            "reference": "Fast moves higher often translate into financial tightening.",
            "interpretation": (
                "- **Up fast** → pressure on equities and existing bonds.\n"
                "- **Down** → supports duration; equities benefit if it’s not growth collapsing."
            ),
            "dalio_bridge": "Higher yields can reflect inflation, term premium, or both.",
        },
    },
    "yield_curve_10_2": {
        "label": "US Yield Curve (10Y–2Y)",
        "unit": "pp",
        "direction": +1,
        "source": "Derived (DGS10 - DGS2)",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "10Y–2Y slope: cycle proxy (growth expectations vs policy stance).",
            "reference": "<0 inverted (late cycle); >0 normal (heuristics).",
            "interpretation": (
                "- **Deeply negative** and persistent → higher recession risk / risk-off.\n"
                "- **Re-steepening above 0** → cycle normalization."
            ),
            "dalio_bridge": "Inversion often precedes deleveraging phases as policy stays tight vs the cycle.",
        },
    },

    # 2) MACRO
    "breakeven_10y": {
        "label": "10Y Breakeven Inflation",
        "unit": "%",
        "direction": -1,
        "source": "FRED T10YIE",
        "scale": 1.0,
        "ref_line": 2.5,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Market-implied inflation expectation (10Y): nominal vs TIPS.",
            "reference": "~2–3% anchored; >3% sticky inflation risk (heuristics).",
            "interpretation": (
                "- **Up** → higher risk of restrictive policy for longer.\n"
                "- **Down toward target** → more room for easing."
            ),
            "dalio_bridge": "Higher inflation expectations increase the odds of financial repression in debt stress.",
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
            "reference": "Fed target ~2%; sustained >3–4% = sticky (heuristics).",
            "interpretation": (
                "- **Disinflation** → supportive for duration and (often) equities.\n"
                "- **Re-acceleration** → tightening risk / higher-for-longer."
            ),
            "dalio_bridge": "Persistent inflation is the key constraint: less room for bailouts.",
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
            "what": "Labor slack proxy: cycle and recession probability.",
            "reference": "Fast rises often coincide with slowdown/recession.",
            "interpretation": (
                "- **Up quickly** → growth scare / risk-off.\n"
                "- **Stable** → more benign backdrop."
            ),
            "dalio_bridge": "Slack rising with high debt increases political pressure for support (fiscal dominance risk).",
        },
    },

    # 3) CONDITIONS & STRESS
    "usd_index": {
        "label": "USD Index (DXY / Broad Proxy)",
        "unit": "",
        "direction": -1,
        "source": "yfinance DX-Y.NYB (fallback FRED DTWEXBGS)",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Dollar strength proxy. If DXY is missing, uses FRED broad trade-weighted USD index.",
            "reference": "Strong USD = tighter global financial conditions (heuristic).",
            "interpretation": (
                "- **USD up** → global tightening / pressure on risk assets.\n"
                "- **USD down** → easier conditions."
            ),
            "dalio_bridge": "USD up = global funding stress up (especially for USD debt).",
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
            "what": "High yield spread: credit stress / default risk pricing.",
            "reference": "<4% often benign; >6–7% stress (heuristics).",
            "interpretation": (
                "- **Up** → risk-off (credit stress).\n"
                "- **Down** → risk appetite improves."
            ),
            "dalio_bridge": "Credit stress up accelerates deleveraging (non-linear).",
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
            "what": "S&P 500 implied volatility.",
            "reference": "<15 low; 15–25 normal; >25 stress (heuristics).",
            "interpretation": (
                "- **Up** → risk-off.\n"
                "- **Down** → risk-on."
            ),
            "dalio_bridge": "Higher vol tightens conditions even without policy hikes (risk premia up).",
        },
    },
    "spy_trend": {
        "label": "SPY Trend (Price / 200d MA)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance SPY",
        "scale": 1.0,
        "ref_line": 1.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Trend proxy: SPY vs its 200-day moving average.",
            "reference": ">1 bull trend; <1 downtrend (heuristics).",
            "interpretation": (
                "- **>1** → risk-on confirmation.\n"
                "- **<1** → risk-off confirmation."
            ),
            "dalio_bridge": "Trend down + credit stress up often marks deleveraging phases.",
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
            "what": "HY vs IG ratio: appetite for credit risk.",
            "reference": "Up = more HY appetite; down = flight-to-quality.",
            "interpretation": (
                "- **Up** → risk-on.\n"
                "- **Down** → risk-off."
            ),
            "dalio_bridge": "Flight-to-quality signals tightening funding constraints.",
        },
    },

    # 4) PLUMBING
    "fed_balance_sheet": {
        "label": "Fed Balance Sheet (WALCL)",
        "unit": "bn USD",
        "direction": +1,
        "source": "FRED WALCL (millions USD → bn USD)",
        "scale": 1.0 / 1000.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Fed assets: system liquidity proxy (QE vs QT).",
            "reference": "Expansion supports risk assets; contraction drains liquidity (heuristics).",
            "interpretation": (
                "- **Up** → more liquidity (tailwind).\n"
                "- **Down** → liquidity drain (headwind)."
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
            "what": "Reverse repo usage: liquidity parked risk-free.",
            "reference": "Higher = liquidity stuck; falling = liquidity released (heuristics).",
            "interpretation": (
                "- **Up** → less fuel for risk.\n"
                "- **Down** → potential tailwind."
            ),
            "dalio_bridge": "RRP falling often releases marginal liquidity.",
        },
    },

    # 5) DALIO CORE
    "interest_payments": {
        "label": "US Federal Interest Payments (Quarterly)",
        "unit": "bn USD",
        "direction": -1,
        "source": "FRED A091RC1Q027SBEA",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Federal interest payments: debt service pressure.",
            "reference": "Stress rises when the trend accelerates and becomes a political constraint.",
            "interpretation": (
                "- **Up persistently** → higher odds of fiscal dominance / repression.\n"
                "- **Down** → debt constraint more manageable."
            ),
            "dalio_bridge": "Debt service up increases incentives for repression/monetization.",
        },
    },
    "federal_receipts": {
        "label": "US Federal Receipts (Quarterly)",
        "unit": "bn USD",
        "direction": +1,
        "source": "FRED FGRECPT",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Federal current receipts: used to assess debt service sustainability.",
            "reference": "Higher receipts help offset interest burden (heuristic).",
            "interpretation": (
                "- **Up** (vs interest) → sustainability improves.\n"
                "- **Down** → fiscal constraint tightens."
            ),
            "dalio_bridge": "Interest/receipts rising = the debt is 'getting heavy'.",
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
        "expander": {
            "what": "Sustainability proxy: share of receipts consumed by interest.",
            "reference": "High and accelerating values = fiscal/political constraint (heuristic).",
            "interpretation": (
                "- **Up** → higher odds policy shifts toward funding support.\n"
                "- **Down** → more policy room."
            ),
            "dalio_bridge": "Higher debt service increases incentives to tolerate inflation / compress real rates.",
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
            "reference": "Persistent deficits = persistent Treasury supply (heuristic).",
            "interpretation": (
                "- **More negative** → upward pressure on term premium/funding.\n"
                "- **Improving** → reduces structural pressure."
            ),
            "dalio_bridge": "Deficit up → supply up → term premium up → long duration suffers.",
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
            "what": "Term premium: compensation demanded to hold nominal duration.",
            "reference": "Up = long nominal duration less reliable (heuristic).",
            "interpretation": (
                "- **Up** → higher risk in long nominal bonds.\n"
                "- **Down** → duration becomes a better hedge again."
            ),
            "dalio_bridge": "When term premium rises on supply/funding, duration can stop hedging.",
        },
    },

    # 6) EXTERNAL
    "current_account_gdp": {
        "label": "US Current Account Balance (% of GDP)",
        "unit": "%",
        "direction": +1,
        "source": "FRED USAB6BLTT02STSAQ",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Current account balance: negative = reliance on foreign capital.",
            "reference": "Persistent deficit = vulnerability when USD funding tightens (heuristic).",
            "interpretation": (
                "- **More negative** → external reliance up.\n"
                "- **Toward 0 / positive** → constraint eases."
            ),
            "dalio_bridge": "External deficits amplify vulnerability during global tightening.",
        },
    },

    # CROSS (non-weighted)
    "world_equity": {
        "label": "Global Equities (URTH)",
        "unit": "",
        "direction": +1,
        "source": "yfinance URTH",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Global equity proxy: confirms regime beyond the US.",
            "reference": "Trend/drawdown as confirmation or contradiction.",
            "interpretation": (
                "- **Trend up** → risk-on confirmation.\n"
                "- **Trend down** → risk-off confirmation."
            ),
            "dalio_bridge": "If global equities roll over, risk may be structural.",
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
            "what": "Long-duration Treasuries proxy (classic risk-off hedge).",
            "reference": "Rallies often coincide with flight-to-quality.",
            "interpretation": (
                "- **TLT up** → often risk-off / easing expectations.\n"
                "- **TLT down** with yields up → duration headwind."
            ),
            "dalio_bridge": "If TLT fails to hedge, term premium / inflationary deleveraging risk may be rising.",
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
            "what": "Gold: hedge against inflation/shocks/systemic risk.",
            "reference": "Breakouts often signal hedging demand.",
            "interpretation": (
                "- **Gold up** → hedging demand.\n"
                "- **Gold down** in equity bull → cleaner risk-on."
            ),
            "dalio_bridge": "Gold often works when policy shifts toward repression / tolerated inflation.",
        },
    },
}

BLOCKS = {
    "price_of_time": {
        "name": "1) Price of Time (Monetary Stance)",
        "weight": 0.20,
        "indicators": ["real_10y", "nominal_10y", "yield_curve_10_2"],
        "desc": "Cost of capital and duration sensitivity.",
    },
    "macro": {
        "name": "2) Macro Cycle (Inflation / Growth)",
        "weight": 0.15,
        "indicators": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],
        "desc": "Policy constraint: sticky inflation vs growth slowdown.",
    },
    "conditions": {
        "name": "3) Financial Conditions & Stress (USD + Credit + Vol + Trend)",
        "weight": 0.20,
        "indicators": ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"],
        "desc": "Global tightening: dollar, spreads, volatility, and trend.",
    },
    "plumbing": {
        "name": "4) System Liquidity (Plumbing)",
        "weight": 0.15,
        "indicators": ["fed_balance_sheet", "rrp"],
        "desc": "System liquidity: support vs drain for risk assets.",
    },
    "debt_fiscal": {
        "name": "5) Dalio Core — Debt & Fiscal Dominance",
        "weight": 0.20,
        "indicators": ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"],
        "desc": "Sovereign balance sheet + funding constraints.",
    },
    "external": {
        "name": "6) External Balance — Who Funds Who",
        "weight": 0.10,
        "indicators": ["current_account_gdp"],
        "desc": "External constraint under USD tightening.",
    },
    "cross": {
        "name": "Cross-Asset Confirmation (Non-Weighted)",
        "weight": 0.00,
        "indicators": ["world_equity", "duration_proxy_tlt", "gold"],
        "desc": "Cross-asset confirmation (does not affect global score).",
    },
}


# =========================
# DATA FETCHERS
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
        return pd.Series(vals, index=idx).astype(float).sort_index()
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


# =========================
# FREQ + DELTAS
# =========================

def infer_frequency(series: pd.Series) -> str:
    if series is None:
        return "unknown"
    s = series.dropna()
    if len(s) < 6:
        return "unknown"
    idx = pd.to_datetime(s.index).sort_values()
    diffs = idx.to_series().diff().dropna().dt.days
    if diffs.empty:
        return "unknown"
    med = float(diffs.median())
    if med <= 5:
        return "daily"
    if med <= 12:
        return "weekly"
    if med <= 45:
        return "monthly"
    if med <= 120:
        return "quarterly"
    if med <= 500:
        return "annual"
    return "unknown"


def pct_change_by_days(series: pd.Series, days: int) -> float:
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


def pct_change_by_periods(series: pd.Series, periods_back: int) -> float:
    if series is None or series.empty:
        return np.nan
    s = series.dropna()
    if len(s) <= periods_back:
        return np.nan
    curr_val = s.iloc[-1]
    past_val = s.iloc[-(periods_back + 1)]
    if pd.isna(past_val) or pd.isna(curr_val) or past_val == 0:
        return np.nan
    return (curr_val / past_val - 1.0) * 100.0


def compute_deltas(series: pd.Series) -> dict:
    freq = infer_frequency(series)
    if freq in ("daily", "weekly", "unknown"):
        return {"freq": freq, "label_a": "Δ7d", "val_a": pct_change_by_days(series, 7),
                "label_b": "Δ30d", "val_b": pct_change_by_days(series, 30),
                "label_c": "Δ1Y", "val_c": pct_change_by_days(series, 365)}
    if freq == "monthly":
        return {"freq": freq, "label_a": "Δ1M", "val_a": pct_change_by_periods(series, 1),
                "label_b": "Δ3M", "val_b": pct_change_by_periods(series, 3),
                "label_c": "Δ12M", "val_c": pct_change_by_periods(series, 12)}
    if freq == "quarterly":
        return {"freq": freq, "label_a": "Δ1Q", "val_a": pct_change_by_periods(series, 1),
                "label_b": "Δ4Q", "val_b": pct_change_by_periods(series, 4),
                "label_c": "Δ8Q", "val_c": pct_change_by_periods(series, 8)}
    if freq == "annual":
        return {"freq": freq, "label_a": "Δ1Y", "val_a": pct_change_by_periods(series, 1),
                "label_b": "Δ3Y", "val_b": pct_change_by_periods(series, 3),
                "label_c": "Δ5Y", "val_c": pct_change_by_periods(series, 5)}
    return {"freq": freq, "label_a": "Δ7d", "val_a": pct_change_by_days(series, 7),
            "label_b": "Δ30d", "val_b": pct_change_by_days(series, 30),
            "label_c": "Δ1Y", "val_c": pct_change_by_days(series, 365)}


def fmt_delta(val: float) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "n/a"
    return f"{val:+.1f}%"


# =========================
# SCORING
# =========================

def rolling_percentile_last(hist: pd.Series, latest: float) -> float:
    h = hist.dropna()
    if len(h) < 8 or pd.isna(latest):
        return np.nan
    return float((h <= latest).mean())


def compute_indicator_score(series: pd.Series, direction: int, scoring_mode: str = "z5y"):
    if series is None or series.empty:
        return np.nan, np.nan, np.nan
    s = series.dropna()
    if len(s) < 8:
        return np.nan, np.nan, (np.nan if len(s) == 0 else float(s.iloc[-1]))

    latest = float(s.iloc[-1])
    end = s.index.max()

    if scoring_mode == "pct20y":
        start = end - DateOffset(years=20)
        hist = s[s.index >= start]
        if len(hist) < 8:
            return np.nan, np.nan, latest
        p = rolling_percentile_last(hist, latest)
        if np.isnan(p):
            return np.nan, np.nan, latest
        sig = (p - 0.5) * 4.0
    else:
        if len(s) < 20:
            return np.nan, np.nan, latest
        start = end - DateOffset(years=5)
        hist = s[s.index >= start]
        if len(hist) < 20:
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


def status_pill_html(status: str) -> str:
    if status == "risk_on":
        return "<span class='pill good'>🟢 Risk-on</span>"
    if status == "risk_off":
        return "<span class='pill bad'>🔴 Risk-off</span>"
    if status == "neutral":
        return "<span class='pill warn'>🟡 Neutral</span>"
    return "<span class='pill'>⚪️ n/a</span>"


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
        return f"{v:.1f} {unit}"
    if unit == "":
        return f"{v:.2f}"
    return f"{v:.2f} {unit}"


# =========================
# RESAMPLING (FOR WALLBOARD / LONG HISTORY)
# =========================

def downsample_series(series: pd.Series, years_back: int, mode: str) -> pd.Series:
    """
    mode: "wallboard" / "desktop" / "mobile"
    We downsample mostly daily series for readability + performance.
    """
    if series is None or series.empty:
        return series
    s = series.dropna()
    if s.empty:
        return s

    freq = infer_frequency(s)
    if freq not in ("daily", "weekly"):
        return s  # keep monthly/quarterly/annual as-is

    # choose target
    if years_back >= 20:
        rule = "M"
    elif years_back >= 12:
        rule = "W"
    else:
        rule = None

    # wallboard tends to benefit from fewer points
    if mode == "wallboard" and years_back >= 8:
        rule = "W" if rule is None else rule

    if rule is None:
        return s

    try:
        # Use last observation in period (more "market-like")
        return s.resample(rule).last().dropna()
    except Exception:
        return s


# =========================
# "SO-WHAT" TITLES (RULE-BASED)
# =========================

def _trend_word(delta: float) -> str:
    if np.isnan(delta):
        return "flat"
    if delta >= 1.0:
        return "rising"
    if delta <= -1.0:
        return "falling"
    return "stable"


def _band_from_signal(sig: float) -> str:
    if np.isnan(sig):
        return "unknown"
    if sig >= 1.0:
        return "high"
    if sig <= -1.0:
        return "low"
    return "normal"


def so_what_title(key: str, series: pd.Series, indicator_scores: dict, years_back: int, meta: dict) -> str:
    info = indicator_scores.get(key, {})
    status = info.get("status", "n/a")
    sig = info.get("signal", np.nan)
    latest = info.get("latest", np.nan)

    deltas = compute_deltas(series)
    d_mid_label = deltas["label_b"]
    d_mid = deltas["val_b"]
    trend = _trend_word(d_mid)
    band = _band_from_signal(sig)
    ref = meta.get("ref_line", None)

    ref_ctx = ""
    if ref is not None and latest is not None and not (isinstance(latest, float) and np.isnan(latest)):
        try:
            ref_ctx = "above ref" if float(latest) > float(ref) else "below ref"
        except Exception:
            ref_ctx = ""

    so = "monitor"
    if key in ("real_10y", "nominal_10y"):
        so = "tightening headwind" if trend == "rising" else ("easing tailwind" if trend == "falling" else "rates steady")
        if key == "real_10y" and ref_ctx:
            so += " (real>0 bites)" if ref_ctx.startswith("above") else " (real<0 supportive)"
    elif key == "yield_curve_10_2":
        so = "cycle stress (inversion)" if (ref_ctx.startswith("below") or band == "low") else "cycle normalizing"
    elif key in ("breakeven_10y", "cpi_yoy"):
        so = "inflation constraint risk" if trend == "rising" else ("disinflation supportive" if trend == "falling" else "inflation steady")
    elif key == "usd_index":
        so = "global tightening" if trend == "rising" else ("conditions easing" if trend == "falling" else "USD steady")
    elif key == "hy_oas":
        so = "credit stress building" if trend == "rising" else ("credit easing" if trend == "falling" else "credit stable")
    elif key == "vix":
        so = "risk premia up" if trend == "rising" else ("vol calming" if trend == "falling" else "vol stable")
    elif key == "spy_trend":
        so = "risk-on confirmation" if (ref_ctx.startswith("above") or band == "high") else "risk-off warning"
    elif key == "hyg_lqd_ratio":
        so = "risk appetite improving" if trend == "rising" else ("flight-to-quality" if trend == "falling" else "appetite steady")
    elif key == "fed_balance_sheet":
        so = "liquidity tailwind" if trend == "rising" else ("liquidity drain" if trend == "falling" else "liquidity stable")
    elif key == "rrp":
        so = "liquidity parked" if trend == "rising" else ("liquidity released" if trend == "falling" else "RRP stable")
    elif key in ("interest_to_receipts", "interest_payments", "deficit_gdp", "term_premium_10y", "current_account_gdp"):
        if key == "term_premium_10y":
            so = "duration hedge weaker" if trend == "rising" else ("duration hedge improves" if trend == "falling" else "term premium steady")
        elif key == "interest_to_receipts":
            so = "fiscal constraint rising" if trend == "rising" else ("constraint easing" if trend == "falling" else "constraint stable")
        elif key == "deficit_gdp":
            so = "deficit pressure" if trend != "flat" else "deficit stable"
        elif key == "current_account_gdp":
            so = "external reliance risk" if trend == "falling" else ("constraint easing" if trend == "rising" else "external steady")
        else:
            so = "debt stress risk" if trend == "rising" else ("stress easing" if trend == "falling" else "stress stable")

    status_tag = "Risk-on" if status == "risk_on" else ("Risk-off" if status == "risk_off" else ("Neutral" if status == "neutral" else "n/a"))
    delta_txt = fmt_delta(d_mid)
    horizon_txt = f"{years_back}Y view"

    ctx_bits = [f"{trend} ({d_mid_label} {delta_txt})"]
    if ref_ctx:
        ctx_bits.append(ref_ctx)
    ctx = ", ".join(ctx_bits)

    return f"{so} — {ctx} | {status_tag} | {horizon_txt}"


# =========================
# PLOTTING (LEGIBILITY ENHANCED)
# =========================

def plot_premium(series: pd.Series, title: str, ref_line=None, height: int = 300):
    s = series.dropna()
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=s.index,
            y=s.values,
            mode="lines",
            line=dict(width=2),
            name="",
            hovertemplate="%{x|%Y-%m-%d}<br><b>%{y:.4f}</b><extra></extra>",
        )
    )

    if ref_line is not None:
        fig.add_hline(
            y=float(ref_line),
            line_width=1,
            line_dash="dot",
            opacity=0.9,
            line_color="rgba(255,255,255,0.28)",
        )

    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=14, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        showlegend=False,
        font=dict(color="rgba(255,255,255,0.90)"),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.10)",
        zeroline=False,
        showline=True,
        linecolor="rgba(255,255,255,0.18)",
        linewidth=1,
        ticks="outside",
        tickfont=dict(color="rgba(255,255,255,0.86)", size=11),
        tickcolor="rgba(255,255,255,0.18)",
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.10)",
        zeroline=False,
        showline=True,
        linecolor="rgba(255,255,255,0.18)",
        linewidth=1,
        ticks="outside",
        tickfont=dict(color="rgba(255,255,255,0.86)", size=11),
        tickcolor="rgba(255,255,255,0.18)",
    )

    # Visible in-plot title (top-left), with backdrop
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.01, y=0.99,
        text=title,
        showarrow=False,
        align="left",
        font=dict(size=13, color="rgba(255,255,255,0.98)"),
        bgcolor="rgba(0,0,0,0.38)",
        bordercolor="rgba(255,255,255,0.22)",
        borderwidth=1,
        borderpad=6,
    )
    return fig


def sparkline(series: pd.Series, height: int = 90):
    s = series.dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values,
        mode="lines",
        line=dict(width=2),
        hoverinfo="skip"
    ))
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


# =========================
# FULL TILE (DEEP DIVE)
# =========================

def render_tile_full(key: str, series: pd.Series, indicator_scores: dict, years_back: int, layout_mode: str):
    meta = INDICATOR_META[key]
    info = indicator_scores.get(key, {})
    score = info.get("score", np.nan)
    status = info.get("status", "n/a")
    latest = info.get("latest", np.nan)
    mode = meta.get("scoring_mode", "z5y")

    deltas = compute_deltas(series)
    score_txt = "n/a" if np.isnan(score) else f"{score:.1f}"
    latest_txt = fmt_value(latest, meta["unit"], meta.get("scale", 1.0))
    mode_badge = "<span class='pill'>score: z5y</span>" if mode == "z5y" else "<span class='pill'>score: pct20y</span>"

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style='display:flex; align-items:baseline; justify-content:space-between; gap: 10px; margin-bottom: 6px;'>
          <div>
            <div style='font-size:1.0rem; font-weight:650; margin-bottom:2px;'>{meta["label"]}</div>
            <div style='color:var(--muted); font-size:0.85rem; margin-bottom:8px;'>Source: {meta["source"]}</div>
          </div>
          <div style='text-align:right'>
            <div>{mode_badge}<span class='pill'>Latest: {latest_txt}</span>{status_pill_html(status)}</div>
            <div style='font-size:0.85rem; color:var(--muted);'>Score: {score_txt} · {deltas["label_b"]}: {fmt_delta(deltas["val_b"])}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("Definition & how to read", expanded=False):
        exp = meta["expander"]
        st.markdown(f"**What it is:** {exp['what']}")
        st.markdown(f"**Reference levels:** {exp['reference']}")
        st.markdown("**Two-way interpretation:**")
        st.markdown(exp["interpretation"])
        st.markdown(f"**Dalio bridge:** {exp.get('dalio_bridge','')}")
        st.markdown(
            f"**What changed:** "
            f"{deltas['label_a']} {fmt_delta(deltas['val_a'])}, "
            f"{deltas['label_b']} {fmt_delta(deltas['val_b'])}, "
            f"{deltas['label_c']} {fmt_delta(deltas['val_c'])}"
        )

    # resample for performance / readability
    mode_key = "wallboard" if layout_mode == "Wallboard (55'')" else ("mobile" if layout_mode == "Mobile" else "desktop")
    s_plot = downsample_series(series, years_back, mode_key)

    height = 230 if layout_mode == "Mobile" else (260 if layout_mode == "Wallboard (55'')" else 305)
    chart_title = so_what_title(key, series, indicator_scores, years_back, meta)
    fig = plot_premium(s_plot, chart_title, ref_line=meta.get("ref_line", None), height=height)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# WALLBOARD COMPACT TILE
# =========================

def render_tile_compact(key: str, series: pd.Series, indicator_scores: dict, years_back: int, show_spark: bool):
    meta = INDICATOR_META[key]
    info = indicator_scores.get(key, {})
    score = info.get("score", np.nan)
    status = info.get("status", "n/a")
    latest = info.get("latest", np.nan)

    deltas = compute_deltas(series)
    latest_txt = fmt_value(latest, meta["unit"], meta.get("scale", 1.0))
    score_txt = "n/a" if np.isnan(score) else f"{score:.0f}"

    # Slightly denser, screen-share friendly title
    short_title = meta["label"]
    if len(short_title) > 32:
        short_title = short_title[:31] + "…"

    st.markdown("<div class='wb-card'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='wb-title'>{short_title}</div>
        <div class='wb-meta'>{meta["source"]}</div>
        <div class='wb-row'>
          <div class='wb-big'>{latest_txt}</div>
          <div style='text-align:right'>
            {status_pill_html(status)}
            <div class='wb-small'>Score: <b>{score_txt}</b> · {deltas["label_b"]}: <b>{fmt_delta(deltas["val_b"])}</b></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if show_spark:
        s_spark = downsample_series(series, years_back, "wallboard")
        # keep last ~2 years for sparkline so it’s readable
        if not s_spark.empty:
            cutoff = s_spark.index.max() - pd.Timedelta(days=730)
            s_spark = s_spark[s_spark.index >= cutoff]
        if s_spark is not None and not s_spark.empty and len(s_spark) >= 5:
            st.plotly_chart(sparkline(s_spark, height=90), use_container_width=True, config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# OPERATING LINES (ETF-BASED)
# =========================

def latest_value(indicator_scores: dict, key: str) -> float:
    v = indicator_scores.get(key, {}).get("latest", np.nan)
    if v is None:
        return np.nan
    try:
        return float(v)
    except Exception:
        return np.nan


def operating_lines(block_scores: dict, indicator_scores: dict):
    gs = block_scores.get("GLOBAL", {}).get("score", np.nan)

    def _sg(x):
        if np.isnan(x):
            return 0.0
        return float(x)

    cond = _sg(block_scores.get("conditions", {}).get("score", np.nan))

    if not np.isnan(gs):
        if gs >= 60 and cond >= 55:
            equity = "↑ Increase — beta OK; watch credit"
        elif gs <= 40 or cond <= 40:
            equity = "↓ Reduce — defense / quality"
        else:
            equity = "→ Neutral — moderate sizing"
    else:
        equity = "n/a"

    pot = _sg(block_scores.get("price_of_time", {}).get("score", np.nan))
    termp_score = _sg(indicator_scores.get("term_premium_10y", {}).get("score", np.nan))
    cpi_latest = latest_value(indicator_scores, "cpi_yoy")
    breakeven_latest = latest_value(indicator_scores, "breakeven_10y")

    inflation_elevated = (not np.isnan(cpi_latest) and cpi_latest >= 3.0) or (not np.isnan(breakeven_latest) and breakeven_latest >= 2.7)
    inflation_benign = (not np.isnan(cpi_latest) and cpi_latest <= 2.6) and (np.isnan(breakeven_latest) or breakeven_latest <= 2.6)

    if termp_score <= 40 and inflation_elevated:
        duration = "Short/Neutral — avoid long nominals; prefer quality / TIPS"
    elif pot >= 55 and inflation_benign and termp_score >= 55:
        duration = "Long (hedge) — duration hedge improves"
    else:
        duration = "Neutral — balance term-premium risk vs cycle"

    hy = _sg(indicator_scores.get("hy_oas", {}).get("score", np.nan))
    hyg = _sg(indicator_scores.get("hyg_lqd_ratio", {}).get("score", np.nan))
    ds = _sg(indicator_scores.get("interest_to_receipts", {}).get("score", np.nan))

    if hy <= 40 or hyg <= 40 or ds <= 40:
        credit = "IG > HY — reduce default/funding risk"
    elif hy >= 60 and hyg >= 60 and ds >= 50:
        credit = "Opportunistic HY — sizing discipline"
    else:
        credit = "Neutral — quality tilt, selective"

    usd = _sg(indicator_scores.get("usd_index", {}).get("score", np.nan))
    dalio = _sg(block_scores.get("debt_fiscal", {}).get("score", np.nan))

    if dalio <= 40 and inflation_elevated:
        hedges = "Gold / real-asset tilt — repression risk"
    elif usd <= 40 and cond <= 45:
        hedges = "USD / cash-like — funding stress"
    else:
        hedges = "Light mix — cash-like + tactical gold"

    return equity, duration, credit, hedges


# =========================
# MAIN
# =========================

def main():
    st.title("Global Finance | Macro Overview (Dalio-Enhanced)")
    st.markdown(
        "<div class='muted'>Market thermometers + a Dalio layer on debt sustainability, fiscal dominance, and the external constraint.</div>",
        unsafe_allow_html=True
    )

    # Sidebar
    st.sidebar.header("Settings")
    if st.sidebar.button("🔄 Refresh data (clear cache)"):
        st.cache_data.clear()
        st.rerun()

    years_back = st.sidebar.slider("Historical window (years)", 5, 30, 15)

    st.sidebar.subheader("Layout")
    layout_mode = st.sidebar.radio(
        "View mode",
        ["Desktop", "Mobile", "Wallboard (55'')"],
        index=2
    )
    mobile_mode = layout_mode == "Mobile"
    wallboard_mode = layout_mode == "Wallboard (55'')"

    show_sparklines = False
    if wallboard_mode:
        show_sparklines = st.sidebar.checkbox("Wallboard: show sparklines", value=False)

    today = datetime.now(timezone.utc).date()
    start_date = (today - DateOffset(years=years_back)).date().isoformat()
    st.sidebar.markdown(f"**Start date:** {start_date}")

    fred_key = get_fred_api_key()
    if fred_key is None:
        st.sidebar.error("⚠️ Missing `FRED_API_KEY` in Streamlit secrets.")

    # Fetch
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

        # Derived: yield curve
        if not fred["nominal_10y"].empty and not fred["dgs2"].empty:
            yc = fred["nominal_10y"].to_frame("10y").join(fred["dgs2"].to_frame("2y"), how="inner")
            indicators["yield_curve_10_2"] = (yc["10y"] - yc["2y"]).dropna()
        else:
            indicators["yield_curve_10_2"] = pd.Series(dtype=float)

        # CPI YoY
        indicators["cpi_yoy"] = (fred["cpi_index"].pct_change(12) * 100.0).dropna() if not fred["cpi_index"].empty else pd.Series(dtype=float)

        # Direct
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

        # Derived: interest/receipts
        ip = indicators.get("interest_payments", pd.Series(dtype=float))
        fr = indicators.get("federal_receipts", pd.Series(dtype=float))
        if ip is not None and fr is not None and (not ip.empty) and (not fr.empty):
            join = ip.to_frame("interest").join(fr.to_frame("receipts"), how="inner").dropna()
            join = join[join["receipts"] != 0]
            indicators["interest_to_receipts"] = (join["interest"] / join["receipts"]).dropna()
        else:
            indicators["interest_to_receipts"] = pd.Series(dtype=float)

        # yfinance
        yf_map = fetch_yf_many(["DX-Y.NYB", "^VIX", "SPY", "HYG", "LQD", "URTH", "TLT", "GLD"], start_date)

        dxy = yf_map.get("DX-Y.NYB", pd.Series(dtype=float))
        if dxy is None or dxy.empty:
            dxy = fred["usd_fred"]
        indicators["usd_index"] = dxy

        indicators["vix"] = yf_map.get("^VIX", pd.Series(dtype=float))

        spy = yf_map.get("SPY", pd.Series(dtype=float))
        indicators["spy_trend"] = (spy / spy.rolling(200).mean()).dropna() if spy is not None and not spy.empty else pd.Series(dtype=float)

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

    # Score indicators
    indicator_scores = {}
    for key, meta in INDICATOR_META.items():
        series = indicators.get(key, pd.Series(dtype=float))
        mode = meta.get("scoring_mode", "z5y")
        score, sig, latest = compute_indicator_score(series, meta["direction"], scoring_mode=mode)
        indicator_scores[key] = {"score": score, "signal": sig, "latest": latest, "status": classify_status(score), "mode": mode}

    # Score blocks + global
    block_scores = {}
    global_score = 0.0
    w_used = 0.0

    for bkey, binfo in BLOCKS.items():
        if bkey == "cross":
            vals = [indicator_scores.get(ikey, {}).get("score", np.nan) for ikey in binfo["indicators"]]
            vals = [v for v in vals if not np.isnan(v)]
            bscore = float(np.mean(vals)) if vals else np.nan
            block_scores[bkey] = {"score": bscore, "status": classify_status(bscore)}
            continue

        vals = [indicator_scores.get(ikey, {}).get("score", np.nan) for ikey in binfo["indicators"]]
        vals = [v for v in vals if not np.isnan(v)]
        if vals:
            bscore = float(np.mean(vals))
            block_scores[bkey] = {"score": bscore, "status": classify_status(bscore)}
            global_score += bscore * binfo["weight"]
            w_used += binfo["weight"]
        else:
            block_scores[bkey] = {"score": np.nan, "status": "n/a"}

    global_score = (global_score / w_used) if w_used > 0 else np.nan
    global_status = classify_status(global_score)
    block_scores["GLOBAL"] = {"score": global_score, "status": global_status}

    # Freshness
    latest_points = [s.index.max() for s in indicators.values() if s is not None and not s.empty]
    data_max_date = max(latest_points) if latest_points else None

    # Tabs
    tabs = st.tabs([
        "Overview",
        "Wallboard",
        "Deep Dive (Charts)",
        "What Changed",
        "Report"
    ])

    # =========================
    # OVERVIEW
    # =========================
    with tabs[0]:
        left, right = st.columns([2, 1])

        with left:
            st.markdown(
                """
                <div class="section-card">
                  <div class="tiny">
                    <b>What Risk-on / Neutral / Risk-off means (ETF lens):</b><br/>
                    🟢 <b>Risk-on</b>: conditions + liquidity support risk assets → larger equity budget, more credit tolerance.<br/>
                    🟡 <b>Neutral</b>: mixed signals → moderate sizing, quality tilt, balanced hedges.<br/>
                    🔴 <b>Risk-off</b>: stress/tightening dominates → lower equity beta, prefer IG/quality; be cautious with HY and long nominals when inflation/term premium are high.
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("### Executive Snapshot")
            gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
            eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)

            def _btxt(k):
                sc = block_scores.get(k, {}).get("score", np.nan)
                stt = block_scores.get(k, {}).get("status", "n/a")
                return status_pill_html(stt), ("n/a" if np.isnan(sc) else f"{sc:.1f}")

            p1_s, p1_v = _btxt("price_of_time")
            p2_s, p2_v = _btxt("macro")
            p3_s, p3_v = _btxt("conditions")
            p4_s, p4_v = _btxt("plumbing")
            p5_s, p5_v = _btxt("debt_fiscal")
            p6_s, p6_v = _btxt("external")

            # In mobile: avoid 3-wide grid
            if mobile_mode:
                st.markdown(
                    f"""
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
                      <hr/>
                      <div class="kpi-sub">
                        {p1_s} Price of Time: <b>{p1_v}</b><br/>
                        {p2_s} Macro: <b>{p2_v}</b><br/>
                        {p3_s} Conditions: <b>{p3_v}</b><br/>
                        {p4_s} Plumbing: <b>{p4_v}</b><br/>
                        {p5_s} Debt & Fiscal: <b>{p5_v}</b><br/>
                        {p6_s} External: <b>{p6_v}</b>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div class="kpi-grid">
                      <div class="kpi-card">
                        <div class="kpi-title">Global Score (0–100) — 6 core blocks</div>
                        <div class="kpi-value">{gs_txt}</div>
                        <div class="kpi-sub">{status_pill_html(global_status)}</div>
                        <div class="kpi-sub">
                          <b>Equity risk budget:</b> {eq_line}<br/>
                          <b>Duration stance:</b> {dur_line}<br/>
                          <b>Credit stance:</b> {cr_line}<br/>
                          <b>Hedges:</b> {hdg_line}
                        </div>
                      </div>

                      <div class="kpi-card">
                        <div class="kpi-title">Blocks (score)</div>
                        <div class="kpi-sub">
                          {p1_s} Price of Time: <b>{p1_v}</b><br/>
                          {p2_s} Macro Cycle: <b>{p2_v}</b><br/>
                          {p3_s} Conditions & Stress: <b>{p3_v}</b><br/>
                          {p4_s} Plumbing: <b>{p4_v}</b><br/>
                          {p5_s} Debt & Fiscal: <b>{p5_v}</b><br/>
                          {p6_s} External Balance: <b>{p6_v}</b>
                        </div>
                      </div>

                      <div class="kpi-card">
                        <div class="kpi-title">Dalio bridges (one-liners)</div>
                        <div class="kpi-sub">
                          1) <b>Deficit ↑ → supply ↑ → term premium ↑ → duration suffers</b><br/>
                          2) <b>Term premium ↑ + USD ↑ → global tightening → risk-off</b><br/>
                          3) <b>Debt service ↑ → political pressure → repression risk</b><br/>
                          4) <b>Repression = compressed real rates → real assets hedge</b><br/>
                          5) <b>External deficits → foreign funding reliance → vulnerability</b>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            cross_sc = block_scores.get("cross", {}).get("score", np.nan)
            cross_st = block_scores.get("cross", {}).get("status", "n/a")
            cross_txt = "n/a" if np.isnan(cross_sc) else f"{cross_sc:.1f}"
            st.markdown(
                f"<div class='section-card'><div class='tiny'>Cross confirmation (non-weighted): <b>{cross_txt}</b> {status_pill_html(cross_st)}</div></div>",
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

            with st.expander("How scoring works", expanded=False):
                st.markdown(
                    """
- **Market thermometers**: **z-score ~5Y** (`z5y`) → clamp [-2,+2] → 0–100.
- **Structural constraints**: **percentile ~20Y** (`pct20y`) mapped to [-2,+2] → 0–100.
- Thresholds: **>60 Risk-on**, **40–60 Neutral**, **<40 Risk-off** (heuristics).
                    """
                )

    # =========================
    # WALLBOARD (tile-first)
    # =========================
    with tabs[1]:
        st.markdown("### Wallboard (tile-first)")
        if not wallboard_mode:
            st.info("Tip: switch **View mode** to **Wallboard (55'')** in the sidebar for the intended layout.")

        # Top strip: global + blocks
        gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
        eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)

        def _btxt_simple(k):
            sc = block_scores.get(k, {}).get("score", np.nan)
            stt = block_scores.get(k, {}).get("status", "n/a")
            return ("n/a" if np.isnan(sc) else f"{sc:.0f}"), status_pill_html(stt)

        b1, b1s = _btxt_simple("price_of_time")
        b2, b2s = _btxt_simple("macro")
        b3, b3s = _btxt_simple("conditions")
        b4, b4s = _btxt_simple("plumbing")
        b5, b5s = _btxt_simple("debt_fiscal")
        b6, b6s = _btxt_simple("external")

        st.markdown(
            f"""
            <div class="section-card">
              <div style="display:flex; justify-content:space-between; gap:14px; flex-wrap:wrap;">
                <div style="min-width:320px;">
                  <div class="kpi-title">Global Score</div>
                  <div class="kpi-value">{gs_txt}</div>
                  <div class="kpi-sub">{status_pill_html(global_status)}</div>
                </div>
                <div style="min-width:420px;">
                  <div class="kpi-title">Operating lines (ETF)</div>
                  <div class="kpi-sub">
                    <b>Equity:</b> {eq_line}<br/>
                    <b>Duration:</b> {dur_line}<br/>
                    <b>Credit:</b> {cr_line}<br/>
                    <b>Hedges:</b> {hdg_line}
                  </div>
                </div>
                <div style="min-width:420px;">
                  <div class="kpi-title">Blocks</div>
                  <div class="kpi-sub">
                    {b1s} Price of Time: <b>{b1}</b> ·
                    {b2s} Macro: <b>{b2}</b> ·
                    {b3s} Conditions: <b>{b3}</b><br/>
                    {b4s} Plumbing: <b>{b4}</b> ·
                    {b5s} Debt/Fiscal: <b>{b5}</b> ·
                    {b6s} External: <b>{b6}</b>
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Choose number of columns for wallboard
        cols_count = 6 if wallboard_mode else (4 if not mobile_mode else 1)

        # Wallboard key set (curated, 12 tiles)
        core_keys = [
            "real_10y", "usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio",
            "term_premium_10y", "interest_to_receipts", "deficit_gdp", "fed_balance_sheet", "rrp", "current_account_gdp"
        ]

        rows = [core_keys[i:i+cols_count] for i in range(0, len(core_keys), cols_count)]
        for r in rows:
            cols = st.columns(len(r))
            for c, k in zip(cols, r):
                with c:
                    s = indicators.get(k, pd.Series(dtype=float))
                    if s is None or s.empty:
                        st.warning(f"Missing: {INDICATOR_META[k]['label']}")
                    else:
                        render_tile_compact(k, s, indicator_scores, years_back, show_spark=show_sparklines)

        # Optional: show "all indicators" wallboard grid
        with st.expander("Show all indicators (wallboard grid)", expanded=False):
            all_keys = [k for k in INDICATOR_META.keys()]
            rows2 = [all_keys[i:i+cols_count] for i in range(0, len(all_keys), cols_count)]
            for r in rows2:
                cols = st.columns(len(r))
                for c, k in zip(cols, r):
                    with c:
                        s = indicators.get(k, pd.Series(dtype=float))
                        if s is None or s.empty:
                            st.caption("n/a")
                        else:
                            render_tile_compact(k, s, indicator_scores, years_back, show_spark=False)

    # =========================
    # DEEP DIVE (charts)
    # =========================
    with tabs[2]:
        st.markdown("### Deep Dive (charts)")
        st.markdown("<div class='muted'>Full charts + definitions. Use this tab when you want to explain the drivers.</div>", unsafe_allow_html=True)

        # In desktop: block-by-block with 2 columns; in mobile: single column; in wallboard: use 4 columns for speed
        for bkey, binfo in BLOCKS.items():
            st.markdown(f"#### {binfo['name']}")
            st.markdown(f"<div class='muted'>{binfo['desc']}</div>", unsafe_allow_html=True)

            keys = binfo["indicators"]
            if mobile_mode:
                ncols = 1
            elif wallboard_mode:
                ncols = 2  # charts are heavy; keep 2-wide even on 55''
            else:
                ncols = 2

            rows = [keys[i:i+ncols] for i in range(0, len(keys), ncols)]
            for r in rows:
                cols = st.columns(len(r))
                for c, k in zip(cols, r):
                    with c:
                        s = indicators.get(k, pd.Series(dtype=float))
                        if s is None or s.empty:
                            st.warning(f"Missing: {INDICATOR_META[k]['label']}")
                        else:
                            render_tile_full(k, s, indicator_scores, years_back, layout_mode)

            st.markdown("---")

    # =========================
    # WHAT CHANGED
    # =========================
    with tabs[3]:
        st.markdown("### What Changed (frequency-aware)")
        rows = []
        for key, meta in INDICATOR_META.items():
            s = indicators.get(key, pd.Series(dtype=float))
            if s is None or s.empty:
                continue
            deltas = compute_deltas(s)
            rows.append(
                {
                    "Indicator": meta["label"],
                    "Scoring": meta.get("scoring_mode", "z5y"),
                    "Freq": deltas["freq"],
                    deltas["label_a"]: None if np.isnan(deltas["val_a"]) else round(deltas["val_a"], 2),
                    deltas["label_b"]: None if np.isnan(deltas["val_b"]) else round(deltas["val_b"], 2),
                    deltas["label_c"]: None if np.isnan(deltas["val_c"]) else round(deltas["val_c"], 2),
                    "Score": None if np.isnan(indicator_scores[key]["score"]) else round(indicator_scores[key]["score"], 1),
                    "Regime": indicator_scores[key]["status"],
                }
            )
        st.dataframe(pd.DataFrame(rows).set_index("Indicator"), use_container_width=True) if rows else st.info("Not enough data to compute changes.")

    # =========================
    # REPORT
    # =========================
    with tabs[4]:
        st.markdown("### Report (optional) — AI-ready payload")
        st.markdown("<div class='muted'>Copyable payload for a multi-page memo with chart titles + so-what explanations.</div>", unsafe_allow_html=True)

        if st.button("Generate payload"):
            payload_lines = []
            payload_lines.append("macro_regime_payload_dalio:")
            payload_lines.append(f"  generated_at_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            payload_lines.append(f"  global_score: {0.0 if np.isnan(global_score) else round(global_score, 1)}")
            payload_lines.append(f"  global_status: {global_status}")
            payload_lines.append("  scoring_notes: \"market thermometers use z5y; structural constraints use pct20y\"")
            payload_lines.append(f"  horizon_years: {years_back}")
            payload_lines.append(f"  layout_mode: \"{layout_mode}\"")

            payload_lines.append("  blocks:")
            for bkey, binfo in BLOCKS.items():
                if bkey == "cross":
                    continue
                bscore = block_scores[bkey]["score"]
                bstatus = block_scores[bkey]["status"]
                payload_lines.append(f"    - key: \"{bkey}\"")
                payload_lines.append(f"      name: \"{binfo['name']}\"")
                payload_lines.append(f"      weight: {binfo['weight']}")
                payload_lines.append(f"      score: {0.0 if np.isnan(bscore) else round(bscore, 1)}")
                payload_lines.append(f"      status: {bstatus}")

            payload_lines.append("  operating_lines:")
            eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)
            payload_lines.append(f"    equity_risk_budget: \"{eq_line}\"")
            payload_lines.append(f"    duration_stance: \"{dur_line}\"")
            payload_lines.append(f"    credit_stance: \"{cr_line}\"")
            payload_lines.append(f"    hedges: \"{hdg_line}\"")

            payload_lines.append("  indicators:")
            for key, meta in INDICATOR_META.items():
                s_info = indicator_scores.get(key, {})
                score = s_info.get("score", np.nan)
                status = s_info.get("status", "n/a")
                latest = s_info.get("latest", np.nan)
                series = indicators.get(key, pd.Series(dtype=float))
                deltas = compute_deltas(series)
                mode = meta.get("scoring_mode", "z5y")
                title = so_what_title(key, series, indicator_scores, years_back, meta)

                payload_lines.append(f"    - name: \"{meta['label']}\"")
                payload_lines.append(f"      key: \"{key}\"")
                payload_lines.append(f"      scoring_mode: \"{mode}\"")
                payload_lines.append(f"      freq: \"{deltas['freq']}\"")
                payload_lines.append(f"      chart_title: \"{title}\"")
                payload_lines.append(f"      latest_value: \"{fmt_value(latest, meta['unit'], meta.get('scale', 1.0))}\"")
                payload_lines.append(f"      score: {0.0 if np.isnan(score) else round(score, 1)}")
                payload_lines.append(f"      status: {status}")
                payload_lines.append(f"      change_a: \"{deltas['label_a']} {fmt_delta(deltas['val_a'])}\"")
                payload_lines.append(f"      change_b: \"{deltas['label_b']} {fmt_delta(deltas['val_b'])}\"")
                payload_lines.append(f"      change_c: \"{deltas['label_c']} {fmt_delta(deltas['val_c'])}\"")

            st.code("\n".join(payload_lines), language="yaml")

            st.markdown("**Suggested prompt:**")
            st.code(
                """
You are a multi-asset macro strategist. You receive the YAML payload above.

Write an investor-ready memo (ETF-based) that:
1) Separates market thermometers vs structural constraints.
2) Assesses regime risk (fiscal dominance / repression / inflationary deleveraging / classic credit risk-off).
3) Gives an actionable allocation view (equity / duration / credit / hedges).
4) Lists 3–5 near-term triggers.
5) Uses each provided `chart_title` and adds a 2–3 sentence “so-what” under it.
                """.strip(),
                language="markdown"
            )


if __name__ == "__main__":
    main()
