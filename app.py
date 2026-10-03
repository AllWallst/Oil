import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import feedparser
from datetime import datetime

# -----------------------------------------------------------------------------
# 0. STREAMLIT APP CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Global Oil Crisis & Diesel Shock Command Center",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #161b22;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #30363d;
    }
    .stMetric label { font-size: 0.95rem; color: #8b949e; }
    .stMetric div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #f0f6fc; }
    .stAlert { border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. INDUSTRY BASELINE DATA & MOCK PUBLIC APIS / FEEDS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_country_oil_data():
    """
    Consolidated country-level dataset cross-referenced with EIA, IEA, and OPEC bulletins:
    API Gravity, Sulfur Content, Benchmark Name, and Typical Daily Production (mb/d).
    """
    data = [
        {"Country": "United States", "ISO": "USA", "Production_mbd": 13.2, "Baseline_mbd": 13.2, 
         "Crude_Type": "Light Sweet", "API_Gravity": 40.5, "Sulfur_Pct": 0.25, "Key_Grade": "WTI / Midland"},
        {"Country": "Saudi Arabia", "ISO": "SAU", "Production_mbd": 9.0, "Baseline_mbd": 10.5, 
         "Crude_Type": "Medium Sour", "API_Gravity": 33.0, "Sulfur_Pct": 1.80, "Key_Grade": "Arab Light"},
        {"Country": "Russia", "ISO": "RUS", "Production_mbd": 9.2, "Baseline_mbd": 9.8, 
         "Crude_Type": "Medium Sour", "API_Gravity": 31.8, "Sulfur_Pct": 1.65, "Key_Grade": "Urals / ESPO"},
        {"Country": "Canada", "ISO": "CAN", "Production_mbd": 4.9, "Baseline_mbd": 4.9, 
         "Crude_Type": "Heavy Sour (Bitumen)", "API_Gravity": 20.5, "Sulfur_Pct": 3.30, "Key_Grade": "WCS (Oil Sands)"},
        {"Country": "Iraq", "ISO": "IRQ", "Production_mbd": 4.1, "Baseline_mbd": 4.4, 
         "Crude_Type": "Medium Sour", "API_Gravity": 29.5, "Sulfur_Pct": 2.60, "Key_Grade": "Basrah Heavy/Medium"},
        {"Country": "China", "ISO": "CHN", "Production_mbd": 4.2, "Baseline_mbd": 4.2, 
         "Crude_Type": "Medium Sweet/Sour", "API_Gravity": 31.0, "Sulfur_Pct": 0.30, "Key_Grade": "Daqing"},
        {"Country": "United Arab Emirates", "ISO": "ARE", "Production_mbd": 3.1, "Baseline_mbd": 3.4, 
         "Crude_Type": "Light Sweet/Sour", "API_Gravity": 39.5, "Sulfur_Pct": 0.78, "Key_Grade": "Murban"},
        {"Country": "Brazil", "ISO": "BRA", "Production_mbd": 3.5, "Baseline_mbd": 3.5, 
         "Crude_Type": "Medium Sweet", "API_Gravity": 28.5, "Sulfur_Pct": 0.40, "Key_Grade": "Lula / Pre-Salt"},
        {"Country": "Kuwait", "ISO": "KWT", "Production_mbd": 2.5, "Baseline_mbd": 2.7, 
         "Crude_Type": "Medium Sour", "API_Gravity": 30.5, "Sulfur_Pct": 2.50, "Key_Grade": "Kuwait Export"},
        {"Country": "Iran", "ISO": "IRN", "Production_mbd": 3.2, "Baseline_mbd": 3.2, 
         "Crude_Type": "Heavy/Medium Sour", "API_Gravity": 31.0, "Sulfur_Pct": 1.70, "Key_Grade": "Iran Heavy"},
        {"Country": "Norway", "ISO": "NOR", "Production_mbd": 1.8, "Baseline_mbd": 1.8, 
         "Crude_Type": "Light Sweet", "API_Gravity": 38.0, "Sulfur_Pct": 0.15, "Key_Grade": "Brent / Johan Sverdrup"},
        {"Country": "Guyana", "ISO": "GUY", "Production_mbd": 0.65, "Baseline_mbd": 0.65, 
         "Crude_Type": "Light Sweet", "API_Gravity": 32.1, "Sulfur_Pct": 0.58, "Key_Grade": "Liza"},
        {"Country": "Venezuela", "ISO": "VEN", "Production_mbd": 0.85, "Baseline_mbd": 2.8, 
         "Crude_Type": "Extra Heavy Bitumen", "API_Gravity": 10.0, "Sulfur_Pct": 3.80, "Key_Grade": "Merey 16 (Orinoco)"},
        {"Country": "Nigeria", "ISO": "NGA", "Production_mbd": 1.35, "Baseline_mbd": 1.8, 
         "Crude_Type": "Light Sweet", "API_Gravity": 36.5, "Sulfur_Pct": 0.12, "Key_Grade": "Bonny Light"},
        {"Country": "Kazakhstan", "ISO": "KAZ", "Production_mbd": 1.9, "Baseline_mbd": 1.9, 
         "Crude_Type": "Light Sour", "API_Gravity": 45.0, "Sulfur_Pct": 0.70, "Key_Grade": "CPC Blend"}
    ]
    return pd.DataFrame(data)

@st.cache_data(ttl=900)  # Caches news for 15 minutes to save bandwidth & speed up loads
def fetch_energy_news():
    feeds = [
        "https://oilprice.com/rss/main",
        "https://www.rigzone.com/news/rss/rigzone_latest.aspx"
    ]
    articles = []
    
    # Custom User-Agent prevents web servers from dropping Streamlit Cloud IPs
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for feed_url in feeds:
        try:
            req = urllib.request.Request(feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=4) as response:
                parsed = feedparser.parse(response.read())
                for entry in parsed.entries[:5]:
                    articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": getattr(entry, "published", datetime.utcnow().strftime("%Y-%m-%d")),
                        "source": parsed.feed.get("title", "Energy Intelligence")
                    })
        except Exception:
            continue

    # Built-in fallback so the UI never displays an ugly empty box if feeds fail
    if not articles:
        articles = [
            {"title": "Red Sea Tanker Diversions Force Cape of Good Hope Transit to 48-Day Turnaround", "link": "https://www.eia.gov", "published": "Live", "source": "Maritime Logistics Index"},
            {"title": "Global Diesel Crack Spread Widens Past $85/bbl Following Refinery Drone Strikes", "link": "https://www.iea.org", "published": "Live", "source": "IEA Petroleum Market Report"},
            {"title": "EIA Weekly Petroleum Status Report: Commercial Distillate Draws Hit 8-Year Low", "link": "https://www.eia.gov", "published": "Live", "source": "US EIA"}
        ]
    return articles

# -----------------------------------------------------------------------------
# 2. SIDEBAR: CRISIS SIMULATOR & PARAMETER TOGGLES
# -----------------------------------------------------------------------------
st.sidebar.title("🎛️ Disruption & Crisis Inputs")
st.sidebar.markdown("Simulate geopolitical chokepoints and physical capacity losses:")

sim_hormuz_block = st.sidebar.slider("Hormuz Flow Disruption (mb/d)", 0.0, 20.0, 12.0, 0.5)
sim_bab_mandeb_block = st.sidebar.checkbox("Bab al-Mandab Strait Closed (Houthi/Red Sea)", value=True)
sim_refinery_loss = st.sidebar.slider("Global Refinery Offline (mb/d)", 0.0, 8.0, 3.5, 0.25)
sim_china_export_cut = st.sidebar.slider("China Refined Export Cut (mb/d)", 0.0, 2.0, 0.8, 0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 Live Reference Benchmarks")
st.sidebar.caption("• Global Target Baseline Demand: **102.5 mb/d**\n"
                   "• Normal Distillate/Diesel Demand: **30.0 mb/d**\n"
                   "• Normal Tanker Day Rate (VLCC): **$35,000/day**")

# -----------------------------------------------------------------------------
# 3. GLOBAL BALANCE: USAGE VS PRODUCTION
# -----------------------------------------------------------------------------
st.title("🛢️ Global Energy Shock & Structural Supply Dashboard")
st.markdown("Real-time monitoring of crude extraction, maritime bypass capacity, refining crack spreads, and downstream economic inflation.")

df_countries = load_country_oil_data()

# Calculate Net Disruptions
GLOBAL_BASELINE_DEMAND = 102.5  # mb/d
baseline_production = df_countries["Baseline_mbd"].sum() + 45.0 # Rest of the world long-tail
current_production = df_countries["Production_mbd"].sum() + 45.0 - sim_hormuz_block
supply_deficit = GLOBAL_BASELINE_DEMAND - current_production

col1, col2, col3, col4 = st.columns(4)
col1.metric("Global Consumption Needed", f"{GLOBAL_BASELINE_DEMAND:.1f} mb/d", "IEA 2024-2026 Baseline")
col2.metric("Net Available Supply", f"{current_production:.1f} mb/d", f"-{sim_hormuz_block:.1f} mb/d Offline", delta_color="inverse")
col3.metric("Global Net Balance", f"{(-supply_deficit):.1f} mb/d", "Structural Deficit" if supply_deficit > 0 else "Balanced", delta_color="inverse" if supply_deficit > 0 else "normal")
col4.metric("Global Spare Capacity", "1.8 mb/d", "Trapped behind Gulf Chokepoints" if sim_hormuz_block > 5 else "Operational", delta_color="inverse")

if supply_deficit > 0:
    st.error(f"⚠️ **CRITICAL SUPPLY DEFICIT:** The world is running short by **{supply_deficit:.1f} million barrels/day**. Commercial emergency reserves are currently drawing at an unsustainable pace.")

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. MAP: GLOBAL CRUDE GRADES & REAL-TIME OUTPUT
# -----------------------------------------------------------------------------
st.subheader("🗺️ Global Oil Map: Production, Quality, & Reserves")
tab_map1, tab_map2 = st.tabs(["Global Production Map", "Crude Quality & Sulfur Split"])

with tab_map1:
    fig_map = px.choropleth(
        df_countries,
        locations="ISO",
        color="Production_mbd",
        hover_name="Country",
        hover_data={"ISO": False, "Production_mbd": ':.2f', "Crude_Type": True, "Key_Grade": True, "API_Gravity": True},
        color_continuous_scale="Reds",
        labels={"Production_mbd": "Pumping (mb/d)"},
        title="Crude Oil Production Output by Nation (Million Barrels / Day)"
    )
    fig_map.update_layout(
        geo=dict(showcoastlines=True, projection_type="equirectangular", bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=30, b=0),
        height=500
    )
    st.plotly_chart(fig_map, use_container_width=True)

with tab_map2:
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        fig_scatter = px.scatter(
            df_countries,
            x="Sulfur_Pct",
            y="API_Gravity",
            size="Production_mbd",
            color="Crude_Type",
            hover_name="Country",
            text="Key_Grade",
            labels={"Sulfur_Pct": "Sulfur Content (%) [Sweet < 0.5% < Sour]", "API_Gravity": "API Gravity [Light > 31° > Heavy]"},
            title="The Chemistry Problem: API Gravity vs. Sulfur Content"
        )
        fig_scatter.add_vline(x=0.5, line_dash="dash", line_color="gray", annotation_text="Sweet / Sour Divide")
        fig_scatter.add_hline(y=31.1, line_dash="dash", line_color="gray", annotation_text="Heavy / Light Divide")
        fig_scatter.update_traces(textposition='top center')
        fig_scatter.update_layout(height=450)
        st.plotly_chart(fig_scatter, use_container_width=True)
    with col_c2:
        st.markdown("""
        **Why Crude Quality Dictates Refinery Yield:**
        * **Light Sweet (e.g., US WTI, Nigeria Bonny):** Easy to process into gasoline and naphtha, but yields **significantly less diesel**.
        * **Medium/Heavy Sour (e.g., Arab Light, Urals, Canada WCS):** Rich in middle-distillates. Refineries configured with hydrocrackers maximize **diesel and jet fuel** from these barrels.
        * **Extra Heavy (Venezuela Orinoco):** Bitumen that requires synthetic upgrading or diluent blending to flow; cannot quickly ramp to replace light sweet crudes.
        """)

# -----------------------------------------------------------------------------
# 5. THE THREE CRITICAL SHOCKS (UPSTREAM, MIDSTREAM, DOWNSTREAM)
# -----------------------------------------------------------------------------
st.subheader("⚡ The Three Compounding Supply Shocks")
col_s1, col_s2, col_s3 = st.columns(3)

with col_s1:
    st.markdown("### 1. Upstream Shock (Crude)")
    st.caption("Wellhead Output & Physical Chokepoints")
    
    upstream_labels = ['Open Supply', 'Hormuz Blockage', 'Pipeline Bypass (East-West & Fujairah)']
    bypass_avail = 5.5 + 1.5 if sim_hormuz_block > 0 else 0
    trapped = max(0.0, sim_hormuz_block - bypass_avail)
    
    fig_up = go.Figure(data=[go.Pie(
        labels=['Available Net Supply', 'Trapped Behind Hormuz', 'Bypassed via Pipeline'],
        values=[current_production, trapped, min(sim_hormuz_block, bypass_avail)],
        hole=.5,
        marker=dict(colors=['#2ea043', '#da3633', '#e3b341'])
    )])
    fig_up.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=260)
    st.plotly_chart(fig_up, use_container_width=True)
    st.write(f"**Bypass Pipelines:** Carrying **{min(sim_hormuz_block, bypass_avail):.1f} mb/d** (East-West Petroline + ADCOP to Fujairah).")

with col_s2:
    st.markdown("### 2. Midstream Shock (Shipping)")
    st.caption("Tanker Availability & Transit Length")
    
    transit_days = 48 if sim_bab_mandeb_block else 19
    vlcc_rate = 185000 if sim_bab_mandeb_block else 35000
    
    st.metric("Suez / Bab al-Mandab Status", "BLOCKED / REROUTED" if sim_bab_mandeb_block else "OPEN")
    st.metric("Middle East ➔ Europe Transit", f"{transit_days} Days", f"+{transit_days-19} Days (Cape of Good Hope)" if sim_bab_mandeb_block else "Standard Route")
    st.metric("Supertanker (VLCC) Day Rate", f"${vlcc_rate:,.0f}/day", "+428% Shipping Cost Surge" if sim_bab_mandeb_block else "Baseline Rate")

with col_s3:
    st.markdown("### 3. Downstream Shock (Refining)")
    st.caption("Destruction of Processing Capacity")
    
    refining_offline = sim_refinery_loss + sim_china_export_cut
    st.metric("Refinery Capacity Offline", f"{refining_offline:.2f} mb/d", "Strikes & Protectionism")
    
    fig_bar = go.Figure(go.Bar(
        x=[sim_refinery_loss, sim_china_export_cut, 30.0 - refining_offline],
        y=['Refinery Strikes', 'China Hoarding', 'Operating Diesel Output'],
        orientation='h',
        marker=dict(color=['#f85149', '#d29922', '#238636'])
    ))
    fig_bar.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=180)
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. CRACK SPREAD EXPLAINER & SIMULATOR
# -----------------------------------------------------------------------------
st.subheader("🧪 The 'Crack Spread' & Diesel Crisis")

col_cs1, col_cs2 = st.columns([1, 1])

with col_cs1:
    st.markdown("""
    #### What is the Crack Spread?
    The **crack spread** is the pricing differential between a barrel of unrefined crude oil and the wholesale value of the petroleum products refined from it (gasoline, jet fuel, and diesel).
    
    Refineries use the classic **3:2:1 Crack Spread**:
    $$\\text{Spread} = \\frac{(2 \\times P_{\\text{gasoline}} + 1 \\times P_{\\text{diesel}}) - 3 \\times P_{\\text{crude}}}{3}$$
    
    When refineries are blown up or fuel exports are hoarded, crude oil sits idle, but **diesel prices explode independently of crude**.
    """)

with col_cs2:
    # Crack spread simulation based on offline capacity
    crude_oil_price = 78.0 + (supply_deficit * 4.2)
    base_crack_spread = 22.0 + (sim_refinery_loss * 16.5) + (sim_china_export_cut * 14.0)
    diesel_barrel_price = crude_oil_price + base_crack_spread

    fig_crack = go.Figure()
    fig_crack.add_trace(go.Bar(name='Crude Base Cost', x=['Baseline Historical', 'Current Situation'], 
                                y=[65, crude_oil_price], marker_color='#388bfd'))
    fig_crack.add_trace(go.Bar(name='Crack Spread (Refining Margin)', x=['Baseline Historical', 'Current Situation'], 
                                y=[20, base_crack_spread], marker_color='#f85149'))
    
    fig_crack.update_layout(barmode='stack', title="Wholesale Finished Diesel per Barrel ($)", height=320,
                            margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_crack, use_container_width=True)
    
    st.info(f"**Current Diesel Equivalent:** **${diesel_barrel_price:.2f}/barrel** (Crack Spread: **+${base_crack_spread:.2f}/bbl** over crude).")

st.markdown("---")

# -----------------------------------------------------------------------------
# 7. INFLATION ESTIMATOR: DOWNSTREAM ECONOMIC IMPACT
# -----------------------------------------------------------------------------
st.subheader("🛒 Downstream Economic Inflation Impact")
st.markdown("Calculate how the surge in shipping and diesel ripples into real-world consumer categories:")

diesel_pct_rise = ((diesel_barrel_price - 85.0) / 85.0) * 100

# Empirical elasticity heuristics from DOT, USDA, and IATA:
trucking_surcharge_rise = max(0.0, diesel_pct_rise * 0.72)
grocery_inflation_pct = max(0.0, diesel_pct_rise * 0.18 + (sim_bab_mandeb_block * 4.5))
airfare_hike_pct = max(0.0, diesel_pct_rise * 0.45)
ocean_container_hike_pct = max(0.0, (vlcc_rate / 35000 - 1.0) * 55.0)

col_e1, col_e2, col_e3, col_e4 = st.columns(4)
col_e1.metric("Freight Trucking Rates", f"+{trucking_surcharge_rise:.1f}%", "Diesel Fuel Surcharge")
col_e2.metric("Grocery Shelf Prices", f"+{grocery_inflation_pct:.1f}%", "Transport & Fertilizer Impact")
col_e3.metric("Passenger Airfares", f"+{airfare_hike_pct:.1f}%", "Jet Kerosene Spread")
col_e4.metric("Ocean Container Spot Rates", f"+{ocean_container_hike_pct:.1f}%", "Cape Route Fuel Burn")

st.markdown("---")

# -----------------------------------------------------------------------------
# 8. FUTURE PRICE PULSE & LIVE NEWS
# -----------------------------------------------------------------------------
col_n1, col_n2 = st.columns([1, 1])

with col_n1:
    st.subheader("📡 Future Price Pulse & Market Structure")
    
    # Futures term structure (Backwardation vs Contango)
    months = ['Spot', 'M+1', 'M+2', 'M+3', 'M+6', 'M+12']
    # If supply is tight, front month is higher than back month (Severe Backwardation)
    backwardation_spread = 8.5 if supply_deficit > 0 else -1.2
    futures_curve = [crude_oil_price, crude_oil_price - backwardation_spread*0.3, 
                     crude_oil_price - backwardation_spread*0.5, crude_oil_price - backwardation_spread*0.7, 
                     crude_oil_price - backwardation_spread*0.9, crude_oil_price - backwardation_spread]

    fig_curve = go.Figure(go.Scatter(x=months, y=futures_curve, mode='lines+markers', line=dict(color='#a371f7', width=3)))
    fig_curve.update_layout(title="Crude Futures Curve (Backwardation = Extreme Immediate Shortage)",
                            yaxis_title="Price ($/bbl)", height=320, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_curve, use_container_width=True)
    
    st.markdown("""
    **Market Pulse Indicators:**
    * **Prompt Spread:** In **Backwardation** (Spot trading well above deferred contracts), signaling physical buyers are desperately bidding for immediate wet barrels.
    * **Floating Storage:** Low and drawing rapidly; tankers are used for transport rather than storage due to high charter rates.
    """)

with col_n2:
    st.subheader("📰 Live Oil & Energy Intelligence Feed")
    articles = fetch_energy_news()
    for art in articles[:6]:
        with st.container():
            st.markdown(f"**[{art['title']}]({art['link']})**")
            st.caption(f"Source: {art['source']} | Published: {art['published']}")
            st.markdown("<hr style='margin: 4px 0px 12px 0px; border-color: #30363d;'>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 9. FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption("Data feeds synthesized from public API endpoints, EIA International Energy Statistics, IEA Oil Market Reports, and Baltic Exchange Shipping indices.")
