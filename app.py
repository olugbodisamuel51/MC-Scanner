import streamlit as st
import requests
import time
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Solana Sentinel Super App",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- UTILITY FUNCTIONS ---
def get_dex_data(contract_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs'): return data['pairs'][0]
        return None
    except:
        return None

def get_rugcheck_data(contract_address):
    url = f"https://api.rugcheck.xyz/v1/tokens/{contract_address}/report"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🛰️ Sentinel Hub")
app_mode = st.sidebar.radio("Select Tool", [
    "📡 Live Monitor (V13)",
    "🛡️ Safe Entry Check (V14)",
    "🚫 Anti-Rug Checker",
    "🐋 Whale Hunter",
    "📊 Coin's State Analysis"
])

st.sidebar.markdown("---")
st.sidebar.info("Developed for Live Solana Monitoring")

# ==========================================
# TOOL 1: LIVE MONITOR (Sentinel V13)
# ==========================================
if app_mode == "📡 Live Monitor (V13)":
    st.title("📡 Sentinel V13: Live Monitor")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        token = st.text_input("Enter Token Address", key="v13_token")
    with col2:
        refresh_rate = st.slider("Refresh (s)", 2, 30, 5)

    start_btn = st.toggle("🛰️ Start Monitoring", key="v13_start")
    
    if start_btn and token:
        dashboard = st.empty()
        
        # Session state for tracking start price
        if 'start_price' not in st.session_state:
            st.session_state.start_price = None

        while True:
            pair = get_dex_data(token)
            security = get_rugcheck_data(token)
            
            if not pair:
                dashboard.error("❌ Token not found or API error.")
                time.sleep(5)
                continue
                
            # Extract Data
            try:
                price = float(pair.get('priceUsd', 0))
                if st.session_state.start_price is None: st.session_state.start_price = price
                
                fdv = pair.get('fdv', 0)
                liq = pair.get('liquidity', {}).get('usd', 0)
                vol_m5 = pair.get('volume', {}).get('m5', 0)
                buys = pair.get('txns', {}).get('m5', {}).get('buys', 0)
                sells = pair.get('txns', {}).get('m5', {}).get('sells', 0)
                pair_age_ms = pair.get('pairCreatedAt', 0)
                
                # --- NEW AGE LOGIC ---
                age_mins = (time.time() * 1000 - pair_age_ms) / 60000 if pair_age_ms else 0
                
                if age_mins > 1440: # More than 24 hours (1440 mins)
                    age_display = f"{age_mins/1440:.1f} days"
                elif age_mins > 60: # More than 60 mins
                    age_display = f"{age_mins/60:.1f} hours"
                else: # Minutes
                    age_display = f"{age_mins:.0f} mins"
                # ---------------------

                lp_ratio = (liq / fdv * 100) if fdv > 0 else 0
                drift = ((price - st.session_state.start_price) / st.session_state.start_price) * 100
                
                # Render UI
                with dashboard.container():
                    # Top Metrics
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Price", f"${price:.6f}", f"{drift:.2f}% Session")
                    m2.metric("Market Cap", f"${fdv:,.0f}")
                    m3.metric("Liquidity", f"${liq:,.0f}", f"{lp_ratio:.1f}% Ratio")
                    m4.metric("Age", age_display) # <--- Updated here
                    
                    # Momentum
                    st.progress(buys / (buys+sells) if (buys+sells) > 0 else 0.5, text=f"Momentum: {buys} Buys vs {sells} Sells")
                    
                    # Security Gates (Corrected Display)
                    st.subheader("🛡️ Security Gates")
                    g1, g2, g3 = st.columns(3)
                    
                    # LP Gate
                    lp_locked = "Unknown"
                    if security:
                        lp_pct = 0
                        for m in security.get('markets', []):
                            if m.get('lp', {}).get('lpLocked', 0) > 0:
                                lp_pct = m['lp']['lpLocked']
                        lp_locked = f"{lp_pct:.1f}% Locked"
                    
                    if "Unknown" not in lp_locked:
                        g1.success(f"LP: {lp_locked}")
                    else:
                        g1.warning("LP: Unverified")
                    
                    # Bundle Gate
                    is_bundled = False
                    if security and security.get('risks'):
                        for r in security['risks']:
                            if 'bundle' in r.get('name', '').lower(): is_bundled = True
                    
                    if is_bundled:
                        g2.error("⚠️ BUNDLE DETECTED")
                    else:
                        g2.success("✅ No Bundles")
                    
                    # Vol Gate
                    if vol_m5 > 5000:
                        g3.success(f"Vol: ${vol_m5:,.0f}")
                    else:
                        g3.warning(f"Low Vol: ${vol_m5:,.0f}")

                    st.caption(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
            
            except Exception as e:
                dashboard.error(f"Error parsing data: {e}")

            time.sleep(refresh_rate)
            
# ==========================================
# TOOL 2: SAFE ENTRY CHECK (V14)
# ==========================================
elif app_mode == "🛡️ Safe Entry Check (V14)":
    st.title("🛡️ Sentinel V14: Safe Entry Check")
    token = st.text_input("Enter Token Address", key="v14_token")
    
    if st.button("Analyze Entry"):
        with st.spinner("Analyzing..."):
            pair = get_dex_data(token)
            if not pair:
                st.error("Token not found.")
            else:
                # Logic
                fdv = pair.get('fdv', 0)
                liq = pair.get('liquidity', {}).get('usd', 0)
                created_at = pair.get('pairCreatedAt', 0)
                age_hours = (time.time() - (created_at / 1000)) / 3600 if created_at else 0
                liq_ratio = (liq / fdv * 100) if fdv > 0 else 0
                vol_5m = pair.get('volume', {}).get('m5', 0)
                change_5m = pair.get('priceChange', {}).get('m5', 0)
                
                # Thresholds
                req_ratio = 1.0 if fdv > 10_000_000 else 8.0
                
                # Display
                st.markdown(f"### 🎯 Report: ${pair['baseToken']['symbol']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Market Cap", f"${fdv:,.0f}")
                c2.metric("Liq Ratio", f"{liq_ratio:.1f}%", f"Target: {req_ratio}%")
                c3.metric("Age", f"{age_hours:.1f}h")
                
                reasons = []
                if liq_ratio < req_ratio: reasons.append(f"Liquidity too thin (Has {liq_ratio:.1f}%)")
                if vol_5m < 50 and age_hours > 1: reasons.append("Dead Volume")
                if change_5m > 15: reasons.append(f"Panic Pumping (+{change_5m}%)")
                if age_hours < 0.5: reasons.append("Too New (<30 mins)")
                
                if reasons:
                    st.error("🛑 VERDICT: UNSAFE TO COPY")
                    for r in reasons: st.write(f"⚠️ {r}")
                else:
                    st.success("✅ VERDICT: SAFE ENTRY")
                    st.write("Matches safety criteria.")

# ==========================================
# TOOL 3: ANTI-RUG CHECKER
# ==========================================
elif app_mode == "🚫 Anti-Rug Checker":
    st.title("🚫 Anti-Rug Analyzer")
    token = st.text_input("Enter Token Address", key="rug_token")
    
    if st.button("Scan for Rugs"):
        with st.spinner("Scanning Holder Distribution..."):
            dex = get_dex_data(token)
            rug = get_rugcheck_data(token)
            
            if not dex or not rug:
                st.error("Data unavailable.")
            else:
                top_holders = rug.get('topHolders', [])
                top_1_pct = top_holders[0].get('pct', 0) if top_holders else 0
                top_10_pct = sum(h.get('pct', 0) for h in top_holders[:10])
                
                st.markdown(f"### Security Scan: {dex['baseToken']['name']}")
                
                col1, col2 = st.columns(2)
                
                risk = False
                with col1:
                    st.markdown("**Whale Concentration**")
                    if top_1_pct > 5:
                        st.error(f"❌ Top Holder: {top_1_pct:.2f}% (>5%)")
                        risk = True
                    else:
                        st.success(f"✅ Top Holder: {top_1_pct:.2f}%")
                        
                with col2:
                    st.markdown("**Top 10 Team**")
                    if top_10_pct > 30:
                        st.error(f"❌ Top 10: {top_10_pct:.2f}% (>30%)")
                        risk = True
                    else:
                        st.success(f"✅ Top 10: {top_10_pct:.2f}%")
                
                if risk:
                    st.error("⛔ DANGER: High Whale Manipulation Risk")
                else:
                    st.success("✅ Distribution Looks Healthy")

# ==========================================
# TOOL 4: WHALE HUNTER
# ==========================================
elif app_mode == "🐋 Whale Hunter":
    st.title("🐋 Whale Hunter")
    token = st.text_input("Enter Token Address", key="whale_token")
    
    if st.button("Hunt Whales"):
        pair = get_dex_data(token)
        if pair:
            vol_5m = pair.get('volume', {}).get('m5', 0)
            change_5m = pair.get('priceChange', {}).get('m5', 0)
            buys = pair.get('txns', {}).get('m5', {}).get('buys', 0)
            sells = pair.get('txns', {}).get('m5', {}).get('sells', 0)
            total = buys + sells
            buy_pressure = (buys/total*100) if total > 0 else 50
            
            st.metric("5m Volume", f"${vol_5m:,.0f}")
            st.metric("Price Change (5m)", f"{change_5m}%")
            
            alert = "⚪ Stable"
            if vol_5m > 5000 and abs(change_5m) < 0.1:
                if buy_pressure > 60: alert = "🧱 HIDDEN BUY WALL (Accumulation)"
                elif buy_pressure < 40: alert = "🧱 HIDDEN SELL WALL (Distribution)"
            elif change_5m < -2.0 and buy_pressure > 60:
                alert = "🪤 BEAR TRAP (Price Fakeout)"
            elif change_5m > 2.0 and buy_pressure < 40:
                alert = "🎣 EXIT LIQUIDITY PUMP"
                
            if "Stable" not in alert:
                st.warning(f"🚨 WHALE ALERT: {alert}")
            else:
                st.info("No active whale manipulation detected.")

# ==========================================
# TOOL 5: COIN STATE (IMPROVED)
# ==========================================
elif app_mode == "📊 Coin's State Analysis":
    st.title("📊 Coin's Phase Analyzer")
    token = st.text_input("Enter Token Address", key="state_token")
    
    if st.button("Diagnose Phase"):
        pair = get_dex_data(token)
        if pair:
            liq = pair.get('liquidity', {}).get('usd', 0)
            vol_24 = pair.get('volume', {}).get('h24', 0)
            created_at = pair.get('pairCreatedAt', 0)
            age_hours = (time.time() - (created_at / 1000)) / 3600 if created_at else 0
            change_24 = pair.get('priceChange', {}).get('h24', 0)
            
            # --- IMPROVED LOGIC ---
            phase = "Unknown"
            
            if liq < 5000: 
                phase = "💀 DEAD / RUGGED"
            elif vol_24 < 1000: 
                phase = "💤 DORMANT"
            elif age_hours < 24: 
                phase = "🚀 LAUNCH / DISCOVERY"
            elif change_24 < -30: 
                phase = "📉 DUMPING HARD"
            elif -30 <= change_24 <= -10: 
                phase = "🩸 BLEEDING / CORRECTION"  # <--- This catches your -24%
            elif change_24 > 30: 
                phase = "📈 PUMPING"
            elif 10 <= change_24 <= 30:
                phase = "🌲 STEADY GROWTH"
            elif -10 < change_24 < 10:
                if vol_24 > 50000:
                    phase = "⚖️ ACCUMULATION (High Vol)"
                else:
                    phase = "🦀 CRAB / CHOP (Low Vol)"
            
            st.header(f"Diagnosis: {phase}")
            
            # Display stats nicely
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Liquidity", f"${liq:,.0f}")
            c2.metric("Volume 24h", f"${vol_24:,.0f}")
            c3.metric("Age", f"{age_hours:.1f}h")
            c4.metric("Change 24h", f"{change_24}%")
