#!/usr/bin/env python3
"""
Lucy Scanner - Realtime + pykrx integrated
- Naver realtime: current price, change %, volume (live)
- pykrx: historical data, technical conditions (offline)
- No API key needed
"""

import json
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from smart_money_analyzer import SMCAnalyzer
from chart_generator import ChartGenerator

try:
    from pykrx import stock as pykrx_stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    print("\n[!] 'pykrx' library is missing.")
    print("    Please run 'setup.bat' to install dependencies.\n")


class LucyScannerRealtime:
    """Lucy-style surge scanner with realtime data"""

    def __init__(self, theme_file: str = None):
        self.data_dir = os.path.dirname(os.path.abspath(__file__))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module='pykrx')

        # Theme data
        self.stock_themes = {}
        if theme_file:
            self._load_theme_data(theme_file)
        else:
            # Check data/ first, then current dir
            paths_to_check = [
                os.path.join(self.data_dir, "data", "naver_stock_themes.json"),
                os.path.join(self.data_dir, "naver_stock_themes.json")
            ]
            
            for path in paths_to_check:
                if os.path.exists(path):
                    self._load_theme_data(path)
                    break


        # All stock codes cache
        self._all_codes = None
        self._code_names = {}

        # SMC Analysis
        self.smc_analyzer = SMCAnalyzer()
        self.chart_generator = ChartGenerator()


    def _load_theme_data(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.stock_themes = json.load(f)
            print(f"[Theme] {len(self.stock_themes)} stocks loaded")
        except Exception as e:
            print(f"[Error] Theme load failed: {e}")

    def _has_theme(self, code: str) -> bool:
        return code in self.stock_themes and len(self.stock_themes[code]) > 0

    def _get_themes(self, code: str) -> List[str]:
        return self.stock_themes.get(code, [])

    def _get_all_codes(self) -> List[str]:
        """Get all stock codes from pykrx"""
        if self._all_codes:
            return self._all_codes

        if not PYKRX_AVAILABLE:
            return list(self.stock_themes.keys())

        try:
            kospi = pykrx_stock.get_market_ticker_list(market="KOSPI")
            kosdaq = pykrx_stock.get_market_ticker_list(market="KOSDAQ")
            self._all_codes = kospi + kosdaq
            print(f"[Codes] {len(self._all_codes)} stocks (KOSPI: {len(kospi)}, KOSDAQ: {len(kosdaq)})")
            return self._all_codes
        except Exception as e:
            print(f"[Error] Code list: {e}")
            return list(self.stock_themes.keys())

    def _get_naver_realtime(self, code: str) -> Optional[Dict]:
        """Get realtime data from Naver"""
        try:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            resp = self.session.get(url, timeout=5)
            if resp.status_code != 200:
                return None

            html = resp.text
            import re

            # Name
            name_match = re.search(r'<title>(.+?)\s*:', html)
            name = name_match.group(1) if name_match else code

            # Current price
            price_match = re.search(r'<p class="no_today">\s*<em[^>]*>\s*<span class="blind">현재가</span>\s*([\d,]+)', html)
            if not price_match:
                price_match = re.search(r'"currentPrice":([\d]+)', html)
            price = int(price_match.group(1).replace(',', '')) if price_match else 0

            # Change %
            change_match = re.search(r'등락률[^>]*>\s*<em[^>]*>[^<]*</em>\s*<em class="(up|down)">\s*<span[^>]*>[^<]*</span>\s*([\d.]+)%', html)
            if change_match:
                direction = 1 if change_match.group(1) == 'up' else -1
                change_pct = float(change_match.group(2)) * direction
            else:
                change_pct = 0.0

            # Volume amount (approximate from volume * price)
            vol_match = re.search(r'"tradingVolume":([\d]+)', html)
            volume = int(vol_match.group(1)) if vol_match else 0
            volume_amt = volume * price

            # Prev close
            prev_match = re.search(r'"previousClosePrice":([\d]+)', html)
            prev_close = int(prev_match.group(1)) if prev_match else price

            # [NEW] Parse Open, High, Low for Charting
            # High (고가) - sp_txt4
            high_match = re.search(r'<span class="sptxt sp_txt4">고가</span>.*?<span class="blind">([\d,]+)</span>', html, re.DOTALL)
            high = int(high_match.group(1).replace(',', '')) if high_match else price

            # Low (저가) - sp_txt5
            low_match = re.search(r'<span class="sptxt sp_txt5">저가</span>.*?<span class="blind">([\d,]+)</span>', html, re.DOTALL)
            low = int(low_match.group(1).replace(',', '')) if low_match else price

            # Open (시가) - sp_txt3
            open_match = re.search(r'<span class="sptxt sp_txt3">시가</span>.*?<span class="blind">([\d,]+)</span>', html, re.DOTALL)
            open_val = int(open_match.group(1).replace(',', '')) if open_match else price

            # Date (기준일)
            date_match = re.search(r'<em class="date">\s*([\d.]+)', html)
            date_str = date_match.group(1) if date_match else None

            return {
                'code': code,
                'name': name,
                'price': price,
                'prev_close': prev_close,
                'change_pct': change_pct,
                'volume': volume,
                'volume_amt': volume_amt,
                'open': open_val,
                'high': high,
                'low': low,
                'date': date_str
            }
        except Exception as e:
            # print(f"Error parsing Naver realtime: {e}")
            return None

    def _get_naver_sise_realtime(self, codes: List[str]) -> Dict[str, Dict]:
        """Batch get realtime data using Naver sise API"""
        results = {}

        # Naver allows batch query up to 100 codes
        batch_size = 100
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i+batch_size]
            code_str = ','.join(batch)

            try:
                url = f"https://finance.naver.com/api/sise/etfItemList.nhn?codes={code_str}"
                resp = self.session.get(url, timeout=10)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                for item in data.get('result', {}).get('etfItemList', []):
                    code = item.get('itemcode', '')
                    results[code] = {
                        'code': code,
                        'name': item.get('itemname', ''),
                        'price': item.get('nowval', 0),
                        'prev_close': item.get('quession', 0),
                        'change_pct': item.get('changeRate', 0),
                        'volume': item.get('accvolume', 0),
                        'volume_amt': item.get('accvolume', 0) * item.get('nowval', 0)
                    }
            except:
                continue

        return results

    def _get_naver_rising_stocks(self, market: str = "KOSPI", count: int = 100) -> List[Dict]:
        """Get top rising stocks from Naver"""
        results = []

        try:
            if market == "KOSPI":
                url = "https://finance.naver.com/sise/sise_rise.naver?sosok=0"
            else:
                url = "https://finance.naver.com/sise/sise_rise.naver?sosok=1"

            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return results

            html = resp.text
            import re

            # Parse table rows
            pattern = r'<a href="/item/main\.naver\?code=(\d{6})"[^>]*>([^<]+)</a>.*?<td class="number">([\d,]+)</td>.*?<td class="number">\s*<span class="(tah p11 red01|tah p11 nv01)">\s*([\d,]+)\s*</span>.*?<span class="(tah p11 red01|tah p11 nv01)">\s*\+?([\d.]+)%'

            matches = re.findall(pattern, html, re.DOTALL)

            for match in matches[:count]:
                code, name, price, _, change, _, change_pct = match
                results.append({
                    'code': code,
                    'name': name.strip(),
                    'price': int(price.replace(',', '')),
                    'change': int(change.replace(',', '')),
                    'change_pct': float(change_pct)
                })

        except Exception as e:
            print(f"[Error] Rising stocks: {e}")

        return results

    def _get_historical_data(self, code: str, days: int = 60) -> pd.DataFrame:
        """Get historical data from pykrx and merge with realtime Naver data"""
        if not PYKRX_AVAILABLE:
            print(f"[Error] pykrx not available for code {code}")
            return pd.DataFrame()
        try:
            end = datetime.now().strftime("%Y%m%d")
            start = (datetime.now() - timedelta(days=days + 30)).strftime("%Y%m%d")
            print(f"[Debug] Fetching {code} from {start} to {end}")

            df = pykrx_stock.get_market_ohlcv(start, end, code)
            print(f"[Debug] Got {len(df)} rows for {code}")

            # Check if df has expected columns (handle Korean/English column names)
            if not df.empty:
                # Rename columns if needed (pykrx sometimes returns different names)
                col_map = {
                    'Open': '시가', 'High': '고가', 'Low': '저가',
                    'Close': '종가', 'Volume': '거래량',
                    '시가': '시가', '고가': '고가', '저가': '저가',
                    '종가': '종가', '거래량': '거래량'
                }
                df = df.rename(columns=col_map)

                # Ensure required columns exist
                required = ['시가', '고가', '저가', '종가', '거래량']
                missing = [c for c in required if c not in df.columns]
                if missing:
                    print(f"[Warning] Missing columns: {missing}, available: {df.columns.tolist()}")

            # [NEW] Merge Realtime Data
            try:
                realtime = self._get_naver_realtime(code)
                if realtime and realtime.get('price'):
                    # Prepare row data
                    latest_data = {
                        '시가': realtime.get('open', 0),
                        '고가': realtime.get('high', 0),
                        '저가': realtime.get('low', 0),
                        '종가': realtime['price'],
                        '거래량': realtime['volume']
                    }

                    # Fallback for 0 values
                    if latest_data['시가'] == 0: latest_data['시가'] = latest_data['종가']
                    if latest_data['고가'] == 0: latest_data['고가'] = latest_data['종가']
                    if latest_data['저가'] == 0: latest_data['저가'] = latest_data['종가']

                    # Determine date
                    today_dt = pd.to_datetime(datetime.now().date())
                    if realtime.get('date'):
                        try:
                            # Naver date format: 2025.12.19
                            today_dt = pd.to_datetime(realtime['date'])
                        except:
                            pass

                    if df.empty:
                        df = pd.DataFrame([latest_data], index=[today_dt])
                    else:
                        last_date = df.index[-1]

                        if last_date.date() == today_dt.date():
                            # Update existing today's row
                            for col in ['시가', '고가', '저가', '종가', '거래량']:
                                if col in df.columns:
                                    df.at[last_date, col] = latest_data[col]
                        else:
                            # Append new row for today
                            new_row = pd.DataFrame([latest_data], index=[today_dt])
                            df = pd.concat([df, new_row])

            except Exception as e:
                print(f"[Warning] Realtime merge failed: {e}")

            return df.tail(days) if len(df) > days else df
        except Exception as e:
            print(f"[Error] _get_historical_data failed for {code}: {e}")
            return pd.DataFrame()

    def _check_technical_conditions(self, df: pd.DataFrame) -> List[str]:
        """Check all technical conditions"""
        conditions = []

        if len(df) < 20:
            return conditions

        try:
            # Golden cross (5MA > 20MA)
            ma5 = df['종가'].rolling(5).mean()
            ma20 = df['종가'].rolling(20).mean()
            if ma5.iloc[-1] > ma20.iloc[-1]:
                if len(ma5) > 3 and ma5.iloc[-3] <= ma20.iloc[-3]:
                    conditions.append('GoldenX')
                elif ma5.iloc[-1] > ma20.iloc[-1]:
                    conditions.append('MA5>20')
        except:
            pass

        try:
            # Volume explosion (3x avg)
            if len(df) >= 21:
                avg_vol = df['거래량'].iloc[-21:-1].mean()
                today_vol = df['거래량'].iloc[-1]
                if avg_vol > 0 and today_vol >= avg_vol * 3:
                    conditions.append('Vol3x')
        except:
            pass

        try:
            # 20MA support
            if len(df) >= 20:
                ma20_val = df['종가'].rolling(20).mean().iloc[-1]
                if df['종가'].iloc[-1] > ma20_val:
                    conditions.append('MA20+')
        except:
            pass

        try:
            # 60-day new high
            if len(df) >= 60:
                high_60d = df['고가'].iloc[-60:-1].max()
                if df['종가'].iloc[-1] >= high_60d:
                    conditions.append('High60')
        except:
            pass

        try:
            # 7-day surge (15%+)
            if len(df) >= 7:
                low_7d = df['저가'].iloc[-7:].min()
                current = df['종가'].iloc[-1]
                if low_7d > 0 and (current - low_7d) / low_7d * 100 >= 15:
                    conditions.append('Surge7d')
        except:
            pass

        try:
            # RSI
            delta = df['종가'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = rsi.iloc[-1]
            if not pd.isna(rsi_val) and rsi_val >= 60:
                conditions.append(f'RSI{rsi_val:.0f}')
        except:
            pass

        return conditions

    def scan_realtime(self,
                      min_change: float = 5.0,
                      min_volume_억: float = 100,
                      require_theme: bool = True,
                      min_conditions: int = 2,
                      top_n: int = 50) -> List[Dict]:
        """
        Realtime scan using Naver data

        Args:
            min_change: Minimum change % (default 5%)
            min_volume_억: Minimum volume amount in 억 (default 100억)
            require_theme: Require theme stock (default True)
            min_conditions: Minimum technical conditions (default 2)
            top_n: Max results to return (default 50)
        """

        print(f"\n{'='*60}")
        print(f"[Realtime Scan] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Conditions: Change {min_change}%+ | Volume {min_volume_억}억+ | Theme={require_theme} | Tech {min_conditions}+")
        print(f"{'='*60}\n")

        stocks = []
        min_volume_amt = min_volume_억 * 1e8

        # Step 1: Get rising stocks from Naver (fast)
        print("[1/3] Getting rising stocks from Naver...")
        rising_kospi = self._get_naver_rising_stocks("KOSPI", 200)
        rising_kosdaq = self._get_naver_rising_stocks("KOSDAQ", 200)
        all_rising = rising_kospi + rising_kosdaq
        print(f"  Found {len(all_rising)} rising stocks")

        # Step 2: Filter by change % and theme
        print("[2/3] Filtering candidates...")
        candidates = []
        for stock in all_rising:
            if stock['change_pct'] < min_change:
                continue
            if require_theme and not self._has_theme(stock['code']):
                continue
            candidates.append(stock)
        print(f"  {len(candidates)} passed (change + theme)")

        # Step 3: Get detailed data and check conditions
        print("[3/3] Checking technical conditions...")
        passed = 0

        for stock in candidates:
            try:
                code = stock['code']

                # Get realtime details
                detail = self._get_naver_realtime(code)
                if not detail:
                    continue

                # Volume filter
                if detail['volume_amt'] < min_volume_amt:
                    continue

                # Get historical data for technical conditions
                df_hist = self._get_historical_data(code, days=60)
                conditions = self._check_technical_conditions(df_hist)

                # Min conditions filter
                if len(conditions) < min_conditions:
                    continue

                themes = self._get_themes(code)

                stock_info = {
                    'code': code,
                    'name': detail['name'],
                    'price': detail['price'],
                    'prev_close': detail['prev_close'],
                    'change_pct': round(stock['change_pct'], 2),
                    'volume_amt': detail['volume_amt'],
                    'volume_억': round(detail['volume_amt'] / 1e8, 1),
                    'themes': themes[:3],
                    'conditions': conditions,
                    'cond_count': len(conditions)
                }
                stocks.append(stock_info)
                passed += 1

                if passed % 5 == 0:
                    print(f"  Progress: {passed} stocks passed")

                if passed >= top_n:
                    break

            except Exception as e:
                continue

        # Sort by conditions count, then change %
        stocks.sort(key=lambda x: (x['cond_count'], x['change_pct']), reverse=True)

        print(f"\n[Done] {len(stocks)} stocks found")
        return stocks

    def scan_pykrx(self,
                   date_str: str = None,
                   min_change: float = 3.0,
                   min_volume_억: float = 200,
                   require_theme: bool = True,
                   min_conditions: int = 3) -> List[Dict]:
        """
        Scan using pykrx (for after-market or historical)
        """


        # Suppress warnings
        import warnings
        warnings.simplefilter(action='ignore', category=FutureWarning)

        if not PYKRX_AVAILABLE:
            print("[Error] pykrx not available")
            return []

        # Find latest trading day if date not specified
        if not date_str:
            target_date = self._find_latest_trading_date()
            print(f"[Info] Auto-detected latest trading date: {target_date}")
        else:
            target_date = date_str

        today = target_date
        min_volume_amt = min_volume_억 * 1e8

        print(f"\n{'='*60}")
        print(f"[pykrx Scan] {today}")
        print(f"Conditions: Change {min_change}%+ | Volume {min_volume_억}억+ | Theme={require_theme} | Tech {min_conditions}+")
        print(f"{'='*60}\n")

        stocks = []

        # Get OHLCV
        print("[1/4] Loading OHLCV...")
        try:
            df_ohlcv = pykrx_stock.get_market_ohlcv(today, market="ALL")
        except Exception as e:
            print(f"[Error] Failed to load data: {e}")
            return []

        if df_ohlcv.empty:
            print("[Error] No OHLCV data found for this date.")
            return []


        # Get prev close
        print("[2/4] Loading prev data...")
        prev_date = self._get_prev_date(today)
        df_prev = pykrx_stock.get_market_ohlcv(prev_date, market="ALL")
        prev_close = df_prev['종가'].to_dict() if not df_prev.empty else {}

        # Get market cap
        print("[3/4] Loading market cap...")
        df_cap = pykrx_stock.get_market_cap(today, market="ALL")
        market_cap = df_cap['시가총액'].to_dict() if not df_cap.empty else {}

        # Filter
        print("[4/4] Scanning stocks...")
        candidates = []

        for code in df_ohlcv.index:
            row = df_ohlcv.loc[code]

            # Basic filter
            if row['거래대금'] < min_volume_amt:
                continue
            if row['거래량'] == 0 or row['시가'] == 0:
                continue
            if row['종가'] < 1000:
                continue
            if code[-1] in '56789':
                continue

            # Change %
            prev = prev_close.get(code, row['시가'])
            change_pct = (row['종가'] - prev) / prev * 100 if prev > 0 else 0
            if change_pct < min_change:
                continue

            # Theme
            if require_theme and not self._has_theme(code):
                continue

            candidates.append((code, change_pct, row, market_cap.get(code, 0)))

        print(f"  Candidates: {len(candidates)}")

        # Check technical conditions
        passed = 0
        for code, change_pct, row, cap in candidates:
            try:
                name = pykrx_stock.get_market_ticker_name(code) or code

                if any(x in name for x in ['스팩', 'SPAC', 'ETF', 'ETN', '리츠']):
                    continue

                df_hist = self._get_historical_data(code, days=60)
                conditions = self._check_technical_conditions(df_hist)

                if len(conditions) < min_conditions:
                    continue

                themes = self._get_themes(code)
                prev = prev_close.get(code, row['시가'])

                stock_info = {
                    'code': code,
                    'name': name,
                    'price': int(row['종가']),
                    'prev_close': int(prev),
                    'change_pct': round(change_pct, 2),
                    'volume_amt': int(row['거래대금']),
                    'volume_억': round(row['거래대금'] / 1e8, 1),
                    'market_cap_억': round(cap / 1e8, 0),
                    'themes': themes[:3],
                    'conditions': conditions,
                    'cond_count': len(conditions)
                }
                stocks.append(stock_info)
                passed += 1

                if passed % 10 == 0:
                    print(f"  Progress: {passed} stocks passed")

            except:
                continue

        stocks.sort(key=lambda x: (x['cond_count'], x['change_pct']), reverse=True)

        print(f"\n[Done] {len(stocks)} stocks found")
        return stocks



    def scan_smc(self, target_code: str = None) -> List[Dict]:
        """
        Smart Money Concepts Analysis
        Analyzes a set of target stocks (or a single stock) for SMC features
        """
        if not PYKRX_AVAILABLE:
            print("[Error] pykrx not available")
            return []

        print(f"\n{'='*60}")
        print(f"[Smart Money Analysis] Detecting OB, FVG, S/R")
        print(f"{'='*60}\n")
        
        candidates = []

        if target_code:
            # Single stock mode
            print(f"[Target] Analyzing single stock: {target_code}")
            try:
                name = pykrx_stock.get_market_ticker_name(target_code)
                if not name:
                    print(f"[Error] Invalid code: {target_code}")
                    return []
                candidates.append({'code': target_code, 'name': name})
            except:
                print(f"[Error] Failed to look up code: {target_code}")
                return []
        else:
            # Full scan mode
            # 1. Get List of "Interesting" Stocks 
            print("[1/3] Getting candidates (Rising Stocks)...")
            rising_kospi = self._get_naver_rising_stocks("KOSPI", 50)
            rising_kosdaq = self._get_naver_rising_stocks("KOSDAQ", 50)
            candidates = rising_kospi + rising_kosdaq
            print(f"  Got {len(candidates)} candidates.")

        results = []
        
        step_desc = "[2/3]" if not target_code else "[Analysis]"
        print(f"{step_desc} Analyzing Market Structure...")

        for i, stock in enumerate(candidates):
            try:
                code = stock['code']
                name = stock['name']
                
                # Fetch detailed history
                df = self._get_historical_data(code, days=120)
                if len(df) < 60: continue

                # Run SMC Analysis
                sr_levels = self.smc_analyzer.get_support_resistance_zones(df)
                obs = self.smc_analyzer.get_order_blocks(df)
                fvgs = self.smc_analyzer.get_fvg(df)
                
                # Filter: Only show if there are recent OBs or FVGs near current price?
                # For now, just generate charts for all valid candidates that have some features
                
                if len(obs) > 0 or len(fvgs) > 0:
                    analysis_result = {
                        'sr_levels': sr_levels,
                        'obs': obs,
                        'fvgs': fvgs
                    }
                    
                    # Generate Chart
                    chart_path = self.chart_generator.create_chart(df, analysis_result, code, name)
                    
                    results.append({
                        'code': code,
                        'name': name,
                        'chart_path': chart_path,
                        'obs_count': len(obs),
                        'fvg_count': len(fvgs)
                    })
                    
                    print(f"  [{i+1}/{len(candidates)}] {name}: Generated {chart_path}")
            
            except Exception as e:
                # print(e)
                continue
                
        print(f"\n[Done] Generated {len(results)} analysis charts.")
        print(f"Check the 'charts' folder.\n")
        return results

    def scan_squeeze(self, date_str: str = None, vol_mult: float = 5.0, cv_threshold: float = 2.5) -> List[Dict]:
        """
        Scan for Squeeze Breakout (Sideways -> Volume Explosion)
        Args:
            vol_mult: Volume spike multiplier (Today / Yesterday >= 5)
            cv_threshold: Coefficient of Variation (StdDev/Mean * 100) limit for previous 59 days
        """
        if not PYKRX_AVAILABLE:
            print("[Error] pykrx not available")
            return []

        # 1. Determine Date
        if not date_str:
            target_date = self._find_latest_trading_date()
        else:
            target_date = date_str
        
        print(f"\n{'='*60}")
        print(f"[Squeeze Scan] Target Date: {target_date}")
        print(f"Condition 1: Volume Spike >= {vol_mult}x (vs Yesterday)")
        print(f"Condition 2: Volatility(59days) < {cv_threshold}% (Sideways)")
        print(f"{'='*60}\n")

        stocks = []

        # 2. Get Today & Yesterday Data
        print("[1/4] Loading Market Data...")
        try:
            df_today = pykrx_stock.get_market_ohlcv(target_date, market="ALL")
            prev_date = self._get_prev_date(target_date)
            df_prev = pykrx_stock.get_market_ohlcv(prev_date, market="ALL")
            
            if df_today.empty or df_prev.empty:
                print("[Error] No data found.")
                return []
        except Exception as e:
            print(f"[Error] Data load failed: {e}")
            return []

        # 3. Filter by Volume Spike First (Fastest)
        print("[2/4] Screening Volume Spikes...")
        candidates = []
        for code in df_today.index:
            try:
                # Basic hygiene
                nm = pykrx_stock.get_market_ticker_name(code)
                if any(x in nm for x in ['스팩', 'SPAC', 'ETF', 'ETN', '리츠']):
                    continue
                
                vol_today = df_today.at[code, '거래량']
                if code not in df_prev.index: continue
                vol_prev = df_prev.at[code, '거래량']

                if vol_prev == 0: continue
                
                # Check Spike
                if vol_today >= vol_prev * vol_mult:
                     candidates.append(code)
            except:
                continue
        
        print(f"  -> {len(candidates)} stocks passed volume filter.")

        # 4. Check Volatility (Slower, requires history)
        print("[3/4] Checking Volatility (Sideways)...")
        passed = 0
        
        for code in candidates:
            try:
                # Get 60 days including today, then take previous 59
                df_hist = self._get_historical_data(code, days=90) # Get enough buffer
                if len(df_hist) < 60: continue
                
                # Previous 60 days excluding today? 
                # User said "Recent 60 days... 59 days stddev very low"
                # Let's look at the window BEFORE today.
                # If today is included, the huge jump might ruin the stddev.
                # So we analyze the window [Today-60 : Today-1]
                
                df_window = df_hist.iloc[:-1].tail(60)
                if len(df_window) < 30: continue

                # Calculate Coefficient of Variation (StdDev / Mean)
                closes = df_window['종가']
                std_dev = closes.std()
                mean_price = closes.mean()
                
                if mean_price == 0: continue
                
                cv = (std_dev / mean_price) * 100
                
                if cv <= cv_threshold:
                    # Found one!
                    name = pykrx_stock.get_market_ticker_name(code)
                    row = df_today.loc[code]
                    prev_close = df_prev.loc[code]['종가']
                    change_pct = (row['종가'] - prev_close) / prev_close * 100
                    
                    stocks.append({
                        'code': code,
                        'name': name,
                        'price': int(row['종가']),
                        'prev_close': int(prev_close),
                        'change_pct': round(change_pct, 2),
                        'volume_억': round(row['거래대금'] / 1e8, 1),
                        'volume_x': round(row['거래량'] / df_prev.loc[code]['거래량'], 1),
                        'volatility_cv': round(cv, 2),
                        'conditions': [f'Vol {vol_mult}x', f'CV {round(cv,1)}%'],
                        'themes': self._get_themes(code)
                    })
                    passed += 1
                    if passed % 5 == 0:
                        print(f"  Found {passed} stocks...")
                        
            except Exception as e:
                # print(e)
                continue

        stocks.sort(key=lambda x: x['volatility_cv']) # Sort by tightest consolidation
        
        print(f"\n[Done] {len(stocks)} stocks found")
        return stocks

    def scan_accumulation(self, date_str: str = None) -> List[Dict]:
        """
        Scan for 'Smart Money Accumulation/Breakout' (세력 매집)
        Logic:
          1. 60-day Box Range (yesterday) < 30% (Low Volatility)
          2. Today's Close > Yesterday's 60-day High (Breakout)
          3. Today's Volume > Max Volume of previous 60 days (Volume Breakout)
        """
        if not PYKRX_AVAILABLE:
            print("[Error] pykrx not available")
            return []

        # 1. Determine Date
        if not date_str:
            target_date = self._find_latest_trading_date()
        else:
            target_date = date_str

        print(f"\n{'='*60}")
        print(f"[Accumulation Scan] Target Date: {target_date}")
        print(f"Conditions: 60d Range<30% | Price Breakout | Volume Breakout")
        print(f"{'='*60}\n")

        stocks = []

        # 2. Get Today's Market Data
        print("[1/4] Loading Market Data...")
        try:
            df_today = pykrx_stock.get_market_ohlcv(target_date, market="ALL")
            if df_today.empty:
                print("[Error] No data found.")
                return []
        except Exception as e:
            print(f"[Error] Data load failed: {e}")
            return []

        # 3. Filter Candidates
        print("[2/4] Screening Candidates...")
        
        total_tickers = df_today.index
        candidates = []
        for code in total_tickers:
            try:
                # Basic hygiene
                if df_today.at[code, '거래대금'] < 500_000_000: # Min 5억
                    continue

                nm = pykrx_stock.get_market_ticker_name(code)
                if not nm: continue
                if any(x in nm for x in ['스팩', 'SPAC', 'ETF', 'ETN', '리츠']):
                    continue
                candidates.append(code)
            except:
                pass
        
        print(f"  Checking {len(candidates)} stocks (Detailed History)...")

        processed = 0
        passed_count = 0
        
        for code in candidates:
            processed += 1
            if processed % 100 == 0:
                print(f"  Scanning... {processed}/{len(candidates)} (Found: {passed_count})")

            try:
                # Need ~70 days of history
                # We need enough history to calculate 60-day range for YESTERDAY
                df_hist = self._get_historical_data(code, days=90)
                
                # Check actual length
                if len(df_hist) < 62: continue
                
                # We assume the last row is 'Today' (target_date)
                # But strict checking: 
                # If target_date is in index, use it.
                # If we are strictly following "Yesterday's 60-day candle", we need to shift.
                
                # Slicing:
                # [-1] = Today
                # [-61:-1] = Previous 60 days (Yesterday back to -60)
                
                df_prev_60 = df_hist.iloc[-61:-1]
                if len(df_prev_60) < 60: continue

                current = df_hist.iloc[-1] # Today
                
                # 1. Volatility Condition: (High - Low) / Low < 30% (over those 60 days)
                # Formula: 고저=(상단-하단)/하단*100;
                high_60 = df_prev_60['종가'].max() # 상단
                low_60 = df_prev_60['종가'].min()  # 하단
                
                if low_60 == 0: continue
                
                volatility = (high_60 - low_60) / low_60 * 100
                if volatility >= 30:
                    continue
                    
                # 2. Breakout: Close > Yesterday's 60d High
                # CrossUp(C, 상단(1)) -> Today Close > high_60
                if current['종가'] <= high_60:
                    continue
                    
                # 3. Volume: Highest(V,60,1) < V -> Today Vol > Max Vol of Prev 60
                max_vol_60 = df_prev_60['거래량'].max()
                if current['거래량'] <= max_vol_60:
                    continue
                    
                # Passed
                name = pykrx_stock.get_market_ticker_name(code)
                
                stocks.append({
                    'code': code,
                    'name': name,
                    'price': int(current['종가']),
                    'change_pct': round((current['종가'] - df_prev_60['종가'].iloc[-1])/df_prev_60['종가'].iloc[-1]*100, 2),
                    'volume_억': round(current['거래대금'] / 1e8, 1),
                    'conditions': [f'Range {int(volatility)}%', 'Breakout'],
                    'themes': self._get_themes(code)
                })
                passed_count += 1
                
            except Exception as e:
                continue

        print(f"\n[Done] Found {len(stocks)} stocks.")
        stocks.sort(key=lambda x: x['volume_억'], reverse=True)
        return stocks

    def _find_latest_trading_date(self) -> str:
        """Find the most recent trading date with valid volume"""
        dt = datetime.now()
        for i in range(10):  # Check up to 10 days back
            check_date = dt - timedelta(days=i)
            date_str = check_date.strftime("%Y%m%d")
            
            # Skip future dates? (Already constrained by loop starting now)
            
            try:
                # Quick check with KOSPI index or a major stock (Samsung Electronics 005930)
                # But to be safe, check market ohlcv total volume
                # Checking entire market ohlcv might be slow, but accurate.
                df = pykrx_stock.get_market_ohlcv(date_str, market="KOSPI")
                if not df.empty and df['거래량'].sum() > 0:
                    return date_str
            except:
                pass
        return dt.strftime("%Y%m%d")

    def _get_prev_date(self, date_str: str) -> str:
        """Get previous trading date"""
        dt = datetime.strptime(date_str, "%Y%m%d")
        for i in range(1, 10):
            prev_dt = dt - timedelta(days=i)
            prev_str = prev_dt.strftime("%Y%m%d")
            try:
                df = pykrx_stock.get_market_ohlcv(prev_str, market="KOSPI")
                if not df.empty:
                    return prev_str
            except:
                continue
        return date_str

    def print_result(self, stocks: List[Dict], top_n: int = 30):
        """Print results"""
        print(f"\n{'='*90}")
        print(f"Top {min(top_n, len(stocks))} Stocks")
        print(f"{'='*90}")
        print(f"{'#':>3} {'Code':>8} {'Name':<14} {'Change':>7} {'Volume':>10} {'Conditions'}")
        print(f"{'-'*90}")

        for i, s in enumerate(stocks[:top_n], 1):
            conds = ','.join(s['conditions'][:4])
            if len(s['conditions']) > 4:
                conds += f"+{len(s['conditions'])-4}"
            themes = ','.join(s.get('themes', [])[:2])
            print(f"{i:3d} {s['code']:>8} {s['name'][:14]:<14} {s['change_pct']:>+6.1f}% "
                  f"{s['volume_억']:>8.0f}억  {conds}")
            if themes:
                print(f"{'':>32} [{themes}]")

        if len(stocks) > top_n:
            print(f"... and {len(stocks) - top_n} more")

    def save_result(self, stocks: List[Dict], filename: str = None):
        """Save results to JSON"""
        if not filename:
            now = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"lucy_scan_{now}.json"
        
        # Ensure 'data' directory exists
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            
        filename = os.path.join(data_dir, filename)

        result = {
            'scan_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'count': len(stocks),
            'stocks': stocks
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n[Saved JSON] {filename}")

        # Also save as CSV for HTS import
        csv_filename = filename.replace('.json', '.csv')
        try:
            # Flatten data for CSV
            csv_data = []
            for s in stocks:
                csv_data.append({
                    'Code': s['code'],
                    'Name': s['name'],
                    'Price': s['price'],
                    'Change(%)': s['change_pct'],
                    'Volume(억)': s['volume_억'],
                    'Conditions': ','.join(s['conditions']),
                    'Themes': ','.join(s.get('themes', []))
                })
            
            if csv_data:
                df = pd.DataFrame(csv_data)
                # Save with BOM for Excel/HTS compatibility
                df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                print(f"[Saved CSV]  {csv_filename}")

                # [NEW] Kiwoom HTS specific format (Name, Code)
                kiwoom_filename = filename.replace('.json', '_kiwoom.csv')
                df_kiwoom = df[['Name', 'Code']].copy()
                df_kiwoom.columns = ['종목명', '종목코드'] # Rename headers to Korean
                df_kiwoom.to_csv(kiwoom_filename, index=False, encoding='cp949') # Kiwoom often prefers cp949 (EUC-KR)
                print(f"[Saved HTS]  {kiwoom_filename}")

        except Exception as e:
            print(f"[Error] Failed to save CSV: {e}")




def main():
    import argparse

    parser = argparse.ArgumentParser(description='Lucy Scanner (Realtime + pykrx)')
    parser.add_argument('--realtime', '-r', action='store_true', help='Realtime scan (Naver)')
    parser.add_argument('--squeeze', action='store_true', help='Squeeze Breakout scan (Low Volatility + Vol Spike)')
    parser.add_argument('--acc', action='store_true', help='Smart Money Accumulation Breakout')
    parser.add_argument('--smc', action='store_true', help='Smart Money Concepts Analysis (S/R, OB, FVG)')
    parser.add_argument('--code', type=str, help='Target stock code for SMC analysis')
    parser.add_argument('--date', type=str, help='Date for pykrx scan (YYYYMMDD)')
    parser.add_argument('--min-change', type=float, default=5.0, help='Min change %% (default 5)')
    parser.add_argument('--min-volume', type=float, default=100, help='Min volume in 억 (default 100)')
    parser.add_argument('--vol-mult', type=float, default=5.0, help='Volume spike multiplier (default 5.0)')
    parser.add_argument('--min-cond', type=int, default=2, help='Min technical conditions (default 2)')
    parser.add_argument('--no-theme', action='store_true', help='Disable theme filter')
    parser.add_argument('--save', '-s', action='store_true', help='Save result')
    args = parser.parse_args()

    scanner = LucyScannerRealtime()

    if args.realtime:
        # Realtime scan
        stocks = scanner.scan_realtime(
            min_change=args.min_change,
            min_volume_억=args.min_volume,
            require_theme=not args.no_theme,
            min_conditions=args.min_cond
        )
    elif args.squeeze:
        # Squeeze scan
        stocks = scanner.scan_squeeze(
            date_str=args.date,
            vol_mult=args.vol_mult,
            cv_threshold=3.0 # Default specific to this strategy
        )
    elif args.smc:
        # Smart Money scan
        scanner.scan_smc(target_code=args.code)
        stocks = [] # SMC generates charts mainly
    elif args.acc:
        # Accumulation scan
        stocks = scanner.scan_accumulation(date_str=args.date)
    else:
        # pykrx scan (after-market)
        stocks = scanner.scan_pykrx(
            date_str=args.date,
            min_change=args.min_change,
            min_volume_억=args.min_volume,
            require_theme=not args.no_theme,
            min_conditions=args.min_cond
        )

    scanner.print_result(stocks)

    if args.save:
        scanner.save_result(stocks)


if __name__ == '__main__':
    main()
