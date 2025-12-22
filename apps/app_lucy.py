import streamlit as st
import pandas as pd
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from lucy_scanner_realtime import LucyScannerRealtime
from smart_money_analyzer import SMCAnalyzer
from chart_generator import ChartGenerator

# Page Config
st.set_page_config(page_title="Lucy", page_icon="L", layout="wide")

# Custom CSS for "Toss" style clean look
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif;
    }
    
    /* Remove default streamlit header margin */
    .block-container {
        padding-top: 3rem;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: #4e5968;
        font-size: 16px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        color: #3182f6; /* Toss Blue */
        border-bottom: 2px solid #3182f6;
    }

    /* Input fields */
    div[data-baseweb="input"] > div {
        background-color: #f2f4f6;
        border: none;
        border-radius: 8px;
    }
    
    /* Buttons */
    button[kind="primary"] {
        background-color: #3182f6;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 700;
        color: #191f28;
    }
    [data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #8b95a1;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Scanner
@st.cache_resource
def get_scanner():
    return LucyScannerRealtime()

scanner = get_scanner()

# Header Section
col_logo, col_title = st.columns([1, 8])

# We need the path to the logo. Assuming it's in the artifacts dir or current dir.
# The previous tool saved it to the artifacts dir, but we need to move it or Reference it.
# The user's artifact dir is c:\Users\soet3\.gemini\antigravity\brain\3f197919-2fdd-42ef-979b-7914e3a7cac5
# But the script runs in c:\Users\soet3\OneDrive\Desktop\주식종목찾기
# I will assume the image needs to be copied there or just use a placeholder text if I can't copy it easily yet.
# Actually I can copy/write the image to the working dir. I'll simply look for 'lucy_logo.png' in the current dir.
# The user hasn't asked me to move it yet. I'll rely on the text header for now if image is missing.

logo_path = "lucy_logo.png"
if os.path.exists(logo_path):
    with col_logo:
        st.image(logo_path, width=60)
    with col_title:
        st.title("Lucy")
else:
    st.title("Lucy") # Simple text logo if image missing

# st.markdown("### 한국 주식 시장 스마트 머니 & 변동성 분석 시스템")

# Tabs (Clean names)
tab1, tab2, tab3 = st.tabs(["종목 분석", "스퀴즈 검색", "실시간 순위"])

# --- Tab 1: Single Analysis ---
with tab1:
    st.markdown("#### 종목 정밀 분석")
    st.caption("지지/저항, 오더블록, FVG를 분석합니다.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        target_code = st.text_input("종목 코드", value="005930", placeholder="예: 005930")
        st.write("")
        run_btn = st.button("분석하기", type="primary")

    if run_btn and target_code:
        try:
            with st.spinner("분석 중..."):
                try:
                    name = scanner._get_naver_realtime(target_code)['name'] 
                except:
                    name = "알수없음"
                
                df = scanner._get_historical_data(target_code, days=120)
                
                if df.empty:
                    st.error("데이터 없음")
                else:
                    smc = SMCAnalyzer()
                    sr_levels = smc.get_support_resistance_zones(df)
                    obs = smc.get_order_blocks(df)
                    fvgs = smc.get_fvg(df)
                    
                    analysis_result = {
                        'sr_levels': sr_levels,
                        'obs': obs,
                        'fvgs': fvgs
                    }
                    
                    gen = ChartGenerator()
                    fig = gen.get_fig(df, analysis_result, target_code, name)
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Clean Metric Display
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("지지/저항", f"{len(sr_levels)} 구간")
                    with c2:
                        st.metric("오더블록", f"{len(obs)} 개")
                    with c3:
                        st.metric("FVG GAP", f"{len(fvgs)} 개")
                        
        except Exception as e:
            st.error(f"오류: {e}")

# --- Tab 2: Squeeze Breakout ---
with tab2:
    st.markdown("#### 변동성 돌파 (Squeeze)")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        vol_mult = st.number_input("거래량 배수", min_value=2.0, max_value=20.0, value=5.0, step=0.5)
    with c2:
        cv_thresh = st.number_input("변동성 기준", min_value=1.0, max_value=10.0, value=3.0, step=0.1)
    with c3:
        st.write("")
        st.write("") # spacers
        btn_squeeze = st.button("검색 시작", type="primary")
        
    if btn_squeeze:
        with st.spinner("스캔 중..."):
            results = scanner.scan_squeeze(vol_mult=vol_mult, cv_threshold=cv_thresh)
            
            if not results:
                st.info("검색된 종목이 없습니다.")
            else:
                st.success(f"{len(results)}개 종목 발견")
                
                df_res = pd.DataFrame(results)
                df_display = df_res[['code', 'name', 'price', 'change_pct', 'volume_억', 'volume_x', 'volatility_cv']].copy()
                df_display.columns = ['코드', '종목명', '현재가', '등락률', '거래대금(억)', '거래량배수', '변동성']
                
                st.dataframe(df_display, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 차트 미리보기")
                cols = st.columns(3)
                for i, item in enumerate(results[:3]):
                    with cols[i]:
                        st.markdown(f"**{item['name']}**")
                        try:
                            df_h = scanner._get_historical_data(item['code'], days=100)
                            smc = SMCAnalyzer()
                            res = {'sr_levels': smc.get_support_resistance_zones(df_h), 'obs': smc.get_order_blocks(df_h), 'fvgs': smc.get_fvg(df_h)}
                            fig = ChartGenerator().get_fig(df_h, res, item['code'], item['name'])
                            fig.update_layout(height=300, title=None, margin=dict(l=0,r=0,t=0,b=0))
                            st.plotly_chart(fig, use_container_width=True)
                        except:
                            st.caption("-")

# --- Tab 3: Realtime Scanner ---
with tab3:
    st.markdown("#### 실시간 순위 (Naver)")
    
    c1, c2 = st.columns(2)
    with c1:
        min_change = st.number_input("등락률 (%)", 0.0, 30.0, 5.0)
    with c2:
        min_vol = st.number_input("거래대금 (억)", 0, 1000, 100)
        
    st.write("")
    btn_real = st.button("실시간 조회", type="primary")
    
    if btn_real:
        with st.spinner("조회 중..."):
            res = scanner.scan_realtime(min_change=min_change, min_volume_억=min_vol, min_conditions=1)
            if res:
                df_real = pd.DataFrame(res)
                df_disp = df_real[['code', 'name', 'price', 'change_pct', 'volume_억', 'cond_count']].copy()
                df_disp.columns = ['코드', '종목명', '현재가', '등락률', '거래대금(억)', '기술적조건']
                
                st.dataframe(df_disp, use_container_width=True)
            else:
                st.info("검색 결과가 없습니다.")
