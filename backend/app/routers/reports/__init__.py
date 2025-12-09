from fastapi import APIRouter

from .global_reports import router as global_router
from .fiscal import router as fiscal_router
from .sales import router as sales_router
from .customers import router as customers_router
from .audit import router as audit_router
from .analytics import router as analytics_router
from .inventory import router as inventory_router

router = APIRouter(prefix="/reports")

router.include_router(global_router)
router.include_router(fiscal_router)
router.include_router(sales_router)
router.include_router(customers_router)
router.include_router(audit_router)
router.include_router(analytics_router)
router.include_router(inventory_router)
