# 📋 Guida all'installazione — Budget Progetto

Questa guida ti porta dall'installazione al sistema funzionante in meno di 30 minuti.

---

## 1. Installa Python e le dipendenze

```bash
pip install -r requirements.txt
```

---

## 2. Crea il Google Sheet

1. Vai su [sheets.google.com](https://sheets.google.com) e crea un nuovo foglio
2. Denominalo **"Budget Progetto"** (o come preferisci)
3. Copia l'**ID** dalla barra degli indirizzi:
   ```
   https://docs.google.com/spreadsheets/d/  ←QUI_C'È_L'ID→  /edit
   ```

---

## 3. Crea le credenziali Google (Service Account)

### 3a. Vai su Google Cloud Console
1. Apri [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un nuovo progetto (es. "budget-progetto")

### 3b. Abilita le API necessarie
1. Menu → **API e servizi** → **Libreria**
2. Cerca e abilita **Google Sheets API**
3. Cerca e abilita **Google Drive API**

### 3c. Crea il Service Account
1. Menu → **API e servizi** → **Credenziali**
2. Clicca **Crea credenziali** → **Account di servizio**
3. Dai un nome (es. "budget-app") e clicca **Crea e continua**
4. Salta i passaggi opzionali → **Fine**

### 3d. Scarica il file JSON
1. Nella lista degli account di servizio, clicca sull'account appena creato
2. Scheda **Chiavi** → **Aggiungi chiave** → **Crea nuova chiave** → **JSON**
3. Salva il file scaricato

### 3e. Condividi il Google Sheet con il Service Account
1. Apri il file JSON scaricato e copia il valore di `client_email`
   (sarà qualcosa come `budget-app@nome-progetto.iam.gserviceaccount.com`)
2. Apri il tuo Google Sheet
3. Clicca **Condividi** (in alto a destra)
4. Incolla l'email del service account e dai permesso **Editor**

---

## 4. Configura i secrets dell'app

1. Nella cartella del progetto, crea la cartella `.streamlit/` se non esiste
2. Apri il file `.streamlit/secrets.toml`
3. Incolla l'ID del Google Sheet nel campo `google_sheet_id`
4. Apri il file JSON del service account e copia i valori uno a uno nei campi corrispondenti

Esempio del file JSON (per capire cosa copiare dove):
```json
{
  "type": "service_account",
  "project_id": "nome-progetto",          ← va in project_id
  "private_key_id": "abc123",             ← va in private_key_id
  "private_key": "-----BEGIN RSA...",     ← va in private_key
  "client_email": "xxx@yyy.iam...",       ← va in client_email
  "client_id": "123456789",              ← va in client_id
  ...
}
```

---

## 5. Avvia l'applicazione

```bash
streamlit run app.py
```

L'app si aprirà nel browser all'indirizzo `http://localhost:8501`

---

## 6. Credenziali di accesso (da cambiare!)

| Ente | Password predefinita |
|------|---------------------|
| Fond. Madeo | `madeo2024` |
| APG | `apg2024` |
| Bessimo | `bessimo2024` |
| Igea | `igea2024` |
| Servizi per l'accoglienza | `servizi2024` |
| ATS | `ats2024` |
| Ufficio di Piano | `udp2024` |
| **COORDINATORE** | `admin2024` |

> ⚠️ **Cambia le password** nel file `app.py` alla sezione `PARTNERS_PASSWORDS` prima di distribuire l'app ai partner.

---

## 7. (Opzionale) Pubblica online con Streamlit Cloud

Per rendere l'app accessibile da browser a tutti i partner senza installare nulla:

1. Carica il progetto su [GitHub](https://github.com) (repo privato)
2. Vai su [share.streamlit.io](https://share.streamlit.io)
3. Connetti il repo e seleziona `app.py`
4. Nella sezione **Secrets**, incolla il contenuto del tuo `secrets.toml`
5. Deploy! Otterrai un link pubblico da condividere con i partner

---

## 8. Struttura dei dati su Google Sheets

Il foglio "Rendicontazione" verrà creato automaticamente con queste colonne:

| Colonna | Descrizione |
|---------|-------------|
| Timestamp | Data e ora dell'inserimento |
| Partner | Nome dell'ente |
| Mese | Mese di riferimento |
| Anno | Anno |
| Area | Area del quadro logico |
| Azione | Azione specifica |
| Tipo Costo | Personale / Spese |
| Descrizione | Dettaglio della voce |
| Ore | Ore lavorate (se personale) |
| Importo (€) | Importo in euro |
| Finanziamento/Cofinanziamento | Tipo di imputazione |
| Note | Note aggiuntive |

---

## Supporto

Per problemi tecnici o modifiche al sistema, contatta il referente IT del progetto.
