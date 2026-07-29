# Watchdog Report - 2026-07-29 16:05:57

**CRITICAL: 10 | WARNING: 3**

| Nivel | Estrategia | Check | Detalle |
| :--- | :--- | :--- | :--- |
| [ OK ] | core | - | NAV $122,274.91 | sin anomalias |
| [ OK ] | alternatives | - | NAV $320,922.38 | sin anomalias |
| [ OK ] | dividends | - | NAV $203,905.33 | sin anomalias |
| [ OK ] | high_beta | - | NAV $100,537.97 | sin anomalias |
| [ OK ] | macd | - | NAV $118,150.55 | sin anomalias |
| [ OK ] | multi_strategy | - | NAV $0.00 | sin anomalias |
| [CRIT] | shadow_frontier | W3 | NAV salto 23.0% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy10 | - | NAV $203,646.46 | sin anomalias |
| [ OK ] | strategy11 | - | NAV $208,159.47 | sin anomalias |
| [ OK ] | strategy12 | - | NAV $189,581.47 | sin anomalias |
| [ OK ] | strategy13 | - | NAV $189,591.30 | sin anomalias |
| [ OK ] | strategy14 | - | NAV $192,819.21 | sin anomalias |
| [ OK ] | strategy15 | - | NAV $192,829.61 | sin anomalias |
| [ OK ] | strategy16 | - | NAV $193,375.34 | sin anomalias |
| [ OK ] | strategy17 | - | NAV $100,000.00 | sin anomalias |
| [CRIT] | strategy18 | W3 | NAV salto 23.7% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy19 | - | NAV $179,121.52 | sin anomalias |
| [ OK ] | strategy20 | - | NAV $150,941.42 | sin anomalias |
| [ OK ] | strategy21 | - | NAV $150,967.82 | sin anomalias |
| [ OK ] | strategy22 | - | NAV $200,000.00 | sin anomalias |
| [ OK ] | strategy23 | - | NAV $175,316.03 | sin anomalias |
| [ OK ] | strategy24 | - | NAV $179,998.47 | sin anomalias |
| [ OK ] | strategy25 | - | NAV $198,037.77 | sin anomalias |
| [WARN] | strategy27 | W2 | [INACTIVE STRATEGY] 11 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy29 | W2 | [INACTIVE STRATEGY] 11 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy30 | W2 | [INACTIVE STRATEGY] 11 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [ OK ] | strategy31 | - | NAV $174,541.17 | sin anomalias |
| [CRIT] | strategy9 | W5 | DD live -8.4% excede 1.25x el MaxDD del backtest (-6.0%): fuera de distribucion validada |
| [ OK ] | us_dcs | - | NAV $100,266.97 | sin anomalias |
| [CRIT] | us_stocks | W4 | Cash negativo: [-92103.22] |
| [CRIT] | us_stocks | W5 | DD live -133.7% excede 1.25x el MaxDD del backtest (-25.1%): fuera de distribucion validada |
| [CRIT] | broker | W6 | Cash de Alpaca NEGATIVO: $-92,103.22 (margen no intencional; probable fill fantasma previo) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AAPL broker=62 vs ledgers=59 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AMZN broker=253 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AVGO broker=166 vs ledgers=115 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: GOOGL broker=54 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
