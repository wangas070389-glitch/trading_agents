"""
HALT GATE: interruptor de emergencia por estrategia.
El watchdog escribe HALT_<nombre>.flag cuando detecta un CRITICAL.
Cada runner llama halted(dir_path, nombre) como PRIMERA linea de main():
si el flag existe, el runner se niega a operar hasta que un humano lo
borre tras investigar. La decision mas valiosa de un sistema autonomo
es dejar de operar, y esa no requiere juicio: requiere reflejo.
"""
import os


def halted(dir_path: str, name: str) -> bool:
    flag = os.path.join(dir_path, f"HALT_{name}.flag")
    if os.path.exists(flag):
        try:
            with open(flag, "r", encoding="utf-8") as f:
                reason = f.read().strip()[:300]
        except Exception:
            reason = "(ilegible)"
        print("=" * 70)
        print(f"HALT ACTIVO para '{name}' - EJECUCION ABORTADA")
        print(f"Razon: {reason}")
        print(f"Para reanudar: investigar, corregir, y borrar {os.path.basename(flag)}")
        print("=" * 70)
        return True
    return False


def raise_halt(dir_path: str, name: str, reason: str):
    flag = os.path.join(dir_path, f"HALT_{name}.flag")
    with open(flag, "w", encoding="utf-8") as f:
        f.write(reason)
    return flag
