import os
import sys
import json
import datetime
import argparse
from connectors.alpaca_connector import AlpacaConnector

def main():
    parser = argparse.ArgumentParser(description="Automatiza la reconciliacion de S3 (Fase 0)")
    parser.add_argument("--key", required=True, help="Alpaca API Key ID")
    parser.add_argument("--secret", required=True, help="Alpaca API Secret Key")
    parser.add_argument("--base", default="https://paper-api.alpaca.markets", help="Alpaca Base URL")
    args = parser.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("================================================================================")
    # 1. Conectar a Alpaca
    print("Conectando a Alpaca...")
    try:
        client = AlpacaConnector(api_key=args.key, secret_key=args.secret, base_url=args.base)
        acct = client.get_account_info()
        positions = client.get_positions()
    except Exception as e:
        print(f"Error al conectar con Alpaca: {e}")
        sys.exit(1)

    cash = float(acct.get("cash", 0.0))
    equity = float(acct.get("equity", 100000.0))
    print(f"Cuenta conectada exitosamente.")
    print(f"Cash en Alpaca: ${cash:,.2f} USD | Equity: ${equity:,.2f} USD")
    print(f"Posiciones activas en broker: {len(positions)}")

    # Validar criterio de cash
    if cash < 0:
        print("\n[WARNING] El saldo de cash en el broker sigue siendo NEGATIVO.")
        print("Por favor, vende posiciones manualmente en la web de Alpaca para que el cash sea >= 0.")
        print("La reconciliacion se detiene para evitar consolidar una cuenta sobre-apalancada.")
        sys.exit(1)

    # 2. Generar el nuevo holdings list
    holdings = []
    total_holdings_val = 0.0
    for pos in positions:
        ticker = pos["symbol"]
        shares = float(pos["qty"])
        price = float(pos["current_price"])
        buy_price = float(pos["avg_entry_price"])
        val = shares * price
        total_holdings_val += val
        holdings.append({
            "ticker": ticker,
            "shares": shares,
            "buy_price": buy_price,
            "last_price": price,
            "peak_price": max(buy_price, price),
            "target_weight": 0.25  # weight default
        })

    # Re-calcular total_capital basándose en el NAV real
    total_capital = cash + total_holdings_val
    print(f"NAV calculado: ${total_capital:,.2f} USD")

    # 3. Guardar en portfolio_us_stocks.json
    portfolio_data = {
        "total_capital": round(total_capital, 2),
        "cash_balance": round(cash, 2),
        "holdings": holdings,
        "last_updated": timestamp
    }
    
    portfolio_path = os.path.join(dir_path, "portfolio_us_stocks.json")
    with open(portfolio_path, "w", encoding="utf-8") as f:
        json.dump(portfolio_data, f, indent=2)
    print(f"\n[OK] {portfolio_path} actualizado con los datos reales del broker.")

    # 4. Registrar la transaccion en transactions_us_stocks.md
    tx_path = os.path.join(dir_path, "transactions_us_stocks.md")
    note = f"Reconciliacion de Fase 0: Sincronizacion manual con broker. Cash: ${cash:.2f}, Holdings: {len(holdings)} activos."
    log_line = f"| {today_str} | RECON | SYNC | 0 | 0.00 | +0.00 | Manual | FILLED | {note} |\n"
    
    if os.path.exists(tx_path):
        with open(tx_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# Transaction Ledger (Isolated US Stock Momentum)\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"
        
    lines = content.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            insert_idx = i
            break
    if insert_idx is not None:
        lines.insert(insert_idx, log_line.strip())
    else:
        lines.append(log_line.strip())
        
    with open(tx_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[OK] Evento de reconciliacion anotado en {tx_path}")

    # 5. Borrar el flag de HALT
    halt_path = os.path.join(dir_path, "HALT_us_stocks.flag")
    if os.path.exists(halt_path):
        os.remove(halt_path)
        print(f"[OK] Flag de bloqueo eliminado: {halt_path}")
    else:
        print("[INFO] No existia ningun flag de bloqueo HALT activo.")

    # 6. Reactivar S3 en scheduler.py
    scheduler_path = os.path.join(dir_path, "scheduler.py")
    if os.path.exists(scheduler_path):
        with open(scheduler_path, "r", encoding="utf-8") as f:
            sched_content = f.read()
        
        target_comment = '# "run_live_alpaca_us_stocks.py",   # S3 SUSPENDIDA: reconciliar margen -44k vs Alpaca antes de reactivar'
        target_uncomment = '    "run_live_alpaca_us_stocks.py",'
        
        if target_comment in sched_content:
            sched_content = sched_content.replace(target_comment, target_uncomment)
            with open(scheduler_path, "w", encoding="utf-8") as f:
                f.write(sched_content)
            print("[OK] S3 reactivado en scheduler.py.")
        else:
            print("[INFO] S3 ya parecia estar reactivado o modificado en scheduler.py.")

    print("\nReconciliacion completada exitosamente. Puedes subir estos cambios a Git.")
    print("================================================================================")

if __name__ == "__main__":
    main()
