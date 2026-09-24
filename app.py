import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configure mobile viewport and layout
st.set_page_config(
    page_title="NSE Stock Analyzer",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom mobile-friendly styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e1e24;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid #333;
    }
    .bullish { color: #00E676; font-weight: bold; }
    .bearish { color: #FF5252; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📱 NSE Intraday Screener")
st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

# Liquid NSE stocks trading around Rs 10 - Rs 60
SYMBOLS = [
    "YESBANK.NS",
    "IDEA.NS",
    "SUZLON.NS",
    "RPOWER.NS",
    "CENTRALBK.NS",
    "UCOBANK.NS",
    "IOB.NS",
    "SOUTHBANK.NS",
    "GMRINFRA.NS"
]

@st.cache_data(ttl=60)
def fetch_stock_data(tickers):
    data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d", interval="15m")
            if hist.empty or len(hist) < 2:
                continue

            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            pct_change = ((current_price - prev_close) / prev_close) * 100
            volume = hist['Volume'].iloc[-1]
            avg_volume = hist['Volume'].mean()

            # Technical logic: VWAP calculation
            hist['Typical_Price'] = (hist['High'] + hist['Low'] + hist['Close']) / 3
            vwap = (hist['Typical_Price'] * hist['Volume']).cumsum() / hist['Volume'].cumsum()
            current_vwap = vwap.iloc[-1]

            # Signal Generation
            bias = "Bullish (Above VWAP)" if current_price >= current_vwap else "Bearish (Below VWAP)"
            vol_surge = volume > (1.2 * avg_volume)

            data.append({
                "Symbol": ticker.replace(".NS", ""),
                "Price (₹)": round(current_price, 2),
                "Change (%)": round(pct_change, 2),
                "VWAP (₹)": round(current_vwap, 2),
                "Bias": bias,
                "Vol Spike": "🔥 Yes" if vol_surge else "Normal",
                "RawTicker": ticker
            })
        except Exception:
            continue
    return pd.DataFrame(data)

# Fetch and render data
with st.spinner("Analyzing market momentum..."):
    df = fetch_stock_data(SYMBOLS)

if df.empty:
    st.warning("No data retrieved. Market might be closed or API rate limited.")
else:
    # Filter by price range under Rs 50
    st.subheader("⚡ High Volume Stocks (₹0 - ₹50)")
    
    for _, row in df.iterrows():
        color_class = "bullish" if row["Change (%)"] >= 0 else "bearish"
        st.markdown(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0;">{row['Symbol']}</h3>
                <span class="{color_class}" style="font-size: 1.2rem;">₹{row['Price (₹)']} ({row['Change (%)']:+}%)</span>
            </div>
            <div style="margin-top: 8px; font-size: 0.9rem; color: #BBB;">
                VWAP: ₹{row['VWAP (₹)']} | Setup: <b>{row['Bias']}</b> | Volume: {row['Vol Spike']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Detailed Intraday Chart for selected stock
    st.markdown("---")
    st.subheader("🔍 Intraday Chart (15m)")
    selected = st.selectbox("Select stock to inspect:", df["Symbol"].tolist())
    
    if selected:
        selected_ticker = f"{selected}.NS"
        stock_detail = yf.Ticker(selected_ticker).history(period="1d", interval="5m")
        if not stock_detail.empty:
            fig = go.Figure(data=[go.Candlestick(
                x=stock_detail.index,
                open=stock_detail['Open'],
                high=stock_detail['High'],
                low=stock_detail['Low'],
                close=stock_detail['Close'],
                name="Price"
            )])
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=10, b=10),
                height=350,
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)
          
