"""Local Development Server simulating Netlify Functions and static site hosting.

Run:
    python dev_server.py
Then open http://localhost:8888
"""

import http.server
import json
import os
import socketserver
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

PUBLIC_DIR = os.path.join(BASE_DIR, "public")
from netlify.functions.plan import handler as netlify_plan_handler

PORT = 8888


class NetlifyDevHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_OPTIONS(self):
        if self.path.startswith("/api/") or self.path.startswith("/.netlify/functions/"):
            event = {"httpMethod": "OPTIONS", "headers": dict(self.headers), "body": ""}
            res = netlify_plan_handler(event, None)
            self.send_response(res.get("statusCode", 200))
            for k, v in res.get("headers", {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(res.get("body", "").encode("utf-8"))
        else:
            super().do_OPTIONS()

    def do_POST(self):
        if self.path.startswith("/api/plan") or self.path.startswith("/.netlify/functions/plan"):
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
            
            event = {
                "httpMethod": "POST",
                "headers": dict(self.headers),
                "body": post_data,
            }
            res = netlify_plan_handler(event, None)
            
            self.send_response(res.get("statusCode", 200))
            for k, v in res.get("headers", {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(res.get("body", "").encode("utf-8"))
        else:
            self.send_error(404, "Endpoint not found")


def main():
    with socketserver.TCPServer(("", PORT), NetlifyDevHandler) as httpd:
        print(f"TRIP PLANER Netlify Local Dev Server running at: http://localhost:{PORT}")
        print(f"Serving frontend from: {PUBLIC_DIR}")
        print("Routing /api/plan to netlify/functions/plan.py")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dev server.")


if __name__ == "__main__":
    main()
