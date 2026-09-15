"""Vercel Python Entrypoint for Serverless Functions.

Provides top-level 'app' and 'handler' variables required by Vercel CLI.
"""

from api.plan import handler

# Export for WSGI/ASGI and BaseHTTPRequestHandler runtimes
app = handler

__all__ = ["app", "handler"]
