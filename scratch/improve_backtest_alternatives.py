import os
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

# Universe Configuration
CRYPTO = ["BTC-USD", "ETH-USD"]
COMMODITIES = ["GLD", "SLV", "USO", "DBA"]
FOREX = ["EURUSD=X", "GBPUSD=X", "USDMXN=X", "USDJPY=X"]
ALL_TICKERS = CRYPTO + COMMODITIES + FOREX + ["UUP"]

# Sizing & Limits
MAX_CRYPTO_WEIGHT = 0.20
MAX_COMMODITY_WEIGHT = 0.20
MAX_FOREX_WEIGHT = 0.15
MAX_CONCURRENT_POSITIONS = 5
MONTHLY_CONTRIBUTION = 1000.0  # USD
INITIAL_CAPITAL = 100000.0     # USD
TRANSACTION_FEE_RATE = 0.0029  # 0.29% round-trip friction
USD_CASH_YIELD = 0.045         # 4.5% annual cash yield on USD reserves

# 1. Indicator Calculations
def calculate_sma(series: pd.Series, period: int = 200) -> pd.Series:
    return series.rolling(window=period).mean()

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, adjust=False).mean()
    avg_loss = loss.ewm(com=period-1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1.0 + rs.fillna(0)))
    return rsi

def calculate_bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0):
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + (num_std * std)
    lower = middle - (num_std * std)
    return upper, middle, lower

def calculate_donchian_channels(high: pd.Series, low: pd.Series, period: int = 20):
    upper = high.rolling(window=period).max()
    lower = low.rolling(window=period).min()
    return upper, lower

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    up_move = high.diff()
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    # Wilder's smoothing
    atr = tr.ewm(alpha=1.0/period, adjust=False).mean()
    plus_di = 100.0 * pd.Series(plus_dm, index=df.index).ewm(alpha=1.0/period, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100.0 * pd.Series(minus_dm, index=df.index).ewm(alpha=1.0/period, adjust=False).mean() / atr.replace(0, np.nan)
    
    plus_di = plus_di.fillna(0)
    minus_di = minus_di.fillna(0)
    
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    dx = dx.fillna(0)
    adx = dx.ewm(alpha=1.0/period, adjust=False).mean()
    return adx

def evaluate_signals_improved(ticker: str, asset_type: str, df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 200:
        return {"ticker": ticker, "signal": "neutral", "reason": "Insufficient data"}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    
    curr_close = float(close.iloc[-1])
    adx = calculate_adx(df, 14)
    curr_adx = float(adx.iloc[-1])
    
    if asset_type == "crypto":
        # Sma 50 filter
        sma_50 = calculate_sma(close, 50)
        macd, signal = calculate_macd(close)
        
        curr_sma = float(sma_50.iloc[-1])
        curr_macd = float(macd.iloc[-1])
        curr_signal = float(signal.iloc[-1])
        
        prev_macd = float(macd.iloc[-2])
        prev_signal = float(signal.iloc[-2])
        
        trend_bull = curr_close > curr_sma
        macd_cross_up = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
        macd_cross_down = (prev_macd >= prev_signal) and (curr_macd < curr_signal)
        
        if trend_bull and macd_cross_up and curr_adx > 18:
            return {
                "ticker": ticker,
                "signal": "buy",
                "price": curr_close,
                "indicators": {"adx": curr_adx},
                "reason": f"MACD cross up in bull trend (SMA 50) with ADX trend confirmation ({curr_adx:.1f})"
            }
        elif macd_cross_down or not trend_bull:
            return {
                "ticker": ticker,
                "signal": "sell",
                "price": curr_close,
                "indicators": {},
                "reason": "MACD cross down or bearish trend break"
            }
            
    elif asset_type == "commodity":
        # Sma 50 filter
        sma_50 = calculate_sma(close, 50)
        donch_high_20, _ = calculate_donchian_channels(high, low, 20)
        _, donch_low_10 = calculate_donchian_channels(high, low, 10)
        
        curr_sma = float(sma_50.iloc[-1])
        prev_donch_high = float(donch_high_20.iloc[-2])
        prev_donch_low = float(donch_low_10.iloc[-2])
        
        trend_bull = curr_close > curr_sma
        
        if trend_bull and curr_close > prev_donch_high and curr_adx > 20:
            return {
                "ticker": ticker,
                "signal": "buy",
                "price": curr_close,
                "indicators": {"adx": curr_adx},
                "reason": f"Donchian breakout in bull trend (SMA 50) with strong ADX trend ({curr_adx:.1f})"
            }
        elif curr_close < prev_donch_low or not trend_bull:
            return {
                "ticker": ticker,
                "signal": "sell",
                "price": curr_close,
                "indicators": {},
                "reason": "Breakout below 10-day low or bearish trend break"
            }
            
    elif asset_type == "forex":
        upper, middle, lower = calculate_bollinger_bands(close, 20, 2.0)
        rsi = calculate_rsi(close, 14)
        
        curr_upper = float(upper.iloc[-1])
        curr_lower = float(lower.iloc[-1])
        curr_rsi = float(rsi.iloc[-1])
        
        # Forex: require ADX < 25 (ranging) for mean reversion
        if curr_close <= curr_lower and curr_rsi <= 35 and curr_adx < 25:
            return {
                "ticker": ticker,
                "signal": "buy",
                "price": curr_close,
                "indicators": {"adx": curr_adx},
                "reason": f"Oversold (RSI={curr_rsi:.1f}) in ranging market (ADX={curr_adx:.1f})"
            }
        elif curr_close >= curr_upper and curr_rsi >= 65:
            return {
                "ticker": ticker,
                "signal": "sell",
                "price": curr_close,
                "indicators": {},
                "reason": f"Overbought (RSI={curr_rsi:.1f}) at upper Bollinger Band"
            }
            
    return {"ticker": ticker, "signal": "neutral", "reason": "No signals"}

def main():
    print("=" * 80)
    print("STARTING DXY-HEDGED ALTERNATIVE ASSETS STRATEGY SIMULATION")
    print("=" * 80)

    start_date = "2021-06-20"
    end_date = "2026-06-20"
    
    print("Downloading historical data...")
    data = yf.download(ALL_TICKERS, start=start_date, end=end_date, group_by='ticker', progress=False)
    
    valid_tickers = [t for t in ALL_TICKERS if t in data.columns.levels[0] and t != "UUP"]
    aligned_dates = sorted(list(data.index))
    
    # Simulation State
    cash = INITIAL_CAPITAL
    holdings = {}
    trade_log = []
    nav_history = []
    dates_history = []
    
    total_contributed = INITIAL_CAPITAL
    last_month = aligned_dates[0].month

    for i, date in enumerate(aligned_dates):
        if i < 200:
            continue
            
        date_str = date.strftime("%Y-%m-%d")
        
        # 1. Accrue Daily Yield on Cash
        cash *= (1.0 + USD_CASH_YIELD / 252.0)
        
        # 2. Savings DCA Inflow
        if date.month != last_month:
            cash += MONTHLY_CONTRIBUTION
            total_contributed += MONTHLY_CONTRIBUTION
            last_month = date.month
            
        # Calculate DXY (UUP) Trend
        uup_data = data["UUP"].iloc[:i+1].dropna(how='all')
        uup_close = float(uup_data["Close"].iloc[-1])
        uup_sma50 = float(uup_data["Close"].rolling(50).mean().iloc[-1])
        dxy_headwind = uup_close > uup_sma50
        
        # Dynamic Risk Sizing & Caps based on USD trend
        if dxy_headwind:
            # Strong dollar: reduce weights and risk by half
            current_risk_pct = 0.0075
            crypto_cap = MAX_CRYPTO_WEIGHT * 0.5
            commodity_cap = MAX_COMMODITY_WEIGHT * 0.5
            forex_cap = MAX_FOREX_WEIGHT * 0.5
        else:
            # Normal regime
            current_risk_pct = 0.015
            crypto_cap = MAX_CRYPTO_WEIGHT
            commodity_cap = MAX_COMMODITY_WEIGHT
            forex_cap = MAX_FOREX_WEIGHT

        # 3. Calculate portfolio NAV
        current_equity = 0.0
        for ticker, h in list(holdings.items()):
            ticker_data = data[ticker].iloc[:i+1].dropna(how='all')
            curr_close = float(ticker_data["Close"].iloc[-1])
            current_equity += h["shares"] * curr_close
            
            # Update peak price for Crypto
            h["last_price"] = curr_close
            if curr_close > h["peak_price"]:
                h["peak_price"] = curr_close
                unrealized_ret = (curr_close / h["buy_price"]) - 1.0
                # Looser arm condition: 25% profit
                if unrealized_ret >= 0.25:
                    h["armed"] = True
                    
        portfolio_value = cash + current_equity
        nav_history.append(portfolio_value)
        dates_history.append(date)

        # 4. Check exits
        for ticker, h in list(holdings.items()):
            ticker_data = data[ticker].iloc[:i+1].dropna(how='all')
            ticker_data.columns = [c.lower() for c in ticker_data.columns]
            curr_close = float(ticker_data["close"].iloc[-1])
            
            asset_type = h["asset_type"]
            exit_triggered = False
            exit_reason = ""
            
            # A. Trailing Stop (Crypto) - Looser 12% trailing stop
            if asset_type == "crypto" and h["armed"]:
                if curr_close < h["peak_price"] * 0.88:
                    exit_triggered = True
                    exit_reason = f"Enhanced Trailing Stop (Peak: ${h['peak_price']:.2f}, Trigger: ${h['peak_price']*0.88:.2f})"
                    
            # B. Indicator Signals
            if not exit_triggered:
                signal_res = evaluate_signals_improved(ticker, asset_type, ticker_data)
                if signal_res["signal"] == "sell":
                    exit_triggered = True
                    exit_reason = signal_res["reason"]
                    
            if exit_triggered:
                shares_to_sell = h["shares"]
                gross_proceeds = shares_to_sell * curr_close
                fee = gross_proceeds * TRANSACTION_FEE_RATE
                cash += (gross_proceeds - fee)
                
                realized_pnl = gross_proceeds - (shares_to_sell * h["buy_price"])
                pnl_pct = (curr_close / h["buy_price"] - 1.0) * 100.0
                
                trade_log.append({
                    "ticker": ticker,
                    "asset_type": asset_type,
                    "entry_date": h["entry_date"],
                    "exit_date": date_str,
                    "entry_price": h["buy_price"],
                    "exit_price": curr_close,
                    "shares": shares_to_sell,
                    "pnl": realized_pnl,
                    "pnl_pct": pnl_pct,
                    "reason": exit_reason
                })
                del holdings[ticker]

        # 5. Evaluate entries
        if len(holdings) >= MAX_CONCURRENT_POSITIONS:
            continue
            
        candidates = []
        for ticker in valid_tickers:
            if ticker in holdings:
                continue
                
            if ticker in CRYPTO:
                asset_type = "crypto"
            elif ticker in COMMODITIES:
                asset_type = "commodity"
            else:
                asset_type = "forex"
                
            ticker_data = data[ticker].iloc[:i+1].dropna(how='all')
            ticker_data.columns = [c.lower() for c in ticker_data.columns]
            
            signal_res = evaluate_signals_improved(ticker, asset_type, ticker_data)
            if signal_res["signal"] == "buy":
                candidates.append((ticker, asset_type, signal_res, ticker_data))
                
        candidates.sort(key=lambda x: 0 if x[1] == "crypto" else (1 if x[1] == "commodity" else 2))
        
        for ticker, asset_type, sig_res, t_data in candidates:
            if len(holdings) >= MAX_CONCURRENT_POSITIONS:
                break
                
            close_price = sig_res["price"]
            
            # Sizing Cap
            if asset_type == "crypto":
                max_w = crypto_cap
            elif asset_type == "commodity":
                max_w = commodity_cap
            else:
                max_w = forex_cap
                
            # Volatility Sizing (ATR-based Risk Parity)
            atr_series = calculate_atr(t_data, 14)
            curr_atr = float(atr_series.iloc[-1])
            
            # Risk dynamically adjusted
            risk_amt = portfolio_value * current_risk_pct
            stop_dist = 2.5 * curr_atr
            
            if stop_dist > 0:
                target_shares = risk_amt / stop_dist
                target_val = target_shares * close_price
            else:
                target_val = portfolio_value * max_w
                
            target_val = min(target_val, portfolio_value * max_w)
            
            # Check cash buffer
            if target_val > cash:
                target_val = cash * 0.98
                
            shares = int(target_val / (close_price * (1.0 + TRANSACTION_FEE_RATE)))
            if shares > 0:
                cost = shares * close_price
                fee = cost * TRANSACTION_FEE_RATE
                total_cost = cost + fee
                
                cash -= total_cost
                holdings[ticker] = {
                    "shares": shares,
                    "buy_price": close_price,
                    "peak_price": close_price,
                    "armed": False,
                    "target_weight": target_val / portfolio_value,
                    "asset_type": asset_type,
                    "entry_date": date_str
                }

    # Force close at end
    final_date_str = aligned_dates[-1].strftime("%Y-%m-%d")
    final_portfolio_val = cash
    for ticker, h in list(holdings.items()):
        curr_close = float(data[ticker]["Close"].iloc[-1])
        shares_to_sell = h["shares"]
        gross_proceeds = shares_to_sell * curr_close
        fee = gross_proceeds * TRANSACTION_FEE_RATE
        final_portfolio_val += (gross_proceeds - fee)
        
        realized_pnl = gross_proceeds - (shares_to_sell * h["buy_price"])
        pnl_pct = (curr_close / h["buy_price"] - 1.0) * 100.0
        
        trade_log.append({
            "ticker": ticker,
            "asset_type": h["asset_type"],
            "entry_date": h["entry_date"],
            "exit_date": final_date_str,
            "entry_price": h["buy_price"],
            "exit_price": curr_close,
            "shares": shares_to_sell,
            "pnl": realized_pnl,
            "pnl_pct": pnl_pct,
            "reason": "Simulation End Forced Exit"
        })

    # Calculations
    nav_series = pd.Series(nav_history)
    daily_returns = nav_series.pct_change().dropna()
    total_months = len(aligned_dates[200:]) / 21.0
    cagr = ((final_portfolio_val / total_contributed) ** (12.0 / total_months)) - 1.0 if total_contributed > 0 else 0.0
    
    risk_free_daily = USD_CASH_YIELD / 252.0
    excess_returns = daily_returns - risk_free_daily
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0.0
    
    running_max = nav_series.cummax()
    drawdowns = (nav_series - running_max) / running_max
    max_dd = drawdowns.min()
    
    n_trades = len(trade_log)
    win_trades = [t for t in trade_log if t["pnl"] > 0]
    win_rate = (len(win_trades) / n_trades * 100.0) if n_trades > 0 else 0.0

    # Save NAV history to CSV
    nav_df = pd.DataFrame({"Date": dates_history, "NAV": nav_history})
    nav_df.to_csv("alternatives_backtest_nav.csv", index=False)
    print("NAV history saved to alternatives_backtest_nav.csv")

    print("=" * 80)
    print("DXY-HEDGED ALTERNATIVES BACKTEST RESULTS")
    print(f"Final NAV: ${final_portfolio_val:,.2f} USD")
    print(f"CAGR (TWR): {cagr*100:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Total Trades: {n_trades}")
    print(f"Win Rate: {win_rate:.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    main()
