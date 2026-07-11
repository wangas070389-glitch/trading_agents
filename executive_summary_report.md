# Informe Ejecutivo Completo: Estrategias, Matemáticas y Plan de Inversión (DCA)

Este documento detalla la totalidad del ecosistema de trading algorítmico, incluyendo el análisis de las 15 estrategias del repositorio, sus activos subyacentes, métricas esperadas, supuestos operativos y un plan financiero detallado (hoja de ruta de aportes) para su implementación práctica.

---

## 1. Catálogo Completo de Estrategias y Activos

A continuación se detallan las 15 estrategias que componen el repositorio, especificando los activos que evalúan, su lógica operativa y expectativas de rendimiento (basadas en backtests históricos limpios):

### A. Estrategias del Mercado Mexicano (BMV/IPC)

#### **S1: Adaptive Value (Concentrada en Valor)**
*   **Activos Evaluados:** 22 acciones líderes de la BMV (ej. `AMXB.MX`, `WALMEX.MX`, `GFNORTEO.MX`, `BIMBOA.MX`, `GAPB.MX`).
*   **Lógica:** Filtra acciones mediante un valuador de flujos descontados (DCS) buscando subvaluación (DCS $\ge 0.15$) y confirmación de tendencia alcista por encima de la SMA de 20 y 100 días.
*   **Expectativas (KPIs):** CAGR: **20.07%** | Sharpe: **0.82** | Drawdown Máximo: **-28.18%**.
*   **DCA Propuesto:** $2,000 MXN / mes.

#### **S2: 1d MACD Systematic (Seguimiento de Tendencia)**
*   **Activos Evaluados:** 22 acciones líderes de la BMV más 5 acciones de EE. UU. en el SIC.
*   **Lógica:** Cruce de MACD estándar (12, 26, 9) filtrado por una EMA de 50 días para operar únicamente en mercados alcistas, combinado con un Trailing Stop dinámico del 2% tras alcanzar un 15% de ganancia.
*   **Expectativas (KPIs):** CAGR: **18.44%** | Sharpe: **1.76** | Drawdown Máximo: **-9.49%**.
*   **DCA Propuesto:** $2,000 MXN / mes.

#### **S8: Dividend Quality & Yield (Flujo de Efectivo)**
*   **Activos Evaluados:** Fibras y acciones mexicanas con alto dividendo y balances sólidos (ej. `VESTA.MX`, `ASURB.MX`, `KIMBERA.MX`).
*   **Lógica:** Selecciona activos con altos retornos de dividendos históricos sostenibles por flujo de caja libre, ponderado por volatilidad inversa.
*   **Expectativas (KPIs):** CAGR: **14.50%** | Sharpe: **1.12** | Drawdown Máximo: **-11.20%**.
*   **DCA Propuesto:** $2,000 MXN / mes.

#### **S9: AI-Regime Adaptive Stat-Arb (Arbitraje Estadístico)**
*   **Activos Evaluados:** Pares de acciones correlacionadas en la BMV (ej. aeropuertos `GAPB.MX` / `OMAB.MX` / `ASURB.MX`).
*   **Lógica:** Cointegración de pares evaluada diariamente. Las desviaciones de la media de Z-score gatillan compras y ventas en corto de los pares, adaptando los umbrales según el régimen HMM general.
*   **Expectativas (KPIs):** CAGR: **26.80%** | Sharpe: **1.45** | Drawdown Máximo: **-7.50%**.
*   **DCA Propuesto:** $2,000 MXN / mes.

---

### B. Estrategias del Mercado Estadounidense (Alpaca / USD)

#### **S3: US Stock Momentum (Apalancada - Halted)**
*   **Activos Evaluados:** 12 acciones líderes de gran capitalización de EE. UU. (ej. `AAPL`, `NVDA`, `MSFT`, `AMZN`, `TSLA`, `JPM`).
*   **Lógica:** Momentum de alta frecuencia operado con apalancamiento marginal en Alpaca. 
*   *Nota Crítica:* Actualmente suspendida debido a pérdidas por balance de cash negativo en el bróker.
*   **Expectativas (KPIs):** CAGR: **25.40%** | Sharpe: **1.15** | Drawdown Máximo: **-18.20%**.
*   **DCA Propuesto:** $1,000 USD / mes (detenido hasta reconciliación).

#### **S4: US DCS Value-Growth (Large Cap)**
*   **Activos Evaluados:** 12 acciones líderes de EE. UU. más `SPY`.
*   **Lógica:** Selecciona las 3 acciones de mayor crecimiento de flujos que coticen con descuento respecto a su valor intrínseco (DCS).
*   **Expectativas (KPIs):** CAGR: **21.93%** | Sharpe: **1.14** | Drawdown Máximo: **-12.19%**.
*   **DCA Propuesto:** $1,000 USD / mes.

#### **S5: Alternative Assets (Crypto & Commodities)**
*   **Activos Evaluados:** Criptomonedas (`BTC-USD`, `ETH-USD`), Materias Primas (`GLD` - Oro, `SLV` - Plata, `USO` - Petróleo, `DBA` - Agricultura) y divisas.
*   **Lógica:** Rotación de activos basada en momentum relativo y paridad de riesgo para diversificar fuera de acciones tradicionales.
*   **Expectativas (KPIs):** CAGR: **18.40%** | Sharpe: **0.95** | Drawdown Máximo: **-15.20%**.
*   **DCA Propuesto:** $1,000 USD / mes.

#### **S6: High-Beta Momentum (Crecimiento Acelerado)**
*   **Activos Evaluados:** Acciones de EE. UU. con Beta > 1.2 respecto a `SPY` (ej. `NVDA`, `TSLA`, `AMD`).
*   **Lógica:** Compras concentradas en los 3 activos con mayor inercia alcista durante mercados alcistas (filtro `SPY` > SMA 200).
*   **Expectativas (KPIs):** CAGR: **22.10%** | Sharpe: **1.05** | Drawdown Máximo: **-19.50%**.
*   **DCA Propuesto:** $1,000 USD / mes.

---

### C. Estrategias AI Intradía (30m QQQ / TQQQ / SQQQ)

#### **S10: AI Intraday VWAP (Momento Intradía)**
*   **Activos Evaluados:** `TQQQ` (3x Bull Nasdaq), `SQQQ` (3x Bear Nasdaq), y `QQQ` (como índice de referencia).
*   **Lógica:** Usa el M-HMM intradía para definir el régimen diario. En mercados Bull/Bear opera rupturas de las bandas VWAP (1.5x ATR). En mercados Chop opera reversiones contra las bandas.
*   **Expectativas (KPIs):** CAGR: **53.25%** | Sharpe: **2.73** | Drawdown Máximo: **-4.14%**.
*   **DCA Propuesto:** $3,000 MXN / mes.

#### **S11: AI Intraday CCI-ADX (Twin Intradía)**
*   **Activos Evaluados:** `TQQQ`, `SQQQ` y `QQQ`.
*   **Lógica:** Combina el filtro de régimen M-HMM con osciladores de sobrecompra/sobreventa (CCI) e indicadores de fuerza de tendencia (ADX).
*   **Expectativas (KPIs):** CAGR: **11.88%** | Sharpe: **0.10** | Drawdown Máximo: **-16.31%**.
*   **DCA Propuesto:** $3,000 MXN / mes.

---

### D. Estrategias Multiciclo Core y Agregadoras (QQQ + BONDIA)

#### **S12: Vol-Targeted Trend (VTTL Core)**
*   **Activos Evaluados:** `TQQQ` y efectivo remunerado en **BONDIA** (Carry Trade MXN).
*   **Lógica:** Modula la exposición a `TQQQ` basándose en un objetivo de volatilidad constante del 20% anualizado. Si la volatilidad del mercado sube, reduce exposición a cash; si baja, se apalanca hasta 1.5x.
*   **Expectativas (KPIs):** CAGR: **17.13%** | Sharpe: **0.46** | Drawdown Máximo: **-21.34%** (Respaldado por 22.5 años de datos).
*   **DCA Propuesto:** $2,000 MXN / mes.

#### **S13: Risk Appetite (CARA - CPPI)**
*   **Activos Evaluados:** `TQQQ` y cash **BONDIA**.
*   **Lógica:** Modula la exposición según un colchón de riesgo constante para proteger el capital ante caídas del mercado.
*   *Nota:* Actualmente retirada en formato individual y asimilada como componente dentro de S14/S15.
*   **Expectativas (KPIs):** CAGR: **15.95%** | Sharpe: **0.45** | Drawdown Máximo: **-25.02%**.

#### **S14: Aggregator (HEDGE - Multi-Experto)**
*   **Activos Evaluados:** Asignación ponderada entre las estrategias `S12` (VTTL), `S13` (CARA) y **Cash (BONDIA)**.
*   **Lógica:** Algoritmo **HEDGE (Actualización de Pesos Multiplicativos)**. Asigna capital dinámicamente según el arrepentimiento histórico acumulado de cada sub-estrategia para minimizar el drawdown máximo.
*   **Expectativas (KPIs):** CAGR: **15.17%** | Sharpe: **0.53** | Drawdown Máximo: **-15.19%** (19.2 años de datos).
*   **DCA Propuesto:** $2,000 MXN / mes.

#### **S15: Tracker (TRACK)**
*   **Activos Evaluados:** Mismo universo que HEDGE.
*   **Lógica:** Versión de seguimiento pasivo del HEDGE con rebalanceos retardados para reducir costos transaccionales.
*   **Expectativas (KPIs):** CAGR: **15.05%** | Sharpe: **0.53** | Drawdown Máximo: **-14.73%**.
*   **DCA Propuesto:** $2,000 MXN / mes.

#### **S7: Core Hybrid Portfolio (Consolidado Global)**
*   **Activos Evaluados:** Mezcla balanceada de todas las sub-estrategias anteriores rebalanceada bajo **Paridad de Riesgo**.
*   **Expectativas (KPIs):** CAGR: **15.63%** | Sharpe: **1.07** | Drawdown Máximo: **-10.49%**.

---

## 2. Recomendaciones Finales de Estructura de Inversión

### La Estructura Core-Satélite (Recomendada)
Intentar fondear y operar las 15 estrategias de forma aislada y separada en cuentas individuales es financieramente ineficiente y sumamente complejo (requeriría un flujo mensual agregado de **$18,000 MXN** y **$3,000 USD** en depósitos). 

En su lugar, se recomienda consolidar el capital en **dos únicas cuentas operativas**:

```
PORTAFOLIO GLOBAL
 ├── [80% del Capital] CUENTA CORE (Estrategia S7 / S14 HEDGE)
 │    └── Preservación, crecimiento estable y control estricto de Drawdowns (MaxDD -15%).
 └── [20% del Capital] CUENTA SATÉLITE (Estrategia S10 AI Intraday VWAP)
      └── Crecimiento agresivo aprovechando las rupturas de alta frecuencia (CAGR +53%).
```

---

## 3. Hoja de Ruta de Aportaciones Financieras (DCA)

Para seguir una planeación estratégica disciplinada con un **Capital Inicial de $100,000 MXN** (distribuido 80/20 entre la Cuenta Core y la Cuenta Satélite), debes programar las siguientes aportaciones (DCA):

### Frecuencia e Importe de los Depósitos

*   **Cuenta Core (80% / S7 o S14):** Depósito mensual de **$3,000 MXN** (a realizarse el primer día hábil de cada mes).
*   **Cuenta Satélite (20% / S10):** Depósito mensual de **$1,000 MXN** (a realizarse el primer día hábil de cada mes).
*   **Total Ahorro Compuesto:** **$4,000 MXN / mes** ($48,000 MXN anualizados).

---

### Cronograma de Ejecución y Flujos de Capital

#### **Fase 1: Preparación y Saneamiento (Mes 1)**
*   **Acción Financiera:** 
    1.  Abrir/revisar tu cuenta en Alpaca y GBM/BONDIA.
    2.  Asignar el balance inicial: **$80,000 MXN** a la Cuenta Core (S14/S7) y **$20,000 MXN** a la Cuenta Satélite (S10).
    3.  *Crítico:* Resolver el saldo negativo de S3 vendiendo las posiciones de margen en el tablero de Alpaca para liberar el flag del watchdog.
*   **Ejecución de Código:** Correr `reconcile_s3.py` para sincronizar los archivos locales.

#### **Fase 2: Acumulación Activa (Meses 2 a 12)**
*   **Acción Financiera:** Inyectar los **$4,000 MXN mensuales** distribuidos (3k a Core, 1k a Satélite).
*   **Ejecución de Código:** Dejar correr el programador automático `.github/workflows/monitor.yml` cada 30 minutos.
*   **Meta de NAV al Finalizar el Año 1:** **$162,398.07 MXN** en valor de cartera neto.

#### **Fase 3: Maduración y Consolidación (Años 2 a 5)**
*   **Acción Financiera:** Mantener los depósitos disciplinados de **$4,000 MXN mensuales**.
*   **Ejecución de Código:** Monitorear reportes mensuales de desempeño (`comparison_report.md`). Si S10 mantiene su Sharpe > 2.0 en real tras 1 año, mantener su ponderación. Si decae, traspasar capital a la Cuenta Core de menor riesgo.
*   **Meta de NAV al Finalizar el Año 5:** **$663,205.90 MXN** (Ahorro total depositado: $296k MXN | Retorno generado: +$367k MXN).

#### **Fase 4: Retiro e Interés Compuesto Puro (Años 6 a 10)**
*   **Acción Financiera:** Continuar aportaciones o suspender depósitos y dejar capitalizar.
*   **Meta de NAV al Finalizar el Año 10 (con depósitos constantes):** **$3,554,234.20 MXN** (Ahorro total depositado: $496k MXN | Retorno generado: +$3.05M MXN).
