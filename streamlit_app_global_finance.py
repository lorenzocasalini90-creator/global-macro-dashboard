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
    page_title="Global finance | Macro overview",
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
        --border:rgba(255,255,255,0.08);
        --muted:rgba(255,255,255,0.65);
        --text:rgba(255,255,255,0.92);
        --accent:rgba(99,102,241,1); /* indigo */
        --good:rgba(34,197,94,1);    /* green */
        --warn:rgba(245,158,11,1);   /* amber */
        --bad:rgba(239,68,68,1);     /* red */
      }

      /* Streamlit background */
      .stApp {
        background: radial-gradient(1200px 700px at 20% 0%, #121a33 0%, #0b0f19 45%, #0b0f19 100%);
        color: var(--text);
      }
      /* Remove top padding a bit */
      .block-container { padding-top: 1.1rem; }

      /* Headings */
      h1, h2, h3, h4 { color: var(--text); letter-spacing: -0.02em; }
      .muted { color: var(--muted); }

      /* Card components */
      .kpi-grid {
        display:grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
      }
      .kpi-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.03) 100%);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px 16px 12px 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
      }
      .kpi-title { font-size: 0.95rem; color: var(--muted); margin-bottom: 6px; }
      .kpi-value { font-size: 2.0rem; font-weight: 750; line-height: 1.05; color: var(--text); }
      .kpi-sub { margin-top: 6px; font-size: 0.95rem; color: var(--muted); }
      .pill {
        display:inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.04);
        font-size: 0.85rem;
        color: var(--text);
        margin-right: 8px;
      }
      .pill.good { border-color: rgba(34,197,94,0.35); background: rgba(34,197,94,0.10); }
      .pill.warn { border-color: rgba(245,158,11,0.35); background: rgba(245,158,11,0.10); }
      .pill.bad  { border-color: rgba(239,68,68,0.35);  background: rgba(239,68,68,0.10); }

      .section-card {
        background: rgba(255,255,255,0.035);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 14px 14px 10px 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
        margin-bottom: 12px;
      }
      .tile-title { font-size: 1.0rem; font-weight: 650; margin-bottom: 2px; }
      .tile-meta { color: var(--muted); font-size: 0.85rem; margin-bottom: 8px; }
      .tile-toprow {
        display:flex; align-items:baseline; justify-content:space-between; gap: 10px;
        margin-bottom: 6px;
      }
      .tiny { font-size: 0.85rem; color: var(--muted); }
      hr { border-color: var(--border); }

      /* Tabs aesthetics */
      button[data-baseweb="tab"] {
        color: var(--muted) !important;
      }
      button[data-baseweb="tab"][aria-selected="true"]{
        color: var(--text) !important;
      }

      /* Dataframe */
      .stDataFrame { border: 1px solid var(--border); border-radius: 12px; overflow:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# CONFIG: INDICATORS & BLOCKS
# =========================

INDICATOR_META = {
    # Policy & Real Rates
    "real_10y": {
        "label": "US 10Y TIPS real yield",
        "unit": "%",
        "direction": -1,  # high = risk-off
        "source": "FRED DFII10",
        "scale": 1.0,
        "ref_line": 0.0,
        "expander": {
            "what": "Rendimento reale (TIPS 10Y): prezzo del tempo al netto dell’inflazione attesa.",
            "reference": "<0% molto accomodante; 0–2% neutrale; >2% restrittivo (euristiche).",
            "interpretation": (
                "- **↑ real yield** → headwind per equity (growth) e duration lunga.\n"
                "- **↓ real yield** → tailwind per risk asset e bond long duration."
            ),
        },
    },
    "nominal_10y": {
        "label": "US 10Y nominal yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DGS10",
        "scale": 1.0,
        "ref_line": None,
        "expander": {
            "what": "Rendimento nominale Treasury 10Y: costo del capitale e benchmark per sconto cash flow.",
            "reference": "Movimenti rapidi verso l’alto spesso equivalgono a tightening finanziario.",
            "interpretation": (
                "- **↑ rapido** → pressione su equity e su bond esistenti.\n"
                "- **↓** → supporto a duration e spesso a equity (dipende dal contesto macro)."
            ),
        },
    },
    "yield_curve_10_2": {
        "label": "US Yield curve (10Y–2Y)",
        "unit": "pp",
        "direction": +1,
        "source": "FRED DGS10 - DGS2",
        "scale": 1.0,
        "ref_line": 0.0,
        "expander": {
            "what": "Differenza 10Y–2Y: proxy ciclo/attese recessione.",
            "reference": "<0 curva invertita (late cycle); >0 curva normale (euristiche).",
            "interpretation": (
                "- **Molto negativa** e persistente → rischio recessione / risk-off.\n"
                "- **Ritorno sopra 0** → normalizzazione del ciclo."
            ),
        },
    },

    # Inflation & Growth
    "breakeven_10y": {
        "label": "10Y Breakeven inflation",
        "unit": "%",
        "direction": -1,
        "source": "FRED T10YIE",
        "scale": 1.0,
        "ref_line": 2.5,  # euristico
        "expander": {
            "what": "Inflazione attesa (10Y) implicita dal mercato: nominali vs TIPS.",
            "reference": "~2–3% = ben ancorata; molto >3% = rischio inflazione sticky (euristiche).",
            "interpretation": (
                "- **↑** → rischio policy restrittiva più a lungo.\n"
                "- **↓ verso target** → più spazio per easing."
            ),
        },
    },
    "cpi_yoy": {
        "label": "US CPI YoY",
        "unit": "%",
        "direction": -1,
        "source": "FRED CPIAUCSL (YoY calcolato)",
        "scale": 1.0,
        "ref_line": 3.0,  # euristico
        "expander": {
            "what": "Inflazione headline YoY (proxy).",
            "reference":  "Target 2% (Fed); >3–4% a lungo = sticky (euristiche).",
            "interpretation": (
                "- **Disinflation** → supportive per duration ed equity.\n"
                "- **Re-acceleration** → rischio tightening / tassi più alti più a lungo."
            ),
        },
    },
    "unemployment_rate": {
        "label": "US Unemployment rate",
        "unit": "%",
        "direction": -1,
        "source": "FRED UNRATE",
        "scale": 1.0,
        "ref_line": None,
        "expander": {
            "what": "Disoccupazione USA: proxy crescita / ciclo.",
            "reference":  "Salite rapide spesso associano slowdown/recessione.",
            "interpretation": (
                "- **↑ veloce** → rischio recessionario (risk-off).\n"
                "- **Stabile** → contesto più benigno."
            ),
        },
    },

    # Financial Conditions & Liquidity
    "usd_index": {
        "label": "USD index (DXY / FRED proxy)",
        "unit": "",
        "direction": -1,
        "source": "yfinance DX-Y.NYB (fallback FRED DTWEXBGS)",
        "scale": 1.0,
        "ref_line": None,
        "expander": {
            "what": "Misura di forza del dollaro. Se DXY non è disponibile, usa proxy FRED broad dollar index.",
            "reference":  "USD forte = condizioni globali più strette (euristico).",
            "interpretation": (
                "- **USD ↑** → tightening globale / pressione su risk asset.\n"
                "- **USD ↓** → condizioni più accomodanti."
            ),
        },
    },
    "hy_oas": {
        "label": "US High Yield OAS",
        "unit": "pp",
        "direction": -1,
        "source": "FRED BAMLH0A0HYM2",
        "scale": 1.0,
        "ref_line": 4.5,  # euristico
        "expander": {
            "what": "Spread HY (OAS): stress creditizio e rischio default percepito.",
            "reference": "<4% spesso benigno; >6–7% stress (euristiche).",
            "interpretation": (
                "- **↑** → risk-off (credit stress).\n"
                "- **↓** → risk appetite."
            ),
        },
    },
    "fed_balance_sheet": {
        "label": "Fed balance sheet (WALCL)",
        "unit": "bn USD",
        "direction": +1,
        "source": "FRED WALCL (milioni -> bn)",
        "scale": 1.0 / 1000.0,
        "ref_line": None,
        "expander": {
            "what": "Totale attivi Fed: proxy liquidità sistemica.",
            "reference":  "Trend espansivo (QE) tende a supportare risk asset; QT tende a drenare.",
            "interpretation": (
                "- **↑** → più liquidità (tailwind).\n"
                "- **↓** → drenaggio (headwind)."
            ),
        },
    },
    "rrp": {
        "label": "Fed Overnight RRP",
        "unit": "bn USD",
        "direction": -1,
        "source": "FRED RRPONTSYD",
        "scale": 1.0,
        "ref_line": 0.0,
        "expander": {
            "what": "RRP: liquidità parcheggiata in facility risk-free.",
            "reference":  "RRP alto = liquidità 'ferma'; in calo = liquidità rilasciata.",
            "interpretation": (
                "- **RRP ↑** → meno benzina per risk asset.\n"
                "- **RRP ↓** → potenziale supporto a risk-on."
            ),
        },
    },

    # Risk Appetite & Stress
    "vix": {
        "label": "VIX",
        "unit": "",
        "direction": -1,
        "source": "yfinance ^VIX",
        "scale": 1.0,
        "ref_line": 20.0,
        "expander": {
            "what": "Volatilità implicita S&P 500.",
            "reference": "<15 basso; 15–25 normale; >25 stress (euristiche).",
            "interpretation": (
                "- **↑** → risk-off.\n"
                "- **↓** → risk-on."
            ),
        },
    },
    "spy_trend": {
        "label": "SPY trend (SPY / 200d MA)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance SPY",
        "scale": 1.0,
        "ref_line": 1.0,
        "expander": {
            "what": "Trend proxy: prezzo SPY vs media 200 giorni.",
            "reference": ">1 bull trend; <1 downtrend (euristiche).",
            "interpretation": (
                "- **>1** → supporto risk-on.\n"
                "- **<1** → risk-off."
            ),
        },
    },
    "hyg_lqd_ratio": {
        "label": "Credit risk appetite (HYG / LQD)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance HYG, LQD",
        "scale": 1.0,
        "ref_line": None,
        "expander": {
            "what": "HY vs IG: propensione al rischio credito.",
            "reference": "Ratio ↑ = più appetite HY; ratio ↓ = flight to quality.",
            "interpretation": (
                "- **↑** → risk-on.\n"
                "- **↓** → risk-off."
            ),
        },
    },

    # Cross-Asset Performance
    "world_equity": {
        "label": "Global equities (URTH)",
        "unit": "",
        "direction": +1,
        "source": "yfinance URTH",
        "scale": 1.0,
        "ref_line": None,
        "expander": {
            "what": "Equity globale: conferma regime non solo US.",
            "reference": "Trend e drawdown come conferma/smentita.",
            "interpretation": (
                "- **Trend ↑** → conferma risk-on.\n"
                "- **Trend ↓** → conferma risk-off."
            ),
        },
    },
    "duration_proxy_tlt": {
        "label": "Long duration (TLT)",
        "unit": "",
        "direction": -1,
        "source": "yfinance TLT",
        "scale": 1.0,
        "ref_line": None,
        "expander": {
            "what": "Treasury lunga duration (hedge tipico in risk-off).",
            "reference": "Rally TLT spesso coincide con flight-to-quality.",
            "interpretation": (
                "- **TLT ↑** → spesso risk-off / easing expectations.\n"
                "- **TLT ↓** con yields ↑ → headwind per duration."
            ),
        },
    },
    "gold": {
        "label": "Gold (GLD)",
        "unit": "",
        "direction": -1,
        "source": "yfinance GLD",
        "scale": 1.0,
        "ref_line": None,
        "expander": {
            "what": "Oro: hedge (inflazione/shock/sistemico).",
            "reference": "Breakout spesso segnala domanda di hedging.",
            "interpretation": (
                "- **Gold ↑** → domanda di hedge.\n"
                "- **Gold ↓** in bull equity → risk-on pulito."
            ),
        },
    },
}

BLOCKS = {
    "policy": {
        "name": "Policy & Real Rates",
        "weight": 0.25,
        "indicators": ["real_10y", "nominal_10y", "yield_curve_10_2"],
        "layout_rows": [["real_10y", "nominal_10y"], ["yield_curve_10_2"]],
        "desc": "Prezzo del tempo: tassi reali/nominali e forma della curva.",
    },
    "macro": {
        "name": "Inflation & Growth",
        "weight": 0.20,
        "indicators": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],
        "layout_rows": [["breakeven_10y", "cpi_yoy"], ["unemployment_rate"]],
        "desc": "Backdrop macro: disinflation vs reflation vs slowdown.",
    },
    "fincond": {
        "name": "Financial Conditions & Liquidity",
        "weight": 0.20,
        "indicators": ["usd_index", "hy_oas", "fed_balance_sheet", "rrp"],
        "layout_rows": [["usd_index", "hy_oas"], ["fed_balance_sheet", "rrp"]],
        "desc": "USD, spreads, e proxy liquidità.",
    },
    "risk": {
        "name": "Risk Appetite & Stress",
        "weight": 0.20,
        "indicators": ["vix", "spy_trend", "hyg_lqd_ratio"],
        "layout_rows": [["vix", "spy_trend"], ["hyg_lqd_ratio"]],
        "desc": "Volatilità, trend azionario, appetite per HY.",
    },
    "cross": {
        "name": "Cross-Asset Confirmation",
        "weight": 0.15,
        "indicators": ["world_equity", "duration_proxy_tlt", "gold"],
        "layout_rows": [["world_equity", "duration_proxy_tlt"], ["gold"]],
        "desc": "Conferme da equity globale, duration, oro.",
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
    """
    Fetch robusto per singolo ticker (evita problemi multi-ticker / multiindex).
    """
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
# SCORING
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


def compute_indicator_score(series: pd.Series, direction: int):
    """
    Returns: (score_0_100, z, latest)
    """
    if series is None or series.empty:
        return np.nan, np.nan, np.nan
    s = series.dropna()
    if len(s) < 20:
        return np.nan, np.nan, s.iloc[-1]

    end = s.index.max()
    start = end - DateOffset(years=5)
    hist = s[s.index >= start]
    if len(hist) < 10:
        hist = s

    mean = hist.mean()
    std = hist.std()
    latest = s.iloc[-1]
    z = 0.0 if (std is None or std == 0 or np.isnan(std)) else (latest - mean) / std

    raw = direction * z
    raw = float(np.clip(raw, -2.0, 2.0))
    score = (raw + 2.0) / 4.0 * 100.0
    return score, z, latest


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
        return "<span class='pill warn'>🟡 Neutrale</span>"
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
# PLOTTING (PREMIUM)
# =========================

def plot_premium(series: pd.Series, title: str, ref_line=None):
    s = series.dropna()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=s.index,
            y=s.values,
            mode="lines",
            line=dict(width=2),
            name=title,
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
        height=290,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
        ),
        showlegend=False,
        font=dict(color="rgba(255,255,255,0.85)"),
    )
    return fig


def render_tile(key: str, series: pd.Series, indicator_scores: dict):
    meta = INDICATOR_META[key]
    s_info = indicator_scores.get(key, {})
    score = s_info.get("score", np.nan)
    status = s_info.get("status", "n/a")
    latest = s_info.get("latest", np.nan)

    d7 = pct_change_over_days(series, 7)
    d30 = pct_change_over_days(series, 30)
    d1y = pct_change_over_days(series, 365)

    score_txt = "n/a" if np.isnan(score) else f"{score:.1f}"
    latest_txt = fmt_value(latest, meta["unit"], meta.get("scale", 1.0))

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='tile-toprow'>
          <div>
            <div class='tile-title'>{meta["label"]}</div>
            <div class='tile-meta'>Fonte: {meta["source"]}</div>
          </div>
          <div style='text-align:right'>
            <div><span class='pill'>Ultimo: {latest_txt}</span>{status_pill_html(status)}</div>
            <div class='tiny'>Score: {score_txt} · Δ30d: {("n/a" if np.isnan(d30) else f"{d30:+.1f}%")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("Definizione & guida alla lettura", expanded=False):
        exp = meta["expander"]
        st.markdown(f"**Che metrica è**: {exp['what']}")
        st.markdown(f"**Valori di riferimento**: {exp['reference']}")
        st.markdown("**Interpretazione bidirezionale**:")
        st.markdown(exp["interpretation"])
        st.markdown(
            f"**What changed**: "
            f"{'n/a' if np.isnan(d7) else f'{d7:+.1f}%'} (7d), "
            f"{'n/a' if np.isnan(d30) else f'{d30:+.1f}%'} (30d), "
            f"{'n/a' if np.isnan(d1y) else f'{d1y:+.1f}%'} (1Y)"
        )

    fig = plot_premium(series, meta["label"], ref_line=meta.get("ref_line", None))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# MAIN
# =========================

def main():
    st.title("Global finance | Macro overview")
    st.markdown(
        "<div class='muted'>Macro-first dashboard per leggere regime globale e tradurlo in decisioni ETF-based su equity, duration, credito, hedges.</div>",
        unsafe_allow_html=True
    )

    # Sidebar controls
    st.sidebar.header("Impostazioni")
    if st.sidebar.button("🔄 Refresh data (clear cache)"):
        st.cache_data.clear()
        st.rerun()

    years_back = st.sidebar.slider("Orizzonte storico (anni)", 5, 20, 10)
    today = datetime.now(timezone.utc).date()
    start_date = (today - DateOffset(years=years_back)).date().isoformat()
    st.sidebar.markdown(f"**Data start:** {start_date}")

    fred_key = get_fred_api_key()
    if fred_key is None:
        st.sidebar.error("⚠️ Manca `FRED_API_KEY` nei secrets.")

    # Fetch data
    with st.spinner("Caricamento dati (FRED + yfinance)..."):
        # --- FRED
        fred = {
            "real_10y": fetch_fred_series("DFII10", start_date),
            "nominal_10y": fetch_fred_series("DGS10", start_date),
            "dgs2": fetch_fred_series("DGS2", start_date),
            "breakeven_10y": fetch_fred_series("T10YIE", start_date),
            "cpi_index": fetch_fred_series("CPIAUCSL", start_date),
            "unemployment_rate": fetch_fred_series("UNRATE", start_date),
            "hy_oas": fetch_fred_series("BAMLH0A0HYM2", start_date),
            "fed_balance_sheet": fetch_fred_series("WALCL", start_date),
            "rrp": fetch_fred_series("RRPONTSYD", start_date),

            # USD proxy from FRED (broad trade-weighted dollar index)
            # This is the “fixable” part: even if yfinance DXY flakes, this always renders.
            "usd_fred": fetch_fred_series("DTWEXBGS", start_date),
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

        # Direct FRED indicators
        indicators["real_10y"] = fred["real_10y"]
        indicators["nominal_10y"] = fred["nominal_10y"]
        indicators["breakeven_10y"] = fred["breakeven_10y"]
        indicators["unemployment_rate"] = fred["unemployment_rate"]
        indicators["hy_oas"] = fred["hy_oas"]
        indicators["fed_balance_sheet"] = fred["fed_balance_sheet"]
        indicators["rrp"] = fred["rrp"]

        # --- YFINANCE (robust per-ticker)
        yf_map = fetch_yf_many(
            ["DX-Y.NYB", "^VIX", "SPY", "HYG", "LQD", "URTH", "TLT", "GLD"],
            start_date
        )

        # USD index: try DXY from yfinance, else fallback to FRED DTWEXBGS
        dxy = yf_map.get("DX-Y.NYB", pd.Series(dtype=float))
        if dxy is None or dxy.empty:
            dxy = fred["usd_fred"]
        indicators["usd_index"] = dxy

        indicators["vix"] = yf_map.get("^VIX", pd.Series(dtype=float))

        # SPY trend
        spy = yf_map.get("SPY", pd.Series(dtype=float))
        if spy is not None and not spy.empty:
            ma200 = spy.rolling(200).mean()
            indicators["spy_trend"] = (spy / ma200).dropna()
        else:
            indicators["spy_trend"] = pd.Series(dtype=float)

        # HYG / LQD
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
        score, z, latest = compute_indicator_score(series, meta["direction"])
        indicator_scores[key] = {"score": score, "z": z, "latest": latest, "status": classify_status(score)}

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
        if vals:
            bscore = float(np.mean(vals))
            block_scores[bkey] = {"score": bscore, "status": classify_status(bscore)}
            global_score += bscore * binfo["weight"]
            w_used += binfo["weight"]
        else:
            block_scores[bkey] = {"score": np.nan, "status": "n/a"}
    global_score = (global_score / w_used) if w_used > 0 else np.nan
    global_status = classify_status(global_score)

    # Data freshness
    latest_points = []
    for k, s in indicators.items():
        if s is not None and not s.empty:
            latest_points.append(s.index.max())
    data_max_date = max(latest_points) if latest_points else None

    # =========================
    # TABS (reduce scroll)
    # =========================
    tabs = st.tabs(["Overview", "Policy", "Macro", "Conditions", "Risk", "Cross", "What changed", "Report"])

    # -------------------------
    # Overview
    # -------------------------
    with tabs[0]:
        left, right = st.columns([2, 1])
        with left:
            st.markdown("### Executive snapshot")
            gs_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
            st.markdown(
                f"""
                <div class="kpi-grid">
                  <div class="kpi-card">
                    <div class="kpi-title">Regime score (0–100)</div>
                    <div class="kpi-value">{gs_txt}</div>
                    <div class="kpi-sub">{status_pill_html(global_status)}</div>
                  </div>
                  <div class="kpi-card">
                    <div class="kpi-title">Blocchi (score)</div>
                    <div class="kpi-sub">
                      {status_pill_html(block_scores["policy"]["status"])} Policy: <b>{("n/a" if np.isnan(block_scores["policy"]["score"]) else f"{block_scores['policy']['score']:.1f}")}</b><br/>
                      {status_pill_html(block_scores["macro"]["status"])} Macro: <b>{("n/a" if np.isnan(block_scores["macro"]["score"]) else f"{block_scores['macro']['score']:.1f}")}</b><br/>
                      {status_pill_html(block_scores["fincond"]["status"])} Conditions: <b>{("n/a" if np.isnan(block_scores["fincond"]["score"]) else f"{block_scores['fincond']['score']:.1f}")}</b><br/>
                      {status_pill_html(block_scores["risk"]["status"])} Risk: <b>{("n/a" if np.isnan(block_scores["risk"]["score"]) else f"{block_scores['risk']['score']:.1f}")}</b><br/>
                      {status_pill_html(block_scores["cross"]["status"])} Cross: <b>{("n/a" if np.isnan(block_scores["cross"]["score"]) else f"{block_scores['cross']['score']:.1f}")}</b>
                    </div>
                  </div>
                  <div class="kpi-card">
                    <div class="kpi-title">Interpretazione operativa (heuristic)</div>
                    <div class="kpi-sub">
                      🟢 Risk-on: ↑ equity risk budget · duration neutrale/leggera · ↑ credito (HY) con controllo rischio<br/>
                      🟡 Neutrale: sizing moderato · qualità · hedges medi<br/>
                      🔴 Risk-off: ↓ equity · ↑ duration qualità · ↓ HY · ↑ hedges (cash/gold/USD)
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
                f"<div class='tiny'>Latest datapoint: <b>{('n/a' if data_max_date is None else str(data_max_date.date()))}</b></div>",
                unsafe_allow_html=True
            )
            st.markdown("<div class='tiny'>Tip: usa <b>Refresh data</b> in sidebar per forzare update.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("Come leggere score & soglie", expanded=False):
                st.markdown(
                    """
- Ogni indicatore → **z-score** su finestra ~5Y, con segno coerente (risk-on / risk-off), clamp [-2, +2] → mappato 0–100.
- Soglie: **>60 Risk-on**, **40–60 Neutrale**, **<40 Risk-off** (euristiche).
- Global score = media ponderata dei blocchi.
- Le soglie non sono “accademiche”: servono per avere una lettura coerente e comparabile nel tempo.
                    """
                )

            # Quick DXY debug hint (non intrusivo)
            usd_series = indicators.get("usd_index", pd.Series(dtype=float))
            if usd_series is None or usd_series.empty:
                st.warning("USD index vuoto: né DXY (yfinance) né proxy FRED risultano disponibili.")
            else:
                st.caption("USD index: se DXY manca su yfinance, la dashboard usa FRED DTWEXBGS come proxy (sempre disponibile).")

    # -------------------------
    # Block render helper
    # -------------------------
    def render_block(block_key: str):
        b = BLOCKS[block_key]
        st.markdown(f"### {b['name']}")
        st.markdown(f"<div class='muted'>{b['desc']}</div>", unsafe_allow_html=True)

        bscore = block_scores[block_key]["score"]
        bstatus = block_scores[block_key]["status"]
        bscore_txt = "n/a" if np.isnan(bscore) else f"{bscore:.1f}"
        st.markdown(
            f"<div class='section-card'><div class='tiny'>Block score: <b>{bscore_txt}</b> {status_pill_html(bstatus)}</div></div>",
            unsafe_allow_html=True
        )

        for row in b["layout_rows"]:
            if len(row) == 2:
                c1, c2 = st.columns(2)
                for col, key in zip([c1, c2], row):
                    with col:
                        s = indicators.get(key, pd.Series(dtype=float))
                        if s is None or s.empty:
                            st.warning(f"Dati mancanti per {INDICATOR_META[key]['label']}.")
                        else:
                            render_tile(key, s, indicator_scores)
            elif len(row) == 1:
                key = row[0]
                s = indicators.get(key, pd.Series(dtype=float))
                if s is None or s.empty:
                    st.warning(f"Dati mancanti per {INDICATOR_META[key]['label']}.")
                else:
                    render_tile(key, s, indicator_scores)

    # -------------------------
    # Tabs: blocks
    # -------------------------
    with tabs[1]:
        render_block("policy")
    with tabs[2]:
        render_block("macro")
    with tabs[3]:
        render_block("fincond")
    with tabs[4]:
        render_block("risk")
    with tabs[5]:
        render_block("cross")

    # -------------------------
    # What changed
    # -------------------------
    with tabs[6]:
        st.markdown("### What changed – Δ 7d / 30d / 1Y")
        rows = []
        for key, meta in INDICATOR_META.items():
            s = indicators.get(key, pd.Series(dtype=float))
            if s is None or s.empty:
                continue
            rows.append(
                {
                    "Indicatore": meta["label"],
                    "Δ 7d %": None if np.isnan(pct_change_over_days(s, 7)) else round(pct_change_over_days(s, 7), 2),
                    "Δ 30d %": None if np.isnan(pct_change_over_days(s, 30)) else round(pct_change_over_days(s, 30), 2),
                    "Δ 1Y %": None if np.isnan(pct_change_over_days(s, 365)) else round(pct_change_over_days(s, 365), 2),
                    "Score": None if np.isnan(indicator_scores[key]["score"]) else round(indicator_scores[key]["score"], 1),
                    "Regime": indicator_scores[key]["status"],
                }
            )
        if rows:
            df = pd.DataFrame(rows).set_index("Indicatore")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nessun dato sufficiente per calcolare variazioni.")

    # -------------------------
    # Report
    # -------------------------
    with tabs[7]:
        st.markdown("### Report (opzionale) – Payload per ChatGPT")
        st.markdown("<div class='muted'>Genera un payload copiabile per trasformare segnali macro in implicazioni operative ETF-based.</div>", unsafe_allow_html=True)

        generate_payload = st.button("Generate payload")

        if generate_payload:
            payload_lines = []
            payload_lines.append("macro_regime_payload:")
            payload_lines.append(f"  generated_at_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            payload_lines.append(f"  global_score: {0.0 if np.isnan(global_score) else round(global_score, 1)}")
            payload_lines.append(f"  global_status: {global_status}")

            payload_lines.append("  blocks:")
            for bkey, binfo in BLOCKS.items():
                bscore = block_scores[bkey]["score"]
                bstatus = block_scores[bkey]["status"]
                payload_lines.append(f"    - name: \"{binfo['name']}\"")
                payload_lines.append(f"      score: {0.0 if np.isnan(bscore) else round(bscore, 1)}")
                payload_lines.append(f"      status: {bstatus}")

            payload_lines.append("  indicators:")
            for key, meta in INDICATOR_META.items():
                s_info = indicator_scores.get(key, {})
                score = s_info.get("score", np.nan)
                status = s_info.get("status", "n/a")
                latest = s_info.get("latest", np.nan)
                series = indicators.get(key, pd.Series(dtype=float))
                d30 = pct_change_over_days(series, 30)

                payload_lines.append(f"    - name: \"{meta['label']}\"")
                payload_lines.append(f"      key: \"{key}\"")
                payload_lines.append(f"      latest_value: \"{fmt_value(latest, meta['unit'], meta.get('scale', 1.0))}\"")
                payload_lines.append(f"      score: {0.0 if np.isnan(score) else round(score, 1)}")
                payload_lines.append(f"      status: {status}")
                payload_lines.append(f"      delta_30d_pct: {0.0 if np.isnan(d30) else round(d30, 2)}")

            payload_text = "\n".join(payload_lines)
            st.code(payload_text, language="yaml")

            st.markdown("**Prompt suggerito:**")
            st.code(
                """
Sei un macro strategist multi-asset. Ricevi il payload YAML sopra (dashboard macro-finanziaria).

Task:
1) Ricostruisci il regime (Risk-on/Neutral/Risk-off) spiegando driver chiave (real rates, inflazione, curva, USD, credito, vol, equity, duration, oro) e coerenza/divergenze tra blocchi.
2) Produci un report operativo ETF-based:
   - Equity exposure (come cambiare risk budget)
   - Duration (corta/media/lunga)
   - Credit risk (IG vs HY)
   - Hedges (USD, gold, cash-like)
   - 3–5 segnali da monitorare nelle prossime 2–4 settimane con soglie indicative
Tono concreto, implementabile, prudente. Soglie euristiche.
                """.strip(),
                language="markdown"
            )


if __name__ == "__main__":
    main()

