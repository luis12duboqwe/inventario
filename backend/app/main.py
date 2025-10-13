"""Main entry point for the simplified Softmobile API."""
from __future__ import annotations

from http import HTTPStatus

from .domain import InMemoryRepository, SoftmobileError
from .http import Response, Router, SimpleApp

app = SimpleApp()


def _reset_state() -> None:
    app.state["repository"] = InMemoryRepository()


def _reset_and_seed() -> None:
    _reset_state()


app.reset_state = _reset_and_seed  # type: ignore[attr-defined]
app.reset_state()


@app.exception_handler(SoftmobileError)
def handle_domain_error(request, exc: SoftmobileError) -> Response:
    return Response(status_code=exc.status_code, content=exc.to_dict())


@app.get("/", status_code=HTTPStatus.OK)
def root(_: object) -> dict[str, str]:
    return {"message": "Softmobile API operational"}


api_router = Router(prefix="/api/v1")


@api_router.get("/health", status_code=HTTPStatus.OK)
def health(_: object) -> dict[str, str]:
    return {"status": "ok"}


@api_router.get("/stores/", status_code=HTTPStatus.OK)
def list_stores(_: object) -> list[dict[str, object]]:
    repo: InMemoryRepository = app.state["repository"]
    return [store.to_dict() for store in repo.list_stores()]


@api_router.post("/stores/", status_code=HTTPStatus.CREATED)
def create_store(request, /) -> dict[str, object]:
    repo: InMemoryRepository = app.state["repository"]
    payload = request.body or {}
    store = repo.create_store(payload)
    return store.to_dict()


@api_router.get("/stores/{store_id}/devices/", status_code=HTTPStatus.OK)
def list_devices(_: object, store_id: str) -> list[dict[str, object]]:
    repo: InMemoryRepository = app.state["repository"]
    devices = repo.list_devices(store_id)
    return [device.to_dict() for device in devices]


@api_router.post("/stores/{store_id}/devices/", status_code=HTTPStatus.CREATED)
def create_device(request, store_id: str) -> dict[str, object]:
    repo: InMemoryRepository = app.state["repository"]
    payload = request.body or {}
    device = repo.create_device(store_id, payload)
    return device.to_dict()


app.include_router(api_router)
