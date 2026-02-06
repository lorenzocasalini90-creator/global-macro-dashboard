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
    page_title="Global finance | Macro overview (Dalio-enhanced)",
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

      button[data-baseweb="tab"] { color: var(--muted) !important; }
      button[data-baseweb="tab"][aria-selected="true"]{ color: var(--text) !important; }

      .stDataFrame { border: 1px solid var(--border); border-radius: 12px; overflow:hidden; }
      code { color: rgba(255,255,255,0.86); }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# CONFIG: INDICATORS & BLOCKS (DALIO-ENHANCED)
# =========================

# Scoring modes:
# - z5y: z-score vs last ~5y (market thermometers)
# - pct20y: percentile vs last ~20y (structural/stock constraints)
INDICATOR_META = {
    # -------------------------
    # BLOCCO 1 — PRICE OF TIME
    # -------------------------
    "real_10y": {
        "label": "US 10Y TIPS real yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DFII10",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Rendimento reale (TIPS 10Y): prezzo del tempo al netto dell’inflazione attesa.",
            "reference": "<0% molto accomodante; 0–2% neutrale; >2% restrittivo (euristiche).",
            "interpretation": (
                "- **↑ real yield** → headwind equity (growth) e duration lunga.\n"
                "- **↓ real yield** → tailwind risk assets e duration più difensiva."
            ),
            "dalio_bridge": "Real yield ↑ stringe il vincolo di funding per tutti (costo reale capitale).",
        },
    },
    "nominal_10y": {
        "label": "US 10Y nominal yield",
        "unit": "%",
        "direction": -1,
        "source": "FRED DGS10",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Rendimento nominale Treasury 10Y: costo del capitale e benchmark per sconto cash flow.",
            "reference": "Movimenti rapidi verso l’alto spesso equivalgono a tightening finanziario.",
            "interpretation": (
                "- **↑ rapido** → pressione su equity e bond esistenti.\n"
                "- **↓** → supporto a duration e spesso a equity (dipende dal contesto macro)."
            ),
            "dalio_bridge": "Yield ↑ = mercato chiede più compenso (o inflazione, o term premium, o entrambe).",
        },
    },
    "yield_curve_10_2": {
        "label": "US Yield curve (10Y–2Y)",
        "unit": "pp",
        "direction": +1,
        "source": "FRED DGS10 - DGS2",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Differenza 10Y–2Y: proxy ciclo/attese recessione.",
            "reference": "<0 curva invertita (late cycle); >0 curva normale (euristiche).",
            "interpretation": (
                "- **Molto negativa** e persistente → rischio recessione / risk-off.\n"
                "- **Ritorno sopra 0** → normalizzazione del ciclo."
            ),
            "dalio_bridge": "Curva invertita = policy restrittiva rispetto al ciclo → aumenta probabilità di deleveraging.",
        },
    },

    # -------------------------
    # BLOCCO 2 — MACRO (INFLATION/GROWTH)
    # -------------------------
    "breakeven_10y": {
        "label": "10Y Breakeven inflation",
        "unit": "%",
        "direction": -1,
        "source": "FRED T10YIE",
        "scale": 1.0,
        "ref_line": 2.5,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Inflazione attesa (10Y) implicita dal mercato: nominali vs TIPS.",
            "reference": "~2–3% = ben ancorata; molto >3% = rischio inflazione sticky (euristiche).",
            "interpretation": (
                "- **↑** → rischio policy restrittiva più a lungo.\n"
                "- **↓ verso target** → più spazio per easing."
            ),
            "dalio_bridge": "Inflazione attesa ↑ rende più probabile repressione finanziaria (tassi reali compressi) in stress.",
        },
    },
    "cpi_yoy": {
        "label": "US CPI YoY",
        "unit": "%",
        "direction": -1,
        "source": "FRED CPIAUCSL (YoY calcolato)",
        "scale": 1.0,
        "ref_line": 3.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Inflazione headline YoY (proxy).",
            "reference": "Target 2% (Fed); >3–4% a lungo = sticky (euristiche).",
            "interpretation": (
                "- **Disinflation** → supportive per duration ed equity.\n"
                "- **Re-acceleration** → rischio tightening / tassi più alti più a lungo."
            ),
            "dalio_bridge": "Inflazione persistente = vincolo primario di policy (meno spazio per rescue del credito).",
        },
    },
    "unemployment_rate": {
        "label": "US Unemployment rate",
        "unit": "%",
        "direction": -1,
        "source": "FRED UNRATE",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Disoccupazione USA: proxy crescita / ciclo.",
            "reference": "Salite rapide spesso associano slowdown/recessione.",
            "interpretation": (
                "- **↑ veloce** → rischio recessionario (risk-off).\n"
                "- **Stabile** → contesto più benigno."
            ),
            "dalio_bridge": "Slack ↑ + debito alto = pressioni politiche per policy di supporto (dominanza fiscale più probabile).",
        },
    },

    # -------------------------
    # BLOCCO 3 — FINANCIAL CONDITIONS & STRESS
    # -------------------------
    "usd_index": {
        "label": "USD index (DXY / FRED proxy)",
        "unit": "",
        "direction": -1,
        "source": "yfinance DX-Y.NYB (fallback FRED DTWEXBGS)",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Misura di forza del dollaro. Se DXY non è disponibile, usa proxy FRED broad dollar index.",
            "reference": "USD forte = condizioni globali più strette (euristico).",
            "interpretation": (
                "- **USD ↑** → tightening globale / pressione su risk asset.\n"
                "- **USD ↓** → condizioni più accomodanti."
            ),
            "dalio_bridge": "USD ↑ = funding stress globale ↑ (leva e debito in USD diventano più pesanti).",
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
            "what": "Spread HY (OAS): stress creditizio e rischio default percepito.",
            "reference": "<4% spesso benigno; >6–7% stress (euristiche).",
            "interpretation": (
                "- **↑** → risk-off (credit stress).\n"
                "- **↓** → risk appetite."
            ),
            "dalio_bridge": "Credit stress ↑ accelera deleveraging (non-lineare).",
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
            "what": "Volatilità implicita S&P 500.",
            "reference": "<15 basso; 15–25 normale; >25 stress (euristiche).",
            "interpretation": (
                "- **↑** → risk-off.\n"
                "- **↓** → risk-on."
            ),
            "dalio_bridge": "Vol ↑ = condizioni finanziarie stringono anche senza rialzi tassi (risk premium ↑).",
        },
    },
    "spy_trend": {
        "label": "SPY trend (SPY / 200d MA)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance SPY",
        "scale": 1.0,
        "ref_line": 1.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Trend proxy: prezzo SPY vs media 200 giorni.",
            "reference": ">1 bull trend; <1 downtrend (euristiche).",
            "interpretation": (
                "- **>1** → supporto risk-on.\n"
                "- **<1** → risk-off."
            ),
            "dalio_bridge": "Trend ↓ + credit stress ↑ = fase tipica di deleveraging.",
        },
    },
    "hyg_lqd_ratio": {
        "label": "Credit risk appetite (HYG / LQD)",
        "unit": "ratio",
        "direction": +1,
        "source": "yfinance HYG, LQD",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "HY vs IG: propensione al rischio credito.",
            "reference": "Ratio ↑ = più appetite HY; ratio ↓ = flight to quality.",
            "interpretation": (
                "- **↑** → risk-on.\n"
                "- **↓** → risk-off."
            ),
            "dalio_bridge": "Flight-to-quality segnala vincoli di funding che si irrigidiscono.",
        },
    },

    # -------------------------
    # BLOCCO 4 — LIQUIDITY PLUMBING
    # -------------------------
    "fed_balance_sheet": {
        "label": "Fed balance sheet (WALCL)",
        "unit": "bn USD",
        "direction": +1,
        "source": "FRED WALCL (millions USD -> bn USD)",
        "scale": 1.0 / 1000.0,  # WALCL is in millions of USD
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Totale attivi Fed: proxy liquidità sistemica.",
            "reference": "Trend espansivo (QE) tende a supportare risk asset; QT tende a drenare.",
            "interpretation": (
                "- **↑** → più liquidità (tailwind).\n"
                "- **↓** → drenaggio (headwind)."
            ),
            "dalio_bridge": "Il “plumbing” determina se i flussi sostengono o drenano i risk assets.",
        },
    },
    "rrp": {
        "label": "Fed Overnight RRP",
        "unit": "bn USD",
        "direction": -1,
        "source": "FRED RRPONTSYD (typically bn USD)",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "z5y",
        "expander": {
            "what": "RRP: liquidità parcheggiata in facility risk-free.",
            "reference": "RRP alto = liquidità 'ferma'; in calo = liquidità rilasciata.",
            "interpretation": (
                "- **RRP ↑** → meno benzina per risk asset.\n"
                "- **RRP ↓** → potenziale supporto a risk-on."
            ),
            "dalio_bridge": "RRP ↓ spesso libera marginal liquidity (supporto tattico al risk).",
        },
    },

    # -------------------------
    # BLOCCO 5 — DALIO CORE: DEBT & FISCAL DOMINANCE
    # -------------------------
    "interest_payments": {
        "label": "US Federal interest payments (quarterly)",
        "unit": "bn USD",
        "direction": -1,
        "source": "FRED A091RC1Q027SBEA (billions, quarterly)",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Spesa interessi del governo federale (pagamenti interessi).",
            "reference": "Stress ↑ quando la dinamica accelera e diventa vincolo politico.",
            "interpretation": (
                "- **↑ persistente** → aumenta probabilità di dominanza fiscale / repressione.\n"
                "- **↓** → vincolo del debito più gestibile."
            ),
            "dalio_bridge": "Debt service ↑ → pressione politica → incentivi a repressione finanziaria.",
        },
    },
    "federal_receipts": {
        "label": "US Federal current receipts (quarterly)",
        "unit": "bn USD",
        "direction": +1,
        "source": "FRED FGRECPT (billions, quarterly)",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Entrate correnti federali (receipts).",
            "reference": "Usato per ratio interest/receipts: sostenibilità del servizio del debito.",
            "interpretation": (
                "- **Receipts ↑** (a parità di interessi) → sostenibilità migliore.\n"
                "- **Receipts ↓** → vincolo fiscale più stringente."
            ),
            "dalio_bridge": "Interest/receipts ↑ = il debito “pesa” e riduce margine di manovra.",
        },
    },
    "interest_to_receipts": {
        "label": "Debt service stress (Interest / Receipts)",
        "unit": "ratio",
        "direction": -1,
        "source": "Derived: A091RC1Q027SBEA / FGRECPT",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Proxy sostenibilità: quota di receipts “mangiata” dagli interessi.",
            "reference": "Valori alti e in accelerazione = vincolo politico/fiscale (euristico).",
            "interpretation": (
                "- **↑** → aumenta probabilità di policy orientata al funding.\n"
                "- **↓** → più spazio per policy anti-inflazione senza stress."
            ),
            "dalio_bridge": "Debt service ↑ → incentivi a tollerare inflazione / comprimere tassi reali.",
        },
    },
    "deficit_gdp": {
        "label": "Federal surplus/deficit as % of GDP",
        "unit": "%",
        "direction": -1,
        "source": "FRED FYFSGDA188S (% GDP, annual)",
        "scale": 1.0,
        "ref_line": -3.0,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Saldo federale (% PIL). Valori negativi = deficit.",
            "reference": "Deficit persistente = supply Treasury persistente (euristico).",
            "interpretation": (
                "- **Deficit ↑ in valore assoluto (più negativo)** → pressione su term premium e funding.\n"
                "- **Miglioramento** → riduce pressione strutturale."
            ),
            "dalio_bridge": "Deficit ↑ → supply Treasury ↑ → term premium ↑ → duration perde.",
        },
    },
    "term_premium_10y": {
        "label": "US 10Y term premium (ACM)",
        "unit": "%",
        "direction": -1,
        "source": "FRED ACMTP10",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Premio a termine: compenso richiesto dal mercato per detenere duration nominale.",
            "reference": "Term premium ↑ = duration nominale più “tossica” (euristico).",
            "interpretation": (
                "- **↑** → rischio su bond lunghi nominali.\n"
                "- **↓** → duration torna hedge più affidabile."
            ),
            "dalio_bridge": "Se term premium sale per supply/funding, la duration smette di proteggere.",
        },
    },

    # -------------------------
    # BLOCCO 6 — EXTERNAL BALANCE
    # -------------------------
    "current_account_gdp": {
        "label": "US Current account balance (% of GDP)",
        "unit": "%",
        "direction": +1,
        "source": "FRED USAB6BLTT02STSAQ (% GDP, quarterly)",
        "scale": 1.0,
        "ref_line": 0.0,
        "scoring_mode": "pct20y",
        "expander": {
            "what": "Saldo conto corrente USA (% PIL). Valori negativi = dipendenza da capitali esteri.",
            "reference": "Deficit persistente = vulnerabilità quando USD funding si stringe (euristico).",
            "interpretation": (
                "- **Più negativo** → dipendenza estera ↑.\n"
                "- **Verso 0 / positivo** → vincolo esterno ↓."
            ),
            "dalio_bridge": "Current account deficit = dipendenza da capitali esteri → vulnerabilità in tightening globale.",
        },
    },

    # -------------------------
    # CROSS-ASSET CONFIRMATION
    # -------------------------
    "world_equity": {
        "label": "Global equities (URTH)",
        "unit": "",
        "direction": +1,
        "source": "yfinance URTH",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Equity globale: conferma regime non solo US.",
            "reference": "Trend e drawdown come conferma/smentita.",
            "interpretation": (
                "- **Trend ↑** → conferma risk-on.\n"
                "- **Trend ↓** → conferma risk-off."
            ),
            "dalio_bridge": "Conferma cross-asset: se il mondo rompe, il rischio è più strutturale.",
        },
    },
    "duration_proxy_tlt": {
        "label": "Long duration (TLT)",
        "unit": "",
        "direction": -1,
        "source": "yfinance TLT",
        "scale": 1.0,
        "ref_line": None,
        "scoring_mode": "z5y",
        "expander": {
            "what": "Treasury lunga duration (hedge tipico in risk-off).",
            "reference": "Rally TLT spesso coincide con flight-to-quality.",
            "interpretation": (
                "- **TLT ↑** → spesso risk-off / easing expectations.\n"
                "- **TLT ↓** con yields ↑ → headwind per duration."
            ),
            "dalio_bridge": "TLT che non protegge in stress spesso segnala inflationary deleveraging / term premium ↑.",
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
            "what": "Oro: hedge (inflazione/shock/sistemico).",
            "reference": "Breakout spesso segnala domanda di hedging.",
            "interpretation": (
                "- **Gold ↑** → domanda di hedge.\n"
                "- **Gold ↓** in bull equity → risk-on pulito."
            ),
            "dalio_bridge": "Oro tende a funzionare come hedge quando policy vira a repressione / inflazione tollerata.",
        },
    },
}

# 6 blocchi core + 1 tab extra di conferma (non pesa nel global)
BLOCKS = {
    "price_of_time": {
        "name": "1) Price of time (Monetary stance)",
        "weight": 0.20,
        "indicators": ["real_10y", "nominal_10y", "yield_curve_10_2"],
        "layout_rows": [["real_10y", "nominal_10y"], ["yield_curve_10_2"]],
        "desc": "Costo reale del capitale e sensibilità degli asset alla duration.",
    },
    "macro": {
        "name": "2) Macro cycle (Inflation / Growth)",
        "weight": 0.15,
        "indicators": ["breakeven_10y", "cpi_yoy", "unemployment_rate"],
        "layout_rows": [["breakeven_10y", "cpi_yoy"], ["unemployment_rate"]],
        "desc": "Vincolo di policy: inflazione sticky vs rallentamento crescita.",
    },
    "conditions": {
        "name": "3) Financial conditions & stress (USD + credit + vol + trend)",
        "weight": 0.20,
        "indicators": ["usd_index", "hy_oas", "vix", "spy_trend", "hyg_lqd_ratio"],
        "layout_rows": [["usd_index", "hy_oas"], ["vix", "spy_trend"], ["hyg_lqd_ratio"]],
        "desc": "Tightening globale: dollaro, credito, volatilità e trend (termometro di risk-on/off).",
    },
    "plumbing": {
        "name": "4) System liquidity (plumbing)",
        "weight": 0.15,
        "indicators": ["fed_balance_sheet", "rrp"],
        "layout_rows": [["fed_balance_sheet", "rrp"]],
        "desc": "Liquidità sistemica: supporto vs drenaggio per i risk assets.",
    },
    "debt_fiscal": {
        "name": "5) Dalio core — Debt sustainability & fiscal dominance",
        "weight": 0.20,
        "indicators": ["interest_to_receipts", "deficit_gdp", "term_premium_10y", "interest_payments", "federal_receipts"],
        "layout_rows": [["interest_to_receipts", "deficit_gdp"], ["term_premium_10y"], ["interest_payments", "federal_receipts"]],
        "desc": "Quando il problema non è più il ciclo ma il bilancio sovrano e i vincoli di funding.",
    },
    "external": {
        "name": "6) External balance — Who funds who",
        "weight": 0.10,
        "indicators": ["current_account_gdp"],
        "layout_rows": [["current_account_gdp"]],
        "desc": "Vincolo esterno: dipendenza da capitali esteri e vulnerabilità in USD tightening.",
    },
    "cross": {
        "name": "Cross-asset confirmation (non-weighted)",
        "weight": 0.00,
        "indicators": ["world_equity", "duration_proxy_tlt", "gold"],
        "layout_rows": [["world_equity", "duration_proxy_tlt"], ["gold"]],
        "desc": "Conferme cross-asset (utile per coerenza del regime; non pesa nel global score).",
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
        s = pd.Series(vals, index=idx).astype(float).sort_index()
        return s
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600)
def fetch_yf_one(ticker: str, start_date: str) -> pd.Series:
    """Fetch robusto per singolo ticker (evita problemi multi-ticker / multiindex)."""
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
# FREQUENCY-AWARE DELTAS
# =========================

def infer_frequency(series: pd.Series) -> str:
    """
    Rough frequency classification based on median spacing in days.
    Returns one of: 'daily', 'weekly', 'monthly', 'quarterly', 'annual', 'unknown'
    """
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
    """
    Returns:
      {
        "label_a": "Δ7d", "val_a": float or nan,
        "label_b": "Δ30d", "val_b": float or nan,
        "label_c": "Δ1Y", "val_c": float or nan,
        "freq": "daily|weekly|monthly|quarterly|annual|unknown"
      }
    For slower series, uses period-based deltas (1Q/4Q, 1Y/5Y) instead of days-based.
    """
    freq = infer_frequency(series)

    if freq in ("daily", "weekly", "unknown"):
        return {
            "freq": freq,
            "label_a": "Δ7d",
            "val_a": pct_change_by_days(series, 7),
            "label_b": "Δ30d",
            "val_b": pct_change_by_days(series, 30),
            "label_c": "Δ1Y",
            "val_c": pct_change_by_days(series, 365),
        }

    if freq == "monthly":
        return {
            "freq": freq,
            "label_a": "Δ1M",
            "val_a": pct_change_by_periods(series, 1),
            "label_b": "Δ3M",
            "val_b": pct_change_by_periods(series, 3),
            "label_c": "Δ12M",
            "val_c": pct_change_by_periods(series, 12),
        }

    if freq == "quarterly":
        return {
            "freq": freq,
            "label_a": "Δ1Q",
            "val_a": pct_change_by_periods(series, 1),
            "label_b": "Δ4Q",
            "val_b": pct_change_by_periods(series, 4),
            "label_c": "Δ8Q",
            "val_c": pct_change_by_periods(series, 8),
        }

    if freq == "annual":
        return {
            "freq": freq,
            "label_a": "Δ1Y",
            "val_a": pct_change_by_periods(series, 1),
            "label_b": "Δ3Y",
            "val_b": pct_change_by_periods(series, 3),
            "label_c": "Δ5Y",
            "val_c": pct_change_by_periods(series, 5),
        }

    return {
        "freq": freq,
        "label_a": "Δ7d",
        "val_a": pct_change_by_days(series, 7),
        "label_b": "Δ30d",
        "val_b": pct_change_by_days(series, 30),
        "label_c": "Δ1Y",
        "val_c": pct_change_by_days(series, 365),
    }


def fmt_delta(val: float) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "n/a"
    return f"{val:+.1f}%"


# =========================
# SCORING (z5y vs pct20y)
# =========================

def rolling_percentile_last(hist: pd.Series, latest: float) -> float:
    """Percentile rank of latest within hist (0..1)."""
    h = hist.dropna()
    if len(h) < 8 or pd.isna(latest):
        return np.nan
    return float((h <= latest).mean())


def compute_indicator_score(series: pd.Series, direction: int, scoring_mode: str = "z5y"):
    """
    Returns: (score_0_100, signal, latest)
    signal = z-score (for z5y) or percentile-mapped signal in [-2,+2] (for pct20y)
    """
    if series is None or series.empty:
        return np.nan, np.nan, np.nan
    s = series.dropna()
    if len(s) < 8:
        return np.nan, np.nan, (np.nan if len(s) == 0 else float(s.iloc[-1]))

    latest = float(s.iloc[-1])
    end = s.index.max()

    if scoring_mode == "pct20y":
        # allow fewer observations; structural series can be quarterly/annual
        start = end - DateOffset(years=20)
        hist = s[s.index >= start]
        if len(hist) < 8:
            # if we don't have enough for a meaningful percentile, return n/a
            return np.nan, np.nan, latest
        p = rolling_percentile_last(hist, latest)  # 0..1
        if np.isnan(p):
            return np.nan, np.nan, latest
        sig = (p - 0.5) * 4.0  # 0->-2, 0.5->0, 1->+2
    else:
        # z5y: needs enough observations to be stable
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
    mode = meta.get("scoring_mode", "z5y")

    deltas = compute_deltas(series)
    score_txt = "n/a" if np.isnan(score) else f"{score:.1f}"
    latest_txt = fmt_value(latest, meta["unit"], meta.get("scale", 1.0))
    mode_badge = "<span class='pill'>score: z5y</span>" if mode == "z5y" else "<span class='pill'>score: pct20y</span>"

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='tile-toprow'>
          <div>
            <div class='tile-title'>{meta["label"]}</div>
            <div class='tile-meta'>Fonte: {meta["source"]}</div>
          </div>
          <div style='text-align:right'>
            <div>{mode_badge}<span class='pill'>Ultimo: {latest_txt}</span>{status_pill_html(status)}</div>
            <div class='tiny'>Score: {score_txt} · {deltas["label_b"]}: {fmt_delta(deltas["val_b"])}</div>
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
        st.markdown(f"**Ponte (Dalio)**: {exp.get('dalio_bridge','')}")
        st.markdown(
            f"**What changed**: "
            f"{deltas['label_a']} {fmt_delta(deltas['val_a'])}, "
            f"{deltas['label_b']} {fmt_delta(deltas['val_b'])}, "
            f"{deltas['label_c']} {fmt_delta(deltas['val_c'])}"
        )

    fig = plot_premium(series, meta["label"], ref_line=meta.get("ref_line", None))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# DALIO OPERATING LINES (ETF-BASED)
# =========================

def latest_value(indicator_scores: dict, key: str) -> float:
    v = indicator_scores.get(key, {}).get("latest", np.nan)
    return np.nan if v is None else float(v) if not (isinstance(v, float) and np.isnan(v)) else np.nan


def operating_lines(block_scores: dict, indicator_scores: dict):
    """
    4 decision-friendly lines:
    - Equity risk budget
    - Duration stance
    - Credit stance
    - Hedges
    NOTE: uses a mix of block scores (regime) + SELECTED latest values (levels), to avoid score/level confusion.
    """
    gs = block_scores.get("GLOBAL", {}).get("score", np.nan)

    def _sg(x):
        if np.isnan(x): return 0.0
        return float(x)

    # Equity budget: mostly global + conditions
    cond = _sg(block_scores.get("conditions", {}).get("score", np.nan))

    if not np.isnan(gs):
        if gs >= 60 and cond >= 55:
            equity = "↑ (increase) — beta ok, ma controlla credito"
        elif gs <= 40 or cond <= 40:
            equity = "↓ (reduce) — priorità difesa / qualità"
        else:
            equity = "→ (neutral) — sizing moderato"
    else:
        equity = "n/a"

    # Duration stance: combine regime (price_of_time) + LEVELS (CPI, term premium)
    pot = _sg(block_scores.get("price_of_time", {}).get("score", np.nan))
    termp_score = _sg(indicator_scores.get("term_premium_10y", {}).get("score", np.nan))

    cpi_latest = latest_value(indicator_scores, "cpi_yoy")          # LEVEL in %
    breakeven_latest = latest_value(indicator_scores, "breakeven_10y")  # LEVEL in %

    # Heuristic logic (level-aware):
    # - if term premium stress + inflation elevated -> avoid long nominal, prefer short/TIPS
    # - if disinflation and price_of_time improving and term premium benign -> long duration can hedge
    inflation_elevated = (not np.isnan(cpi_latest) and cpi_latest >= 3.0) or (not np.isnan(breakeven_latest) and breakeven_latest >= 2.7)
    inflation_benign = (not np.isnan(cpi_latest) and cpi_latest <= 2.6) and (np.isnan(breakeven_latest) or breakeven_latest <= 2.6)

    if termp_score <= 40 and inflation_elevated:
        duration = "short/neutral — evita long nominal; preferisci qualità / TIPS"
    elif pot >= 55 and inflation_benign and termp_score >= 55:
        duration = "long (hedge) — disinflation + duration torna difensiva"
    else:
        duration = "neutral — bilancia rischio term premium vs ciclo"

    # Credit stance: HY OAS + HYG/LQD + debt stress
    hy = _sg(indicator_scores.get("hy_oas", {}).get("score", np.nan))
    hyg = _sg(indicator_scores.get("hyg_lqd_ratio", {}).get("score", np.nan))
    ds = _sg(indicator_scores.get("interest_to_receipts", {}).get("score", np.nan))

    if hy <= 40 or hyg <= 40 or ds <= 40:
        credit = "IG > HY — riduci rischio default / funding"
    elif hy >= 60 and hyg >= 60 and ds >= 50:
        credit = "opportunistic HY — con sizing e stop"
    else:
        credit = "neutral — qualità con selettività"

    # Hedges: USD vs Gold vs Cash-like (policy/fiscal) — mix regime + inflation level
    usd = _sg(indicator_scores.get("usd_index", {}).get("score", np.nan))
    dalio = _sg(block_scores.get("debt_fiscal", {}).get("score", np.nan))

    if dalio <= 40 and inflation_elevated:
        hedges = "Gold / real-asset tilt — rischio repressione / inflazione tollerata"
    elif usd <= 40 and cond <= 45:
        hedges = "USD / cash-like — funding stress"
    else:
        hedges = "mix leggero (cash-like + gold tattico)"

    return equity, duration, credit, hedges


# =========================
# MAIN
# =========================

def main():
    st.title("Global finance | Macro overview (Dalio-enhanced)")
    st.markdown(
        "<div class='muted'>Dashboard macro-finance: mantiene i “thermometers” di mercato ma aggiunge un layer Dalio su sostenibilità del debito, dominanza fiscale e vincolo esterno.</div>",
        unsafe_allow_html=True
    )

    # Sidebar controls
    st.sidebar.header("Impostazioni")
    if st.sidebar.button("🔄 Refresh data (clear cache)"):
        st.cache_data.clear()
        st.rerun()

    years_back = st.sidebar.slider("Orizzonte storico (anni)", 5, 30, 15)
    today = datetime.now(timezone.utc).date()
    start_date = (today - DateOffset(years=years_back)).date().isoformat()
    st.sidebar.markdown(f"**Data start:** {start_date}")

    fred_key = get_fred_api_key()
    if fred_key is None:
        st.sidebar.error("⚠️ Manca `FRED_API_KEY` nei secrets.")

    # Fetch data
    with st.spinner("Caricamento dati (FRED + yfinance)..."):
        fred = {
            # Price of time
            "real_10y": fetch_fred_series("DFII10", start_date),
            "nominal_10y": fetch_fred_series("DGS10", start_date),
            "dgs2": fetch_fred_series("DGS2", start_date),

            # Macro
            "breakeven_10y": fetch_fred_series("T10YIE", start_date),
            "cpi_index": fetch_fred_series("CPIAUCSL", start_date),
            "unemployment_rate": fetch_fred_series("UNRATE", start_date),

            # Conditions/Stress
            "hy_oas": fetch_fred_series("BAMLH0A0HYM2", start_date),
            "usd_fred": fetch_fred_series("DTWEXBGS", start_date),

            # Plumbing
            "fed_balance_sheet": fetch_fred_series("WALCL", start_date),
            "rrp": fetch_fred_series("RRPONTSYD", start_date),

            # Dalio: debt & fiscal
            "interest_payments": fetch_fred_series("A091RC1Q027SBEA", start_date),
            "federal_receipts": fetch_fred_series("FGRECPT", start_date),
            "deficit_gdp": fetch_fred_series("FYFSGDA188S", start_date),
            "term_premium_10y": fetch_fred_series("ACMTP10", start_date),

            # External
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

        # Direct FRED indicators (core)
        indicators["real_10y"] = fred["real_10y"]
        indicators["nominal_10y"] = fred["nominal_10y"]
        indicators["breakeven_10y"] = fred["breakeven_10y"]
        indicators["unemployment_rate"] = fred["unemployment_rate"]
        indicators["hy_oas"] = fred["hy_oas"]
        indicators["fed_balance_sheet"] = fred["fed_balance_sheet"]
        indicators["rrp"] = fred["rrp"]

        # Dalio indicators
        indicators["interest_payments"] = fred["interest_payments"]
        indicators["federal_receipts"] = fred["federal_receipts"]
        indicators["deficit_gdp"] = fred["deficit_gdp"]
        indicators["term_premium_10y"] = fred["term_premium_10y"]
        indicators["current_account_gdp"] = fred["current_account_gdp"]

        # Derived: interest / receipts ratio
        ip = indicators.get("interest_payments", pd.Series(dtype=float))
        fr = indicators.get("federal_receipts", pd.Series(dtype=float))
        if ip is not None and fr is not None and (not ip.empty) and (not fr.empty):
            join = ip.to_frame("interest").join(fr.to_frame("receipts"), how="inner").dropna()
            join = join[join["receipts"] != 0]
            indicators["interest_to_receipts"] = (join["interest"] / join["receipts"]).dropna()
        else:
            indicators["interest_to_receipts"] = pd.Series(dtype=float)

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

        # Cross confirmation
        indicators["world_equity"] = yf_map.get("URTH", pd.Series(dtype=float))
        indicators["duration_proxy_tlt"] = yf_map.get("TLT", pd.Series(dtype=float))
        indicators["gold"] = yf_map.get("GLD", pd.Series(dtype=float))

    # Score indicators (mode-aware)
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

    # Score blocks + global (6 blocchi core)
    block_scores = {}
    global_score = 0.0
    w_used = 0.0
    for bkey, binfo in BLOCKS.items():
        if bkey == "cross":
            vals = []
            for ikey in binfo["indicators"]:
                sc = indicator_scores.get(ikey, {}).get("score", np.nan)
                if not np.isnan(sc):
                    vals.append(sc)
            bscore = float(np.mean(vals)) if vals else np.nan
            block_scores[bkey] = {"score": bscore, "status": classify_status(bscore)}
            continue

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
    block_scores["GLOBAL"] = {"score": global_score, "status": global_status}

    # Data freshness
    latest_points = []
    for _, s in indicators.items():
        if s is not None and not s.empty:
            latest_points.append(s.index.max())
    data_max_date = max(latest_points) if latest_points else None

    # Tabs
    tabs = st.tabs([
        "Overview",
        "1) Price of time",
        "2) Macro cycle",
        "3) Conditions & stress",
        "4) Liquidity plumbing",
        "5) Debt & Fiscal (Dalio)",
        "6) External balance",
        "Cross confirmation",
        "What changed",
        "Report",
    ])

    # -------------------------
    # Overview
    # -------------------------
    with tabs[0]:
        left, right = st.columns([2, 1])

        with left:
            st.markdown("### Executive snapshot (con layer Dalio)")
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

            st.markdown(
                f"""
                <div class="kpi-grid">
                  <div class="kpi-card">
                    <div class="kpi-title">Global score (0–100) — 6 blocchi core</div>
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
                    <div class="kpi-title">Blocchi (score)</div>
                    <div class="kpi-sub">
                      {p1_s} Price of time: <b>{p1_v}</b><br/>
                      {p2_s} Macro: <b>{p2_v}</b><br/>
                      {p3_s} Conditions: <b>{p3_v}</b><br/>
                      {p4_s} Plumbing: <b>{p4_v}</b><br/>
                      {p5_s} Debt & Fiscal: <b>{p5_v}</b><br/>
                      {p6_s} External balance: <b>{p6_v}</b>
                    </div>
                  </div>

                  <div class="kpi-card">
                    <div class="kpi-title">Dalio “bridges” (1-liners)</div>
                    <div class="kpi-sub">
                      1) <b>Deficit ↑ → supply ↑ → term premium ↑ → duration perde</b><br/>
                      2) <b>Term premium ↑ + USD ↑ → tightening globale → risk-off</b><br/>
                      3) <b>Debt service ↑ → pressione politica → repressione finanziaria</b><br/>
                      4) <b>Repressione = real rates compressi → real assets hedge</b><br/>
                      5) <b>Current account deficit → dipendenza estera → vulnerabilità</b>
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
            st.markdown("<div class='tiny'>Tip: usa <b>Refresh data</b> in sidebar per forzare update.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("Come leggere score & soglie", expanded=False):
                st.markdown(
                    """
- Indicatori “market thermometers” (USD, spread, VIX, trend, real rates) → **z-score ~5Y** (`z5y`), clamp [-2,+2] → 0–100.
- Indicatori “stock/structural” (debito/fiscale/estero, term premium) → **percentile ~20Y** (`pct20y`) mappato in [-2,+2] → 0–100.
- Soglie: **>60 Risk-on**, **40–60 Neutrale**, **<40 Risk-off** (euristiche).
- Global score = media ponderata dei **6 blocchi core** (Cross è solo conferma).
- Nota: le “operating lines” combinano **regime (score)** + **livelli (latest CPI/breakeven)** per evitare confusione score≠livello.
                    """
                )

            usd_series = indicators.get("usd_index", pd.Series(dtype=float))
            if usd_series is None or usd_series.empty:
                st.warning("USD index vuoto: né DXY (yfinance) né proxy FRED risultano disponibili.")
            else:
                st.caption("USD index: se DXY manca su yfinance, la dashboard usa FRED DTWEXBGS come proxy.")

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
            else:
                cols = st.columns(len(row))
                for col, key in zip(cols, row):
                    with col:
                        s = indicators.get(key, pd.Series(dtype=float))
                        if s is None or s.empty:
                            st.warning(f"Dati mancanti per {INDICATOR_META[key]['label']}.")
                        else:
                            render_tile(key, s, indicator_scores)

    # -------------------------
    # Tabs: blocks
    # -------------------------
    with tabs[1]:
        render_block("price_of_time")
    with tabs[2]:
        render_block("macro")
    with tabs[3]:
        render_block("conditions")
    with tabs[4]:
        render_block("plumbing")
    with tabs[5]:
        render_block("debt_fiscal")
    with tabs[6]:
        render_block("external")
    with tabs[7]:
        render_block("cross")

    # -------------------------
    # What changed
    # -------------------------
    with tabs[8]:
        st.markdown("### What changed – frequency-aware")
        rows = []
        for key, meta in INDICATOR_META.items():
            s = indicators.get(key, pd.Series(dtype=float))
            if s is None or s.empty:
                continue

            deltas = compute_deltas(s)
            rows.append(
                {
                    "Indicatore": meta["label"],
                    "Scoring": meta.get("scoring_mode", "z5y"),
                    "Freq": deltas["freq"],
                    deltas["label_a"]: None if np.isnan(deltas["val_a"]) else round(deltas["val_a"], 2),
                    deltas["label_b"]: None if np.isnan(deltas["val_b"]) else round(deltas["val_b"], 2),
                    deltas["label_c"]: None if np.isnan(deltas["val_c"]) else round(deltas["val_c"], 2),
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
    with tabs[9]:
        st.markdown("### Report (opzionale) – Payload per ChatGPT")
        st.markdown("<div class='muted'>Payload copiabile: include blocchi Dalio (Debt/Fiscal + External) e modalità di scoring per evitare falsi segnali.</div>", unsafe_allow_html=True)

        generate_payload = st.button("Generate payload")

        if generate_payload:
            payload_lines = []
            payload_lines.append("macro_regime_payload_dalio:")
            payload_lines.append(f"  generated_at_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            payload_lines.append(f"  global_score: {0.0 if np.isnan(global_score) else round(global_score, 1)}")
            payload_lines.append(f"  global_status: {global_status}")
            payload_lines.append("  scoring_notes: \"market thermometers use z5y; structural constraints use pct20y\"")

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

                payload_lines.append(f"    - name: \"{meta['label']}\"")
                payload_lines.append(f"      key: \"{key}\"")
                payload_lines.append(f"      scoring_mode: \"{mode}\"")
                payload_lines.append(f"      freq: \"{deltas['freq']}\"")
                payload_lines.append(f"      latest_value: \"{fmt_value(latest, meta['unit'], meta.get('scale', 1.0))}\"")
                payload_lines.append(f"      score: {0.0 if np.isnan(score) else round(score, 1)}")
                payload_lines.append(f"      status: {status}")
                payload_lines.append(f"      change_a: \"{deltas['label_a']} {fmt_delta(deltas['val_a'])}\"")
                payload_lines.append(f"      change_b: \"{deltas['label_b']} {fmt_delta(deltas['val_b'])}\"")
                payload_lines.append(f"      change_c: \"{deltas['label_c']} {fmt_delta(deltas['val_c'])}\"")

            payload_text = "\n".join(payload_lines)
            st.code(payload_text, language="yaml")

            st.markdown("**Prompt suggerito (Dalio-aware):**")
            st.code(
                """
Sei un macro strategist multi-asset. Ricevi il payload YAML sopra (dashboard macro-finance Dalio-enhanced).

Task:
1) Ricostruisci il regime: separa “market thermometers” (USD/spread/VIX/trend/real rates) da “constraints” (debt service/deficit/term premium/external balance).
2) Spiega se c’è rischio di cambio regime strutturale (dominanza fiscale / repressione finanziaria / inflationary deleveraging).
3) Produci un report operativo ETF-based:
   - Equity exposure (risk budget)
   - Duration (short/neutral/long; nominal vs TIPS)
   - Credit risk (IG vs HY)
   - Hedges (USD, gold, cash-like)
   - 3–5 trigger da monitorare nelle prossime 2–6 settimane (soglie euristiche)
Tono concreto, prudente, implementabile.
                """.strip(),
                language="markdown"
            )


if __name__ == "__main__":
    main()
