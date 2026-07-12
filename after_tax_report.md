# After-Tax / Real-Fee Hurdle — What Actually Lands in Your Pocket
**Generated:** 2026-07-11 20:21:19 | Common window: 2022-06-21 → 2026-07-02 | Marginal ISR assumed: 35% | Inflation assumed: 4.2%

> **Not tax advice.** Simplified comparison model — confirm regimes and rates
> with a Mexican contador before moving real money.

## 1. The hurdle, after tax
Bondia pays 6.53% nominal; ISR applies to the *real* component
(nominal − inflation = 2.33%):

| Marginal bracket | After-tax Bondia hurdle |
| :---: | :---: |
| 30% | **5.83%** |
| 35% | **5.71%** |

## 2. Strategies net of real fees and taxes (common window)
Route **SIC** = casa de bolsa mexicana (0.29%/side, **10% definitive ISR on gains**).
Route **US broker** = e.g. Alpaca real (0% commission, gains taxed as ordinary
income at the 35% marginal rate — no 10% regime).

| Strategy | As modeled | +SIC fee drag | **Net (SIC)** | Net (US broker) | Best route | vs hurdle 5.71% |
| :--- | ---: | ---: | ---: | ---: | :---: | :---: |
| S1 Alpha Growth | +38.62% | −0.00% | **+34.76%** | — | SIC | PASS |
| S4 US DCF | +26.25% | −0.00% | **+23.62%** | +17.82% | SIC | PASS |
| S8 Dividends | +17.01% | −0.00% | **+15.31%** | — | SIC | PASS |
| S2 MACD (re-tuned) | +17.42% | −0.91% | **+14.85%** | — | SIC | PASS |
| S12 VTTL | +17.19% | −1.34% | **+14.26%** | +11.36% | SIC | PASS |
| S9 Stat-Arb | +15.47% | −0.00% | **+13.93%** | +13.07% | SIC | PASS |
| S6 High Beta | +11.10% | −0.00% | **+9.99%** | +9.48% | SIC | PASS |
| S14 HEDGE | +11.37% | −0.62% | **+9.67%** | +7.47% | SIC | PASS |
| S15 TRACK | +11.12% | −0.62% | **+9.44%** | +7.31% | SIC | PASS |
| S5 Alternatives | +9.90% | −0.00% | **+8.91%** | +6.81% | SIC | PASS |
| S13 CARA | +10.77% | −4.03% | **+6.07%** | +7.55% | US broker | PASS |

## 3. Findings
- **The 10% BMV/SIC regime dominates.** For every strategy with both routes
  available, executing through a Mexican casa de bolsa nets more after tax than
  a commission-free US broker, because 10% definitive beats 35% marginal by
  far more than 0.29%/side costs at these turnover levels. **Real money should
  trade SIC-listed instruments through a Mexican broker.**
- **High turnover is the silent killer on the SIC route.** The fee drag column
  is `turnover × 2 × (0.29% − modeled fee)`: S13 (8.4× turnover, 5 bps modeled)
  loses ~4% a year to real commissions its backtest never charged; S12–S15's
  cheap cost model flatters them all.
- **Hurdle-passing set (35% bracket): S1 Alpha Growth, S4 US DCF, S8 Dividends, S2 MACD (re-tuned), S12 VTTL, S9 Stat-Arb, S6 High Beta, S14 HEDGE, S15 TRACK, S5 Alternatives, S13 CARA.**
- No strategy fails.
- Intraday sleeves (S10/S11/S16): dozens of round trips per 60 days makes the
  SIC route instantly fatal (S16 v1 already proved −35% at 0.29%/side), and the
  US-broker route taxes whatever remains at 35%. Their walk-forward edge was
  ~0 pre-tax; after tax the case for 0% allocation is even stronger.

## 4. Impact on the target allocation (efficient_frontier_report.md)
- Re-check the hurdle filter with after-tax numbers: membership below.
- Because the SIC tax is a flat 10% of gains, relative rankings barely move;
  the fee-drag adjustment is what reorders S12–S15 (especially S13).

## 5. Model caveats
- Gains tax approximated as `10% × max(annual return, 0)` — ignores the
  inflation-adjusted cost basis (helps you) and loss carryforwards (help you);
  both make reality slightly better than this table.
- Turnover figures are the KPI-table estimates, not measured round trips.
- Dividend strategies (S8) additionally face ~10% withholding on the dividend
  stream itself (~0.3-0.5% extra drag at a 3-5% yield) — not modeled.
- S5 holds crypto ETFs; confirm SIC availability and tax treatment per instrument.
- FX conversion spreads on funding (one-off ~0.3%) not modeled.
