# Watchdog Report - 2026-07-28 16:21:17

**CRITICAL: 10 | WARNING: 3**

| Nivel | Estrategia | Check | Detalle |
| :--- | :--- | :--- | :--- |
| [ OK ] | core | - | NAV $122,547.20 | sin anomalias |
| [ OK ] | alternatives | - | NAV $201,554.29 | sin anomalias |
| [ OK ] | dividends | - | NAV $206,992.33 | sin anomalias |
| [ OK ] | high_beta | - | NAV $100,537.97 | sin anomalias |
| [ OK ] | macd | - | NAV $119,956.62 | sin anomalias |
| [ OK ] | multi_strategy | - | NAV $0.00 | sin anomalias |
| [CRIT] | shadow_frontier | W3 | NAV salto 25.0% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy10 | - | NAV $203,610.45 | sin anomalias |
| [ OK ] | strategy11 | - | NAV $208,122.64 | sin anomalias |
| [ OK ] | strategy12 | - | NAV $192,596.87 | sin anomalias |
| [ OK ] | strategy13 | - | NAV $192,614.39 | sin anomalias |
| [ OK ] | strategy14 | - | NAV $194,758.00 | sin anomalias |
| [ OK ] | strategy15 | - | NAV $194,762.98 | sin anomalias |
| [ OK ] | strategy16 | - | NAV $193,341.13 | sin anomalias |
| [ OK ] | strategy17 | - | NAV $100,000.00 | sin anomalias |
| [CRIT] | strategy18 | W3 | NAV salto 24.9% en 1d con exposicion 0%: posible bug de contabilidad (tope plausible 3.0%) |
| [ OK ] | strategy19 | - | NAV $185,458.13 | sin anomalias |
| [ OK ] | strategy20 | - | NAV $160,373.00 | sin anomalias |
| [ OK ] | strategy21 | - | NAV $160,388.49 | sin anomalias |
| [ OK ] | strategy22 | - | NAV $200,000.00 | sin anomalias |
| [ OK ] | strategy23 | - | NAV $186,234.80 | sin anomalias |
| [ OK ] | strategy24 | - | NAV $191,037.52 | sin anomalias |
| [ OK ] | strategy25 | - | NAV $198,002.76 | sin anomalias |
| [WARN] | strategy27 | W2 | [INACTIVE STRATEGY] 10 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy29 | W2 | [INACTIVE STRATEGY] 10 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [WARN] | strategy30 | W2 | [INACTIVE STRATEGY] 10 dias habiles vivos y CERO trades (solo interes): logica de entrada muerta? |
| [ OK ] | strategy31 | - | NAV $180,421.02 | sin anomalias |
| [ OK ] | strategy9 | - | NAV $183,250.94 | sin anomalias |
| [ OK ] | us_dcs | - | NAV $101,095.39 | sin anomalias |
| [CRIT] | us_stocks | W4 | Cash negativo: [-92103.18] |
| [CRIT] | us_stocks | W3 | NAV salto 178.6% en 1d con exposicion 135%: posible bug de contabilidad (tope plausible 48.6%) |
| [CRIT] | us_stocks | W5 | DD live -133.7% excede 1.25x el MaxDD del backtest (-25.1%): fuera de distribucion validada |
| [CRIT] | broker | W6 | Cash de Alpaca NEGATIVO: $-92,103.18 (margen no intencional; probable fill fantasma previo) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AAPL broker=62 vs ledgers=59 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AMZN broker=253 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: AVGO broker=166 vs ledgers=115 (firma de SELL fantasma: el broker aun lo tiene) |
| [CRIT] | broker | W6 | HUERFANO en Alpaca: GOOGL broker=54 vs ledgers=0 (firma de SELL fantasma: el broker aun lo tiene) |
