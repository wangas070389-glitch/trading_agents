import os
import sys
import json
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer

class DashboardAPIHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        
        # 1. API: GET /api/portfolio
        if self.path == '/api/portfolio':
            portfolio_file = os.path.join(dir_path, 'portfolio.json')
            if not os.path.exists(portfolio_file):
                self.send_error(404, "portfolio.json not found")
                return
            
            try:
                with open(portfolio_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"Error reading portfolio: {str(e)}")
            return

        # 2. Static File MIME Correction (prevents Windows registry content-type issues)
        clean_path = self.path.split('?')[0].lstrip('/')
        if not clean_path or clean_path == "":
            clean_path = "index.html"
            
        file_path = os.path.join(dir_path, clean_path)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            if clean_path.endswith('.html'):
                self.send_header('Content-type', 'text/html; charset=utf-8')
            elif clean_path.endswith('.css'):
                self.send_header('Content-type', 'text/css; charset=utf-8')
            elif clean_path.endswith('.js'):
                self.send_header('Content-type', 'application/javascript; charset=utf-8')
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
            return
            
        super().do_GET()

    def do_POST(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        
        # API: POST /api/refresh
        if self.path == '/api/refresh':
            try:
                # Execute the monitor python script to update prices from Yahoo Finance
                monitor_script = os.path.join(dir_path, 'monitor_portfolio.py')
                result = subprocess.run([sys.executable, monitor_script], capture_output=True, text=True)
                
                # Read updated data
                portfolio_file = os.path.join(dir_path, 'portfolio.json')
                with open(portfolio_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                response = {
                    "status": "success",
                    "log": result.stdout,
                    "data": data
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                response = {
                    "status": "error",
                    "message": str(e)
                }
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        # API: POST /api/backtest
        if self.path == '/api/backtest':
            try:
                # Import backtest runner
                from backtest import run_backtest_simulation
                
                # Execute simulation
                results = run_backtest_simulation()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode('utf-8'))
            except Exception as e:
                response = {
                    "status": "error",
                    "message": str(e)
                }
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        # API: POST /api/backtest_macd
        if self.path == '/api/backtest_macd':
            try:
                # Import backtest runner
                from backtest_macd import run_macd_simulation_for_api
                
                # Read JSON body if present
                content_length = int(self.headers.get('Content-Length', 0))
                ticker = "SPY"
                if content_length > 0:
                    try:
                        body = self.rfile.read(content_length)
                        req_data = json.loads(body.decode('utf-8'))
                        ticker = req_data.get("ticker", "SPY")
                    except Exception:
                        pass
                
                # Execute simulation
                results = run_macd_simulation_for_api(ticker=ticker)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode('utf-8'))
            except Exception as e:
                response = {
                    "status": "error",
                    "message": str(e)
                }
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
            return
            
        self.send_error(404, "Endpoint not found")

def start_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, DashboardAPIHandler)
    print("=" * 80)
    print(f"PORTFOLIO DASHBOARD SERVER RUNNING AT: http://localhost:{port}")
    print("Open http://localhost:8000 in your browser to view the dashboard.")
    print("Press Ctrl+C to terminate.")
    print("=" * 80)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == '__main__':
    start_server()
