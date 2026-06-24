import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px  # Behalten für eventuelle Diagramme

# Page Configuration
st.set_page_config(page_title="MD Snackz Lagersystem", layout="wide")

# Google Sheets Verbindung initialisieren
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. DATEN LADEN & DIRETK REPARIEREN ---
def load_daten():
    # Bestand auslesen
    try:
        df_b = conn.read(worksheet="Bestand")
    except Exception:
        df_b = pd.DataFrame(columns=['Barcode', 'Artikelname', 'Menge', 'Kaufpreis', 'Verkaufspreis', 'MHD'])
    
    # Historie auslesen
    try:
        df_h = conn.read(worksheet="Historie")
    except Exception:
        df_h = pd.DataFrame(columns=['Barcode', 'Artikelname', 'Menge', 'Aktion', 'Finanz_Effekt', 'Zeitpunkt'])
    
    # WICHTIG: Barcodes direkt beim Laden von '.0' befreien und als Text (String) sichern
    if 'Barcode' in df_b.columns:
        df_b['Barcode'] = df_b['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    if 'Barcode' in df_h.columns:
        df_h['Barcode'] = df_h['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
    return df_b, df_h

# --- 2. DATEN MIT SAUBEREM FORMAT SPEICHERN ---
def save_daten(df_b, df_h):
    df_b_save = df_b.copy()
    df_h_save = df_h.copy()
    
    # Barcodes vor dem Hochladen nochmals säubern (Zahlen-Formatierung verhindern)
    if not df_b_save.empty and 'Barcode' in df_b_save.columns:
        df_b_save['Barcode'] = df_b_save['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    if not df_h_save.empty and 'Barcode' in df_h_save.columns:
        df_h_save['Barcode'] = df_h_save['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # Datumsspalten als Text formatieren
    if not df_b_save.empty:
        df_b_save['MHD'] = df_b_save['MHD'].astype(str)
    if not df_h_save.empty:
        df_h_save['Zeitpunkt'] = df_h_save['Zeitpunkt'].astype(str)
        
    # In Google Sheets zurückschreiben
    conn.update(worksheet="Bestand", data=df_b_save)
    conn.update(worksheet="Historie", data=df_h_save)

# Daten initial laden
df_bestand, df_historie = load_daten()

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("# 📦 MD Snackz")
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navigation",
    ["Schnell-Buchung", "Bestands-Tabelle", "Einzel-Produkt Einsicht"],
    label_visibility="collapsed"
)

# --- FINANZIELLE ÜBERSICHT (HEADLINE) ---
st.markdown("# 💰 Finanzielle Übersicht")

if not df_historie.empty and 'Finanz_Effekt' in df_historie.columns:
    # Finanz_Effekt Spalte sicher numerisch konvertieren
    df_historie['Finanz_Effekt'] = pd.to_numeric(df_historie['Finanz_Effekt'], errors='coerce').fillna(0.0)
    
    # Berechnungen (Ohne .abs() Fehler auf Primitiven)
    gesamtkosten = abs(df_historie[df_historie['Finanz_Effekt'] < 0]['Finanz_Effekt'].sum())
    einnahmen = df_historie[df_historie['Finanz_Effekt'] > 0]['Finanz_Effekt'].sum()
    defizit = einnahmen - gesamtkosten
else:
    gesamtkosten, einnahmen, defizit = 0.0, 0.0, 0.0

col1, col2, col3 = st.columns(3)
col1.metric("Gesamtkosten (Einkauf)", f"{gesamtkosten:.2f} €")
col2.metric("Tatsächliche Einnahmen", f"{einnahmen:.2f} €")
col3.metric("Verlust / Defizit", f"{defizit:.2f} €", delta=f"{defizit:.2f} €")
st.markdown("---")


# --- ANSICHT 1: SCHNELL-BUCHUNG ---
if menu == "Schnell-Buchung":
    st.subheader("🔄 Schnell-Buchung (Wareneingang / Warenausgang)")
    
    with st.form("buchung_form"):
        # text_input statt number_input nutzen, um .0 Formatierungen abzufangen!
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
                # Barcode bereinigen
                barcode_clean = str(barcode_input).replace('.0', '').strip()
                
                # Prüfen ob Artikel bereits existiert
                idx = df_bestand[df_bestand['Barcode'] == barcode_clean].index
                
                if not idx.empty:
                    current_name = df_bestand.loc[idx[0], 'Artikelname']
                    current_menge = int(df_bestand.loc[idx[0], 'Menge'])
                    # Preise vom bestehenden Artikel übernehmen falls nicht im Formular geändert
                    kp = kaufpreis if kaufpreis > 0 else float(df_bestand.loc[idx[0], 'Kaufpreis'])
                    vp = verkaufspreis if verkaufspreis > 0 else float(df_bestand.loc[idx[0], 'Verkaufspreis'])
                else:
                    current_name = artikelname if artikelname else f"Produkt {barcode_clean}"
                    current_menge = 0
                    kp = kaufpreis
                    vp = verkaufspreis
                
                # Mengen & Finanzeffekt berechnen
                if aktion == "Wareneingang":
                    neue_menge = current_menge + menge
                    finanz_effekt = -(menge * kp)
                else:  # Warenausgang
                    neue_menge = max(0, current_menge - menge)
                    finanz_effekt = (menge * vp)
                
                # Bestand updaten
                if not idx.empty:
                    df_bestand.loc[idx[0], 'Menge'] = neue_menge
                    df_bestand.loc[idx[0], 'MHD'] = str(mhd)
                    if kaufpreis > 0: df_bestand.loc[idx[0], 'Kaufpreis'] = kp
                    if verkaufspreis > 0: df_bestand.loc[idx[0], 'Verkaufspreis'] = vp
                else:
                    new_product = pd.DataFrame([{
                        'Barcode': barcode_clean, 'Artikelname': current_name, 'Menge': neue_menge,
                        'Kaufpreis': kp, 'Verkaufspreis': vp, 'MHD': str(mhd)
                    }])
                    df_bestand = pd.concat([df_bestand, new_product], ignore_index=True)
                
                # Historie befüllen
                new_history_entry = pd.DataFrame([{
                    'Barcode': barcode_clean,
                    'Artikelname': current_name,
                    'Menge': menge if aktion == "Wareneingang" else -menge,
                    'Aktion': aktion,
                    'Finanz_Effekt': finanz_effekt,
                    'Zeitpunkt': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                df_historie = pd.concat([df_historie, new_history_entry], ignore_index=True)
                
                # Daten in Cloud sichern
                save_daten(df_bestand, df_historie)
                st.success(f"Erfolgreich gebucht: {aktion} von '{current_name}' ({menge} Stk.)")
                st.rerun()


# --- ANSICHT 2: BESTANDS-TABELLE ---
elif menu == "Bestands-Tabelle":
    st.subheader("📊 Aktueller Gesamtbestand")
    if df_bestand.empty:
        st.info("Es sind noch keine Produkte im System registriert.")
    else:
        st.dataframe(df_bestand, use_container_width=True)


# --- ANSICHT 3: EINZEL-PRODUKT EINSICHT (INKL. SORTIERUNG) ---
elif menu == "Einzel-Produkt Einsicht":
    st.subheader("🔍 Einzel-Produkt Einsicht & Historie")
    
    if df_bestand.empty:
        st.info("Keine Produkte für die Einsicht vorhanden.")
    else:
        # Dropdown zur Produktauswahl generieren
        produkt_liste = df_bestand.apply(lambda r: f"{r['Artikelname']} ({r['Barcode']})", axis=1).tolist()
        auswahl = st.selectbox("Produkt auswählen", produkt_liste)
        
        # Ausgewählten Barcode ermitteln
        selected_barcode = df_bestand.iloc[produkt_liste.index(auswahl)]['Barcode']
        selected_product = df_bestand[df_bestand['Barcode'] == selected_barcode].iloc[0]
        
        # Produktdetails anzeigen
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Artikelname", str(selected_product['Artikelname']))
        c2.metric("Aktuelle Menge", f"{selected_product['Menge']} Stk.")
        c3.metric("Verkaufspreis", f"{float(selected_product['Verkaufspreis']):.2f} €")
        c4.metric("MHD", str(selected_product['MHD']))
        
        st.markdown("### 📜 Alle Aktionen zu diesem Produkt")
        
        # Historie filtern
        df_produkt_hist = df_historie[df_historie['Barcode'] == selected_barcode].copy()
        
        if df_produkt_hist.empty:
            st.info("Für dieses Produkt liegt noch keine Buchungs-Historie vor.")
        else:
            # --- ZIEL ERREICHT: Neueste Aktionen zuerst anzeigen (Absteigend sortiert) ---
            if 'Zeitpunkt' in df_produkt_hist.columns:
                df_produkt_hist = df_produkt_hist.sort_values(by='Zeitpunkt', ascending=False)
            
            st.dataframe(df_produkt_hist, use_container_width=True)
