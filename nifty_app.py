import time
import requests
import pandas as pd
import streamlit as st

EXPIRY = "16-Dec-2025"
REFRESH_SECONDS = 30

st.set_page_config(page_title="NIFTY Option Chain", layout="wide")


# --------------------------------
# Create session + cookies
# --------------------------------
@st.cache_resource
def get_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
        "Connection": "keep-alive",
        "Host": "www.nseindia.com"
    })

    # 🔑 Warm up cookies (CRITICAL)
    session.get("https://www.nseindia.com", timeout=10)

    return session


# --------------------------------
# Fetch NIFTY option chain
# --------------------------------
@st.cache_data(ttl=REFRESH_SECONDS)
def fetch_nifty_data():
    session = get_session()

    url = (
        "https://www.nseindia.com/api/option-chain-v3"
        "?type=Indices&symbol=NIFTY&expiry=16-Dec-2025"
    )

    def _fetch():
        r = session.get(url, timeout=10)
        if "application/json" not in r.headers.get("Content-Type", ""):
            raise ValueError("Invalid response (not JSON)")
        return r.json()

    try:
        data = _fetch()
    except Exception:
        # 🔁 Force cookie refresh once
        session.get("https://www.nseindia.com", timeout=10)
        data = _fetch()

    spot = data["records"]["underlyingValue"]

    rows = []
    ce_oi = pe_oi = 0
    ce_vol = pe_vol = 0

    for item in data["records"]["data"]:
        if item.get("expiryDate") != EXPIRY:
            continue

        ce = item.get("CE", {})
        pe = item.get("PE", {})

        ce_oi += ce.get("openInterest", 0)
        pe_oi += pe.get("openInterest", 0)
        ce_vol += ce.get("totalTradedVolume", 0)
        pe_vol += pe.get("totalTradedVolume", 0)

        rows.append({
            "Strike": item["strikePrice"],
            "CE LTP": ce.get("lastPrice"),
            "CE OI": ce.get("openInterest"),
            "CE Volume": ce.get("totalTradedVolume"),
            "PE LTP": pe.get("lastPrice"),
            "PE OI": pe.get("openInterest"),
            "PE Volume": pe.get("totalTradedVolume"),
        })

    df = pd.DataFrame(rows).sort_values("Strike")

    pcr_oi = round(pe_oi / ce_oi, 2) if ce_oi else 0
    pcr_vol = round(pe_vol / ce_vol, 2) if ce_vol else 0

    return spot, pcr_oi, pcr_vol, df


# --------------------------------
# UI
# --------------------------------
st.title("📊 NIFTY Option Chain")
st.write(f"**Expiry:** {EXPIRY}")

try:
    spot, pcr_oi, pcr_vol, df = fetch_nifty_data()

    c1, c2, c3 = st.columns(3)
    c1.metric("NIFTY Spot", spot)
    c2.metric("Put / Call OI", pcr_oi)
    c3.metric("Put / Call Volume", pcr_vol)

    st.divider()
    st.dataframe(df, use_container_width=True, height=600)

except Exception as e:
    st.warning(
        "NSE temporarily blocked this request.\n\n"
        "• This is common with NSE\n"
        "• Please wait 1–2 minutes and refresh\n"
        "• Works best when run locally"
    )
    st.stop()

st.caption(f"Auto refresh every {REFRESH_SECONDS} seconds")

time.sleep(REFRESH_SECONDS)
st.rerun()
