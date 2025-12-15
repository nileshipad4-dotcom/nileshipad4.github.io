import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="NIFTY Option Chain", layout="wide")

EXPIRY = "16-Dec-2025"

@st.cache_data(ttl=30)
def fetch_nifty_option_chain(expiry):
    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain"
    })

    # Warm cookies
    session.get("https://www.nseindia.com", timeout=10)
    time.sleep(1)

    url = (
        "https://www.nseindia.com/api/option-chain-v3"
        f"?type=Indices&symbol=NIFTY&expiry={expiry}"
    )

    r = session.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()

    spot = data["records"]["underlyingValue"]
    records = data["records"]["data"]

    rows = []
    for item in records:
        ce = item.get("CE", {})
        pe = item.get("PE", {})

        rows.append({
            "Strike Price": item["strikePrice"],
            "Call Price": ce.get("lastPrice"),
            "Call OI": ce.get("openInterest"),
            "Put Price": pe.get("lastPrice"),
            "Put OI": pe.get("openInterest"),
            "Call Volume": ce.get("totalTradedVolume"),
            "Put Volume": pe.get("totalTradedVolume"),
        })

    df = pd.DataFrame(rows).sort_values("Strike Price")
    return spot, df


st.title("📊 NIFTY Option Chain – All Strikes")
st.caption("Source: NSE Website (run locally)")

try:
    spot, df = fetch_nifty_option_chain(EXPIRY)

    c1, c2 = st.columns(2)
    c1.metric("NIFTY Spot", spot)
    c2.metric("Expiry", EXPIRY)

    st.dataframe(df, use_container_width=True, height=600)

except Exception as e:
    st.error("NSE temporarily blocked this request.")
    st.warning("Run this app locally for reliable data.")

st.button("🔄 Refresh")
