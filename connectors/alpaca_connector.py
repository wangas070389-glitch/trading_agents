import os
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

    def get_order(self, order_id: str) -> dict:
        """Fetch details of a specific order."""
        url = f"{self.base_url}/v2/orders/{order_id}"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
