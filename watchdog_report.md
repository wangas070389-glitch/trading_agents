# Watchdog Report - 2026-07-13 01:47:16

**CRITICAL: 6 | WARNING: 2**

| Nivel | Estrategia | Check | Detalle |
| :--- | :--- | :--- | :--- |
| [ OK ] | core | - | NAV $120,775.20 | sin anomalias |
| [ OK ] | alternatives | - | NAV $101,317.45 | sin anomalias |
| [ OK ] | dividends | - | NAV $197,782.69 | sin anomalias |
| [ OK ] | high_beta | - | NAV $101,719.13 | sin anomalias |
| [ OK ] | macd | - | NAV $119,596.28 | sin anomalias |
| [ OK ] | multi_strategy | - | NAV $0.00 | sin anomalias |
| [ OK ] | shadow_frontier | - | NAV $100,039.46 | sin anomalias |
| [WARN] | strategy10 | W2 | Sin trades aun (7/10 dias de gracia) |
| [ OK ] | strategy11 | - | NAV $202,010.14 | sin anomalias |
| [ OK ] | strategy12 | - | NAV $202,232.60 | sin anomalias |
| [ OK ] | strategy13 | - | NAV $202,241.82 | sin anomalias |
| [ OK ] | strategy14 | - | NAV $201,900.71 | sin anomalias |
| [ OK ] | strategy15 | - | NAV $201,893.47 | sin anomalias |
| [WARN] | strategy16 | W2 | Sin trades aun (4/10 dias de gracia) |
| [ OK ] | strategy9 | - | NAV $194,133.33 | sin anomalias |
| [ OK ] | us_dcs | - | NAV $102,216.64 | sin anomalias |
| [CRIT] | us_stocks | W4 | Cash negativo: [-62477.4] |
| [CRIT] | us_stocks | W3 | NAV salto 76.5% en 1d con exposicion 109%: posible bug de contabilidad (tope plausible 39.3%) |
| [CRIT] | us_stocks | W5 | DD live -76.5% excede 1.25x el MaxDD del backtest (-25.1%): fuera de distribucion validada |
| [CRIT] | broker | W6 | Cash de Alpaca NEGATIVO: $-62,477.40 (margen no intencional; probable fill fantasma previo) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: JPM broker=59 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: TSLA broker=47 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
