import unittest
from unittest.mock import patch, MagicMock
from connectors.alpaca_connector import AlpacaConnector

class TestAlpacaConnector(unittest.TestCase):
    @patch("connectors.alpaca_connector.os.path.exists")
    @patch.dict('os.environ', {}, clear=True)
    def test_get_headers_missing(self, mock_exists):
        # Prevent loading of local .env files
        mock_exists.return_value = False
        connector = AlpacaConnector(api_key=None, secret_key=None)
        with self.assertRaises(ValueError):
            connector._get_headers()

    def test_get_headers_ok(self):
        connector = AlpacaConnector(api_key="test_key", secret_key="test_secret")
        headers = connector._get_headers()
        self.assertEqual(headers["APCA-API-KEY-ID"], "test_key")
        self.assertEqual(headers["APCA-API-SECRET-KEY"], "test_secret")
        self.assertEqual(headers["Content-Type"], "application/json")

    @patch("connectors.alpaca_connector.requests.get")
    def test_get_account_info(self, mock_get):
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "acc_123", "cash": "10000.00"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        connector = AlpacaConnector(api_key="key", secret_key="secret", base_url="https://paper-api.alpaca.markets")
        res = connector.get_account_info()
        
        self.assertEqual(res["id"], "acc_123")
        mock_get.assert_called_once_with(
            "https://paper-api.alpaca.markets/v2/account",
            headers=connector._get_headers()
        )

    @patch("connectors.alpaca_connector.requests.post")
    def test_submit_order(self, mock_post):
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "order_abc", "status": "accepted"}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        connector = AlpacaConnector(api_key="key", secret_key="secret", base_url="https://paper-api.alpaca.markets")
        res = connector.submit_order(ticker="AAPL", qty=10, side="buy")
        
        self.assertEqual(res["id"], "order_abc")
        mock_post.assert_called_once_with(
            "https://paper-api.alpaca.markets/v2/orders",
            json={
                "symbol": "AAPL",
                "qty": "10",
                "side": "buy",
                "type": "market",
                "time_in_force": "day"
            },
            headers=connector._get_headers()
        )

if __name__ == "__main__":
    unittest.main()
