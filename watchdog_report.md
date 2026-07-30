# Watchdog Report - 2026-07-30 16:10:14

**CRITICAL: 10 | WARNING: 3**

| Nivel | Estrategia | Check | Detalle |
| :--- | :--- | :--- | :--- |
| [ OK ] | core | - | NAV $122,480.25 | sin anomalias |
| [ OK ] | alternatives | - | NAV $441,246.16 | sin anomalias |
| [ OK ] | dividends | - | NAV $203,544.28 | sin anomalias |
| [ OK ] | high_beta | - | NAV $100,480.07 | sin anomalias |
| [ OK ] | macd | - | NAV $117,897.13 | sin anomalias |
| [ OK ] | multi_strategy | - | NAV $0.00 | sin anomalias |
| [CRIT] | shadow_frontier | W3 | NAV salto 20.1% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy10 | - | NAV $203,682.97 | sin anomalias |
| [ OK ] | strategy11 | - | NAV $207,774.15 | sin anomalias |
| [ OK ] | strategy12 | - | NAV $192,868.51 | sin anomalias |
| [ OK ] | strategy13 | - | NAV $191,326.12 | sin anomalias |
| [ OK ] | strategy14 | - | NAV $194,828.21 | sin anomalias |
| [ OK ] | strategy15 | - | NAV $194,818.36 | sin anomalias |
| [ OK ] | strategy16 | - | NAV $194,983.35 | sin anomalias |
| [ OK ] | strategy17 | - | NAV $100,000.00 | sin anomalias |
| [CRIT] | strategy18 | W3 | NAV salto 19.5% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy19 | - | NAV $166,209.87 | sin anomalias |
| [ OK ] | strategy20 | - | NAV $161,055.81 | sin anomalias |
| [ OK ] | strategy21 | - | NAV $161,031.39 | sin anomalias |
| [ OK ] | strategy22 | - | NAV $200,000.00 | sin anomalias |
| [ OK ] | strategy23 | - | NAV $186,984.64 | sin anomalias |
| [ OK ] | strategy24 | - | NAV $171,531.41 | sin anomalias |
| [ OK ] | strategy25 | - | NAV $198,073.28 | sin anomalias |
| [WARN] | strategy27 | W2 | [INACTIVE STRATEGY] 12 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy29 | W2 | [INACTIVE STRATEGY] 12 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy30 | W2 | [INACTIVE STRATEGY] 12 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [ OK ] | strategy31 | - | NAV $174,733.09 | sin anomalias |
| [CRIT] | strategy9 | W5 | DD live -8.8% excede 1.25x el MaxDD del backtest (-6.0%): fuera de distribucion validada |
| [ OK ] | us_dcs | - | NAV $101,363.52 | sin anomalias |
| [CRIT] | us_stocks | W4 | Cash negativo: [-51592.28] |
| [CRIT] | us_stocks | W3 | NAV salto 141.1% en 1d con exposicion 138%: posible bug de contabilidad (tope plausible 49.8%) |
| [CRIT] | us_stocks | W5 | DD live -133.7% excede 1.25x el MaxDD del backtest (-25.1%): fuera de distribucion validada |
| [CRIT] | broker | W6 | Cash de Alpaca NEGATIVO: $-71,324.73 (margen no intencional; probable fill fantasma previo) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AAPL broker=62 vs ledgers=59 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AMZN broker=253 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: GOOGL broker=54 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
