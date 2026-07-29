# Watchdog Report - 2026-07-29 20:32:05

**CRITICAL: 9 | WARNING: 3**

| Nivel | Estrategia | Check | Detalle |
| :--- | :--- | :--- | :--- |
| [ OK ] | core | - | NAV $122,282.68 | sin anomalias |
| [ OK ] | alternatives | - | NAV $381,208.26 | sin anomalias |
| [ OK ] | dividends | - | NAV $203,083.61 | sin anomalias |
| [ OK ] | high_beta | - | NAV $100,537.97 | sin anomalias |
| [ OK ] | macd | - | NAV $117,827.60 | sin anomalias |
| [ OK ] | multi_strategy | - | NAV $0.00 | sin anomalias |
| [ OK ] | shadow_frontier | - | NAV $152,426.63 | sin anomalias |
| [ OK ] | strategy10 | - | NAV $203,651.25 | sin anomalias |
| [ OK ] | strategy11 | - | NAV $207,743.76 | sin anomalias |
| [ OK ] | strategy12 | - | NAV $188,846.17 | sin anomalias |
| [ OK ] | strategy13 | - | NAV $188,856.01 | sin anomalias |
| [ OK ] | strategy14 | - | NAV $192,227.24 | sin anomalias |
| [ OK ] | strategy15 | - | NAV $192,223.92 | sin anomalias |
| [ OK ] | strategy16 | - | NAV $192,248.45 | sin anomalias |
| [ OK ] | strategy17 | - | NAV $100,000.00 | sin anomalias |
| [ OK ] | strategy18 | - | NAV $152,574.73 | sin anomalias |
| [CRIT] | strategy19 | W3 | NAV salto 6.0% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy20 | - | NAV $149,044.65 | sin anomalias |
| [ OK ] | strategy21 | - | NAV $149,070.71 | sin anomalias |
| [ OK ] | strategy22 | - | NAV $200,000.00 | sin anomalias |
| [ OK ] | strategy23 | - | NAV $173,092.20 | sin anomalias |
| [ OK ] | strategy24 | - | NAV $189,731.36 | sin anomalias |
| [ OK ] | strategy25 | - | NAV $198,044.31 | sin anomalias |
| [WARN] | strategy27 | W2 | [INACTIVE STRATEGY] 11 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy29 | W2 | [INACTIVE STRATEGY] 11 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy30 | W2 | [INACTIVE STRATEGY] 11 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [ OK ] | strategy31 | - | NAV $176,829.04 | sin anomalias |
| [CRIT] | strategy9 | W5 | DD live -8.4% excede 1.25x el MaxDD del backtest (-6.0%): fuera de distribucion validada |
| [ OK ] | us_dcs | - | NAV $100,289.39 | sin anomalias |
| [CRIT] | us_stocks | W4 | Cash negativo: [-95710.67] |
| [CRIT] | us_stocks | W5 | DD live -133.7% excede 1.25x el MaxDD del backtest (-25.1%): fuera de distribucion validada |
| [CRIT] | broker | W6 | Cash de Alpaca NEGATIVO: $-95,710.67 (margen no intencional; probable fill fantasma previo) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AAPL broker=62 vs ledgers=59 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AMZN broker=253 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AVGO broker=175 vs ledgers=124 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: GOOGL broker=54 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
