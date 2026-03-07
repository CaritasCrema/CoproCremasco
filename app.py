"""
Budget Progetto - Monitoraggio Spese e Ore per Partner
Applicazione Streamlit con Google Sheets come backend — v2

Novità:
 - Calcolo automatico importo da ore × costo orario (per partner, configurabile)
 - Preventivo personalizzabile: caricamento Excel o inserimento manuale (solo coordinatore)
 - Vista quadro logico in sola lettura per ogni partner (solo le proprie voci)
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAZIONE PAGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Budget Progetto",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Fraunces', serif; }
.main-title { font-family:'Fraunces',serif; font-size:2.2rem; color:#1a365d; margin-bottom:0; }
.subtitle { color:#718096; font-size:0.9rem; margin-bottom:1.5rem; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#1a365d 0%,#2a4a7f 100%); }
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
[data-testid="stSidebar"] label { font-size:0.78rem !important; letter-spacing:0.06em; text-transform:uppercase; color:#a0aec0 !important; }
[data-testid="metric-container"] { background:white; border:1px solid #e2e8f0; border-radius:12px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
.stButton > button { background:linear-gradient(135deg,#2b6cb0,#1a365d); color:white !important; border:none; border-radius:8px; font-weight:600; width:100%; padding:0.55rem 1.2rem; }
.stButton > button:hover { opacity:0.88; }
.section-header { font-family:'Fraunces',serif; font-size:1.25rem; color:#1a365d; border-left:4px solid #2b6cb0; padding-left:10px; margin:1.8rem 0 1rem 0; }
.badge-fin { background:#ebf8ff; color:#2b6cb0; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.badge-cofin { background:#f0fff4; color:#276749; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.alert-success { background:#f0fff4; border-left:4px solid #38a169; padding:12px 16px; border-radius:8px; margin:1rem 0; color:#276749; font-size:0.9rem; }
.alert-info { background:#ebf8ff; border-left:4px solid #2b6cb0; padding:12px 16px; border-radius:8px; margin:1rem 0; color:#1a365d; font-size:0.9rem; }
.calc-box { background:#f7fafc; border:1px solid #bee3f8; border-radius:10px; padding:14px 18px; margin:0.5rem 0 1rem 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# COSTANTI
# ─────────────────────────────────────────────────────────────────────────────
PARTNERS_PASSWORDS = {
    "Fond. Madeo":               "madeo2024",
    "APG":                       "apg2024",
    "Bessimo":                   "bessimo2024",
    "Igea":                      "igea2024",
    "Servizi per l'accoglienza": "servizi2024",
    "ATS":                       "ats2024",
    "Ufficio di Piano":          "udp2024",
    "COORDINATORE":              "admin2024",
}

AREE_DEFAULT = {
    "AREA 1 - Rete Accoglienze": [
        "AZIONE 1.1 - Prima accoglienza",
        "AZIONE 1.2 - Housing Led",
        "AZIONE 1.3 - Una casa per noi",
        "AZIONE 1.4 - Dormitorio invernale",
    ],
    "AREA 2 - Bassa Soglia": [
        "AZIONE 2.1 - Centro diurno",
        "AZIONE 2.2 - Servizi estivi",
        "AZIONE 2.3 - Progetto Includiamo Sul Serio",
    ],
    "AREA 3 - Patti": ["AZIONE 3.1 - Patti"],
    "AREA 4 - Azioni di sistema": [
        "AZIONE 4.1 - Amministrazione di programma",
        "AZIONE 4.2 - Formazione e Comunicazione",
        "AZIONE 4.3 - Monitoraggio e Valutazione",
        "AZIONE 4.4 - Spese generali",
    ],
}

BUDGET_PREVENTIVO_DEFAULT = {
    "AZIONE 1.1 - Prima accoglienza":            (102200.0, 38325.0),
    "AZIONE 1.2 - Housing Led":                  (26400.0,  0.0),
    "AZIONE 1.3 - Una casa per noi":             (13000.0,  0.0),
    "AZIONE 1.4 - Dormitorio invernale":         (5000.0,   145904.18),
    "AZIONE 2.1 - Centro diurno":                (8205.9,   0.0),
    "AZIONE 2.2 - Servizi estivi":               (17525.68, 0.0),
    "AZIONE 2.3 - Progetto Includiamo Sul Serio":(21100.0,  20000.0),
    "AZIONE 3.1 - Patti":                        (27482.8,  0.0),
    "AZIONE 4.1 - Amministrazione di programma": (0.0,      2890.8),
    "AZIONE 4.2 - Formazione e Comunicazione":   (0.0,      3000.0),
    "AZIONE 4.3 - Monitoraggio e Valutazione":   (500.0,    500.0),
    "AZIONE 4.4 - Spese generali":               (6313.44,  0.0),
}

# Quadro logico dettagliato (sola lettura per i partner)
QUADRO_LOGICO_DEFAULT = [
    {"Area":"AREA 1","Azione":"AZIONE 1.1 - Prima accoglienza","Attività":"8 posti distrettuali di prima accoglienza","Costo":"TOT diaria","RisorseUmane":"educatore, coordinatore, assistente sociale","CostoUnitario":35.0,"Quantità":2920,"UdM":"giorni","TotBudget":102200.0,"Partner":"da definirsi","Finanziato":102200.0,"Cofinanziato":0.0},
    {"Area":"AREA 1","Azione":"AZIONE 1.1 - Prima accoglienza","Attività":"3 posti distrettuali - Fond. Madeo","Costo":"TOT diaria","RisorseUmane":"","CostoUnitario":35.0,"Quantità":1095,"UdM":"giorni","TotBudget":38325.0,"Partner":"Fond. Madeo","Finanziato":0.0,"Cofinanziato":38325.0},
    {"Area":"AREA 1","Azione":"AZIONE 1.2 - Housing Led","Attività":"4 appartamenti seconda accoglienza","Costo":"Utenze/affitto/spese condominiali","RisorseUmane":"educatore dedicato 6h/mese per appartamento","CostoUnitario":550.0,"Quantità":48,"UdM":"mesi","TotBudget":26400.0,"Partner":"da definirsi","Finanziato":26400.0,"Cofinanziato":0.0},
    {"Area":"AREA 1","Azione":"AZIONE 1.3 - Una casa per noi","Attività":"Rimborso spese 1 appartamento di accoglienza","Costo":"personale + costi gestione","RisorseUmane":"coordinatore, educatore","CostoUnitario":13000.0,"Quantità":12,"UdM":"mesi","TotBudget":13000.0,"Partner":"Fond. Madeo","Finanziato":13000.0,"Cofinanziato":0.0},
    {"Area":"AREA 1","Azione":"AZIONE 1.4 - Dormitorio invernale","Attività":"Rifugio San Martino - dormitorio invernale","Costo":"personale + costi e utenze","RisorseUmane":"coordinatore, operatori, volontari, educatore, AS, psicologo, addetto pulizie","CostoUnitario":145904.18,"Quantità":6,"UdM":"mesi","TotBudget":145904.18,"Partner":"Fond. Madeo","Finanziato":0.0,"Cofinanziato":145904.18},
    {"Area":"AREA 1","Azione":"AZIONE 1.4 - Dormitorio invernale","Attività":"Potenziamento extra Diocesi - fondo persone senza dimora","Costo":"personale + costi di gestione","RisorseUmane":"","CostoUnitario":5000.0,"Quantità":12,"UdM":"mesi","TotBudget":5000.0,"Partner":"da definirsi","Finanziato":5000.0,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.1 - Centro diurno","Attività":"Centro diurno - gestione e realizzazione","Costo":"personale","RisorseUmane":"educatore Liv 3S","CostoUnitario":24.09,"Quantità":90,"UdM":"h (45 sett.)","TotBudget":2168.1,"Partner":"Fond. Madeo","Finanziato":2168.1,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.1 - Centro diurno","Attività":"Centro diurno - gestione e realizzazione","Costo":"personale","RisorseUmane":"educatore Liv D3","CostoUnitario":24.69,"Quantità":90,"UdM":"h (45 sett.)","TotBudget":2222.1,"Partner":"APG","Finanziato":2222.1,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.1 - Centro diurno","Attività":"Centro diurno - gestione e realizzazione","Costo":"personale","RisorseUmane":"educatore Liv D2","CostoUnitario":25.73,"Quantità":90,"UdM":"h (45 sett.)","TotBudget":2315.7,"Partner":"Bessimo","Finanziato":2315.7,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.1 - Centro diurno","Attività":"Centro diurno - acquisti","Costo":"acquisti","RisorseUmane":"","CostoUnitario":1500.0,"Quantità":1,"UdM":"anno","TotBudget":1500.0,"Partner":"Fond. Madeo","Finanziato":1500.0,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.2 - Servizi estivi","Attività":"Servizio docce","Costo":"personale","RisorseUmane":"educatore Liv 3S","CostoUnitario":24.09,"Quantità":16,"UdM":"gg apertura","TotBudget":770.88,"Partner":"Fond. Madeo","Finanziato":770.88,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.2 - Servizi estivi","Attività":"Servizio docce","Costo":"personale","RisorseUmane":"educatore Liv D3","CostoUnitario":24.69,"Quantità":16,"UdM":"gg apertura","TotBudget":790.08,"Partner":"APG","Finanziato":790.08,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.2 - Servizi estivi","Attività":"Servizio docce","Costo":"personale","RisorseUmane":"educatore Liv D2","CostoUnitario":25.73,"Quantità":16,"UdM":"gg apertura","TotBudget":823.36,"Partner":"Bessimo","Finanziato":823.36,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.2 - Servizi estivi","Attività":"Dormitorio estivo - Locanda del Mantello","Costo":"personale","RisorseUmane":"coordinatore, educatore, volontari, AS, psicologo","CostoUnitario":24.09,"Quantità":504,"UdM":"h (126 gg)","TotBudget":12141.36,"Partner":"Fond. Madeo","Finanziato":12141.36,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.2 - Servizi estivi","Attività":"Dormitorio estivo - acquisti (vitto) e utenze","Costo":"acquisti e utenze","RisorseUmane":"","CostoUnitario":2000.0,"Quantità":1,"UdM":"anno","TotBudget":2000.0,"Partner":"Fond. Madeo","Finanziato":2000.0,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.3 - Progetto Includiamo Sul Serio","Attività":"Servizio drop In","Costo":"utenze, acquisti, affitto","RisorseUmane":"","CostoUnitario":21000.0,"Quantità":12,"UdM":"mesi","TotBudget":21100.0,"Partner":"Bessimo","Finanziato":21100.0,"Cofinanziato":0.0},
    {"Area":"AREA 2","Azione":"AZIONE 2.3 - Progetto Includiamo Sul Serio","Attività":"Servizio drop In","Costo":"personale","RisorseUmane":"4 educatori (1 coordinatore), 2 medici, 2 infermieri, 1 psicologo, 1 mediatore, 1 ASA, 1 legale, 1 AS","CostoUnitario":20000.0,"Quantità":12,"UdM":"mesi","TotBudget":20000.0,"Partner":"Bessimo","Finanziato":0.0,"Cofinanziato":20000.0},
    {"Area":"AREA 3","Azione":"AZIONE 3.1 - Patti","Attività":"Budget per la realizzazione dei patti","Costo":"budget patti","RisorseUmane":"","CostoUnitario":20000.0,"Quantità":12,"UdM":"mesi","TotBudget":20000.0,"Partner":"da definirsi","Finanziato":20000.0,"Cofinanziato":0.0},
    {"Area":"AREA 3","Azione":"AZIONE 3.1 - Patti","Attività":"Personale tutor patti","Costo":"tutor","RisorseUmane":"1 educatore + 1 psicologo + 1 AS (6 ore/mese ciascuno)","CostoUnitario":26.33,"Quantità":72,"UdM":"ore","TotBudget":5482.8,"Partner":"Fond. Madeo","Finanziato":5482.8,"Cofinanziato":0.0},
    {"Area":"AREA 4","Azione":"AZIONE 4.1 - Amministrazione di programma","Attività":"Costo amministrativo di programma","Costo":"personale","RisorseUmane":"1 amministrativo","CostoUnitario":24.09,"Quantità":120,"UdM":"ore","TotBudget":2890.8,"Partner":"ATS","Finanziato":0.0,"Cofinanziato":2890.8},
    {"Area":"AREA 4","Azione":"AZIONE 4.2 - Formazione e Comunicazione","Attività":"Formazione annuale operatori + comunicazione","Costo":"formazione e comunicazione","RisorseUmane":"","CostoUnitario":3000.0,"Quantità":12,"UdM":"mesi","TotBudget":3000.0,"Partner":"Ufficio di Piano","Finanziato":0.0,"Cofinanziato":3000.0},
    {"Area":"AREA 4","Azione":"AZIONE 4.3 - Monitoraggio e Valutazione","Attività":"Ingaggio ente esterno monitoraggio","Costo":"monitoraggio e valutazione","RisorseUmane":"","CostoUnitario":1000.0,"Quantità":12,"UdM":"mesi","TotBudget":1000.0,"Partner":"ATS","Finanziato":500.0,"Cofinanziato":500.0},
    {"Area":"AREA 4","Azione":"AZIONE 4.4 - Spese generali","Attività":"Spese generali personale (10% costi personale)","Costo":"spese generali","RisorseUmane":"","CostoUnitario":6313.44,"Quantità":1,"UdM":"anno","TotBudget":6313.44,"Partner":"ATS","Finanziato":6313.44,"Cofinanziato":0.0},
]

TIPI_COSTO = [
    "Personale - Ore lavorate",
    "Spese - Utenze",
    "Spese - Vitto/Alloggio",
    "Spese - Acquisti",
    "Spese - Affitto",
    "Spese - Altro",
]

MESI = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
        "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]

ANNO = 2025

INTESTAZIONE_SHEET = [
    "Timestamp","Partner","Mese","Anno","Area","Azione",
    "Tipo Costo","Descrizione","Ore","Costo Orario (€)","Importo (€)",
    "Finanziamento/Cofinanziamento","Note"
]

SHEET_COSTI  = "CostiOrari"
SHEET_PREV   = "Preventivo"

# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_gsheet_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        raw_key = creds_dict.get("private_key", "")
        if raw_key:
            lines   = [l.strip() for l in raw_key.strip().splitlines()]
            header  = next((l for l in lines if "BEGIN" in l), "-----BEGIN PRIVATE KEY-----")
            footer  = next((l for l in lines if "END"   in l), "-----END PRIVATE KEY-----")
            body    = "".join(l for l in lines if "BEGIN" not in l and "END" not in l and l)
            chunked = "\n".join(body[i:i+64] for i in range(0, len(body), 64))
            creds_dict["private_key"] = f"{header}\n{chunked}\n{footer}\n"
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Errore connessione Google Sheets: {e}")
        return None

def get_worksheets(client):
    try:
        sh = client.open_by_key(st.secrets["google_sheet_id"])
        def get_or_create(name, rows, cols, header=None):
            try:
                return sh.worksheet(name)
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(title=name, rows=rows, cols=cols)
                if header:
                    ws.append_row(header)
                return ws
        ws_rend  = get_or_create("Rendicontazione", 5000, 15, INTESTAZIONE_SHEET)
        ws_costi = get_or_create(SHEET_COSTI, 500, 5, ["Partner","FiguraProfessionale","CostoOrario"])
        ws_prev  = get_or_create(SHEET_PREV, 200, 5, ["Azione","PreventivoFinanziato","PreventivoCofinanziato"])
        return ws_rend, ws_costi, ws_prev
    except Exception as e:
        st.error(f"❌ Errore apertura fogli: {e}")
        return None, None, None

def carica_df(ws, cols):
    try:
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=cols)
    except Exception as e:
        st.error(f"Errore lettura: {e}")
        return pd.DataFrame(columns=cols)

def salva_riga(ws, riga):
    try:
        ws.append_row(riga, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def carica_costi_orari(ws_costi):
    df = carica_df(ws_costi, ["Partner","FiguraProfessionale","CostoOrario"])
    result = {}
    for _, r in df.iterrows():
        try:
            result[(str(r["Partner"]).strip(), str(r["FiguraProfessionale"]).strip())] = float(r["CostoOrario"])
        except:
            pass
    return result

def figure_per_partner(costi_orari, partner):
    return [fig for (p, fig) in costi_orari.keys() if p == partner]

def carica_preventivo(ws_prev):
    df = carica_df(ws_prev, ["Azione","PreventivoFinanziato","PreventivoCofinanziato"])
    if df.empty:
        return dict(BUDGET_PREVENTIVO_DEFAULT)
    result = {}
    for _, r in df.iterrows():
        try:
            result[str(r["Azione"]).strip()] = (
                float(r["PreventivoFinanziato"]),
                float(r["PreventivoCofinanziato"])
            )
        except:
            pass
    return result if result else dict(BUDGET_PREVENTIVO_DEFAULT)

def aree_da_preventivo(budget):
    aree = {}
    for azione in budget.keys():
        try:
            num = azione.split("AZIONE")[1].strip().split(".")[0].strip()
            label = next((k for k in AREE_DEFAULT if k.startswith(f"AREA {num}")), f"AREA {num}")
        except:
            label = "Altre azioni"
        aree.setdefault(label, [])
        if azione not in aree[label]:
            aree[label].append(azione)
    return aree if aree else AREE_DEFAULT

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "partner" not in st.session_state:
    st.session_state.partner = None

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
def mostra_login():
    _, col_m, _ = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="main-title" style="text-align:center">📊 Budget Progetto</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle" style="text-align:center">Monitoraggio spese e ore per partner</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("#### Accedi al tuo spazio")
            partner_sel = st.selectbox("Seleziona il tuo ente", list(PARTNERS_PASSWORDS.keys()))
            password    = st.text_input("Password", type="password")
            if st.button("Accedi →"):
                if PARTNERS_PASSWORDS.get(partner_sel) == password:
                    st.session_state.logged_in = True
                    st.session_state.partner   = partner_sel
                    st.rerun()
                else:
                    st.error("Password errata. Contatta il coordinatore.")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def mostra_sidebar():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.partner}")
        st.markdown("---")
        if st.session_state.partner == "COORDINATORE":
            voci = ["📥 Inserimento", "📊 Cruscotto", "📋 Quadro logico", "⚙️ Gestione preventivo"]
        else:
            voci = ["📥 Inserimento", "📋 Quadro logico"]
        pagina = st.radio("Navigazione", voci, label_visibility="collapsed")
        st.markdown("---")
        if st.button("🔓 Esci"):
            st.session_state.logged_in = False
            st.session_state.partner   = None
            st.rerun()
    return pagina

# ─────────────────────────────────────────────────────────────────────────────
# PAGINA INSERIMENTO
# ─────────────────────────────────────────────────────────────────────────────
def pagina_inserimento(ws_rend, ws_costi, ws_prev, partner):
    st.markdown('<div class="main-title">📥 Inserimento mensile</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">Ente: <strong>{partner}</strong> — Anno {ANNO}</div>', unsafe_allow_html=True)

    budget  = carica_preventivo(ws_prev)
    aree    = aree_da_preventivo(budget)
    co      = carica_costi_orari(ws_costi)

    col1, col2 = st.columns(2)
    with col1:
        mese = st.selectbox("Mese di riferimento", MESI, index=date.today().month - 1)
    with col2:
        area_sel = st.selectbox("Area", list(aree.keys()))
    azione_sel = st.selectbox("Azione", aree[area_sel])

    st.markdown('<div class="section-header">Voce di spesa / ore</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        tipo_costo = st.selectbox("Tipo di costo", TIPI_COSTO)
    with col4:
        fin_cofin = st.radio("Imputazione", ["Finanziamento", "Cofinanziamento"], horizontal=True)

    descrizione = st.text_input("Descrizione voce", placeholder="es. Mario Rossi - Educatore")

    ore = 0.0
    costo_orario_usato = 0.0
    importo = 0.0

    if "Personale" in tipo_costo:
        figure = figure_per_partner(co, partner)
        col5, col6, col7 = st.columns(3)

        with col5:
            ore = st.number_input("Ore lavorate nel mese", min_value=0.0, step=0.5, format="%.1f")

        with col6:
            if figure:
                scelta = st.selectbox("Figura professionale", ["— seleziona —"] + figure)
                if scelta != "— seleziona —":
                    costo_orario_usato = co.get((partner, scelta), 0.0)
                    st.caption(f"Tariffa configurata: € {costo_orario_usato:.2f}/h")
                else:
                    costo_orario_usato = st.number_input("Oppure inserisci costo orario (€/h)",
                                                          min_value=0.0, step=0.01, format="%.2f")
            else:
                costo_orario_usato = st.number_input(
                    "Costo orario (€/h)", min_value=0.0, step=0.01, format="%.2f",
                    help="Il coordinatore può pre-configurare le tariffe in '⚙️ Gestione preventivo'")

        importo_calc = round(ore * costo_orario_usato, 2)

        with col7:
            st.markdown(f"""
            <div class='calc-box'>
              <small style='color:#718096;text-transform:uppercase;letter-spacing:.05em;font-size:0.75rem'>Importo calcolato</small><br>
              <span style='font-size:1.6rem;font-weight:700;color:#1a365d'>€ {importo_calc:,.2f}</span><br>
              <small style='color:#a0aec0'>{ore:.1f} h × € {costo_orario_usato:.2f}/h</small>
            </div>
            """, unsafe_allow_html=True)

        importo = st.number_input(
            "Importo (€) — modificabile se necessario",
            min_value=0.0, value=float(importo_calc), step=0.01, format="%.2f",
            help="Il valore è calcolato automaticamente ma puoi correggerlo.")
    else:
        importo = st.number_input("Importo (€)", min_value=0.0, step=0.01, format="%.2f")

    note = st.text_area("Note (facoltativo)", placeholder="Riferimenti, giustificativi...", height=80)

    prev_fin, prev_cofin = budget.get(azione_sel, (0, 0))
    with st.expander("📋 Preventivo per questa azione"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Preventivo finanziato",   f"€ {prev_fin:,.2f}")
        c2.metric("Preventivo cofinanziato", f"€ {prev_cofin:,.2f}")
        c3.metric("Totale azione",           f"€ {prev_fin + prev_cofin:,.2f}")

    st.markdown("---")
    if st.button("💾 Salva voce"):
        if not descrizione.strip():
            st.warning("Inserisci una descrizione per la voce.")
            return
        if importo == 0 and ore == 0:
            st.warning("Inserisci almeno un importo o delle ore.")
            return
        riga = [
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            partner, mese, ANNO, area_sel, azione_sel,
            tipo_costo, descrizione.strip(),
            ore, costo_orario_usato, importo,
            fin_cofin, note.strip(),
        ]
        if salva_riga(ws_rend, riga):
            st.markdown('<div class="alert-success">✅ Voce salvata su Google Sheets!</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">📋 Le tue voci inserite</div>', unsafe_allow_html=True)
    df = carica_df(ws_rend, INTESTAZIONE_SHEET)
    if not df.empty:
        df_p = df[df["Partner"] == partner].copy()
        if not df_p.empty:
            df_p["Importo (€)"] = pd.to_numeric(df_p["Importo (€)"], errors="coerce").map(
                lambda x: f"€ {x:,.2f}" if pd.notna(x) else "")
            st.dataframe(
                df_p[["Mese","Azione","Tipo Costo","Descrizione",
                      "Ore","Costo Orario (€)","Importo (€)","Finanziamento/Cofinanziamento"]],
                use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna voce ancora inserita da questo ente.")
    else:
        st.info("Nessuna voce ancora inserita.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGINA QUADRO LOGICO (sola lettura)
# ─────────────────────────────────────────────────────────────────────────────
def pagina_quadro_logico(partner):
    is_coord = (partner == "COORDINATORE")
    st.markdown('<div class="main-title">📋 Quadro Logico</div>', unsafe_allow_html=True)
    if is_coord:
        st.markdown('<div class="subtitle">Vista completa del preventivo per tutte le voci e i partner</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="subtitle">Voci di competenza di <strong>{partner}</strong> — sola lettura</div>', unsafe_allow_html=True)

    df_ql = pd.DataFrame(QUADRO_LOGICO_DEFAULT)
    if not is_coord:
        df_ql = df_ql[df_ql["Partner"].str.strip() == partner].copy()
        if df_ql.empty:
            st.info(f"Nessuna voce del quadro logico risulta associata a '{partner}'.\nContatta il coordinatore se ritieni ci sia un errore.")
            return

    # KPI
    tot_fin   = df_ql["Finanziato"].sum()
    tot_cofin = df_ql["Cofinanziato"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("💶 Finanziato assegnato",    f"€ {tot_fin:,.2f}")
    c2.metric("🤝 Cofinanziato assegnato",  f"€ {tot_cofin:,.2f}")
    c3.metric("📊 Totale",                  f"€ {tot_fin + tot_cofin:,.2f}")

    for area in df_ql["Area"].unique():
        st.markdown(f'<div class="section-header">{area}</div>', unsafe_allow_html=True)
        df_a = df_ql[df_ql["Area"] == area].copy()
        df_a["CostoUnitario"] = df_a["CostoUnitario"].map(lambda x: f"€ {x:,.2f}")
        df_a["TotBudget"]     = df_a["TotBudget"].map(lambda x: f"€ {x:,.2f}")
        df_a["Finanziato"]    = df_a["Finanziato"].map(lambda x: f"€ {x:,.2f}")
        df_a["Cofinanziato"]  = df_a["Cofinanziato"].map(lambda x: f"€ {x:,.2f}")
        cols = ["Azione","Attività","Costo","RisorseUmane","CostoUnitario",
                "Quantità","UdM","TotBudget","Finanziato","Cofinanziato"]
        if is_coord:
            cols.insert(8, "Partner")
        st.dataframe(df_a[cols], use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGINA GESTIONE PREVENTIVO (solo coordinatore)
# ─────────────────────────────────────────────────────────────────────────────
def pagina_gestione_preventivo(ws_costi, ws_prev):
    st.markdown('<div class="main-title">⚙️ Gestione preventivo</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Personalizza budget per azione e costi orari per partner</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 Carica da Excel", "✏️ Modifica manuale", "💼 Costi orari partner"])

    # ── TAB 1: Excel ──────────────────────────────────────────────────────
    with tab1:
        st.markdown('<div class="section-header">Importa preventivo da file Excel</div>', unsafe_allow_html=True)
        st.markdown("""<div class='alert-info'>
        Il file Excel deve avere almeno 3 colonne:<br>
        <strong>Azione</strong> &nbsp;|&nbsp; <strong>PreventivoFinanziato</strong> &nbsp;|&nbsp; <strong>PreventivoCofinanziato</strong>
        </div>""", unsafe_allow_html=True)

        uploaded = st.file_uploader("Carica file Excel (.xlsx)", type=["xlsx","xls"])
        if uploaded:
            try:
                df_xl = pd.read_excel(uploaded)
                st.write("**Anteprima file:**")
                st.dataframe(df_xl.head(8), use_container_width=True, hide_index=True)

                col_az  = st.selectbox("Colonna Azione",                 df_xl.columns.tolist(), key="xl_az")
                col_fin = st.selectbox("Colonna Preventivo Finanziato",  df_xl.columns.tolist(), key="xl_fin")
                col_cof = st.selectbox("Colonna Preventivo Cofinanziato",df_xl.columns.tolist(), key="xl_cof")

                if st.button("💾 Importa nel sistema"):
                    ws_prev.clear()
                    ws_prev.append_row(["Azione","PreventivoFinanziato","PreventivoCofinanziato"])
                    n = 0
                    for _, row in df_xl.iterrows():
                        az = str(row[col_az]).strip()
                        if not az or az.lower() == "nan":
                            continue
                        try:
                            fin = float(str(row[col_fin]).replace("€","").replace(",",".").strip() or 0)
                            cof = float(str(row[col_cof]).replace("€","").replace(",",".").strip() or 0)
                        except:
                            fin, cof = 0.0, 0.0
                        ws_prev.append_row([az, fin, cof])
                        n += 1
                    st.success(f"✅ {n} azioni importate nel preventivo!")
            except Exception as e:
                st.error(f"Errore lettura Excel: {e}")

    # ── TAB 2: manuale ────────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="section-header">Preventivo attuale</div>', unsafe_allow_html=True)
        budget = carica_preventivo(ws_prev)
        df_prev = pd.DataFrame([
            {"Azione": k, "Finanziato (€)": v[0], "Cofinanziato (€)": v[1],
             "Totale (€)": v[0] + v[1]}
            for k, v in budget.items()
        ])
        st.dataframe(df_prev, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-header">Aggiungi / modifica azione</div>', unsafe_allow_html=True)
        azione_n = st.text_input("Nome azione (es. AZIONE 5.1 - Nuova attività)")
        c1, c2 = st.columns(2)
        with c1:
            fin_n   = st.number_input("Preventivo finanziato (€)",   min_value=0.0, step=100.0, format="%.2f", key="mn_fin")
        with c2:
            cofin_n = st.number_input("Preventivo cofinanziato (€)", min_value=0.0, step=100.0, format="%.2f", key="mn_cof")

        if st.button("💾 Salva azione"):
            if not azione_n.strip():
                st.warning("Inserisci il nome dell'azione.")
            else:
                records = ws_prev.get_all_records()
                found   = False
                for i, r in enumerate(records, start=2):
                    if str(r.get("Azione","")).strip() == azione_n.strip():
                        ws_prev.update(f"A{i}:C{i}", [[azione_n.strip(), fin_n, cofin_n]])
                        found = True
                        break
                if not found:
                    ws_prev.append_row([azione_n.strip(), fin_n, cofin_n])
                st.success(f"✅ Azione '{azione_n}' salvata!")
                st.rerun()

    # ── TAB 3: costi orari ────────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="section-header">Tariffe orarie configurate</div>', unsafe_allow_html=True)
        df_co = carica_df(ws_costi, ["Partner","FiguraProfessionale","CostoOrario"])
        if not df_co.empty:
            df_co["CostoOrario"] = pd.to_numeric(df_co["CostoOrario"], errors="coerce").map(
                lambda x: f"€ {x:.2f}/h" if pd.notna(x) else "")
            st.dataframe(df_co, use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna tariffa ancora configurata.")

        st.markdown('<div class="section-header">Aggiungi / modifica tariffa</div>', unsafe_allow_html=True)
        p_co  = st.selectbox("Partner", [p for p in PARTNERS_PASSWORDS if p != "COORDINATORE"])
        fig_co = st.text_input("Figura professionale (es. Educatore Liv.3S)")
        tar_co = st.number_input("Costo orario (€/h)", min_value=0.0, step=0.01, format="%.2f")

        if st.button("💾 Salva tariffa"):
            if not fig_co.strip():
                st.warning("Inserisci il nome della figura professionale.")
            elif tar_co <= 0:
                st.warning("Il costo orario deve essere maggiore di 0.")
            else:
                records = ws_costi.get_all_records()
                found   = False
                for i, r in enumerate(records, start=2):
                    if str(r.get("Partner","")).strip() == p_co and \
                       str(r.get("FiguraProfessionale","")).strip() == fig_co.strip():
                        ws_costi.update(f"A{i}:C{i}", [[p_co, fig_co.strip(), tar_co]])
                        found = True
                        break
                if not found:
                    ws_costi.append_row([p_co, fig_co.strip(), tar_co])
                st.success(f"✅ {p_co} — {fig_co} → € {tar_co:.2f}/h")
                st.rerun()

        if not df_co.empty:
            st.markdown('<div class="section-header">Elimina tariffa</div>', unsafe_allow_html=True)
            df_co_raw = carica_df(ws_costi, ["Partner","FiguraProfessionale","CostoOrario"])
            opzioni = [f"{r['Partner']} — {r['FiguraProfessionale']}" for _, r in df_co_raw.iterrows()]
            da_el   = st.selectbox("Seleziona tariffa da eliminare", opzioni)
            if st.button("🗑️ Elimina"):
                idx = opzioni.index(da_el) + 2
                ws_costi.delete_rows(idx)
                st.success("Tariffa eliminata.")
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGINA CRUSCOTTO
# ─────────────────────────────────────────────────────────────────────────────
def pagina_cruscotto(ws_rend, ws_prev):
    st.markdown('<div class="main-title">📊 Cruscotto Coordinatore</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Avanzamento rendicontazione vs preventivo annuale</div>', unsafe_allow_html=True)

    df     = carica_df(ws_rend, INTESTAZIONE_SHEET)
    budget = carica_preventivo(ws_prev)

    if df.empty:
        st.info("Nessun dato ancora inserito dai partner.")
        return

    df["Importo (€)"] = pd.to_numeric(df["Importo (€)"], errors="coerce").fillna(0)
    df["Ore"]         = pd.to_numeric(df["Ore"],         errors="coerce").fillna(0)

    tot_fp = sum(v[0] for v in budget.values())
    tot_cp = sum(v[1] for v in budget.values())
    tot_fr = df[df["Finanziamento/Cofinanziamento"] == "Finanziamento"]["Importo (€)"].sum()
    tot_cr = df[df["Finanziamento/Cofinanziamento"] == "Cofinanziamento"]["Importo (€)"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💶 Finanziamento rendicontato",
              f"€ {tot_fr:,.2f}", delta=f"{tot_fr/tot_fp*100:.1f}% del preventivo" if tot_fp else "")
    c2.metric("🤝 Cofinanziamento rendicontato",
              f"€ {tot_cr:,.2f}", delta=f"{tot_cr/tot_cp*100:.1f}% del preventivo" if tot_cp else "")
    c3.metric("🕐 Ore totali inserite", f"{df['Ore'].sum():,.0f} h")
    c4.metric("📝 Voci inserite", len(df))

    st.markdown('<div class="section-header">Avanzamento per Azione</div>', unsafe_allow_html=True)
    for azione, (pf, pc) in budget.items():
        df_az = df[df["Azione"] == azione]
        rf    = df_az[df_az["Finanziamento/Cofinanziamento"] == "Finanziamento"]["Importo (€)"].sum()
        rc    = df_az[df_az["Finanziamento/Cofinanziamento"] == "Cofinanziamento"]["Importo (€)"].sum()
        perc_f = (rf / pf * 100) if pf > 0 else 0
        perc_c = (rc / pc * 100) if pc > 0 else 0

        with st.expander(f"**{azione}**  —  Fin: {perc_f:.1f}%  |  Cofin: {perc_c:.1f}%"):
            ca, cb = st.columns(2)
            for col, label, rend, prev, perc, badge in [
                (ca, "FINANZIAMENTO",   rf, pf, perc_f, "badge-fin"),
                (cb, "COFINANZIAMENTO", rc, pc, perc_c, "badge-cofin"),
            ]:
                with col:
                    color = "#38a169" if perc < 80 else ("#f59e0b" if perc < 100 else "#e53e3e")
                    st.markdown(f"<span class='{badge}'>{label}</span>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style='margin:8px 0;'>
                      <div style='background:#e2e8f0;border-radius:999px;height:10px;'>
                        <div style='width:{min(perc,100):.1f}%;background:{color};height:100%;border-radius:999px;'></div>
                      </div>
                      <small style='color:#718096'>€ {rend:,.2f} / € {prev:,.2f}</small>
                    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Dettaglio voci</div>', unsafe_allow_html=True)
    col_fp, col_fm = st.columns(2)
    with col_fp:
        fp = st.selectbox("Partner", ["Tutti"] + [p for p in PARTNERS_PASSWORDS if p != "COORDINATORE"])
    with col_fm:
        fm = st.selectbox("Mese", ["Tutti"] + MESI)

    df_v = df.copy()
    if fp != "Tutti": df_v = df_v[df_v["Partner"] == fp]
    if fm != "Tutti": df_v = df_v[df_v["Mese"] == fm]

    if not df_v.empty:
        df_v["Importo (€)"] = df_v["Importo (€)"].map(lambda x: f"€ {x:,.2f}")
        st.dataframe(df_v[["Timestamp","Partner","Mese","Azione","Tipo Costo","Descrizione",
                            "Ore","Costo Orario (€)","Importo (€)","Finanziamento/Cofinanziamento","Note"]],
                     use_container_width=True, hide_index=True)
        csv = df_v.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Esporta CSV", data=csv, file_name="rendicontazione.csv", mime="text/csv")
    else:
        st.info("Nessuna voce per i filtri selezionati.")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    mostra_login()
else:
    pagina = mostra_sidebar()
    client = get_gsheet_client()
    if client:
        ws_rend, ws_costi, ws_prev = get_worksheets(client)
        if ws_rend:
            if   pagina == "📊 Cruscotto":
                pagina_cruscotto(ws_rend, ws_prev)
            elif pagina == "📋 Quadro logico":
                pagina_quadro_logico(st.session_state.partner)
            elif pagina == "⚙️ Gestione preventivo":
                pagina_gestione_preventivo(ws_costi, ws_prev)
            else:
                pagina_inserimento(ws_rend, ws_costi, ws_prev, st.session_state.partner)
    else:
        st.error("Impossibile connettersi a Google Sheets. Verifica i secrets.")
