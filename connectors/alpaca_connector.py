import os
import time
import requests

class AlpacaConnector:
    def __init__(self, api_key=None, secret_key=None, base_url=None):
        # Load local .env if available
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            k, v = line.strip().split("=", 1)
                            os.environ[k] = v
            except Exception:
                pass

        # Load from arguments or fallback to environment variables
        self.api_key = api_key or os.environ.get("ALPACA_API_KEY")
        self.secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY")
        self.base_url = base_url or os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        # Clean URL to prevent trailing slash issues
        if self.base_url:
            self.base_url = self.base_url.rstrip("/")

    def _get_headers(self) -> dict:
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API credentials (APCA_API_KEY_ID / APCA_API_SECRET_KEY) are not set.")
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }

    def get_account_info(self) -> dict:
        """Fetch general account information."""
        url = f"{self.base_url}/v2/account"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def get_positions(self) -> list:
        """Fetch current open positions."""
        url = f"{self.base_url}/v2/positions"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def submit_order(self, ticker: str, qty: float, side: str, order_type: str = "market", time_in_force: str = "day") -> dict:
        """
        Submit a buy or sell order.
        ticker: Symbol (e.g. AAPL, NVDA)
        qty: Number of shares (float or int)
        side: 'buy' or 'sell'
        """
        url = f"{self.base_url}/v2/orders"
        payload = {
            "symbol": ticker,
            "qty": str(qty),
            "side": side.lower(),
            "type": order_type,
            "time_in_force": time_in_force
        }
        response = requests.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()


    def submit_and_confirm(self, ticker: str, qty: float, side: str,
                           order_type: str = "market", time_in_force: str = "day",
                           timeout_s: int = 30) -> dict:
        """Envia una orden y CONFIRMA el fill real via polling. NUNCA lanza:
        devuelve {"filled": bool, "status", "filled_qty", "filled_avg_price", "id"}.
        El ledger local SOLO debe mutarse si filled es True."""
        try:
            order = self.submit_order(ticker, qty, side, order_type, time_in_force)
        except Exception as e:
            return {"filled": False, "status": f"submit_error: {e}",
                    "filled_qty": 0.0, "filled_avg_price": None, "id": None}
        order_id = order.get("id")
        status = order.get("status", "")
        deadline = time.time() + timeout_s
        while status not in ("filled", "canceled", "rejected", "expired") and time.time() < deadline:
            time.sleep(2)
            try:
                order = self.get_order(order_id)
                status = order.get("status", "")
            except Exception as e:
                status = f"poll_error: {e}"
                break
        filled = status == "filled"
        return {"filled": filled, "status": status,
                "filled_qty": float(order.get("filled_qty") or 0.0) if filled else 0.0,
                "filled_avg_price": float(order.get("filled_avg_price") or 0.0) if filled else None,
                "id": order_id}

    def get_order(self, order_id: str) -> dict:
        """Fetch details of a specific order."""
        url = f"{self.base_url}/v2/orders/{order_id}"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
