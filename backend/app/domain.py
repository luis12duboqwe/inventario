"""Domain models and services for Softmobile without external dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from typing import Any


class SoftmobileError(Exception):
    """Error raised when domain validation fails."""

    def __init__(self, *, status_code: int, code: str, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        payload = {"error": {"code": self.code, "message": self.message}}
        if self.context:
            payload["error"]["context"] = self.context
        return payload


@dataclass(slots=True)
class Store:
    id: int
    name: str
    location: str | None = None
    phone: str | None = None
    manager: str | None = None
    status: str = "activa"
    code: str = ""
    timezone: str = "UTC"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "phone": self.phone,
            "manager": self.manager,
            "status": self.status,
            "code": self.code,
            "timezone": self.timezone,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class Device:
    id: int
    store_id: int
    sku: str
    name: str
    quantity: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "store_id": self.store_id,
            "sku": self.sku,
            "name": self.name,
            "quantity": self.quantity,
        }


@dataclass
class InMemoryRepository:
    """Simple in-memory data store used in lieu of a full database."""

    stores: dict[int, Store] = field(default_factory=dict)
    devices: dict[int, Device] = field(default_factory=dict)
    _store_sequence: int = 0
    _device_sequence: int = 0

    def reset(self) -> None:
        self.stores.clear()
        self.devices.clear()
        self._store_sequence = 0
        self._device_sequence = 0

    # --- store operations -------------------------------------------
    def create_store(self, payload: dict[str, Any]) -> Store:
        data = _validate_store_payload(payload)
        if any(store.name.lower() == data["name"].lower() for store in self.stores.values()):
            raise SoftmobileError(
                status_code=int(HTTPStatus.CONFLICT),
                code="store_already_exists",
                message="Ya existe una sucursal con ese nombre.",
            )
        code = data.get("code")
        if code and any(store.code.lower() == code.lower() for store in self.stores.values()):
            raise SoftmobileError(
                status_code=int(HTTPStatus.CONFLICT),
                code="store_code_already_exists",
                message="Ya existe una sucursal con ese código.",
            )
        self._store_sequence += 1
        if not code:
            code = f"SUC-{self._store_sequence:03d}"
            data["code"] = code
        data["status"] = (data.get("status") or "activa").lower()
        store = Store(id=self._store_sequence, **data)
        self.stores[store.id] = store
        return store

    def list_stores(self) -> list[Store]:
        return sorted(self.stores.values(), key=lambda store: store.name.lower())

    def get_store(self, store_id: int) -> Store:
        try:
            store_id_int = int(store_id)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise SoftmobileError(
                status_code=int(HTTPStatus.BAD_REQUEST),
                code="invalid_store_id",
                message="El identificador de la sucursal debe ser numérico.",
            ) from exc
        store = self.stores.get(store_id_int)
        if store is None:
            raise SoftmobileError(
                status_code=int(HTTPStatus.NOT_FOUND),
                code="store_not_found",
                message="La sucursal solicitada no existe.",
            )
        return store

    # --- device operations ------------------------------------------
    def create_device(self, store_id: int, payload: dict[str, Any]) -> Device:
        store = self.get_store(store_id)
        data = _validate_device_payload(payload)
        if any(
            device.sku.lower() == data["sku"].lower()
            for device in self.devices.values()
            if device.store_id == store.id
        ):
            raise SoftmobileError(
                status_code=int(HTTPStatus.CONFLICT),
                code="device_already_exists",
                message="Ya existe un dispositivo con ese SKU en la sucursal.",
            )
        self._device_sequence += 1
        device = Device(id=self._device_sequence, store_id=store.id, **data)
        self.devices[device.id] = device
        return device

    def list_devices(self, store_id: int) -> list[Device]:
        store = self.get_store(store_id)
        return sorted(
            [device for device in self.devices.values() if device.store_id == store.id],
            key=lambda device: device.sku.lower(),
        )


def _validate_store_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SoftmobileError(
            status_code=int(HTTPStatus.BAD_REQUEST),
            code="invalid_store_payload",
            message="Se esperaba un objeto JSON para la sucursal.",
        )
    name = _require_string(payload, "name", max_length=120)
    location = _optional_string(payload, "location", max_length=255)
    phone = _optional_string(payload, "phone", max_length=30)
    manager = _optional_string(payload, "manager", max_length=120)
    status = _optional_string(payload, "status", default="activa", max_length=30)
    code = _optional_string(payload, "code", max_length=20)
    timezone = _optional_string(payload, "timezone", default="UTC", max_length=50)
    return {
        "name": name,
        "location": location,
        "phone": phone,
        "manager": manager,
        "status": status or "activa",
        "code": code,
        "timezone": timezone or "UTC",
    }


def _validate_device_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SoftmobileError(
            status_code=int(HTTPStatus.BAD_REQUEST),
            code="invalid_device_payload",
            message="Se esperaba un objeto JSON para el dispositivo.",
        )
    sku = _require_string(payload, "sku", max_length=80)
    name = _require_string(payload, "name", max_length=120)
    quantity = payload.get("quantity", 0)
    if not isinstance(quantity, int) or quantity < 0:
        raise SoftmobileError(
            status_code=int(HTTPStatus.BAD_REQUEST),
            code="invalid_quantity",
            message="La cantidad debe ser un entero positivo o cero.",
        )
    return {"sku": sku, "name": name, "quantity": quantity}


def _require_string(payload: dict[str, Any], key: str, *, max_length: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SoftmobileError(
            status_code=int(HTTPStatus.BAD_REQUEST),
            code=f"missing_{key}",
            message=f"El campo '{key}' es obligatorio.",
        )
    value = value.strip()
    if len(value) > max_length:
        raise SoftmobileError(
            status_code=int(HTTPStatus.BAD_REQUEST),
            code=f"{key}_too_long",
            message=f"El campo '{key}' supera el máximo de {max_length} caracteres.",
        )
    return value


def _optional_string(
    payload: dict[str, Any],
    key: str,
    *,
    default: str | None = None,
    max_length: int,
) -> str | None:
    value = payload.get(key, default)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SoftmobileError(
            status_code=int(HTTPStatus.BAD_REQUEST),
            code=f"invalid_{key}",
            message=f"El campo '{key}' debe ser una cadena si se proporciona.",
        )
    value = value.strip()
    if len(value) > max_length:
        raise SoftmobileError(
            status_code=int(HTTPStatus.BAD_REQUEST),
            code=f"{key}_too_long",
            message=f"El campo '{key}' supera el máximo de {max_length} caracteres.",
        )
    return value
