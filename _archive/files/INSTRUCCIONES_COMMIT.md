# Fase 0 - Instrucciones de despliegue y VERIFICACION

## 1. Copiar archivos al repo (respetando rutas)
Raiz: halt_gate.py, watchdog.py, scheduler.py, y los 9 run_live_*.py
connectors/: alpaca_connector.py, market_data.py
.github/workflows/: monitor.yml

## 2. Commit
git add halt_gate.py watchdog.py scheduler.py run_live_*.py connectors/ .github/workflows/monitor.yml
git commit -m "Fase 0: fill confirmation en 4 runners, HALT gate, watchdog W6+cobertura total, market_data failover, cron diario, S3/S10/S11 suspendidas"
git push origin main

## 3. VERIFICAR (la leccion de esta semana: el diff manda, no el resumen)
git log --oneline -1                                  # el commit existe
grep -c submit_and_confirm connectors/alpaca_connector.py   # debe dar >= 1
grep -c "Mock executing" run_live_alpaca_us_stocks.py       # debe dar 0
grep -c halt_gate run_live_strategy12.py                    # debe dar 1
grep W6 watchdog.py | head -1                               # W6 presente
grep "45 19" .github/workflows/monitor.yml                  # cron diario

## 4. Exponer credenciales al watchdog (activa W6) en monitor.yml,
##    en el paso "python watchdog.py":
      env:
        APCA_API_KEY_ID: ${{ secrets.APCA_API_KEY_ID }}
        APCA_API_SECRET_KEY: ${{ secrets.APCA_API_SECRET_KEY }}
   (usa los nombres reales de tus secrets)

## 5. Reconciliacion de S3 (manual, una vez):
   a) En Alpaca paper: vender posiciones hasta cash >= 0.
   b) Copiar posiciones/cash REALES del broker a portfolio_us_stocks.json.
   c) Anotar el episodio en transactions_us_stocks.md.
   d) Borrar HALT_us_stocks.flag y descomentar S3 en scheduler.py.

## 6. Criterio de salida de Fase 0:
   5 dias habiles consecutivos de watchdog en verde con W6 activo.
   Hasta entonces: NADA nuevo se construye.
