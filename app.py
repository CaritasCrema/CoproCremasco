"""
Budget Progetto - Monitoraggio Spese e Ore per Partner
Applicazione Streamlit con Google Sheets come backend
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials
import json

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

.main-title {
    font-family: 'Fraunces', serif;
    font-size: 2.2rem;
    color: #1a365d;
    margin-bottom: 0;
}
.subtitle { color: #718096; font-size: 0.9rem; margin-bottom: 1.5rem; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a365d 0%, #2a4a7f 100%);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] label {
    font-size: 0.78rem !important;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #a0aec0 !important;
}

[data-testid="metric-container"] {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.stButton > button {
    background: linear-gradient(135deg, #2b6cb0, #1a365d);
    color: white !important;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    width: 100%;
    padding: 0.55rem 1.2rem;
}
.stButton > button:hover { opacity: 0.88; }

.section-header {
    font-family: 'Fraunces', serif;
    font-size: 1.25rem;
    color: #1a365d;
    border-left: 4px solid #2b6cb0;
    padding-left: 10px;
    margin: 1.8rem 0 1rem 0;
}
.badge-fin {
    background: #ebf8ff; color: #2b6cb0;
    padding: 2px 10px; border-radius: 20px; font-size: 0.78rem; font-weight:600;
}
.badge-cofin {
    background: #f0fff4; color: #276749;
    padding: 2px 10px; border-radius: 20px; font-size: 0.78rem; font-weight:600;
}
.alert-warning {
    background: #fffbeb; border-left: 4px solid #f59e0b;
    padding: 12px 16px; border-radius: 8px; margin: 1rem 0;
    color: #92400e; font-size: 0.9rem;
}
.alert-success {
    background: #f0fff4; border-left: 4px solid #38a169;
    padding: 12px 16px; border-radius: 8px; margin: 1rem 0;
    color: #276749; font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DATI PROGETTO — Budget preventivo estratto dal quadro logico
# ─────────────────────────────────────────────────────────────────────────────
PARTNERS_PASSWORDS = {
    "Fond. Madeo":              "madeo2024",
    "APG":                      "apg2024",
    "Bessimo":                  "bessimo2024",
    "Igea":                     "igea2024",
    "Servizi per l'accoglienza":"servizi2024",
    "ATS":                      "ats2024",
    "Ufficio di Piano":         "udp2024",
    "COORDINATORE":             "admin2024",   # accesso completo
}

AREE = {
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
    "AREA 3 - Patti": [
        "AZIONE 3.1 - Patti",
    ],
    "AREA 4 - Azioni di sistema": [
        "AZIONE 4.1 - Amministrazione di programma",
        "AZIONE 4.2 - Formazione e Comunicazione",
        "AZIONE 4.3 - Monitoraggio e Valutazione",
        "AZIONE 4.4 - Spese generali",
    ],
}

# Budget preventivo per azione: {azione: (finanziato, cofinanziato)}
BUDGET_PREVENTIVO = {
    "AZIONE 1.1 - Prima accoglienza":           (102200.0,  38325.0),
    "AZIONE 1.2 - Housing Led":                 (26400.0,   0.0),
    "AZIONE 1.3 - Una casa per noi":            (13000.0,   0.0),
    "AZIONE 1.4 - Dormitorio invernale":        (5000.0,    145904.18),
    "AZIONE 2.1 - Centro diurno":               (8205.9,    0.0),
    "AZIONE 2.2 - Servizi estivi":              (17525.68,  0.0),
    "AZIONE 2.3 - Progetto Includiamo Sul Serio":(21100.0,  20000.0),
    "AZIONE 3.1 - Patti":                       (27482.8,   0.0),
    "AZIONE 4.1 - Amministrazione di programma":(0.0,       2890.8),
    "AZIONE 4.2 - Formazione e Comunicazione":  (0.0,       3000.0),
    "AZIONE 4.3 - Monitoraggio e Valutazione":  (500.0,     500.0),
    "AZIONE 4.4 - Spese generali":              (6313.44,   0.0),
}

TIPI_COSTO = ["Personale - Ore lavorate", "Spese - Utenze", "Spese - Vitto/Alloggio",
              "Spese - Acquisti", "Spese - Affitto", "Spese - Altro"]

MESI = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
        "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]

ANNO = 2025

INTESTAZIONE_SHEET = [
    "Timestamp", "Partner", "Mese", "Anno", "Area", "Azione",
    "Tipo Costo", "Descrizione", "Ore", "Importo (€)", "Finanziamento/Cofinanziamento", "Note"
]

# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE SHEETS — connessione
# ─────────────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_gsheet_client():
    """Crea client Google Sheets dalle credenziali nei secrets di Streamlit."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Errore connessione Google Sheets: {e}")
        return None

def get_worksheet(client, sheet_name="Rendicontazione"):
    """Apre il Google Sheet e restituisce il foglio 'Rendicontazione'."""
    try:
        spreadsheet_id = st.secrets["google_sheet_id"]
        sh = client.open_by_key(spreadsheet_id)
        try:
            ws = sh.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=sheet_name, rows=2000, cols=15)
            ws.append_row(INTESTAZIONE_SHEET)
        return ws
    except Exception as e:
        st.error(f"❌ Errore apertura foglio: {e}")
        return None

def carica_dati(ws):
    """Carica tutte le righe dal foglio come DataFrame."""
    try:
        records = ws.get_all_records()
        if not records:
            return pd.DataFrame(columns=INTESTAZIONE_SHEET)
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Errore lettura dati: {e}")
        return pd.DataFrame(columns=INTESTAZIONE_SHEET)

def salva_riga(ws, riga: list):
    """Aggiunge una riga al foglio Google Sheets."""
    try:
        ws.append_row(riga, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False

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
    col_c, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="main-title" style="text-align:center">📊 Budget Progetto</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle" style="text-align:center">Monitoraggio spese e ore per partner</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("#### Accedi al tuo spazio")
            partner_sel = st.selectbox("Seleziona il tuo ente", list(PARTNERS_PASSWORDS.keys()))
            password = st.text_input("Password", type="password")
            if st.button("Accedi →"):
                if PARTNERS_PASSWORDS.get(partner_sel) == password:
                    st.session_state.logged_in = True
                    st.session_state.partner = partner_sel
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
            pagina = st.radio("Navigazione", ["📥 Inserimento", "📊 Cruscotto coordinatore"], label_visibility="collapsed")
        else:
            pagina = "📥 Inserimento"
            st.markdown("**Modalità:** Inserimento dati mensile")
        st.markdown("---")
        if st.button("🔓 Esci"):
            st.session_state.logged_in = False
            st.session_state.partner = None
            st.rerun()
    return pagina

# ─────────────────────────────────────────────────────────────────────────────
# PAGINA INSERIMENTO
# ─────────────────────────────────────────────────────────────────────────────
def pagina_inserimento(ws, partner):
    st.markdown('<div class="main-title">📥 Inserimento mensile</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">Ente: <strong>{partner}</strong> — Anno {ANNO}</div>', unsafe_allow_html=True)

    # Selezione mese e area
    col1, col2 = st.columns(2)
    with col1:
        mese = st.selectbox("Mese di riferimento", MESI, index=date.today().month - 1)
    with col2:
        area_sel = st.selectbox("Area", list(AREE.keys()))

    azione_sel = st.selectbox("Azione", AREE[area_sel])

    st.markdown('<div class="section-header">Voce di spesa / ore</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        tipo_costo = st.selectbox("Tipo di costo", TIPI_COSTO)
    with col4:
        fin_cofin = st.radio("Imputazione", ["Finanziamento", "Cofinanziamento"], horizontal=True)

    descrizione = st.text_input("Descrizione voce (es. 'Educatore Liv.3S - Mario Rossi')", placeholder="Descrivi la voce...")

    col5, col6 = st.columns(2)
    with col5:
        if "Personale" in tipo_costo:
            ore = st.number_input("Ore lavorate nel mese", min_value=0.0, step=0.5, format="%.1f")
        else:
            ore = 0.0
    with col6:
        importo = st.number_input("Importo (€)", min_value=0.0, step=0.01, format="%.2f")

    note = st.text_area("Note (facoltativo)", placeholder="Riferimenti, giustificativi...", height=80)

    # Anteprima budget disponibile
    prev_fin, prev_cofin = BUDGET_PREVENTIVO.get(azione_sel, (0, 0))
    with st.expander("📋 Preventivo per questa azione"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Preventivo finanziato", f"€ {prev_fin:,.2f}")
        c2.metric("Preventivo cofinanziato", f"€ {prev_cofin:,.2f}")
        c3.metric("Totale azione", f"€ {prev_fin + prev_cofin:,.2f}")

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
            partner,
            mese,
            ANNO,
            area_sel,
            azione_sel,
            tipo_costo,
            descrizione.strip(),
            ore,
            importo,
            fin_cofin,
            note.strip(),
        ]
        if salva_riga(ws, riga):
            st.markdown('<div class="alert-success">✅ Voce salvata correttamente su Google Sheets!</div>', unsafe_allow_html=True)

    # Storico del partner (mese corrente)
    st.markdown('<div class="section-header">📋 Le tue voci inserite</div>', unsafe_allow_html=True)
    df = carica_dati(ws)
    if not df.empty:
        df_partner = df[df["Partner"] == partner].copy()
        if not df_partner.empty:
            df_partner_disp = df_partner[["Mese", "Azione", "Tipo Costo", "Descrizione", "Ore", "Importo (€)", "Finanziamento/Cofinanziamento"]].copy()
            df_partner_disp["Importo (€)"] = pd.to_numeric(df_partner_disp["Importo (€)"], errors="coerce").map(lambda x: f"€ {x:,.2f}" if pd.notna(x) else "")
            st.dataframe(df_partner_disp, use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna voce ancora inserita da questo ente.")
    else:
        st.info("Nessuna voce ancora inserita.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGINA CRUSCOTTO COORDINATORE
# ─────────────────────────────────────────────────────────────────────────────
def pagina_cruscotto(ws):
    st.markdown('<div class="main-title">📊 Cruscotto Coordinatore</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Avanzamento rendicontazione vs preventivo annuale</div>', unsafe_allow_html=True)

    df = carica_dati(ws)

    if df.empty:
        st.info("Nessun dato ancora inserito dai partner.")
        return

    df["Importo (€)"] = pd.to_numeric(df["Importo (€)"], errors="coerce").fillna(0)
    df["Ore"] = pd.to_numeric(df["Ore"], errors="coerce").fillna(0)

    # ── KPI globali ────────────────────────────────────────────────────────
    tot_fin_prev  = sum(v[0] for v in BUDGET_PREVENTIVO.values())
    tot_cofin_prev = sum(v[1] for v in BUDGET_PREVENTIVO.values())
    tot_fin_rend  = df[df["Finanziamento/Cofinanziamento"] == "Finanziamento"]["Importo (€)"].sum()
    tot_cofin_rend = df[df["Finanziamento/Cofinanziamento"] == "Cofinanziamento"]["Importo (€)"].sum()
    tot_ore = df["Ore"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💶 Finanziamento rendicontato",
              f"€ {tot_fin_rend:,.2f}",
              delta=f"{tot_fin_rend/tot_fin_prev*100:.1f}% del preventivo" if tot_fin_prev else "")
    c2.metric("🤝 Cofinanziamento rendicontato",
              f"€ {tot_cofin_rend:,.2f}",
              delta=f"{tot_cofin_rend/tot_cofin_prev*100:.1f}% del preventivo" if tot_cofin_prev else "")
    c3.metric("🕐 Ore totali inserite", f"{tot_ore:,.0f} h")
    c4.metric("📝 Voci inserite", len(df))

    # ── Avanzamento per azione ─────────────────────────────────────────────
    st.markdown('<div class="section-header">Avanzamento per Azione</div>', unsafe_allow_html=True)

    righe = []
    for azione, (prev_f, prev_c) in BUDGET_PREVENTIVO.items():
        df_az = df[df["Azione"].str.contains(azione.split(" - ")[0], na=False, regex=False)]
        rend_f = df_az[df_az["Finanziamento/Cofinanziamento"] == "Finanziamento"]["Importo (€)"].sum()
        rend_c = df_az[df_az["Finanziamento/Cofinanziamento"] == "Cofinanziamento"]["Importo (€)"].sum()
        perc_f = (rend_f / prev_f * 100) if prev_f > 0 else 0
        perc_c = (rend_c / prev_c * 100) if prev_c > 0 else 0
        righe.append({
            "Azione": azione,
            "Prev. Fin. (€)": prev_f,
            "Rend. Fin. (€)": rend_f,
            "% Fin.": round(perc_f, 1),
            "Prev. Cofin. (€)": prev_c,
            "Rend. Cofin. (€)": rend_c,
            "% Cofin.": round(perc_c, 1),
        })

    df_riepilogo = pd.DataFrame(righe)

    # Barre di avanzamento per azione
    for _, row in df_riepilogo.iterrows():
        with st.expander(f"**{row['Azione']}**  —  Fin: {row['% Fin.']}%  |  Cofin: {row['% Cofin.']}%"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"<span class='badge-fin'>FINANZIAMENTO</span>", unsafe_allow_html=True)
                perc = min(row["% Fin."] / 100, 1.0)
                col_b = "#38a169" if row["% Fin."] < 80 else ("#f59e0b" if row["% Fin."] < 100 else "#e53e3e")
                st.markdown(f"""
                <div style='margin:8px 0;'>
                  <div style='background:#e2e8f0;border-radius:999px;height:10px;'>
                    <div style='width:{perc*100:.1f}%;background:{col_b};height:100%;border-radius:999px;'></div>
                  </div>
                  <small style='color:#718096'>€ {row['Rend. Fin. (€)']:,.2f} / € {row['Prev. Fin. (€)']:,.2f}</small>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<span class='badge-cofin'>COFINANZIAMENTO</span>", unsafe_allow_html=True)
                perc2 = min(row["% Cofin."] / 100, 1.0)
                col_b2 = "#38a169" if row["% Cofin."] < 80 else ("#f59e0b" if row["% Cofin."] < 100 else "#e53e3e")
                st.markdown(f"""
                <div style='margin:8px 0;'>
                  <div style='background:#e2e8f0;border-radius:999px;height:10px;'>
                    <div style='width:{perc2*100:.1f}%;background:{col_b2};height:100%;border-radius:999px;'></div>
                  </div>
                  <small style='color:#718096'>€ {row['Rend. Cofin. (€)']:,.2f} / € {row['Prev. Cofin. (€)']:,.2f}</small>
                </div>""", unsafe_allow_html=True)

    # ── Avanzamento per partner ────────────────────────────────────────────
    st.markdown('<div class="section-header">Voci per Partner</div>', unsafe_allow_html=True)
    filtro_partner = st.selectbox("Filtra per partner", ["Tutti"] + list(PARTNERS_PASSWORDS.keys())[:-1])
    filtro_mese = st.selectbox("Filtra per mese", ["Tutti"] + MESI)

    df_view = df.copy()
    if filtro_partner != "Tutti":
        df_view = df_view[df_view["Partner"] == filtro_partner]
    if filtro_mese != "Tutti":
        df_view = df_view[df_view["Mese"] == filtro_mese]

    if not df_view.empty:
        df_view["Importo (€)"] = df_view["Importo (€)"].map(lambda x: f"€ {x:,.2f}")
        cols_show = ["Timestamp","Partner","Mese","Azione","Tipo Costo","Descrizione","Ore","Importo (€)","Finanziamento/Cofinanziamento","Note"]
        st.dataframe(df_view[cols_show], use_container_width=True, hide_index=True)

        # Export CSV
        csv = df_view.to_csv(index=False).encode("utf-8")
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
        ws = get_worksheet(client)
        if ws:
            if pagina == "📊 Cruscotto coordinatore":
                pagina_cruscotto(ws)
            else:
                pagina_inserimento(ws, st.session_state.partner)
    else:
        st.error("Impossibile connettersi a Google Sheets. Verifica i secrets.")
