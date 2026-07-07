"""
WATCHDOG: auditor de fallo silencioso para todos los portafolios del repo.
==========================================================================
Escanea portfolio_strategy*.json + transactions_strategy*.md y verifica:

  W1  STALENESS       last_updated con mas de MAX_STALE_HOURS de antiguedad
                      en dia habil -> el cron esta muerto o el script crashea.
  W2  ZERO-TRADE      estrategia viva >= MIN_DAYS_FOR_TRADE dias habiles con
                      cero transacciones no-interes -> logica de entrada
                      posiblemente muerta (esto habria detectado S10/S11 en
                      su primera semana).
  W3  NAV-JUMP        salto de NAV dia-a-dia imposible dada la exposicion
                      (holdings 3x acotan el movimiento plausible) -> bug de
                      contabilidad (esto habria detectado el P&L invertido
                      de SQQQ en su primer trade).
  W4  NEGATIVE/NAN    cash negativo, shares negativos, NaN en el JSON.
  W5  DD-BREAKER      drawdown live > tolerancia sobre el MaxDD del backtest
                      (si existe strategyN_backtest_nav.csv) -> el live esta
                      fuera de la distribucion que validaste.

Salida: watchdog_report.md + exit code 1 si hay CRITICAL -> GitHub Actions
marca la corrida EN ROJO. El fallo deja de ser silencioso.

Uso:  python watchdog.py            (auditar y fallar en critico)
      python watchdog.py --dry-run  (auditar sin exit code)
Integracion en workflow (paso final, despues de los runners):
      - run: python watchdog.py
"""
