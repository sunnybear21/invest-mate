import pandas as pd
from lucy_scanner_realtime import LucyScannerRealtime

scanner = LucyScannerRealtime()
# Samsung Electronics
code = '005930'
print("Fetching data...")
df = scanner._get_historical_data(code, days=5)

if df.empty:
    print("DataFrame is empty.")
else:
    print(f"Last row date: {df.index[-1]}")
    print("Last row data:")
    print(df.iloc[-1][['시가', '고가', '저가', '종가', '거래량']])
    print(f"Total rows: {len(df)}")
