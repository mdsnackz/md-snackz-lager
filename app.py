import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="MD Snackz Lager", page_icon="📦", layout="centered")

# ==========================================
# 🔒 PASSWORT-SCHUTZ (LOGIN-MAUER)
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.title("🔒 MD Snackz – Lager-Login")
    
    eingabe_passwort = st.text_input("Bitte Passwort eingeben:", type="password", placeholder="Dein Passwort...")
    
    if st.button("Einloggen", type="primary", use_container_width=True):
        if eingabe_passwort == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Falsches Passwort! Zugriff verweigert.")
    st.stop()


# ==========================================
# 🌐 GOOGLE SHEETS VERBINDUNG
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_daten():
    try:
        df_b = conn.read(worksheet="Bestand", ttl=0)
        if df_b.empty or "Barcode" not in df_b.columns:
            df_b = pd.DataFrame(columns=["Barcode", "Name", "MHD", "Menge", "Kaufpreis", "Verkaufspreis"])
        else:
            df_b["Barcode"] = df_b["Barcode"].astype(str)
            df_b['MHD'] = pd.to_datetime(df_b['MHD']).dt.date
    except Exception:
        df_b = pd.DataFrame(columns=["Barcode", "Name", "MHD", "Menge", "Kaufpreis", "Verkaufspreis"])
    
    try:
        df_h = conn.read(worksheet="Historie", ttl=0)
        if df_h.empty or "Barcode" not in df_h.columns:
            df_h = pd.DataFrame(columns=["Zeitpunkt", "Barcode", "Name", "Typ", "Menge", "Bestand_Danach", "Kaufpreis", "Verkaufspreis"])
        else:
            df_h["Barcode"] = df_h["Barcode"].astype(str)
            df_h['Zeitpunkt'] = pd.to_datetime(df_h['Zeitpunkt'])
    except Exception:
        df_h = pd.DataFrame(columns=["Zeitpunkt", "Barcode", "Name", "Typ", "Menge", "Bestand_Danach", "Kaufpreis", "Verkaufspreis"])
        
    return df_b, df_h

def save_daten(df_b, df_h):
    df_b_save = df_b.copy()
    df_h_save = df_h.copy()
    if not df_b_save.empty:
        df_b_save['MHD'] = df_b_save['MHD'].astype(str)
    if not df_h_save.empty:
        df_h_save['Zeitpunkt'] = df_h_save['Zeitpunkt'].astype(str)
        
    # Die korrekte Methode für gsheets-connection ist .update()
    conn.update(worksheet="Bestand", data=df_b_save)
    conn.update(worksheet="Historie", data=df_h_save)

df_bestand, df_historie = load_daten()

def get_gesamtbestand(barcode, df_b):
    if df_b.empty: return 0
    return df_b[df_b["Barcode"] == barcode]["Menge"].sum()


# ==========================================
# 🍔 SEITEN-NAVIGATION
# ==========================================
if "ansicht" not in st.session_state:
    st.session_state.ansicht = "🔄 Schnell-Buchung"

st.sidebar.title("📦 MD Snackz")
st.sidebar.markdown(f"🔓 Eingeloggt")
st.sidebar.markdown("<br>", unsafe_allow_html=True)

if st.sidebar.button("🔄 Schnell-Buchung", use_container_width=True, type="primary" if st.session_state.ansicht == "🔄 Schnell-Buchung" else "secondary"):
    st.session_state.ansicht = "🔄 Schnell-Buchung"
    st.rerun()

if st.sidebar.button("📊 Bestands-Tabelle", use_container_width=True, type="primary" if st.session_state.ansicht == "📊 Bestands-Tabelle" else "secondary"):
    st.session_state.ansicht = "📊 Bestands-Tabelle"
    st.rerun()

if st.sidebar.button("🔍 Einzel-Produkt Einsicht", use_container_width=True, type="primary" if st.session_state.ansicht == "🔍 Einzel-Produkt Einsicht" else "secondary"):
    st.session_state.ansicht = "🔍 Einzel-Produkt Einsicht"
    st.rerun()

st.sidebar.markdown("---")
ansicht = st.session_state.ansicht


# ==========================================
# SEITE 1: SCHNELL-BUCHUNG
# ==========================================
if ansicht == "🔄 Schnell-Buchung":
    st.title("🔄 Ware scannen & buchen")
    
    if st.button("Abmelden 🚪", key="logout_btn"):
        st.session_state.authenticated = False
        st.rerun()
        
    if "reset_key" not in st.session_state:
        st.session_state.reset_key = 0

    barcode = st.text_input("Barcode scannen / eingeben", key=f"barcode_{st.session_state.reset_key}", placeholder="Hier scannen...")
    
    if barcode:
        barcode = str(barcode).strip()
        
        bekannter_name = ""
        bekannter_kauf = 0.0
        bekannter_verkauf = 0.0
        
        if not df_bestand.empty and barcode in df_bestand["Barcode"].values:
            row = df_bestand[df_bestand["Barcode"] == barcode].iloc[0]
            bekannter_name = row["Name"]
            bekannter_kauf = float(row["Kaufpreis"])
            bekannter_verkauf = float(row["Verkaufspreis"])
        elif not df_historie.empty and barcode in df_historie["Barcode"].values:
            row = df_historie[df_historie["Barcode"] == barcode].iloc[-1]
            bekannter_name = row["Name"]
            bekannter_kauf = float(row["Kaufpreis"])
            bekannter_verkauf = float(row["Verkaufspreis"])
            
        akt_bestand = get_gesamtbestand(barcode, df_bestand)
        
        if bekannter_name:
            st.success(f"**{bekannter_name}** erkannt! (Bestand: {akt_bestand} Stück | Einkauf: {bekannter_kauf:.2f}€ | Verkauf: {bekannter_verkauf:.2f}€)")
        else:
            st.info("✨ Neues Produkt erkannt! Bitte gib einmalig den Namen und die Preise an.")
            
        aktion = st.radio("Aktion wählen:", [
            "📥 Wareneingang (Einkauf)", 
            "📤 Warenausgang (Entnahme)",
            "⚠️ Korrektur (Im Automat abgelaufen)"
        ], key=f"aktion_{st.session_state.reset_key}")
        
        if aktion == "📥 Wareneingang (Einkauf)":
            if not bekannter_name:
                p_name = st.text_input("Produkt-Name", key=f"name_{st.session_state.reset_key}")
                k_preis = st.number_input("Einkaufspreis pro Stück (€)", min_value=0.00, format="%.2f", step=None, key=f"kauf_{st.session_state.reset_key}")
                v_preis = st.number_input("Verkaufspreis pro Stück (€)", min_value=0.00, format="%.2f", step=None, key=f"verkauf_{st.session_state.reset_key}")
            else:
                p_name = bekannter_name
                k_preis = bekannter_kauf
                v_preis = bekannter_verkauf
                
            menge = st.number_input("Anzahl Packungen / Stück", min_value=1, value=1, step=None, key=f"menge_{st.session_state.reset_key}")
            mhd = st.date_input("MHD eingeben", datetime.date.today() + datetime.timedelta(days=90), key=f"mhd_{st.session_state.reset_key}")
            
            if st.button("Einkauf buchen", type="primary"):
                if p_name:
                    same_batch = df_bestand[(df_bestand["Barcode"] == barcode) & (df_bestand["MHD"] == mhd)]
                    if not same_batch.empty:
                        df_bestand.loc[same_batch.index[0], "Menge"] = int(df_bestand.loc[same_batch.index[0], "Menge"]) + int(menge)
                    else:
                        neu_row = pd.DataFrame([{"Barcode": barcode, "Name": p_name, "MHD": mhd, "Menge": int(menge), "Kaufpreis": k_preis, "Verkaufspreis": v_preis}])
                        df_bestand = pd.concat([df_bestand, neu_row], ignore_index=True)
                    
                    neu_hist = pd.DataFrame([{"Zeitpunkt": datetime.datetime.now(), "Barcode": barcode, "Name": p_name, "Typ": "Einkauf", "Menge": int(menge), "Bestand_Danach": get_gesamtbestand(barcode, df_bestand), "Kaufpreis": k_preis, "Verkaufspreis": v_preis}])
                    df_historie = pd.concat([df_historie, neu_hist], ignore_index=True)
                    
                    save_daten(df_bestand, df_historie)
                    st.session_state.reset_key += 1
                    st.rerun()
                else:
                    st.error("Bitte einen Produktnamen eingeben.")
                    
        elif aktion == "📤 Warenausgang (Entnahme)":
            if akt_bestand > 0:
                menge_raus = st.number_input("Anzahl entnehmen", min_value=1, max_value=int(akt_bestand), value=1, step=None, key=f"menge_raus_{st.session_state.reset_key}")
                
                if st.button("Entnahme buchen", type="primary"):
                    p_name = bekannter_name
                    menge_zu_entnehmen = int(menge_raus)
                    
                    idx_liste = df_bestand[df_bestand["Barcode"] == barcode].sort_values(by="MHD").index.tolist()
                    
                    for idx in idx_liste:
                        if menge_zu_entnehmen <= 0: break
                        akt_zeilen_menge = int(df_bestand.loc[idx, "Menge"])
                        
                        if akt_zeilen_menge <= menge_zu_entnehmen:
                            menge_zu_entnehmen -= akt_zeilen_menge
                            df_bestand = df_bestand.drop(idx)
                        else:
                            df_bestand.loc[idx, "Menge"] = akt_zeilen_menge - menge_zu_entnehmen
                            menge_zu_entnehmen = 0
                    
                    neu_hist = pd.DataFrame([{"Zeitpunkt": datetime.datetime.now(), "Barcode": barcode, "Name": p_name, "Typ": "Entnahme", "Menge": -int(menge_raus), "Bestand_Danach": get_gesamtbestand(barcode, df_bestand), "Kaufpreis": bekannter_kauf, "Verkaufspreis": bekannter_verkauf}])
                    df_historie = pd.concat([df_historie, neu_hist], ignore_index=True)
                    
                    save_daten(df_bestand, df_historie)
                    st.session_state.reset_key += 1
                    st.rerun()
            else:
                st.error("Kein Bestand im Lager zum Entnehmen!")
                
        elif aktion == "⚠️ Korrektur (Im Automat abgelaufen)":
            if bekannter_name:
                st.warning("Diese Buchung reduziert deinen berechneten Gewinn, da das Produkt im Automaten abgelaufen ist.")
                menge_korrektur = st.number_input("Anzahl abgelaufener Produkte", min_value=1, value=1, step=None, key=f"menge_korr_{st.session_state.reset_key}")
                
                if st.button("Korrektur buchen", type="primary"):
                    neu_hist = pd.DataFrame([{
                        "Zeitpunkt": datetime.datetime.now(), 
                        "Barcode": barcode, 
                        "Name": bekannter_name, 
                        "Typ": "Korrektur (Ablauf)", 
                        "Menge": -int(menge_korrektur), 
                        "Bestand_Danach": akt_bestand, 
                        "Kaufpreis": bekannter_kauf, 
                        "Verkaufspreis": bekannter_verkauf
                    }])
                    df_historie = pd.concat([df_historie, neu_hist], ignore_index=True)
                    
                    save_daten(df_bestand, df_historie)
                    st.session_state.reset_key += 1
                    st.rerun()
            else:
                st.error("Dieses Produkt ist neu. Du kannst keine Korrektur für ein Produkt buchen, das noch nie im Lager war.")


# ==========================================
# SEITE 2: BESTANDS-TABELLE
# ==========================================
elif ansicht == "📊 Bestands-Tabelle":
    st.title("📊 Gesamtes Lager")
    
    if not df_bestand.empty:
        übersicht = df_bestand.groupby(["Barcode", "Name", "Kaufpreis", "Verkaufspreis"]).agg(
            Gesamtbestand=("Menge", "sum"),
            Nächstes_MHD=("MHD", "min")
        ).reset_index()
        
        st.dataframe(übersicht.sort_values(by="Nächstes_MHD"), use_container_width=True, hide_index=True)
        
        mhd_warnung = übersicht.sort_values(by="Nächstes_MHD").iloc[0]
        st.error(f"🚨 **Frühestes MHD:** **{mhd_warnung['Name']}** läuft am **{mhd_warnung['Nächstes_MHD'].strftime('%d.%m.%Y')}** ab!")
    else:
        st.info("Das Lager ist aktuell komplett leer.")

    if not df_historie.empty:
        st.write("---")
        st.markdown("### 📈 Gesamter Gewinn- und Verlustverlauf")
        
        df_gesamt_hist = df_historie.sort_values(by="Zeitpunkt").copy()
        
        # FEHLER BEHOBEN: Nutzt jetzt die sichere, eingebaute abs()-Funktion von Python
        def berechne_finanz_effekt_gesamt(r):
            if r['Typ'] == 'Einkauf': 
                return -(abs(float(r['Menge'])) * float(r['Kaufpreis']))
            elif r['Typ'] == 'Entnahme': 
                return abs(float(r['Menge'])) * float(r['Verkaufspreis'])
            elif r['Typ'] == 'Korrektur (Ablauf)': 
                return -(abs(float(r['Menge'])) * float(r['Verkaufspreis']))
            return 0
            
        df_gesamt_hist['Finanz_Effekt'] = df_gesamt_hist.apply(berechne_finanz_effekt_gesamt, axis=1)
        df_gesamt_hist['Bilanz_Verlauf'] = df_gesamt_hist['Finanz_Effekt'].cumsum()
        
        gesamte_bilanz_aktuell = df_gesamt_hist['Bilanz_Verlauf'].iloc[-1] if not df_gesamt_hist.empty else 0.0
        
        fig_gesamt_finanz = px.line(df_gesamt_hist, x="Zeitpunkt", y="Bilanz_Verlauf", markers=True)
        gesamt_linie_farbe = '#2ECC71' if gesamte_bilanz_aktuell >= 0 else '#E74C3C'
        fig_gesamt_finanz.update_traces(line_shape='spline', line_color=gesamt_linie_farbe, line_width=3)
        fig_gesamt_finanz.update_layout(yaxis_title="Gesamt-Gewinn / Verlust (€)", xaxis_title="Zeitverlauf")
        fig_gesamt_finanz.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_gesamt_finanz, use_container_width=True, config={'displayModeBar': False})

    if not df_historie.empty:
        st.write("---")
        st.markdown("### 💰 Produkt-Preise nachträglich anpassen")
        
        alle_produkte = sorted(df_historie["Name"].unique())
        produkt_auswahl = st.selectbox("Wähle ein Produkt aus:", alle_produkte)
        
        akt_kauf = 0.0
        akt_verkauf = 0.0
        if not df_bestand.empty and produkt_auswahl in df_bestand["Name"].values:
            row_b = df_bestand[df_bestand["Name"] == produkt_auswahl].iloc[0]
            akt_kauf = float(row_b["Kaufpreis"])
            akt_verkauf = float(row_b["Verkaufspreis"])
        else:
            row_h = df_historie[df_historie["Name"] == produkt_auswahl].iloc[-1]
            akt_kauf = float(row_h["Kaufpreis"])
            akt_verkauf = float(row_h["Verkaufspreis"])
            
        col_p1, col_p2 = st.columns(2)
        neuer_kaufpreis = col_p1.number_input("Neuer Einkaufspreis (€)", min_value=0.00, value=akt_kauf, format="%.2f")
        neuer_verkaufspreis = col_p2.number_input("Neuer Verkaufspreis (€)", min_value=0.00, value=akt_verkauf, format="%.2f")
        
        if st.button("Preise für die Zukunft speichern", type="primary"):
            if not df_bestand.empty and produkt_auswahl in df_bestand["Name"].values:
                p_barcode = df_bestand[df_bestand["Name"] == produkt_auswahl].iloc[0]["Barcode"]
                df_bestand.loc[df_bestand["Name"] == produkt_auswahl, "Kaufpreis"] = neuer_kaufpreis
                df_bestand.loc[df_bestand["Name"] == produkt_auswahl, "Verkaufspreis"] = neuer_verkaufspreis
            else:
                p_barcode = df_historie[df_historie["Name"] == produkt_auswahl].iloc[-1]["Barcode"]
            
            system_zeile = pd.DataFrame([{
                "Zeitpunkt": datetime.datetime.now(), "Barcode": p_barcode, "Name": produkt_auswahl, "Typ": "Preisänderung", 
                "Menge": 0, "Bestand_Danach": get_gesamtbestand(p_barcode, df_bestand), "Kaufpreis": neuer_kaufpreis, "Verkaufspreis": neuer_verkaufspreis
            }])
            df_historie = pd.concat([df_historie, system_zeile], ignore_index=True)
            
            save_daten(df_bestand, df_historie)
            st.success(f"Preise für '{produkt_auswahl}' angepasst!")
            st.rerun()


# ==========================================
# SEITE 3: EINZEL-PRODUKT EINSICHT
# ==========================================
elif ansicht == "🔍 Einzel-Produkt Einsicht":
    st.title("🔍 Einzel-Produkt Finanz- & Bestandsanalyse")
    
    if not df_historie.empty:
        produkt_liste = df_historie["Name"].unique()
        auswahl = st.selectbox("Welches Produkt möchtest du analysieren?", produkt_liste)
        
        df_produkt_hist = df_historie[df_historie["Name"] == auswahl].sort_values(by="Zeitpunkt")
        
        einzel_kauf = float(df_produkt_hist["Kaufpreis"].iloc[-1]) if not df_produkt_hist.empty else 0.0
        einzel_verkauf = float(df_produkt_hist["Verkaufspreis"].iloc[-1]) if not df_produkt_hist.empty else 0.0
        
        st.info(f"💰 **Aktuelle Preise:** Einkauf: **{einzel_kauf:.2f} €** | Verkauf: **{einzel_verkauf:.2f} €**")
        
        einkäufe = df_produkt_hist[df_produkt_hist["Typ"] == "Einkauf"]
        gesamt_kosten = (einkäufe["Menge"].astype(float) * einkäufe["Kaufpreis"].astype(float)).sum()
        
        entnahmen = df_produkt_hist[df_produkt_hist["Typ"] == "Entnahme"]
        roher_umsatz = (entnahmen["Menge"].astype(float).apply(abs) * entnahmen["Verkaufspreis"].astype(float)).sum()
        
        korrekturen = df_produkt_hist[df_produkt_hist["Typ"] == "Korrektur (Ablauf)"]
        verlust_durch_ablauf = (korrekturen["Menge"].astype(float).apply(abs) * korrekturen["Verkaufspreis"].astype(float)).sum()
        
        gesamt_einnahmen = roher_umsatz - verlust_durch_ablauf
        gewinn_verlust = gesamt_einnahmen - gesamt_kosten
        
        st.write("---")
        st.markdown("### 💰 Finanzielle Übersicht")
        c1, c2, c3 = st.columns(3)
        c1.metric("Gesamtkosten (Einkauf)", f"{gesamt_kosten:.2f} €")
        c2.metric("Tatsächliche Einnahmen", f"{gesamt_einnahmen:.2f} €")
        
        if gewinn_verlust >= 0:
            c3.metric("Reiner Gewinn", f"+{gewinn_verlust:.2f} €", delta=f"{gewinn_verlust:.2f} €")
        else:
            c3.metric("Verlust", f"{gewinn_verlust:.2f} €", delta=f"{gewinn_verlust:.2f} €", delta_color="inverse")
            
        # FEHLER BEHOBEN: Nutzt jetzt ebenfalls die sichere Python-abs()-Funktion
        def berechne_finanz_effekt(r):
            if r['Typ'] == 'Einkauf': 
                return -(abs(float(r['Menge'])) * float(r['Kaufpreis']))
            elif r['Typ'] in ['Entnahme', 'Korrektur (Ablauf)']: 
                return abs(float(r['Menge'])) * float(r['Verkaufspreis'])
            return 0
            
        df_produkt_hist['Finanz_Effekt'] = df_produkt_hist.apply(berechne_finanz_effekt, axis=1)
        df_produkt_hist['Bilanz_Verlauf'] = df_produkt_hist['Finanz_Effekt'].cumsum()
        
        st.write("---")
        st.markdown("### 📈 Gewinn- und Verlustverlauf")
        fig_finanz = px.line(df_produkt_hist, x="Zeitpunkt", y="Bilanz_Verlauf", markers=True)
        linie_farbe = '#2ECC71' if gewinn_verlust >= 0 else '#E74C3C'
        fig_finanz.update_traces(line_shape='spline', line_color=linie_farbe, line_width=3)
        fig_finanz.update_layout(yaxis_title="Gewinn / Verlust (€)", xaxis_title="Zeitverlauf")
        fig_finanz.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_finanz, use_container_width=True, config={'displayModeBar': False})
        
        st.write("---")
        st.markdown("### 📦 Physischer Bestandsverlauf")
        fig_bestand = px.line(df_produkt_hist, x="Zeitpunkt", y="Bestand_Danach", markers=True)
        fig_bestand.update_traces(line_shape='spline', line_color='#FF4B4B', line_width=3)
        fig_bestand.update_layout(yaxis_title="Bestand (Stück)", xaxis_title="Zeitverlauf")
        st.plotly_chart(fig_bestand, use_container_width=True, config={'displayModeBar': False})
        
        st.write("---")
        st.markdown("### 📋 Jede einzelne Buchung im Detail")
        anzeige_tabelle = df_produkt_hist.copy()
        anzeige_tabelle["Zeitpunkt"] = anzeige_tabelle["Zeitpunkt"].dt.strftime("%d.%m.%Y %H:%M")
        
        def berechne_zeilen_gesamt(r):
            if r['Typ'] == 'Einkauf': return abs(float(r['Menge'])) * float(r['Kaufpreis'])
            elif r['Typ'] in ['Entnahme', 'Korrektur (Ablauf)']: return abs(float(r['Menge'])) * float(r['Verkaufspreis'])
            return 0.0
                
        anzeige_tabelle["Gesamtwert (€)"] = anzeige_tabelle.apply(berechne_zeilen_gesamt, axis=1).map("{:.2f} €".format)
        anzeige_tabelle = anzeige_tabelle.rename(columns={"Menge": "Menge (Änderung)", "Bestand_Danach": "Bestand Danach"})
        
        st.dataframe(anzeige_tabelle[["Zeitpunkt", "Typ", "Menge (Änderung)", "Bestand Danach", "Gesamtwert (€)"]], use_container_width=True, hide_index=True)
        
    else:
        st.info("Noch keine Buchungen vorhanden.")
