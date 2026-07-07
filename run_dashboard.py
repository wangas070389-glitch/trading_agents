import os
import sys
import time
import webbrowser
import http.server
import socketserver
import threading

PORT = 8050
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"\n[Dashboard Server] Active and serving files on port {PORT}")
        print(f"[Dashboard Server] Folder: {DIRECTORY}")
        print(f"[Dashboard Server] Press CTRL+C to terminate.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()

def main():
    print("================================================================================")
    print("TRADING AGENTS SUITE: WEB DASHBOARD LAUNCHER")
    print("================================================================================")
    
    # Run the server in a separate background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Give the server 1 second to bind and start listening
    time.sleep(1.0)
    
    # Launch browser to dashboard index page
    url = f"http://localhost:{PORT}/index.html"
    print(f"\n[Launcher] Launching web browser to {url}...")
    webbrowser.open(url)
    
    # Keep the main process running to keep the server alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Launcher] Dashboard server terminated. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    main()
