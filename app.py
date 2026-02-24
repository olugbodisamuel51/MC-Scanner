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

def send_telegram_alert(message, bot_token, chat_id):
    """Sends a Telegram message and displays errors if it fails."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            st.error(f"Telegram API Error: {response.text}")
    except Exception as e:
        st.error(f"Failed to connect to Telegram: {e}")

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🛰️ Sentinel Hub")
app_mode = st.sidebar.radio("Select Tool", [
    "📡 Live Monitor (V13)",
    "🛡️ Safe Entry Check (V14)",
    "🚫 Anti-Rug Checker",
    "🐋 Whale Hunter",
    "📊 Coin's State Analysis",
    "🎯 Scalp Scanner (Live)"  
])

st.sidebar.markdown("---")
st.sidebar.subheader("📱 Alert Settings")

# Hardcoded Telegram credentials
tg_token = "8534212195:AAH-PYRMFR1h7kt2vGAbx6hH26QWCP0VLDQ" # Using your valid token from the screenshot
tg_chat_id = "1692637798"

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
        
        if 'start_price' not in st.session_state:
            st.session_state.start_price = None

        while True:
            pair = get_dex_data(token)
            security = get_rugcheck_data(token)
            
            if not pair:
                dashboard.error("❌ Token not found or API error.")
                time.sleep(5)
                continue
                
            try:
                price = float(pair.get('priceUsd', 0))
                if st.session_state.start_price is None: st.session_state.start_price = price
                
                fdv = pair.get('fdv', 0)
                liq = pair.get('liquidity', {}).get('usd', 0)
                vol_m5 = pair.get('volume', {}).get('m5', 0)
                buys = pair.get('txns', {}).get('m5', {}).get('buys', 0)
                sells = pair.get('txns', {}).get('m5', {}).get('sells', 0)
                pair_age_ms = pair.get('pairCreatedAt', 0)
                
                age_mins = (time.time() * 1000 - pair_age_ms) / 60000 if pair_age_ms else 0
                
                if age_mins > 1440: 
                    age_display = f"{age_mins/1440:.1f} days"
                elif age_mins > 60: 
                    age_display = f"{age_mins/60:.1f} hours"
                else: 
                    age_display = f"{age_mins:.0f} mins"

                lp_ratio = (liq / fdv * 100) if fdv > 0 else 0
                drift = ((price - st.session_state.start_price) / st.session_state.start_price) * 100
                
                with dashboard.container():
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Price", f"${price:.6f}", f"{drift:.2f}% Session")
                    m2.metric("Market Cap", f"${fdv:,.0f}")
                    m3.metric("Liquidity", f"${liq:,.0f}", f"{lp_ratio:.1f}% Ratio")
                    m4.metric("Age", age_display) 
                    
                    st.progress(buys / (buys+sells) if (buys+sells) > 0 else 0.5, text=f"Momentum: {buys} Buys vs {sells} Sells")
                    
                    st.subheader("🛡️ Security Gates")
                    g1, g2, g3 = st.columns(3)
                    
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
                    
                    is_bundled = False
                    if security and security.get('risks'):
                        for r in security['risks']:
                            if 'bundle' in r.get('name', '').lower(): is_bundled = True
                    
                    if is_bundled:
                        g2.error("⚠️ BUNDLE DETECTED")
                    else:
                        g2.success("✅ No Bundles")
                    
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
                fdv = pair.get('fdv', 0)
                liq = pair.get('liquidity', {}).get('usd', 0)
                created_at = pair.get('pairCreatedAt', 0)
                age_hours = (time.time() - (created_at / 1000)) / 3600 if created_at else 0
                liq_ratio = (liq / fdv * 100) if fdv > 0 else 0
                vol_5m = pair.get('volume', {}).get('m5', 0)
                change_5m = pair.get('priceChange', {}).get('m5', 0)
                
                req_ratio = 1.0 if fdv > 10_000_000 else 8.0
                
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
# TOOL 3: LIVE ANTI-RUG / EXIT MONITOR
# ==========================================
elif app_mode == "🚫 Anti-Rug Checker":
    st.title("🚫 Live Anti-Rug / Exit Monitor")
    st.markdown("Track whale accumulation in real-time. If concentration increases, **GET OUT**.")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        token = st.text_input("Enter Token Address", key="rug_token")
    with c2:
        refresh_rate = st.slider("Refresh (s)", 2, 30, 5, key="rug_refresh")
    
    is_scanning = st.toggle("🛡️ Start Live Protection", key="rug_active")
    
    if is_scanning and token:
        dashboard = st.empty()
        
        # Initialize session state to track the baseline percentages and step alerts
        if 'baseline_top1' not in st.session_state or st.session_state.get('rug_current_token') != token:
            st.session_state.baseline_top1 = None
            st.session_state.baseline_top10 = None
            st.session_state.last_alerted_top1 = None
            st.session_state.last_alerted_top10 = None
            st.session_state.rug_current_token = token
            st.session_state.last_alert_state = "SAFE"

        while True:
            try:
                dex = get_dex_data(token)
                rug = get_rugcheck_data(token)
                
                if not dex or not rug:
                    dashboard.error("❌ Data unavailable or fetching error. Retrying...")
                    time.sleep(refresh_rate)
                    continue
                    
                top_holders = rug.get('topHolders', [])
                top_1_pct = top_holders[0].get('pct', 0) if top_holders else 0
                top_10_pct = sum(h.get('pct', 0) for h in top_holders[:10])
                market_cap = dex.get('fdv', 0)
                symbol = dex.get('baseToken', {}).get('symbol', 'Unknown')
                
                # Set baseline on first successful scan
                if st.session_state.baseline_top1 is None:
                    st.session_state.baseline_top1 = top_1_pct
                    st.session_state.baseline_top10 = top_10_pct
                    st.session_state.last_alerted_top1 = top_1_pct
                    st.session_state.last_alerted_top10 = top_10_pct
                
                # Calculate total movement since scan started
                delta_top1 = top_1_pct - st.session_state.baseline_top1
                delta_top10 = top_10_pct - st.session_state.baseline_top10
                
                # Calculate micro-movement since the LAST alert
                step_top1 = top_1_pct - st.session_state.last_alerted_top1
                step_top10 = top_10_pct - st.session_state.last_alerted_top10
                
                # Determine Risk Thresholds
                is_danger = top_1_pct > 5 or top_10_pct > 30
                is_consolidating = delta_top1 > 0.5 or delta_top10 > 1.0 
                
                # Trigger for +0.01% micro-accumulation (using 0.009 to catch floating point math rounding)
                is_micro_increase = step_top1 >= 0.009 or step_top10 >= 0.009
                
                # --- TELEGRAM ALERT LOGIC (Micro-Tracking) ---
                if is_micro_increase or is_danger or is_consolidating:
                    if is_danger:
                        current_state = "HIGH RISK BREACH"
                    elif is_consolidating:
                        current_state = "WHALE CONSOLIDATION"
                    else:
                        current_state = "MICRO ACCUMULATION (+0.01%)"
                    
                    # Alert if the major risk state escalated OR if we stepped up another +0.01%
                    if st.session_state.last_alert_state != current_state or is_micro_increase:
                        if tg_token and tg_chat_id:
                            msg = f"🚨 <b>SENTINEL ALERT: {symbol}</b> 🚨\n\n"
                            msg += f"⚠️ <b>Status:</b> {current_state}\n"
                            msg += f"💰 <b>Market Cap:</b> ${market_cap:,.0f}\n"
                            msg += f"🐋 <b>Top 1% Holder:</b> {top_1_pct:.2f}% (Total Δ: {delta_top1:+.2f}%)\n"
                            msg += f"🎯 <b>Top 10% Holders:</b> {top_10_pct:.2f}% (Total Δ: {delta_top10:+.2f}%)\n\n"
                            msg += "👉 <b>Action Required: Monitor Closely or Exit.</b>"
                            
                            send_telegram_alert(msg, tg_token, tg_chat_id)
                        
                        # Lock in the new numbers so it waits for the next +0.01% step before pinging again
                        st.session_state.last_alert_state = current_state
                        st.session_state.last_alerted_top1 = top_1_pct
                        st.session_state.last_alerted_top10 = top_10_pct
                else:
                    if not is_danger and not is_consolidating:
                        st.session_state.last_alert_state = "SAFE"
                
                # If whales sell and percentages drop, lower the tracking baseline so we catch them buying back in
                if step_top1 < 0 or step_top10 < 0:
                    st.session_state.last_alerted_top1 = top_1_pct
                    st.session_state.last_alerted_top10 = top_10_pct
                
                # --- DASHBOARD UI ---
                with dashboard.container():
                    st.markdown(f"### Security Scan: ${symbol} | MC: ${market_cap:,.0f}")
                    
                    # --- DYNAMIC EXIT INSTRUCTIONS ---
                    if is_consolidating:
                        st.error("🚨 EXIT NOW: WHALES ARE CONSOLIDATING! 🚨")
                        st.markdown("> **Instruction:** Top holder percentages are increasing since you started tracking. Sell to avoid the incoming dump.")
                    elif is_danger:
                        st.warning("⚠️ CAUTION: High Risk Thresholds Breached. Prepare to exit.")
                    elif is_micro_increase:
                        st.info("🔍 CAUTION: Micro accumulation detected. Watch for sudden consolidation.")
                    else:
                        st.success("✅ SAFE ZONES: Holding steady. No signs of wallet consolidation.")
                        
                    st.divider()
                    
                    # --- METRICS ---
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Top Holder (Whale)**")
                        delta_color = "inverse" if delta_top1 > 0 else "normal"
                        st.metric(
                            "Top 1%", 
                            f"{top_1_pct:.2f}%", 
                            f"{delta_top1:+.2f}% since scan started", 
                            delta_color=delta_color
                        )
                        if top_1_pct > 5:
                            st.error(f"❌ Base Risk: > 5%")
                        else:
                            st.success(f"✅ Base Risk: < 5%")
                            
                    with col2:
                        st.markdown("**Top 10 Team/Snipers**")
                        delta_color2 = "inverse" if delta_top10 > 0 else "normal"
                        st.metric(
                            "Top 10%", 
                            f"{top_10_pct:.2f}%", 
                            f"{delta_top10:+.2f}% since scan started",
                            delta_color=delta_color2
                        )
                        if top_10_pct > 25:
                            st.error(f"❌ Base Risk: > 25%")
                        else:
                            st.success(f"✅ Base Risk: < 25%")

                    st.caption(f"Tracking initialized at: Top 1 ({st.session_state.baseline_top1:.2f}%) | Top 10 ({st.session_state.baseline_top10:.2f}%)")
                    st.caption(f"Last Scan: {datetime.now().strftime('%H:%M:%S')} (Refreshing every {refresh_rate}s)")
                    
            except Exception as e:
                dashboard.error(f"Error checking rug status: {e}")
                
            time.sleep(refresh_rate)

# ==========================================
# TOOL 4: WHALE HUNTER (LIVE AUTO-REFRESH)
# ==========================================
elif app_mode == "🐋 Whale Hunter":
    st.title("🐋 Whale Hunter (Live)")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        token = st.text_input("Enter Token Address", key="whale_token")
    with c2:
        refresh_rate = st.slider("Refresh (s)", 2, 30, 5, key="whale_refresh")
    
    is_hunting = st.toggle("🏹 Start Hunting", key="whale_active")
    
    if is_hunting and token:
        dashboard = st.empty()
        
        while True:
            try:
                pair = get_dex_data(token)
                if not pair:
                    dashboard.error("❌ Token not found. Waiting...")
                    time.sleep(refresh_rate)
                    continue

                vol_5m = pair.get('volume', {}).get('m5', 0)
                change_5m = pair.get('priceChange', {}).get('m5', 0)
                buys = pair.get('txns', {}).get('m5', {}).get('buys', 0)
                sells = pair.get('txns', {}).get('m5', {}).get('sells', 0)
                total = buys + sells
                buy_pressure = (buys/total*100) if total > 0 else 50
                
                alert = "⚪ Stable"
                alert_color = "off"
                
                if vol_5m > 5000 and abs(change_5m) < 0.1:
                    if buy_pressure > 60: 
                        alert = "🧱 HIDDEN BUY WALL (Accumulation)"
                        alert_color = "green"
                    elif buy_pressure < 40: 
                        alert = "🧱 HIDDEN SELL WALL (Distribution)"
                        alert_color = "red"
                
                elif change_5m < -2.0 and buy_pressure > 60:
                    alert = "🪤 BEAR TRAP (Price Fakeout)"
                    alert_color = "green" 
                elif change_5m > 2.0 and buy_pressure < 40:
                    alert = "🎣 EXIT LIQUIDITY PUMP"
                    alert_color = "red" 
                
                elif change_5m > 5:
                    alert = "🚀 PUMPING HARD"
                    alert_color = "green"
                elif change_5m < -5:
                    alert = "📉 DUMPING HARD"
                    alert_color = "red"

                with dashboard.container():
                    st.markdown(f"### Status: {alert}")
                    
                    if alert_color == "red":
                        st.error(f"🚨 ALERT: {alert}")
                    elif alert_color == "green":
                        st.success(f"✅ SIGNAL: {alert}")
                    elif alert_color == "orange":
                        st.warning(f"⚠️ CAUTION: {alert}")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("5m Volume", f"${vol_5m:,.0f}")
                    m2.metric("Price Change (5m)", f"{change_5m}%")
                    m3.metric("Buy Pressure", f"{buy_pressure:.0f}%", f"{buys} Buys / {sells} Sells")
                    
                    st.caption("Buy vs Sell Pressure (5m)")
                    st.progress(buy_pressure / 100, text=f"{buy_pressure:.1f}% Buys")
                    
                    st.divider()
                    st.caption(f"Last Scan: {datetime.now().strftime('%H:%M:%S')} (Refreshing every {refresh_rate}s)")

            except Exception as e:
                dashboard.error(f"Error: {e}")
            
            time.sleep(refresh_rate)

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
                phase = "🩸 BLEEDING / CORRECTION"  
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
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Liquidity", f"${liq:,.0f}")
            c2.metric("Volume 24h", f"${vol_24:,.0f}")
            c3.metric("Age", f"{age_hours:.1f}h")
            c4.metric("Change 24h", f"{change_24}%")

# ==========================================
# TOOL 6: SCALP SCANNER V5 (LIVE AUTO-REFRESH)
# ==========================================
elif app_mode == "🎯 Scalp Scanner (Live)":
    st.title("🎯 Scalp Scanner V5 (Live)")
    st.markdown("Strict entry logic engine optimizing for `+30% to +50%` scalps.")
    
    # Input Layout
    c1, c2 = st.columns([3, 1])
    with c1:
        token = st.text_input("Enter Token Address", key="scalp_token")
    with c2:
        refresh_rate = st.slider("Refresh (s)", 2, 30, 5, key="scalp_refresh")
    
    # Start Toggle
    is_scanning = st.toggle("🎯 Start Scalp Scanner", key="scalp_active")
    
    if is_scanning and token:
        dashboard = st.empty()
        
        while True:
            try:
                pair = get_dex_data(token)
                
                if not pair:
                    dashboard.error("❌ Token not found or liquidity pool isn't live yet. Waiting...")
                    time.sleep(refresh_rate)
                    continue

                symbol = pair.get('baseToken', {}).get('symbol', 'Unknown')
                dex = pair.get('dexId', 'Unknown').upper()
                price_usd = float(pair.get('priceUsd', '0'))
                liquidity = pair.get('liquidity', {}).get('usd', 0)
                
                m5_volume = pair.get('volume', {}).get('m5', 0)
                m5_buys = pair.get('txns', {}).get('m5', {}).get('buys', 0)
                m5_sells = pair.get('txns', {}).get('m5', {}).get('sells', 0)
                m5_price_change = pair.get('priceChange', {}).get('m5', 0)
                
                total_txns_5m = m5_buys + m5_sells
                buy_sell_ratio = round(m5_buys / m5_sells, 2) if m5_sells > 0 else float(m5_buys)
                
                # --- SCALPER'S PROBABILITY ENGINE ---
                win_prob = 0
                
                if m5_volume > 50000: win_prob += 30
                elif m5_volume > 20000: win_prob += 15
                
                if buy_sell_ratio > 2.0: win_prob += 30
                elif buy_sell_ratio > 1.3: win_prob += 15
                
                if total_txns_5m > 400: win_prob += 20
                elif total_txns_5m > 200: win_prob += 10
                
                if 5 <= m5_price_change <= 20: win_prob += 20  
                elif 0 < m5_price_change < 5: win_prob += 5    
                elif m5_price_change > 25: win_prob -= 30      
                elif m5_price_change < 0: win_prob -= 50       
                
                win_prob = max(0, min(100, win_prob))

                # --- PNL PROJECTION LOGIC ---
                if win_prob >= 80:
                    pnl_est = "+30% to +50% (High Conviction Scalp)"
                    state = "🎯 PRIME SCALP ENTRY: Massive heat, perfect momentum."
                    status_color = "success"
                elif win_prob >= 60:
                    pnl_est = "+15% to +30% (Moderate Scalp)"
                    state = "🔥 HEATING UP: Good pressure, monitor closely for breakout."
                    status_color = "info"
                elif win_prob >= 40:
                    pnl_est = "Break-even to +10% (Chop Zone)"
                    state = "⚖️ CONSOLIDATING: Sideways movement, wait for confirmation."
                    status_color = "warning"
                elif m5_price_change < -5 and buy_sell_ratio > 1.1 and m5_volume > 10000:
                    pnl_est = "-30% to -60% (Exit Liquidity)"
                    state = "🚨 DISTRIBUTION TRAP: Whales dumping on retail buys."
                    status_color = "error"
                elif m5_price_change > 25 and win_prob < 40:
                    pnl_est = "-40% to -80% (Buying the Top)"
                    state = "🌋 OVEREXTENDED: Danger of severe pullback. Do not chase."
                    status_color = "error"
                else:
                    pnl_est = "-50% to -100% (Bleed/Dump)"
                    state = "🩸 AVOID / CUT LOSSES: Momentum is dead."
                    status_color = "error"

                # Update Dashboard
                with dashboard.container():
                    st.subheader(f"TOKEN: {symbol} | DEX: {dex}")
                    
                    # Alert Banner
                    if status_color == "success": st.success(state)
                    elif status_color == "info": st.info(state)
                    elif status_color == "warning": st.warning(state)
                    else: st.error(state)
                        
                    # Target & Assurance Metrics
                    col1, col2 = st.columns(2)
                    col1.metric("⚡ WIN ASSURANCE", f"{win_prob}%")
                    col2.metric("💰 PROJECTED PnL", pnl_est)
                    
                    st.progress(win_prob / 100, text="Engine Confidence Score")
                    st.divider()
                    
                    # Data Breakdown
                    st.markdown("### 5-Minute Micro-Metrics")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Volume Velocity", f"${m5_volume:,.2f}")
                    m2.metric("Price Accel", f"{m5_price_change}%", f"${price_usd:,.6f}")
                    m3.metric("Txn Freq", f"{total_txns_5m}", f"Ratio: {buy_sell_ratio}")
                    m4.metric("Liquidity", f"${liquidity:,.2f}")
                    
                    st.caption(f"Pressure Breakdown: {m5_buys} Buys / {m5_sells} Sells")
                    st.caption(f"Last Scan: {datetime.now().strftime('%H:%M:%S')} (Refreshing every {refresh_rate}s)")

            except Exception as e:
                dashboard.error(f"Error fetching data: {e}")
            
            time.sleep(refresh_rate)

# ==========================================
# TOOL 7: LIQUIDITY PRESSURE ENGINE
# ==========================================
elif app_mode == "💧 Liquidity Pressure Engine":
    st.title("💧 Tool 7: Liquidity & Pressure Engine")
    st.markdown("Live monitoring of net volume, transaction battles, and Liquidity Resistance.")
    
    # Input Layout
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        token = st.text_input("Enter Token Address", key="t7_token")
    with c2:
        # User selects the 'x' time period for the volume/tx data
        tf = st.selectbox("Timeframe (x)", ["m5", "h1", "h6", "h24"], key="t7_tf")
    with c3:
        # Live refresh slider
        refresh_rate = st.slider("Refresh (s)", 2, 30, 5, key="t7_refresh")
        
    is_tracking = st.toggle("⚙️ Start Engine", key="t7_active")
    
    if is_tracking and token:
        dashboard = st.empty()
        
        while True:
            try:
                dex = get_dex_data(token)
                rug = get_rugcheck_data(token)
                
                if not dex:
                    dashboard.error("❌ Token not found or API error. Waiting...")
                    time.sleep(refresh_rate)
                    continue
                    
                # 1. Liquidity Locked Status
                lp_status = "Unverified ⚠️"
                if rug:
                    lp_pct = 0
                    for m in rug.get('markets', []):
                        if m.get('lp', {}).get('lpLocked', 0) > 0:
                            lp_pct = m['lp']['lpLocked']
                    if lp_pct > 0:
                        lp_status = f"Yes ({lp_pct:.1f}% Locked) 🔒"
                    else:
                        lp_status = "No (0% Locked) 🚨"
                        
                # 2. Extract Base Metrics
                liquidity = float(dex.get('liquidity', {}).get('usd', 0))
                total_vol = float(dex.get('volume', {}).get(tf, 0))
                txns = dex.get('txns', {}).get(tf, {})
                buys = int(txns.get('buys', 0))
                sells = int(txns.get('sells', 0))
                total_txns = buys + sells
                
                # 3. Calculate Transactions & Volumes
                net_txs = buys - sells
                
                # Approximating Buy/Sell volume based on TX ratio (DEX APIs group volume total)
                buy_ratio = (buys / total_txns) if total_txns > 0 else 0.5
                buy_vol = total_vol * buy_ratio
                sell_vol = total_vol * (1 - buy_ratio)
                net_vol = buy_vol - sell_vol
                
                # 4. Liquidity Resistance Formula: [Net Buy Vol / Liquidity] * 100
                if liquidity > 0:
                    liq_resistance = (net_vol / liquidity) * 100
                else:
                    liq_resistance = 0
                    
                # 5. Determine the Winner
                if net_vol > 0:
                    winner = "🟢 BULLS WINNING (Net Buy Pressure)"
                    res_color = "normal"
                elif net_vol < 0:
                    winner = "🔴 BEARS WINNING (Net Sell Pressure)"
                    res_color = "inverse"
                else:
                    winner = "⚪ NEUTRAL (Stagnant)"
                    res_color = "off"
                    
                # --- DASHBOARD UI ---
                with dashboard.container():
                    st.subheader(f"Token: {dex.get('baseToken', {}).get('symbol', 'Unknown')}")
                    st.markdown(f"**Liquidity Locked:** {lp_status}")
                    st.markdown(f"**Market Dominance:** {winner}")
                    
                    st.divider()
                    
                    # Volume Metrics
                    st.markdown(f"### 📊 Volume Battle ({tf})")
                    v1, v2, v3 = st.columns(3)
                    v1.metric("Buy Volume", f"${buy_vol:,.2f}")
                    v2.metric("Sell Volume", f"${sell_vol:,.2f}")
                    v3.metric("NET Volume", f"${net_vol:,.2f}", f"{'+' if net_vol > 0 else ''}{net_vol:,.2f} USD")
                    
                    # TX Metrics
                    st.markdown(f"### ⚔️ Transaction Battle ({tf})")
                    t1, t2, t3 = st.columns(3)
                    t1.metric("Buy Txs", f"{buys}")
                    t2.metric("Sell Txs", f"{sells}")
                    t3.metric("NET Txs", f"{net_txs}", f"{'+' if net_txs > 0 else ''}{net_txs} Txs")
                    
                    st.divider()
                    
                    # Liquidity Resistance
                    st.markdown("### 🧱 Liquidity Resistance (Force vs Mass)")
                    r1, r2 = st.columns([1, 2])
                    r1.metric("Total Liquidity", f"${liquidity:,.2f}")
                    
                    if liq_resistance > 0:
                        res_state = "🔥 Upward pressure overcoming LP mass."
                    elif liq_resistance < 0:
                        res_state = "🩸 Downward pressure dragging LP mass."
                    else:
                        res_state = "⚖️ No pressure applied."
                        
                    r2.metric(
                        f"Liquidity Resistance ({tf})", 
                        f"{liq_resistance:+.2f}%", 
                        res_state, 
                        delta_color=res_color
                    )
                    
                    st.caption(f"Last Scan: {datetime.now().strftime('%H:%M:%S')} (Refreshing every {refresh_rate}s) | Volume distributed via TX ratio.")
                    
            except Exception as e:
                dashboard.error(f"Error parsing engine data: {e}")
                
            time.sleep(refresh_rate)
