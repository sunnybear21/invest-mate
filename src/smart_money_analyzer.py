import pandas as pd
import numpy as np

class SMCAnalyzer:
    """
    SMC Analyzer with Native Python Implementation
    - Refined S/R (Clustering)
    - Stricter Order Block Detection
    """
    def __init__(self):
        pass

    def get_support_resistance_zones(self, df: pd.DataFrame, window: int = 10, merge_threshold: float = 0.015) -> list:
        """
        Identify Support/Resistance using Swing Highs/Lows with Clustering
        - Window increased to 10 for significant levels
        - Merges levels within 1.5% of each other
        """
        if df.empty:
            return []
            
        highs = df['고가']
        lows = df['저가']
        
        raw_levels = []
        
        # 1. Detect Swing Highs/Lows
        for i in range(window, len(df) - window):
            # Swing High
            if all(highs.iloc[i] > highs.iloc[i-window:i]) and \
               all(highs.iloc[i] > highs.iloc[i+1:i+1+window]):
                raw_levels.append(highs.iloc[i])
                
            # Swing Low
            if all(lows.iloc[i] < lows.iloc[i-window:i]) and \
               all(lows.iloc[i] < lows.iloc[i+1:i+1+window]):
                raw_levels.append(lows.iloc[i])
        
        if not raw_levels:
            return []
            
        # 2. Cluster/Merge Levels
        raw_levels.sort()
        merged_levels = []
        
        if raw_levels:
            current_cluster = [raw_levels[0]]
            
            for i in range(1, len(raw_levels)):
                level = raw_levels[i]
                last_val = current_cluster[-1]
                
                # If within threshold (e.g. 1.5%), add to cluster
                if abs(level - last_val) / last_val <= merge_threshold:
                    current_cluster.append(level)
                else:
                    # Finalize current cluster (take average)
                    avg_level = sum(current_cluster) / len(current_cluster)
                    merged_levels.append(int(avg_level))
                    current_cluster = [level]
            
            # Final cluster
            if current_cluster:
                avg_level = sum(current_cluster) / len(current_cluster)
                merged_levels.append(int(avg_level))
                
        return merged_levels

    def get_order_blocks(self, df: pd.DataFrame) -> list:
        """
        Identify Order Blocks (OB)
        - Bullish OB: Last DOWN candle before strong UP move
        - Bearish OB: Last UP candle before strong DOWN move
        - Top/Bottom defined by the OB candle
        """
        obs = []
        if len(df) < 5:
            return []

        df['body'] = abs(df['종가'] - df['시가'])
        avg_body = df['body'].rolling(20).mean()
        
        for i in range(2, len(df) - 2):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Use stricter confirmation: Body size AND Follow-through
            # 1. Bullish OB
            if curr['종가'] > curr['시가']: # Green Impulse
                if curr['body'] > 1.5 * avg_body.iloc[i]: # Strong move (Loosened from 2.0)
                    # Check break of previous high for confirmation
                     if curr['종가'] > df['고가'].iloc[i-1]:
                         if prev['종가'] < prev['시가']: # Red OB candle
                             top = max(prev['시가'], prev['종가'])
                             bottom = min(prev['시가'], prev['종가'])
                             
                             # Mitigation
                             mitigated = False
                             mitigation_date = None
                             future = df.iloc[i+1:]
                             
                             # Optimization: vectorized check? No, loop is fine for daily data
                             for idx, row in future.iterrows():
                                 # Mitigated if price touches the zone
                                 if row['저가'] <= top and row['고가'] >= bottom:
                                     mitigated = True
                                     mitigation_date = idx
                                     break
                             
                             obs.append({
                                 'type': 'Bullish OB',
                                 'date': prev.name,
                                 'top': top,
                                 'bottom': bottom,
                                 'mitigated': mitigated,
                                 'mitigation_date': mitigation_date
                             })

            # 2. Bearish OB
            if curr['종가'] < curr['시가']: # Red Impulse
                 if curr['body'] > 1.5 * avg_body.iloc[i]:
                     if curr['종가'] < df['저가'].iloc[i-1]:
                         if prev['종가'] > prev['시가']: # Green OB candle
                             top = max(prev['시가'], prev['종가'])
                             bottom = min(prev['시가'], prev['종가'])
                             
                             mitigated = False
                             mitigation_date = None
                             future = df.iloc[i+1:]
                             for idx, row in future.iterrows():
                                 if row['고가'] >= bottom and row['저가'] <= top:
                                     mitigated = True
                                     mitigation_date = idx
                                     break
                                     
                             obs.append({
                                 'type': 'Bearish OB',
                                 'date': prev.name,
                                 'top': top,
                                 'bottom': bottom,
                                 'mitigated': mitigated,
                                 'mitigation_date': mitigation_date
                             })
                             
        return obs

    def get_fvg(self, df: pd.DataFrame) -> list:
        """
        Identify Fair Value Gaps (FVG)
        """
        fvgs = []
        if len(df) < 3:
            return []
            
        for i in range(len(df) - 2):
            c1 = df.iloc[i]
            c2 = df.iloc[i+1]
            c3 = df.iloc[i+2]
            
            # Bullish FVG
            if c2['종가'] > c2['시가']:
                if c1['고가'] < c3['저가']:
                    # Size check: gap should be somewhat visible?
                    # gap_size = c3['저가'] - c1['고가']
                    # if gap_size > ...
                    
                    top = c3['저가']
                    bottom = c1['고가']
                    
                    mitigated = False
                    mitigation_date = None
                    future = df.iloc[i+3:]
                    for idx, row in future.iterrows():
                        if row['저가'] <= top: # Touched/Filled
                            mitigated = True
                            mitigation_date = idx
                            break
                            
                    fvgs.append({
                        'type': 'Bullish FVG',
                        'date': c2.name,
                        'top': top,
                        'bottom': bottom,
                        'mitigated': mitigated,
                        'mitigation_date': mitigation_date
                    })

            # Bearish FVG
            if c2['종가'] < c2['시가']:
                if c1['저가'] > c3['고가']:
                    top = c1['저가']
                    bottom = c3['고가']
                    
                    mitigated = False
                    mitigation_date = None
                    future = df.iloc[i+3:]
                    for idx, row in future.iterrows():
                        if row['고가'] >= bottom:
                            mitigated = True
                            mitigation_date = idx
                            break
                            
                    fvgs.append({
                        'type': 'Bearish FVG',
                        'date': c2.name,
                        'top': top,
                        'bottom': bottom,
                        'mitigated': mitigated,
                        'mitigation_date': mitigation_date
                    })
                    
        return fvgs
