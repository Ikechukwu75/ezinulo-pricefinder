
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime

# === Design ===
st.set_page_config(page_title="ezinụlọ PriceFinder", layout="centered")
st.markdown(
    """
    <style>
        .main {background-color: #f7f7f7;}
        .css-1d391kg {background-color: #f7f7f7;}
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .logo {
            width: 200px;
            margin-bottom: 1rem;
        }
        .footer {
            margin-top: 2rem;
            text-align: center;
            font-size: 0.8em;
            color: #888;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# === Logo ===
st.image("ezinulo_Logo.jpg", use_column_width=False)

# === Title ===
st.markdown("<h2 style='color:#1f3c60;'>ezinụlọ PriceFinder</h2>", unsafe_allow_html=True)
st.write("🚀 Lade eine EAN-Liste hoch und erhalte automatisch den besten Preis auf Google Shopping und Idealo.")

# === File Upload ===
uploaded_file = st.file_uploader("📤 EAN-Datei hochladen (.csv oder .xlsx)", type=["csv", "xlsx"])

# === Preischeck Funktion ===
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
    except Exception:
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
    except Exception:
        return "Error", "N/A"
    return "Not Found", "N/A"

# === Datenverarbeitung ===
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df['EAN'] = df['EAN'].astype(str)
    results = []

    with st.spinner("🔍 Preise werden gesucht..."):
        for ean in df['EAN']:
            google_price, google_link = fetch_google_price(ean)
            idealo_price, idealo_link = fetch_idealo_price(ean)

            results.append({
                "EAN": ean,
                "Google Preis": google_price,
                "Google Link": google_link,
                "Idealo Preis": idealo_price,
                "Idealo Link": idealo_link
            })

    result_df = pd.DataFrame(results)
    st.success("✅ Preise erfolgreich gefunden!")

    st.dataframe(result_df)

    # === Download Button ===
    buffer = BytesIO()
    result_df.to_excel(buffer, index=False)
    st.download_button(
        label="📥 Ergebnis als Excel herunterladen",
        data=buffer,
        file_name=f"preisvergleich_{datetime.today().date()}.xlsx",
        mime="application/vnd.ms-excel"
    )

# === Footer ===
st.markdown("<div class='footer'>Powered by ezinụlọ 🌿</div>", unsafe_allow_html=True)
