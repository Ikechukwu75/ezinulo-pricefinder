import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime
import re
import altair as alt

# === Basic Page Configuration ===
st.set_page_config(page_title="ezinụlọ PriceFinder", layout="centered")

# === CSS Styling für Dark Mode, responsives Layout & Custom Progress-Bar ===
def local_css(css_text):
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)

default_css = """
/* Grundlegendes Styling */
body { background-color: #f7f7f7; color: #1f3c60; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

/* Responsives Layout */
@media only screen and (max-width: 768px) {
    .logo { width: 150px; }
}

/* Custom Progress Bar mit Leaf-Icon als Zeiger */
.progress-container {
    position: relative;
    height: 25px;
    background-color: #ddd;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 1rem;
}
.progress-bar {
    height: 100%;
    background-color: #6eb344;
    text-align: center;
    line-height: 25px;
    color: white;
    transition: width 0.3s ease;
}
/* Der "Zeiger": Wir nutzen hier das Logo (das Blatt wird extrahiert – hier simuliert) */
.progress-pointer {
    position: absolute;
    top: -10px;
    width: 40px;
    height: 40px;
    background-image: url("ezinulo_Logo.jpg");
    background-size: contain;
    background-repeat: no-repeat;
    transition: left 0.3s ease;
}
.footer {
    margin-top: 2rem;
    text-align: center;
    font-size: 0.8em;
    color: #888;
}
"""

dark_css = """
body { background-color: #1f1f1f; color: #f7f7f7; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
.progress-container { background-color: #444; }
.progress-bar { background-color: #6eb344; }
.footer { color: #aaa; }
"""

# Standard CSS anwenden
local_css(default_css)

# === Dark Mode Toggle ===
dark_mode = st.checkbox("Dark Mode aktivieren")
if dark_mode:
    local_css(dark_css)

# === Logo und Titel ===
st.image("ezinulo_Logo.jpg", use_column_width=False, output_format="auto", caption="ezinụlọ")
st.markdown("<h2 style='color:#1f3c60;'>ezinụlọ PriceFinder</h2>", unsafe_allow_html=True)
st.write("🚀 Lade eine EAN-Liste hoch und erhalte automatisch den besten Preis auf Google Shopping und Idealo.")

# === Mini-Infoboxen mit Tipps ===
st.info("Tipp: Lade eine Datei mit einer Spalte namens **EAN** hoch. Unterstützt werden .csv und .xlsx.")

# === File Upload ===
uploaded_file = st.file_uploader("📤 EAN-Datei hochladen (.csv oder .xlsx)", type=["csv", "xlsx"])

# === Smart-Filter: Obergrenze für Preise (in Euro) ===
price_filter = st.number_input("Maximalpreis (in Euro, 0 = kein Filter):", min_value=0.0, step=0.1, value=0.0)

# === Funktionen: Preise holen ===

def fetch_google_price(ean):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://www.google.com/search?tbm=shop&q={ean}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        result = soup.select_one('div.sh-dgr__grid-result')

        if result:
            price_elem = result.select_one('span.T14wmb')
            link_elem = result.select_one('a.shntl')

            price = price_elem.text.strip() if price_elem else "Not Found"
            link = "https://www.google.com" + link_elem["href"] if link_elem else "N/A"
            return price, link
    except Exception as e:
        return "Error", "N/A"
    return "Not Found", "N/A"

def fetch_idealo_price(ean):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://www.idealo.de/preisvergleich/MainSearchProductCategory.html?q={ean}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        result = soup.select_one("div.offerList-item")

        if result:
            price_elem = result.select_one(".price")
            link_elem = result.select_one("a")

            price = price_elem.text.strip() if price_elem else "Not Found"
            link = "https://www.idealo.de" + link_elem["href"] if link_elem else "N/A"
            return price, link
    except Exception as e:
        return "Error", "N/A"
    return "Not Found", "N/A"

# Funktion zum Extrahieren numerischer Werte aus Preis-Strings
def parse_price(price_str):
    # Beispiel: "€ 12,34" oder "12,34 €" → 12.34
    try:
        match = re.search(r"(\d+[\.,]?\d*)", price_str.replace(" ", ""))
        if match:
            value = match.group(1).replace(",", ".")
            return float(value)
    except Exception:
        return None
    return None

# === Verarbeitung & Fortschrittsanzeige ===
if uploaded_file:
    # Laden der Datei
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df['EAN'] = df['EAN'].astype(str)
    results = []
    total = len(df)
    
    st.write("### Preisvergleich läuft...")
    progress_bar = st.progress(0)
    progress_container = st.empty()  # Für custom Progress-Balken

    # Für Fortschrittsanzeige mit Pointer: Container für HTML
    progress_html = """
    <div class="progress-container" id="progress-container">
        <div class="progress-bar" id="progress-bar" style="width:0%;">0%</div>
        <div class="progress-pointer" id="progress-pointer" style="left:0%;"></div>
    </div>
    """
    st.markdown(progress_html, unsafe_allow_html=True)

    for idx, ean in enumerate(df['EAN'], start=1):
        st.write(f"Verarbeite EAN {idx} von {total}: {ean}")
        google_price, google_link = fetch_google_price(ean)
        idealo_price, idealo_link = fetch_idealo_price(ean)

        results.append({
            "EAN": ean,
            "Google Preis": google_price,
            "Google Link": google_link,
            "Idealo Preis": idealo_price,
            "Idealo Link": idealo_link
        })
        # Update progress: prozentualer Fortschritt
        progress = int((idx / total) * 100)
        progress_bar.progress(progress)
        # Update custom progress bar via JavaScript injection (simuliert via st.markdown)
        custom_progress = f"""
        <script>
            var progressBar = window.parent.document.getElementById("progress-bar");
            var progressPointer = window.parent.document.getElementById("progress-pointer");
            if(progressBar) {{
                progressBar.style.width = "{progress}%";
                progressBar.innerHTML = "{progress}%";
            }}
            if(progressPointer) {{
                progressPointer.style.left = "{progress}%";
            }}
        </script>
        """
        st.markdown(custom_progress, unsafe_allow_html=True)

    result_df = pd.DataFrame(results)
    
    # Smart-Filter anwenden: Nur Zeilen, bei denen mindestens ein Preis unter dem Limit liegt (sofern gesetzt)
    if price_filter > 0:
        def filter_price(row):
            # Versuche beide Preise zu parsen und vergleiche
            gp = parse_price(str(row["Google Preis"]))
            ip = parse_price(str(row["Idealo Preis"]))
            prices = [p for p in [gp, ip] if p is not None]
            return any(p < price_filter for p in prices) if prices else False
        result_df = result_df[result_df.apply(filter_price, axis=1)]
    
    st.success("✅ Preise erfolgreich ermittelt!")
    st.dataframe(result_df)

    # === Download Buttons für Excel und CSV ===
    buffer_excel = BytesIO()
    result_df.to_excel(buffer_excel, index=False)
    buffer_excel.seek(0)
    
    buffer_csv = result_df.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Ergebnis als Excel herunterladen",
        data=buffer_excel,
        file_name=f"preisvergleich_{datetime.today().date()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.download_button(
        label="📥 Ergebnis als CSV herunterladen",
        data=buffer_csv,
        file_name=f"preisvergleich_{datetime.today().date()}.csv",
        mime="text/csv"
    )
    
    # === Chart: Histogramm der Google Preise (numerisch) ===
    # Extrahiere Preise, falls parsebar
    google_prices = result_df["Google Preis"].apply(lambda x: parse_price(str(x)))
    chart_data = pd.DataFrame({"Google Preise": google_prices.dropna()})
    if not chart_data.empty:
        st.write("### Preisverteilung (Google)")
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X("Google Preise:Q", bin=alt.Bin(maxbins=20), title="Preis in Euro"),
            y=alt.Y("count()", title="Anzahl Produkte")
        ).properties(width=600, height=300)
        st.altair_chart(chart, use_container_width=True)

# === Footer ===
st.markdown("<div class='footer'>Powered by ezinụlọ 🌿</div>", unsafe_allow_html=True)
