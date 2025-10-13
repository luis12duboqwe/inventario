"""Version 1 of the public API."""
from fastapi import APIRouter

from .endpoints import devices, health, stores

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stores.router, prefix="/stores", tags=["stores"])
api_router.include_router(
    devices.router, prefix="/stores/{store_id}/devices", tags=["devices"]
)
