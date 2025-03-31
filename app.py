import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime
import re
import altair as alt
import base64
import concurrent.futures

# === Basic Page Configuration ===
st.set_page_config(page_title="ezinụlọ PriceFinder", layout="centered")

# === CSS Styling für Dark Mode, responsives Layout & Custom Progress-Bar ===
def local_css(css_text):
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)

# === Ergebnisanzeige Schritt 4 ===
st.markdown("""<hr style='margin-top: 2rem; margin-bottom: 1rem;'>""", unsafe_allow_html=True)
st.markdown("### 📊 Schritt 4: Ergebnisse anzeigen & exportieren")

uploaded_file = st.file_uploader("Wähle deine Datei mit EANs", type=["csv", "xlsx"])

def scrape_google_price(query):
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.google.com/search?tbm=shop&q={query}"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        price = soup.select_one("span.a8Pemb")
        return price.text.strip() if price else None
    except Exception:
        return None

def scrape_idealo_price(query):
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.idealo.de/preisvergleich/MainSearchProductCategory.html?q={query}"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        price = soup.select_one("div.offerList-price span")
        return price.text.strip() if price else None
    except Exception:
        return None

def fallback_price_scraper(ean, name):
    google = scrape_google_price(ean) or scrape_google_price(name)
    idealo = scrape_idealo_price(ean) or scrape_idealo_price(name)
    return google, idealo

def recommend_prices(g_price, i_price):
    try:
        g = float(re.sub(r"[^\d.]", "", g_price)) if g_price else None
        i = float(re.sub(r"[^\d.]", "", i_price)) if i_price else None
        prices = [p for p in [g, i] if p is not None]
        avg = sum(prices) / len(prices) if prices else 0
        uvp = round(avg * 1.3, 2)
        b2b = round(avg / 1.8, 2) if avg else 0
        faktor = 1.3
        marge = round(((uvp - avg) / uvp) * 100, 2) if uvp else 0
        return uvp, b2b, faktor, marge
    except:
        return 0, 0, 0, 0

def calculate_margin_vs_ek(preis, ek):
    try:
        if preis and ek and ek > 0:
            return round(((preis - ek) / preis) * 100, 2)
        else:
            return 0
    except:
        return 0

def style_marge(m):
    if m >= 30:
        return f'<span style="color:green;font-weight:bold;">{m}%</span>'
    elif m >= 15:
        return f'<span style="color:orange;font-weight:bold;">{m}%</span>'
    else:
        return f'<span style="color:red;font-weight:bold;">{m}%</span>'

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if "EAN" not in df.columns or "EK" not in df.columns or "Name" not in df.columns:
            st.error("Die Datei muss die Spalten 'EAN', 'Name' und 'EK' enthalten.")
        else:
            df_result = df.copy()

            progress_bar = st.progress(0)
            status_text = st.empty()

            google_results = {}
            idealo_results = {}

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_row = {
                    executor.submit(fallback_price_scraper, row["EAN"], row["Name"]): idx
                    for idx, row in df_result.iterrows()
                }

                for i, future in enumerate(concurrent.futures.as_completed(future_to_row)):
                    idx = future_to_row[future]
                    g_price, i_price = future.result()
                    google_results[df_result.at[idx, "EAN"]] = g_price
                    idealo_results[df_result.at[idx, "EAN"]] = i_price
                    progress_bar.progress((i + 1) / len(df_result))
                    status_text.text(f"{i+1}/{len(df_result)} verarbeitet...")

            df_result["Google Preis"] = df_result["EAN"].map(google_results)
            df_result["Idealo Preis"] = df_result["EAN"].map(idealo_results)

            df_result["UVP"], df_result["B2B"], df_result["Multiplikator"], df_result["Marge"] = zip(*df_result.apply(lambda row: recommend_prices(row["Google Preis"], row["Idealo Preis"]), axis=1))
            df_result["Marge"] = df_result["Marge"].astype(float)

            df_result["Marge vs EK"] = df_result.apply(lambda row: calculate_margin_vs_ek(row["UVP"], row["EK"]), axis=1)

            marge_filter = st.slider("🔎 Nur Produkte mit Mindestmarge anzeigen", 0, 100, 0)
            filtered = df_result[df_result["Marge"] >= marge_filter].reset_index(drop=True)

            styled = filtered.copy()
            styled["Marge"] = styled["Marge"].apply(lambda x: style_marge(x), convert_dtype=False)
            styled["Marge vs EK"] = styled["Marge vs EK"].apply(lambda x: style_marge(x), convert_dtype=False)
            st.markdown(styled.to_html(escape=False, index=False), unsafe_allow_html=True)

            chart = alt.Chart(filtered).mark_bar().encode(
                alt.X("Marge", bin=True),
                y='count()'
            ).properties(title="📈 Margenverteilung")
            st.altair_chart(chart, use_container_width=True)

            st.markdown("#### 📥 Exportiere die Ergebnisse")
            csv = filtered.to_csv(index=False).encode("utf-8")
            st.download_button("💾 CSV herunterladen", csv, "preisfinder_ergebnisse.csv", "text/csv", key='download-csv')

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
