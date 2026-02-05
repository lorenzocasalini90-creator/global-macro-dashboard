import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
from pandas.tseries.offsets import DateOffset


# -------------- CONFIG DI BASE --------------

st.set_page_config(
    page_title="Global finance | Macro overview",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS minimale per look "premium" sobrio + card per charts
st.markdown(
    """
    <style>
    .big-number {
        font-size: 2.2rem;
        font-weight: 650;
        line-height: 1.05;
    }
    .sub-number {
        font-size: 1.0rem;
        color: #666;
    }
    .kpi-card {
        padding: 1rem 1.2rem;
        border-radius: 0.9rem;
        border: 1px solid #dedede;
        background-color: #fbfbfb;
        margin-bottom: 1rem;
        box-shadow: 0 1px 0 rgba(0,0,0,0.02);
    }
    .chart-card {
        padding: 0.9rem 1.0rem;
        border-radius: 0.9rem;
        border: 1px solid #e3e3e3;
        background-color: #ffffff;
        margin: 0.5rem 0 1rem 0;
        box-shadow: 0 1px 0 rgba(0,0,0,0.02);
    }
    .section-separator {
        border-top: 1px solid #e6e6e6;
        margin: 1.25rem 0 1rem 0;
    }
    .tiny-muted {
        color: #777;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------- METADATA INDICATORI --------------

INDICATOR_META = {
    # Policy & Real Rates
    "real_10y": {
        "label": "US 10Y TIPS real yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DFII10",
        "scale": 1.0,
        "zero_line": True,
        "expander": {
            "what": "Rendimento reale (al netto dell'inflazione attesa) sui Treasury USA a 10 anni (TIPS).",
            "reference": "Area <0% = condizioni molto accomodanti; 0–2% = zona neutrale; >2% = condizioni restrittive.",
            "interpretation": (
                "- In **rialzo** su livelli alti → freno per equity (soprattutto growth) e duration lunga.\n"
                "- In **calo** o su livelli bassi → tailwind per risk asset e bond long duration."
            ),
        },
    },
    "nominal_10y": {
        "label": "US 10Y nominal yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DGS10",
        "scale": 1.0,
        "zero_line": False,
        "expander": {
            "what": "Rendimento nominale sui Treasury USA a 10 anni.",
            "reference": "Tipicamente 2–4% in fasi 'normali'; spike rapidi verso l'alto spesso associati a shock di policy / inflazione.",
            "interpretation": (
                "- **Rialzo rapido** → repricing del costo del capitale, pressione su equity e su bond esistenti.\n"
                "- **Discesa** → spesso associata a easing / flight to quality (dipende dal contesto macro)."
            ),
        },
    },
    "yield_curve_10_2": {
        "label": "US Yield curve 10Y–2Y",
        "unit": "pp",
        "direction": +1,
        "source": "DGS10 - DGS2",
        "scale": 1.0,
        "zero_line": True,
        "expander": {
            "what": "Differenza tra rendimento Treasury 10Y e 2Y (curva dei rendimenti).",
            "reference": "Spread >0: curva 'normale'; spread <0: curva invertita, spesso segnale di recessione futura.",
            "interpretation": (
                "- Spread **molto negativo** e persistente → fase late-cycle / pre-recessione (risk-off).\n"
                "- Spread **positivo e in aumento** → normalizzazione del ciclo, contesto più favorevole a risk asset."
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
        "zero_line": False,
        "expander": {
            "what": "Inflazione media attesa dal mercato per i prossimi 10 anni, derivata da nominali vs TIPS.",
            "reference": "Circa 2–3% = inflazione 'ben ancorata'; >>3% = rischio inflazione elevata/persistente.",
            "interpretation": (
                "- Valori **elevati e in aumento** → rischio di policy restrittiva prolungata.\n"
                "- Valori **in calo verso il target** → scenario di disinflazione, supportive per duration e equity."
            ),
        },
    },
    "cpi_yoy": {
        "label": "US CPI YoY",
        "unit": "%",
        "direction": -1,
        "source": "FRED CPIAUCSL (YoY)",
        "scale": 1.0,
        "zero_line": False,
        "expander": {
            "what": "Inflazione headline USA anno su anno.",
            "reference": "2% target Fed; valori >3–4% per lungo tempo indicano inflazione 'sticky'.",
            "interpretation": (
                "- CPI **in rallentamento** → disinflazione, margine per allentare le condizioni finanziarie.\n"
                "- CPI **in riaccelerazione** → rischio di rialzi/rinvii nei tagli di tasso, scenario meno favorevole a risk asset."
            ),
        },
    },
    "unemployment_rate": {
        "label": "US Unemployment rate",
        "unit": "%",
        "direction": -1,
        "source": "FRED UNRATE",
        "scale": 1.0,
        "zero_line": False,
        "expander": {
            "what": "Tasso di disoccupazione USA.",
            "reference": "Minimi storici ~3–4%; aumenti rapidi spesso precedono/seguono recessioni.",
            "interpretation": (
                "- Disoccupazione **ai minimi ma stabile** → mercato del lavoro forte.\n"
                "- Disoccupazione **in forte crescita** → segnale di slowdown / recessione → ambiente più risk-off."
            ),
        },
    },

    # Financial Conditions & Liquidity
    "dxy": {
        "label": "USD (DXY / UUP proxy)",
        "unit": "",
        "direction": -1,
        "source": "yfinance DX-Y.NYB (fallback: UUP)",
        "scale": 1.0,
        "zero_line": False,
        "expander": {
            "what": "Indice del dollaro USA (o proxy ETF UUP se DXY non disponibile) come misura di tightness globale.",
            "reference": "USD forte e persistente spesso coincide con fasi di tightening/stress globale.",
            "interpretation": (
                "- USD **forte e in apprezzamento** → condizioni più dure per EM/commodities, spesso risk-off.\n"
                "- USD **debole** → condizioni più accomodanti e supporto ai risk asset globali."
            ),
        },
    },
    "hy_oas": {
        "label": "US HY credit spread (OAS)",
        "unit": "pp",
        "direction": -1,
        "source": "FRED BAMLH0A0HYM2",
        "scale": 1.0,
        "zero_line": False,
        "expander": {
            "what": "Spread opzionale aggiustato dei corporate bond High Yield USA vs Treasury.",
            "reference": "Spread bassi (es. <400 bps) = risk appetite; spike sopra 600–700 bps = stress significativo.",
            "interpretation": (
                "- Spread **in allargamento** → mercato che prezza maggior rischio default → risk-off.\n"
                "- Spread **in compressione** → appetite per credito HY."
            ),
        },
    },
    "fed_balance_sheet": {
        "label": "Fed balance sheet (WALCL)",
        "unit": "bn USD",
        "direction": +1,
        "source": "FRED WALCL",
        "scale": 1.0 / 1000.0,  # milioni -> bn
        "zero_line": False,
        "expander": {
            "what": "Totale attivi della Fed (dimensione del bilancio).",
            "reference": "Trend di espansione (QE) tende a supportare la liquidità; contrazione (QT) tende a drenarla.",
            "interpretation": (
                "- Bilancio **in espansione** → più liquidità nel sistema, supporto ai risk asset.\n"
                "- Bilancio **in contrazione rapida** → vento contrario per equity/credit."
            ),
        },
    },
    "rrp": {
        "label": "Fed Overnight RRP usage",
        "unit": "bn USD",
        "direction": -1,
        "source": "FRED RRPONTSYD",
        "scale": 1.0,  # già bn
        "zero_line": True,
        "expander": {
            "what": "Reverse Repo overnight: liquidità parcheggiata in strumenti risk-free.",
            "reference": "RRP alto = liquidità 'ferma'; RRP in calo = liquidità che torna verso il mercato.",
            "interpretation": (
                "- RRP **elevato** → meno benzina per risk asset.\n"
                "- RRP **in calo** → potenziale supporto a risk-on."
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
        "zero_line": False,
        "expander": {
            "what": "Volatilità implicita a 30 giorni sull'S&P 500.",
            "reference": "VIX <15 basso; 15–25 normale; >25–30 stress; >40 panic.",
            "interpretation": (
                "- VIX **basso/stabile** → risk-on.\n"
                "- VIX **alto/spiking** → risk-off."
            ),
        },
    },
    "spy_trend": {
        "label": "SPY / 200d MA (trend)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance SPY",
        "scale": 1.0,
        "zero_line": True,  # linea 1.0
        "expander": {
            "what": "Rapporto tra SPY e media mobile 200 giorni (trend di lungo periodo).",
            "reference": "Ratio >1 = trend rialzista; <1 = trend ribassista.",
            "interpretation": (
                "- Ratio **>1** → bull trend.\n"
                "- Ratio **<1** → downtrend / risk-off."
            ),
        },
    },
    "hyg_lqd_ratio": {
        "label": "HYG / LQD (HY vs IG)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance HYG, LQD",
        "scale": 1.0,
        "zero_line": False,
        "expander": {
            "what": "Rapporto HY vs IG: misura la propensione al rischio di credito.",
            "reference": "Ratio in salita = appetite per HY; in calo = fuga verso qualità.",
            "interpretation": (
                "- Ratio **in salita** → risk-on.\n"
                "- Ratio **in discesa** → risk-off."
            ),
        },
    },

    # Cross-Asset Performance
    "world_equity": {
        "label": "World equity (URTH)",
        "unit": "",
        "direction": +1,
        "source": "yfinance URTH",
        "scale": 1.0,
        "zero_line": False,
        "expander": {
            "what": "ETF MSCI World: proxy del risk-on globale.",
            "reference": "Trend e drawdown aiutano a capire se il risk-on è davvero globale.",
            "interpretation": (
                "- Uptrend → conferma risk-on.\n"
                "- Downtrend → conferma risk-off."
            ),
        },
    },
    "duration_proxy_tlt": {
        "label": "Long duration (TLT)",
        "unit": "",
        "direction": -1,
        "source": "yfinance TLT",
        "scale": 1.0,
        "zero_line": False,
        "expander": {
            "what": "Treasury USA lunga duration: hedge tipico in risk-off.",
            "reference": "Rally TLT spesso coincide con flight-to-quality.",
            "interpretation": (
                "- TLT **in rally** → spesso contesto risk-off (ma bene per chi hedgia duration).\n"
                "- TLT **debole** con tassi in salita → attenzione a duration e equity long-duration."
            ),
        },
    },
    "gold": {
        "label": "Gold (GLD)",
        "unit": "",
        "direction": -1,
        "source": "yfinance GLD",
        "scale": 1.0,
        "zero_line": False,
        "expander": {
            "what": "Oro: hedge contro inflazione / shock / rischio sistemico.",
            "reference": "Breakout spesso associato a aumento incertezza macro/geopolitica/monetaria.",
            "interpretation": (
                "- Oro **forte** → domanda di hedge.\n"
                "- Oro **debole** in bull equity → regime più risk-on 'pulito'."
            ),
        },
    },
}


BLOCKS = {
    "policy": {
        "name": "1) Policy & Real Rates",
        "weight": 0.25,
        "indicators": ["real_10y", "nominal_10y", "yield_curve_10_2"],
        "layout_rows": [["real_10y", "nominal_10y"], ["yield_curve_10_2"]],
        "description": "Tassi reali/nominali e curva: misura quanto il 'prezzo del tempo' è favorevole o ostile ai risk asset.",
    },
    "macro": {
        "name": "2) Inflazione & Crescita",
        "weight": 0.20,
        "indicators": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],
        "layout_rows": [["breakeven_10y", "cpi_yoy"], ["unemployment_rate"]],
        "description": "Backdrop macro: disinflation vs reflation vs stagflation/slowdown.",
    },
    "fincond": {
        "name": "3) Financial Conditions & Liquidity",
        "weight": 0.20,
        "indicators": ["dxy", "hy_oas", "fed_balance_sheet", "rrp"],
        "layout_rows": [["dxy", "hy_oas"], ["fed_balance_sheet", "rrp"]],
        "description": "Condizioni finanziarie, credito e proxy liquidità USD.",
    },
    "risk": {
        "name": "4) Risk Appetite & Stress",
        "weight": 0.20,
        "indicators": ["vix", "spy_trend", "hyg_lqd_ratio"],
        "layout_rows": [["vix", "spy_trend"], ["hyg_lqd_ratio"]],
        "description": "Volatilità, trend equity e rischio credito (HY vs IG).",
    },
    "cross": {
        "name": "5) Cross-Asset Confirmation",
        "weight": 0.15,
        "indicators": ["world_equity", "duration_proxy_tlt", "gold"],
        "layout_rows": [["world_equity", "duration_proxy_tlt"], ["gold"]],
        "description": "Conferme da equity globale, duration e hedge (oro).",
    },
}


# -------------- HELPER FUNCTIONS --------------

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
        dates = [obs["date"] for obs in data]
        values = []
        for obs in data:
            v = obs["value"]
            try:
                v_float = float(v)
            except Exception:
                v_float = np.nan
            values.append(v_float)
        s = pd.Series(values, index=pd.to_datetime(dates))
        s = s.replace({".": np.nan}).astype(float)
        return s.sort_index()
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600)
def fetch_yf_series(tickers, start_date: str) -> dict:
    if isinstance(tickers, str):
        tickers = [tickers]
    out = {}
    try:
        data = yf.download(
            tickers,
            start=start_date,
            auto_adjust=True,
            progress=False,
        )
        px = None
        if isinstance(data.columns, pd.MultiIndex):
            if "Adj Close" in data.columns.get_level_values(0):
                px = data["Adj Close"]
            elif "Close" in data.columns.get_level_values(0):
                px = data["Close"]
            else:
                px = data.xs(data.columns.get_level_values(0)[0], axis=1, level=0)
        else:
            if "Adj Close" in data.columns:
                px = data["Adj Close"]
            elif "Close" in data.columns:
                px = data["Close"]
            else:
                px = data

        if isinstance(px, pd.Series):
            out[tickers[0]] = px.dropna()
        else:
            for t in tickers:
                if t in px.columns:
                    out[t] = px[t].dropna()
    except Exception:
        for t in tickers:
            try:
                df = yf.download(t, start=start_date, auto_adjust=True, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    if "Adj Close" in df.columns.get_level_values(0):
                        s = df["Adj Close"]
                        out[t] = s if isinstance(s, pd.Series) else s.iloc[:, 0]
                    elif "Close" in df.columns.get_level_values(0):
                        s = df["Close"]
                        out[t] = s if isinstance(s, pd.Series) else s.iloc[:, 0]
                    else:
                        out[t] = df.iloc[:, 0].dropna()
                else:
                    if "Adj Close" in df.columns:
                        out[t] = df["Adj Close"].dropna()
                    elif "Close" in df.columns:
                        out[t] = df["Close"].dropna()
                    else:
                        out[t] = df.iloc[:, 0].dropna()
            except Exception:
                out[t] = pd.Series(dtype=float)
    return out


def pct_change_over_days(series: pd.Series, days: int) -> float:
    if series is None or series.empty:
        return np.nan
    s = series.dropna()
    if s.empty:
        return np.nan
    last_date = s.index.max()
    target_date = last_date - timedelta(days=days)
    past_slice = s[s.index <= target_date]
    if past_slice.empty:
        return np.nan
    past_val = past_slice.iloc[-1]
    curr_val = s.iloc[-1]
    if pd.isna(past_val) or pd.isna(curr_val) or past_val == 0:
        return np.nan
    return (curr_val / past_val - 1.0) * 100.0


def compute_indicator_score(series: pd.Series, direction: int):
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

    if std is None or std == 0 or np.isnan(std):
        z = 0.0
    else:
        z = (latest - mean) / std

    raw = direction * z
    raw = max(-2.0, min(2.0, raw))
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


def status_emoji(status: str) -> str:
    return {"risk_on": "🟢", "neutral": "🟡", "risk_off": "🔴"}.get(status, "⚪️")


def status_label_it(status: str) -> str:
    return {"risk_on": "Risk-on", "neutral": "Neutrale", "risk_off": "Risk-off"}.get(status, "N/A")


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


def score_to_badge(score: float) -> str:
    s = classify_status(score)
    return f"{status_emoji(s)} {status_label_it(s)}"


def render_indicator_tile(key: str, series: pd.Series, indicator_scores: dict):
    meta = INDICATOR_META[key]
    score_info = indicator_scores.get(key, {})
    score = score_info.get("score", np.nan)
    status = score_info.get("status", "n/a")
    latest = score_info.get("latest", np.nan)

    delta_7d = pct_change_over_days(series, 7)
    delta_30d = pct_change_over_days(series, 30)
    delta_1y = pct_change_over_days(series, 365)

    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)

    top_left, top_right = st.columns([3, 2])
    with top_left:
        st.markdown(f"**{meta['label']}**")
        st.markdown(f"<div class='tiny-muted'>Fonte: {meta['source']}</div>", unsafe_allow_html=True)
    with top_right:
        score_txt = "n/a" if np.isnan(score) else f"{score:.1f}"
        latest_txt = fmt_value(latest, meta["unit"], meta.get("scale", 1.0))
        st.markdown(f"**Ultimo**: {latest_txt}")
        st.markdown(f"**Score**: {score_txt} ({score_to_badge(score)})")

    with st.expander("Definizione & guida alla lettura", expanded=False):
        exp = meta["expander"]
        st.markdown(f"**Che metrica è**: {exp['what']}")
        st.markdown(f"**Valori di riferimento**: {exp['reference']}")
        st.markdown("**Interpretazione bidirezionale**:")
        st.markdown(exp["interpretation"])
        st.markdown(
            f"**What changed**: "
            f"{'n/a' if np.isnan(delta_7d) else f'{delta_7d:+.1f}%'} (7d), "
            f"{'n/a' if np.isnan(delta_30d) else f'{delta_30d:+.1f}%'} (30d), "
            f"{'n/a' if np.isnan(delta_1y) else f'{delta_1y:+.1f}%'} (1Y)"
        )

    # Chart
    st.line_chart(series)

    # Quick reference for zero-line metrics (solo testo, per non complicare chart)
    if meta.get("zero_line", False):
        st.caption("Nota: metrica con **linea di riferimento** (es. 0 o 1.0) utile per interpretare regime.")

    st.markdown("</div>", unsafe_allow_html=True)


# -------------- MAIN DASHBOARD --------------

def main():
    st.title("Global finance | Macro overview")
    st.write(
        "Dashboard macro–finanziaria **global multi-asset** per leggere il regime di mercato e tradurlo in decisioni operative "
        "su **equity exposure**, **duration**, **credit risk** e **hedging**."
    )

    # ---- Sidebar ----
    st.sidebar.header("Impostazioni")

    if st.sidebar.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

    years_back = st.sidebar.slider(
        "Orizzonte storico (anni)",
        min_value=5,
        max_value=20,
        value=10,
        help="Orizzonte per i grafici e per la stima dei regimi (z-score).",
    )

    today = datetime.today().date()
    start_date = (today - DateOffset(years=years_back)).date().isoformat()

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data start:** " + start_date)

    fred_key = get_fred_api_key()
    if fred_key is None:
        st.sidebar.error("⚠️ Inserisci `FRED_API_KEY` in `st.secrets` per abilitare i dati macro (FRED).")

    # ---- Fetch dati con spinner ----
    with st.spinner("Caricamento dati (FRED + yfinance)..."):
        fred_series_ids = {
            "real_10y": "DFII10",
            "nominal_10y": "DGS10",
            "dgs2": "DGS2",
            "breakeven_10y": "T10YIE",
            "cpi_index": "CPIAUCSL",
            "unemployment_rate": "UNRATE",
            "hy_oas": "BAMLH0A0HYM2",
            "fed_balance_sheet": "WALCL",
            "rrp": "RRPONTSYD",
        }
        fred_data = {k: fetch_fred_series(v, start_date) for k, v in fred_series_ids.items()}

        indicators = {}
        indicators["real_10y"] = fred_data["real_10y"]
        indicators["nominal_10y"] = fred_data["nominal_10y"]

        if not fred_data["nominal_10y"].empty and not fred_data["dgs2"].empty:
            yc = fred_data["nominal_10y"].to_frame("10y").join(
                fred_data["dgs2"].to_frame("2y"), how="inner"
            )
            indicators["yield_curve_10_2"] = (yc["10y"] - yc["2y"]).dropna()
        else:
            indicators["yield_curve_10_2"] = pd.Series(dtype=float)

        cpi_index = fred_data["cpi_index"]
        indicators["cpi_yoy"] = (cpi_index.pct_change(12) * 100.0).dropna() if not cpi_index.empty else pd.Series(dtype=float)
        indicators["breakeven_10y"] = fred_data["breakeven_10y"]
        indicators["unemployment_rate"] = fred_data["unemployment_rate"]

        indicators["hy_oas"] = fred_data["hy_oas"]
        indicators["fed_balance_sheet"] = fred_data["fed_balance_sheet"]
        indicators["rrp"] = fred_data["rrp"]

        yf_tickers = ["DX-Y.NYB", "UUP", "^VIX", "SPY", "HYG", "LQD", "URTH", "TLT", "GLD"]
        yf_data = fetch_yf_series(yf_tickers, start_date)

        # DXY with fallback
        dxy_series = yf_data.get("DX-Y.NYB", pd.Series(dtype=float))
        if dxy_series is None or dxy_series.empty:
            dxy_series = yf_data.get("UUP", pd.Series(dtype=float))
        indicators["dxy"] = dxy_series

        indicators["vix"] = yf_data.get("^VIX", pd.Series(dtype=float))

        spy_series = yf_data.get("SPY", pd.Series(dtype=float))
        if not spy_series.empty:
            ma200 = spy_series.rolling(200).mean()
            indicators["spy_trend"] = (spy_series / ma200).dropna()
        else:
            indicators["spy_trend"] = pd.Series(dtype=float)

        hyg = yf_data.get("HYG", pd.Series(dtype=float))
        lqd = yf_data.get("LQD", pd.Series(dtype=float))
        if not hyg.empty and not lqd.empty:
            joined = hyg.to_frame("HYG").join(lqd.to_frame("LQD"), how="inner").dropna()
            indicators["hyg_lqd_ratio"] = (joined["HYG"] / joined["LQD"]).dropna()
        else:
            indicators["hyg_lqd_ratio"] = pd.Series(dtype=float)

        indicators["world_equity"] = yf_data.get("URTH", pd.Series(dtype=float))
        indicators["duration_proxy_tlt"] = yf_data.get("TLT", pd.Series(dtype=float))
        indicators["gold"] = yf_data.get("GLD", pd.Series(dtype=float))

    # ---- Calcolo punteggi ----
    indicator_scores = {}
    for key, series in indicators.items():
        meta = INDICATOR_META.get(key)
        if meta is None:
            continue
        score, z, latest = compute_indicator_score(series, meta["direction"])
        indicator_scores[key] = {"score": score, "z": z, "latest": latest, "status": classify_status(score)}

    block_scores = {}
    global_score = 0.0
    total_weight_used = 0.0
    for bkey, binfo in BLOCKS.items():
        vals = []
        for ikey in binfo["indicators"]:
            s = indicator_scores.get(ikey)
            if s and not np.isnan(s["score"]):
                vals.append(s["score"])
        if vals:
            block_score = float(np.mean(vals))
            block_scores[bkey] = {"score": block_score, "status": classify_status(block_score)}
            global_score += block_score * binfo["weight"]
            total_weight_used += binfo["weight"]
        else:
            block_scores[bkey] = {"score": np.nan, "status": "n/a"}

    global_score = (global_score / total_weight_used) if total_weight_used > 0 else np.nan
    global_status = classify_status(global_score)

    # -------------- SEZIONE SINTETICA ARRICCHITA --------------

    st.markdown("<div class='section-separator'></div>", unsafe_allow_html=True)
    st.subheader("0) Executive snapshot")

    with st.expander("Come leggere score & soglie", expanded=False):
        st.markdown(
            """
- Ogni indicatore viene trasformato in uno **score 0–100** usando uno z-score (ultimo valore vs storia recente) con segno coerente (risk-on / risk-off).
- **60+** = segnale pro-risk (🟢), **40–60** = neutrale (🟡), **<40** = risk-off (🔴).
- Il **Regime score globale** è una media ponderata dei blocchi (Policy/Macro/Conditions/Risk/Cross).
- Soglie e pesi sono **euristiche** (spiegabili e modificabili) — servono per coerenza, non per “precisione accademica”.
            """
        )

    k1, k2, k3 = st.columns(3)

    with k1:
        global_score_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("**Regime score (0–100)**")
        st.markdown(f"<div class='big-number'>{global_score_txt}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='sub-number'>{status_emoji(global_status)} {status_label_it(global_status)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with k2:
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("**Sintesi blocchi (score)**")
        for bkey, binfo in BLOCKS.items():
            s = block_scores[bkey]["score"]
            s_txt = "n/a" if np.isnan(s) else f"{s:.1f}"
            st.write(f"- {binfo['name']}: **{s_txt}** {score_to_badge(s)}")
        st.markdown("</div>", unsafe_allow_html=True)

    with k3:
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("**Impatti operativi (heuristic)**")
        st.write("- 🟢 Risk-on: ↑ equity risk budget, duration neutrale/leggera, ↑ credito (HY) con controllo rischio")
        st.write("- 🟡 Neutrale: sizing moderato, preferenza per qualità, hedges medi")
        st.write("- 🔴 Risk-off: ↓ equity, ↑ duration qualità, ↓ HY, ↑ hedges (cash/gold/USD)")
        st.markdown("</div>", unsafe_allow_html=True)

    # -------------- SEZIONI PER BLOCCHI (LAYOUT 2-UP) --------------

    for bkey, binfo in BLOCKS.items():
        st.markdown("<div class='section-separator'></div>", unsafe_allow_html=True)
        st.subheader(binfo["name"])
        st.write(binfo["description"])

        bscore = block_scores[bkey]["score"]
        bstatus = block_scores[bkey]["status"]
        bscore_txt = "n/a" if np.isnan(bscore) else f"{bscore:.1f}"
        st.write(f"**Block score:** {bscore_txt} {status_emoji(bstatus)} {status_label_it(bstatus)}")

        for row in binfo.get("layout_rows", []):
            if len(row) == 2:
                c1, c2 = st.columns(2)
                left_key, right_key = row
                with c1:
                    s = indicators.get(left_key, pd.Series(dtype=float))
                    if s is None or s.empty:
                        st.warning(f"Dati mancanti per {INDICATOR_META[left_key]['label']}.")
                    else:
                        render_indicator_tile(left_key, s, indicator_scores)
                with c2:
                    s = indicators.get(right_key, pd.Series(dtype=float))
                    if s is None or s.empty:
                        st.warning(f"Dati mancanti per {INDICATOR_META[right_key]['label']}.")
                    else:
                        render_indicator_tile(right_key, s, indicator_scores)
            elif len(row) == 1:
                only_key = row[0]
                s = indicators.get(only_key, pd.Series(dtype=float))
                if s is None or s.empty:
                    st.warning(f"Dati mancanti per {INDICATOR_META[only_key]['label']}.")
                else:
                    render_indicator_tile(only_key, s, indicator_scores)

    # -------------- WHAT CHANGED (COMPATTO) --------------

    st.markdown("<div class='section-separator'></div>", unsafe_allow_html=True)
    st.subheader("6) What changed – Δ 7d / 30d / 1Y")

    rows = []
    for key, meta in INDICATOR_META.items():
        series = indicators.get(key, pd.Series(dtype=float))
        if series is None or series.empty:
            continue
        d7 = pct_change_over_days(series, 7)
        d30 = pct_change_over_days(series, 30)
        d365 = pct_change_over_days(series, 365)
        rows.append(
            {
                "Indicatore": meta["label"],
                "Δ 7d %": None if np.isnan(d7) else round(d7, 2),
                "Δ 30d %": None if np.isnan(d30) else round(d30, 2),
                "Δ 1Y %": None if np.isnan(d365) else round(d365, 2),
            }
        )

    if rows:
        df_changes = pd.DataFrame(rows).set_index("Indicatore")
        st.dataframe(df_changes, use_container_width=True)
    else:
        st.write("Nessun dato sufficiente per calcolare le variazioni.")

    # -------------- REPORT / PAYLOAD --------------

    st.markdown("<div class='section-separator'></div>", unsafe_allow_html=True)
    st.subheader("7) Report (opzionale) – Payload per ChatGPT")

    st.write(
        "Genera un payload testuale copiabile per produrre un report operativo in ChatGPT (senza API)."
    )

    generate_payload = st.button("Generate payload")

    if generate_payload:
        payload_lines = []
        payload_lines.append("macro_regime_payload:")
        payload_lines.append(f"  generated_at: {today.isoformat()}")
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
            payload_lines.append(
                f"      latest_value: \"{fmt_value(latest, meta['unit'], meta.get('scale', 1.0))}\""
            )
            payload_lines.append(f"      score: {0.0 if np.isnan(score) else round(score, 1)}")
            payload_lines.append(f"      status: {status}")
            payload_lines.append(f"      delta_30d_pct: {0.0 if np.isnan(d30) else round(d30, 2)}")

        payload_text = "\n".join(payload_lines)

        st.markdown("**Payload generato (copiabile):**")
        st.code(payload_text, language="yaml")

        st.markdown("**Prompt suggerito per ChatGPT:**")
        prompt_text = """
Sei un macro strategist multi-asset. Ricevi il payload YAML sopra, generato dalla mia dashboard macro-finanziaria.

Task:
1) Ricostruisci il regime (Risk-on/Neutral/Risk-off) spiegando driver chiave (real rates, inflazione, curva, USD, credito, vol, equity, duration, oro).
2) Produci un report operativo ETF-based:
   - Equity exposure (aumenta/riduci rischio)
   - Duration (corta/media/lunga)
   - Credit risk (IG vs HY)
   - Hedges (USD, gold, cash-like)
   - 3–5 segnali da monitorare con soglie indicative.
Tono concreto, implementabile, prudente. Soglie euristiche.
"""
        st.code(prompt_text, language="markdown")


if __name__ == "__main__":
    main()
