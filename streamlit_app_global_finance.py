import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
from pandas.tseries.offsets import DateOffset


# -------------- CONFIG DI BASE --------------

st.set_page_config(
    page_title="Global Macro Regime Dashboard (Equity & Bond)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS minimale per look "premium" sobrio
st.markdown(
    """
    <style>
    .big-number {
        font-size: 2.2rem;
        font-weight: 600;
    }
    .sub-number {
        font-size: 1.0rem;
        color: #666;
    }
    .kpi-card {
        padding: 1rem 1.2rem;
        border-radius: 0.8rem;
        border: 1px solid #e0e0e0;
        background-color: #fafafa;
        margin-bottom: 1rem;
    }
    .section-separator {
        border-top: 1px solid #e0e0e0;
        margin: 1.5rem 0 1rem 0;
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
        "direction": -1,  # alto = risk-off
        "source": "FRED DFII10",
        "scale": 1.0,
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
        "direction": +1,  # curva più ripida = più risk-on
        "source": "DGS10 - DGS2",
        "scale": 1.0,
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
        "direction": -1,  # inflazione attesa alta = rischio restrizione
        "source": "FRED T10YIE",
        "scale": 1.0,
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
        "expander": {
            "what": "Tasso di disoccupazione USA.",
            "reference": "Minimi storici ~3–4%; aumenti rapidi spesso precedono/seguono recessioni.",
            "interpretation": (
                "- Disoccupazione **ai minimi ma stabile** → mercato del lavoro forte, ma attenzione a eccessi di overheating.\n"
                "- Disoccupazione **in forte crescita** → segnale di slowdown / recessione → ambiente più risk-off."
            ),
        },
    },

    # Financial Conditions & Liquidity
    "dxy": {
        "label": "US Dollar index (DXY)",
        "unit": "",
        "direction": -1,  # USD forte = condizioni più strette
        "source": "yfinance DX-Y.NYB",
        "scale": 1.0,
        "expander": {
            "what": "Indice del dollaro USA contro principali valute (proxy condizioni finanziarie globali).",
            "reference": "Trend forte e persistente del USD spesso coincide con fasi di stress o tightening globale.",
            "interpretation": (
                "- USD **forte e in apprezzamento** → condizioni più dure per EM e commodities, risk-off.\n"
                "- USD **debole o in deprezzamento** → condizioni più accomodanti, supporto a risk asset globali."
            ),
        },
    },
    "hy_oas": {
        "label": "US HY credit spread (OAS)",
        "unit": "pp",
        "direction": -1,
        "source": "FRED BAMLH0A0HYM2",
        "scale": 1.0,
        "expander": {
            "what": "Spread opzionale aggiustato dei corporate bond High Yield USA vs Treasury.",
            "reference": "Spread bassi (es. <400 bps) = risk appetite; spike sopra 600–700 bps = stress significativo.",
            "interpretation": (
                "- Spread **in allargamento** → mercato che prezza maggior rischio default → risk-off.\n"
                "- Spread **in compressione** → ricerca di rendimento, appetite per credito HY."
            ),
        },
    },
    "fed_balance_sheet": {
        "label": "Fed balance sheet (WALCL)",
        "unit": "bn USD",
        "direction": +1,  # bilancio più grande = più liquidità
        "source": "FRED WALCL",
        "scale": 1.0 / 1000.0,  # WALCL è in milioni USD -> bn USD
        "expander": {
            "what": "Totale attivi della Federal Reserve (dimensione del bilancio).",
            "reference": "Trend di espansione spesso associato a programmi di QE/liquidità straordinaria.",
            "interpretation": (
                "- Bilancio **in espansione** → più liquidità nel sistema, supporto ai risk asset.\n"
                "- Bilancio **in contrazione rapida** → QT e drenaggio di liquidità, spesso vento contrario per equity/credit."
            ),
        },
    },
    "rrp": {
        "label": "Fed Overnight RRP usage",
        "unit": "bn USD",
        "direction": -1,  # più RRP = più liquidità parcheggiata
        "source": "FRED RRPONTSYD",
        "scale": 1.0,  # RRPONTSYD è già in bn USD
        "expander": {
            "what": "Volume di Reverse Repo overnight della Fed (liquidità parcheggiata in strumenti risk-free).",
            "reference": "Valori elevati indicano molta liquidità 'ferma' fuori dai mercati di rischio.",
            "interpretation": (
                "- RRP **elevato e persistente** → liquidità che non fluisce verso risk asset.\n"
                "- RRP **in calo** → rilascio di liquidità verso il mercato, potenziale supporto a risk-on."
            ),
        },
    },

    # Risk Appetite & Stress
    "vix": {
        "label": "VIX (S&P 500 implied vol)",
        "unit": "",
        "direction": -1,
        "source": "yfinance ^VIX",
        "scale": 1.0,
        "expander": {
            "what": "Volatilità implicita a 30 giorni sull'S&P 500.",
            "reference": "VIX <15 = bassa volatilità; 15–25 = normale; >25–30 = stress; >40 = panic.",
            "interpretation": (
                "- VIX **molto basso e stabile** → complacency / risk-on (ma attenzione a eccessi).\n"
                "- VIX **in spike e stabilmente alto** → fasi di stress sistemico → risk-off."
            ),
        },
    },
    "spy_trend": {
        "label": "SPY / 200d MA (trend)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance SPY",
        "scale": 1.0,
        "expander": {
            "what": "Rapporto tra prezzo di SPY e sua media mobile a 200 giorni (proxy di trend di lungo periodo).",
            "reference": "Valori >1 indicano trend rialzista di lungo periodo; <1 trend ribassista.",
            "interpretation": (
                "- Ratio **>1 e crescente** → bull market strutturale, contesto più risk-on.\n"
                "- Ratio **<1 e decrescente** → bear market / drawdown prolungato → risk-off."
            ),
        },
    },
    "hyg_lqd_ratio": {
        "label": "HYG / LQD (HY vs IG credit)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance HYG, LQD",
        "scale": 1.0,
        "expander": {
            "what": "Rapporto tra ETF High Yield (HYG) e Investment Grade (LQD).",
            "reference": "Ratio in salita = HY che sovraperforma IG; ratio in calo = fuga verso qualità IG.",
            "interpretation": (
                "- Ratio **in salita** → mercato più disposto a prendere rischio di credito (risk-on).\n"
                "- Ratio **in discesa** → preferenza per IG, tipica di fasi risk-off."
            ),
        },
    },

    # Cross-Asset Performance
    "world_equity": {
        "label": "World equity (URTH / ACWI)",
        "unit": "",
        "direction": +1,
        "source": "yfinance URTH",
        "scale": 1.0,
        "expander": {
            "what": "ETF su MSCI World (o equivalente), proxy del risk-on globale.",
            "reference": "Trend di prezzo e drawdown forniscono il contesto globale oltre l'S&P 500.",
            "interpretation": (
                "- Trend **rialzista** e drawdown contenuti → conferma di regime risk-on globale.\n"
                "- Trend **ribassista / drawdown profondi** → conferma di regime risk-off globale."
            ),
        },
    },
    "duration_proxy_tlt": {
        "label": "US long Treasuries (TLT)",
        "unit": "",
        "direction": -1,  # rally TLT spesso in fasi di stress
        "source": "yfinance TLT",
        "scale": 1.0,
        "expander": {
            "what": "ETF su Treasury USA a lunga duration.",
            "reference": "Rally forti e improvvisi spesso coincidono con flight-to-quality / tagli tassi.",
            "interpretation": (
                "- TLT **in rally forte** spesso associato a fasi di stress su equity (risk-off), ma positivo per chi è lungo duration.\n"
                "- TLT **debole** in contesti di rialzo tassi → attenzione a duration e a equity long-duration."
            ),
        },
    },
    "gold": {
        "label": "Gold (GLD)",
        "unit": "",
        "direction": -1,
        "source": "yfinance GLD",
        "scale": 1.0,
        "expander": {
            "what": "ETF sull'oro fisico, hedge contro inflazione / rischio sistemico.",
            "reference": "Breakout dell'oro spesso segnala aumento di timori macro/geo o monetari.",
            "interpretation": (
                "- Oro **in forte uptrend** → mercato cerca hedging contro shock (inflazione, geopolitica, rischio sistemico).\n"
                "- Oro **laterale/debole** in bull equity 'pulito' → regime più risk-on."
            ),
        },
    },
}


BLOCKS = {
    "policy": {
        "name": "1) Policy & Real Rates",
        "weight": 0.25,
        "indicators": ["real_10y", "nominal_10y", "yield_curve_10_2"],
        "description": "Lettura di tassi reali/nominali e forma della curva per capire quanto il 'prezzo del tempo' sia favorevole o ostile ai risk asset.",
    },
    "macro": {
        "name": "2) Inflazione & Crescita",
        "weight": 0.20,
        "indicators": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],
        "description": "Backdrop macro: disinflation vs reflation vs stagflation/slowdown.",
    },
    "fincond": {
        "name": "3) Financial Conditions & Liquidity",
        "weight": 0.20,
        "indicators": ["dxy", "hy_oas", "fed_balance_sheet", "rrp"],
        "description": "Condizioni finanziarie globali, credito e liquidità dollaro.",
    },
    "risk": {
        "name": "4) Risk Appetite & Stress",
        "weight": 0.20,
        "indicators": ["vix", "spy_trend", "hyg_lqd_ratio"],
        "description": "Sentiment e stress di mercato tra equity e credito.",
    },
    "cross": {
        "name": "5) Asset Performance & Cross-Asset Confirmation",
        "weight": 0.15,
        "indicators": ["world_equity", "duration_proxy_tlt", "gold"],
        "description": "Conferma incrociata da equity globale, duration e hedging (oro).",
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
        s = s.sort_index()
        return s
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

        # yfinance può tornare MultiIndex columns (Price field -> tickers) oppure colonne piatte
        if isinstance(data.columns, pd.MultiIndex):
            # tipicamente livello 0 contiene "Adj Close" / "Close"
            if "Adj Close" in data.columns.get_level_values(0):
                px = data["Adj Close"]
            elif "Close" in data.columns.get_level_values(0):
                px = data["Close"]
            else:
                # fallback: prova a prendere il primo campo disponibile
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
        # Fallback: fetch each ticker separately
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
    """
    Ritorna (score_0_100, z_score, latest_value)
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
    if status == "risk_on":
        return "🟢"
    if status == "risk_off":
        return "🔴"
    if status == "neutral":
        return "🟡"
    return "⚪️"


def status_label_it(status: str) -> str:
    if status == "risk_on":
        return "Risk-on"
    if status == "risk_off":
        return "Risk-off"
    if status == "neutral":
        return "Neutrale"
    return "N/A"


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
        return f"{v:.2f}"
    if unit == "bn USD":
        return f"{v:.1f} {unit}"
    if unit == "":
        # prezzi/indici: lascia due decimali, ma senza unità
        return f"{v:.2f}"
    return f"{v:.2f} {unit}"


# -------------- MAIN DASHBOARD --------------

def main():
    st.title("Global Macro Regime Dashboard – Equity & Bond (ETF-based)")

    st.write(
        "Dashboard macro–finanziaria **global multi-asset** per leggere il regime di mercato "
        "e tradurlo in decisioni operative su equity, duration, credito e hedging."
    )

    # ---- Sidebar: parametri ----
    st.sidebar.header("Impostazioni")

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

    # ---- Fetch dati ----
    st.info("Caricamento dati in corso (FRED + yfinance). L'operazione può richiedere qualche secondo...")

    # ---- Fetch dati FRED ----
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

    # Costruzione serie derivate FRED
    indicators = {}

    # Policy & rates
    indicators["real_10y"] = fred_data["real_10y"]
    indicators["nominal_10y"] = fred_data["nominal_10y"]

    if not fred_data["nominal_10y"].empty and not fred_data["dgs2"].empty:
        yc = fred_data["nominal_10y"].to_frame("10y").join(
            fred_data["dgs2"].to_frame("2y"), how="inner"
        )
        indicators["yield_curve_10_2"] = (yc["10y"] - yc["2y"]).dropna()
    else:
        indicators["yield_curve_10_2"] = pd.Series(dtype=float)

    # Macro: CPI YoY e unemployment
    cpi_index = fred_data["cpi_index"]
    if not cpi_index.empty:
        indicators["cpi_yoy"] = (cpi_index.pct_change(12) * 100.0).dropna()
    else:
        indicators["cpi_yoy"] = pd.Series(dtype=float)

    indicators["breakeven_10y"] = fred_data["breakeven_10y"]
    indicators["unemployment_rate"] = fred_data["unemployment_rate"]

    # Financial conditions
    indicators["hy_oas"] = fred_data["hy_oas"]
    indicators["fed_balance_sheet"] = fred_data["fed_balance_sheet"]
    indicators["rrp"] = fred_data["rrp"]

    # ---- Fetch dati yfinance ----
    yf_tickers = [
        "DX-Y.NYB",  # DXY
        "^VIX",
        "SPY",
        "HYG",
        "LQD",
        "URTH",
        "TLT",
        "GLD",
    ]
    yf_data = fetch_yf_series(yf_tickers, start_date)

    indicators["dxy"] = yf_data.get("DX-Y.NYB", pd.Series(dtype=float))
    indicators["vix"] = yf_data.get("^VIX", pd.Series(dtype=float))

    # SPY trend
    spy_series = yf_data.get("SPY", pd.Series(dtype=float))
    if not spy_series.empty:
        ma200 = spy_series.rolling(200).mean()
        spy_trend = (spy_series / ma200).dropna()
        indicators["spy_trend"] = spy_trend
    else:
        indicators["spy_trend"] = pd.Series(dtype=float)

    # HYG / LQD ratio
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

    # ---- Calcolo punteggi per indicatore ----
    indicator_scores = {}
    for key, series in indicators.items():
        meta = INDICATOR_META.get(key)
        if meta is None:
            continue
        score, z, latest = compute_indicator_score(series, meta["direction"])
        status = classify_status(score)
        indicator_scores[key] = {
            "score": score,
            "z": z,
            "latest": latest,
            "status": status,
        }

    # ---- Calcolo punteggi per blocco e score globale ----
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
            block_status = classify_status(block_score)
            block_scores[bkey] = {"score": block_score, "status": block_status}
            global_score += block_score * binfo["weight"]
            total_weight_used += binfo["weight"]
        else:
            block_scores[bkey] = {"score": np.nan, "status": "n/a"}

    if total_weight_used > 0:
        global_score = global_score / total_weight_used
    else:
        global_score = np.nan

    global_status = classify_status(global_score)

    # ---- KPI principali ----
    st.markdown("<div class='section-separator'></div>", unsafe_allow_html=True)
    st.subheader("0) KPI sintetici & regime globale")

    col1, col2, col3 = st.columns(3)

    with col1:
        global_score_txt = "n/a" if np.isnan(global_score) else f"{global_score:.1f}"
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("**Regime score (0–100)**")
        st.markdown(f"<div class='big-number'>{global_score_txt}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='sub-number'>{status_emoji(global_status)} {status_label_it(global_status)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        pol = block_scores.get("policy", {}).get("score", np.nan)
        mac = block_scores.get("macro", {}).get("score", np.nan)
        txt = "n/a"
        if not np.isnan(pol) and not np.isnan(mac):
            txt = f"{(pol + mac) / 2:.1f}"
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("**Policy & Macro** (media)")
        st.markdown(f"<div class='big-number'>{txt}</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='sub-number'>Stato medio di tassi reali, curva, inflazione e crescita.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        risk_block = block_scores.get("risk", {}).get("score", np.nan)
        fin_block = block_scores.get("fincond", {}).get("score", np.nan)
        txt2 = "n/a"
        if not np.isnan(risk_block) and not np.isnan(fin_block):
            txt2 = f"{(risk_block + fin_block) / 2:.1f}"
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("**Conditions & Risk appetite** (media)")
        st.markdown(f"<div class='big-number'>{txt2}</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='sub-number'>Financial conditions, credito, vol e sentiment.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption("Nota: soglie regime (euristiche): <40 = Risk-off, 40–60 = Neutrale, >60 = Risk-on.")

    # -------------- SEZIONI PER BLOCCHI --------------

    for bkey, binfo in BLOCKS.items():
        st.markdown("<div class='section-separator'></div>", unsafe_allow_html=True)
        st.subheader(binfo["name"])
        st.write(binfo["description"])

        bscore = block_scores[bkey]["score"]
        bstatus = block_scores[bkey]["status"]

        colb1, colb2 = st.columns([1, 3])
        with colb1:
            st.markdown("**Block score**")
            if np.isnan(bscore):
                st.write("n/a")
            else:
                st.write(f"{bscore:.1f} {status_emoji(bstatus)} {status_label_it(bstatus)}")
        with colb2:
            st.write("")

        for ikey in binfo["indicators"]:
            meta = INDICATOR_META.get(ikey)
            if meta is None:
                continue

            series = indicators.get(ikey, pd.Series(dtype=float))
            if series is None or series.empty:
                st.warning(f"Dati mancanti per {meta['label']}.")
                continue

            score_info = indicator_scores.get(ikey, {})
            score = score_info.get("score", np.nan)
            status = score_info.get("status", "n/a")
            latest = score_info.get("latest", np.nan)

            delta_1m = pct_change_over_days(series, 30)
            delta_6m = pct_change_over_days(series, 180)
            delta_1y = pct_change_over_days(series, 365)

            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{meta['label']}**")

                with st.expander("Definizione & guida alla lettura", expanded=False):
                    exp = meta["expander"]
                    st.markdown(f"**Che metrica è**: {exp['what']}")
                    st.markdown(f"**Valori di riferimento**: {exp['reference']}")
                    st.markdown("**Interpretazione bidirezionale**:")
                    st.markdown(exp["interpretation"])
                    st.markdown(
                        f"**Snapshot 1M / 6M / 1Y**: "
                        f"{'n/a' if np.isnan(delta_1m) else f'{delta_1m:+.1f}%'} / "
                        f"{'n/a' if np.isnan(delta_6m) else f'{delta_6m:+.1f}%'} / "
                        f"{'n/a' if np.isnan(delta_1y) else f'{delta_1y:+.1f}%'}"
                    )

            with c2:
                st.metric(
                    label="Ultimo valore",
                    value=fmt_value(latest, meta["unit"], meta.get("scale", 1.0)),
                    delta=None if np.isnan(delta_1m) else f"{delta_1m:+.1f}% vs 1M",
                )
                score_txt = "n/a" if np.isnan(score) else f"{score:.1f}"
                st.write(f"{status_emoji(status)} {status_label_it(status)} (score {score_txt})")

            st.line_chart(series)

    # -------------- WHAT CHANGED --------------

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

    # -------------- REPORT / PAYLOAD PER CHATGPT --------------

    st.markdown("<div class='section-separator'></div>", unsafe_allow_html=True)
    st.subheader("7) Report (opzionale) – Payload per ChatGPT")

    st.write(
        "Questa sezione genera un payload testuale che puoi copiare e incollare in ChatGPT, "
        "insieme a un prompt standard per ottenere un report operativo (senza usare API)."
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

        st.markdown("**Prompt suggerito per ChatGPT (da incollare sotto al payload):**")
        prompt_text = """
Sei un macro strategist multi-asset. Ricevi il payload YAML qui sopra, generato dalla mia dashboard macro-finanziaria personale.

Task:
1. Leggi attentamente il payload e ricostruisci il **regime attuale** (Risk-on / Neutral / Risk-off) spiegando:
   - ruolo di tassi reali, inflazione, curva, USD, credito, vol, equity, duration, oro
   - coerenza o divergenze tra blocchi.

2. Produci un **report operativo in italiano**, con sezioni:
   1) Sintesi regime (max 5 bullet molto chiari)
   2) Equity (ETF): quanto rischio posso prendere? (aumenti/riduzioni graduali di esposizione, tipo SPY/ACWI, factor ETF, EM vs DM)
   3) Duration (bond ETF): preferenza per corta/media/lunga, tipo IEF/TLT, con motivazione
   4) Credit risk (IG vs HY): mix suggerito tra LQD / HYG e commento sugli spread
   5) Hedges: ruolo di USD, gold, cash-like (es. T-Bill ETF), se aumentare o ridurre
   6) Segnali chiave “increase/decrease risk”: quali variabili monitorare nelle prossime 2–4 settimane, con soglie indicative.

3. Sii **concreto e implementabile** per un investitore che usa solo ETF liquidi globali, senza usare leva o derivati. Usa toni prudenti, sottolinea che il regime è una guida probabilistica (non certezza) e che le soglie sono euristiche.

Non aggiungere disclaimer legali lunghissimi: una breve nota finale è sufficiente.
"""
        st.code(prompt_text, language="markdown")


if __name__ == "__main__":
    main()


