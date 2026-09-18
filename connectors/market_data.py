"""
MARKET DATA CONNECTOR: Alpaca primero, yfinance como fallback.
La fuente primaria es el mismo broker que ejecuta -> elimina la clase de
bugs 'yfinance devolvio datos parciales'. Requiere APCA_API_KEY_ID y
APCA_API_SECRET_KEY en el entorno; sin ellas cae a yfinance con aviso.

Uso (drop-in para los runners):
    from connectors.market_data import get_daily_closes
    qqq = get_daily_closes("QQQ", days=750)   # pd.Series indexada por fecha
"""
import os
import datetime
import pandas as pd
import requests

ALPACA_DATA_URL = "https://data.alpaca.markets/v2/stocks/{sym}/bars"
_HEADERS = None


def _headers():
    global _HEADERS
    if _HEADERS is None:
        k, s = os.environ.get("APCA_API_KEY_ID"), os.environ.get("APCA_API_SECRET_KEY")
        _HEADERS = {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s} if k and s else {}
    return _HEADERS


def _alpaca_daily(symbol: str, days: int) -> pd.Series:
    if not _headers():
        raise RuntimeError("sin credenciales APCA en entorno")
    start = (datetime.datetime.utcnow() - datetime.timedelta(days=int(days * 1.6))).strftime("%Y-%m-%dT00:00:00Z")
    bars, token = [], None
    for _ in range(10):
        params = {"timeframe": "1Day", "start": start, "limit": 10000,
                  "adjustment": "split", "feed": "iex"}
        if token:
            params["page_token"] = token
        r = requests.get(ALPACA_DATA_URL.format(sym=symbol), headers=_headers(), params=params, timeout=20)
        r.raise_for_status()
        js = r.json()
        bars.extend(js.get("bars") or [])
        token = js.get("next_page_token")
        if not token:
            break
    if not bars:
        raise RuntimeError(f"Alpaca sin barras para {symbol}")
    idx = pd.to_datetime([b["t"] for b in bars]).tz_localize(None).normalize()
    return pd.Series([float(b["c"]) for b in bars], index=idx, name=symbol).tail(days)


def _yf_daily(symbol: str, days: int) -> pd.Series:
    import yfinance as yf
    df = yf.download(symbol, period=f"{max(days + 30, 60)}d", interval="1d",
                     progress=False, auto_adjust=True)
    if df.empty:
        raise RuntimeError(f"yfinance sin datos para {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    s = df["Close"]
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    return s.tail(days).rename(symbol)


def get_vix3m(days: int = 500, vix_series: pd.Series = None) -> pd.Series:
    """Cierres diarios de VIX3M (3-Month Volatility Index).
    Yahoo Finance ^VIX3M frecuentemente trunca su historial a 1 sola barra.
    Esta funcion usa CBOE CDN directo -> FRED VXVCLS -> yfinance (si >=20 barras) -> proxy sintetico."""
    import io
    import urllib.request

    # 1. CBOE CDN official daily prices
    try:
        url = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            df = pd.read_csv(io.StringIO(resp.read().decode("utf-8")))
        df["Date"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y")
        s = pd.to_numeric(df.set_index("Date").sort_index()["CLOSE"], errors="coerce").dropna()
        if len(s) >= 20:
            return s.tail(days).rename("^VIX3M")
    except Exception as e:
        print(f"[market_data] CBOE CDN fallo para VIX3M ({e}); intentando FRED.")

    # 2. FRED St. Louis Fed (VXVCLS)
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VXVCLS"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            df = pd.read_csv(io.StringIO(resp.read().decode("utf-8")), index_col=0, parse_dates=True)
        s = pd.to_numeric(df["VXVCLS"], errors="coerce").dropna()
        if len(s) >= 20:
            return s.tail(days).rename("^VIX3M")
    except Exception as e:
        print(f"[market_data] FRED fallo para VXVCLS ({e}); intentando yfinance.")

    # 3. Yahoo Finance ^VIX3M (solo si entrega historial valido)
    try:
        import yfinance as yf
        df = yf.download("^VIX3M", period=f"{max(days + 30, 60)}d", interval="1d",
                         progress=False, auto_adjust=True)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            s = df["Close"].dropna()
            if s.index.tz is not None:
                s.index = s.index.tz_localize(None)
            if len(s) >= 20:
                return s.tail(days).rename("^VIX3M")
    except Exception as e:
        print(f"[market_data] yfinance fallo para ^VIX3M ({e}).")

    # 4. Fallback matematico: Proxy de estructura temporal (SMA40 de VIX * 1.05)
    # Identico al proxy de referencia usado en el diseno y backtests de Strategy 13, 14, 15
    print("[market_data] AVISO: Usando proxy sintetico de VIX3M (SMA40 VIX * 1.05).")
    if vix_series is None or len(vix_series) == 0:
        try:
            vix_series = _yf_daily("^VIX", days=max(days, 100))
        except Exception:
            pass
    if vix_series is not None and len(vix_series) > 0:
        proxy = vix_series.rolling(40, min_periods=1).mean() * 1.05
        return proxy.tail(days).rename("^VIX3M")

    raise RuntimeError("Imposible obtener VIX3M ni proxy de VIX desde ninguna fuente.")


def get_daily_closes(symbol: str, days: int = 500) -> pd.Series:
    """Cierres diarios ajustados. Alpaca -> fallback yfinance.
    Indices/FX (^VIX, MXN=X) van directo a yfinance (Alpaca no los sirve).
    VIX3M usa proveedor multi-fuente resiliente."""
    if symbol in ("^VIX3M", "VIX3M", "^VXV"):
        return get_vix3m(days)
    if symbol.startswith("^") or "=" in symbol or symbol.endswith(".MX"):
        return _yf_daily(symbol, days)
    try:
        return _alpaca_daily(symbol, days)
    except Exception as e:
        print(f"[market_data] Alpaca fallo para {symbol} ({e}); usando yfinance.")
        return _yf_daily(symbol, days)

