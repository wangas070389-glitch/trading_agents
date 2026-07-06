# Strategy 13: CARA - Cross-Asset Risk Appetite
**Periodo:** 2007-04-11 a 2026-07-02 | **Modo:** Datos reales

## Resultados (MXN)
| Metrica | CARA | QQQ B&H |
| :--- | ---: | ---: |
| CAGR | 15.95% | 19.35% |
| Vol anual | 14.22% | 22.35% |
| Sharpe (rf 9.5% MXN) | 0.45 | 0.44 |
| Max Drawdown | -25.02% | -41.21% |

## Validacion
* PSR: **0.9976** | DSR (N=1): **0.9976** | Rotacion: 8.39x/anio
* Tiempo score 3 / 2 / <=1: 53% / 26% / 21%

## Reglas
1. Voto 1: VIX3M > VIX (contango). Voto 2: HYG/IEF > SMA(60). Voto 3: QQQ > SMA(100).
2. Score 3 -> min(20%/vol20d, 1.5x) via TQQQ/3. Score 2 -> mitad. Score <=1 -> 0 equity.
3. Score <=1 activa hedge: 35% del cash a USD (tasa USD + USDMXN).
4. Senal cierre t -> retorno t+1. Banda de rebalanceo 20%. Costos 5/2 bps.
