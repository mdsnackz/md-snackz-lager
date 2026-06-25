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

# Navigation State initialisieren
if 'menu_option' not in st.session_state:
    st.session_state['menu_option'] = "🏠 Dashboard"

def go_to_dashboard():
    st.session_state['menu_option'] = "🏠 Dashboard"

# --- HILFSFUNKTION: TABELLEN SAUBER FORMATIEREN & EINFÄRBEN ---
def style_buchungen(df):
    """Kappt Nullen, formatiert Euro und färbt die Tabelle ein."""
    df_clean = df.copy()
    
    # 1. Mengen zu reinen Zahlen machen (ohne .000000)
    if 'Menge' in df_clean.columns:
        df_clean['Menge'] = pd.to_numeric(df_clean['Menge'], errors='coerce').fillna(0).astype(int)
        
    # Finanzen zu Zahlen casten für die spätere Währungsformatierung
    for col in ['Finanz_Effekt', 'Kaufpreis', 'Verkaufspreis']:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0.0)
            
    styler = df_clean.style
    
    # 2. Währungen sauber mit 2 Nachkommastellen anzeigen
    format_dict = {}
    for col in ['Finanz_Effekt', 'Kaufpreis', 'Verkaufspreis']:
        if col in df_clean.columns:
            format_dict[col] = "{:.2f} €"
    if format_dict:
        styler = styler.format(format_dict)
        
    # 3. Farben definieren
    def color_aktion(val):
        if val == "Wareneingang": return 'color: #ff4b4b; font-weight: bold;' # Rot
        elif val == "Warenausgang (Verkauf)": return 'color: #2ec4b6; font-weight: bold;' # Grün
        elif "Ausschuss" in str(val): return 'color: #ffca28; font-weight: bold;' # Gelb
        return ''
        
    def color_finanz(val):
        if isinstance(val, (int, float)):
            if val > 0: return 'color: #2ec4b6; font-weight: bold;'
            elif val < 0: return 'color: #ff4b4b; font-weight: bold;'
        return ''

    # 4. Farben anwenden
    try:
        if 'Aktion' in df_clean.columns: styler = styler.map(color_aktion, subset=['Aktion'])
        if 'Finanz_Effekt' in df_clean.columns: styler = styler.map(color_finanz, subset=['Finanz_Effekt'])
    except AttributeError:
        if 'Aktion' in df_clean.columns: styler = styler.applymap(color_aktion, subset=['Aktion'])
        if 'Finanz_Effekt' in df_clean.columns: styler = styler.applymap(color_finanz, subset=['Finanz_Effekt'])
            
    return styler

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

df_bestand, df_historie = load_daten()

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    /* Styling für das Seitenmenü */
    div[data-testid="stRadio"] div[role="radiogroup"] { display: flex; flex-direction: column; gap: 12px; }
    div[data-testid="stRadio"] div[role="radiogroup"] > label {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 14px 18px !important; border-radius: 10px !important;
        color: white !important; display: flex !important; align-items: center !important;
        width: 100% !important; cursor: pointer !important; transition: all 0.2s ease-in-out;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.1) !important; border-color: rgba(255, 255, 255, 0.2) !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #ff4b4b !important; border-color: #ff4b4b !important;
        font-weight: bold !important; box-shadow: 0px 4px 10px rgba(255, 75, 75, 0.3);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p {
        font-size: 16px !important; margin: 0 !important;
    }
    div[data-testid="stRadio"] [data-testid="stWidgetLabel"] { display: none !important; }
    
    /* MD SNACKZ LOGO (Kein Button-Design mehr, nur Text!) */
    div[data-testid="stSidebar"] div.stButton:first-of-type > button {
        background: transparent !important;
        border: none !important; 
        box-shadow: none !important;
        padding: 0 !important; 
        margin-bottom: 20px !important;
        display: flex !important;
        justify-content: flex-start !important;
    }
    div[data-testid="stSidebar"] div.stButton:first-of-type > button p { 
        font-size: 42px !important; 
        font-weight: 900 !important; 
        color: #ff4b4b !important; 
        margin: 0 !important; 
        font-family: 'Arial', sans-serif !important;
        letter-spacing: -1px !important;
    }
    div[data-testid="stSidebar"] div.stButton:first-of-type > button:hover p { 
        color: #ff7676 !important; 
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
st.sidebar.button("MD Snackz", on_click=go_to_dashboard, use_container_width=True)

menu = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "📊 Bestands-Tabelle", "🔍 Einzel-Produkt Einsicht", "💰 Finanzielle Übersicht"],
    key="menu_option"
)

st.sidebar.markdown("---")

# --- ZEITFILTER-LOGIK FÜR ANDERE SEITEN ---
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

# --- ANSICHT 1: 🏠 DASHBOARD ---
if menu == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    
    # 1. BEREICH: SCHNELL-BUCHUNG
    st.markdown("### 🔄 Produkt-Buchung")
    if 'success_msg' in st.session_state:
        st.success(st.session_state['success_msg'])
        del st.session_state['success_msg']
        
    barcode_input = st.text_input("Barcode scannen / eingeben", key="schnell_barcode").strip()
    
    if barcode_input:
        barcode_clean = str(barcode_input).replace('.0', '').strip()
        idx = df_bestand[df_bestand['Barcode'] == barcode_clean].index
        exists = not idx.empty
        
        aktion = st.selectbox("Aktion", ["Wareneingang", "Warenausgang (Verkauf)", "Ausschuss / Defekt (Umsatzverlust)"])
        
        with st.form("buchung_details_form", clear_on_submit=True):
            if not exists:
                st.warning(f"🆕 Neues Produkt mit Barcode {barcode_clean} erkannt.")
                artikelname = st.text_input("Artikelname (Pflichtfeld)").strip()
                default_kp = 0.0; default_vp = 0.0; default_mhd = datetime.today().date()
            else:
                current_name = df_bestand.loc[idx[0], 'Artikelname']
                st.info(f"✅ Produkt im Bestand: **{current_name}**")
                artikelname = current_name
                try: default_kp = float(df_bestand.loc[idx[0], 'Kaufpreis']) if pd.notna(df_bestand.loc[idx[0], 'Kaufpreis']) else 0.0
                except: default_kp = 0.0
                try: default_vp = float(df_bestand.loc[idx[0], 'Verkaufspreis']) if pd.notna(df_bestand.loc[idx[0], 'Verkaufspreis']) else 0.0
                except: default_vp = 0.0
                try: default_mhd = pd.to_datetime(df_bestand.loc[idx[0], 'MHD']).date()
                except: default_mhd = datetime.today().date()
            
            c_menge, c_kp, c_vp = st.columns(3)
            with c_menge: menge = st.number_input("Menge", min_value=1, step=1, value=1)
            with c_kp: kaufpreis = st.number_input("Kaufpreis (€)", min_value=0.0, step=0.01, value=default_kp)
            with c_vp: verkaufspreis = st.number_input("Verkaufspreis (€)", min_value=0.0, step=0.01, value=default_vp)
            
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
                    kp = kaufpreis; vp = verkaufspreis
                    
                    if aktion == "Wareneingang":
                        neue_menge = current_menge + menge; finanz_effekt = -(menge * kp); historie_menge = menge
                    elif aktion == "Warenausgang (Verkauf)":
                        neue_menge = max(0, current_menge - menge); finanz_effekt = (menge * vp); historie_menge = -menge
                    else:
                        neue_menge = current_menge; finanz_effekt = -(menge * vp); historie_menge = 0  
                    
                    new_history_entry = pd.DataFrame([{
                        'Barcode': barcode_clean, 'Artikelname': artikelname, 'Menge': historie_menge,
                        'Aktion': aktion, 'Finanz_Effekt': finanz_effekt, 'Zeitpunkt': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'MHD': str(mhd) if aktion == "Wareneingang" else ""
                    }])
                    df_historie = pd.concat([df_historie, new_history_entry], ignore_index=True)
                    
                    aktueller_mhd = str(default_mhd)
                    if neue_menge > 0:
                        df_we = df_historie[(df_historie['Barcode'] == barcode_clean) & (df_historie['Aktion'] == "Wareneingang")].copy()
                        if not df_we.empty and 'MHD' in df_we.columns:
                            df_we['Zeitpunkt_dt'] = pd.to_datetime(df_we['Zeitpunkt'], errors='coerce')
                            df_we = df_we.sort_values(by='Zeitpunkt_dt', ascending=False)
                            computed_mhd = None; cum_incoming = 0
                            for _, row in df_we.iterrows():
                                try: m_val = int(float(row['Menge']))
                                except: m_val = 0
                                cum_incoming += m_val
                                if cum_incoming >= neue_menge:
                                    val_mhd = str(row['MHD']).strip()
                                    if val_mhd and val_mhd.lower() != 'nan' and val_mhd != "":
                                        computed_mhd = val_mhd
                                        break
                            if computed_mhd: aktueller_mhd = computed_mhd
                    else: aktueller_mhd = ""
                    
                    if exists:
                        df_bestand.loc[idx[0], 'Menge'] = neue_menge; df_bestand.loc[idx[0], 'MHD'] = aktueller_mhd
                        df_bestand.loc[idx[0], 'Kaufpreis'] = kp; df_bestand.loc[idx[0], 'Verkaufspreis'] = vp
                    else:
                        new_product = pd.DataFrame([{'Barcode': barcode_clean, 'Artikelname': artikelname, 'Menge': neue_menge, 'Kaufpreis': kp, 'Verkaufspreis': vp, 'MHD': aktueller_mhd}])
                        df_bestand = pd.concat([df_bestand, new_product], ignore_index=True)
                    
                    save_daten(df_bestand, df_historie)
                    st.session_state['reset_barcode'] = True
                    st.session_state['success_msg'] = f"✅ Erfolgreich gebucht: {aktion} von '{artikelname}' ({menge} Stk.)"
                    st.rerun()

    st.markdown("---")
    
    # 2. BEREICH: CHARTS & LETZTE AKTIONEN NEBENEINANDER
    col_graph, col_table = st.columns([1.2, 1])
    
    with col_graph:
        st.markdown("### 📊 Finanz-Übersicht (All-Time)")
        df_finanz_all = df_historie.copy()
        
        # Zahlen nur oberhalb des Charts platzieren
        if not df_finanz_all.empty:
            df_finanz_all['Finanz_Effekt'] = pd.to_numeric(df_finanz_all['Finanz_Effekt'], errors='coerce').fillna(0.0)
            ausgaben = abs(df_finanz_all[df_finanz_all['Finanz_Effekt'] < 0]['Finanz_Effekt'].sum())
            einnahmen = df_finanz_all[df_finanz_all['Finanz_Effekt'] > 0]['Finanz_Effekt'].sum()
            gewinn = df_finanz_all['Finanz_Effekt'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("🔴 Ausgaben", f"{ausgaben:.2f} €")
            c2.metric("🟢 Einnahmen", f"{einnahmen:.2f} €")
            c3.metric("🔵 Bilanz", f"{gewinn:.2f} €")
            
            st.markdown("#### 📈 Kumulierter Umsatz")
            df_finanz_all['Zeitpunkt'] = pd.to_datetime(df_finanz_all['Zeitpunkt'])
            df_finanz_all = df_finanz_all.sort_values(by='Zeitpunkt')
            df_finanz_all['Gesamtbilanz'] = df_finanz_all['Finanz_Effekt'].cumsum()
            
            fig = px.line(df_finanz_all, x='Zeitpunkt', y='Gesamtbilanz', labels={'Gesamtbilanz': 'Bilanz (€)', 'Zeitpunkt': 'Datum'}, markers=False)
            fig.update_traces(line_color='#2ec4b6', line_width=3, line_shape='spline')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Noch keine Finanzdaten verfügbar.")

    with col_table:
        st.markdown("#### 🕒 Letzte 10 Aktionen")
        df_recent = df_historie.copy()
        if not df_recent.empty:
            df_recent['Zeitpunkt'] = pd.to_datetime(df_recent['Zeitpunkt'])
            # NEU: .head(10) für eine längere Liste
            df_recent = df_recent.sort_values(by='Zeitpunkt', ascending=False).head(10)
            df_recent['Datum'] = df_recent['Zeitpunkt'].dt.strftime('%d.%m. %H:%M')
            
            df_disp = df_recent[['Datum', 'Artikelname', 'Aktion', 'Menge']]
            st.dataframe(style_buchungen(df_disp), hide_index=True, use_container_width=True)
            
    st.markdown("---")
    
    # 3. BEREICH: TOP PERFORMER
    st.markdown("### 🏆 Top Performer (Höchster Gesamtgewinn)")
    if not df_historie.empty:
        df_hist_tp = df_historie.copy()
        df_hist_tp['Finanz_Effekt'] = pd.to_numeric(df_hist_tp['Finanz_Effekt'], errors='coerce').fillna(0.0)
        
        gewinn_pro_produkt = df_hist_tp.groupby('Artikelname')['Finanz_Effekt'].sum().reset_index()
        
        if not gewinn_pro_produkt.empty and gewinn_pro_produkt['Finanz_Effekt'].max() > 0:
            top_produkt = gewinn_pro_produkt.loc[gewinn_pro_produkt['Finanz_Effekt'].idxmax()]
            st.success(f"Dein absoluter Top Performer ist **{top_produkt['Artikelname']}** mit einem Gesamtgewinn von **{top_produkt['Finanz_Effekt']:.2f} €**! 🚀")
            
            df_top = df_hist_tp[df_hist_tp['Artikelname'] == top_produkt['Artikelname']].copy()
            df_top['Zeitpunkt'] = pd.to_datetime(df_top['Zeitpunkt'])
            df_top = df_top.sort_values(by='Zeitpunkt')
            df_top['Kumulierter_Gewinn'] = df_top['Finanz_Effekt'].cumsum()
            
            fig_top = px.line(df_top, x='Zeitpunkt', y='Kumulierter_Gewinn', labels={'Kumulierter_Gewinn': 'Gewinn (€)', 'Zeitpunkt': 'Datum'}, markers=True)
            fig_top.update_traces(line_color='#ffca28', line_width=4, line_shape='spline')
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("Es wurden bisher nur Waren eingekauft oder kein Produkt hat einen positiven Gewinn erzielt.")

# --- ANSICHT 2: BESTANDS-TABELLE ---
elif menu == "📊 Bestands-Tabelle":
    st.subheader("📊 Aktueller Gesamtbestand")
    if df_bestand.empty:
        st.info("Es sind noch keine Produkte im System registriert.")
    else:
        st.dataframe(style_buchungen(df_bestand), width="stretch", hide_index=True)
    
    st.markdown("---")
    
    st.subheader("📜 Buchungshistorie (Alle Änderungen)")
    if df_historie.empty:
        st.info("Es wurden noch keine Buchungen erfasst.")
    else:
        df_hist_sorted = df_historie.copy()
        df_hist_sorted['Zeitpunkt'] = pd.to_datetime(df_hist_sorted['Zeitpunkt'])
        df_hist_sorted = df_hist_sorted.sort_values(by='Zeitpunkt', ascending=False).reset_index(drop=True)

        items_per_page = 10
        total_pages = max(1, (len(df_hist_sorted) - 1) // items_per_page + 1)

        if 'hist_page' not in st.session_state:
            st.session_state.hist_page = 1
        
        if st.session_state.hist_page > total_pages:
            st.session_state.hist_page = total_pages

        start_idx = (st.session_state.hist_page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        df_page = df_hist_sorted.iloc[start_idx:end_idx]
        st.dataframe(style_buchungen(df_page), width="stretch", hide_index=True)

        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("⬅️ Vorherige", disabled=(st.session_state.hist_page <= 1), use_container_width=True):
                st.session_state.hist_page -= 1
                st.rerun()
        with col2:
            st.markdown(f"<div style='text-align: center; padding-top: 5px; font-size: 16px;'>Seite <b>{st.session_state.hist_page}</b> von <b>{total_pages}</b></div>", unsafe_allow_html=True)
        with col3:
            if st.button("Nächste ➡️", disabled=(st.session_state.hist_page >= total_pages), use_container_width=True):
                st.session_state.hist_page += 1
                st.rerun()

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
            
            try: v_menge = int(float(selected_product['Menge']))
            except: v_menge = 0
            c2.metric("Aktuelle Menge", f"{v_menge} Stk.")
            
            try: v_preis = float(selected_product['Verkaufspreis'])
            except: v_preis = 0.0
            c3.metric("Verkaufspreis", f"{v_preis:.2f} €")
            
            c4.metric("MHD (Nächstes)", str(selected_product['MHD']))
            
            df_prod_all = df_historie[df_historie['Barcode'] == selected_barcode].copy()
            
            if df_prod_all.empty:
                st.info("Für dieses Produkt liegt keine Buchungs-Historie vor.")
            else:
                df_prod_all['Zeitpunkt'] = pd.to_datetime(df_prod_all['Zeitpunkt'])
                df_prod_all = df_prod_all.sort_values(by='Zeitpunkt')
                df_prod_all['Menge'] = pd.to_numeric(df_prod_all['Menge'], errors='coerce').fillna(0)
                df_prod_all['Finanz_Effekt'] = pd.to_numeric(df_prod_all['Finanz_Effekt'], errors='coerce').fillna(0.0)
                
                df_prod_all['Tatsächlicher_Bestand'] = df_prod_all['Menge'].cumsum()
                
                df_prod_filtered = df_prod_all.copy()
                if zeitraum == "Year":
                    df_prod_filtered = df_prod_filtered[df_prod_filtered['Zeitpunkt'].dt.year == ausgewaehltes_jahr]
                elif zeitraum == "Monthly":
                    df_prod_filtered = df_prod_filtered[(df_prod_filtered['Zeitpunkt'].dt.year == ausgewaehltes_jahr) & (df_prod_filtered['Zeitpunkt'].dt.month == ausgewaehlter_monat)]
                
                if df_prod_filtered.empty:
                    st.info(f"Keine Aktionen im gewählten Zeitraum ({zeitraum}).")
                else:
                    st.markdown("### 📈 Tatsächlicher Bestandsverlauf")
                    fig_prod = px.line(df_prod_filtered, x='Zeitpunkt', y='Tatsächlicher_Bestand', title=f"Lagerbestand von '{selected_product['Artikelname']}'", markers=True)
                    fig_prod.update_traces(line_color='#2ec4b6', line_width=3, line_shape='spline')
                    st.plotly_chart(fig_prod, width="stretch")
                    
                    st.markdown("### 💰 Umsatz- & Finanzverlauf")
                    df_prod_filtered = df_prod_filtered.sort_values(by='Zeitpunkt')
                    df_prod_filtered['Umsatz_Entwicklung'] = df_prod_filtered['Finanz_Effekt'].cumsum()
                    zeitraum_bilanz = df_prod_filtered['Finanz_Effekt'].sum()
                    
                    fig_umsatz = px.line(df_prod_filtered, x='Zeitpunkt', y='Umsatz_Entwicklung', title=f"Gewinn/Verlust von '{selected_product['Artikelname']}' ({zeitraum})", markers=True)
                    fig_umsatz.update_traces(line_color='#2ec4b6' if zeitraum_bilanz >= 0 else '#ff4b4b', line_width=3, line_shape='spline')
                    fig_umsatz.add_hline(y=0, line_dash="dash", line_color="rgba(255, 255, 255, 0.4)")
                    st.plotly_chart(fig_umsatz, width="stretch")
                
                st.markdown("### 📜 Einzelaktionen im Zeitraum")
                df_prod_filtered_disp = df_prod_filtered.sort_values(by='Zeitpunkt', ascending=False)
                st.dataframe(style_buchungen(df_prod_filtered_disp), width="stretch", hide_index=True)

# --- ANSICHT 4: FINANZIELLE ÜBERSICHT ---
elif menu == "💰 Finanzielle Übersicht":
    st.markdown("# 💰 Finanzielle Übersicht & Bilanz")

    df_hist_calc = df_historie.copy()
    if not df_hist_calc.empty:
        df_hist_calc['Zeitpunkt'] = pd.to_datetime(df_hist_calc['Zeitpunkt'])
        if zeitraum == "Year":
            df_hist_calc = df_hist_calc[df_hist_calc['Zeitpunkt'].dt.year == ausgewaehltes_jahr]
        elif zeitraum == "Monthly":
            df_hist_calc = df_hist_calc[(df_hist_calc['Zeitpunkt'].dt.year == ausgewaehltes_jahr) & (df_hist_calc['Zeitpunkt'].dt.month == ausgewaehlter_monat)]

    if not df_hist_calc.empty and 'Finanz_Effekt' in df_hist_calc.columns:
        df_hist_calc['Finanz_Effekt'] = pd.to_numeric(df_hist_calc['Finanz_Effekt'], errors='coerce').fillna(0.0)
        gesamtkosten = abs(df_hist_calc[df_hist_calc['Finanz_Effekt'] < 0]['Finanz_Effekt'].sum())
        einnahmen = df_hist_calc[df_hist_calc['Finanz_Effekt'] > 0]['Finanz_Effekt'].sum()
        defizit = df_hist_calc['Finanz_Effekt'].sum()
    else:
        gesamtkosten, einnahmen, defizit = 0.0, 0.0, 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Kosten (Einkauf / Verlust)", f"{gesamtkosten:.2f} €")
    col2.metric("Einnahmen (Verkauf)", f"{einnahmen:.2f} €")
    col3.metric("Bilanz", f"{defizit:.2f} €")

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
            df_finanz_filtered = df_finanz_filtered[(df_finanz_filtered['Zeitpunkt'].dt.year == ausgewaehltes_jahr) & (df_finanz_filtered['Zeitpunkt'].dt.month == ausgewaehlter_monat)]
            
        if df_finanz_filtered.empty:
            st.info(f"Keine Transaktionen im Zeitraum ({zeitraum}).")
        else:
            fig_gesamt = px.line(df_finanz_filtered, x='Zeitpunkt', y='Gesamtbilanz', title=f"Kumulierte Finanz-Bilanz ({zeitraum})", markers=True)
            fig_gesamt.update_traces(line_color='#2ec4b6' if defizit >= 0 else '#ff4b4b', line_width=3, line_shape='spline')
            fig_gesamt.add_hline(y=0, line_dash="dash", line_color="rgba(255, 255, 255, 0.4)")
            st.plotly_chart(fig_gesamt, width="stretch")
