from __future__ import annotations

from fastapi import Request, Response


async def cors_preflight_handler(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=200)
        origin = request.headers.get("origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        allow_headers = request.headers.get(
            "access-control-request-headers")
        if allow_headers:
            response.headers["Access-Control-Allow-Headers"] = allow_headers
        allow_method = request.headers.get("access-control-request-method")
        if allow_method:
            response.headers["Access-Control-Allow-Methods"] = allow_method
        return response
    return await call_next(request)
