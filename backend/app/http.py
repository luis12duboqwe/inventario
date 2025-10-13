"""Minimal HTTP-like framework tailored for offline testing."""
from __future__ import annotations

import re
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Callable, Dict, Iterable, Optional


@dataclass
class Response:
    """Simple response object mimicking the interface of requests.Response."""

    status_code: int
    content: Any = None

    def json(self) -> Any:
        return self.content


@dataclass
class Request:
    """Lightweight request wrapper passed to handlers."""

    method: str
    path: str
    body: Any | None = None


class Route:
    """Internal representation of a registered endpoint."""

    def __init__(
        self,
        *,
        methods: Iterable[str],
        path: str,
        endpoint: Callable[..., Any],
        status_code: int,
    ) -> None:
        self.methods = {method.upper() for method in methods}
        self.path = path
        self.endpoint = endpoint
        self.status_code = status_code
        self.pattern, self.param_names = self._compile_path(path)

    @staticmethod
    def _compile_path(path: str) -> tuple[re.Pattern[str], list[str]]:
        param_names: list[str] = []

        def _replace(match: re.Match[str]) -> str:
            name = match.group(1)
            param_names.append(name)
            return r"(?P<%s>[^/]+)" % name

        pattern = re.sub(r"{([^}/]+)}", _replace, path)
        regex = re.compile(f"^{pattern}$")
        return regex, param_names

    def matches(self, method: str, path: str) -> Optional[dict[str, str]]:
        if method.upper() not in self.methods:
            return None
        match = self.pattern.match(path)
        if not match:
            return None
        return match.groupdict()


class SimpleApp:
    """Extremely small HTTP application used for tests."""

    def __init__(self) -> None:
        self.routes: list[Route] = []
        self.exception_handlers: dict[type[Exception], Callable[[Request, Exception], Response]] = {}
        self.state: dict[str, Any] = {}

    # --- routing API -------------------------------------------------
    def route(self, path: str, *, methods: Iterable[str], status_code: int = HTTPStatus.OK) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(Route(methods=methods, path=path, endpoint=func, status_code=int(status_code)))
            return func

        return decorator

    def get(self, path: str, *, status_code: int = HTTPStatus.OK) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(path, methods=["GET"], status_code=status_code)

    def post(self, path: str, *, status_code: int = HTTPStatus.CREATED) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(path, methods=["POST"], status_code=status_code)

    def include_router(self, router: "Router", *, prefix: str = "") -> None:
        for route in router.routes:
            merged_path = f"{prefix.rstrip('/')}{route.path}" if prefix else route.path
            self.routes.append(Route(methods=route.methods, path=merged_path, endpoint=route.endpoint, status_code=route.status_code))

    # --- exception handling -----------------------------------------
    def exception_handler(
        self, exc_type: type[Exception]
    ) -> Callable[[Callable[[Request, Exception], Response]], Callable[[Request, Exception], Response]]:
        def decorator(handler: Callable[[Request, Exception], Response]) -> Callable[[Request, Exception], Response]:
            self.exception_handlers[exc_type] = handler
            return handler

        return decorator

    # --- lifecycle utilities ----------------------------------------
    def reset_state(self) -> None:  # pragma: no cover - override in app if needed
        self.state.clear()

    # --- request processing -----------------------------------------
    def handle_request(self, method: str, path: str, *, json: Any | None = None) -> Response:
        request = Request(method=method, path=path, body=json)
        for route in self.routes:
            params = route.matches(method, path)
            if params is None:
                continue
            try:
                result = route.endpoint(request, **{name: value for name, value in params.items()})
            except Exception as exc:  # pragma: no cover - basic dispatch path
                response = self._handle_exception(request, exc)
                if response is None:
                    raise
                return response
            if isinstance(result, Response):
                return result
            return Response(status_code=route.status_code, content=result)
        return Response(status_code=int(HTTPStatus.NOT_FOUND), content={"error": {"code": "not_found", "message": "Endpoint not found"}})

    def _handle_exception(self, request: Request, exc: Exception) -> Response | None:
        for exc_type, handler in self.exception_handlers.items():
            if isinstance(exc, exc_type):
                return handler(request, exc)
        return None


class Router:
    """Router used to group endpoints."""

    def __init__(self, *, prefix: str = "") -> None:
        self.prefix = prefix
        self.routes: list[Route] = []

    def route(self, path: str, *, methods: Iterable[str], status_code: int = HTTPStatus.OK) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        full_path = f"{self.prefix}{path}"

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(Route(methods=methods, path=full_path, endpoint=func, status_code=int(status_code)))
            return func

        return decorator

    def get(self, path: str, *, status_code: int = HTTPStatus.OK) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(path, methods=["GET"], status_code=status_code)

    def post(self, path: str, *, status_code: int = HTTPStatus.CREATED) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(path, methods=["POST"], status_code=status_code)


class TestClient:
    """Client that mirrors the API of fastapi.testclient for our tests."""

    def __init__(self, app: SimpleApp) -> None:
        self.app = app

    def __enter__(self) -> "TestClient":
        self.app.reset_state()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - no special shutdown
        return None

    # request helpers -------------------------------------------------
    def get(self, path: str) -> Response:
        return self.app.handle_request("GET", path)

    def post(self, path: str, *, json: Dict[str, Any] | None = None) -> Response:
        return self.app.handle_request("POST", path, json=json)
