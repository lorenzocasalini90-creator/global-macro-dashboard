import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from pandas.tseries.offsets import DateOffset


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Global finance | Macro overview (Dalio-enhanced)",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# PREMIUM THEME / CSS (dark, readable, wallboard-ready)
# =========================================================
st.markdown(
    """
<style>
  :root{
    --bg:#0b0f19;
    --panel:#0f1629;
    --panel2:#0c1324;
    --border:rgba(255,255,255,0.10);
    --muted:rgba(255,255,255,0.68);
    --text:rgba(255,255,255,0.94);
    --accent:rgba(99,102,241,1);
    --good:rgba(34,197,94,1);
    --warn:rgba(245,158,11,1);
    --bad:rgba(239,68,68,1);
  }

  .stApp {
    background: radial-gradient(1200px 700px at 20% 0%, #121a33 0%, #0b0f19 45%, #0b0f19 100%);
    color: var(--text);
  }
  .block-container { padding-top: 1.0rem; }

  h1,h2,h3,h4 { color: var(--text); letter-spacing:-0.02em; }
  .muted { color: var(--muted); }

  /* --- Pills --- */
  .pill{
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding:6px 12px;
    border-radius:999px;
    border:1px solid var(--border);
    background:rgba(255,255,255,0.03);
    font-size:0.88rem;
    color:var(--text);
    white-space:nowrap;
  }
  .pill.good{ border-color:rgba(34,197,94,0.35); background:rgba(34,197,94,0.10); }
  .pill.warn{ border-color:rgba(245,158,11,0.35); background:rgba(245,158,11,0.10); }
  .pill.bad { border-color:rgba(239,68,68,0.35); background:rgba(239,68,68,0.10); }

  /* --- Cards --- */
  .card{
    background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.03) 100%);
    border:1px solid var(--border);
    border-radius:18px;
    padding:16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  }
  .card-tight{
    background: rgba(255,255,255,0.035);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 14px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.18);
  }

  /* KPI tile layout */
  .kpi-grid{
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap:14px;
  }
  .kpi-title{ font-size:0.95rem; color:var(--muted); margin-bottom:6px; }
  .kpi-value{ font-size:2.1rem; font-weight:800; line-height:1.05; color:var(--text); }
  .kpi-sub{ margin-top:8px; font-size:0.98rem; color:var(--muted); }

  /* Wallboard indicator card */
  .wb-card{
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 14px;
    box-shadow: 0 8px 22px rgba(0,0,0,0.20);
    height: 100%;
  }
  .wb-title{ font-size: 1.10rem; font-weight: 750; margin-bottom: 6px; color: var(--text); }
  .wb-source{ color: var(--muted); font-size: 0.88rem; margin-bottom: 10px; }
  .wb-row{
    display:flex; align-items:baseline; justify-content:space-between; gap:12px;
    margin-top:8px;
  }
  .wb-value{
    font-size: 2.1rem;
    font-weight: 900;
    letter-spacing: -0.02em;
    color: var(--text);
  }
  .wb-meta{
    color: var(--muted);
    font-size: 0.92rem;
    margin-top: 6px;
    display:flex;
    justify-content:space-between;
    gap:10px;
  }

  /* --- Plotly frame readability --- */
  div[data-testid="stPlotlyChart"] > div{
    border-radius: 14px !important;
    overflow: hidden !important;
  }

  /* --- Expander: remove white bar, keep readable, sticky header --- */
  div[data-testid="stExpander"] details {
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 16px !important;
    background: rgba(255,255,255,0.03) !important;
    overflow: hidden !important;
  }
  div[data-testid="stExpander"] summary {
    background: rgba(255,255,255,0.03) !important;
    color: rgba(255,255,255,0.92) !important;
    border-bottom: 1px solid rgba(255,255,255,0.08) !important;
    padding: 10px 14px !important;
    position: sticky !important;
    top: 0 !important;
    z-index: 30 !important;
  }
  div[data-testid="stExpander"] summary:hover {
    background: rgba(255,255,255,0.06) !important;
  }
  div[data-testid="stExpander"] summary span,
  div[data-testid="stExpander"] summary p {
    color: rgba(255,255,255,0.92) !important;
  }

  /* --- Buttons: ensure readable (payload + refresh) --- */
  div.stButton > button {
    color: rgba(255,255,255,0.92) !important;
    border-color: rgba(255,255,255,0.14) !important;
    background: rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
  }
  div.stButton > button:hover {
    background: rgba(255,255,255,0.10) !important;
    border-color: rgba(255,255,255,0.22) !important;
  }

  /* --- Dataframe readability --- */
  .stDataFrame {
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 14px;
    overflow: hidden;
  }

  /* Responsive tweaks */
  @media (max-width: 850px){
    .kpi-grid{ grid-template-columns: 1fr; }
  }

  /* Optional: keep content from stretching too wide unless in wallboard */
  .maxw-1400 .block-container{ max-width: 1400px; }
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# INDICATORS META (Dalio-enhanced) — ENGLISH
# =========================================================

INDICATOR_META = {
    # -------------------------
    # 1) PRICE OF TIME
    # -------------------------
    "real_10y": {
        "label": "US 10Y TIPS Real Yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DFII10",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "10Y real yield (TIPS): the price of time net of inflation.",
            "reference": "<0% very easy; 0–2% neutral; >2% restrictive (heuristics).",
            "interpretation": (
                "- **Real yields rising** → headwind for equities (esp. growth) and long duration.\n"
                "- **Real yields falling** → tailwind for risk assets; duration becomes less toxic."
            ),
            "dalio_bridge": "Higher real yields tighten the funding constraint economy-wide.",
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
            "what": "10Y Treasury yield: discount rate benchmark; financial tightening proxy.",
            "reference": "Fast upward moves often equal tightening via higher discounting and term premium.",
            "interpretation": (
                "- **Yields up fast** → pressure on equities and existing bonds.\n"
                "- **Yields down** → supports duration; equity impact depends on growth/inflation mix."
            ),
            "dalio_bridge": "Yield up = market demands higher compensation (inflation and/or term premium).",
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
            "what": "10Y–2Y slope: cycle/recession expectations proxy.",
            "reference": "<0 inverted (late cycle); >0 normal (heuristics).",
            "interpretation": (
                "- **Deep/persistent inversion** → late-cycle risk; recession odds higher.\n"
                "- **Re-steepening above 0** → normalization / easier stance."
            ),
            "dalio_bridge": "Inversion often signals policy is restrictive vs the cycle → deleveraging risk rises.",
        },
    },

    # -------------------------
    # 2) MACRO CYCLE
    # -------------------------
    "breakeven_10y": {
        "label": "10Y Breakeven Inflation",
        "unit": "%",
        "direction": -1,
        "source": "FRED T10YIE",
        "scale": 1.0,
        "ref_line": 2.5,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Market-implied long-run inflation expectations: nominals vs TIPS.",
            "reference": "~2–3% anchored; >3% sticky inflation risk (heuristics).",
            "interpretation": (
                "- **Breakevens up** → higher odds of restrictive policy for longer.\n"
                "- **Breakevens down toward target** → more room to ease."
            ),
            "dalio_bridge": "Higher expected inflation increases the odds of financial repression in stress episodes.",
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
        "expander": {
            "what": "Headline CPI year-over-year.",
            "reference": "Fed target is ~2%; >3–4% persistent = sticky inflation (heuristics).",
            "interpretation": (
                "- **Disinflation** → supports duration and often equities.\n"
                "- **Re-acceleration** → higher-for-longer risk."
            ),
            "dalio_bridge": "Sticky inflation becomes the main constraint on policy support.",
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
            "what": "Labor slack proxy for growth cycle.",
            "reference": "Fast rises often coincide with slowdown/recession.",
            "interpretation": (
                "- **Unemployment up quickly** → recession risk → risk-off.\n"
                "- **Stable/low** → more benign growth backdrop."
            ),
            "dalio_bridge": "Higher slack + high debt raises political pressure for support (fiscal dominance risk).",
        },
    },

    # -------------------------
    # 3) FINANCIAL CONDITIONS & STRESS
    # -------------------------
    "usd_index": {
        "label": "USD Index (DXY / Broad Proxy)",
        "unit": "",
        "direction": -1,
        "source": "yfinance DX-Y.NYB (fallback FRED DTWEXBGS)",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Dollar strength proxy. If DXY is missing, uses FRED broad USD index.",
            "reference": "Stronger USD usually tightens global financial conditions.",
            "interpretation": (
                "- **USD up** → global tightening; pressure on risk assets.\n"
                "- **USD down** → loosening impulse."
            ),
            "dalio_bridge": "USD strength raises global funding stress (especially where debt is USD-linked).",
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
            "reference": "<4% benign; >6–7% stress (heuristics).",
            "interpretation": (
                "- **Spreads widening** → risk-off (credit stress).\n"
                "- **Spreads tightening** → risk appetite improving."
            ),
            "dalio_bridge": "Credit stress can accelerate deleveraging non-linearly.",
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
            "what": "Equity implied volatility proxy for near-term risk premium.",
            "reference": "<15 calm; 15–25 normal; >25 stress (heuristics).",
            "interpretation": "- **VIX up** → risk-off.\n- **VIX down** → risk-on.",
            "dalio_bridge": "Vol can tighten conditions even without rate hikes (risk premium up).",
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
            "what": "Trend proxy: SPY relative to 200-day moving average.",
            "reference": ">1 bull trend; <1 downtrend (heuristics).",
            "interpretation": "- **>1** → supports risk-on.\n- **<1** → risk-off backdrop.",
            "dalio_bridge": "Trend down + credit stress up is a classic deleveraging setup.",
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
            "what": "HY vs IG ratio: credit risk appetite.",
            "reference": "Higher = more HY appetite; lower = flight to quality.",
            "interpretation": "- **Up** → risk-on.\n- **Down** → risk-off.",
            "dalio_bridge": "Flight-to-quality often signals tightening funding constraints.",
        },
    },

    # -------------------------
    # 4) LIQUIDITY PLUMBING
    # -------------------------
    "fed_balance_sheet": {
        "label": "Fed Balance Sheet (WALCL)",
        "unit": "bn USD",
        "direction": +1,
        "source": "FRED WALCL (millions -> bn)",
        "scale": 1.0 / 1000.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Fed assets as a system liquidity proxy.",
            "reference": "Expanding balance sheet (QE) tends to support risk; QT tends to drain.",
            "interpretation": "- **Up** → liquidity tailwind.\n- **Down** → liquidity headwind.",
            "dalio_bridge": "Plumbing governs whether flows support or drain risk assets.",
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
            "what": "Cash parked at the Fed’s RRP facility.",
            "reference": "High RRP = liquidity ‘stuck’; falling RRP releases marginal liquidity.",
            "interpretation": "- **RRP up** → less fuel for risk.\n- **RRP down** → supportive impulse.",
            "dalio_bridge": "RRP down often releases marginal liquidity (tactical support).",
        },
    },

    # -------------------------
    # 5) DALIO CORE — DEBT / FISCAL DOMINANCE
    # -------------------------
    "interest_payments": {
        "label": "US Federal Interest Payments (Quarterly)",
        "unit": "bn USD",
        "direction": -1,
        "source": "FRED A091RC1Q027SBEA",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Federal government interest payments (debt service).",
            "reference": "Becomes a political constraint when it accelerates materially.",
            "interpretation": "- **Rising persistently** → higher fiscal dominance / repression risk.\n- **Falling** → constraint eases.",
            "dalio_bridge": "Debt service up → political pressure → higher odds of repression / inflation tolerance.",
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
            "what": "Federal revenues, used for debt service sustainability ratios.",
            "reference": "Higher receipts improves interest/receipts sustainability (ceteris paribus).",
            "interpretation": "- **Receipts up** → improves sustainability.\n- **Receipts down** → increases fiscal strain.",
            "dalio_bridge": "Interest/receipts rising = less room for anti-inflation policy in stress.",
        },
    },
    "interest_to_receipts": {
        "label": "Debt Service Stress (Interest / Receipts)",
        "unit": "ratio",
        "direction": -1,
        "source": "Derived: A091RC1Q027SBEA / FGRECPT",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Share of receipts consumed by interest.",
            "reference": "Higher + rising = political/fiscal constraint (heuristic).",
            "interpretation": "- **Up** → fiscal dominance risk up.\n- **Down** → constraint eases.",
            "dalio_bridge": "Higher debt service share pushes policy toward funding / repression.",
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
            "what": "Federal balance as % of GDP. Negative = deficit.",
            "reference": "Persistent large deficits increase Treasury supply and term premium risk.",
            "interpretation": "- **More negative** → structural duration pressure.\n- **Improving** → reduces supply pressure.",
            "dalio_bridge": "Deficit up → supply up → term premium up → duration suffers.",
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
            "what": "Compensation demanded for holding long-duration nominal Treasuries.",
            "reference": "Rising term premium can make long nominals a weaker hedge.",
            "interpretation": "- **Up** → long nominal duration more toxic.\n- **Down** → duration hedge becomes more reliable.",
            "dalio_bridge": "If term premium rises from supply/funding, bonds may not hedge equities in stress.",
        },
    },

    # -------------------------
    # 6) EXTERNAL BALANCE
    # -------------------------
    "current_account_gdp": {
        "label": "US Current Account Balance (% of GDP)",
        "unit": "%",
        "direction": +1,
        "source": "FRED USAB6BLTT02STSAQ",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "External funding constraint: current account as % of GDP.",
            "reference": "Persistent deficits increase vulnerability when USD funding tightens.",
            "interpretation": "- **More negative** → external reliance up.\n- **Toward 0/positive** → constraint eases.",
            "dalio_bridge": "Current account deficit = reliance on foreign capital → vulnerability in global tightening.",
        },
    },

    # -------------------------
    # CROSS-ASSET CONFIRMATION (non-weighted)
    # -------------------------
    "world_equity": {
        "label": "Global Equities (URTH)",
        "unit": "",
        "direction": +1,
        "source": "yfinance URTH",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Global equities confirmation (not just US).",
            "reference": "Trend/drawdown confirm or contradict local signals.",
            "interpretation": "- **Uptrend** → confirms risk-on.\n- **Downtrend** → confirms risk-off.",
            "dalio_bridge": "If global equities break, the risk regime is more structural.",
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
            "what": "Long Treasury duration proxy (classic hedge in growth shocks).",
            "reference": "Rallies often coincide with flight-to-quality (context matters).",
            "interpretation": "- **TLT up** → often risk-off / easing expectations.\n- **TLT down** + yields up → duration headwind.",
            "dalio_bridge": "If TLT fails in stress, it can signal inflationary deleveraging / term premium rising.",
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
            "what": "Gold as hedge (inflation/shocks/monetary repression risk).",
            "reference": "Breakouts can signal rising hedging demand.",
            "interpretation": "- **Gold up** → hedging demand rising.\n- **Gold down** during equity bull → cleaner risk-on.",
            "dalio_bridge": "Gold often works when policy shifts toward repression / inflation tolerance.",
        },
    },
}

# Blocks (core + cross)
BLOCKS = {
    "price_of_time": {
        "name": "1) Price of Time (Monetary Stance)",
        "weight": 0.20,
        "indicators": ["real_10y", "nominal_10y", "yield_curve_10_2"],
        "desc": "Cost of capital (real + nominal) and curve shape.",
    },
    "macro": {
        "name": "2) Macro Cycle (Inflation / Growth)",
        "weight": 0.15,
        "indicators": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],
        "desc": "Policy constraint: sticky inflation vs growth slowdown.",
    },
    "conditions": {
        "name": "3) Financial Conditions & Stress",
        "weight": 0.20,
        "indicators": ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"],
        "desc": "Fast regime signals: USD, credit stress, vol, trend, credit appetite.",
    },
    "plumbing": {
        "name": "4) System Liquidity (Plumbing)",
        "weight": 0.15,
        "indicators": ["fed_balance_sheet", "rrp"],
        "desc": "System liquidity: tailwind vs drain for risk assets.",
    },
    "debt_fiscal": {
        "name": "5) Debt & Fiscal (Dalio)",
        "weight": 0.20,
        "indicators": ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"],
        "desc": "Sovereign constraint: debt service, deficit/supply, term premium.",
    },
    "external": {
        "name": "6) External Balance",
        "weight": 0.10,
        "indicators": ["current_account_gdp"],
        "desc": "Who funds who: external reliance vulnerability during tightening.",
    },
    "cross": {
        "name": "Cross-Asset Confirmation (Non-weighted)",
        "weight": 0.00,
        "indicators": ["world_equity", "duration_proxy_tlt", "gold"],
        "desc": "Useful confirmation layer; does not affect the global score.",
    },
}

# For wallboard grouping
WALLBOARD_GROUPS = [
    ("Market Thermometers", "Fast regime signals: rates, USD, credit stress, vol, trend, risk appetite.",
     ["real_10y", "usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"]),
    ("Liquidity / Plumbing", "System liquidity: tailwind vs drain for risk assets.",
     ["fed_balance_sheet", "rrp"]),
    ("Structural Constraints (Dalio)", "Debt sustainability, term premium, and external funding constraint.",
     ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "current_account_gdp"]),
    ("Macro Cycle", "Inflation vs growth: what the central bank is constrained by.",
     ["breakeven_10y", "cpi_yoy", "unemployment_rate"]),
    ("Cross Confirmation", "Cross-asset coherence checks (not in global score).",
     ["world_equity", "duration_proxy_tlt", "gold"]),
]


# =========================================================
# DATA FETCHERS
# =========================================================

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
    out = {}
    for t in tickers:
        out[t] = fetch_yf_one(t, start_date)
    return out


# =========================================================
# SCORING + HELPERS
# =========================================================

def rolling_percentile_last(hist: pd.Series, latest: float) -> float:
    h = hist.dropna()
    if len(h) < 10 or pd.isna(latest):
        return np.nan
    return float((h <= latest).mean())


def compute_indicator_score(series: pd.Series, direction: int, scoring_mode: str = "z5y"):
    """
    Returns: (score_0_100, signal, latest)
    - z5y => zscore on ~5y history
    - pct20y => percentile on ~20y history, mapped to [-2,+2]
    """
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
        sig = (p - 0.5) * 4.0  # [-2,+2] approx
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
    return {"risk_on": "Risk-on", "neutral": "Neutral", "risk_off": "Risk-off"}.get(status, "n/a")


def status_pill_html(status: str) -> str:
    if status == "risk_on":
        return "<span class='pill good'>🟢 Risk-on</span>"
    if status == "risk_off":
        return "<span class='pill bad'>🔴 Risk-off</span>"
    if status == "neutral":
        return "<span class='pill warn'>🟡 Neutral</span>"
    return "<span class='pill'>⚪ n/a</span>"


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


def infer_delta_horizon(series: pd.Series) -> tuple[int, str]:
    """
    Choose a sensible delta horizon:
    - daily/weekly series => 30d
    - quarterly-ish series => 90d (1Q)
    """
    s = series.dropna()
    if len(s) < 5:
        return 30, "Δ30d"
    diffs = s.index.to_series().diff().dropna().dt.days
    med = float(diffs.median()) if len(diffs) else 1.0
    if med >= 20:
        return 90, "Δ1Q"
    return 30, "Δ30d"


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


# =========================================================
# PLOTTING (Readable, titled, framed)
# =========================================================

def make_dynamic_title(meta_label: str, series: pd.Series, score: float, status: str, horizon_years: int) -> str:
    # light “so-what” title without API calls
    last = float(series.dropna().iloc[-1]) if series is not None and not series.dropna().empty else np.nan
    delta_days, delta_label = infer_delta_horizon(series)
    d = pct_change_over_days(series, delta_days)
    d_txt = "n/a" if np.isnan(d) else f"{d:+.1f}% {delta_label}"
    sc_txt = "n/a" if np.isnan(score) else f"{score:.0f}"
    return f"{meta_label} — {status_label(status)} ({sc_txt}) • {d_txt} • {horizon_years}Y"


def plot_premium(series: pd.Series, title_text: str, ref_line=None, height: int = 300):
    s = series.dropna()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=s.index,
            y=s.values,
            mode="lines",
            line=dict(width=2),
            name="",
        )
    )
    if ref_line is not None:
        fig.add_hline(
            y=float(ref_line),
            line_width=1,
            line_dash="dot",
            opacity=0.7,
        )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=34, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        showlegend=False,
        font=dict(color="rgba(255,255,255,0.92)"),
        title=dict(
            text=title_text,
            x=0.01,
            xanchor="left",
            y=0.98,
            yanchor="top",
            font=dict(color="rgba(255,255,255,0.95)", size=14),
        ),
    )
    return fig


def plot_sparkline(series: pd.Series, height: int = 120):
    s = series.dropna()
    if s.empty:
        fig = go.Figure()
        fig.update_layout(
            height=height,
            margin=dict(l=6, r=6, t=6, b=6),
            paper_bgcolor="rgba(255,255,255,0.03)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text="Missing: no data available",
                    x=0.02, y=0.5, xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(color="rgba(255,255,255,0.70)", size=12),
                    align="left"
                )
            ],
        )
        return fig

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", line=dict(width=2)))
    fig.update_layout(
        height=height,
        margin=dict(l=6, r=6, t=6, b=6),
        paper_bgcolor="rgba(255,255,255,0.03)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
        font=dict(color="rgba(255,255,255,0.9)"),
    )
    return fig


# =========================================================
# ETF OPERATING LINES
# =========================================================

def operating_lines(block_scores: dict, indicator_scores: dict):
    gs = block_scores.get("GLOBAL", {}).get("score", np.nan)

    def _sg(x):
        return 0.0 if np.isnan(x) else float(x)

    cond = _sg(block_scores.get("conditions", {}).get("score", np.nan))
    debt = _sg(block_scores.get("debt_fiscal", {}).get("score", np.nan))
    macro = _sg(block_scores.get("macro", {}).get("score", np.nan))

    if not np.isnan(gs):
        if gs >= 60 and cond >= 55:
            equity = "↑ Neutral→Risk-on: increase beta carefully (watch credit)."
        elif gs <= 40 or cond <= 40:
            equity = "↓ Risk-off: reduce beta; prefer quality/defensives."
        else:
            equity = "→ Neutral: moderate sizing."
    else:
        equity = "n/a"

    pot = _sg(block_scores.get("price_of_time", {}).get("score", np.nan))
    termp = _sg(indicator_scores.get("term_premium_10y", {}).get("score", np.nan))
    infl = _sg(indicator_scores.get("cpi_yoy", {}).get("score", np.nan))

    if termp <= 40 and infl <= 45:
        duration = "Short/neutral: avoid long nominals; prefer quality/TIPS tilt."
    elif pot <= 40 and infl <= 45 and termp >= 55:
        duration = "Long duration can hedge: disinflation + term premium supportive."
    else:
        duration = "Neutral: balance term-premium risk vs cycle."

    hy = _sg(indicator_scores.get("hy_oas", {}).get("score", np.nan))
    hyg = _sg(indicator_scores.get("hyg_lqd_ratio", {}).get("score", np.nan))
    ds = _sg(indicator_scores.get("interest_to_receipts", {}).get("score", np.nan))

    if hy <= 40 or hyg <= 40 or ds <= 40:
        credit = "IG > HY: reduce default/funding risk."
    elif hy >= 60 and hyg >= 60 and ds >= 50:
        credit = "Opportunistic HY: small sizing, risk controls."
    else:
        credit = "Neutral: quality bias, selective risk."

    usd = _sg(indicator_scores.get("usd_index", {}).get("score", np.nan))
    dalio = _sg(block_scores.get("debt_fiscal", {}).get("score", np.nan))

    if dalio <= 40 and infl >= 55:
        hedges = "Gold/real-asset tilt: repression/inflation tolerance risk."
    elif usd <= 40 and cond <= 45:
        hedges = "USD/cash-like: funding stress hedge."
    else:
        hedges = "Light mix: cash-like + tactical gold."

    return equity, duration, credit, hedges


# =========================================================
# UI RENDERERS
# =========================================================

def render_tile(key: str, series: pd.Series, indicator_scores: dict, years_back: int):
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

    st.markdown("<div class='card-tight'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="display:flex; align-items:baseline; justify-content:space-between; gap:12px; margin-bottom:6px;">
          <div>
            <div style="font-size:1.05rem; font-weight:760;">{meta["label"]}</div>
            <div class="muted" style="font-size:0.88rem;">Source: {meta["source"]}</div>
          </div>
          <div style="text-align:right;">
            <div>{mode_badge}<span class='pill'>Latest: {latest_txt}</span>{status_pill_html(status)}</div>
            <div class="muted" style="font-size:0.90rem; margin-top:6px;">
              Score: <b>{score_txt}</b> · Δ30d: {("n/a" if np.isnan(d30) else f"{d30:+.1f}%")}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Definition & how to read", expanded=False):
        exp = meta["expander"]
        st.markdown(f"**What it is:** {exp['what']}")
        st.markdown(f"**Reference levels:** {exp['reference']}")
        st.markdown("**Interpretation (two-way):**")
        st.markdown(exp["interpretation"])
        st.markdown(f"**Dalio bridge:** {exp.get('dalio_bridge','')}")
        st.markdown(
            f"**What changed:** "
            f"{'n/a' if np.isnan(d7) else f'{d7:+.1f}%'} (7d), "
            f"{'n/a' if np.isnan(d30) else f'{d30:+.1f}%'} (30d), "
            f"{'n/a' if np.isnan(d1y) else f'{d1y:+.1f}%'} (1Y)"
        )

    title = make_dynamic_title(meta["label"], series, score, status, years_back)
    fig = plot_premium(series, title_text=title, ref_line=meta.get("ref_line", None), height=310)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"tile_chart_{key}")

    st.markdown("</div>", unsafe_allow_html=True)


def wallboard_indicator_card(key: str, series: pd.Series, indicator_scores: dict):
    meta = INDICATOR_META[key]
    info = indicator_scores.get(key, {})
    score = info.get("score", np.nan)
    status = info.get("status", "n/a")
    latest = info.get("latest", np.nan)

    latest_txt = fmt_value(latest, meta["unit"], meta.get("scale", 1.0))
    delta_days, delta_label = infer_delta_horizon(series)
    d = pct_change_over_days(series, delta_days)
    d_txt = "n/a" if np.isnan(d) else f"{d:+.1f}%"

    score_txt = "n/a" if np.isnan(score) else f"{score:.0f}"

    st.markdown("<div class='wb-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='wb-title'>{meta['label']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='wb-source'>{meta['source']}</div>", unsafe_allow_html=True)

    # Sparkline (NO placeholders; always unique key)
    st.plotly_chart(
        plot_sparkline(series, height=120),
        use_container_width=True,
        config={"displayModeBar": False},
        key=f"wb_spark_{key}",
    )

    st.markdown(
        f"""
        <div class="wb-row">
          <div class="wb-value">{latest_txt}</div>
          <div>{status_pill_html(status)}</div>
        </div>
        <div class="wb-meta">
          <div>Score: <b>{score_txt}</b></div>
          <div>{delta_label}: <b>{d_txt}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# MAIN
# =========================================================

def main():
    # Sidebar controls
    st.sidebar.header("Settings")

    layout_mode = st.sidebar.selectbox(
        "Layout mode",
        ["Auto", "Desktop", "Mobile", 'Wallboard (55")'],
        index=0,
    )

    years_back = st.sidebar.slider("History window (years)", 5, 30, 15)
    today = datetime.now(timezone.utc).date()
    start_date = (today - DateOffset(years=years_back)).date().isoformat()
    st.sidebar.caption(f"Start date: {start_date}")

    # Top buttons
    colA, colB = st.sidebar.columns([1, 1])
    with colA:
        if st.button("🔄 Refresh data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    with colB:
        st.caption("")

    fred_key = get_fred_api_key()
    if fred_key is None:
        st.sidebar.error("Missing `FRED_API_KEY` in Streamlit secrets.")

    # Optional max width
    if layout_mode in ["Auto", "Desktop"]:
        st.markdown('<div class="maxw-1400"></div>', unsafe_allow_html=True)

    st.title("Global finance | Macro overview (Dalio-enhanced)")
    st.markdown(
        "<div class='muted'>Macro-finance dashboard: market thermometers + Dalio-style structural constraints (debt, fiscal dominance, external balance).</div>",
        unsafe_allow_html=True,
    )

    # Fetch data
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

        # Derived: interest / receipts ratio
        ip = indicators.get("interest_payments", pd.Series(dtype=float))
        fr = indicators.get("federal_receipts", pd.Series(dtype=float))
        if (ip is not None and fr is not None) and (not ip.empty) and (not fr.empty):
            join = ip.to_frame("interest").join(fr.to_frame("receipts"), how="inner").dropna()
            join = join[join["receipts"] != 0]
            indicators["interest_to_receipts"] = (join["interest"] / join["receipts"]).dropna()
        else:
            indicators["interest_to_receipts"] = pd.Series(dtype=float)

        # YFINANCE
        yf_map = fetch_yf_many(
            ["DX-Y.NYB", "^VIX", "SPY", "HYG", "LQD", "URTH", "TLT", "GLD"],
            start_date
        )

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

    # Score indicators
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

    # Score blocks + global
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
        if bkey != "cross" and binfo["weight"] > 0 and not np.isnan(bscore):
            global_score += bscore * binfo["weight"]
            w_used += binfo["weight"]

    global_score = (global_score / w_used) if w_used > 0 else np.nan
    global_status = classify_status(global_score)
    block_scores["GLOBAL"] = {"score": global_score, "status": global_status}

    # Data freshness
    latest_points = []
    for _, s in indicators.items():
        if s is not None and not s.empty:
            latest_points.append(s.index.max())
    data_max_date = max(latest_points) if latest_points else None
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Tabs
    tabs = st.tabs([
        "Overview",
        "Wallboard",
        "Deep dive",
        "What changed",
        "Report"
    ])

    # =========================================================
    # OVERVIEW
    # =========================================================
    with tabs[0]:
        left, right = st.columns([2.2, 1.0])

        with left:
            st.markdown("## Executive Snapshot")

            # Risk regime legend (requested)
            st.markdown(
                """
<div class="card-tight">
  <div class="muted" style="margin-bottom:8px;"><b>Risk regime legend (how to interpret Risk-on / Neutral / Risk-off)</b></div>
  <div class="muted">
    • <b>Risk-on</b>: conditions supportive → higher equity beta, looser credit, lower stress.<br/>
    • <b>Neutral</b>: mixed signals → moderate sizing, quality bias, avoid over-committing.<br/>
    • <b>Risk-off</b>: tightening/stress dominates → lower beta, prefer IG/quality, consider hedges.
  </div>
</div>
""",
                unsafe_allow_html=True
            )

            gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
            eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)

            # Block summary format: "Name: Regime (Score)" (requested ordering)
            def block_line(bkey: str, label: str):
                sc = block_scores.get(bkey, {}).get("score", np.nan)
                stt = block_scores.get(bkey, {}).get("status", "n/a")
                sc_txt = "n/a" if np.isnan(sc) else f"{sc:.1f}"
                return f"{label}: {status_label(stt)} ({sc_txt})"

            # Two categories (requested)
            market_thermos = [
                block_line("price_of_time", "Price of Time"),
                block_line("macro", "Macro Cycle"),
                block_line("conditions", "Conditions & Stress"),
                block_line("plumbing", "Liquidity / Plumbing"),
            ]
            structural = [
                block_line("debt_fiscal", "Debt & Fiscal"),
                block_line("external", "External Balance"),
            ]

            st.markdown(
                f"""
<div class="kpi-grid">
  <div class="card">
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

  <div class="card">
    <div class="kpi-title">Block scores (name → regime → score)</div>
    <div class="kpi-sub">
      <div class="muted" style="margin-bottom:6px;"><b>Market thermometers</b></div>
      {"<br/>".join(market_thermos)}
      <div style="height:12px;"></div>
      <div class="muted" style="margin-bottom:6px;"><b>Structural constraints</b></div>
      {"<br/>".join(structural)}
    </div>
  </div>

  <div class="card">
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

        with right:
            st.markdown("### Info")
            st.markdown("<div class='card-tight'>", unsafe_allow_html=True)
            st.markdown(f"<div class='muted'>Now: <b>{now_utc}</b></div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='muted'>Latest datapoint: <b>{('n/a' if data_max_date is None else str(pd.to_datetime(data_max_date).date()))}</b></div>",
                unsafe_allow_html=True
            )
            st.markdown(f"<div class='muted'>Layout mode: <b>{layout_mode}</b></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("How scoring works (quick)", expanded=False):
                st.markdown(
                    """
**Two score types (kept intentionally simple):**
- **Market thermometers** use **z-score ~5Y** (`z5y`) → clamp **[-2,+2]** → map to **0–100**.
- **Structural constraints** use **percentile ~20Y** (`pct20y`) → map to **[-2,+2]** → **0–100**.

**Thresholds (heuristics):**
- **>60 = Risk-on**
- **40–60 = Neutral**
- **<40 = Risk-off**

Interpretation: the score is a *regime thermometer*, not a forecast. Use “What changed” to detect inflections.
                    """
                )

            usd_series = indicators.get("usd_index", pd.Series(dtype=float))
            if usd_series is None or usd_series.empty:
                st.warning("USD index is empty: neither yfinance DXY nor FRED proxy is available.")
            else:
                st.caption("USD index uses yfinance DXY when available, otherwise FRED DTWEXBGS.")

    # =========================================================
    # WALLBOARD (Grouped, consistent)
    # =========================================================
    with tabs[1]:
        st.markdown("## Wallboard (grouped, consistent)")

        # Top banner card
        gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
        eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        cL, cR = st.columns([1.1, 1.2])
        with cL:
            st.markdown("<div class='kpi-title'>Global Score</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-value'>{gs_txt}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-sub'>{status_pill_html(global_status)}</div>", unsafe_allow_html=True)

            # Block summary in required order
            st.markdown("<div class='kpi-title' style='margin-top:14px;'>Block summary (name → regime → score)</div>", unsafe_allow_html=True)
            st.markdown(
                f"""
<div class="muted" style="margin-bottom:6px;"><b>Market thermometers</b></div>
<div class="muted">{block_line("price_of_time", "Price of Time")}</div>
<div class="muted">{block_line("macro", "Macro Cycle")}</div>
<div class="muted">{block_line("conditions", "Conditions & Stress")}</div>
<div class="muted">{block_line("plumbing", "Liquidity / Plumbing")}</div>
<div style="height:12px;"></div>
<div class="muted" style="margin-bottom:6px;"><b>Structural constraints</b></div>
<div class="muted">{block_line("debt_fiscal", "Debt & Fiscal")}</div>
<div class="muted">{block_line("external", "External Balance")}</div>
""",
                unsafe_allow_html=True
            )

        with cR:
            st.markdown("<div class='kpi-title'>Operating lines (ETF)</div>", unsafe_allow_html=True)
            st.markdown(
                f"""
<div class="kpi-sub">
  <b>Equity</b>: {eq_line}<br/>
  <b>Duration</b>: {dur_line}<br/>
  <b>Credit</b>: {cr_line}<br/>
  <b>Hedges</b>: {hdg_line}
</div>
""",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # Groups
        # Choose columns based on mode
        if layout_mode == "Mobile":
            ncols = 1
        elif layout_mode == 'Wallboard (55")':
            ncols = 3
        else:
            ncols = 3

        show_all = st.toggle("Show all indicators (with definitions)", value=False)

        for gname, gdesc, keys in WALLBOARD_GROUPS:
            st.markdown(f"### {gname}")
            st.markdown(f"<div class='muted'>{gdesc}</div>", unsafe_allow_html=True)

            cols = st.columns(ncols)
            col_idx = 0
            for k in keys:
                s = indicators.get(k, pd.Series(dtype=float))
                with cols[col_idx]:
                    if s is None or s.empty:
                        # still show a consistent card even if missing
                        st.markdown("<div class='wb-card'>", unsafe_allow_html=True)
                        st.markdown(f"<div class='wb-title'>{INDICATOR_META[k]['label']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='wb-source'>{INDICATOR_META[k]['source']}</div>", unsafe_allow_html=True)
                        st.plotly_chart(
                            plot_sparkline(pd.Series(dtype=float), height=120),
                            use_container_width=True,
                            config={"displayModeBar": False},
                            key=f"wb_spark_{k}_missing",
                        )
                        st.markdown("<div class='muted'>Missing series.</div>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        wallboard_indicator_card(k, s, indicator_scores)

                    if show_all:
                        with st.expander(f"Details: {INDICATOR_META[k]['label']}", expanded=False):
                            exp = INDICATOR_META[k]["expander"]
                            st.markdown(f"**What it is:** {exp['what']}")
                            st.markdown(f"**Reference levels:** {exp['reference']}")
                            st.markdown("**Interpretation:**")
                            st.markdown(exp["interpretation"])
                            st.markdown(f"**Dalio bridge:** {exp.get('dalio_bridge','')}")
                col_idx = (col_idx + 1) % ncols

            st.markdown("---")

    # =========================================================
    # DEEP DIVE
    # =========================================================
    with tabs[2]:
        st.markdown("## Deep dive (charts + explanations)")
        st.markdown("<div class='muted'>Designed for analysis. Wallboard is for at-a-glance monitoring.</div>", unsafe_allow_html=True)

        # Render blocks with consistent 2-column layout (avoid disalignment)
        for bkey in ["price_of_time", "macro", "conditions", "plumbing", "debt_fiscal", "external", "cross"]:
            b = BLOCKS[bkey]
            st.markdown(f"### {b['name']}")
            st.markdown(f"<div class='muted'>{b['desc']}</div>", unsafe_allow_html=True)
            bscore = block_scores[bkey]["score"]
            bstatus = block_scores[bkey]["status"]
            btxt = "n/a" if np.isnan(bscore) else f"{bscore:.1f}"
            st.markdown(
                f"<div class='card-tight'><div class='muted'>Block score: <b>{btxt}</b> {status_pill_html(bstatus)}</div></div>",
                unsafe_allow_html=True
            )

            keys = b["indicators"]
            # 2-up columns, always consistent
            for i in range(0, len(keys), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j >= len(keys):
                        continue
                    k = keys[i + j]
                    s = indicators.get(k, pd.Series(dtype=float))
                    with cols[j]:
                        if s is None or s.empty:
                            st.markdown("<div class='card-tight'>", unsafe_allow_html=True)
                            st.warning(f"Missing data: {INDICATOR_META[k]['label']}")
                            st.markdown("</div>", unsafe_allow_html=True)
                        else:
                            render_tile(k, s, indicator_scores, years_back)

            st.markdown("---")

    # =========================================================
    # WHAT CHANGED
    # =========================================================
    with tabs[3]:
        st.markdown("## What changed (Δ7d / Δ30d / Δ1Y)")
        st.markdown(
            """
<div class="muted">
Use this table to spot inflections. Scores show the current regime, while deltas show what is *moving* recently.
For slower-moving quarterly series, Δ30d can be noisy or unavailable; interpret Δ1Y and the score more heavily.
</div>
""",
            unsafe_allow_html=True
        )

        rows = []
        for key, meta in INDICATOR_META.items():
            s = indicators.get(key, pd.Series(dtype=float))
            if s is None or s.empty:
                continue
            rows.append(
                {
                    "Indicator": meta["label"],
                    "Group": (
                        "Market thermometer" if meta.get("scoring_mode") == "z5y" else "Structural constraint"
                    ),
                    "Scoring": meta.get("scoring_mode", "z5y"),
                    "Δ7d %": pct_change_over_days(s, 7),
                    "Δ30d %": pct_change_over_days(s, 30),
                    "Δ1Y %": pct_change_over_days(s, 365),
                    "Score": indicator_scores[key]["score"],
                    "Regime": status_label(indicator_scores[key]["status"]),
                    "Why it matters": meta["expander"]["dalio_bridge"] if meta.get("scoring_mode") == "pct20y" else meta["expander"]["what"],
                }
            )

        if not rows:
            st.info("Not enough data to compute changes.")
        else:
            df = pd.DataFrame(rows)

            # Improve readability: wrap long text, keep columns compact
            df["Δ7d %"] = df["Δ7d %"].round(2)
            df["Δ30d %"] = df["Δ30d %"].round(2)
            df["Δ1Y %"] = df["Δ1Y %"].round(2)
            df["Score"] = df["Score"].round(1)

            # Column help (tooltips) — requested
            col_cfg = {
                "Indicator": st.column_config.TextColumn(
                    "Indicator",
                    help="The underlying series (ETF-friendly macro indicator).",
                    width="large",
                ),
                "Group": st.column_config.TextColumn(
                    "Group",
                    help="Market thermometers move fast; structural constraints move slower but can dominate regimes.",
                    width="medium",
                ),
                "Scoring": st.column_config.TextColumn(
                    "Scoring",
                    help="z5y = z-score vs ~5Y history; pct20y = percentile vs ~20Y history mapped to 0–100.",
                    width="small",
                ),
                "Δ7d %": st.column_config.NumberColumn(
                    "Δ7d %",
                    help="Short-term move. Can be noisy for low-frequency series.",
                    format="%.2f",
                    width="small",
                ),
                "Δ30d %": st.column_config.NumberColumn(
                    "Δ30d %",
                    help="Monthly move. Best for daily/weekly series.",
                    format="%.2f",
                    width="small",
                ),
                "Δ1Y %": st.column_config.NumberColumn(
                    "Δ1Y %",
                    help="Medium-term move. Useful for slow-moving series.",
                    format="%.2f",
                    width="small",
                ),
                "Score": st.column_config.NumberColumn(
                    "Score",
                    help="0–100 regime score (higher = more risk-on).",
                    format="%.1f",
                    width="small",
                ),
                "Regime": st.column_config.TextColumn(
                    "Regime",
                    help="Risk-on / Neutral / Risk-off derived from score thresholds.",
                    width="small",
                ),
                "Why it matters": st.column_config.TextColumn(
                    "Why it matters",
                    help="One-line reminder to avoid losing context when scanning many indicators.",
                    width="large",
                ),
            }

            # Sort for scanning
            df = df.sort_values(["Group", "Indicator"]).reset_index(drop=True)

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config=col_cfg,
            )

            st.markdown(
                """
<div class="card-tight">
  <div class="muted"><b>How to use this section</b></div>
  <div class="muted">
    • Use <b>Score/Regime</b> to understand the current state (thermometer).<br/>
    • Use <b>Δ30d / Δ1Y</b> to detect inflections and confirm direction (momentum of the driver).<br/>
    • If a line is “weird” (e.g., quarterly series), rely more on <b>Score + Δ1Y</b> than Δ7d.
  </div>
</div>
""",
                unsafe_allow_html=True
            )

    # =========================================================
    # REPORT / PAYLOAD
    # =========================================================
    with tabs[4]:
        st.markdown("## Report (optional) — payload for ChatGPT")
        st.markdown("<div class='muted'>Copyable payload including Dalio blocks and scoring modes.</div>", unsafe_allow_html=True)

        generate_payload = st.button("Generate payload", type="primary")

        if generate_payload:
            payload_lines = []
            payload_lines.append("macro_regime_payload_dalio:")
            payload_lines.append(f"  generated_at_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            payload_lines.append(f"  global_score: {0.0 if np.isnan(global_score) else round(global_score, 1)}")
            payload_lines.append(f"  global_status: {global_status}")
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
                payload_lines.append(f"      status: {bstatus}")

            payload_lines.append("  operating_lines:")
            eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)
            payload_lines.append(f'    equity: "{eq_line}"')
            payload_lines.append(f'    duration: "{dur_line}"')
            payload_lines.append(f'    credit: "{cr_line}"')
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
                payload_lines.append(f"      status: {status}")
                payload_lines.append(f"      delta_30d_pct: {0.0 if np.isnan(d30) else round(d30, 2)}")

            payload_text = "\n".join(payload_lines)
            st.code(payload_text, language="yaml")

            st.markdown("**Suggested prompt (Dalio-aware):**")
            st.code(
                """
You are a multi-asset macro strategist. You receive the YAML payload above (macro-finance dashboard, Dalio-enhanced).

Tasks:
1) Reconstruct the regime: separate “market thermometers” (USD/spreads/VIX/trend/real rates) from “constraints” (debt service/deficit/term premium/external balance).
2) Explain whether there is risk of a structural regime shift (fiscal dominance / financial repression / inflationary deleveraging).
3) Produce an ETF-oriented action note:
   - Equity exposure (risk budget)
   - Duration (short/neutral/long; nominal vs TIPS)
   - Credit risk (IG vs HY)
   - Hedges (USD, gold, cash-like)
   - 3–5 triggers to monitor over the next 2–6 weeks (heuristic thresholds)

Tone: concrete, cautious, implementable.
                """.strip(),
                language="markdown"
            )


if __name__ == "__main__":
    main()
