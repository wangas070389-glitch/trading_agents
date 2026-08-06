# Watchdog Report - 2026-08-06 04:47:14

**CRITICAL: 13 | WARNING: 2**

| Nivel | Estrategia | Check | Detalle |
| :--- | :--- | :--- | :--- |
| [ OK ] | core | - | NAV $121,802.30 | sin anomalias |
| [CRIT] | alternatives | W5 | DD live -84.5% excede 1.25x el MaxDD del backtest (-7.1%): fuera de distribucion validada |
| [ OK ] | dividends | - | NAV $203,126.49 | sin anomalias |
| [ OK ] | high_beta | - | NAV $103,099.76 | sin anomalias |
| [ OK ] | macd | - | NAV $117,871.35 | sin anomalias |
| [ OK ] | multi_strategy | - | NAV $0.00 | sin anomalias |
| [ OK ] | shadow_frontier | - | NAV $208,565.18 | sin anomalias |
| [CRIT] | strategy10 | W1 | Sin actualizar desde 2026-08-04 23:17:19 (2 dias habiles): cron muerto o script crasheando |
| [ OK ] | strategy11 | - | NAV $212,849.77 | sin anomalias |
| [ OK ] | strategy12 | - | NAV $203,583.96 | sin anomalias |
| [ OK ] | strategy13 | - | NAV $201,626.27 | sin anomalias |
| [CRIT] | strategy14 | W3 | NAV salto 15.9% en 1d con exposicion 18%: posible bug de contabilidad (tope plausible 6.5%) |
| [CRIT] | strategy15 | W3 | NAV salto 15.9% en 1d con exposicion 18%: posible bug de contabilidad (tope plausible 6.5%) |
| [ OK ] | strategy16 | - | NAV $197,210.93 | sin anomalias |
| [ OK ] | strategy17 | - | NAV $101,000.00 | sin anomalias |
| [ OK ] | strategy18 | - | NAV $103,875.98 | sin anomalias |
| [ OK ] | strategy19 | - | NAV $173,150.09 | sin anomalias |
| [ OK ] | strategy20 | - | NAV $185,586.40 | sin anomalias |
| [ OK ] | strategy21 | - | NAV $185,600.54 | sin anomalias |
| [ OK ] | strategy22 | - | NAV $200,000.00 | sin anomalias |
| [ OK ] | strategy23 | - | NAV $214,905.69 | sin anomalias |
| [ OK ] | strategy24 | - | NAV $157,326.01 | sin anomalias |
| [ OK ] | strategy25 | - | NAV $198,302.96 | sin anomalias |
| [WARN] | strategy27 | W2 | [INACTIVE STRATEGY] 26 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy29 | W2 | [INACTIVE STRATEGY] 26 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [ OK ] | strategy30 | - | NAV $101,654.75 | sin anomalias |
| [ OK ] | strategy31 | - | NAV $174,733.09 | sin anomalias |
| [CRIT] | strategy9 | W5 | DD live -8.8% excede 1.25x el MaxDD del backtest (-6.0%): fuera de distribucion validada |
| [ OK ] | us_dcs | - | NAV $104,320.17 | sin anomalias |
| [CRIT] | us_stocks | W4 | Cash negativo: [-78825.85] |
| [CRIT] | us_stocks | W5 | DD live -139.6% excede 1.25x el MaxDD del backtest (-25.1%): fuera de distribucion validada |
| [CRIT] | broker | W6 | Cash de Alpaca NEGATIVO: $-78,825.85 (margen no intencional; probable fill fantasma previo) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AAPL broker=3 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AMZN broker=322 vs ledgers=68.6745 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AVGO broker=96 vs ledgers=51.6073 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: GOOGL broker=104 vs ledgers=52.0731 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: MSFT broker=38 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
