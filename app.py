import io
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="NSE Live Watchlist",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS matching the broker watchlist interface
st.markdown(
    """
<style>
    .top-header {
        background-color: #4a154b;
        color: white;
        padding: 16px;
        border-radius: 14px 14px 0 0;
        margin-bottom: 0px;
    }
    .top-header h2 { color: white; margin: 0; font-size: 1.3rem; font-weight: 700; }
    .top-header p { color: #d1b3d1; margin: 2px 0 0 0; font-size: 0.85rem; }

    .index-container {
        display: flex;
        justify-content: space-between;
        background-color: #f7f7f9;
        color: #111;
        padding: 10px 14px;
        border-bottom: 1px solid #e2e2e8;
        font-size: 0.82rem;
    }
    .idx-box { width: 48%; }
    .idx-name { font-weight: bold; color: #444; }
    .idx-val-green { color: #00875A; font-weight: bold; }
    .idx-val-red { color: #DE350B; font-weight: bold; }

    .stock-row {
        background-color: #ffffff;
        padding: 12px 14px;
        border-bottom: 1px solid #eeeeee;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .stock-sym { font-size: 1.02rem; font-weight: 700; color: #111111; margin: 0; }
    .stock-exch { font-size: 0.75rem; font-weight: 500; color: #7a7a85; margin-top: 2px; }
    .stock-price { font-size: 1.02rem; font-weight: 700; text-align: right; margin: 0; }
    .price-green { color: #00875A; }
    .price-red { color: #DE350B; }
    .sub-change { font-size: 0.78rem; text-align: right; }
</style>
""",
    unsafe_allow_html=True,
)

# Official NSE Live Archives Index Endpoints
NSE_FEEDS = {
    "NIFTY 50 (50 Stocks)": (
        "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
    ),
    "NIFTY 100 (100 Stocks)": (
        "https://archives.nseindia.com/content/indices/ind_nifty100list.csv"
    ),
    "NIFTY 500 (500 Stocks)": (
        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    ),
    "Banking (Nifty Bank)": (
        "https://archives.nseindia.com/content/indices/ind_niftybanklist.csv"
    ),
    "PSU Banks": (
        "https://archives.nseindia.com/content/indices/ind_niftypsubanklist.csv"
    ),
    "Energy & Renewables": (
        "https://archives.nseindia.com/content/indices/ind_niftyenergylist.csv"
    ),
    "Infrastructure & Railways": (
        "https://archives.nseindia.com/content/indices/ind_niftyinfralist.csv"
    ),
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
}


# Cache NSE index constituents for 12 hours so it doesn't repeatedly download the large CSV
@st.cache_data(ttl=43200)
def fetch_symbols_from_nse(url):
  try:
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code == 200:
      df = pd.read_csv(io.StringIO(resp.text))
      # Standard NSE constituent CSV column is 'Symbol'
      col = [c for c in df.columns if "Symbol" in c or "SYMBOL" in c]
      if col:
        symbols = df[col[0]].dropna().unique().tolist()
        return [str(s).strip() for s in symbols if str(s).strip()]
  except Exception:
    pass
  return []


# --- HEADER SECTION ---
st.markdown(
    f"""
<div class="top-header">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2>NSE Live Screener ▾</h2>
        <span style="font-size:1.4rem;">≡ ⊕</span>
    </div>
    <p>Live Feed from NSE India • {datetime.now().strftime("%d %b %Y, %I:%M %p")}</p>
</div>
""",
    unsafe_allow_html=True,
)

# Watchlist category selector
selected_feed_name = st.selectbox(
    "Select Index:", list(NSE_FEEDS.keys()), label_visibility="collapsed"
)

# Dynamically fetch constituents for the selected feed
raw_symbols = fetch_symbols_from_nse(NSE_FEEDS[selected_feed_name])
if not raw_symbols:
  st.error("Connecting to NSE master database...")
  st.stop()

# Controls: Search, Price Filter, and Batch Display Size
col_search, col_price = st.columns([2, 1])
search_term = col_search.text_input(
    "🔍 Filter Symbol...", placeholder="e.g. YESBANK, RELIANCE"
)
max_price = col_price.slider(
    "Max Price (₹)", min_value=10, max_value=5000, value=50, step=10
)

# Filter symbol list before fetching prices to avoid rate limiting
active_symbols = [
    s for s in raw_symbols if not search_term or (search_term.upper() in s)
]
# For large indices (e.g. 500 stocks), display the top chunk per page
batch_limit = st.slider(
    "Display Count", min_value=20, max_value=min(150, len(active_symbols)), value=50
)
active_symbols = active_symbols[:batch_limit]


# Download live quotes in one single batch HTTP call
@st.cache_data(ttl=60)
def fetch_market_snapshot(symbol_list):
  yf_tickers = [f"{s}.NS" for s in symbol_list] + ["^NSEI", "^NSEBANK"]
  try:
    data = yf.download(
        yf_tickers, period="5d", interval="1d", group_by="ticker", progress=False
    )
  except Exception:
    return {}, []

  # Parse Indices
  indices = {}
  for idx_key, name in [("^NSEI", "NIFTY 50"), ("^NSEBANK", "NIFTY BANK")]:
    try:
      df_idx = data[idx_key].dropna()
      if len(df_idx) >= 2:
        c = df_idx["Close"].iloc[-1]
        p = df_idx["Close"].iloc[-2]
        d = c - p
        pct = (d / p) * 100
        indices[name] = {
            "val": f"{c:,.2f}",
            "diff": f"{d:+,.2f}",
            "pct": f"({pct:+.2f}%)",
            "up": d >= 0,
        }
    except Exception:
      indices[name] = {
          "val": "--",
          "diff": "0.00",
          "pct": "(0.00%)",
          "up": True,
      }

  # Parse Equities
  stocks = []
  for sym in symbol_list:
    try:
      df_s = data[f"{sym}.NS"].dropna()
      if len(df_s) >= 2:
        c = df_s["Close"].iloc[-1]
        p = df_s["Close"].iloc[-2]
        d = c - p
        pct = (d / p) * 100
        stocks.append({
            "symbol": sym,
            "exch": "NSE EQ",
            "price": c,
            "diff": d,
            "pct": pct,
        })
    except Exception:
      continue

  return indices, stocks


with st.spinner(f"Loading {len(active_symbols)} scrips from NSE..."):
  indices, stocks = fetch_market_snapshot(active_symbols)

# --- DUAL INDEX STRIP ---
n50 = indices.get(
    "NIFTY 50", {"val": "--", "diff": "0.00", "pct": "(0.00%)", "up": True}
)
nbank = indices.get(
    "NIFTY BANK", {"val": "--", "diff": "0.00", "pct": "(0.00%)", "up": True}
)

st.markdown(
    f"""
<div class="index-container">
    <div class="idx-box">
        <span class="idx-name">NIFTY 50</span>
        <span class="{'idx-val-green' if n50['up'] else 'idx-val-red'}">
            {'▲' if n50['up'] else '▼'} {n50['val']}
        </span>
        <div style="font-size:0.75rem;" class="{'idx-val-green' if n50['up'] else 'idx-val-red'}">
            {n50['diff']} {n50['pct']}
        </div>
    </div>
    <div style="border-left: 1px solid #ccc; height: 35px; margin: 0 8px;"></div>
    <div class="idx-box">
        <span class="idx-name">NIFTY BANK</span>
        <span class="{'idx-val-green' if nbank['up'] else 'idx-val-red'}">
            {'▲' if nbank['up'] else '▼'} {nbank['val']}
        </span>
        <div style="font-size:0.75rem;" class="{'idx-val-green' if nbank['up'] else 'idx-val-red'}">
            {nbank['diff']} {nbank['pct']}
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# Filter by selected price cap
filtered_stocks = [s for s in stocks if s["price"] <= max_price]

# --- RENDER STOCK ROWS ---
if not filtered_stocks:
  st.warning(f"No stocks found below ₹{max_price} in {selected_feed_name}.")
else:
  for s in filtered_stocks:
    is_up = s["diff"] >= 0
    color_cls = "price-green" if is_up else "price-red"
    sign = "+" if is_up else ""

    st.markdown(
        f"""
        <div class="stock-row">
            <div>
                <p class="stock-sym">{s['symbol']}</p>
                <p class="stock-exch">{s['exch']}</p>
            </div>
            <div>
                <p class="stock-price">₹{s['price']:,.2f}</p>
                <p class="sub-change {color_cls}">{sign}{s['diff']:,.2f} ({sign}{s['pct']:.2f}%)</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- EXPANDABLE INTRADAY CHART ---
st.markdown("---")
with st.expander("📊 Intraday Candlestick Chart (5-Minute)"):
  sel_sym = st.selectbox(
      "Choose stock to chart:", [s["symbol"] for s in filtered_stocks]
  )
  if sel_sym:
    t = yf.Ticker(f"{sel_sym}.NS")
    c_df = t.history(period="1d", interval="5m")
    if not c_df.empty:
      fig = go.Figure(
          data=[
              go.Candlestick(
                  x=c_df.index,
                  open=c_df["Open"],
                  high=c_df["High"],
                  low=c_df["Low"],
                  close=c_df["Close"],
                  name="5m Price",
              )
          ]
      )
      fig.update_layout(
          title=f"{sel_sym} Intraday",
          xaxis_rangeslider_visible=False,
          margin=dict(l=10, r=10, t=30, b=10),
          height=340,
          template="plotly_white",
      )
      st.plotly_chart(fig, use_container_width=True)
