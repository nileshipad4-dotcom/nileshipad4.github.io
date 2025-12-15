import tls_client
import pandas as pd
import time
import streamlit as st

# =============================
# CONFIG
# =============================
EXPIRIES = ["16-Dec-2025", "30-Dec-2025"]
REFRESH_SECONDS = 300


# =============================
# Streamlit Page Config
# =============================
st.set_page_config(
    page_title="NIFTY Option Chain",
    layout="wide"
)


# =============================
# Create ONE TLS Session
# =============================
@st.cache_resource
def create_session():
    session = tls_client.Session(
        client_identifier="chrome_120",
        random_tls_extension_order=True
    )

    session.headers.update({
        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain"
    })

    # Warm cookies once
    session.get("https://www.nseindia.com")
    time.sleep(1)

    return session


# =============================
# Fetch NIFTY Option Chain (V3)
# =============================
@st.cache_data(ttl=REFRESH_SECONDS)
def fetch_nifty_option_chain(expiry):

    session = create_session()

    url = (
        "https://www.nseindia.com/api/option-chain-v3"
        f"?type=Indices&symbol=NIFTY&expiry={expiry}"
    )

    try:
        r = session.get(url)

        if "application/json" not in r.headers.get("Content-Type", ""):
            raise Exception("Blocked")

        data = r.json()

    except Exception:
        # Refresh cookies once
        session.get("https://www.nseindia.com")
        time.sleep(1)

        r = session.get(url)
        if "application/json" not in r.headers.get("Content-Type", ""):
            return pd.DataFrame()

        data = r.json()

    rows = []

    records = data.get("records", {}).get("data", [])

    for item in records:
        ce = item.get("CE") or {}
        pe = item.get("PE") or {}

        rows.append({
            "Strike": item.get("strikePrice"),
            "CE_OI": ce.get("openInterest"),
            "CE_Volume": ce.get("totalTradedVolume"),
            "CE_LTP": ce.get("lastPrice"),
            "PE_OI": pe.get("openInterest"),
            "PE_Volume": pe.get("totalTradedVolume"),
            "PE_LTP": pe.get("lastPrice"),
        })

    df = pd.DataFrame(rows)

    if df.empty or "Strike" not in df.columns:
        return pd.DataFrame()

    return df.sort_values("Strike")


# =============================
# UI
# =============================
st.title("📊 NIFTY Option Chain (NSE v3)")

st.caption("Data source: NSE | Auto-refresh enabled")

for expiry in EXPIRIES:
    st.subheader(f"Expiry: {expiry}")

    df = fetch_nifty_option_chain(expiry)

    if df.empty:
        st.warning("No data available (NSE may be blocking temporarily).")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            height=600
        )

    st.divider()


# =============================
# Auto Refresh
# =============================
st.caption(f"Auto refresh every {REFRESH_SECONDS} seconds")

time.sleep(REFRESH_SECONDS)
st.rerun()
