# Walk-Forward Validation — S10 / S11 / S16 (Frozen July 2026 Configs)
**Generated:** 2026-07-10 23:08:32 | Window: 60 trading days | Data: ~730d of 1h bars

The July 2026 optimization tuned these strategies on their most recent 60 trading
days. Every earlier window below is **data the frozen configs never saw** — the
closest thing to live evidence that doesn't require waiting.

## S10 VWAP

| Window | Return (60d) | Sharpe | MaxDD | Trades | Win rate | Sample |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 2023-11-20 → 2024-02-15 | -1.01% | -1.68 | -3.24% | 17 | 41% | out-of-sample |
| 2024-02-16 → 2024-05-13 | -4.29% | -1.96 | -6.37% | 15 | 33% | out-of-sample |
| 2024-05-14 → 2024-08-08 | -0.13% | -0.54 | -9.80% | 19 | 47% | out-of-sample |
| 2024-08-09 → 2024-11-01 | -4.03% | -1.87 | -6.49% | 15 | 40% | out-of-sample |
| 2024-11-04 → 2025-01-31 | -2.40% | -1.84 | -4.52% | 11 | 55% | out-of-sample |
| 2025-02-03 → 2025-04-29 | +4.79% | +0.44 | -9.19% | 18 | 56% | out-of-sample |
| 2025-04-30 → 2025-07-25 | +11.18% | +5.56 | -0.03% | 13 | 85% | out-of-sample |
| 2025-07-28 → 2025-10-20 | -2.00% | -1.41 | -5.69% | 16 | 44% | out-of-sample |
| 2025-10-21 → 2026-01-15 | -6.32% | -2.55 | -7.67% | 18 | 33% | out-of-sample |
| 2026-01-16 → 2026-04-14 | +16.52% | +6.53 | -1.57% | 17 | 65% | out-of-sample |
| 2026-04-15 → 2026-07-10 | +6.07% | +1.79 | -2.89% | 16 | 56% | IN-SAMPLE (tuning) |

**Out-of-sample summary (10 windows):** mean +1.23%, median -1.51%, worst -6.32%, best +16.52%, 3/10 positive. In-sample (tuning) window: +6.07%.

## S11 CCI-ADX

| Window | Return (60d) | Sharpe | MaxDD | Trades | Win rate | Sample |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 2023-11-20 → 2024-02-15 | +2.42% | +0.06 | -9.92% | 67 | 51% | out-of-sample |
| 2024-02-16 → 2024-05-13 | +3.46% | +0.54 | -2.98% | 65 | 45% | out-of-sample |
| 2024-05-14 → 2024-08-08 | -9.51% | -2.68 | -11.48% | 71 | 45% | out-of-sample |
| 2024-08-09 → 2024-11-01 | -16.56% | -3.47 | -18.44% | 66 | 39% | out-of-sample |
| 2024-11-04 → 2025-01-31 | -1.73% | -1.01 | -10.21% | 63 | 52% | out-of-sample |
| 2025-02-03 → 2025-04-29 | -17.59% | -1.85 | -22.87% | 60 | 45% | out-of-sample |
| 2025-04-30 → 2025-07-25 | +2.92% | +0.23 | -8.54% | 68 | 49% | out-of-sample |
| 2025-07-28 → 2025-10-20 | -4.64% | -1.80 | -10.03% | 74 | 58% | out-of-sample |
| 2025-10-21 → 2026-01-15 | +0.25% | -0.58 | -9.13% | 60 | 58% | out-of-sample |
| 2026-01-16 → 2026-04-14 | +9.08% | +2.19 | -7.21% | 71 | 55% | out-of-sample |
| 2026-04-15 → 2026-07-10 | +13.95% | +3.54 | -6.58% | 78 | 54% | IN-SAMPLE (tuning) |

**Out-of-sample summary (10 windows):** mean -3.19%, median -0.74%, worst -17.59%, best +9.08%, 5/10 positive. In-sample (tuning) window: +13.95%.

## S16 Router

| Window | Return (60d) | Sharpe | MaxDD | Trades | Win rate | Sample |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 2023-11-20 → 2024-02-15 | +20.08% | +3.08 | -11.80% | 14 | 64% | out-of-sample |
| 2024-02-16 → 2024-05-13 | -14.00% | -2.54 | -17.35% | 18 | 39% | out-of-sample |
| 2024-05-14 → 2024-08-08 | -6.89% | -0.87 | -23.34% | 16 | 62% | out-of-sample |
| 2024-08-09 → 2024-11-01 | +17.21% | +2.79 | -7.58% | 15 | 67% | out-of-sample |
| 2024-11-04 → 2025-01-31 | -7.73% | -1.50 | -17.17% | 16 | 56% | out-of-sample |
| 2025-02-03 → 2025-04-29 | -38.79% | -1.77 | -48.37% | 16 | 44% | out-of-sample |
| 2025-04-30 → 2025-07-25 | +26.74% | +6.69 | -6.11% | 17 | 59% | out-of-sample |
| 2025-07-28 → 2025-10-20 | +6.53% | +1.18 | -4.97% | 17 | 71% | out-of-sample |
| 2025-10-21 → 2026-01-15 | +8.59% | +0.93 | -10.27% | 13 | 54% | out-of-sample |
| 2026-01-16 → 2026-04-14 | -3.13% | -0.35 | -28.23% | 19 | 53% | out-of-sample |
| 2026-04-15 → 2026-07-10 | +60.46% | +12.82 | -10.70% | 18 | 67% | IN-SAMPLE (tuning) |

**Out-of-sample summary (10 windows):** mean +0.86%, median +1.70%, worst -38.79%, best +26.74%, 5/10 positive. In-sample (tuning) window: +60.46%.

## How to read this
- **If out-of-sample windows cluster near the in-sample result**, the edge is
  likely real and the live paper record should confirm it.
- **If the in-sample window is a clear outlier**, the July optimization mostly
  fit noise; expect live performance closer to the out-of-sample mean.
- Same engines, parameters and conventions as the published backtests
  (1h bars, 60d diag-HMM, hybrid 3.0→1.5 ATR stop, 0% commission, Rf 9.5%).
- Caveat: consecutive windows share the same underlying market era (2024-2026
  bull regime dominates); this validates robustness, not all-weather behavior.
