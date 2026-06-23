import pandas as pd
try:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IRLTLT01MXM156N"
    df = pd.read_csv(url, parse_dates=['DATE'], index_col='DATE')
    print("Success! Head of data:")
    print(df.head())
    print("Tail of data:")
    print(df.tail())
except Exception as e:
    print(f"Error: {e}")
