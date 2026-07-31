# Watchdog Report - 2026-07-31 16:20:44

**CRITICAL: 9 | WARNING: 2**

| Nivel | Estrategia | Check | Detalle |
| :--- | :--- | :--- | :--- |
| [ OK ] | core | - | NAV $122,335.58 | sin anomalias |
| [ OK ] | alternatives | - | NAV $521,518.58 | sin anomalias |
| [ OK ] | dividends | - | NAV $202,632.85 | sin anomalias |
| [ OK ] | high_beta | - | NAV $100,387.95 | sin anomalias |
| [ OK ] | macd | - | NAV $118,839.74 | sin anomalias |
| [ OK ] | multi_strategy | - | NAV $0.00 | sin anomalias |
| [CRIT] | shadow_frontier | W3 | NAV salto 10.8% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy10 | - | NAV $203,719.65 | sin anomalias |
| [ OK ] | strategy11 | - | NAV $207,899.38 | sin anomalias |
| [ OK ] | strategy12 | - | NAV $193,660.53 | sin anomalias |
| [ OK ] | strategy13 | - | NAV $191,976.13 | sin anomalias |
| [ OK ] | strategy14 | - | NAV $195,364.23 | sin anomalias |
| [ OK ] | strategy15 | - | NAV $195,372.50 | sin anomalias |
| [ OK ] | strategy16 | - | NAV $195,018.46 | sin anomalias |
| [ OK ] | strategy17 | - | NAV $100,000.00 | sin anomalias |
| [CRIT] | strategy18 | W3 | NAV salto 10.8% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy19 | - | NAV $166,088.10 | sin anomalias |
| [ OK ] | strategy20 | - | NAV $163,404.96 | sin anomalias |
| [ OK ] | strategy21 | - | NAV $163,357.03 | sin anomalias |
| [ OK ] | strategy22 | - | NAV $200,000.00 | sin anomalias |
| [ OK ] | strategy23 | - | NAV $189,700.20 | sin anomalias |
| [ OK ] | strategy24 | - | NAV $168,412.95 | sin anomalias |
| [ OK ] | strategy25 | - | NAV $198,108.94 | sin anomalias |
| [WARN] | strategy27 | W2 | [INACTIVE STRATEGY] 13 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy29 | W2 | [INACTIVE STRATEGY] 13 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [ OK ] | strategy30 | - | NAV $100,202.74 | sin anomalias |
| [ OK ] | strategy31 | - | NAV $174,733.09 | sin anomalias |
| [CRIT] | strategy9 | W5 | DD live -8.8% excede 1.25x el MaxDD del backtest (-6.0%): fuera de distribucion validada |
| [ OK ] | us_dcs | - | NAV $101,250.74 | sin anomalias |
| [CRIT] | us_stocks | W4 | Cash negativo: [-104039.03] |
| [CRIT] | us_stocks | W5 | DD live -133.7% excede 1.25x el MaxDD del backtest (-25.1%): fuera de distribucion validada |
| [CRIT] | broker | W6 | Cash de Alpaca NEGATIVO: $-104,039.03 (margen no intencional; probable fill fantasma previo) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AAPL broker=3 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AMZN broker=347 vs ledgers=160.675 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: GOOGL broker=125 vs ledgers=122.073 (firma de SELL fantasma: el broker aun lo tiene) |
