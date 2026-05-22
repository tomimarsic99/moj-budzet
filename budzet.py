import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(page_title="Automatski Obiteljski Budžet", layout="wide")

# --- PUTANJA ZA TRAJNO SPREMANJE (Desktop) ---
PUTANJA_BAZE = os.path.join(os.path.expanduser("~"), "Desktop", "obiteljski_budzet.csv")

def ucitaj_podatke():
    if os.path.exists(PUTANJA_BAZE):
        try:
            df = pd.read_csv(PUTANJA_BAZE)
            df["Datum"] = pd.to_datetime(df["Datum"]).dt.date
            if "Stalan" not in df.columns:
                df["Stalan"] = False
            return df
        except Exception:
            return pd.DataFrame(columns=["Datum", "Član", "Tip", "Kategorija", "Iznos (EUR)", "Opis", "Stalan"])
    else:
        return pd.DataFrame(columns=["Datum", "Član", "Tip", "Kategorija", "Iznos (EUR)", "Opis", "Stalan"])

def spremi_podatke(df):
    df.to_csv(PUTANJA_BAZE, index=False)

if "baza_transakcija" not in st.session_state:
    st.session_state.baza_transakcija = ucitaj_podatke()

df_sve = st.session_state.baza_transakcija

# --- DANAŠNJI DATUM ---
danas = datetime.date.today()
trenutna_godina = danas.year
trenutni_mjesec_broj = danas.month

mjeseci_imena = ["Siječanj", "Veljača", "Ožujak", "Travanj", "Svibanj", "Lipanj", "Srpanj", "Kolovoz", "Rujan", "Listopad", "Studeni", "Prosinac"]

# --- BOČNI IZBORNIK ---
st.sidebar.title("📌 Navigacija")
stranica = st.sidebar.radio("Idi na:", ["Unos i Trenutno Stanje", "Detaljna Statistika"])

st.sidebar.write("---")
st.sidebar.subheader("🗄️ Arhiva")
pogledaj_arhivu = st.sidebar.checkbox("Pregledaj stare mjesece")

if pogledaj_arhivu and not df_sve.empty:
    sve_godine_u_bazi = sorted(list(set(pd.to_datetime(df_sve["Datum"]).dt.year)), reverse=True)
    if trenutna_godina not in sve_godine_u_bazi:
        sve_godine_u_bazi.insert(0, trenutna_godina)
       
    godina = st.sidebar.selectbox("Odaberi godinu iz arhive:", sve_godine_u_bazi)
    mjesec_ime = st.sidebar.selectbox("Odaberi mjesec iz arhive:", mjeseci_imena, index=trenutni_mjesec_broj-1)
    mjesec_broj = mjeseci_imena.index(mjesec_ime) + 1
else:
    godina = trenutna_godina
    mjesec_broj = trenutni_mjesec_broj
    mjesec_ime = mjeseci_imena[mjesec_broj - 1]

granica_pocetak_mjeseca = pd.Timestamp(year=godina, month=mjesec_broj, day=1)

# --- AUTOMATSKI IZRAČUN OSTATKA ---
preneseni_ostatak = 0.0
if not df_sve.empty:
    df_sve["Privremeni_Datum"] = pd.to_datetime(df_sve["Datum"])
    df_proslost = df_sve[df_sve["Privremeni_Datum"] < granica_pocetak_mjeseca]
    
    if not df_proslost.empty:
        p_prihodi_jednokratni = df_proslost[(df_proslost["Tip"] == "Prihod") & (df_proslost["Stalan"] == False)]["Iznos (EUR)"].sum()
        p_troskovi = df_proslost[df_proslost["Tip"] == "Trošak"]["Iznos (EUR)"].sum()
        p_stednja = df_proslost[df_proslost["Tip"] == "Štednja"]["Iznos (EUR)"].sum()
        
        p_prihodi_stalni = 0.0
        df_stalni_prihodi = df_sve[(df_sve["Tip"] == "Prihod") & (df_sve["Stalan"] == True)]
        
        for idx, red in df_stalni_prihodi.iterrows():
            if red["Privremeni_Datum"] < granica_pocetak_mjeseca:
                broj_mjeseci = (granica_pocetak_mjeseca.year - red["Privremeni_Datum"].year) * 12 + (granica_pocetak_mjeseca.month - red["Privremeni_Datum"].month)
                p_prihodi_stalni += red["Iznos (EUR)"] * broj_mjeseci
                
        preneseni_ostatak = (p_prihodi_jednokratni + p_prihodi_stalni) - p_troskovi - p_stednja

# --- FILTRIRANJE PODATAKA ---
if not df_sve.empty:
    df_sve["Privremeni_Datum"] = pd.to_datetime(df_sve["Datum"])
    df_mjesec_jednokratni = df_sve[(df_sve["Privremeni_Datum"].dt.year == godina) & (df_sve["Privremeni_Datum"].dt.month == mjesec_broj)]
    df_mjesec_stalni = df_sve[(df_sve["Tip"] == "Prihod") & (df_sve["Stalan"] == True) & (df_sve["Privremeni_Datum"] <= granica_pocetak_mjeseca + pd.offsets.MonthEnd(0))]
    df_mjesec = pd.concat([df_mjesec_jednokratni[df_mjesec_jednokratni["Stalan"] == False], df_mjesec_stalni]).drop_duplicates(subset=["Datum", "Član", "Kategorija", "Iznos (EUR)", "Opis", "Stalan"])
else:
    df_mjesec = pd.DataFrame(columns=["Datum", "Član", "Tip", "Kategorija", "Iznos (EUR)", "Opis", "Stalan"])

m_prihodi = df_mjesec[df_mjesec["Tip"] == "Prihod"]["Iznos (EUR)"].sum()
m_troskovi = df_mjesec[df_mjesec["Tip"] == "Trošak"]["Iznos (EUR)"].sum()
m_stednja = df_mjesec[df_mjesec["Tip"] == "Štednja"]["Iznos (EUR)"].sum()
na_raspolaganju = preneseni_ostatak + m_prihodi - m_stednja - m_troskovi

# --- GLAVNI PANEL ---
st.title(f"📊 Obiteljski Budžet: {mjesec_ime} {godina}")
st.write("---")

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("📥 PRIHODI (Ovaj mjesec)", f"{m_prihodi:.2f} €")
with k2:
    st.metric("🐷 ŠTEDNJA (Ovaj mjesec)", f"{m_stednja:.2f} €")
with k3:
    st.metric("⮥ PRENESENO IZ PROŠLOSTI", f"{preneseni_ostatak:.2f} €")
with k4:
    st.metric(label="💳 TRENUTNO NA RASPOLAGANJU", value=f"{na_raspolaganju:.2f} €",
              delta="U plusu ste" if na_raspolaganju >= 0 else "U minusu ste!",
              delta_color="normal" if na_raspolaganju >= 0 else "inverse")
st.write("---")

# --- STRANICA 1: UNOS PODATAKA ---
if stranica == "Unos i Trenutno Stanje":
    st.subheader("➕ Unesi novi financijski događaj")
   
    col1, col2 = st.columns(2)
    with col1:
        tip = st.selectbox("Što unosiš?", ["Trošak", "Prihod", "Štednja"])
        clan = st.selectbox("Član obitelji", ["Zajednički", "Mama", "Tata", "Kći", "Sin"])
        iznos_tekst = st.text_input("Iznos u EUR (npr. 50 ili 12.50):", value="0")
    with col2:
        stalan_prihod = False
        if tip == "Trošak":
            kat = st.selectbox("Kategorija troška", ["Hrana", "Režije", "Prijevoz", "Zabava", "Kredit/Stan", "Ostalo"])
        elif tip == "Prihod":
            kat = st.selectbox("Kategorija prihoda", ["Plaća 1", "Plaća 2", "Najam", "Dodatno"])
            stalan_prihod = st.checkbox("🔄 Ovo je stalan mjesečni prihod (ponavlja se)")
        else:
            kat = st.selectbox("Kategorija štednje", ["Hitni fond", "Putovanja", "Dugoročna štednja"])
           
        datum_unosa = st.date_input("Datum transakcije", datetime.date.today())
        opis = st.text_input("Opis / Napomena")
        
        potvrda = st.button("Spremi u proračun", type="primary")

    if potvrda:
        try:
            iznos_cist = iznos_tekst.replace(",", ".")
            iznos_broj = float(iznos_cist)
            if iznos_broj <= 0:
                st.error("Iznos mora biti veći od 0!")
            else:
                nova_transakcija = pd.DataFrame([{
                    "Datum": datum_unosa, "Član": clan, "Tip": tip,
                    "Kategorija": kat, "Iznos (EUR)": iznos_broj, "Opis": opis, "Stalan": stalan_prihod
                }])
                st.session_state.baza_transakcija = pd.concat([st.session_state.baza_transakcija, nova_transakcija], ignore_index=True)
                spremi_podatke(st.session_state.baza_transakcija)
                st.success("Uspješno spremljeno!")
                st.rerun()
        except ValueError:
            st.error("Greška! Upišite samo brojke.")

    st.write("---")
    st.subheader(f"📋 Popis zapisa aktivnih u: {mjesec_ime}")
    if not df_mjesec.empty:
        for indeks, red in df_mjesec.iterrows():
            originalni_idx_lista = st.session_state.baza_transakcija[
                (st.session_state.baza_transakcija["Datum"] == red["Datum"]) & 
                (st.session_state.baza_transakcija["Kategorija"] == red["Kategorija"]) & 
                (st.session_state.baza_transakcija["Iznos (EUR)"] == red["Iznos (EUR)"]) &
                (st.session_state.baza_transakcija["Opis"] == red["Opis"])
            ].index.tolist()
            
            orig_idx = originalni_idx_lista if originalni_idx_lista else indeks
            
            kol_podaci, col_gumb = st.columns([4, 1])
            with kol_podaci:
                oznaka_stalnog = "🔄 [STALNI] " if red["Stalan"] else ""
                
                # SVE KAKO JE BILO - DODANE SAMO BOJE:
                if red["Tip"] == "Prihod":
                    boja_iznosa = f":green[**+{red['Iznos (EUR)']:.2f} €**]"
                elif red["Tip"] == "Trošak":
                    boja_iznosa = f":red[**-{red['Iznos (EUR)']:.2f} €**]"
                else:
                    boja_iznosa = f":blue[**{red['Iznos (EUR)']:.2f} €**]"
                    
                st.write(f"📅 **{red['Datum']}** | {oznaka_stalnog}👤 {red['Član']} | 🏷️ {red['Kategorija']} | 💰 {boja_iznosa} | 📝 {red['Opis'] if pd.notna(red['Opis']) else ''}")
            with col_gumb:
                if st.button("❌ Ukloni", key=f"del_{red['Kategorija']}_{red['Iznos (EUR)']}_{indeks}"):
                    st.session_state.baza_transakcija = st.session_state.baza_transakcija.drop(orig_idx).reset_index(drop=True)
                    spremi_podatke(st.session_state.baza_transakcija)
                    st.success("Uklonjeno!")
                    st.rerun()
            st.write("---")
    else:
        st.info(f"Nema unesenih podataka za {mjesec_ime}.")

# --- STRANICA 2: DETALJNA STATISTIKA ---
elif stranica == "Detaljna Statistika":
    st.subheader(f"📈 Grafički pregled za {mjesec_ime}")
    if df_mjesec.empty:
        st.info(f"Unesite podatke za {mjesec_ime} kako biste vidjeli grafikone.")
    else:
        g1, g2 = st.columns(2)
        with g1:
            st.write("### 🛑 Troškovi ovog mjeseca")
            df_trosak = df_mjesec[df_mjesec["Tip"] == "Trošak"]
            if not df_trosak.empty:
                po_kat_t = df_trosak.groupby("Kategorija")["Iznos (EUR)"].sum()
                st.bar_chart(po_kat_t)
            else:
                st.info("Nema troškova.")
        with g2:
            st.write("### 🟢 Prihodi ovog mjeseca")
            df_prihod = df_mjesec[df_mjesec["Tip"] == "Prihod"]
            if not df_prihod.empty:
                po_kat_p = df_prihod.groupby("Kategorija")["Iznos (EUR)"].sum()
