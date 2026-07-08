# Strategy 16 Experiment Findings (2026-07-07)

Backtest window: 2026-04-10 to 2026-07-07 (60 trading days), 200,000 MXN initial, 0.29% fee per side.

## Variants tested

| Variant | Universe | Alloc | Trail stop | Extras | Return | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|
| Baseline (committed) | QQQ/SPY/SOXX/IWM | 90% | 1.5 ATR | — | -35.81% | -6.70 | -36.52% |
| Inverse/contrarian (scratch) | QQQ/SPY/SOXX/IWM | 90% | 1.5 ATR | Fade HMM regime | -43.51% | -5.71 | -43.51% |
| Confidence gate | QQQ/SPY | 90% bull / 50% bear+chop | 1.5 ATR | Skip days with HMM score < 0.05 | -19.88% | -4.21 | -19.88% |
| + wider stop & trade cap | QQQ/SPY | 90% bull / 50% bear+chop | 3.0 ATR | + max 1 trade/day | -16.75% | -3.48 | -18.11% |

## Trade-level diagnostics (confidence-gate variant, 41 trades)

- All 41 trades were BULL_TREND entries (TQQQ/UPRO pullback buys). The QQQ/SPY HMM
  never routed to bear/chop trades in this window.
- By exit reason:
  - CCI-settle (labeled VWAP_REVERSION): 18 trades, 72% win rate, +24,031 MXN — the signal core works.
  - Trailing stop (1.5 ATR): 14 trades, **0% win rate**, -53,676 MXN — pure loss engine.
  - EOD liquidation: 9 trades, -10,114 MXN.
- Estimated fees: ~38,652 MXN vs total loss of 39,759 MXN → the strategy was roughly
  **breakeven gross; fees consumed everything**.

With the 3.0 ATR stop + 1 trade/day cap (26 trades): fees drop to ~25,125 MXN but gross
PnL turns negative (≈ -8,400 MXN) — the two stop-outs that still fire lose ~12,300 MXN each,
and the surviving reversion trades lose their edge (win rate 44% vs 72%).

## Follow-up: S16 v2 prototype (HMM router + S10 engine) — 2026-07-07

Hypothesis tested: S16's fee assumption (0.29%/side, Mexican broker) was the structural
killer, since S10/S11 run the same style of intraday leveraged trades at Alpaca 0%.

- Zero-fee control run of the tuned S16 (CCI entries): -4.66% — confirms fees were most
  of the bleed; remaining loss was 2 trailing-stop hits.
- Prototype `scratch/backtest_s16_s10style.py`: S10's exact engine (VWAP band breakout in
  trends, chop reversion with VWAP settle, 1.5 ATR trail, conditional overnight holds,
  0% commission, sweep interest) + S16's 4-asset HMM router (locked to any asset held
  overnight; all-chop fallback uses ATR% not absolute ATR).

**Result: +20.38% (60d), CAGR +116%, Sharpe 3.37, MaxDD -10.12%** — vs S10 standalone
+10.83%, Sharpe 2.73, MaxDD -4.14% on the same window. Router chose SOXX 30d, QQQ 24d,
IWM 6d, SPY 0d. Bull breakouts: 8 trades, 75% win, +38,977. VWAP settles: 100% win.

Caveats before adopting:
- **+40,287 of the +40,398 total PnL came from 6 overnight-held trades** — the edge is
  concentrated in overnight gap capture on 3x ETFs, which is also the biggest risk.
- Trailing stops remain 0% win rate (-23,774 across 2 hits).
- Same 60-day window S10 was tuned on; 21 trades is a small sample. Validate on 1h bars
  over a longer period (yfinance caps 30m data at 60d) before wiring into live.
- Doubles overnight leveraged exposure alongside S10 when both hold the same direction.

## Conclusions

1. **Fees are structurally fatal.** At 0.29% per side, a round trip of ~90% NAV costs
   ~0.5% of NAV. An intraday scalper needs >0.5% gross edge *per trade* just to break even.
   No configuration tested comes close.
2. **The tight trailing stop on 3x ETFs never wins.** 1.5 ATR on 30-minute bars of a 3x
   leveraged ETF stops out on noise with a 0% win rate. Widening it trades many small
   guaranteed losses for a few catastrophic ones — net effect roughly neutral.
3. **The entry signal (CCI < -100 + ADX > 20 pullback buy, settle at CCI 0) shows real
   edge only when allowed to complete** (72% win rate), but its ~0.9% average net gain
   cannot pay for the stop-outs and EOD liquidations that accompany it.
4. **Recommendation:** do not keep tuning intraday parameters — the 60-day sample is
   already being overfit. Either (a) pause/retire S16, or (b) redesign it as a multi-day
   holder (enter on the same HMM+pullback signal, hold until regime flip or a wide daily
   ATR stop) so each fee event is amortized over a multi-day move instead of a scalp.
