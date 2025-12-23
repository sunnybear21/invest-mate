import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os

class ChartGenerator:
    """
    Generate Interactive Charts using Plotly (Refined)
    """

    def __init__(self, output_dir: str = "charts"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def _calculate_fibonacci(self, df: pd.DataFrame, lookback: int = 60) -> dict:
        """
        최근 N일 기준 스윙 고점/저점을 찾아 피보나치 되돌림 레벨 계산
        상승 추세: 저점 → 고점 기준 (되돌림)
        하락 추세: 고점 → 저점 기준 (되돌림)
        """
        if len(df) < lookback:
            lookback = len(df)
        if lookback < 10:
            return None

        recent = df.tail(lookback)
        high_price = recent['고가'].max()
        low_price = recent['저가'].min()

        high_idx = recent['고가'].idxmax()
        low_idx = recent['저가'].idxmin()

        if high_price == low_price:
            return None

        # 추세 판단: 고점이 저점보다 나중이면 상승 추세
        if high_idx > low_idx:
            # 상승 추세: 저점에서 고점으로 올라온 후 되돌림
            swing_high = high_price
            swing_low = low_price
        else:
            # 하락 추세: 고점에서 저점으로 내려온 후 반등
            swing_high = high_price
            swing_low = low_price

        diff = swing_high - swing_low
        fib_ratios = {
            '0%': 0.0,
            '23.6%': 0.236,
            '38.2%': 0.382,
            '50%': 0.5,
            '61.8%': 0.618,
            '78.6%': 0.786,
            '100%': 1.0
        }

        # 되돌림 레벨 계산 (고점 기준으로 내려가는 방향)
        levels = {}
        for name, ratio in fib_ratios.items():
            levels[name] = swing_high - (diff * ratio)

        return {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'levels': levels
        }

    def create_chart(self, df: pd.DataFrame, analysis_result: dict, code: str, name: str) -> str:
        """Create Candlestick chart and save to HTML"""
        fig = self.get_fig(df, analysis_result, code, name)

        filename = f"{self.output_dir}/smc_{code}_{name}.html"
        filename = filename.replace(' ', '_').replace('/', '_')
        
        fig.write_html(filename)
        return filename

    def get_fig(self, df: pd.DataFrame, analysis_result: dict, code: str, name: str):
        """Return Plotly Figure object with High Contrast Colors for Dark Mode"""
        fig = make_subplots(rows=1, cols=1)

        # 1. Candlestick (Custom Colors for Dark Mode)
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['시가'],
            high=df['고가'],
            low=df['저가'],
            close=df['종가'],
            name=f"{name}",
            increasing_line_color='#ef5350', # Red (Korean Up)
            decreasing_line_color='#2962ff'  # Blue (Korean Down)
        ))

        # 1-1. 20-Day Moving Average (Orange)
        if len(df) >= 20:
            ma20 = df['종가'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=df.index,
                y=ma20,
                mode='lines',
                name='20MA',
                line=dict(color='orange', width=1.5),
                opacity=0.8
            ))

        # 1-2. Accumulation Signal Markers (Purple Star)
        # Logic: 60d Range < 30% & Close > 60d High & Vol > 60d Max Vol
        signal_dates = []
        signal_prices = []
        
        # We need at least 62 rows to check 60d history for a valid signal
        if len(df) > 65:
            # Iterate from 61st row to end
            for i in range(61, len(df)):
                # Window: [i-60 : i] -> window size 60, ending at i-1 (Yesterday)
                window = df.iloc[i-60:i]
                current = df.iloc[i]
                
                # Close price window
                closes = window['종가']
                high_60 = closes.max()
                low_60 = closes.min()
                
                if low_60 == 0: continue
                
                # 1. Volatility
                volatility = (high_60 - low_60) / low_60 * 100
                if volatility >= 30: continue
                
                # 2. Price Breakout (Current Close > 60d High)
                if current['종가'] <= high_60: continue
                
                # 3. Volume Breakout
                max_vol = window['거래량'].max()
                if current['거래량'] <= max_vol: continue
                
                signal_dates.append(df.index[i])
                signal_prices.append(current['저가'] * 0.98) # Mark slightly below Low

        if signal_dates:
            fig.add_trace(go.Scatter(
                x=signal_dates,
                y=signal_prices,
                mode='markers',
                name='Accumulation(매집)',
                marker=dict(symbol='star', size=12, color='#d500f9', line=dict(width=1, color='white'))
            ))

        # 2. Support/Resistance Lines
        sr_levels = analysis_result.get('sr_levels', [])
        for level in sr_levels:
            fig.add_hline(
                y=level,
                line_dash="dot",
                line_color="white",
                line_width=1,
                opacity=0.6,
                annotation_text=f"S/R {int(level)}",
                annotation_font_color="white",
                annotation_position="top right"
            )

        # 2-1. Fibonacci Retracement (최근 스윙 고점/저점 기준)
        show_fibonacci = analysis_result.get('show_fibonacci', True)
        fib_data = self._calculate_fibonacci(df) if show_fibonacci else None
        if fib_data:
            fib_colors = {
                '0%': '#ff6b6b',      # 빨강 (저점)
                '23.6%': '#ffa502',   # 주황
                '38.2%': '#ffd93d',   # 노랑
                '50%': '#6bcb77',     # 초록
                '61.8%': '#4d96ff',   # 파랑
                '78.6%': '#9b59b6',   # 보라
                '100%': '#e84393'     # 핑크 (고점)
            }
            fib_levels = fib_data['levels']
            for level_name, price in fib_levels.items():
                fig.add_hline(
                    y=price,
                    line_dash="dash",
                    line_color=fib_colors.get(level_name, 'gray'),
                    line_width=1.5,
                    opacity=0.8,
                    annotation_text=f"{int(price):,}",
                    annotation_font_color=fib_colors.get(level_name, 'gray'),
                    annotation_position="top right"
                )

        # 3. Order Blocks (High Contrast Neon)
        obs = analysis_result.get('obs', [])
        for ob in obs:
            is_bullish = "Bullish" in ob['type']
            # Translucent Neon colors
            base_color = "0, 255, 0" if is_bullish else "255, 0, 0"
            
            # High Opacity (0.75) as requested
            opacity = 0.75 if not ob['mitigated'] else 0.25
            color = f"rgba({base_color}, {opacity})"
            
            x_end = ob['mitigation_date'] if ob['mitigated'] else df.index[-1]
            
            # Border (Keep distinct)
            line_width = 2 if not ob['mitigated'] else 1
            line_color = f"rgb({base_color})" if not ob['mitigated'] else f"rgba({base_color}, 0.5)"

            fig.add_shape(
                type="rect",
                x0=ob['date'],
                y0=ob['bottom'],
                x1=x_end,
                y1=ob['top'],
                line=dict(width=line_width, color=line_color),
                fillcolor=color,
                layer="below"
            )
            
            # Label the OB (Always show label)
            label_text = "매수 OB" if is_bullish else "매도 OB"
            fig.add_trace(go.Scatter(
                x=[ob['date']], 
                y=[ob['top']],
                mode="text",
                text=[label_text],
                textposition="top right",
                textfont=dict(color="white", size=11, weight="bold"),
                showlegend=False
            ))

        # 4. Fair Value Gaps (Yellow / Blue)
        fvgs = analysis_result.get('fvgs', [])
        for fvg in fvgs:
            is_bullish = "Bullish" in fvg['type']
            # User Preference: High Visibility (75% Opacity)
            # Buy (Support) = Neon Yellow, Sell (Resistance) = Blue
            base_color = "255, 255, 0" if is_bullish else "0, 191, 255"
            
            # Opacity 0.75 (25% Transparency) as requested
            opacity = 0.75 if not fvg['mitigated'] else 0.25
            color = f"rgba({base_color}, {opacity})"
            
            # Fix Vertical Line Issue: Ensure minimum width of 1 period
            x_start = fvg['date']
            x_end = fvg['mitigation_date'] if fvg['mitigated'] else df.index[-1]
            
            # Robustly ensure x_end > x_start using TimeDelta to guarantee width on Chart
            if x_end <= x_start:
                # If mitigated immediately or same day, add 1 day to make it visible
                x_end = x_start + pd.Timedelta(days=1)

            fig.add_shape(
                type="rect",
                x0=x_start,
                y0=fvg['bottom'],
                x1=x_end,
                y1=fvg['top'],
                line=dict(width=0),
                fillcolor=color,
                layer="below"
            )
            
            # Label the FVG (Always show label)
            label_text = "매수 FVG" if is_bullish else "매도 FVG"
            fig.add_trace(go.Scatter(
                x=[x_start], 
                y=[fvg['top']],
                mode="text",
                text=[label_text],
                textposition="bottom right",
                textfont=dict(color="white", size=10, weight="bold"),
                showlegend=False
            ))


        # Layout settings (Dark Mode Optimized)
        fig.update_layout(
            title=dict(text=f"{name} ({code})", font=dict(color='white')),
            xaxis=dict(
                title="Date", 
                showgrid=True, 
                gridcolor='#333', 
                color='white'
            ),
            yaxis=dict(
                title="Price", 
                showgrid=True, 
                gridcolor='#333', 
                color='white'
            ),
            paper_bgcolor='#121212', # Match App BG
            plot_bgcolor='#121212',
            xaxis_rangeslider_visible=False,
            height=700,
            margin=dict(l=50, r=150, t=50, b=40),
            showlegend=False
        )
        return fig
