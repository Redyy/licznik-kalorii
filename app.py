import streamlit as st
from streamlit_gsheets import GSheetsConnection
import datetime
import pandas as pd
import matplotlib.pyplot as plt

# Ustawienia strony na samym początku
st.set_page_config(page_title="Licznik Kalorii PRO", page_icon="💪", layout="wide")

# 1. Inicjalizacja stanu sesji dla tworzenia paczek i czyszczenia pól
if 'draft_skladniki' not in st.session_state:
    st.session_state.draft_skladniki = []
if 'paczka_key' not in st.session_state:
    st.session_state.paczka_key = 0
if 'dziennik_key' not in st.session_state:
    st.session_state.dziennik_key = 0

# 2. Połączenie z Google Sheets za pomocą Streamlit GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)

# Funkcje pomocnicze do bezpiecznego pobierania i zapisywania danych
def pobierz_posilki():
    try:
        return conn.read(worksheet="posilki", ttl="0d")
    except Exception:
        # Jeśli arkusz jest pusty, zwraca strukturę
        return pd.DataFrame(columns=['id', 'data', 'nazwa', 'waga', 'kcal_100g', 'bialko_100g', 'kcal_total', 'bialko_total'])

def pobierz_paczki():
    try:
        return conn.read(worksheet="paczki_skladniki", ttl="0d")
    except Exception:
        # Jeśli arkusz jest pusty, zwraca strukturę
        return pd.DataFrame(columns=['paczka_nazwa', 'nazwa', 'waga', 'kcal_100g', 'bialko_100g'])

st.title("💪 Mój Zaawansowany Licznik Kalorii i Białka")

now = datetime.datetime.now()
if now.hour < 5:
    domyslna_data = now.date() - datetime.timedelta(days=1)
else:
    domyslna_data = now.date()

# Pasek boczny - Kalendarz i eksport CSV
st.sidebar.header("📅 Ustawienia czasu")
wybrana_data = st.sidebar.date_input("Aktywny dzień (domyślnie wg reguły 5 AM):", domyslna_data)
data_str = str(wybrana_data)

st.sidebar.markdown("---")
st.sidebar.header("💾 Eksport Danych")

df_posilki = pobierz_posilki()

if not df_posilki.empty:
    csv = df_posilki.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📥 Pobierz całą historię jako .csv",
        data=csv,
        file_name='historia_posilkow.csv',
        mime='text/csv'
    )
else:
    st.sidebar.info("Brak danych do eksportu.")

tab_dziennik, tab_paczki = st.tabs(["📊 Dzisiejszy Dziennik", "📦 Zarządzanie Paczkami"])

# --- ZAKŁADKA 2: ZARZĄDZANIE PACZKAMI ---
with tab_paczki:
    st.header("Stwórz nową paczkę produktów (Zestaw)")
    
    nazwa_paczki = st.text_input("Nazwa całej paczki:", placeholder="np. Zestaw McDonald")
    st.write("---")
    
    st.subheader("1. Dodaj produkt do paczki")
    col1, col2, col3, col4 = st.columns(4)
    with col1: s_nazwa = st.text_input("Nazwa produktu:", key=f"s_n_{st.session_state.paczka_key}")
    with col2: s_waga = st.number_input("Waga (g):", min_value=0.0, step=1.0, value=None, key=f"s_w_{st.session_state.paczka_key}")
    with col3: s_kcal = st.number_input("Kcal w 100g:", min_value=0.0, step=1.0, value=None, key=f"s_k_{st.session_state.paczka_key}")
    with col4: s_bialko = st.number_input("Białko w 100g:", min_value=0.0, step=0.1, value=None, key=f"s_b_{st.session_state.paczka_key}")
    
    if st.button("➕ Dodaj do listy (tymczasowo)"):
        if s_nazwa and s_waga is not None and s_kcal is not None and s_bialko is not None:
            st.session_state.draft_skladniki.append({
                "Nazwa": s_nazwa, "Waga (g)": s_waga, "Kcal/100g": s_kcal, "Białko/100g": s_bialko
            })
            st.session_state.paczka_key += 1 
            st.rerun()
        else:
            st.error("Uzupełnij wszystkie 4 pola produktu, aby go dodać!")

    if st.session_state.draft_skladniki:
        st.subheader("2. Podgląd budowanej paczki")
        df_draft = pd.DataFrame(st.session_state.draft_skladniki)
        st.dataframe(df_draft, use_container_width=True)
        
        col_clear, col_save = st.columns([1, 4])
        with col_clear:
            if st.button("Wyczyść listę"):
                st.session_state.draft_skladniki = []
                st.rerun()
        with col_save:
            if st.button("💾 Zapisz całą paczkę do bazy", type="primary"):
                if nazwa_paczki.strip():
                    try:
                        df_paczki_istniejace = pobierz_paczki()
                        
                        # Usunięcie starej paczki o tej samej nazwie, jeśli istniała
                        if not df_paczki_istniejace.empty:
                            df_paczki_istniejace = df_paczki_istniejace[df_paczki_istniejace['paczka_nazwa'] != nazwa_paczki.strip()]
                        
                        nowe_skladniki = []
                        for prod in st.session_state.draft_skladniki:
                            nowe_skladniki.append({
                                'paczka_nazwa': nazwa_paczki.strip(),
                                'nazwa': prod["Nazwa"],
                                'waga': prod["Waga (g)"],
                                'kcal_100g': prod["Kcal/100g"],
                                'bialko_100g': prod["Białko/100g"]
                            })
                        
                        df_nowe = pd.DataFrame(nowe_skladniki)
                        df_paczki_zaktualizowane = pd.concat([df_paczki_istniejace, df_nowe], ignore_index=True)
                        
                        conn.update(worksheet="paczki_skladniki", data=df_paczki_zaktualizowane)
                        
                        st.session_state.draft_skladniki = [] 
                        st.success(f"Paczka '{nazwa_paczki}' została zapisana w Google Sheets!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd zapisu: {e}")
                else:
                    st.error("Podaj nazwę paczki na samej górze przed zapisem!")

    st.write("---")
    
    st.header("🗑️ Usuń istniejącą paczkę")
    df_paczki = pobierz_paczki()
    
    if not df_paczki.empty and 'paczka_nazwa' in df_paczki.columns:
        istniejace_paczki = df_paczki['paczka_nazwa'].unique().tolist()
        opcje_do_usuniecia = ["-- Wybierz paczkę do usunięcia --"] + istniejace_paczki
        paczka_do_usuniecia = st.selectbox("Wybierz paczkę:", opcje_do_usuniecia)
        
        if paczka_do_usuniecia != "-- Wybierz paczkę do usunięcia --":
            if st.button("Usuń tę paczkę trwale"):
                df_paczki_po_usunieciu = df_paczki[df_paczki['paczka_nazwa'] != paczka_do_usuniecia]
                conn.update(worksheet="paczki_skladniki", data=df_paczki_po_usunieciu)
                st.success(f"Paczka '{paczka_do_usuniecia}' została usunięta!")
                st.rerun()
    else:
        st.info("Brak zapisanych paczek w Google Sheets.")

# --- ZAKŁADKA 1: DZIENNIK I PODSUMOWANIE ---
with tab_dziennik:
    df_posilki = pobierz_posilki()
    df_paczki = pobierz_paczki()

    slownik_produktow = {}
    if not df_posilki.empty:
        # Odfiltrowanie pustych nazw
        df_prod = df_posilki[(df_posilki['kcal_100g'].notna()) & (df_posilki['nazwa'] != '')]
        for _, row in df_prod.iterrows():
            slownik_produktow[row['nazwa']] = (row['kcal_100g'], row['bialko_100g'])

    opcje_paczek = ["-- Wybierz paczkę --"]
    if not df_paczki.empty:
        opcje_paczek += df_paczki['paczka_nazwa'].unique().tolist()

    st.subheader(f"Dziennik: {data_str} (Okres: 5:00 - 4:59)")
    
    st.header("➕ Dodaj do dziennika")
    typ_dodawania = st.radio("Wybierz co chcesz dodać:", ["Pojedynczy produkt / Danie", "Zapisaną paczkę (Zestaw)"], horizontal=True)

    if typ_dodawania == "Pojedynczy produkt / Danie":
        nazwa_key = f"nazwa_input_{st.session_state.dziennik_key}"
        if nazwa_key not in st.session_state:
            st.session_state[nazwa_key] = ""
            
        def uzupelnij_nazwe(wybrana_wartosc, klucz):
            st.session_state[klucz] = wybrana_wartosc
            
        nazwa = st.text_input("Nazwa produktu (zacznij wpisywać, by wyszukać w historii):", key=nazwa_key)
        
        domyslne_kcal, domyslne_bialko = None, None
        dynamiczny_sufix = "nowy"
        
        if nazwa:
            if nazwa in slownik_produktow:
                domyslne_kcal, domyslne_bialko = slownik_produktow[nazwa]
                dynamiczny_sufix = nazwa
            else:
                dopasowania = [p for p in slownik_produktow.keys() if nazwa.lower() in p.lower()]
                if dopasowania:
                    st.caption("Czy chodziło Ci o (kliknij, aby wybrać):")
                    cols = st.columns(min(len(dopasowania), 5))
                    for i, dop in enumerate(dopasowania[:5]):
                        cols[i].button(dop, key=f"btn_{dop}_{st.session_state.dziennik_key}", on_click=uzupelnij_nazwe, args=(dop, nazwa_key))

        tryb = st.radio("Sposób wprowadzania:", ["Na 100g + waga porcji", "Całkowita wartość porcji"], horizontal=True)

        if tryb == "Na 100g + waga porcji":
            col1, col2, col3 = st.columns(3)
            with col1:
                waga = st.number_input("Waga porcji (g):", min_value=0.0, step=1.0, value=None, key=f"wg_{st.session_state.dziennik_key}_{dynamiczny_sufix}")
            with col2:
                kcal_100g = st.number_input("Kalorie w 100g (kcal):", min_value=0.0, step=1.0, value=domyslne_kcal, key=f"kc_{st.session_state.dziennik_key}_{dynamiczny_sufix}")
            with col3:
                bialko_100g = st.number_input("Białko w 100g (g):", min_value=0.0, step=0.1, value=domyslne_bialko, key=f"bi_{st.session_state.dziennik_key}_{dynamiczny_sufix}")
            
            if waga is not None and kcal_100g is not None and bialko_100g is not None:
                kcal_total = round((waga * kcal_100g) / 100.0, 1)
                bialko_total = round((waga * bialko_100g) / 100.0, 1)
            else:
                kcal_total, bialko_total = None, None
        else:
            col1, col2 = st.columns(2)
            with col1:
                kcal_total = st.number_input("Łączne kalorie (kcal):", min_value=0.0, step=1.0, value=None, key=f"kctot_{st.session_state.dziennik_key}_{dynamiczny_sufix}")
            with col2:
                bialko_total = st.number_input("Łączne białko (g):", min_value=0.0, step=0.1, value=None, key=f"bitot_{st.session_state.dziennik_key}_{dynamiczny_sufix}")
            waga, kcal_100g, bialko_100g = None, None, None

        if st.button("Zapisz posiłek", type="primary"):
            if not nazwa:
                st.error("Podaj nazwę!")
            elif kcal_total is None or bialko_total is None:
                st.error("Uzupełnij wartości!")
            else:
                # Generowanie unikalnego ID dla nowego wiersza
                nowy_id = int(df_posilki['id'].max() + 1) if not df_posilki.empty else 1
                
                nowy_wiersz = pd.DataFrame([{
                    'id': nowy_id, 'data': data_str, 'nazwa': nazwa.strip(), 
                    'waga': waga, 'kcal_100g': kcal_100g, 'bialko_100g': bialko_100g, 
                    'kcal_total': kcal_total, 'bialko_total': bialko_total
                }])
                
                df_zaktualizowane = pd.concat([df_posilki, nowy_wiersz], ignore_index=True)
                conn.update(worksheet="posilki", data=df_zaktualizowane)
                
                st.session_state.dziennik_key += 1
                st.rerun()
    else:
        wybrana_paczka = st.selectbox("Wybierz paczkę do załadowania:", opcje_paczek, key=f"paczka_sel_{st.session_state.dziennik_key}")
        if wybrana_paczka != "-- Wybierz paczkę --":
            skladniki = df_paczki[df_paczki['paczka_nazwa'] == wybrana_paczka]
            
            st.write("**Składniki paczki:**")
            for _, skladnik in skladniki.iterrows():
                st.text(f"• {skladnik['nazwa']} - {skladnik['waga']}g (Kcal/100g: {skladnik['kcal_100g']}, B/100g: {skladnik['bialko_100g']})")
                
            if st.button("Dodaj całą paczkę do dziennika", type="primary"):
                nowe_wpisy = []
                start_id = int(df_posilki['id'].max() + 1) if not df_posilki.empty else 1
                
                for _, s in skladniki.iterrows():
                    s_waga = float(s['waga'])
                    s_kcal100 = float(s['kcal_100g'])
                    s_bialko100 = float(s['bialko_100g'])
                    s_kcal_tot = round((s_waga * s_kcal100) / 100.0, 1)
                    s_bialko_tot = round((s_waga * s_bialko100) / 100.0, 1)
                    
                    nowe_wpisy.append({
                        'id': start_id, 'data': data_str, 'nazwa': s['nazwa'], 
                        'waga': s_waga, 'kcal_100g': s_kcal100, 'bialko_100g': s_bialko100, 
                        'kcal_total': s_kcal_tot, 'bialko_total': s_bialko_tot
                    })
                    start_id += 1
                
                df_nowe_wpisy = pd.DataFrame(nowe_wpisy)
                df_zaktualizowane = pd.concat([df_posilki, df_nowe_wpisy], ignore_index=True)
                conn.update(worksheet="posilki", data=df_zaktualizowane)
                
                st.session_state.dziennik_key += 1
                st.rerun()

    st.write("---")
    
    st.subheader("📋 Lista zarejestrowanych posiłków")
    
    # Filtrowanie posiłków na wybrany dzień
    df_dzis = df_posilki[df_posilki['data'] == data_str] if not df_posilki.empty else pd.DataFrame()

    if not df_dzis.empty:
        df_widok = df_dzis.rename(columns={
            'nazwa': 'Produkt/Danie', 'waga': 'Waga (g)', 'kcal_total': 'Kalorie (kcal)', 'bialko_total': 'Białko (g)'
        })
        st.dataframe(df_widok[['Produkt/Danie', 'Waga (g)', 'Kalorie (kcal)', 'Białko (g)']], use_container_width=True)
        
        # Wybór wiersza za pomocą czytelnej nazwy mapowanej na unikalne ID
        lista_id = df_dzis['id'].tolist()
        mapowanie_nazw = {row['id']: f"{row['nazwa']} ({row['kcal_total']} kcal)" for _, row in df_dzis.iterrows()}
        
        id_do_usuniecia = st.selectbox(
            "Usuń pozycję:", lista_id, format_func=lambda x: mapowanie_nazw[x]
        )
        if st.button("Usuń z dziennika"):
            df_posilki_po_usunieciu = df_posilki[df_posilki['id'] != id_do_usuniecia]
            conn.update(worksheet="posilki", data=df_posilki_po_usunieciu)
            st.rerun()
    else:
        st.info("Brak wpisów w bazie dla tego dnia.")

    st.write("---")
    
    st.header("📊 Podsumowanie i realizacja celu")
    
    suma_kcal = float(df_dzis['kcal_total'].sum()) if not df_dzis.empty else 0.0
    suma_bialka = float(df_dzis['bialko_total'].sum()) if not df_dzis.empty else 0.0

    CEL_KCAL = 2700.0
    CEL_BIALKO = 110.0

    wykres_col, tekst_col = st.columns([2, 1])

    with wykres_col:
        fig, ax = plt.subplots(figsize=(6, 3.5))
        
        pct_kcal = (suma_kcal / CEL_KCAL) * 100
        pct_bialko = (suma_bialka / CEL_BIALKO) * 100
        
        if suma_kcal < 2000: color_kcal = '#ff4b4b'
        elif suma_kcal <= 2700: color_kcal = '#faca2b'
        else: color_kcal = '#2ebd59'
            
        if suma_bialka < 70: color_bialko = '#ff4b4b'
        elif suma_bialka <= 110: color_bialko = '#faca2b'
        else: color_bialko = '#2ebd59'

        bars = ax.bar(['Kalorie', 'Białko'], [pct_kcal, pct_bialko], color=[color_kcal, color_bialko], width=0.5)
        ax.axhline(100, color='#808080', linestyle='--', linewidth=1.5, label='Linia Celu')
        
        ax.set_ylim(0, max(120, pct_kcal + 20, pct_bialko + 20))
        ax.set_ylabel('% Realizacji Celu', fontsize=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        ax.text(0, pct_kcal + 3, f"{suma_kcal:.0f} / {CEL_KCAL:.0f} kcal", ha='center', va='bottom', fontweight='bold', fontsize=11)
        ax.text(1, pct_bialko + 3, f"{suma_bialka:.1f} / {CEL_BIALKO:.0f} g", ha='center', va='bottom', fontweight='bold', fontsize=11)
        
        st.pyplot(fig)

    with tekst_col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("### 🎯 Brakuje:")
        brak_kcal = CEL_KCAL - suma_kcal
        brak_bialka = CEL_BIALKO - suma_bialka
        
        if brak_kcal > 0: st.metric("Pozostałe Kalorie", f"{brak_kcal:.0f} kcal")
        else: st.success("Cel kaloryczny osiągnięty! 🥳")
            
        if brak_bialka > 0: st.metric("Pozostałe Białko", f"{brak_bialka:.1f} g")
        else: st.success("Cel białkowy osiągnięty! 🥳")