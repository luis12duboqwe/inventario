"""
Utilidades para el sistema POS (Point of Sale).

Extraídas desde crud_legacy.py para separación de responsabilidades.
"""

from backend.app import models, schemas
from backend.app.services import promotions
from backend.app.utils.decimal_helpers import to_decimal


def repair_payload(order: models.RepairOrder) -> dict[str, object]:
    """Serializa una orden de reparación."""
    return {
        "id": order.id,
        "store_id": order.store_id,
        "status": order.status.value,
        "technician_name": order.technician_name,
        "customer_id": order.customer_id,
        "customer_name": order.customer_name,
        "customer_contact": order.customer_contact,
        "damage_type": order.damage_type,
        "diagnosis": order.diagnosis,
        "device_model": order.device_model,
        "imei": order.imei,
        "labor_cost": float(order.labor_cost),
        "parts_cost": float(order.parts_cost),
        "total_cost": float(order.total_cost),
        "updated_at": order.updated_at.isoformat(),
        "parts_snapshot": order.parts_snapshot,
    }


def pos_config_payload(config: models.POSConfig) -> dict[str, object]:
    """Serializa configuración del POS."""
    return {
        "store_id": config.store_id,
        "tax_rate": float(config.tax_rate),
        "invoice_prefix": config.invoice_prefix,
        "printer_name": config.printer_name,
        "printer_profile": config.printer_profile,
        "quick_product_ids": config.quick_product_ids,
        "promotions_config": config.promotions_config,
        "hardware_settings": config.hardware_settings,
        "updated_at": config.updated_at.isoformat(),
    }


def build_pos_promotions_response(
    config: models.POSConfig,
) -> schemas.POSPromotionsResponse:
    """Construye respuesta de promociones POS."""
    normalized = promotions.load_config(config.promotions_config)
    return schemas.POSPromotionsResponse(
        store_id=config.store_id,
        feature_flags=normalized.feature_flags,
        volume_promotions=normalized.volume_promotions,
        combo_promotions=normalized.combo_promotions,
        coupons=normalized.coupons,
        updated_at=config.updated_at,
    )


def pos_draft_payload(draft: models.POSDraftSale) -> dict[str, object]:
    """Serializa un borrador de venta POS."""
    return {
        "id": draft.id,
        "store_id": draft.store_id,
        "payload": draft.payload,
        "updated_at": draft.updated_at.isoformat(),
    }


def store_credit_payload(credit: models.StoreCredit) -> dict[str, object]:
    """Serializa un crédito de tienda."""
    return {
        "id": credit.id,
        "customer_id": credit.customer_id,
        "code": credit.code,
        "issued_amount": float(to_decimal(credit.issued_amount)),
        "balance_amount": float(to_decimal(credit.balance_amount)),
        "status": credit.status.value,
        "issued_at": credit.issued_at.isoformat(),
        "redeemed_at": credit.redeemed_at.isoformat() if credit.redeemed_at else None,
        "expires_at": credit.expires_at.isoformat() if credit.expires_at else None,
        "context": credit.context or {},
    }


def store_credit_redemption_payload(
    redemption: models.StoreCreditRedemption,
) -> dict[str, object]:
    """Serializa una redención de crédito de tienda."""
    return {
        "id": redemption.id,
        "store_credit_id": redemption.store_credit_id,
        "sale_id": redemption.sale_id,
        "amount": float(to_decimal(redemption.amount)),
        "notes": redemption.notes,
        "created_at": redemption.created_at.isoformat(),
        "created_by_id": redemption.created_by_id,
    }


def loyalty_account_payload(account: models.LoyaltyAccount) -> dict[str, object]:
    """Serializa una cuenta de lealtad."""
    return {
        "id": account.id,
        "customer_id": account.customer_id,
        "points_balance": float(to_decimal(account.points_balance)),
        "tier": account.tier,
        "status": account.status.value,
        "created_at": account.created_at.isoformat(),
        "updated_at": account.updated_at.isoformat(),
        "last_activity_at": account.last_activity_at.isoformat() if account.last_activity_at else None,
        "expires_at": account.expires_at.isoformat() if account.expires_at else None,
    }


def loyalty_transaction_payload(
    transaction: models.LoyaltyTransaction,
) -> dict[str, object]:
    """Serializa una transacción de lealtad."""
    return {
        "id": transaction.id,
        "loyalty_account_id": transaction.loyalty_account_id,
        "transaction_type": transaction.transaction_type.value,
        "points_change": float(to_decimal(transaction.points_change)),
        "balance_after": float(to_decimal(transaction.balance_after)),
        "reference_type": transaction.reference_type,
        "reference_id": transaction.reference_id,
        "notes": transaction.notes,
        "created_at": transaction.created_at.isoformat(),
        "created_by_id": transaction.created_by_id,
    }
