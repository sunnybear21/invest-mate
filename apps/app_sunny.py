import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from lucy_scanner_realtime import LucyScannerRealtime
from smart_money_analyzer import SMCAnalyzer
from chart_generator import ChartGenerator

# Page Config
st.set_page_config(page_title="Sunny Pro", page_icon="☀️", layout="wide")

# Custom CSS for "Sunny Dark Pro" Theme
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
        background-color: #121212; /* Deep Black/Gray */
        color: #e0e0e0;
    }
    
    /* Main App Background */
    .stApp {
        background-color: #121212;
    }
    
    /* Header Styling */
    .header-container {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 30px;
        padding-top: 10px;
    }
    
    /* Sunny Icon (Orange SVG) */
    .sunny-icon {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .sunny-title {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(90deg, #FF8C00, #FFD700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    
    /* Tab Styling - Orange Accent */
    .stTabs [data-baseweb="tab-list"] {
        gap: 25px;
        border-bottom: 1px solid #333;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        font-size: 16px;
        font-weight: 500;
        color: #888;
        background-color: transparent;
        border: none;
        padding-bottom: 0px;
    }
    .stTabs [aria-selected="true"] {
        color: #FF8C00; /* Sunny Orange */
        font-weight: 700;
        border-bottom: 2px solid #FF8C00;
    }
    
    /* Force White Text for Everything in Dark Mode */
    h1, h2, h3, h4, h5, h6, .css-10trblm, p, div, span {
        color: #ffffff !important;
    }
    
    /* Specific overrides for Streamlit elements */
    [data-baseweb="checkbox"] span {
        color: #ffffff !important;
    }
    label {
        color: #ffffff !important;
    }
    
    /* Input Fields (Keep input text white, but background dark) */
    div[data-baseweb="input"] > div {
        background-color: #1e1e1e;
        border: 1px solid #333;
        color: white;
        border-radius: 6px;
    }
    div[data-baseweb="input"] > div:focus-within {
        border-color: #FF8C00;
    }
    input {
        color: white !important;
    }
    
    /* Caption text (slightly dimmer but still readable) */
    .caption-text {
        color: #cccccc !important;
        font-size: 14px;
        margin-top: -10px;
        margin-bottom: 20px;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    [data-testid="stMetricLabel"] {
        color: #bbbbbb !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Scanner
@st.cache_resource
def get_scanner():
    return LucyScannerRealtime()

scanner = get_scanner()

# Sunny Logo SVG (Abstract Sun)
sunny_svg = """
<svg width="36" height="36" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M12 17C14.7614 17 17 14.7614 17 12C17 9.23858 14.7614 7 12 7C9.23858 7 7 9.23858 7 12C7 14.7614 9.23858 17 12 17Z" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M12 1V3" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M12 21V23" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M4.22 4.22L5.64 5.64" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M18.36 18.36L19.78 19.78" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M1 12H3" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M21 12H23" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M4.22 19.78L5.64 18.36" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M18.36 5.64L19.78 4.22" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

st.markdown(f"""
<div class="header-container">
    <div class="sunny-icon">{sunny_svg}</div>
    <div class="sunny-title">Sunny Pro</div>
</div>
""", unsafe_allow_html=True)

# Clean Tabs (No Emojis)
tab1, tab2, tab3 = st.tabs(["종목 분석", "변동성 분석", "실시간 랭킹"])

# --- Tab 1: Analysis ---
with tab1:
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.markdown("### 종목 정밀 분석")
        st.markdown('<p class="caption-text">SMC 기반 지지/저항 및 오더블록 분석</p>', unsafe_allow_html=True)
        
        target_code = st.text_input("종목코드", value="005930", placeholder="예: 005930", label_visibility="collapsed")
        st.write("")
        run_btn = st.button("분석 실행", type="primary")
        
        if run_btn and target_code:
            st.session_state['run_analysis'] = True
            st.session_state['target_code'] = target_code
        
        st.write("")
        c_chk1, c_chk2, c_chk3 = st.columns(3)
        with c_chk1:
            show_ob = st.checkbox("오더블록", value=True)
        with c_chk2:
            show_fvg = st.checkbox("FVG", value=True)
        with c_chk3:
            show_fib = st.checkbox("피보나치", value=True)

        # 피보나치 설명 (체크 시 표시)
        if show_fib:
            with st.expander("📐 피보나치 되돌림 가이드", expanded=False):
                st.markdown("""
**피보나치 되돌림이란?**
- 주가가 상승/하락 후 **얼마나 되돌아갈지** 예측하는 기술적 지표
- 최근 60일간 스윙 고점/저점 기준으로 계산

**핵심 레벨 해석:**
| 레벨 | 의미 | 매매 전략 |
|------|------|-----------|
| **38.2%** | 약한 되돌림 | 강한 추세에서 첫 지지/저항 |
| **50%** | 중간 되돌림 | 심리적 중요 구간 |
| **61.8%** | 황금비율 ⭐ | 가장 중요한 지지/저항 |
| **78.6%** | 깊은 되돌림 | 추세 전환 경계선 |

**매매 활용법:**
1. 🟢 **매수**: 상승 추세에서 61.8% 지지 확인 후 진입
2. 🔴 **매도**: 하락 추세에서 38.2~50% 저항 확인 후 청산
3. ⚠️ **주의**: 78.6% 이탈 시 추세 전환 가능성
                """)

        st.markdown("---")
        st.info("차트 확대를 통해 세부 구간을 확인하세요.")

    with col_right:
        if st.session_state.get('run_analysis'):
            t_code = st.session_state['target_code']
            try:
                with st.spinner("Analyzing..."):
                    try:
                        name = scanner._get_naver_realtime(t_code)['name'] 
                    except:
                        name = "알수없음"
                    
                    df = scanner._get_historical_data(t_code, days=120)
                    
                    if df.empty:
                        st.error("데이터 없음")
                    else:
                        smc = SMCAnalyzer()
                        sr_levels = smc.get_support_resistance_zones(df)
                        obs = smc.get_order_blocks(df)
                        fvgs = smc.get_fvg(df)
                        
                        analysis_result = {
                            'sr_levels': sr_levels,
                            'obs': obs if show_ob else [],
                            'fvgs': fvgs if show_fvg else [],
                            'show_fibonacci': show_fib
                        }

                        gen = ChartGenerator()
                        fig = gen.get_fig(df, analysis_result, t_code, name)
                        
                        # Dark Theme Chart
                        fig.update_layout(
                            paper_bgcolor='#121212',
                            plot_bgcolor='#121212',
                            font=dict(color='#e0e0e0'),
                            margin=dict(l=20, r=20, t=30, b=20)
                        )
                        fig.update_xaxes(gridcolor='#333')
                        fig.update_yaxes(gridcolor='#333')
                        
                        st.plotly_chart(fig)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("지지/저항", len(sr_levels))
                        c2.metric("오더블록", len(obs))
                        c3.metric("FVG", len(fvgs))
                        
                        # --- Price Level Summary (Memo Pad) ---
                        st.markdown("### 📝 주요 구간 가격표 (Memo)")
                        
                        col_f1, col_f2 = st.columns([2, 1])
                        with col_f1:
                            filter_type = st.radio("포지션 필터", ["전체", "매수", "매도"], horizontal=True, label_visibility="collapsed")
                        with col_f2:
                            show_mitigated_memo = st.checkbox("해소된 구간 포함", value=False)

                        # Prepare data for display
                        memo_data = []

                        # Helper for filtering
                        def should_include(item_type, is_mitigated):
                            # 1. Mitigated Filter
                            if is_mitigated and not show_mitigated_memo:
                                return False
                            # 2. Position Filter
                            is_bullish = "Bullish" in item_type
                            if filter_type == "매수" and not is_bullish: return False
                            if filter_type == "매도" and is_bullish: return False
                            return True

                        # OB Data
                        for ob in obs:
                            if should_include(ob['type'], ob['mitigated']):
                                t = "매수 OB" if "Bullish" in ob['type'] else "매도 OB"
                                status = "✅ 활성" if not ob['mitigated'] else "❌ 해소됨"
                                memo_data.append({
                                    "구분": t,
                                    "상태": status,
                                    "상단가격": f"{int(ob['top']):,}",
                                    "하단가격": f"{int(ob['bottom']):,}",
                                    "생성일": ob['date'].strftime('%Y-%m-%d') if hasattr(ob['date'], 'strftime') else str(ob['date'])[:10]
                                })
                                
                        # FVG Data
                        for fvg in fvgs:
                             if should_include(fvg['type'], fvg['mitigated']):
                                t = "매수 FVG" if "Bullish" in fvg['type'] else "매도 FVG"
                                status = "✅ 활성" if not fvg['mitigated'] else "❌ 해소됨"
                                memo_data.append({
                                    "구분": t,
                                    "상태": status,
                                    "상단가격": f"{int(fvg['top']):,}",
                                    "하단가격": f"{int(fvg['bottom']):,}",
                                    "생성일": fvg['date'].strftime('%Y-%m-%d') if hasattr(fvg['date'], 'strftime') else str(fvg['date'])[:10]
                                })
                        
                        if memo_data:
                            df_memo = pd.DataFrame(memo_data)
                            # Sort by Date descending
                            df_memo = df_memo.sort_values(by="생성일", ascending=False)
                            st.dataframe(df_memo, hide_index=True, width="stretch")
                        else:
                            st.info("조건에 맞는 구간이 없습니다.")
                        
            except Exception as e:
                st.error(f"Error: {e}")
        else:
             st.markdown("""
            <div style="height: 400px; display: flex; align-items: center; justify-content: center; border: 1px dashed #333; border-radius: 8px; color: #555;">
                분석 대기 중
            </div>
            """, unsafe_allow_html=True)

# --- Tab 2: Squeeze ---
with tab2:
    st.markdown("### 변동성 돌파 (Squeeze)")
    st.markdown('<p class="caption-text">거래량 급증 & 변동성 축소 종목 발굴</p>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 1, 1], vertical_alignment="bottom")
    with c1:
        vol_mult = st.number_input("거래량(배)", 2.0, 20.0, 5.0, 0.5)
    with c2:
        cv_thresh = st.number_input("변동성(%)", 1.0, 10.0, 3.0, 0.1)
    with c3:
        btn_squeeze = st.button("종목 스캔", type="primary")
        
    if btn_squeeze:
        with st.spinner("Processing..."):
            results = scanner.scan_squeeze(vol_mult=vol_mult, cv_threshold=cv_thresh)
            if results:
                st.success(f"{len(results)}건 발견")
                df_res = pd.DataFrame(results)
                df_display = df_res[['code', 'name', 'price', 'change_pct', 'volume_억', 'volume_x', 'volatility_cv']].copy()
                df_display.columns = ['코드', '종목명', '현재가', '등락률', '거래대금(억)', '거래량배수', '변동성']
                st.dataframe(df_display, hide_index=True)
            else:
                st.warning("조건에 맞는 종목이 없습니다.")

# --- Tab 3: Realtime ---
with tab3:
    st.markdown("### 실시간 주도주")
    st.markdown('<p class="caption-text">실시간 거래대금/등락률 상위 종목</p>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 1, 1], vertical_alignment="bottom")
    with c1:
        min_change = st.number_input("등락률(%)", 0.0, 30.0, 5.0)
    with c2:
        min_vol = st.number_input("거래대금(억)", 0, 1000, 100)
    with c3:
        btn_real = st.button("랭킹 조회", type="primary")
    
    if btn_real:
        with st.spinner("Fetching..."):
            res = scanner.scan_realtime(min_change=min_change, min_volume_억=min_vol, min_conditions=1)
            if res:
                df_real = pd.DataFrame(res)
                df_disp = df_real[['code', 'name', 'price', 'change_pct', 'volume_억', 'cond_count']].copy()
                df_disp.columns = ['코드', '종목명', '현재가', '등락률', '거래대금(억)', '기술적조건']
                st.dataframe(df_disp, hide_index=True)
            else:
                st.info("No data")
