# Strategy 15: TRACK - Fixed-Share Expert Tracking
**Periodo:** 2007-04-11 a 2026-07-02 | **Modo:** Datos reales
**alpha:** 1/252 | **eta:** 0.054

## TRACK vs HEDGE (mismos datos, mismos expertos)
| Metrica | TRACK | HEDGE (S14) |
| :--- | ---: | ---: |
| CAGR | 15.05% | 15.15% |
| Sharpe | 0.53 | 0.53 |
| MaxDD | -14.73% | -15.19% |
| Regret vs mejor estatico | 0.837 | 0.819 |
| Regret vs mejor secuencia anual | 2.525 | 2.508 |

## Pesos finales
* CASH_MXN: 16.6%
* QQQ_BH: 16.7%
* VTTL: 16.7%
* CARA: 16.7%
* TSMOM: 16.7%
* CASH_USD: 16.5%

## Nota honesta
TRACK paga una prima pequena y permanente (el alpha redistribuido) a cambio de
adaptabilidad ante cambios de regimen. En un mundo SIN cambios de liderazgo,
HEDGE gana por esa prima. La eleccion entre S14 y S15 es una apuesta sobre la
frecuencia de rotacion de regimen, no sobre cual es "mejor" en abstracto.
