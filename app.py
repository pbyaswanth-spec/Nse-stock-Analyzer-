import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Page configuration for mobile
st.set_page_config(
    page_title="NSE Stock Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for compact square tiles and mobile responsiveness
st.markdown("""
<style>
    /* Compact, square-like metric cards */
    .stButton > button {
        width: 100%;
        min-height: 95px;
        border-radius: 12px;
        background-color: #1e1e24;
        border: 1px solid #33333e;
        color: #ffffff;
        text-align: center;
        padding: 8px 4px;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover, .stButton > button:focus {
        border-color: #00E676;
        background-color: #26262e;
        color: #ffffff;
    }
    .badge-bullish { color: #00E676; font-weight: bold; }
    .badge-bearish { color: #FF5252; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Curated high-liquidity universe grouped by sector
SECTOR_UNIVERSE = {
    "Banking": [
        {"symbol": "YESBANK.NS", "name": "Yes Bank"},
        {"symbol": "CENTRALBK.NS", "name": "Central Bank"},
        {"symbol": "UCOBANK.NS", "name": "UCO Bank"},
        {"symbol": "IOB.NS", "name": "Indian Overseas Bank"},
        {"symbol": "SOUTHBANK.NS", "name": "South Ind Bank"},
        {"symbol": "IDFCFIRSTB.NS", "name": "IDFC First"},
        {"symbol": "PNB.NS", "name": "PNB"},
        {"symbol": "BANKBARODA.NS", "name": "Bank of Baroda"}
    ],
    "Railways": [
        {"symbol": "IRFC.NS", "name": "IRFC"},
        {"symbol": "RVNL.NS", "name": "Rail Vikas Nigam"},
        {"symbol": "IRCON.NS", "name": "IRCON Intl"},
        {"symbol": "RAILTEL.NS", "name": "RailTel"},
        {"symbol": "RITES.NS", "name": "RITES"},
        {"symbol": "TEXRAIL.NS", "name": "Texmaco Rail"},
        {"symbol": "JWL.NS", "name": "Jupiter Wagons"},
        {"symbol": "TITAGARH.NS", "name": "Titagarh Rail"}
    ],
    "Renewable Energy": [
        {"symbol": "SUZLON.NS", "name": "Suzlon Energy"},
        {"symbol": "RPOWER.NS", "name": "Reliance Power"},
        {"symbol": "JPPOWER.NS", "name": "Jaiprakash Power"},
        {"symbol": "GREENPOWER.NS", "name": "Orient Green"},
        {"symbol": "NHPC.NS", "name": "NHPC"},
        {"symbol": "SJVN.NS", "name": "SJVN Ltd"},
        {"symbol": "TATAPOWER.NS", "name": "Tata Power"},
        {"symbol": "ADANIGREEN.NS", "name": "Adani Green"}
    ]
}

# Session state to track clicked stock
if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = "YESBANK.NS"

st.title("⚡ NSE Sector Analyzer")
st.caption(f"Intraday Screener • {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

# Sector filter tabs
selected_sector = st.radio(
    "Choose Sector:",
    ["All"] + list(SECTOR_UNIVERSE.keys()),
    horizontal=True
)

# Collect symbols to fetch
if selected_sector == "All":
    stocks_to_show = [item for sublist in SECTOR_UNIVERSE.values() for item in sublist]
else:
    stocks_to_show = SECTOR_UNIVERSE[selected_sector]

@st.cache_data(ttl=60)
def fetch_quotes(stock_list):
    results = {}
    for s in stock_list:
        ticker_str = s["symbol"]
        try:
            t = yf.Ticker(ticker_str)
            hist = t.history(period="3d", interval="15m")
            if hist.empty or len(hist) < 2:
                continue

            last_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            chg = ((last_price - prev_price) / prev_price) * 100

            # Calculate VWAP
            typical = (hist['High'] + hist['Low'] + hist['Close']) / 3
            vwap = (typical * hist['Volume']).cumsum() / hist['Volume'].cumsum()
            cur_vwap = vwap.iloc[-1]

            results[ticker_str] = {
                "name": s["name"],
                "clean_symbol": ticker_str.replace(".NS", ""),
                "price": round(last_price, 2),
                "change": round(chg, 2),
                "vwap": round(cur_vwap, 2),
                "bias": "BULLISH" if last_price >= cur_vwap else "BEARISH",
                "vol_spike": hist['Volume'].iloc[-1] > (1.2 * hist['Volume'].mean())
            }
        except Exception:
            continue
    return results

with st.spinner("Screening market depth..."):
    market_data = fetch_quotes(stocks_to_show)

# Display square tiles in a 2-column or 3-column responsive grid
st.subheader("📊 Stocks Matrix (Tap a box to inspect)")

# Render grid in rows of 2 for mobile fit
cols_per_row = 2
stock_keys = list(market_data.keys())

for i in range(0, len(stock_keys), cols_per_row):
    cols = st.columns(cols_per_row)
    for j in range(cols_per_row):
        idx = i + j
        if idx < len(stock_keys):
            ticker_key = stock_keys[idx]
            info = market_data[ticker_key]
            symbol_label = info['clean_symbol']
            price_text = f"₹{info['price']}"
            chg_sign = "+" if info['change'] >= 0 else ""
            chg_text = f"{chg_sign}{info['change']}%"
            
            # Button label acts as the square tile
            label = f"{symbol_label}\n{price_text} ({chg_text})\n{'🟢 Above VWAP' if info['bias']=='BULLISH' else '🔴 Below VWAP'}"
            if cols[j].button(label, key=f"btn_{ticker_key}"):
                st.session_state.selected_stock = ticker_key

# --- SELECTED STOCK DETAILS PANEL ---
st.markdown("---")
sel_ticker = st.session_state.selected_stock
if sel_ticker in market_data:
    detail = market_data[sel_ticker]
    st.subheader(f"🎯 Analysis: {detail['clean_symbol']} ({detail['name']})")
    
    # Intraday Stats Header
    stat1, stat2, stat3 = st.columns(3)
    stat1.metric("LTP", f"₹{detail['price']}", f"{detail['change']}%")
    stat2.metric("Intraday VWAP", f"₹{detail['vwap']}")
    stat3.metric("Volume Spike", "🔥 Yes" if detail['vol_spike'] else "Normal")

    # Intraday Trade Plan Formulation
    entry_level = round(detail['price'] * 1.002, 2)
    sl_level = round(detail['vwap'] if detail['price'] >= detail['vwap'] else detail['price'] * 0.99, 2)
    target1 = round(detail['price'] + abs(detail['price'] - sl_level) * 1.5, 2)
    target2 = round(detail['price'] + abs(detail['price'] - sl_level) * 2.0, 2)

    st.markdown(f"""
    **Intraday Technical Bias:** <span class="{'badge-bullish' if detail['bias']=='BULLISH' else 'badge-bearish'}">{detail['bias']}</span>
    * **Trigger Entry:** Watch for sustained close above `₹{entry_level}`
    * **Stop-Loss (SL):** `₹{sl_level}`
    * **Target 1 (1:1.5):** `₹{target1}` | **Target 2 (1:2):** `₹{target2}`
    """, unsafe_allow_html=True)

    # 5-minute Intraday Candlestick Chart
    hist_chart = yf.Ticker(sel_ticker).history(period="1d", interval="5m")
    if not hist_chart.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=hist_chart.index,
            open=hist_chart['Open'],
            high=hist_chart['High'],
            low=hist_chart['Low'],
            close=hist_chart['Close'],
            name="Candlestick"
        )])
        fig.update_layout(
            title=f"{detail['clean_symbol']} (5m Intraday)",
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=30, b=10),
            height=320,
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
