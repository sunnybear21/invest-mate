import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# Page Config
st.set_page_config(page_title="Trading Journal", page_icon="⚡", layout="wide")

# Custom CSS (Dark Theme + Shadcn Style)
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
        background-color: #09090b !important; /* Shadcn Zinc-950 */
        color: #fafafa !important; /* Zinc-50 */
    }
    .stApp { background-color: #09090b !important; }
    
    /* Force White Text on Inputs */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
        background-color: #18181b !important; /* Zinc-900 */
        border: 1px solid #27272a !important; /* Zinc-800 */
        color: #fafafa !important;
        border-radius: 6px !important;
    }
    input, textarea, select {
        color: #fafafa !important;
        caret-color: #fafafa;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #fafafa !important;
    }
    [data-testid="stMetricLabel"] {
        color: #a1a1aa !important; /* Zinc-400 */
    }
    
    /* Tabs - Minimal Shadcn Style */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #27272a;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre-wrap;
        border-radius: 6px;
        color: #a1a1aa; /* Zinc-400 */
        font-weight: 500;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #27272a; /* Zinc-800 */
        color: #fafafa;
        border: none;
    }
    
    /* Buttons */
    button[kind="primary"] {
        background-color: #fafafa !important;
        color: #09090b !important;
        border: 1px solid #fafafa !important;
        font-weight: 600;
        border-radius: 6px;
    }
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #fafafa !important;
        border: 1px solid #27272a !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, strong { color: #fafafa !important; }
    p, span { color: #d4d4d8; } /* Zinc-300 */
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #18181b !important;
        color: #fafafa !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper for Icons (Lucide Style SVGs)
def icon(name):
    # Minimal SVGs
    icons = {
        "book": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
        "chart": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
        "list": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>'
    }
    return icons.get(name, "")

# Data File
JOURNAL_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "trading_journal.csv")
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "journal_images")

if not os.path.exists(os.path.dirname(JOURNAL_FILE)):
    os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR, exist_ok=True)

# Load Data
def load_data():
    if not os.path.exists(JOURNAL_FILE):
        return pd.DataFrame(columns=[
            "날짜", "종목코드", "종목명", "포지션", "진입가", "청산가",
            "수량", "손익", "수익률(%)", "전략", "진입사유", "실수", "복기", "이미지"
        ])
    try:
        df = pd.read_csv(JOURNAL_FILE)
        # Handle both old English and new Korean column names
        if 'Date' in df.columns:
            df['날짜'] = pd.to_datetime(df['Date']).dt.date
            df = df.drop(columns=['Date'])
        elif '날짜' in df.columns:
            df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        # Rename old English columns to Korean if they exist
        rename_map = {
            'Code': '종목코드', 'Name': '종목명', 'Side': '포지션',
            'EntryPrice': '진입가', 'ExitPrice': '청산가', 'Quantity': '수량',
            'PnL': '손익', 'Return(%)': '수익률(%)', 'Strategy': '전략',
            'Reason': '진입사유', 'Mistake': '실수', 'Review': '복기', 'Image': '이미지'
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        # Ensure 이미지 column exists (for backward compatibility)
        if '이미지' not in df.columns:
            df['이미지'] = None
        return df
    except:
        return pd.DataFrame()

# Save Data
def save_data(df):
    df.to_csv(JOURNAL_FILE, index=False)

# Main Title
st.title("Trading Journal")
st.caption("Dominating the market with disciplined execution.")

# Tabs (No Emojis, Minimal)
tab_entry, tab_dashboard, tab_history = st.tabs(["Journal Entry", "Analytics", "History"])

# --- Tab 1: Entry ---
with tab_entry:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("새로운 매매 기록")
        with st.form("trade_form"):
            t_date = st.date_input("매매 일자", datetime.now())
            c1, c2 = st.columns(2)
            t_code = c1.text_input("종목 코드", placeholder="005930")
            t_name = c2.text_input("종목명", placeholder="삼성전자")
            
            t_side = st.selectbox("포지션", ["Long (매수)", "Short (매도)"])
            
            c3, c4, c5 = st.columns(3)
            t_entry = c3.number_input("진입가", min_value=0, value=0)
            t_exit = c4.number_input("청산가", min_value=0, value=0)
            t_qty = c5.number_input("수량", min_value=1, value=1)
            
            t_strategy = st.selectbox("진입 전략 (패턴)", [
                "세력 매집 (Accumulation)",
                "변동성 돌파 (Squeeze)",
                "눌림목 (Pullback)",
                "수급 주도주 (Leader)",
                "뉴스/테마 (News)",
                "뇌동매매 (Impulsive)"
            ])
            
            t_reason = st.text_area("진입 사유", placeholder="왜 이 종목을 샀나요?")
            t_mistake = st.text_input("실수 / 배울점", placeholder="예: 손절을 너무 늦게 함, 욕심 부림")
            
            # Image Upload
            t_image = st.file_uploader("차트 이미지 (선택)", type=['png', 'jpg', 'jpeg'])
            
            submitted = st.form_submit_button("저장하기", type="primary")
            
            if submitted:
                if t_entry > 0 and t_exit > 0:
                    pnl = (t_exit - t_entry) * t_qty
                    if "Short" in t_side:
                         pnl = (t_entry - t_exit) * t_qty
                         
                    ret_pct = (pnl / (t_entry * t_qty)) * 100
                    
                    # Save Image if uploaded
                    image_filename = None
                    if t_image is not None:
                        try:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            ext = t_image.name.split('.')[-1]
                            image_filename = f"{timestamp}_{t_code}.{ext}"
                            save_path = os.path.join(IMAGES_DIR, image_filename)
                            with open(save_path, "wb") as f:
                                f.write(t_image.getbuffer())
                        except Exception as e:
                            st.error(f"이미지 저장 실패: {e}")

                    new_data = {
                        "날짜": t_date, "종목코드": t_code, "종목명": t_name, "포지션": t_side,
                        "진입가": t_entry, "청산가": t_exit, "수량": t_qty,
                        "손익": pnl, "수익률(%)": round(ret_pct, 2),
                        "전략": t_strategy, "진입사유": t_reason, "실수": t_mistake,
                        "복기": "", "이미지": image_filename
                    }
                    
                    df = load_data()
                    df = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
                    save_data(df)
                    st.success("매매 기록이 저장되었습니다!")
                else:
                    st.error("가격을 정확히 입력해주세요.")

    with col2:
        st.subheader("최근 매매")
        df = load_data()
        if not df.empty:
            # Display Recent Trades with Image Check
            for i, row in df.head(3).iterrows():
                with st.expander(f"{row['날짜']} {row['종목명']} ({row['수익률(%)']}%)"):
                    c_a, c_b = st.columns([2, 1])
                    with c_a:
                        st.write(f"**전략**: {row['전략']}")
                        st.write(f"**진입사유**: {row['진입사유']}")
                        if row['실수']:
                            st.error(f"실수: {row['실수']}")
                    with c_b:
                        st.metric("수익금", f"{row['손익']:,}원")
                        if pd.notna(row['이미지']) and row['이미지']:
                             img_path = os.path.join(IMAGES_DIR, row['이미지'])
                             if os.path.exists(img_path):
                                 st.image(img_path, caption="차트", use_container_width=True)
        else:
            st.info("아직 기록된 매매가 없습니다.")
            
        st.markdown("---")
        st.markdown("**💡 트레이딩 명언**")
        st.info("시장은 언제나 옳다. 틀린 것은 언제나 나의 분석이다.")

# --- Tab 2: Dashboard ---
with tab_dashboard:
    df = load_data()
    if not df.empty:
        # KPI Cards
        total_trades = len(df)
        win_trades = len(df[df['손익'] > 0])
        loss_trades = len(df[df['손익'] <= 0])
        win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = df['손익'].sum()
        avg_ret = df['수익률(%)'].mean()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 매매 횟수", f"{total_trades}회")
        c2.metric("승률 (Win Rate)", f"{win_rate:.1f}%", delta=f"{win_trades}승 {loss_trades}패")
        c3.metric("누적 수익금", f"{total_pnl:,.0f}원", delta_color="normal")
        c4.metric("평균 수익률", f"{avg_ret:.2f}%")
        
        st.markdown("---")
        
        # Charts
        col_charts1, col_charts2 = st.columns(2)
        
        with col_charts1:
            st.subheader("📈 전략별 승률 분석")
            strategy_stats = df.groupby('전략').apply(
                lambda x: pd.Series({
                    '매매횟수': len(x),
                    '승률': (len(x[x['손익'] > 0]) / len(x)) * 100
                })
            ).reset_index()

            fig_bar = px.bar(strategy_stats, x='전략', y='승률',
                             color='승률',
                             title="전략별 승률 (%)",
                             color_continuous_scale='RdYlGn',
                             hover_data=['매매횟수'])
            fig_bar.add_hline(y=50, line_dash="dot", line_color="white", annotation_text="손익분기점")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_charts2:
            st.subheader("💸 누적 수익 곡선")
            df_sorted = df.sort_values(by="날짜")
            df_sorted['누적손익'] = df_sorted['손익'].cumsum()

            fig_line = px.line(df_sorted, x="날짜", y="누적손익", markers=True, title="자산 증감 추이")
            fig_line.update_traces(line_color='#00E396', line_width=3)
            st.plotly_chart(fig_line, use_container_width=True)
            
        # Mistake Analysis
        st.subheader("⚠️ 나의 실수 패턴 (Top 5)")
        mistakes = df['실수'].dropna().value_counts().head(5)
        if not mistakes.empty:
            st.bar_chart(mistakes, color='#ff4b4b')
        else:
            st.info("기록된 실수가 없습니다. 완벽한 트레이딩 중이시군요!")
            
    else:
        st.warning("데이터가 없습니다. 매매를 기록해주세요.")

# --- Tab 3: History ---
with tab_history:
    st.subheader("전체 매매 내역 관리")
    df = load_data()
    
    if not df.empty:
        # Image Gallery Mode
        st.markdown("### 📸 차트 갤러리")
        cols = st.columns(3)
        img_idx = 0
        for i, row in df.iterrows():
            if pd.notna(row['이미지']) and row['이미지']:
                img_path = os.path.join(IMAGES_DIR, row['이미지'])
                if os.path.exists(img_path):
                    with cols[img_idx % 3]:
                        st.image(img_path, caption=f"{row['날짜']} {row['종목명']} ({row['수익률(%)']}%)", use_container_width=True)
                        img_idx += 1
                        
        st.markdown("---")
        
        # Editable Dataframe
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        
        if st.button("수정사항 저장"):
            save_data(edited_df)
            st.success("데이터가 업데이트되었습니다.")
            st.rerun()
            
        # Download
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "CSV 다운로드",
            csv,
            "trading_journal.csv",
            "text/csv",
            key='download-csv'
        )
    else:
        st.info("데이터가 없습니다.")
