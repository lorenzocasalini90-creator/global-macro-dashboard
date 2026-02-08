import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from pandas.tseries.offsets import DateOffset

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Global finance | Macro overview",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS (solo styling: niente layout HTML critico)
# ============================================================

st.markdown(
    """
<style>
  :root{
    --bg:#0b0f19;
    --border:rgba(255,255,255,0.10);
    --muted:rgba(255,255,255,0.72);
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

  /* Tabs readable + selected red */
  button[data-baseweb="tab"]{
    color: rgba(255,255,255,0.92) !important;
    font-weight: 750 !important;
    background: rgba(255,255,255,0.045) !important;
    border-radius: 12px !important;
    margin-right: 6px !important;
    padding: 10px 14px !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
  }
  button[data-baseweb="tab"][aria-selected="true"]{
    color: rgba(255,255,255,0.98) !important;
    background: var(--accentSoft) !important;
    border: 1px solid rgba(244,63,94,0.55) !important;
  }

  /* Buttons (report gen etc.) */
  .stButton>button{
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    background: rgba(255,255,255,0.06) !important;
    color: rgba(255,255,255,0.92) !important;
    font-weight: 750 !important;
    padding: 0.55rem 0.85rem !important;
  }
  .stButton>button:hover{
    background: rgba(255,255,255,0.10) !important;
    border-color: rgba(255,255,255,0.22) !important;
  }

  /* Expander: no white bar */
  div[data-testid="stExpander"]{
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 14px !important;
    background: rgba(255,255,255,0.03) !important;
    overflow: hidden !important;
  }
  div[data-testid="stExpander"] summary{
    background: rgba(255,255,255,0.05) !important;
    color: rgba(255,255,255,0.94) !important;
    padding: 10px 12px !important;
  }

  /* Make captions readable */
  .stCaption, [data-testid="stCaptionContainer"] { color: rgba(255,255,255,0.70) !important; }

</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# INDICATORS & BLOCKS
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
        "expander": {
            "what": "USD strength proxy. If DXY unavailable, uses broad trade-weighted USD.",
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
        "expander": {
            "what": "Trend proxy: SPY vs 200-day moving average.",
            "reference": ">1 = uptrend; <1 = downtrend (heuristics).",
            "interpretation": "- Above 1 supports risk-on behavior.\n- Below 1 signals risk-off trend regime.",
            "bridge": "Trend down + credit stress up is a deleveraging signature.",
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
        "expander": {
            "what": "Total Fed assets: system liquidity proxy.",
            "reference": "Expansion (QE) supports risk; contraction (QT) drains (heuristics).",
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
        "expander": {
            "what": "Reverse repo usage: cash parked in risk-free facility.",
            "reference": "High RRP = liquidity stuck; falling RRP can release liquidity (heuristics).",
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
        "expander": {
            "what": "Government interest expense: debt-service pressure proxy.",
            "reference": "Rising debt service reduces policy flexibility (heuristics).",
            "interpretation": "- Persistent rise increases constraint.\n- Stabilization reduces constraint.",
            "bridge": "Debt service pressure increases incentives for funding-friendly outcomes.",
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
            "what": "Government receipts: supports debt-service capacity.",
            "reference": "Used to compute interest/receipts proxy.",
            "interpretation": "- Receipts up improves capacity.\n- Receipts down tightens constraint.",
            "bridge": "Higher receipts reduce binding nature of debt service.",
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
            "what": "Share of receipts consumed by interest expense.",
            "reference": "High and rising = constraint becomes political (heuristics).",
            "interpretation": "- Higher ratio = tighter fiscal constraint.\n- Lower ratio = more room.",
            "bridge": "Higher debt service increases incentives for inflation-tolerant policy.",
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
            "what": "Fiscal balance (% of GDP). Negative = deficit.",
            "reference": "Persistent large deficits increase supply pressure (heuristics).",
            "interpretation": "- More negative = more funding pressure.\n- Improvement reduces pressure.",
            "bridge": "Supply pressure can show up as higher term premium and weaker bond hedge behavior.",
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
            "what": "Term premium: compensation required to hold nominal duration.",
            "reference": "Rising term premium reduces hedge quality (heuristics).",
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
        "expander": {
            "what": "External funding constraint proxy. Negative = reliance on foreign capital.",
            "reference": "More negative increases vulnerability during USD tightening (heuristics).",
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
        "expander": {
            "what": "Gold: hedge demand proxy (policy/inflation/tail risk).",
            "reference": "Breakouts often reflect hedge demand rather than growth optimism (heuristics).",
            "interpretation": "- Gold up can signal hedge demand.\n- Gold down in equity bull may reflect clean risk-on.",
            "bridge": "Gold can hedge environments where policy turns funding-friendly or real returns compress.",
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
        "desc": "Debt service, deficit dynamics, and funding constraint signal.",
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
# DATA: FETCHERS
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
        col = "Adj Close" if "Adj Close" in df.columns else "Close"
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
    h = hist.dropna()
    if len(h) < 10 or pd.isna(latest):
        return np.nan
    return float((h <= latest).mean())

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
    if status == "risk_on":
        return "Risk-on"
    if status == "risk_off":
        return "Risk-off"
    if status == "neutral":
        return "Neutral"
    return "n/a"

def semaphore(status: str) -> str:
    return {"risk_on": "🟢", "neutral": "🟡", "risk_off": "🔴"}.get(status, "⚪")

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

def recent_trend(series: pd.Series) -> dict:
    if series is None or series.dropna().shape[0] < 10:
        return {"window_label": "n/a", "delta_pct": np.nan, "arrow": "→"}
    freq = infer_frequency_days(series)
    if freq >= 20:
        days = 90
        label = "1Q"
    else:
        days = 30
        label = "30d"
    d = pct_change_over_days(series, days)
    if np.isnan(d):
        return {"window_label": label, "delta_pct": np.nan, "arrow": "→"}
    arrow = "↑" if d > 0.25 else ("↓" if d < -0.25 else "→")
    return {"window_label": label, "delta_pct": d, "arrow": arrow}

# ============================================================
# PLOT
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
        text=f"<b>{title}</b>",
        showarrow=False,
        align="left",
        font=dict(size=14, color="rgba(255,255,255,0.95)"),
        bgcolor="rgba(0,0,0,0.0)"
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
# OPERATING LINES
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
# WALLBOARD TILE (STREAMLIT NATIVE — no HTML)
# ============================================================

def render_tile_native(key: str, series: pd.Series, indicator_scores: dict, show_expander: bool = False):
    meta = INDICATOR_META[key]
    sc = indicator_scores.get(key, {})
    score = sc.get("score", np.nan)
    status = sc.get("status", "n/a")
    latest = sc.get("latest", np.nan)

    latest_txt = fmt_value(latest, meta["unit"], meta.get("scale", 1.0))
    tr = recent_trend(series)
    wlab = tr["window_label"]
    d = tr["delta_pct"]
    arrow = tr["arrow"]
    d_txt = "n/a" if np.isnan(d) else f"{d:+.1f}%"

    ref_line = meta.get("ref_line", None)
    ref_txt = "—" if ref_line is None else str(ref_line)
    ref_note = meta["expander"].get("reference", "—")

    # The tile
    with st.container():
        st.markdown(f"**{meta['label']}**")
        st.caption(meta["source"])

        c1, c2 = st.columns([2, 1], vertical_alignment="center")
        with c1:
            st.markdown(f"### {latest_txt}")
        with c2:
            st.markdown(f"**{semaphore(status)} {status_label(status)}**")

        # Score bar
        if np.isnan(score):
            st.progress(0)
            st.caption("Score: n/a")
        else:
            st.progress(int(np.clip(score, 0, 100)))
            st.caption(f"Score: {score:.0f} · Trend ({wlab}): {arrow} {d_txt}")

        st.caption(f"Reference: {ref_txt} · {ref_note}")

        if show_expander:
            with st.expander("Indicator guide", expanded=False):
                exp = meta["expander"]
                st.markdown(f"**What it is:** {exp.get('what','')}")
                st.markdown(f"**Reference levels / thresholds:** {exp.get('reference','')}")
                st.markdown("**How to read it:**")
                st.markdown(exp.get("interpretation", ""))
                st.markdown(f"**Why it matters (policy/funding link):** {exp.get('bridge','')}")

# ============================================================
# REPORT PROMPT (unchanged)
# ============================================================

REPORT_PROMPT = """SYSTEM / ROLE

You are a senior multi-asset macro strategist writing an internal PM / CIO regime report.
You think in terms of market behavior vs structural constraints, not forecasts.
Your job is to diagnose the current macro regime and translate it into portfolio-relevant implications, using a Dalio-enhanced framework.

You are receiving a YAML payload containing updated macro-financial indicators (rates, inflation, credit, liquidity, fiscal, external balance, gold, etc.).

CRITICAL OUTPUT RULES (NON-NEGOTIABLE)

You must reproduce the exact report structure and section order specified below.

No section may be omitted, merged, or reordered, even if indicators are unchanged.

Do not speculate beyond the data provided.

Do not introduce new indicators or concepts not already in the framework.

Writing must be:

concrete,

cautious,

implementation-oriented,

internally consistent across time.

Each analytical block must include:

a short “What it captures” explanation (if specified),

a one-liner,

KPI-level implications.

TASKS

Using the YAML payload:

1. Reconstruct the macro regime

Explicitly separate:

Market Thermometers (fast, reflexive indicators)

Structural Constraints (slow, compounding pressures)

Assign an implicit regime tone (Risk-On / Neutral / Risk-Off) by behavior, not direction.

2. Assess structural regime risk

Evaluate whether conditions point toward:

fiscal dominance,

financial repression,

inflation-tolerant policy,

or continued late-cycle equilibrium.

Do not call crises unless directly implied by constraints.

3. Translate the regime into portfolio logic

Produce an ETF-oriented action note:

Equity exposure

Duration (nominal vs TIPS)

Credit (IG vs HY)

Hedges (USD, gold, cash)

Emphasize asymmetry, risk budgeting, and optionality.

4. Define short-horizon triggers

Provide 3–5 heuristic triggers (2–6 week horizon).

Triggers must be:

observable,

threshold-based,

directly linked to regime change or de-risking.

MANDATORY REPORT STRUCTURE (FOLLOW EXACTLY)

# Global Macro Regime Report

## Dalio-Enhanced, Multi-Asset View — Internal PM Edition

[Insert current date]

How to Read This Report: What “Risk-On / Neutral / Risk-Off” Really Means

(Define regimes as behavioral pricing regimes, not forecasts.)

Executive Summary

(Single coherent narrative of the regime, tensions, and positioning.)

Context Overview: How This Framework Works

(Market Thermometers vs Structural Constraints.)

Reconstructing the Regime

Market Thermometers

1. Price of Time

1A) Real & Nominal Rates

1B) Yield Curve

2. Macro Cycle

2A) Inflation, Breakevens & Labor

3. Conditions and Stress

3A) Financial Conditions & Risk Appetite

4. Liquidity Plumbing

4A) Liquidity Plumbing

Structural Constraints

5) Debt & Fiscal

5A) Debt Service & Fiscal Dynamics

6. External Balance

7. Gold

   Structural Regime Shift

(Probability, path, and logic — no speculation.)

ETF-Oriented Action Note

Equity Exposure

Duration

Credit Risk

Hedges

Key Triggers

(3–5 near-term triggers.)

Final Bottom Line

(One paragraph, no bullets.)

Appendix: Portfolio Translation & Regime Playbook (Internal)

A. Regime Scorecard Snapshot

B. What Works in This Regime

C. What Requires Caution

D. Regime Transition Map

E. Trigger Matrix

F. Meta-Rules

G. One-Page CIO Takeaway
""".strip()

# ============================================================
# MAIN
# ============================================================

def main():
    st.title("Global finance | Macro overview")

    # Sidebar
    st.sidebar.header("Settings")
    if st.sidebar.button("🔄 Refresh data (clear cache)"):
        st.cache_data.clear()
        st.rerun()

    years_back = st.sidebar.slider("History (years)", 5, 30, 15)
    layout_mode = st.sidebar.selectbox("Layout mode", ["Auto", "Wallboard (55\")", "Deep dive first"], index=0)

    today = datetime.now(timezone.utc).date()
    start_date = (today - DateOffset(years=years_back)).date().isoformat()
    st.sidebar.markdown(f"**Start date:** {start_date}")

    fred_key = get_fred_api_key()
    if fred_key is None:
        st.sidebar.error("⚠️ Missing `FRED_API_KEY` in secrets.")

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

        # Direct FRED
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

        # YFinance
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
        if binfo["weight"] > 0 and not np.isnan(bscore):
            global_score += bscore * binfo["weight"]
            w_used += binfo["weight"]

    global_score = (global_score / w_used) if w_used > 0 else np.nan
    global_status = classify_status(global_score)
    block_scores["GLOBAL"] = {"score": global_score, "status": global_status}

    # Data freshness
    latest_points = [s.index.max() for s in indicators.values() if s is not None and not s.empty]
    data_max_date = max(latest_points) if latest_points else None
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Tabs
    tabs = st.tabs(["Overview", "Wallboard", "Deep dive", "What changed", "Report generation"])

    # ============================================================
    # OVERVIEW (streamlit native)
    # ============================================================
    with tabs[0]:
        st.caption("A macro-finance wallboard that separates fast market thermometers from slow structural constraints, then translates regime into ETF operating lines.")

        eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("Global score")
            gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
            st.markdown(f"### {gs_txt}  {semaphore(global_status)}")
            st.caption(f"Regime: {status_label(global_status)}")
            if not np.isnan(global_score):
                st.progress(int(np.clip(global_score, 0, 100)))
            st.markdown("**Operating lines**")
            st.write(f"**Equity:** {eq_line}")
            st.write(f"**Duration:** {dur_line}")
            st.write(f"**Credit:** {cr_line}")
            st.write(f"**Hedges:** {hdg_line}")

        with c2:
            st.subheader("Block scorecard")
            st.markdown("**Market Thermometers**")
            for k in ["price_of_time", "macro", "conditions", "plumbing"]:
                sc = block_scores[k]["score"]
                stt = block_scores[k]["status"]
                sc_txt = "n/a" if np.isnan(sc) else f"{sc:.1f}"
                st.write(f"{semaphore(stt)} {BLOCKS[k]['name']}: **{status_label(stt)}** ({sc_txt})")

            st.markdown("**Structural Constraints**")
            for k in ["policy_link", "external", "gold_block"]:
                sc = block_scores[k]["score"]
                stt = block_scores[k]["status"]
                sc_txt = "n/a" if np.isnan(sc) else f"{sc:.1f}"
                st.write(f"{semaphore(stt)} {BLOCKS[k]['name']}: **{status_label(stt)}** ({sc_txt})")

        with c3:
            st.subheader("Policy / funding links")
            st.write("1) **Deficit pressure ↑ → supply pressure ↑ → term premium risk ↑**")
            st.write("2) **Debt service pressure ↑ → policy flexibility ↓**")
            st.write("3) **Term premium ↑ + USD ↑ → global tightening impulse**")
            st.write("4) **External deficit → vulnerability in USD tightening**")
            st.write("5) **Gold strength often reflects hedge demand, not growth optimism**")

            st.divider()
            st.caption(f"Now: {now_utc}")
            st.caption(f"Latest datapoint: {('n/a' if data_max_date is None else str(pd.to_datetime(data_max_date).date()))}")
            st.caption(f"Layout mode: {layout_mode}")

        with st.expander("How to read Risk-on / Neutral / Risk-off (behavioral, not forecasts)", expanded=True):
            st.markdown(
                """
**Risk-on:** markets price easier conditions (lower stress premia), credit behaves well, trend and risk appetite are supportive.  
**Neutral:** mixed signals; sizing discipline matters more than directional conviction.  
**Risk-off:** stress/tightening dominates; protect downside first (quality, liquidity, hedges).

**How scores work:**  
- **Market thermometers** use a ~5Y z-score (`z5y`) → clamped to [-2,+2] → mapped to 0–100.  
- **Structural constraints** use a ~20Y percentile (`pct20y`) → mapped to [-2,+2] → 0–100.  
- **Thresholds:** >60 Risk-on, 40–60 Neutral, <40 Risk-off (heuristics).
                """.strip()
            )

    # ============================================================
    # WALLBOARD (native tiles + dropdown)
    # ============================================================
    with tabs[1]:
        st.subheader("Wallboard")
        st.caption("Order: overall → component scores → operating lines → tiles. No HTML tiles: Streamlit-native to eliminate renderer errors.")

        eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)

        top1, top2 = st.columns([1, 1])
        with top1:
            st.markdown("### Overall regime")
            gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
            st.markdown(f"## {gs_txt}  {semaphore(global_status)}")
            st.caption(f"{status_label(global_status)}")
            if not np.isnan(global_score):
                st.progress(int(np.clip(global_score, 0, 100)))
        with top2:
            st.markdown("### Operating lines (ETF)")
            st.write(f"**Equity:** {eq_line}")
            st.write(f"**Duration:** {dur_line}")
            st.write(f"**Credit:** {cr_line}")
            st.write(f"**Hedges:** {hdg_line}")

        st.markdown("### Component scores")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**Market Thermometers**")
            for k in ["price_of_time", "macro", "conditions", "plumbing"]:
                sc = block_scores[k]["score"]
                stt = block_scores[k]["status"]
                st.write(f"{semaphore(stt)} {BLOCKS[k]['name']}: **{status_label(stt)}** ({'n/a' if np.isnan(sc) else f'{sc:.1f}'})")
        with cc2:
            st.markdown("**Structural Constraints**")
            for k in ["policy_link", "external", "gold_block"]:
                sc = block_scores[k]["score"]
                stt = block_scores[k]["status"]
                st.write(f"{semaphore(stt)} {BLOCKS[k]['name']}: **{status_label(stt)}** ({'n/a' if np.isnan(sc) else f'{sc:.1f}'})")

        st.divider()

        # Dropdown / menu a tendina
        keys = list(INDICATOR_META.keys())
        selected = st.selectbox("Select indicator (thermometers / constraints)", keys, format_func=lambda k: INDICATOR_META[k]["label"])
        s_sel = indicators.get(selected, pd.Series(dtype=float))
        meta_sel = INDICATOR_META[selected]
        sc_sel = indicator_scores.get(selected, {})

        with st.expander(f"Selected indicator — {meta_sel['label']}", expanded=True):
            st.write(f"**Source:** {meta_sel['source']}")
            st.write(f"**Latest:** {fmt_value(sc_sel.get('latest', np.nan), meta_sel['unit'], meta_sel.get('scale', 1.0))}")
            st.write(f"**Regime:** {semaphore(sc_sel.get('status','n/a'))} {status_label(sc_sel.get('status','n/a'))}")
            if (s_sel is not None) and (not s_sel.empty):
                st.plotly_chart(plot_premium(s_sel, meta_sel["label"], ref_line=meta_sel.get("ref_line", None), height=260),
                                use_container_width=True, config={"displayModeBar": False}, key=f"wb_sel_{selected}")
            exp = meta_sel["expander"]
            st.markdown(f"**What it is:** {exp.get('what','')}")
            st.markdown(f"**Reference:** {exp.get('reference','')}")
            st.markdown("**How to read it:**")
            st.markdown(exp.get("interpretation",""))
            st.markdown(f"**Why it matters:** {exp.get('bridge','')}")

        show_guides = st.toggle("Show guide under each tile (long)", value=False)

        def render_group(title: str, desc: str, group_keys: list[str]):
            st.markdown(f"## {title}")
            st.caption(desc)

            # 4 columns on desktop
            cols = st.columns(4)
            for i, k in enumerate(group_keys):
                s = indicators.get(k, pd.Series(dtype=float))
                with cols[i % 4]:
                    if s is None or s.empty:
                        st.warning("Missing data")
                        st.markdown(f"**{INDICATOR_META[k]['label']}**")
                        st.caption(INDICATOR_META[k]["source"])
                    else:
                        render_tile_native(k, s, indicator_scores, show_expander=show_guides)
                    st.divider()

        render_group("Price of Time", "Rates and curve: the price of time and late-cycle signal.",
                     ["real_10y", "nominal_10y", "yield_curve_10_2"])
        render_group("Macro Cycle", "Inflation and growth: policy constraint and cycle pressure.",
                     ["breakeven_10y", "cpi_yoy", "unemployment_rate"])
        render_group("Conditions & Stress", "Fast regime: USD, credit stress, vol, trend, risk appetite.",
                     ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"])
        render_group("Liquidity / Plumbing", "System liquidity: tailwind vs drain for risk assets.",
                     ["fed_balance_sheet", "rrp"])
        render_group("Fiscal / Policy Constraint", "Debt service, deficit dynamics, and funding constraint signal.",
                     ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"])
        render_group("External Balance & Gold", "External funding reliance + hedge demand confirmation.",
                     ["current_account_gdp", "gold"])

    # ============================================================
    # DEEP DIVE
    # ============================================================
    with tabs[2]:
        st.subheader("Deep dive")
        st.caption("Charts + definitions.")

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
            sc = indicator_scores.get(k, {})
            st.markdown(f"### {meta['label']}  —  {semaphore(sc.get('status','n/a'))}")
            st.caption(meta["source"])

            if s is None or s.empty:
                st.warning("Missing data for this indicator in the selected history window.")
            else:
                st.plotly_chart(plot_premium(s, meta["label"], ref_line=meta.get("ref_line", None), height=340),
                                use_container_width=True, config={"displayModeBar": False}, key=f"deep_{k}")

            with st.expander("Indicator guide", expanded=False):
                exp = meta["expander"]
                st.markdown(f"**What it is:** {exp.get('what','')}")
                st.markdown(f"**Reference levels / thresholds:** {exp.get('reference','')}")
                st.markdown("**How to read it:**")
                st.markdown(exp.get("interpretation", ""))
                st.markdown(f"**Why it matters (policy/funding link):** {exp.get('bridge','')}")

            st.divider()

    # ============================================================
    # WHAT CHANGED (lightweight; puoi rimettere la tua watchlist se vuoi)
    # ============================================================
    with tabs[3]:
        st.subheader("What changed")
        st.caption("Quick scan: movers and proximity to thresholds.")

        rows = []
        for key, meta in INDICATOR_META.items():
            s = indicators.get(key, pd.Series(dtype=float))
            if s is None or s.empty:
                continue

            tr = recent_trend(s)
            window = tr["window_label"]
            dwin = tr["delta_pct"]

            d7 = pct_change_over_days(s, 7)
            d30 = pct_change_over_days(s, 30)
            d90 = pct_change_over_days(s, 90)
            d1y = pct_change_over_days(s, 365)

            sc = indicator_scores.get(key, {})
            score = sc.get("score", np.nan)
            status = sc.get("status", "n/a")
            mode = meta.get("scoring_mode", "z5y")

            prox = 0.0 if np.isnan(score) else max(0.0, 20.0 - min(abs(score - 40), abs(score - 60))) / 20.0
            move = 0.0 if np.isnan(dwin) else min(1.0, abs(dwin) / 10.0)
            attention = 0.55 * prox + 0.45 * move
            watch = "WATCH" if attention >= 0.55 else ""

            rows.append({
                "Indicator": meta["label"],
                "Scoring": mode,
                "Regime": f"{semaphore(status)} {status_label(status)}",
                "Score": (np.nan if np.isnan(score) else round(score, 1)),
                f"Trend ({window}) %": (np.nan if np.isnan(dwin) else round(dwin, 2)),
                "Δ 7d %": (np.nan if np.isnan(d7) else round(d7, 2)),
                "Δ 30d %": (np.nan if np.isnan(d30) else round(d30, 2)),
                "Δ 1Q %": (np.nan if np.isnan(d90) else round(d90, 2)),
                "Δ 1Y %": (np.nan if np.isnan(d1y) else round(d1y, 2)),
                "Watchlist": watch,
                "Attention": round(attention, 2),
            })

        if rows:
            df = pd.DataFrame(rows).sort_values(["Watchlist", "Attention"], ascending=[True, False])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No sufficient data to compute changes.")

    # ============================================================
    # REPORT GENERATION
    # ============================================================
    with tabs[4]:
        st.subheader("Report generation")
        st.caption("Single copy/paste output: prompt first, then YAML payload.")

        generate = st.button("Generate one-shot prompt + payload")
        if generate:
            payload_lines = []
            payload_lines.append("macro_regime_payload:")
            payload_lines.append(f"  generated_at_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            payload_lines.append(f"  global_score: {0.0 if np.isnan(global_score) else round(global_score, 1)}")
            payload_lines.append(f"  global_status: {global_status}")
            payload_lines.append("  scoring_notes: \"Market thermometers use z5y; structural constraints use pct20y\"")

            payload_lines.append("  blocks:")
            for bkey, binfo in BLOCKS.items():
                bscore = block_scores[bkey]["score"]
                bstatus = block_scores[bkey]["status"]
                payload_lines.append(f"    - key: \"{bkey}\"")
                payload_lines.append(f"      name: \"{binfo['name']}\"")
                payload_lines.append(f"      group: \"{binfo['group']}\"")
                payload_lines.append(f"      weight: {binfo['weight']}")
                payload_lines.append(f"      score: {0.0 if np.isnan(bscore) else round(bscore, 1)}")
                payload_lines.append(f"      status: {bstatus}")

            eq_line, dur_line, cr_line, hdg_line = operating_lines(block_scores, indicator_scores)
            payload_lines.append("  operating_lines:")
            payload_lines.append(f"    equity_exposure: \"{eq_line}\"")
            payload_lines.append(f"    duration: \"{dur_line}\"")
            payload_lines.append(f"    credit: \"{cr_line}\"")
            payload_lines.append(f"    hedges: \"{hdg_line}\"")

            payload_lines.append("  indicators:")
            for key, meta in INDICATOR_META.items():
                s_info = indicator_scores.get(key, {})
                score = s_info.get("score", np.nan)
                status = s_info.get("status", "n/a")
                latest = s_info.get("latest", np.nan)
                series = indicators.get(key, pd.Series(dtype=float))

                tr = recent_trend(series)
                window = tr["window_label"]
                dwin = tr["delta_pct"]

                payload_lines.append(f"    - key: \"{key}\"")
                payload_lines.append(f"      name: \"{meta['label']}\"")
                payload_lines.append(f"      source: \"{meta['source']}\"")
                payload_lines.append(f"      scoring_mode: \"{meta.get('scoring_mode','z5y')}\"")
                payload_lines.append(f"      latest_value: \"{fmt_value(latest, meta['unit'], meta.get('scale', 1.0))}\"")
                payload_lines.append(f"      score: {0.0 if np.isnan(score) else round(score, 1)}")
                payload_lines.append(f"      status: {status}")
                payload_lines.append(f"      trend_window: \"{window}\"")
                payload_lines.append(f"      trend_change_pct: {0.0 if np.isnan(dwin) else round(dwin, 2)}")
                payload_lines.append(f"      reference_line: {('null' if meta.get('ref_line', None) is None else meta.get('ref_line'))}")
                payload_lines.append(f"      reference_notes: \"{meta['expander'].get('reference','')}\"")

            payload_text = "\n".join(payload_lines)

            one_shot = (
                "### COPY/PASTE BELOW (PROMPT + PAYLOAD)\n\n"
                + REPORT_PROMPT
                + "\n\n---\n\n"
                + "YAML PAYLOAD:\n\n```yaml\n"
                + payload_text
                + "\n```\n"
            )

            st.code(one_shot, language="markdown")
            st.caption("Tip: paste the entire block into a new chat. The model should follow the prompt, then read the YAML payload.")

if __name__ == "__main__":
    main()
