import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import plotly.express as px

# Path Setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from src.lucy_scanner_realtime import LucyScannerRealtime
    from src.smart_money_analyzer import SMCAnalyzer
    from src.chart_generator import ChartGenerator
    from src.database import init_db, add_journal_entry, get_user_journal, update_journal_entry, delete_journal_entry
    from src.auth import login_user, register_user
except ImportError:
    # Fallback if run from root
    from src.lucy_scanner_realtime import LucyScannerRealtime
    from src.smart_money_analyzer import SMCAnalyzer
    from src.chart_generator import ChartGenerator
    from src.database import init_db, add_journal_entry, get_user_journal, update_journal_entry, delete_journal_entry
    from src.auth import login_user, register_user

# --- Page Config ---
st.set_page_config(page_title="Sunny Pro Dashboard", layout="wide", page_icon="💹")

# Initialize DB
init_db()

# --- CSS Styling (Visual Spec Implementation) ---
# Colors from Spec:
# Primary: #FF5A5F (Salmon/Coral)
# Background: #09090b (Deep Zinc)
# Surface: #18181b (Zinc-900)
# Border: #27272a (Zinc-800)
# Text: #e4e4e7 (Zinc-200)

st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* GLOBAL RESET */
    * {
        font-family: 'Inter', 'Pretendard', sans-serif;
        box-sizing: border-box;
    }
    
    /* Backgrounds & Text */
    html, body, .stApp {
        background-color: #09090b !important;
        color: #e4e4e7 !important;
    }
    
    /* Remove default top padding */
    .block-container {
        padding-top: 1.5rem !important; /* Reduced padding */
        padding-bottom: 2rem !important;
    }
    
    /* Global Focus Styling - Red Glow */
    button:focus, button:active, input:focus, textarea:focus {
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(255, 90, 95, 0.3) !important;
        border-color: #FF5A5F !important;
    }
    
    /* --------------------------
       Components
       -------------------------- */
    /* Card Box */
    .card-box {
        background-color: #18181b; 
        border: 1px solid #27272a; 
        border-radius: 12px;       
        padding: 20px;
        margin-bottom: 20px;
    }
    
    /* Inputs */
    div[data-baseweb="input"] {
        border: 1px solid #27272a !important;
        border-radius: 8px !important;
        background-color: #09090b !important;
    }
    div[data-baseweb="input"] > div {
        border: none !important;
        background-color: transparent !important;
    }
    input {
        background-color: transparent !important;
        border: none !important;
        color: #e4e4e7 !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #FF5A5F !important;
    }

    /* Buttons */
    div[data-testid="stButton"] > button {
        background-color: #FF5A5F !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.2s;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #FF787C !important;
        transform: scale(0.99);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        border-bottom: 1px solid #27272a;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        color: #71717a;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #FF5A5F !important;
        border-bottom-color: #FF5A5F !important;
    }

    /* --------------------------
       LOGIN SPECIFIC CSS
       -------------------------- */
    /* Target the Login Form Container */
    [data-testid="stForm"] {
        background-color: #18181b; /* Surface */
        border: 1px solid #27272a;
        border-radius: 16px;
        padding: 30px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.4);
    }
    
    /* Hide the "border" of the container if it adds one (it often does) */
    div[data-testid="stForm"] {
        border: 1px solid #27272a !important;
    }
    
    .login-icon {
        width: 40px; height: 40px;
        background: #27272a;
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 15px auto;
    }
</style>
""", unsafe_allow_html=True)


# --- State ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None
if 'scanner' not in st.session_state:
    try:
        st.session_state['scanner'] = LucyScannerRealtime()
    except Exception as e:
        st.session_state['scanner'] = None
        print(f"Scanner init error: {e}") 


def show_login_page():
    # VERTICAL CENTERING VIA CSS
    st.markdown("""
    <style>
        div.block-container {
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            align-items: center;
            height: 100vh;
            min-height: 800px;
            padding-top: 10vh !important;
        }
        [data-testid="stSidebar"] { display: none; }
        div[data-testid="stVerticalBlock"] {
            width: 100%; max-width: 420px; margin: 0 auto;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Unified Login Card (Form)
    with st.form("login_form"):
        # Header Inside Form
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 25px;">
            <div class="login-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5A5F" stroke-width="2">
                    <path d="M3 12h18M3 6h18M3 18h18"/>
                </svg>
            </div>
            <h2 style="color: white; font-weight: 700; margin: 0 0 5px 0;">Welcome back</h2>
            <p style="color: #71717a; font-size: 13px; margin: 0;">Enter your credentials to access the dashboard.</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["Sign In", "Sign Up"])
        
        with tab_login:
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
            # Inputs
            st.markdown('<label style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px;">Username</label>', unsafe_allow_html=True)
            username = st.text_input("Username", key="login_user", label_visibility="collapsed", placeholder="trader@example.com")
            
            st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
            
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <label style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px;">Password</label>
                <span style="font-size: 11px; color: #FF5A5F; cursor: pointer;">Forgot?</span>
            </div>
            """, unsafe_allow_html=True)
            password = st.text_input("Password", key="login_pass", type="password", label_visibility="collapsed", placeholder="••••••••")
            
            st.markdown('<div style="height: 25px;"></div>', unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            
            if submitted:
                user = login_user(username, password)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user
                    st.rerun()
                else:
                    st.error("Invalid Login Credentials")

        with tab_register:
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
            st.markdown('<label style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px;">New Username</label>', unsafe_allow_html=True)
            new_user = st.text_input("New Username", key="reg_user", label_visibility="collapsed")
            
            st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
            st.markdown('<label style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px;">New Password</label>', unsafe_allow_html=True)
            new_pass = st.text_input("New Password", key="reg_pass", type="password", label_visibility="collapsed")
            
            st.markdown('<div style="height: 25px;"></div>', unsafe_allow_html=True)
            
            reg_submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
            
            if reg_submitted:
                if len(new_pass) < 4:
                    st.error("Password must be at least 4 characters")
                else:
                    success, msg = register_user(new_user, new_pass)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                
    st.markdown('<div style="text-align: center; margin-top: 20px; font-size: 11px; color: #52525b;">© 2025 Sunny Pro Investment.</div>', unsafe_allow_html=True)


# --- DASHBOARD PAGE (Spec Implementation) ---
def show_dashboard():
    # Remove Layout Constraint for Dashboard
    st.markdown("""
    <style>
        div.block-container {
            display: block !important;
            height: auto !important;
        }
        div[data-testid="stVerticalBlock"] {
            width: 100% !important;
            max-width: 100% !important;
        }
    </style>
    """, unsafe_allow_html=True)

    user = st.session_state['user_info']
    
    # 1. Top Header (Simplified per request)
    # Replaced Icon with "Papas" style / Pro Chart Icon (Using simplified SVG)
    # Removed Search Bar & Blocks
    with st.container():
        h_left, h_right = st.columns([1, 1]) # Simplified Split
        
        with h_left:
            pass # Icon removed as per request
            
        with h_right:
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; align-items: center; gap: 12px; height: 100%; margin-top: 15px;">
                 <div style="text-align: right; line-height: 1.2;">
                    <div style="font-size: 13px; font-weight: 600; color: #fff;">{user['username']}</div>
                    <div style="font-size: 11px; color: #71717a;">Pro Plan</div>
                 </div>
                 <div style="width: 36px; height: 36px; border-radius: 10px; background: #27272a; border: 1px solid #333; display: flex; align-items: center; justify-content: center; color: #a1a1aa;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-user"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                 </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.write("") # Minimal Spacer

    # 2. Main Grid: Left (Analysis) vs Spacer (Divider) vs Right (Journal)
    col_left, col_sep, col_right = st.columns([1, 0.05, 1], gap="small")
    
    # === LEFT: Chart Analysis ===
    with col_left:
        # Header (SMC Only)
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
            <div style="color: #FF5A5F; display: flex; align-items: center; justify-content: center;">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-activity"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
            </div>
            <div>
                <h3 style="margin: 0; font-size: 16px; font-weight: 700; color: white; line-height: 1.2;">Chart Analysis</h3>
                <p style="margin: 0; font-size: 11px; color: #71717a; line-height: 1.1;">Smart Money Concepts</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Ticker + Run Button Row
        # "Ticker shortened for 6-digit codes, button placed adjacent"
        c_tick, c_btn, c_spacer = st.columns([1, 0.8, 3], gap="small")
        with c_tick:
            target_code = st.text_input("Ticker Symbol", value="005930", placeholder="005930", label_visibility="collapsed")
        with c_btn:
            # use_container_width=True makes it fill the column width (like the KRX badge did)
            # Custom CSS ensures height match ideally, but standard Streamlit aligns well with collapsed label
            btn_run = st.button("Run", type="primary", use_container_width=False)
            
        st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
        
        # Checkboxes
        cc1, cc2 = st.columns(2)
        with cc1: show_ob = st.checkbox("Order Blocks", True)
        with cc2: show_fvg = st.checkbox("Fair Value Gaps", True)
        
        st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
        
        # Original btn_run removed from here (moved up)

        # Analysis Logic - Run when button clicked
        if btn_run:
            st.session_state['run_dash_main'] = True
            st.session_state['dash_target_main'] = target_code

        if st.session_state.get('run_dash_main'):
            t_code = st.session_state.get('dash_target_main', target_code)
            with st.spinner("Analyzing Market Structure..."):
                try:
                    scanner = st.session_state.get('scanner')
                    if scanner is None:
                        st.error("Scanner not initialized. Please check pykrx installation.")
                        st.stop()
                    df = scanner._get_historical_data(t_code, days=120)
                    if not df.empty:
                        smc = SMCAnalyzer()
                        
                        # Calculate Indicators
                        obs = smc.get_order_blocks(df)
                        fvgs = smc.get_fvg(df)
                        sr = smc.get_support_resistance_zones(df)
                        
                        ar = {
                            'sr_levels': sr,
                            'obs': obs if show_ob else [],
                            'fvgs': fvgs if show_fvg else []
                        }
                        
                        # Chart
                        gen = ChartGenerator()
                        fig = gen.get_fig(df, ar, t_code, t_code)
                        fig.update_layout(
                            paper_bgcolor='#18181b', plot_bgcolor='#18181b', 
                            font=dict(color='#a1a1aa'), margin=dict(l=10,r=10,t=30,b=20),
                            height=600
                        )
                        fig.update_xaxes(gridcolor='#27272a')
                        fig.update_yaxes(gridcolor='#27272a')
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # --- Price List (Memo Pad Restoration) ---
                        st.markdown('<div style="border-top: 1px solid #27272a; margin: 20px 0;"></div>', unsafe_allow_html=True)
                        st.markdown("""
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                            <div style="color: #71717a; display: flex; align-items: center;">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-layers"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"></path><path d="m2.2 12.91 8.95 4.07a2 2 0 0 0 1.7 0l8.95-4.07"></path><path d="m2.2 17.91 8.95 4.07a2 2 0 0 0 1.7 0l8.95-4.07"></path></svg>
                            </div>
                            <h4 style="font-size: 14px; color: white; margin: 0; line-height: 1;">Key Levels (Entry & Stop)</h4>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Filters
                        f1, f2 = st.columns([2, 1])
                        with f1:
                            filter_pos = st.radio("Side", ["All", "Long", "Short"], horizontal=True, label_visibility="collapsed")
                        with f2:
                            pass # Spacer
                            
                        # Build Data
                        rows = []
                        # OBs
                        for ob in obs:
                            is_bullish = "Bullish" in ob['type']
                            if filter_pos == "Long" and not is_bullish: continue
                            if filter_pos == "Short" and is_bullish: continue
                            
                            # Determine Entry & Stop based on OB type
                            if is_bullish:
                                # Long: Entry near Top, Stop near Bottom
                                entry_p = ob['top']
                                stop_p = ob['bottom']
                                type_label = "매수 (Long)"
                            else:
                                # Short: Entry near Bottom, Stop near Top
                                entry_p = ob['bottom']
                                stop_p = ob['top']
                                type_label = "매도 (Short)"
                            
                            rows.append({
                                "구분": type_label,
                                "진입가": int(entry_p),
                                "손절가": int(stop_p),
                                "상태": "대기" if not ob['mitigated'] else "완료"
                            })
                        
                        if rows:
                            # Use dedent or start from left to avoid markdown code block triggers
                            table_html = '<style>'
                            table_html += '.custom-table { width: 100%; border-collapse: collapse; font-size: 13px; color: #e4e4e7; background: #18181b; border-radius: 8px; overflow: hidden; margin-top: 10px; }'
                            table_html += '.custom-table th { background: #27272a; color: #a1a1aa; font-weight: 600; padding: 10px; text-align: center; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }'
                            table_html += '.custom-table td { padding: 12px 10px; text-align: center; border-bottom: 1px solid #27272a; }'
                            table_html += '.custom-table tr:last-child td { border-bottom: none; }'
                            table_html += '</style>'
                            table_html += '<table class="custom-table">'
                            table_html += '<thead><tr><th>구분</th><th>진입가</th><th>손절가</th><th>상태</th></tr></thead>'
                            table_html += '<tbody>'
                            
                            for r in rows:
                                badge_bg = '#14532d' if r['상태'] == '완료' else '#27272a'
                                badge_fg = '#4ade80' if r['상태'] == '완료' else '#a1a1aa'
                                table_html += '<tr>'
                                table_html += '<td>' + str(r['구분']) + '</td>'
                                table_html += '<td style="font-weight: 600; color: white;">' + format(r['진입가'], ',') + '</td>'
                                table_html += '<td style="color: #FF5A5F;">' + format(r['손절가'], ',') + '</td>'
                                table_html += '<td><span style="background: ' + badge_bg + '; color: ' + badge_fg + '; padding: 2px 8px; border-radius: 4px; font-size: 11px;">' + str(r['상태']) + '</span></td>'
                                table_html += '</tr>'
                            
                            table_html += '</tbody></table>'
                            st.markdown(table_html, unsafe_allow_html=True)
                        else:
                            st.info("No active levels found.")
                        
                    else:
                        st.error("No Data Found")
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
        else:
             st.markdown("""
             <div style="height: 400px; background: #09090b; border: 1px dashed #27272a; border-radius: 12px; display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 20px;">
                <div style="margin-bottom: 15px; color: #27272a;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trending-up"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline><polyline points="16 7 22 7 22 13"></polyline></svg>
                </div>
                <div style="font-size: 13px; font-weight: 500; color: #52525b;">Run analysis to see chart</div>
             </div>
             """, unsafe_allow_html=True)


    # === MIDDLE: Divider ===
    with col_sep:
        st.markdown("""
        <div style="height: 100vh; border-right: 1px solid #27272a; margin-left: 50%;"></div>
        """, unsafe_allow_html=True)
    # === RIGHT: Trading Journal ===
    with col_right:
        # Inline CSS for Journal Section (Transparent Trash Button & Tab Polish)
        st.markdown("""
        <style>
        /* Target buttons inside expader or specific containers for transparent look */
        div[data-testid="stExpander"] button {
            background-color: transparent !important; 
            border: 1px solid #3f3f46 !important;
            color: #ef4444 !important;
        }
        div[data-testid="stExpander"] button:hover {
            border-color: #ef4444 !important;
            background-color: #27272a !important;
        }
        /* Remove vertical borders from tabs */
        div[data-testid="stTabs"] {
            border: none !important;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 10px;
            border-bottom: 1px solid #27272a !important;
        }
        div[data-testid="stTabs"] [data-baseweb="tab"] {
            border: none !important;
            background-color: transparent !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Spacer to push separate Journal section down to align with 'Run' button area
        st.markdown('<div style="height: 48px;"></div>', unsafe_allow_html=True)
        
        # Tabs at the top (No bounding box wrapping the tabs themselves)
        tab1, tab2 = st.tabs(["New Entry", "Recent Entries"])
        
        # --- TAB 1: New Entry Form ---
        with tab1:
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
            with st.form("journal_spec_form", border=False):
                # Row 1: Date, Symbol, Side
                # Use [1, 1, 1, 0.3] to make inputs slightly shorter width-wise (spacer at end)
                c1, c2, c3, _ = st.columns([1, 1, 1, 0.3])
                with c1:
                    st.markdown('<div style="font-size: 10px; font-weight: 600; color: #71717a; margin-bottom: 4px;">날짜</div>', unsafe_allow_html=True)
                    date = st.date_input("Date", datetime.now(), label_visibility="collapsed")
                with c2:
                    st.markdown('<div style="font-size: 10px; font-weight: 600; color: #71717a; margin-bottom: 4px;">종목코드</div>', unsafe_allow_html=True)
                    symbol = st.text_input("Symbol", placeholder="005930", label_visibility="collapsed")
                with c3:
                    st.markdown('<div style="font-size: 10px; font-weight: 600; color: #71717a; margin-bottom: 4px;">포지션</div>', unsafe_allow_html=True)
                    side = st.selectbox("Side", ["LONG (매수)", "SHORT (매도)"], label_visibility="collapsed")
                
                st.write("")
                
                # Row 2: Entry, Exit, Qty, Fees
                r2c1, r2c2, r2c3, r2c4, _ = st.columns([1, 1, 1, 1, 0.3])
                with r2c1:
                    st.markdown('<div style="font-size: 10px; font-weight: 600; color: #71717a; margin-bottom: 4px;">진입가</div>', unsafe_allow_html=True)
                    entry = st.number_input("Entry", min_value=0, step=100, format="%d", label_visibility="collapsed")
                with r2c2:
                    st.markdown('<div style="font-size: 10px; font-weight: 600; color: #71717a; margin-bottom: 4px;">청산가</div>', unsafe_allow_html=True)
                    exit_p = st.number_input("Exit", min_value=0, step=100, format="%d", label_visibility="collapsed")
                with r2c3:
                    st.markdown('<div style="font-size: 10px; font-weight: 600; color: #71717a; margin-bottom: 4px;">수량</div>', unsafe_allow_html=True)
                    qty = st.number_input("Qty", min_value=1, format="%d", label_visibility="collapsed")
                with r2c4:
                    st.markdown('<div style="font-size: 10px; font-weight: 600; color: #71717a; margin-bottom: 4px;">수수료</div>', unsafe_allow_html=True)
                    fees = st.number_input("Fees", min_value=0, step=10, format="%d", label_visibility="collapsed")
                
                st.write("")
                
                st.markdown('<div style="font-size: 10px; font-weight: 600; color: #71717a; margin-bottom: 4px;">전략 / 셋업</div>', unsafe_allow_html=True)
                strategy = st.selectbox("Strategy", [
                    "세력 매집 (Accumulation)",
                    "변동성 돌파 (Squeeze)",
                    "눌림목 (Pullback)",
                    "수급 주도주 (Leader)",
                    "뉴스/테마 (News)",
                    "뇌동매매 (Impulsive)"
                ], label_visibility="collapsed")
                
                st.write("")
                
                st.markdown('<div style="font-size: 10px; font-weight: 600; color: #71717a; margin-bottom: 4px;">진입 사유 / 메모</div>', unsafe_allow_html=True)
                reason = st.text_area("Notes", height=100, placeholder="왜 이 종목을 샀나요?", label_visibility="collapsed")
                
                st.write("")
                
                st.markdown("""
                <div style="border: 2px dashed #27272a; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 20px; background: #09090b;">
                    <div style="font-size: 24px; color: #3f3f46; margin-bottom: 5px;">☁️</div>
                    <div style="font-size: 12px; font-weight: 500; color: #e4e4e7;">Click to upload image</div>
                    <div style="font-size: 10px; color: #71717a;">Supports PNG, JPG</div>
                </div>
                """, unsafe_allow_html=True)
                img_file = st.file_uploader("Image", type=['png','jpg'], label_visibility="collapsed")
                
                st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
                
                submit = st.form_submit_button("Save Entry", type="primary")
                
                if submit:
                    # Gross PnL
                    gross_pnl = (exit_p - entry) * qty if side == "LONG" else (entry - exit_p) * qty
                    # Net PnL (including fees)
                    pnl = gross_pnl - fees
                    roi = (pnl / (entry * qty))*100 if entry > 0 else 0
                    
                    img_path = None
                    if img_file:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        fname = f"{user['id']}_{ts}.png"
                        img_path = fname
                    
                    data = {
                        'date': date.strftime("%Y-%m-%d"),
                        'code': symbol, 'name': symbol, 'side': side,
                        'entry_price': entry, 'exit_price': exit_p, 'qty': qty,
                        'pnl': pnl, 'roi': roi, 'strategy': strategy,
                        'reason': reason, 'mistake': "", 'review': "",
                        'image_path': img_path
                    }
                    add_journal_entry(user['id'], data)
                    st.success(f"Saved (ROI: {roi:.2f}%)")
                    st.rerun()

        # --- TAB 2: Recent Entries (Expandable List with Pagination) ---
        with tab2:
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
            
            entries_df = get_user_journal(user['id'])
            
            if not entries_df.empty:
                # 1. Pagination Logic (Newest First)
                items_per_page = 5
                total_items = len(entries_df)
                total_pages = (total_items - 1) // items_per_page + 1
                
                if 'journal_page' not in st.session_state:
                    st.session_state['journal_page'] = 1
                
                # Ensure page stays within [1, total_pages]
                st.session_state['journal_page'] = max(1, min(st.session_state.get('journal_page', 1), total_pages))
                    
                # entries_df is already ORDER BY date DESC (Newest First)
                start_idx = (st.session_state['journal_page'] - 1) * items_per_page
                end_idx = start_idx + items_per_page
                page_items = entries_df.iloc[start_idx:end_idx]
                
                # Scrollable Container
                with st.container(height=500):
                    for i, ent in page_items.iterrows():
                        pnl_val = ent['pnl']
                        roi_val = ent['roi']
                        pnl_color = "red" if pnl_val < 0 else "green"
                        pnl_icon = "🔻" if pnl_val < 0 else "🔺"
                        label = f"{ent['date']} | {ent['code']} | {ent['side']} | :{pnl_color}[{pnl_icon} {pnl_val:,.0f} KRW ({roi_val:.2f}%)]"
                        
                        with st.expander(label):
                            st.markdown(f"""
                            <div style="padding: 10px; background: #18181b; border-radius: 8px; margin-bottom: 10px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                    <span style="color: #a1a1aa; font-size: 12px;">Date: <span style="color: white;">{ent['date']}</span></span>
                                    <span style="color: #a1a1aa; font-size: 12px;">Qty: <span style="color: white;">{ent['qty']:,.0f}</span></span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                    <span style="color: #a1a1aa; font-size: 12px;">Entry: <span style="color: white;">{ent['entry_price']:,.0f}</span></span>
                                    <span style="color: #a1a1aa; font-size: 12px;">Exit: <span style="color: white;">{ent['exit_price']:,.0f}</span></span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                    <span style="color: #a1a1aa; font-size: 12px;">Fees: <span style="color: white;">{ent.get('fees', 0):,.0f}</span></span>
                                    <span style="color: #a1a1aa; font-size: 12px;">ROI: <span style="color: #2dd4bf;">{ent['roi']:.2f}%</span></span>
                                </div>
                                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #27272a;">
                                    <div style="color: #71717a; font-size: 11px; font-weight: 600; text-transform: uppercase;">Notes</div>
                                    <div style="color: #e4e4e7; font-size: 13px; margin-top: 4px; line-height: 1.4;">{ent['reason'] or 'No notes.'}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            btn_col1, btn_col2 = st.columns([8, 3.5], gap="small")
                            with btn_col2:
                                sub_col1, sub_col2 = st.columns(2, gap="small")
                                with sub_col1:
                                    ent_csv = pd.DataFrame([ent]).to_csv(index=False).encode('utf-8-sig')
                                    st.download_button(label="CSV", data=ent_csv, file_name=f"trade_{ent['date']}_{ent['code']}.csv", mime='text/csv', key=f"dl_{ent['id']}", use_container_width=True)
                                with sub_col2:
                                    if st.button("Delete", key=f"del_{ent['id']}", type="secondary", use_container_width=True):
                                        delete_journal_entry(ent['id'], user['id'])
                                        st.rerun()
                
                # 3. Compact & Aligned Pagination Bar (< 1 >)
                st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)
                
                # CSS for a unified bar look - FORCE WHITE AND BACKGROUND MATCH
                st.markdown("""
                <style>
                    /* Target by keys and force background and text color */
                    .st-key-prev_pg, .st-key-next_pg {
                        display: flex !important;
                        justify-content: center !important;
                    }
                    .st-key-prev_pg button, .st-key-next_pg button {
                        background-color: transparent !important;
                        background: transparent !important;
                        border: 1px solid #27272a !important;
                        color: transparent !important; /* Hide original character */
                        width: 32px !important;
                        height: 32px !important;
                        min-width: 32px !important;
                        padding: 0 !important;
                        display: flex !important;
                        align-items: center !important;
                        justify-content: center !important;
                        border-radius: 6px !important;
                        box-shadow: none !important;
                        position: relative !important;
                    }
                    /* Force the arrow using pseudo-elements for absolute control */
                    .st-key-prev_pg button::after, .st-key-next_pg button::after {
                        color: white !important;
                        font-weight: 800 !important;
                        font-size: 20px !important;
                        line-height: 1 !important;
                        position: absolute !important;
                        top: 50% !important;
                        left: 50% !important;
                        transform: translate(-50%, -50%) !important;
                        pointer-events: none;
                    }
                    .st-key-prev_pg button::after { content: "‹" !important; }
                    .st-key-next_pg button::after { content: "›" !important; }

                    .st-key-prev_pg button:hover, .st-key-next_pg button:hover:not(:disabled) {
                        border-color: #71717a !important;
                        background-color: #18181b !important;
                    }
                    .st-key-prev_pg button:disabled, .st-key-next_pg button:disabled {
                        opacity: 0.1 !important;
                        border-color: #18181b !important;
                        cursor: not-allowed !important;
                    }
                    /* Hide Streamlit default label */
                    .st-key-prev_pg button p, .st-key-next_pg button p {
                        display: none !important;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                # Five columns to center a small 3-column block
                _, p1, p2, p3, _ = st.columns([5, 0.4, 0.6, 0.4, 5], gap="small")
                
                with p1:
                    if st.button("<", key="prev_pg", disabled=(st.session_state['journal_page'] == 1)):
                        st.session_state['journal_page'] -= 1
                        st.rerun()
                with p2:
                    st.markdown(f"""
                    <div style="display: flex; justify-content: center; align-items: center; height: 32px; color: white; font-size: 15px; font-weight: 700;">
                        {st.session_state['journal_page']}
                    </div>
                    """, unsafe_allow_html=True)
                with p3:
                    if st.button(">", key="next_pg", disabled=(st.session_state['journal_page'] == total_pages)):
                        st.session_state['journal_page'] += 1
                        st.rerun()
            else:
                st.info("No journal entries yet. Add your first trade!")
                
        st.markdown('</div>', unsafe_allow_html=True)


# --- Dispatcher ---
if not st.session_state['logged_in']:
    show_login_page()
else:
    with st.sidebar:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
            <div style="color: #FFD700; display: flex; align-items: center;">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-crown"><path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7Z"></path><path d="M12 17H12.01"></path></svg>
            </div>
            <span style="font-size: 16px; font-weight: 700; color: white;">{st.session_state['user_info']['username']}</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Pro Plan")
        
        # Spacer to push logout to bottom
        st.markdown('<div style="margin-top: calc(100vh - 250px);"></div>', unsafe_allow_html=True)
        
        if st.button("Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()
            
    show_dashboard()
