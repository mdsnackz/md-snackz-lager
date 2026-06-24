import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px

# Page Configuration
st.set_page_config(page_title="MD Snackz Lagersystem", layout="wide")

# Google Sheets Verbindung initialisieren
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. DATEN LADEN & STRUKTUR SCHÜTZEN ---
def load_daten():
    required_b = ['Barcode', 'Artikelname', 'Menge', 'Kaufpreis', 'Verkaufspreis', 'MHD']
    required_h = ['Barcode', 'Artikelname', 'Menge', 'Aktion', 'Finanz_Effekt', 'Zeitpunkt']
    
    # Bestand auslesen
    try:
        df_b = conn.read(worksheet="Bestand")
        if df_b.empty or len(df_b.columns) == 0:
            df_b = pd.DataFrame(columns=required_b)
    except Exception:
        df_b = pd.DataFrame(columns=required_b)
    
    # Historie auslesen
    try:
        df_h = conn.read(worksheet="Historie")
        if df_h.empty or len(df_h.columns) == 0:
            df_h = pd.DataFrame(columns=required_h)
    except Exception:
        df_h = pd.DataFrame(columns=required_h)
    
    # Absicherung: Fehlende Spalten erzwingen, um KeyErrors zu verhindern
    for col in required_b:
        if col not in df_b.columns:
            df_b[col] = ""
    for col in required_h:
        if col not in df_h.columns:
            df_h[col] = ""
    
    # Barcodes säubern
    df_b['Barcode'] = df_b['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_h['Barcode'] = df_h['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # Leere Geister-Zeilen herausfiltern
    df_b = df_b[df_b['Barcode'] != '']
        
    return df_b, df_h

# --- 2. DATEN SPEICHERN ---
def save_daten(df_b, df_h):
    df_b_save = df_b.copy()
    df_h_save = df_h.copy()
    
    df_b_save['Barcode'] = df_b_save['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_h_save['Barcode'] = df_h_save['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    df_b_save['MHD'] = df_b_save['MHD'].astype(str)
    df_h_save['Zeitpunkt'] = df_h_save['Zeitpunkt'].astype(str)
        
    conn.update(worksheet="Bestand", data=df_b_save)
    conn.update(worksheet="Historie", data=df_h_save)

# Daten initial laden
df_bestand, df_historie = load_daten()

# --- 3. CUSTOM CSS FÜR DIE SEITENLEISTE ---
st.sidebar.markdown("""
    <style>
    div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 14px 18px !important;
        border-radius: 10px !important;
        color: white !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #ff4b4b !important;
        border-color: #ff4b4b !important;
        font-weight: bold !important;
        box-shadow: 0px 4px 10px rgba(255, 75, 75, 0.3);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p {
        font-size: 16px !important;
        margin: 0 !important;
    }
    div[data-testid="stRadio"] [data-testid="stWidgetLabel"] {
        display: none !important;
    }
    </style>
""", unsafe_html=True)

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("# 📦 MD Snackz")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation",
    ["🔄 Schnell-Buchung", "📊 Bestands-Tabelle", "🔍 Einzel-Produkt Einsicht"]
)

st.sidebar.markdown("---")

# --- ZEITFILTER ---
st.sidebar.markdown("### 📅 Zeitfilter (Diagramme & Umsatz)")
zeitraum = st.sidebar.selectbox("Zeitraum wählen", ["All Time", "Year", "Monthly"])

ausgewaehltes_jahr = None
ausgewaehlter_monat = None

if not df_historie.empty and 'Zeitpunkt' in df_historie.columns:
    df_historie_years = df_historie.copy()
    df_historie_years['datetime_calc'] = pd.to_datetime(df_historie_years['Zeitpunkt'], errors='coerce')
    verfuegbare_jahre = df_historie_years['datetime_calc'].dt.year.dropna().unique().astype(int).tolist()
    if not verfuegbare_jahre:
        verfuegbare_jahre = [datetime.today().year]
else:
    verfuegbare_jahre = [datetime.today().year]
verfuegbare_jahre = sorted(list(set(verfuegbare_jahre)), reverse=True)

if zeitraum == "Year":
    ausgewaehltes_jahr = st.sidebar.selectbox("Jahr auswählen", verfuegbare_jahre)
elif zeitraum == "Monthly":
    ausgewaehltes_jahr = st.sidebar.selectbox("Jahr auswählen", verfuegbare_jahre)
    monate_namen = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    ausgewaehlter_monat_name = st.sidebar.selectbox("Monat auswählen", monate_namen)
    ausgewaehlter_monat = monate_namen.index(ausgewaehlter_monat_name) + 1

# Filter anwenden
df_historie_filtered = df_historie.copy()

if not df_historie_filtered.empty and 'Zeitpunkt' in df_historie_filtered.columns:
    df_historie_filtered['datetime_temp'] = pd.to_datetime(df_historie_filtered['Zeitpunkt'], errors='coerce')
    
    if zeitraum == "Year":
        df_historie_filtered = df_historie_filtered[df_historie_filtered['datetime_temp'].dt.year == ausgewaehltes_jahr]
    elif zeitraum == "Monthly":
        df_historie_filtered = df_historie_filtered[
            (df_historie_filtered['datetime_temp'].dt.year == ausgewaehltes_jahr) & 
            (df_historie_filtered['datetime_temp'].dt.month == ausgewaehlter_monat)
        ]
    
    if 'datetime_temp' in df_historie_filtered.columns:
        df_historie_filtered = df_historie_filtered.drop(columns=['datetime_temp'])

# --- FINANZIELLE ÜBERSICHT ---
st.markdown("# 💰 Finanzielle Übersicht")

if not df_historie_filtered.empty and 'Finanz_Effekt' in df_historie_filtered.columns:
    df_historie_filtered['Finanz_Effekt'] = pd.to_numeric(df_historie_filtered['Finanz_Effekt'], errors='coerce').fillna(0.0)
    gesamtkosten = abs(df_historie_filtered[df_historie_filtered['Finanz_Effekt'] < 0]['Finanz_Effekt'].sum())
    einnahmen = df_historie_filtered[df_historie_filtered['Finanz_Effekt'] > 0]['Finanz_Effekt'].sum()
    defizit = einnahmen - gesamtkosten
else:
    gesamtkosten, einnahmen, defizit = 0.0, 0.0, 0.0

col1, col2, col3 = st.columns(3)
col1.metric("Gesamtkosten (Einkauf)", f"{gesamtkosten:.2f} €")
col2.metric("Tatsächliche Einnahmen", f"{einnahmen:.2f} €")
col3.metric("Verlust / Defizit", f"{defizit:.2f} €")

if not df_historie_filtered.empty:
    fig_gesamt = px.bar(
        df_historie_filtered, 
        x='Zeitpunkt', 
        y='Finanz_Effekt', 
        color='Aktion',
        title=f"📈 Umsatz- & Transaktionsverlauf ({zeitraum})",
        labels={'Finanz_Effekt': 'Effekt (€)', 'Zeitpunkt': 'Zeitpunkt'},
        color_discrete_map={'Wareneingang': '#ff4b4b', 'Warenausgang': '#2ec4b6'}
    )
    st.plotly_chart(fig_gesamt, use_container_width=True)

st.markdown("---")

# --- ANSICHT 1: SCHNELL-BUCHUNG ---
if menu == "🔄 Schnell-Buchung":
    st.subheader("🔄 Schnell-Buchung (Wareneingang / Warenausgang)")
    
    with st.form("buchung_form"):
        barcode_input = st.text_input("Barcode scannen / eingeben").strip()
        artikelname = st.text_input("Artikelname (nur bei neuem Produkt ausfüllen)")
        menge = st.number_input("Menge", min_value=1, step=1, value=1)
        aktion = st.selectbox("Aktion", ["Wareneingang", "Warenausgang"])
        kaufpreis = st.number_input("Kaufpreis pro Stück (€)", min_value=0.0, step=0.01, value=0.0)
        verkaufspreis = st.number_input("Verkaufspreis pro Stück (€)", min_value=0.0, step=0.01, value=0.0)
        mhd = st.date_input("MHD (Mindesthaltbarkeitsdatum)", value=datetime.today())
        
        submitted = st.form_submit_button("Buchung ausführen")
        
        if submitted:
            if not barcode_input:
                st.error("Bitte gib einen Barcode ein!")
            else:
                barcode_clean = str(barcode_input).replace('.0', '').strip()
                idx = df_bestand[df_bestand['Barcode'] == barcode_clean].index
                
                if not idx.empty:
                    current_name = df_bestand.loc[idx[0], 'Artikelname'] if pd.notna(df_bestand.loc[idx[0], 'Artikelname']) else f"Produkt {barcode_clean}"
                    current_menge = int(df_bestand.loc[idx[0], 'Menge']) if pd.notna(df_bestand.loc[idx[0], 'Menge']) else 0
                    kp = kaufpreis if kaufpreis > 0 else float(df_bestand.loc[idx[0], 'Kaufpreis'])
                    vp = verkaufspreis if verkaufspreis > 0 else float(df_bestand.loc[idx[0], 'Verkaufspreis'])
                else:
                    current_name = artikelname if artikelname else f"Produkt {barcode_clean}"
                    current_menge = 0
                    kp = kaufpreis
                    vp = verkaufspreis
                
                if aktion == "Wareneingang":
                    neue_menge = current_menge + menge
                    finanz_effekt = -(menge * kp)
                else:
                    neue_menge = max(0, current_menge - menge)
                    finanz_effekt = (menge * vp)
                
                if not idx.empty:
                    df_bestand.loc[idx[0], 'Menge'] = neue_menge
                    df_bestand.loc[idx[0], 'MHD'] = str(mhd)
                    df_bestand.loc[idx[0], 'Kaufpreis'] = kp
                    df_bestand.loc[idx[0], 'Verkaufspreis'] = vp
                else:
                    new_product = pd.DataFrame([{
                        'Barcode': barcode_clean, 'Artikelname': current_name, 'Menge': neue_menge,
                        'Kaufpreis': kp, 'Verkaufspreis': vp, 'MHD': str(mhd)
                    }])
                    df_bestand = pd.concat([df_bestand, new_product], ignore_index=True)
                
                new_history_entry = pd.DataFrame([{
                    'Barcode': barcode_clean, 'Artikelname': current_name,
                    'Menge': menge if aktion == "Wareneingang" else -menge,
                    'Aktion': aktion, 'Finanz_Effekt': finanz_effekt,
                    'Zeitpunkt': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                df_historie = pd.concat([df_historie, new_history_entry], ignore_index=True)
                
                save_daten(df_bestand, df_historie)
                st.success(f"Erfolgreich gebucht: {aktion} von '{current_name}' ({menge} Stk.)")
                st.rerun()

# --- ANSICHT 2: BESTANDS-TABELLE ---
elif menu == "📊 Bestands-Tabelle":
    st.subheader("📊 Aktueller Gesamtbestand")
    if df_bestand.empty:
        st.info("Es sind noch keine Produkte im System registriert.")
    else:
        st.dataframe(df_bestand, use_container_width=True)

# --- ANSICHT 3: EINZEL-PRODUKT EINSICHT ---
elif menu == "🔍 Einzel-Produkt Einsicht":
    st.subheader("🔍 Einzel-Produkt Einsicht & Historie")
    
    if df_bestand.empty:
        st.info("Keine Produkte für die Einsicht vorhanden.")
    else:
        df_dropdown = df_bestand[df_bestand['Barcode'].str.strip() != ''].copy()
        
        if df_dropdown.empty:
            st.info("Keine gültigen Produkte gefunden.")
        else:
            df_dropdown['Artikelname'] = df_dropdown['Artikelname'].fillna('Unbekanntes Produkt')
            produkt_liste = df_dropdown.apply(lambda r: f"{str(r['Artikelname'])} ({str(r['Barcode'])})", axis=1).tolist()
            
            auswahl = st.selectbox("Produkt auswählen", produkt_liste)
            
            selected_barcode = df_dropdown.iloc[produkt_liste.index(auswahl)]['Barcode']
            selected_product = df_dropdown[df_dropdown['Barcode'] == selected_barcode].iloc[0]
            
            # Produktdetails anzeigen
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Artikelname", str(selected_product['Artikelname']))
            c2.metric("Aktuelle Menge", f"{selected_product['Menge']} Stk.")
            
            try:
                v_preis = float(selected_product['Verkaufspreis'])
            except:
                v_preis = 0.0
                
            c3.metric("Verkaufspreis", f"{v_preis:.2f} €")
            c4.metric("MHD", str(selected_product['MHD']))
            
            # Historie filtern
            df_produkt_hist = df_historie_filtered[df_historie_filtered['Barcode'] == selected_barcode].copy()
            
            st.markdown("### 📊 Produkt-Diagramm")
            if df_produkt_hist.empty:
                st.info(f"Für dieses Produkt liegt im gewählten Zeitraum ({zeitraum}) keine Buchungs-Historie vor.")
            else:
                df_produkt_hist['Menge'] = pd.to_numeric(df_produkt_hist['Menge'], errors='coerce').fillna(0)
                fig_prod = px.bar(
                    df_produkt_hist, 
                    x='Zeitpunkt', 
                    y='Menge', 
                    color='Aktion',
                    title=f"Mengenveränderungen für '{selected_product['Artikelname']}' ({zeitraum})",
                    labels={'Menge': 'Menge (Stk.)', 'Zeitpunkt': 'Zeitpunkt'},
                    color_discrete_map={'Wareneingang': '#ff4b4b', 'Warenausgang': '#2ec4b6'}
                )
                st.plotly_chart(fig_prod, use_container_width=True)
                
                st.markdown("### 📜 Alle Aktionen zu diesem Produkt im Zeitraum")
                if 'Zeitpunkt' in df_produkt_hist.columns:
                    df_produkt_hist = df_produkt_hist.sort_values(by='Zeitpunkt', ascending=False)
                
                st.dataframe(df_produkt_hist, use_container_width=True)
