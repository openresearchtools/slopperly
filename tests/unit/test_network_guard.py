import socket
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.audit.network_guard import NetworkGuardError, local_only_network


class TinyHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")


class NetworkGuardTests(unittest.TestCase):
    def test_blocks_non_local_socket_before_network(self):
        with local_only_network():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                with self.assertRaises(NetworkGuardError):
                    sock.connect(("8.8.8.8", 443))

    def test_connect_ex_returns_permission_error_for_non_local(self):
        with local_only_network():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                self.assertEqual(sock.connect_ex(("8.8.8.8", 443)), 1)

    def test_allows_loopback_http_runtime(self):
        server = HTTPServer(("127.0.0.1", 0), TinyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/health"
            with local_only_network():
                with urlopen(url, timeout=2) as response:
                    body = response.read()
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(body, b"ok")


if __name__ == "__main__":
    unittest.main()
