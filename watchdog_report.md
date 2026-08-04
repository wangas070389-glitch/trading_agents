# Watchdog Report - 2026-08-04 16:30:21

**CRITICAL: 9 | WARNING: 2**

| Nivel | Estrategia | Check | Detalle |
| :--- | :--- | :--- | :--- |
| [ OK ] | core | - | NAV $122,056.55 | sin anomalias |
| [ OK ] | alternatives | - | NAV $658,410.22 | sin anomalias |
| [ OK ] | dividends | - | NAV $203,164.26 | sin anomalias |
| [ OK ] | high_beta | - | NAV $102,972.29 | sin anomalias |
| [ OK ] | macd | - | NAV $118,913.53 | sin anomalias |
| [ OK ] | multi_strategy | - | NAV $0.00 | sin anomalias |
| [CRIT] | shadow_frontier | W3 | NAV salto 6.6% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy10 | - | NAV $205,865.95 | sin anomalias |
| [ OK ] | strategy11 | - | NAV $212,090.60 | sin anomalias |
| [ OK ] | strategy12 | - | NAV $204,014.82 | sin anomalias |
| [ OK ] | strategy13 | - | NAV $202,081.82 | sin anomalias |
| [ OK ] | strategy14 | - | NAV $203,110.56 | sin anomalias |
| [ OK ] | strategy15 | - | NAV $203,129.19 | sin anomalias |
| [ OK ] | strategy16 | - | NAV $197,159.16 | sin anomalias |
| [ OK ] | strategy17 | - | NAV $101,000.00 | sin anomalias |
| [CRIT] | strategy18 | W3 | NAV salto 5.8% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy19 | - | NAV $173,962.95 | sin anomalias |
| [ OK ] | strategy20 | - | NAV $188,028.74 | sin anomalias |
| [ OK ] | strategy21 | - | NAV $188,047.39 | sin anomalias |
| [ OK ] | strategy22 | - | NAV $200,000.00 | sin anomalias |
| [ OK ] | strategy23 | - | NAV $218,175.54 | sin anomalias |
| [ OK ] | strategy24 | - | NAV $157,284.73 | sin anomalias |
| [ OK ] | strategy25 | - | NAV $198,250.90 | sin anomalias |
| [WARN] | strategy27 | W2 | [INACTIVE STRATEGY] 15 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy29 | W2 | [INACTIVE STRATEGY] 15 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [ OK ] | strategy30 | - | NAV $101,932.83 | sin anomalias |
| [ OK ] | strategy31 | - | NAV $174,733.09 | sin anomalias |
| [CRIT] | strategy9 | W5 | DD live -8.8% excede 1.25x el MaxDD del backtest (-6.0%): fuera de distribucion validada |
| [ OK ] | us_dcs | - | NAV $104,255.34 | sin anomalias |
| [CRIT] | us_stocks | W4 | Cash negativo: [-78167.83] |
| [CRIT] | us_stocks | W5 | DD live -133.7% excede 1.25x el MaxDD del backtest (-25.1%): fuera de distribucion validada |
| [CRIT] | broker | W6 | Cash de Alpaca NEGATIVO: $-78,167.83 (margen no intencional; probable fill fantasma previo) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AAPL broker=3 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AMZN broker=322 vs ledgers=135.675 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: GOOGL broker=104 vs ledgers=101.073 (firma de SELL fantasma: el broker aun lo tiene) |
