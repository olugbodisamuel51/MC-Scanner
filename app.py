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
            pairs = data.get('pairs', [])
            if not pairs: return None
            
            # 1. Filter for Solana pairs only
            sol_pairs = [p for p in pairs if p.get('chainId') == 'solana']
            if not sol_pairs: return pairs[0] 
            
            # 2. Grab the main pair for baseline data (Price, Symbol, FDV)
            main_pair = max(sol_pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
            
            # 3. Create a Synthetic Aggregated Pair
            aggregated_pair = dict(main_pair)
            
            # 4. Sum up all Liquidity across Raydium, Meteora, Orca, etc.
            total_liq = sum(float(p.get('liquidity', {}).get('usd', 0)) for p in sol_pairs)
            aggregated_pair['liquidity'] = {'usd': total_liq}
            
            # 5. Sum up Volume and Transactions for all timeframes
            aggregated_pair['volume'] = {}
            aggregated_pair['txns'] = {}
            
            for tf in ['m5', 'h1', 'h6', 'h24']:
                aggregated_pair['volume'][tf] = sum(float(p.get('volume', {}).get(tf, 0)) for p in sol_pairs)
                buys = sum(int(p.get('txns', {}).get(tf, {}).get('buys', 0)) for p in sol_pairs)
                sells = sum(int(p.get('txns', {}).get(tf, {}).get('sells', 0)) for p in sol_pairs)
                aggregated_pair['txns'][tf] = {'buys': buys, 'sells': sells}
                
            return aggregated_pair
            
        return None
    except:
        return None

def get_rugcheck_data(contract_address):
    url = f"https://api.rugcheck.xyz/v1/tokens/{contract_address}/report"
    try:
        response = requests.get(url, timeout=5)
        
        # Check if the response is successful AND is actually JSON data (not an HTML maintenance page)
        if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
            return response.json()
        else:
            # If it's a maintenance page or error, return an empty dictionary instead of 'None'
            return {} 
            
    except Exception as e:
        # If the server is completely dead and times out, return an empty dictionary
        return {}

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
    "🎯 Scalp Scanner (Live)",
    "💧 Liquidity Pressure Engine",
    "🧠 Deep Psychology Scanner (Tool 8)",
    "🕵️ Cabal Entry Sniffer (Tool 9)"  # <--- ADD THIS LINE
    "🚀 Moon Sniffer (Tool 10)"  # <--- ADD THIS LINE
])
st.sidebar.markdown("---")
st.sidebar.subheader("📱 Alert Settings")

# Hardcoded Telegram credentials
tg_token = "8534212195:AAH-PYRMFR1h7kt2vGAbx6hH26QWCP0VLDQ" 
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
                
                if st.session_state.baseline_top1 is None:
                    st.session_state.baseline_top1 = top_1_pct
                    st.session_state.baseline_top10 = top_10_pct
                    st.session_state.last_alerted_top1 = top_1_pct
                    st.session_state.last_alerted_top10 = top_10_pct
                
                delta_top1 = top_1_pct - st.session_state.baseline_top1
                delta_top10 = top_10_pct - st.session_state.baseline_top10
                
                step_top1 = top_1_pct - st.session_state.last_alerted_top1
                step_top10 = top_10_pct - st.session_state.last_alerted_top10
                
                is_danger = top_1_pct > 5 or top_10_pct > 30
                is_consolidating = delta_top1 > 0.5 or delta_top10 > 1.0 
                
                is_micro_increase = step_top1 >= 0.009 or step_top10 >= 0.009
                
                if is_micro_increase or is_danger or is_consolidating:
                    if is_danger:
                        current_state = "HIGH RISK BREACH"
                    elif is_consolidating:
                        current_state = "WHALE CONSOLIDATION"
                    else:
                        current_state = "MICRO ACCUMULATION (+0.01%)"
                    
                    if st.session_state.last_alert_state != current_state or is_micro_increase:
                        if tg_token and tg_chat_id:
                            msg = f"🚨 <b>SENTINEL ALERT: {symbol}</b> 🚨\n\n"
                            msg += f"⚠️ <b>Status:</b> {current_state}\n"
                            msg += f"💰 <b>Market Cap:</b> ${market_cap:,.0f}\n"
                            msg += f"🐋 <b>Top 1% Holder:</b> {top_1_pct:.2f}% (Total Δ: {delta_top1:+.2f}%)\n"
                            msg += f"🎯 <b>Top 10% Holders:</b> {top_10_pct:.2f}% (Total Δ: {delta_top10:+.2f}%)\n\n"
                            msg += "👉 <b>Action Required: Monitor Closely or Exit.</b>"
                            
                            send_telegram_alert(msg, tg_token, tg_chat_id)
                        
                        st.session_state.last_alert_state = current_state
                        st.session_state.last_alerted_top1 = top_1_pct
                        st.session_state.last_alerted_top10 = top_10_pct
                else:
                    if not is_danger and not is_consolidating:
                        st.session_state.last_alert_state = "SAFE"
                
                if step_top1 < 0 or step_top10 < 0:
                    st.session_state.last_alerted_top1 = top_1_pct
                    st.session_state.last_alerted_top10 = top_10_pct
                
                with dashboard.container():
                    st.markdown(f"### Security Scan: ${symbol} | MC: ${market_cap:,.0f}")
                    
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
    
    c1, c2 = st.columns([3, 1])
    with c1:
        token = st.text_input("Enter Token Address", key="scalp_token")
    with c2:
        refresh_rate = st.slider("Refresh (s)", 2, 30, 5, key="scalp_refresh")
    
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

                with dashboard.container():
                    st.subheader(f"TOKEN: {symbol} | DEX: {dex}")
                    
                    if status_color == "success": st.success(state)
                    elif status_color == "info": st.info(state)
                    elif status_color == "warning": st.warning(state)
                    else: st.error(state)
                        
                    col1, col2 = st.columns(2)
                    col1.metric("⚡ WIN ASSURANCE", f"{win_prob}%")
                    col2.metric("💰 PROJECTED PnL", pnl_est)
                    
                    st.progress(win_prob / 100, text="Engine Confidence Score")
                    st.divider()
                    
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
    
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        token = st.text_input("Enter Token Address", key="t7_token")
    with c2:
        tf = st.selectbox("Timeframe (x)", ["m5", "h1", "h6", "h24"], key="t7_tf")
    with c3:
        refresh_rate = st.slider("Refresh (s)", 2, 30, 5, key="t7_refresh")
        
    is_tracking = st.toggle("⚙️ Start Engine", key="t7_active")

    # Reset tracking baseline if the toggle is turned off
    if not is_tracking:
        st.session_state.pop('t7_tracking_key', None)
    
    if is_tracking and token:
        dashboard = st.empty()

        # Initialize session state to track the baseline when you start searching
        current_t7_key = f"{token}_{tf}"
        if st.session_state.get('t7_tracking_key') != current_t7_key:
            st.session_state.t7_tracking_key = current_t7_key
            st.session_state.t7_start_net_vol = None
            st.session_state.t7_start_time = time.time()
        
        while True:
            try:
                dex = get_dex_data(token)
                rug = get_rugcheck_data(token)
                
                if not dex:
                    dashboard.error("❌ Token not found or API error. Waiting...")
                    time.sleep(refresh_rate)
                    continue
                    
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
                        
                liquidity = float(dex.get('liquidity', {}).get('usd', 0))
                market_cap = float(dex.get('fdv', 0))
                total_vol = float(dex.get('volume', {}).get(tf, 0))
                txns = dex.get('txns', {}).get(tf, {})
                buys = int(txns.get('buys', 0))
                sells = int(txns.get('sells', 0))
                total_txns = buys + sells
                
                net_txs = buys - sells
                buy_ratio = (buys / total_txns) if total_txns > 0 else 0.5
                buy_vol = total_vol * buy_ratio
                sell_vol = total_vol * (1 - buy_ratio)
                net_vol = buy_vol - sell_vol

                # Capture baseline on the very first successful tick
                if st.session_state.t7_start_net_vol is None:
                    st.session_state.t7_start_net_vol = net_vol

                # Calculate Aggregate metrics
                agg_net_vol = net_vol - st.session_state.t7_start_net_vol
                agg_liq_resistance = (agg_net_vol / liquidity) * 100 if liquidity > 0 else 0
                
                if market_cap > 0:
                    liq_ratio = (liquidity / market_cap) * 100
                else:
                    liq_ratio = 0
                    
                if liq_ratio >= 10.0:
                    health_status = "✅ SAFE (Solid Foundation)"
                    health_color = "normal"  
                elif liq_ratio >= 5.0:
                    health_status = "⚠️ MODERATE (Monitor Closely)"
                    health_color = "off"     
                else:
                    health_status = "🚨 DANGER (Paper-Thin LP / High Rug Risk)"
                    health_color = "inverse" 

                if liquidity > 0:
                    liq_resistance = (net_vol / liquidity) * 100
                else:
                    liq_resistance = 0
                    
                if liq_resistance >= 5.0:
                    res_state = "🌋 OVERWHELMING upward force!"
                    res_color = "normal"
                elif liq_resistance >= 2.0:
                    res_state = "🔥 Strong upward pressure."
                    res_color = "normal"
                elif liq_resistance >= 0.5:
                    res_state = "📈 Slight net buying."
                    res_color = "normal"
                elif liq_resistance > -0.5:
                    res_state = "⚖️ Market Noise / Chop (Insignificant)"
                    res_color = "off"
                elif liq_resistance > -2.0:
                    res_state = "📉 Slight net selling."
                    res_color = "inverse"
                elif liq_resistance > -5.0:
                    res_state = "🩸 Strong downward pressure."
                    res_color = "inverse"
                else:
                    res_state = "🕳️ OVERWHELMING downward force!"
                    res_color = "inverse"

                # Aggregate State Logic
                if agg_liq_resistance >= 0.5:
                    agg_res_state = "📈 Net Accumulation"
                    agg_res_color = "normal"
                elif agg_liq_resistance <= -0.5:
                    agg_res_state = "📉 Net Distribution"
                    agg_res_color = "inverse"
                else:
                    agg_res_state = "⚖️ Neutral Session"
                    agg_res_color = "off"

                if net_vol > 0 and liq_resistance >= 0.5:
                    winner = "🟢 BULLS WINNING (Net Buy Pressure)"
                elif net_vol < 0 and liq_resistance <= -0.5:
                    winner = "🔴 BEARS WINNING (Net Sell Pressure)"
                else:
                    winner = "⚪ NEUTRAL (Stagnant / Choppy)"
                    
                with dashboard.container():
                    st.subheader(f"Token: {dex.get('baseToken', {}).get('symbol', 'Unknown')}")
                    st.markdown(f"**Liquidity Locked:** {lp_status}")
                    st.markdown(f"**Market Dominance:** {winner}")
                    
                    st.divider()
                    
                    st.markdown(f"### 📊 Volume Battle ({tf})")
                    v1, v2, v3 = st.columns(3)
                    v1.metric("Buy Volume", f"${buy_vol:,.2f}")
                    v2.metric("Sell Volume", f"${sell_vol:,.2f}")
                    v3.metric("NET Volume", f"${net_vol:,.2f}", f"{'+' if net_vol > 0 else ''}{net_vol:,.2f} USD")
                    
                    st.markdown(f"### ⚔️ Transaction Battle ({tf})")
                    t1, t2, t3 = st.columns(3)
                    t1.metric("Buy Txs", f"{buys}")
                    t2.metric("Sell Txs", f"{sells}")
                    t3.metric("NET Txs", f"{net_txs}", f"{'+' if net_txs > 0 else ''}{net_txs} Txs")
                    
                    st.divider()
                    
                    st.markdown("### 🧱 Liquidity Foundation & Resistance")
                    st.markdown(f"**Structural Health:** {health_status}")
                    
                    r1, r2, r3, r4 = st.columns(4)
                    r1.metric("Market Cap (FDV)", f"${market_cap:,.2f}")
                    r2.metric(
                        "Total Liquidity", 
                        f"${liquidity:,.2f}", 
                        f"{liq_ratio:.2f}% Liq/MC Ratio", 
                        delta_color=health_color
                    )
                    r3.metric(
                        f"Net Force ({tf})", 
                        f"{liq_resistance:+.2f}%", 
                        res_state, 
                        delta_color=res_color
                    )
                    
                    session_duration = int(time.time() - st.session_state.t7_start_time)
                    mins, secs = divmod(session_duration, 60)
                    
                    r4.metric(
                        f"Session Force (Agg)", 
                        f"{agg_liq_resistance:+.2f}%", 
                        f"{agg_res_state} ({mins}m {secs}s)", 
                        delta_color=agg_res_color
                    )
                    
                    st.caption(f"Last Scan: {datetime.now().strftime('%H:%M:%S')} (Refreshing every {refresh_rate}s) | Volume distributed via TX ratio.")
                    
            except Exception as e:
                dashboard.error(f"Error parsing engine data: {e}")
                
            time.sleep(refresh_rate)

    # ==========================================
# TOOL 8: DEEP PSYCHOLOGY SCANNER
# ==========================================
elif app_mode == "🧠 Deep Psychology Scanner (Tool 8)":
    
    import pandas as pd
    import time
    from datetime import datetime
    
    # Define the class logic
    class AdvancedArchetypeClassifier:
        def __init__(self):
            # Stores the live tracking history
            self.history = pd.DataFrame(columns=["timestamp", "mc", "top1", "top10"])
            
        def add_data_point(self, timestamp, mc, top1, top10):
            """Feeds live data into the tracker."""
            new_row = pd.DataFrame({
                "timestamp": [timestamp],
                "mc": [mc],
                "top1": [top1],
                "top10": [top10]
            })
            # Use pd.concat for cleaner dataframe building in modern pandas
            self.history = pd.concat([self.history, new_row], ignore_index=True)
            
        def analyze_token(self):
            """Analyzes time-series data to detect advanced market psychology."""
            if len(self.history) < 3:
                return "⏳ Gathering Data...", "Need at least 3 data points to establish a baseline and trend.", "gray"
                
            baseline = self.history.iloc[0]
            prev = self.history.iloc[-2]
            current = self.history.iloc[-1]
            
            # --- VARIABLES FOR LOGIC ---
            current_mc = current['mc']
            prev_mc = prev['mc']
            baseline_mc = baseline['mc']
            
            current_1pct = current['top1']
            prev_1pct = prev['top1']
            baseline_1pct = baseline['top1']
            
            current_10pct = current['top10']
            prev_10pct = prev['top10']
            
            # Deltas
            mc_delta = current_mc - prev_mc
            delta_1pct = current_1pct - prev_1pct
            delta_10pct = current_10pct - prev_10pct
            
            noise = 0.05 
            mc_tolerance = 0.05 
            mc_round_trip_ceiling = baseline_mc * (1 + mc_tolerance)
            
            # --- 1. FARM DETECTOR LOGIC (Highest Priority) ---
            # Check if a pump actually happened first to avoid false positives on flat charts
            max_mc = self.history['mc'].max()
            has_pumped = max_mc > (baseline_mc * (1 + mc_tolerance))
            
            if has_pumped:
                is_mc_reset = current_mc <= mc_round_trip_ceiling
                is_whale_reloaded = current_1pct >= (baseline_1pct - noise)
                
                if is_mc_reset and is_whale_reloaded:
                    return "🚫 FARMING OPERATION (Blacklist)", "Devs/Snipers completed a round trip. They swung the pump and bought back the floor.", "red"
                elif is_mc_reset and not is_whale_reloaded:
                    return "🟢 HEALTHY RESET", "Market cap reset after a pump, and whales permanently distributed their supply.", "green"

            # --- 2. DIVERGENCE TRAP LOGIC ---
            if delta_1pct > noise and delta_10pct < -noise:
                return "🚨 INSIDER CONSOLIDATION (Trap)", "Top wallets are eating mid-tier wallets. High risk of a dump.", "red"
            elif delta_1pct < -noise and delta_10pct > noise:
                return "🚨 WALLET SPLITTING", "Whales are hiding tokens in smaller wallets to fake decentralization.", "red"

            # --- 3. STANDARD TREND ANALYSIS ---
            whale_delta = delta_1pct 
            
            if mc_delta > 0 and whale_delta < -noise:
                return "🟢 ORGANIC GROWTH", "MC is up, whales are distributing. Healthy uptrend.", "green"
            elif mc_delta > 0 and whale_delta > noise:
                return "⚠️ MANIPULATIVE PUMP", "MC is up, but whales are centralizing. FOMO trap active.", "orange"
            elif mc_delta < 0 and whale_delta < -noise:
                return "🟡 HEALTHY RETRACE", "MC is dropping, but whales are distributing. Finding support.", "orange"
            elif mc_delta < 0 and whale_delta > noise:
                return "🩸 PANIC BLEED (Slop)", "Retail is selling, whales are slowly absorbing the floor.", "red"

           # --- 4. MACRO TREND FALLBACK & CONSOLIDATION ---
            # If the tick-to-tick movement is totally flat, check the overall session trend
            macro_mc_pct = ((current_mc - baseline_mc) / baseline_mc) * 100 if baseline_mc > 0 else 0
            macro_whale_delta = current_1pct - baseline_1pct

            if abs(mc_delta) < 1.0: # If the immediate 10-second movement is essentially $0
                if macro_mc_pct <= -5.0 and macro_whale_delta >= 0.50:
                    return "🩸 MACRO BLEED (Stalled)", f"Tick is flat, but overall PnL is {macro_mc_pct:.1f}%. Whales are eating the slow bleed.", "red"
                elif macro_mc_pct >= 5.0 and macro_whale_delta <= -0.50:
                    return "🟢 MACRO UPTREND (Stalled)", f"Tick is flat, but overall PnL is +{macro_mc_pct:.1f}%. Whales are distributing.", "green"
                else:
                    return "⚪ CONSOLIDATION", "Movements are too small to classify. Waiting for breakout.", "gray"
            
            else:
                return "⚪ CONSOLIDATION", "Movements are too small to classify. Waiting for breakout.", "gray"

#--- STREAMLIT DASHBOARD UI ---
    st.title("Tool 8 v2.0: Deep Psychology Scanner 🧠")
    st.markdown("Automated live scanning of market cap and whale concentration to detect cabal manipulation.")

    c1, c2 = st.columns([3, 1])
    with c1:
        token = st.text_input("Enter Token Address", key="t8_token")
    with c2:
        refresh_rate = st.slider("Refresh (s)", 2, 60, 10, key="t8_refresh")
        
    is_scanning = st.toggle("🧠 Start Deep Scan", key="t8_active")
    
    # Handle session state for the analyzer
    if 'adv_analyzer' not in st.session_state:
        st.session_state.adv_analyzer = AdvancedArchetypeClassifier()
        
    if 't8_current_token' not in st.session_state:
        st.session_state.t8_current_token = None

    if is_scanning and token:
        # Reset tracker if we switch to a new token
        if st.session_state.t8_current_token != token:
            st.session_state.adv_analyzer = AdvancedArchetypeClassifier()
            st.session_state.t8_current_token = token
            
        dashboard = st.empty()
        
        while True:
            try:
                # 1. Fetch live blockchain data using your utility functions
                # (Assuming get_dex_data and get_rugcheck_data are defined elsewhere in your script)
                dex = get_dex_data(token)
                rug = get_rugcheck_data(token)
                
                if not dex or not rug:
                    dashboard.error("❌ Token not found or API error. Waiting...")
                    time.sleep(refresh_rate)
                    continue
                
                # 2. Extract specific metrics needed for Tool 8
                market_cap = float(dex.get('fdv', 0))
                symbol = dex.get('baseToken', {}).get('symbol', 'Unknown')
                
                top_holders = rug.get('topHolders', [])
                top_1_pct = top_holders[0].get('pct', 0) if top_holders else 0
                top_10_pct = sum(h.get('pct', 0) for h in top_holders[:10])
                
                current_time = datetime.now().strftime('%H:%M:%S')
                
                # 3. Inject data into the internal Engine
                st.session_state.adv_analyzer.add_data_point(current_time, market_cap, top_1_pct, top_10_pct)
                
                # --- CALCULATE 3D TRACKING DELTAS FOR THE UI ---
                baseline_mc = st.session_state.adv_analyzer.history.iloc[0]['mc']
                pnl_pct = ((market_cap - baseline_mc) / baseline_mc) * 100 if baseline_mc > 0 else 0
                
                baseline_top1 = st.session_state.adv_analyzer.history.iloc[0]['top1']
                delta_top1 = top_1_pct - baseline_top1
                
                baseline_top10 = st.session_state.adv_analyzer.history.iloc[0]['top10']
                delta_top10 = top_10_pct - baseline_top10
                
                # 4. Get the psychological verdict
                verdict_title, verdict_desc, color = st.session_state.adv_analyzer.analyze_token()
                
                # Map colors to streamlit alert boxes
                if color == "red": alert_color = "error"
                elif color == "green": alert_color = "success"
                elif color == "orange": alert_color = "warning"
                else: alert_color = "info"
                
                # 5. Render the Dashboard
                with dashboard.container():
                    st.subheader(f"Token: {symbol}")
                    
                    m1, m2, m3 = st.columns(3)
                    # PnL displays normal (Green for +, Red for -)
                    m1.metric("Market Cap", f"${market_cap:,.0f}", f"{pnl_pct:+.2f}% PnL (Session)")
                    # Whale metrics display INVERSE (Red if they are buying +, Green if they are selling -)
                    m2.metric("Top 1% Whale", f"{top_1_pct:.2f}%", f"{delta_top1:+.2f}%", delta_color="inverse")
                    m3.metric("Top 10% Cabal", f"{top_10_pct:.2f}%", f"{delta_top10:+.2f}%", delta_color="inverse")
                    
                    st.markdown("### 🎯 Live Behavioral Verdict")
                    if alert_color == "error": st.error(f"### {verdict_title}\n{verdict_desc}")
                    elif alert_color == "success": st.success(f"### {verdict_title}\n{verdict_desc}")
                    elif alert_color == "warning": st.warning(f"### {verdict_title}\n{verdict_desc}")
                    else: st.info(f"### {verdict_title}\n{verdict_desc}")
                    
                    st.divider()
                    st.markdown("### Internal Tracking Matrix")
                    st.dataframe(st.session_state.adv_analyzer.history.tail(5), use_container_width=True)
                    st.caption(f"Session started tracking at Market Cap: ${baseline_mc:,.0f}")
                    st.caption(f"Last Scan: {current_time} (Refreshing every {refresh_rate}s)")
                    
            except Exception as e:
                dashboard.error(f"Error fetching live data: {e}")
                
            time.sleep(refresh_rate)
            
# ==========================================
# TOOL 9: CABAL ENTRY SNIFFER (DYNAMIC MC)
# ==========================================
elif app_mode == "🕵️ Cabal Entry Sniffer (Tool 9)":
    
    import pandas as pd
    import time
    from datetime import datetime

    class DynamicEntryEngine:
        def __init__(self):
            self.history = pd.DataFrame(columns=["timestamp", "mc", "top1", "top10"])
            
        def add_data_point(self, timestamp, mc, top1, top10):
            new_row = pd.DataFrame({"timestamp": [timestamp], "mc": [mc], "top1": [top1], "top10": [top10]})
            self.history = pd.concat([self.history, new_row], ignore_index=True)
            
        def analyze_entry(self):
            if len(self.history) < 5:
                return "⏳ Calibrating Floor...", "Gathering data to establish support baseline.", "gray", 0
                
            current = self.history.iloc[-1]
            current_mc = current['mc']
            
# --- 1. DYNAMIC TIER DETECTION ---
            if current_mc < 500_000:
                tier = "Micro-Cap (Trench Mode)"
                anomaly_threshold = 2.0  # Needs massive 2%+ delta to filter out retail noise
                max_healthy_top1 = 15.0  # High initial concentration is normal here
                max_healthy_top10 = 35.0 # Give trench coins a bit of leeway, but cap at 35%
            else:
                tier = "Macro-Cap (Established)"
                anomaly_threshold = 0.35 # Stealth cabal accumulation (+0.35% is significant)
                max_healthy_top1 = 8.0   # Should be highly decentralized by now
                max_healthy_top10 = 25.0 # Macro-caps must be distributed (< 25%)
                
        # --- 2. FLOOR DETECTION ---
            # Look at the last 10 scans to find the local bottom
            recent_window = self.history.tail(10)
            local_min_mc = recent_window['mc'].min()
            
            # If current MC is within 5% of the local minimum, we are sitting at the "Floor"
            is_at_floor = current_mc <= (local_min_mc * 1.05)
            
            # --- 3. DELTA CALCULATION (Since hitting the floor) ---
            # Compare current holders to the holders when the local minimum was established
            floor_row = recent_window[recent_window['mc'] == local_min_mc].iloc[0]
            delta_10pct = current['top10'] - floor_row['top10']
            delta_1pct = current['top1'] - floor_row['top1']
            
            # --- 4. CABAL ENTRY LOGIC ---
            # TOXIC SUPPLY CHECK: Evaluate BOTH Top 1% and Top 10%
            if current['top1'] > max_healthy_top1 or current['top10'] > max_healthy_top10:
                return f"🛑 TOXIC SUPPLY ({tier})", f"Top 1% holds {current['top1']:.1f}% | Top 10% holds {current['top10']:.1f}%. Exceeds safety limits. Do not enter.", "red", anomaly_threshold
                
            if is_at_floor:
                if delta_10pct >= anomaly_threshold:
                    return f"🎯 SPRING LOADED! ({tier})", f"Price is at the floor ($ {local_min_mc:,.0f}) and Top 10% spiked by +{delta_10pct:.2f}%. CABAL IS LOADING!", "green", anomaly_threshold
                elif delta_10pct <= -anomaly_threshold:
                    return f"🩸 FLOOR FAILING ({tier})", f"Price is at the floor but whales are STILL dumping ({delta_10pct:.2f}%). Support will break.", "red", anomaly_threshold
                else:
                    return f"⚖️ WATCHING FLOOR ({tier})", f"Price stabilized at $ {local_min_mc:,.0f}. Waiting for Cabal spike > +{anomaly_threshold}%...", "warning", anomaly_threshold
            else:
                # Price is pushing up
                mc_pump_pct = ((current_mc - local_min_mc) / local_min_mc) * 100
                if delta_1pct < 0:
                    return f"🟢 HEALTHY MARKUP ({tier})", f"Price up +{mc_pump_pct:.1f}% from floor. Whales are distributing to retail. Safe to ride.", "green", anomaly_threshold
                elif delta_1pct > anomaly_threshold / 2:
                    return f"⚠️ MANIPULATIVE PUMP ({tier})", f"Price up, but Whales are accumulating (+{delta_1pct:.2f}%). Fakeout risk.", "orange", anomaly_threshold
                else:
                    return f"📈 TRENDING UP ({tier})", f"Price moving up naturally. Monitor for resistance.", "gray", anomaly_threshold

    # --- UI ---
    st.title("🕵️ Tool 9: Cabal Entry Sniffer")
    st.markdown("Dynamic floor-detection engine. Automatically switches sensitivity between Micro-caps and Macro-caps.")

    c1, c2 = st.columns([3, 1])
    with c1:
        token = st.text_input("Enter Token Address", key="t9_token")
    with c2:
        refresh_rate = st.slider("Refresh (s)", 2, 60, 5, key="t9_refresh")
        
    is_scanning = st.toggle("🎯 Start Sniper", key="t9_active")
    
    if 'entry_engine' not in st.session_state:
        st.session_state.entry_engine = DynamicEntryEngine()
    if 't9_current_token' not in st.session_state:
        st.session_state.t9_current_token = None

    if is_scanning and token:
        if st.session_state.t9_current_token != token:
            st.session_state.entry_engine = DynamicEntryEngine()
            st.session_state.t9_current_token = token
            
        dashboard = st.empty()
        
        while True:
            try:
                dex = get_dex_data(token)
                rug = get_rugcheck_data(token)
                
                if not dex or not rug:
                    dashboard.error("❌ Token not found or API error. Waiting...")
                    time.sleep(refresh_rate)
                    continue
                
                market_cap = float(dex.get('fdv', 0))
                symbol = dex.get('baseToken', {}).get('symbol', 'Unknown')
                top_holders = rug.get('topHolders', [])
                top_1_pct = top_holders[0].get('pct', 0) if top_holders else 0
                top_10_pct = sum(h.get('pct', 0) for h in top_holders[:10])
                current_time = datetime.now().strftime('%H:%M:%S')
                
                st.session_state.entry_engine.add_data_point(current_time, market_cap, top_1_pct, top_10_pct)
                
                # Fetch Logic
                verdict_title, verdict_desc, color, target_anomaly = st.session_state.entry_engine.analyze_entry()
                
                # Map colors
                if color == "red": alert_color = "error"
                elif color == "green": alert_color = "success"
                elif color == "warning": alert_color = "warning"
                elif color == "orange": alert_color = "warning"
                else: alert_color = "info"
                
                with dashboard.container():
                    st.subheader(f"Sniper Target: {symbol}")
                    
                    st.markdown("### 🎯 Entry Signal")
                    if alert_color == "error": st.error(f"### {verdict_title}\n{verdict_desc}")
                    elif alert_color == "success": st.success(f"### {verdict_title}\n{verdict_desc}")
                    elif alert_color == "warning": st.warning(f"### {verdict_title}\n{verdict_desc}")
                    else: st.info(f"### {verdict_title}\n{verdict_desc}")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Live Market Cap", f"${market_cap:,.0f}")
                    m2.metric("Top 10% Cabal", f"{top_10_pct:.2f}%")
                    m3.metric("Required Anomaly Spike", f"+{target_anomaly}% Δ")
                    
                    st.divider()
                    st.dataframe(st.session_state.entry_engine.history.tail(5), use_container_width=True)
                    
            except Exception as e:
                dashboard.error(f"Error fetching live data: {e}")
                
            time.sleep(refresh_rate)


# ==========================================
# TOOL 10: MOON SNIFFER (HIT & RUN ENGINE)
# ==========================================
elif app_mode == "🚀 Moon Sniffer (Tool 10)":
    
    import pandas as pd
    import time
    from datetime import datetime

    class MoonSnifferEngine:
        def __init__(self):
            # Keeps a rolling window of the last 20 scans to track local ceilings
            self.history = pd.DataFrame(columns=["timestamp", "mc", "top1", "top10"])
            
        def add_data_point(self, timestamp, mc, top1, top10):
            new_row = pd.DataFrame({"timestamp": [timestamp], "mc": [mc], "top1": [top1], "top10": [top10]})
            self.history = pd.concat([self.history, new_row], ignore_index=True)
            # Keep memory lean, only need the last 20 ticks to find a breakout
            if len(self.history) > 20:
                self.history = self.history.iloc[1:]
                
        def analyze_moon_setup(self):
            if len(self.history) < 5:
                return "⏳ Mapping the Chop Zone...", "Gathering baseline data.", "gray", 0, 0
                
            current = self.history.iloc[-1]
            baseline = self.history.iloc[0]
            
            current_mc = current['mc']
            
            # --- FIND THE CEILING ---
            local_max_mc = self.history['mc'].max()
            is_breaking_out = current_mc >= local_max_mc and current_mc > (baseline['mc'] * 1.05)
            
            # --- CALCULATE DELTAS ---
            mc_delta_pct = ((current_mc - baseline['mc']) / baseline['mc']) * 100 if baseline['mc'] > 0 else 0
            delta_1pct = current['top1'] - baseline['top1']
            delta_10pct = current['top10'] - baseline['top10']
            
            # --- 1. THE EXIT TRAP (The "Funny Delta") ---
            # MC is stalling/dropping, but top wallets are suddenly BUYING (+1.0% or more)
            if mc_delta_pct < 5 and (delta_1pct > 1.0 or delta_10pct > 1.5):
                return "🚨 CABAL RELOADING (EXIT NOW)", f"Price stalled but Top 10% spiked by +{delta_10pct:.2f}%. They are loading the rug.", "red", mc_delta_pct, delta_10pct

            # --- 2. THE GOLDEN DIVERGENCE (Moon Entry) ---
            # Price is breaking out, AND whales are aggressively SELLING (-1.5% or more)
            if is_breaking_out and delta_10pct <= -1.5:
                return "🚀 GOLDEN DIVERGENCE (BUY SIGNAL)", f"MC broke the ceiling (+{mc_delta_pct:.1f}%) while Top 10% dumped {delta_10pct:.2f}%. The gates are open!", "green", mc_delta_pct, delta_10pct
                
            # --- 3. FAKEOUT BREAKOUT ---
            # Price is breaking out, BUT whales are BUYING (Shorting the top)
            if is_breaking_out and delta_10pct > 0.5:
                return "🪤 FAKEOUT BREAKOUT (DO NOT BUY)", f"Price broke out, but insiders BOUGHT (+{delta_10pct:.2f}%). This is a liquidity trap.", "orange", mc_delta_pct, delta_10pct
                
            # --- 4. THE CHOP ZONE (Farming) ---
            # Price and holders are just bouncing around with no clear trend
            if abs(delta_10pct) < 1.0:
                return "⚖️ THE CHOP ZONE (WAIT)", f"Top 10% is flat ({delta_10pct:+.2f}%). Cabal is farming fees. Do not enter.", "gray", mc_delta_pct, delta_10pct
                
            # --- 5. BLEEDING ---
            if mc_delta_pct < -5:
                return "🩸 BLEEDING OUT", f"Price dropping (-{mc_delta_pct:.1f}%). No momentum.", "red", mc_delta_pct, delta_10pct
                
            return "👀 WATCHING", "Conditions shifting. Waiting for a trigger.", "gray", mc_delta_pct, delta_10pct

    # --- UI ---
    st.title("🚀 Tool 10: The Moon Sniffer (Hit & Run)")
    st.markdown("Hunts for the 'Golden Divergence': Market Cap breaks resistance while Whale Supply actively melts.")

    c1, c2 = st.columns([3, 1])
    with c1:
        token = st.text_input("Enter Token Address", key="t10_token")
    with c2:
        refresh_rate = st.slider("Refresh (s)", 2, 60, 5, key="t10_refresh")
        
    is_scanning = st.toggle("🚀 Activate Moon Sniffer", key="t10_active")
    
    if 'moon_engine' not in st.session_state:
        st.session_state.moon_engine = MoonSnifferEngine()
    if 't10_current_token' not in st.session_state:
        st.session_state.t10_current_token = None

    if is_scanning and token:
        if st.session_state.t10_current_token != token:
            st.session_state.moon_engine = MoonSnifferEngine()
            st.session_state.t10_current_token = token
            
        dashboard = st.empty()
        
        while True:
            try:
                dex = get_dex_data(token)
                rug = get_rugcheck_data(token)
                
                if not dex or not rug:
                    dashboard.error("❌ Token not found or API error. Waiting...")
                    time.sleep(refresh_rate)
                    continue
                
                market_cap = float(dex.get('fdv', 0))
                symbol = dex.get('baseToken', {}).get('symbol', 'Unknown')
                top_holders = rug.get('topHolders', [])
                top_1_pct = top_holders[0].get('pct', 0) if top_holders else 0
                top_10_pct = sum(h.get('pct', 0) for h in top_holders[:10])
                current_time = datetime.now().strftime('%H:%M:%S')
                
                st.session_state.moon_engine.add_data_point(current_time, market_cap, top_1_pct, top_10_pct)
                
                # Fetch Logic
                verdict_title, verdict_desc, color, mc_pump, whale_dump = st.session_state.moon_engine.analyze_moon_setup()
                
                # Map colors
                if color == "red": alert_color = "error"
                elif color == "green": alert_color = "success"
                elif color == "warning": alert_color = "warning"
                elif color == "orange": alert_color = "warning"
                else: alert_color = "info"
                
                with dashboard.container():
                    st.subheader(f"Target: {symbol}")
                    
                    st.markdown("### 🔭 Hit & Run Signal")
                    if alert_color == "error": st.error(f"### {verdict_title}\n{verdict_desc}")
                    elif alert_color == "success": st.success(f"### {verdict_title}\n{verdict_desc}")
                    elif alert_color == "warning": st.warning(f"### {verdict_title}\n{verdict_desc}")
                    else: st.info(f"### {verdict_title}\n{verdict_desc}")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Live Market Cap", f"${market_cap:,.0f}", f"{mc_pump:+.2f}% MC Breakout")
                    m2.metric("Top 10% Cabal", f"{top_10_pct:.2f}%", f"{whale_dump:+.2f}% Supply Melt", delta_color="inverse")
                    m3.metric("Top 1% Whale", f"{top_1_pct:.2f}%")
                    
                    st.divider()
                    st.markdown("**How to Trade This:** Wait for the green **🚀 GOLDEN DIVERGENCE**. Enter the trade. The absolute second you see a red **🚨 CABAL RELOADING** warning, sell your entire bag.")
                    st.dataframe(st.session_state.moon_engine.history.tail(5), use_container_width=True)
                    
            except Exception as e:
                dashboard.error(f"Error fetching live data: {e}")
                
            time.sleep(refresh_rate)
                
