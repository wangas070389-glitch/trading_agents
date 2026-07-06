# Strategy 12: Vol-Targeted Trend Leverage + MXN Carry (VTTL)
**Periodo:** 2003-12-01 a 2026-07-02 | **Modo:** Datos reales

## Resultados (MXN)
| Metrica | VTTL | QQQ B&H | Bondia |
| :--- | ---: | ---: | ---: |
| CAGR | 17.13% | 17.25% | 6.73% |
| Vol anual | 16.58% | 21.46% | ~0% |
| Sharpe (rf MXN 9.5%) | 0.46 | 0.36 | - |
| Max Drawdown | -21.34% | -41.21% | 0% |

## Validacion estadistica
* PSR (SR*>0): **0.9988** | DSR (N=1): **0.9988**
* Rotacion anual: 2.79x | Costos: 5 bps por notional rotado
* Parametros declarados a priori; rejilla de robustez completa en consola.

## Reglas
1. Trend: exposicion solo si QQQ > SMA(200); si no, 100% Bondia.
2. Vol targeting: exposicion efectiva = min(20%/vol_20d, 1.5x).
3. Implementacion: TQQQ a exposicion/3; capital libre en Bondia (carry MXN).
4. Senal en cierre t aplica al retorno t+1. Banda de rebalanceo 20%.
5. Sin SQQQ, sin HMM, sin parametros ajustados.
