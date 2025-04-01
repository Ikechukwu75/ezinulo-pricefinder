import streamlit as st
import pandas as pd
import requests
import concurrent.futures

st.set_page_config(page_title="ezinụlọ PriceFinder", layout="centered")

st.image("https://raw.githubusercontent.com/yourusername/yourrepo/main/ezinulo_Logo.jpg", width=100)
st.markdown("# 🌿 Willkommen beim ezinụlọ PriceFinder")
st.markdown("Nutze diesen Preisfinder, um automatisch Google Shopping-Preise zu recherchieren, UVP & B2B-Preise zu berechnen und Daten als CSV zu exportieren.")

with st.expander("⚙️ Einstellungen anzeigen"):
    marge_filter = st.slider("🔎 Nur Produkte mit Mindestmarge anzeigen (%)", 0, 100, 0)
    anzeigen_limit = st.number_input("🔢 Maximale Anzahl an Produkten laden", min_value=1, max_value=5000, value=100)
    dark_mode = st.checkbox("🌙 Dark Mode aktivieren")

st.markdown("### 🚀 Schritt 3: Lade eine Datei hoch")
st.info("Die Datei muss mindestens die Spalten `EAN`, `Name` und `EK` enthalten.")

SERPSTACK_API_KEY = st.secrets["SERPSTACK_API_KEY"]

def scrape_google_price_serpstack(query):
    try:
        url = "http://api.serpstack.com/search"
        params = {"access_key": SERPSTACK_API_KEY, "query": query, "type": "shopping"}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        shopping_results = data.get("shopping_results", [])
        if shopping_results:
            price_str = shopping_results[0].get("price", "").replace("€", "").replace(",", ".").strip()
            link_str = shopping_results[0].get("url", "")
            return float(price_str) if price_str else None, link_str
        return None, None
    except Exception:
        return None, None

uploaded_file = st.file_uploader("Wähle deine Datei mit EANs", type=["csv", "xlsx"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        if "EAN" not in df.columns or "EK" not in df.columns or "Name" not in df.columns:
            st.error("Die Datei muss die Spalten 'EAN', 'Name' und 'EK' enthalten.")
        else:
            df_result = df.copy().head(anzeigen_limit)
            progress_bar = st.progress(0)
            status_text = st.empty()

            google_prices = {}
            google_links = {}

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_row = {
                    executor.submit(scrape_google_price_serpstack, row["EAN"]): idx
                    for idx, row in df_result.iterrows()
                }

                for i, future in enumerate(concurrent.futures.as_completed(future_to_row)):
                    idx = future_to_row[future]
                    g_price, g_link = future.result()
                    google_prices[df_result.at[idx, "EAN"]] = g_price
                    google_links[df_result.at[idx, "EAN"]] = g_link
                    progress_bar.progress((i + 1) / len(df_result))
                    status_text.text(f"🍃 {i+1}/{len(df_result)} verarbeitet...")

            df_result["Google Preis"] = df_result["EAN"].map(google_prices)
            df_result["Google Link"] = df_result["EAN"].map(google_links)
            df_result["Link"] = df_result["Google Link"].apply(lambda url: f'<a href="{url}" target="_blank">🔗 Produkt</a>' if pd.notna(url) else "")

            df_result["Marge %"] = df_result.apply(lambda row: round((row["Google Preis"] - row["EK"]) / row["EK"] * 100, 2) if pd.notna(row["Google Preis"]) else None, axis=1)
            df_result["Marge Hinweis"] = df_result["Marge %"].apply(lambda x: "🟢 OK" if pd.notna(x) and x >= marge_filter else ("🔴 Niedrig" if pd.notna(x) else ""))

            df_filtered = df_result[df_result["Google Preis"].notna()]
            df_filtered = df_filtered[df_filtered["Marge %"] >= marge_filter]

            st.markdown(df_filtered.to_html(escape=False, index=False), unsafe_allow_html=True)
            csv = df_filtered.to_csv(index=False).encode("utf-8")
            st.download_button("💾 CSV herunterladen", csv, "preisfinder_ergebnisse.csv", "text/csv")

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")