import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px

# Page Configuration
st.set_page_config(page_title="MD Snackz Lagersystem", layout="wide")

# Google Sheets Verbindung initialisieren
conn = st.connection("gsheets", type=GSheetsConnection)

# --- STREMLIT LIFECYCLE: BARCODE RESET VOR DEM RENDERN ---
if 'reset_barcode' in st.session_state and st.session_state['reset_barcode']:
    st.session_state['schnell_barcode'] = ""
    st.session_state['reset_barcode'] = False

# --- 1. DATEN LADEN & STRUKTUR SCHÜTZEN ---
def load_daten():
    required_b = ['Barcode', 'Artikelname', 'Menge', 'Kaufpreis', 'Verkaufspreis', 'MHD']
    required_h = ['Barcode', 'Artikelname', 'Menge', 'Aktion', 'Finanz_Effekt', 'Zeitpunkt', 'MHD']
    
    try:
        df_b = conn.read(worksheet="Bestand", ttl=0)
        if df_b.empty or len(df_b.columns) == 0:
            df_b = pd.DataFrame(columns=required_b)
    except Exception:
        df_b = pd.DataFrame(columns=required_b)
    
    try:
        df_h = conn.read(worksheet="Historie", ttl=0)
        if df_h.empty or len(df_h.columns) == 0:
            df_h = pd.DataFrame(columns=required_h)
    except Exception:
        df_h = pd.DataFrame(columns=required_h)
    
    for col in required_b:
        if col not in df_b.columns:
            df_b[col] = ""
    for col in required_h:
        if col not in df_h.columns:
            df_h[col] = ""
    
    df_b['Barcode'] = df_b['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_h['Barcode'] = df_h['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
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
    df_h_save['MHD'] = df_h_save['MHD'].astype(str)
        
    conn.update(worksheet="Bestand", data=df_b_save)
    conn.update(worksheet="Historie", data=df_h_save)

# Daten laden
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
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("# 📦 MD Snackz")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation",
    ["🔄 Schnell-Buchung", "📊 Bestands-Tabelle", "🔍 Einzel-Produkt Einsicht", "💰 Finanzielle Übersicht"]
)

st.sidebar.markdown("---")

# --- ZEITFILTER-LOGIK ---
zeitraum = "All Time"
ausgewaehltes_jahr = None
ausgewaehlter_monat = None

if menu in ["🔍 Einzel-Produkt Einsicht", "💰 Finanzielle Übersicht"]:
    st.sidebar.markdown("### 📅 Zeitfilter")
    zeitraum = st.sidebar.selectbox("Zeitraum wählen", ["All Time", "Year", "Monthly"])

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

# ==========================================
# SEITEN-ANSICHTEN
# ==========================================

# --- ANSICHT 1: SCHNELL-BUCHUNG ---
if menu == "🔄 Schnell-Buchung":
    st.subheader("🔄 Schnell-Buchung (Lagerverwaltung)")
    
    if 'success_msg' in st.session_state:
        st.success(st.session_state['success_msg'])
        del st.session_state['success_msg']
        
    barcode_input = st.text_input("Barcode scannen / eingeben", key="schnell_barcode").strip()
    
    if not barcode_input:
        st.info("💡 Bitte scannen oder geben Sie einen Barcode ein, um die Buchungsoptionen anzuzeigen.")
    else:
        barcode_clean = str(barcode_input).replace('.0', '').strip()
        idx = df_bestand[df_bestand['Barcode'] == barcode_clean].index
        exists = not idx.empty
        
        with st.form("buchung_details_form", clear_on_submit=True):
            if not exists:
                st.warning(f"🆕 Neues Produkt mit Barcode {barcode_clean} erkannt.")
                artikelname = st.text_input("Artikelname (Pflichtfeld)").strip()
                default_kp = 0.0
                default_vp = 0.0
                default_mhd = datetime.today().date()
            else:
                current_name = df_bestand.loc[idx[0], 'Artikelname']
                st.info(f"✅ Produkt im Bestand gefunden: **{current_name}**")
                artikelname = current_name
                
                try:
                    default_kp = float(df_bestand.loc[idx[0], 'Kaufpreis']) if pd.notna(df_bestand.loc[idx[0], 'Kaufpreis']) else 0.0
                except:
                    default_kp = 0.0
                try:
                    default_vp = float(df_bestand.loc[idx[0], 'Verkaufspreis']) if pd.notna(df_bestand.loc[idx[0], 'Verkaufspreis']) else 0.0
                except:
                    default_vp = 0.0
                try:
                    default_mhd = pd.to_datetime(df_bestand.loc[idx[0], 'MHD']).date()
                except:
                    default_mhd = datetime.today().date()
            
            menge = st.number_input("Menge", min_value=1, step=1, value=1)
            
            aktion = st.selectbox("Aktion", [
                "Wareneingang", 
                "Warenausgang (Verkauf)", 
                "Ausschuss / Defekt (Umsatzverlust)"
            ])
            
            kaufpreis = st.number_input("Kaufpreis pro Stück (€)", min_value=0.0, step=0.01, value=default_kp)
            verkaufspreis = st.number_input("Verkaufspreis pro Stück (€)", min_value=0.0, step=0.01, value=default_vp)
            
            # Das MHD-Feld wird AUSSCHLIESSLICH bei "Wareneingang" angezeigt!
            if aktion == "Wareneingang":
                mhd = st.date_input("MHD (Mindesthaltbarkeitsdatum)", value=default_mhd)
            else:
                mhd = default_mhd
            
            submitted = st.form_submit_button("Buchung ausführen")
            
            if submitted:
                if not exists and not artikelname:
                    st.error("Bitte gib einen Artikelnamen für das neue Produkt ein!")
                else:
                    current_menge = int(df_bestand.loc[idx[0], 'Menge']) if (exists and pd.notna(df_bestand.loc[idx[0], 'Menge'])) else 0
                    kp = kaufpreis
                    vp = verkaufspreis
                    
                    if aktion == "Wareneingang":
                        neue_menge = current_menge + menge
                        finanz_effekt = -(menge * kp)
                        historie_menge = menge
                    elif aktion == "Warenausgang (Verkauf)":
                        neue_menge = max(0, current_menge - menge)
                        finanz_effekt = (menge * vp)
                        historie_menge = -menge
                    elif aktion == "Ausschuss / Defekt (Umsatzverlust)":
                        neue_menge = current_menge 
                        finanz_effekt = -(menge * vp)  
                        historie_menge = 0  
                    
                    # 1. Eintrag in Historie anfügen (inklusive MHD bei Wareneingängen)
                    new_history_entry = pd.DataFrame([{
                        'Barcode': barcode_clean, 'Artikelname': artikelname,
                        'Menge': historie_menge,
                        'Aktion': aktion, 'Finanz_Effekt': finanz_effekt,
                        'Zeitpunkt': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'MHD': str(mhd) if aktion == "Wareneingang" else ""
                    }])
                    df_historie = pd.concat([df_historie, new_history_entry], ignore_index=True)
                    
                    # 2. FIFO LOGIK: Berechne das älteste, noch verfügbare MHD im Bestand
                    aktueller_mhd = str(default_mhd)
                    if neue_menge > 0:
                        df_we = df_historie[(df_historie['Barcode'] == barcode_clean) & (df_historie['Aktion'] == "Wareneingang")].copy()
                        if not df_we.empty and 'MHD' in df_we.columns:
                            # Nach Zeit absteigend sortieren (neueste zuerst)
                            df_we['Zeitpunkt_dt'] = pd.to_datetime(df_we['Zeitpunkt'], errors='coerce')
                            df_we = df_we.sort_values(by='Zeitpunkt_dt', ascending=False)
                            
                            computed_mhd = None
                            cum_incoming = 0
                            # Von neu nach alt hochrechnen, welche Chargen die aktuelle Restmenge bilden
                            for _, row in df_we.iterrows():
                                try:
                                    m_val = int(float(row['Menge']))
                                except:
                                    m_val = 0
                                cum_incoming += m_val
                                if cum_incoming >= neue_menge:
                                    val_mhd = str(row['MHD']).strip()
                                    if val_mhd and val_mhd.lower() != 'nan' and val_mhd != "":
                                        computed_mhd = val_mhd
                                        break
                            if computed_mhd:
                                aktueller_mhd = computed_mhd
                    else:
                        aktueller_mhd = "" # Ausverkauft -> kein MHD
                    
                    # 3. Bestand updaten
                    if exists:
                        df_bestand.loc[idx[0], 'Menge'] = neue_menge
                        df_bestand.loc[idx[0], 'MHD'] = aktueller_mhd
                        df_bestand.loc[idx[0], 'Kaufpreis'] = kp
                        df_bestand.loc[idx[0], 'Verkaufspreis'] = vp
                    else:
                        new_product = pd.DataFrame([{
                            'Barcode': barcode_clean, 'Artikelname': artikelname, 'Menge': neue_menge,
                            'Kaufpreis': kp, 'Verkaufspreis': vp, 'MHD': aktueller_mhd
                        }])
                        df_bestand = pd.concat([df_bestand, new_product], ignore_index=True)
                    
                    save_daten(df_bestand, df_historie)
                    
                    st.session_state['reset_barcode'] = True
                    st.session_state['success_msg'] = f"✅ Erfolgreich gebucht: {aktion} von '{artikelname}' ({menge} Stk.)"
                    st.rerun()

# --- ANSICHT 2: BESTANDS-TABELLE ---
elif menu == "📊 Bestands-Tabelle":
    st.subheader("📊 Aktueller Gesamtbestand")
    if df_bestand.empty:
        st.info("Es sind noch keine Produkte im System registriert.")
    else:
        st.dataframe(df_bestand, width="stretch")

# --- ANSICHT 3: EINZEL-PRODUKT EINSICHT ---
elif menu == "🔍 Einzel-Produkt Einsicht":
    st.subheader("🔍 Einzel-Produkt Einsicht & Historie")
    
    if df_bestand.empty:
        st.info("Keine Produkte für die Einsicht vorhanden.")
    else:
        df_dropdown = df_bestand.copy()
        df_dropdown['Barcode'] = df_dropdown['Barcode'].astype(str).str.strip()
        df_dropdown = df_dropdown[df_dropdown['Barcode'] != '']
        
        if df_dropdown.empty:
            st.info("Keine gültigen Produkte gefunden.")
        else:
            df_dropdown['Artikelname'] = df_dropdown['Artikelname'].fillna('Unbekanntes Produkt').astype(str)
            produkt_liste = df_dropdown.apply(lambda r: f"{r['Artikelname']} ({r['Barcode']})", axis=1).tolist()
            
            auswahl = st.selectbox("Produkt auswählen", produkt_liste)
            selected_barcode = df_dropdown.iloc[produkt_liste.index(auswahl)]['Barcode']
            selected_product = df_dropdown[df_dropdown['Barcode'] == selected_barcode].iloc[0]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Artikelname", str(selected_product['Artikelname']))
            c2.metric("Aktuelle Menge", f"{selected_product['Menge']} Stk.")
            
            try:
                v_preis = float(selected_product['Verkaufspreis'])
            except:
                v_preis = 0.0
                
            c3.metric("Verkaufspreis", f"{v_preis:.2f} €")
            c4.metric("MHD (Nächstes Fälliges)", str(selected_product['MHD']))
            
            df_prod_all = df_historie[df_historie['Barcode'] == selected_barcode].copy()
            
            st.markdown("### 📈 Tatsächlicher Bestandsverlauf (Entwicklung)")
            if df_prod_all.empty:
                st.info("Für dieses Produkt liegt keine Buchungs-Historie vor.")
            else:
                df_prod_all['Zeitpunkt'] = pd.to_datetime(df_prod_all['Zeitpunkt'])
                df_prod_all = df_prod_all.sort_values(by='Zeitpunkt')
                df_prod_all['Menge'] = pd.to_numeric(df_prod_all['Menge'], errors='coerce').fillna(0)
                
                df_prod_all['Tatsächlicher_Bestand'] = df_prod_all['Menge'].cumsum()
                
                df_prod_filtered = df_prod_all.copy()
                if zeitraum == "Year":
                    df_prod_filtered = df_prod_filtered[df_prod_filtered['Zeitpunkt'].dt.year == ausgewaehltes_jahr]
                elif zeitraum == "Monthly":
                    df_prod_filtered = df_prod_filtered[
                        (df_prod_filtered['Zeitpunkt'].dt.year == ausgewaehltes_jahr) & 
                        (df_prod_filtered['Zeitpunkt'].dt.month == ausgewaehlter_monat)
                    ]
                
                if df_prod_filtered.empty:
                    st.info(f"Keine Aktionen im gewählten Zeitraum ({zeitraum}).")
                else:
                    fig_prod = px.line(
                        df_prod_filtered, 
                        x='Zeitpunkt', 
                        y='Tatsächlicher_Bestand', 
                        title=f"Realer Lagerbestand von '{selected_product['Artikelname']}'",
                        labels={'Tatsächlicher_Bestand': 'Bestand (Stk.)', 'Zeitpunkt': 'Zeitpunkt'},
                        line_shape='spline',
                        markers=True
                    )
                    fig_prod.update_traces(line_color='#2ec4b6', line_width=3)
                    st.plotly_chart(fig_prod, width="stretch")
                
                st.markdown("### 📜 Einzelaktionen im Zeitraum")
                df_prod_filtered_disp = df_prod_filtered.sort_values(by='Zeitpunkt', ascending=False)
                st.dataframe(df_prod_filtered_disp, width="stretch")

# --- ANSICHT 4: FINANZIELLE ÜBERSICHT ---
elif menu == "💰 Finanzielle Übersicht":
    st.markdown("# 💰 Finanzielle Übersicht & Bilanz")

    df_hist_calc = df_historie.copy()
    if not df_hist_calc.empty:
        df_hist_calc['Zeitpunkt'] = pd.to_datetime(df_hist_calc['Zeitpunkt'])
        if zeitraum == "Year":
            df_hist_calc = df_hist_calc[df_hist_calc['Zeitpunkt'].dt.year == ausgewaehltes_jahr]
        elif zeitraum == "Monthly":
            df_hist_calc = df_hist_calc[
                (df_hist_calc['Zeitpunkt'].dt.year == ausgewaehltes_jahr) & 
                (df_hist_calc['Zeitpunkt'].dt.month == ausgewaehlter_monat)
            ]

    if not df_hist_calc.empty and 'Finanz_Effekt' in df_hist_calc.columns:
        df_hist_calc['Finanz_Effekt'] = pd.to_numeric(df_hist_calc['Finanz_Effekt'], errors='coerce').fillna(0.0)
        gesamtkosten = abs(df_hist_calc[df_hist_calc['Finanz_Effekt'] < 0]['Finanz_Effekt'].sum())
        einnahmen = df_hist_calc[df_hist_calc['Finanz_Effekt'] > 0]['Finanz_Effekt'].sum()
        defizit = df_hist_calc['Finanz_Effekt'].sum()
    else:
        gesamtkosten, einnahmen, defizit = 0.0, 0.0, 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Kosten (Einkauf / Verlust im Zeitraum)", f"{gesamtkosten:.2f} €")
    col2.metric("Einnahmen (Verkauf im Zeitraum)", f"{einnahmen:.2f} €")
    col3.metric("Reiner Gewinn / Verlust (Bilanz)", f"{defizit:.2f} €")

    df_finanz_all = df_historie.copy()
    
    st.markdown("### 📈 Kontoverlauf / Gesamtbilanz")
    if df_finanz_all.empty:
        st.info("Es sind noch keine Transaktionen erfasst worden.")
    else:
        df_finanz_all['Zeitpunkt'] = pd.to_datetime(df_finanz_all['Zeitpunkt'])
        df_finanz_all = df_finanz_all.sort_values(by='Zeitpunkt')
        df_finanz_all['Finanz_Effekt'] = pd.to_numeric(df_finanz_all['Finanz_Effekt'], errors='coerce').fillna(0.0)
        
        df_finanz_all['Gesamtbilanz'] = df_finanz_all['Finanz_Effekt'].cumsum()
        
        df_finanz_filtered = df_finanz_all.copy()
        if zeitraum == "Year":
            df_finanz_filtered = df_finanz_filtered[df_finanz_filtered['Zeitpunkt'].dt.year == ausgewaehltes_jahr]
        elif zeitraum == "Monthly":
            df_finanz_filtered = df_finanz_filtered[
                (df_finanz_filtered['Zeitpunkt'].dt.year == ausgewaehltes_jahr) & 
                (df_finanz_filtered['Zeitpunkt'].dt.month == ausgewaehlter_monat)
            ]
            
        if df_finanz_filtered.empty:
            st.info(f"Keine Transaktionen im ausgewählten Zeitraum ({zeitraum}).")
        else:
            fig_gesamt = px.line(
                df_finanz_filtered, 
                x='Zeitpunkt', 
                y='Gesamtbilanz', 
                title=f"Kumulierte Finanz-Bilanz des Sortiments ({zeitraum})",
                labels={'Gesamtbilanz': 'Kontostand / Bilanz (€)', 'Zeitpunkt': 'Zeitpunkt'},
                line_shape='spline',
                markers=True
            )
            fig_gesamt.update_traces(line_color='#2ec4b6' if defizit >= 0 else '#ff4b4b', line_width=3)
            fig_gesamt.add_hline(y=0, line_dash="dash", line_color="rgba(255, 255, 255, 0.4)", annotation_text="Nullgrenze")
            st.plotly_chart(fig_gesamt, width="stretch")
