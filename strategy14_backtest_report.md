# Strategy 14: HEDGE - Online Expert Aggregation
**Periodo:** 2007-04-11 a 2026-07-02 | **Modo:** Datos reales | **eta:** 0.054

## Resultado agregado (MXN)
CAGR 15.17% | Vol 10.70% | Sharpe 0.53 | MaxDD -15.19%

## Garantia verificada
* Mejor experto retrospectivo: **TSMOM**
* Regret empirico **0.8163** <= cota teorica **34.2343** (OK)

## Pesos finales del agregador
* CASH_MXN: 15.4%
* QQQ_BH: 17.4%
* VTTL: 17.3%
* CARA: 16.9%
* TSMOM: 17.5%
* CASH_USD: 15.5%

## Nota honesta
La garantia es RELATIVA: cercania al mejor experto en retrospectiva. Si todos
los expertos son malos, HEDGE sera casi tan malo como el menos malo. Su valor
es eliminar el riesgo de eleccion, no crear alpha.
