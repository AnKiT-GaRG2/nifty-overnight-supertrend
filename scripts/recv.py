"""Tiny local receiver: the browser page POSTs extracted Nifty-futures rows here. Writes only into data/fut_old/."""
import http.server, os, re, urllib.parse
OUT = os.path.abspath('data/fut_old')
class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*'); self.send_header('Access-Control-Allow-Private-Network', 'true')
    def do_OPTIONS(self): self.send_response(204); self._cors(); self.end_headers()
    def do_POST(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); name = re.sub(r'[^A-Za-z0-9_.-]', '', q.get('name', ['x.csv'])[0])
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        with open(os.path.join(OUT, name), 'ab') as f: f.write(body)
        self.send_response(200); self._cors(); self.end_headers(); self.wfile.write(b'ok')
    def log_message(self, *a): pass
http.server.HTTPServer(('127.0.0.1', 8765), H).serve_forever()
