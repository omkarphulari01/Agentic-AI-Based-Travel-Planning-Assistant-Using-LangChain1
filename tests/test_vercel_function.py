"""Unit test for Vercel Serverless Function handler (api/plan.py)."""

import io
import json
from unittest.mock import MagicMock

from api.plan import handler


class MockVercelRequest(handler):
    """Subclass of handler to test without spinning up an HTTP socket."""

    def __init__(self, method: str, path: str, body: bytes = b"", headers: dict | None = None):
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.command = method
        self.path = path
        self.headers = headers or {}
        if body:
            self.headers["Content-Length"] = str(len(body))
        self.request_version = "HTTP/1.1"
        self._headers_buffer = []

    def send_response(self, code, message=None):
        self.status_code = code

    def send_header(self, keyword, value):
        self._headers_buffer.append((keyword, value))

    def end_headers(self):
        pass


def test_vercel_handler_get():
    """Verify GET health check endpoint."""
    req = MockVercelRequest("GET", "/api/plan")
    req.do_GET()
    assert req.status_code == 200
    res = json.loads(req.wfile.getvalue().decode("utf-8"))
    assert res["status"] == "running"


def test_vercel_handler_options():
    """Verify CORS OPTIONS pre-flight response."""
    req = MockVercelRequest("OPTIONS", "/api/plan")
    req.do_OPTIONS()
    assert req.status_code == 200
    res = json.loads(req.wfile.getvalue().decode("utf-8"))
    assert res["status"] == "ok"


def test_vercel_wsgi_app():
    """Verify WSGI app entrypoint in api/index.py."""
    from api.index import app

    statuses = []
    headers = []

    def start_response(status, res_headers):
        statuses.append(status)
        headers.extend(res_headers)

    # Test GET
    body_parts = app({"REQUEST_METHOD": "GET"}, start_response)
    assert statuses[-1] == "200 OK"
    data = json.loads(b"".join(body_parts).decode("utf-8"))
    assert data["status"] == "running"

    # Test OPTIONS
    body_parts = app({"REQUEST_METHOD": "OPTIONS"}, start_response)
    assert statuses[-1] == "200 OK"
    data = json.loads(b"".join(body_parts).decode("utf-8"))
    assert data["status"] == "ok"

