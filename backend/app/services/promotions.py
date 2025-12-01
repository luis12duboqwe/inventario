"""Motor de promociones para el POS corporativo."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from pydantic import ValidationError

from .. import schemas


DEFAULT_PROMOTIONS_CONFIG: schemas.POSPromotionsConfig = schemas.POSPromotionsConfig()


@dataclass
class PromotionFeatureSwitches:
    """Conjunto de banderas finales para habilitar promociones."""

    volume: bool = False
    combos: bool = False
    coupons: bool = False

    @property
    def any_enabled(self) -> bool:
        return self.volume or self.combos or self.coupons


@dataclass
class PromotionApplication:
    """Representa una promoción aplicada a la venta."""

    promotion_id: str
    promotion_type: str
    description: str
    discount_percent: Decimal | None = None
    coupon_code: str | None = None
    affected_items: dict[int, int] = field(default_factory=dict)


@dataclass
class PromotionComputation:
    """Resultado del motor de promociones."""

    sale_request: schemas.POSSaleRequest
    applications: list[PromotionApplication]


def load_config(raw: Mapping[str, object] | None) -> schemas.POSPromotionsConfig:
    """Construye un esquema de configuración seguro desde la base de datos."""

    if not raw:
        return schemas.POSPromotionsConfig()
    try:
        return schemas.POSPromotionsConfig.model_validate(raw)
    except ValidationError:
        return schemas.POSPromotionsConfig()


def resolve_feature_switches(
    *,
    global_volume: bool,
    global_combo: bool,
    global_coupon: bool,
    config_flags: schemas.POSPromotionFeatureFlags,
) -> PromotionFeatureSwitches:
    """Determina qué promociones deben evaluarse considerando banderas globales."""

    return PromotionFeatureSwitches(
        volume=global_volume and config_flags.volume,
        combos=global_combo and config_flags.combos,
        coupons=global_coupon and config_flags.coupons,
    )


def apply_promotions(
    sale_request: schemas.POSSaleRequest,
    *,
    config: schemas.POSPromotionsConfig,
    switches: PromotionFeatureSwitches,
) -> PromotionComputation:
    """Aplica reglas de promociones sobre una venta POS previa a su registro."""

    if not switches.any_enabled:
        return PromotionComputation(sale_request=sale_request, applications=[])

    mutable_request = sale_request.model_copy(deep=True)
    applications: dict[str, PromotionApplication] = {}
    assigned_discount: dict[int, Decimal] = {}
    device_promotions: dict[int, str] = {}

    _apply_volume_promotions(
        mutable_request,
        config,
        switches,
        applications,
        assigned_discount,
        device_promotions,
    )
    _apply_combo_promotions(
        mutable_request,
        config,
        switches,
        applications,
        assigned_discount,
        device_promotions,
    )
    _apply_coupon_promotions(mutable_request, config, switches, applications, assigned_discount)

    return PromotionComputation(
        sale_request=mutable_request,
        applications=list(applications.values()),
    )


def _apply_volume_promotions(
    sale_request: schemas.POSSaleRequest,
    config: schemas.POSPromotionsConfig,
    switches: PromotionFeatureSwitches,
    applications: dict[str, PromotionApplication],
    assigned_discount: dict[int, Decimal],
    device_promotions: dict[int, str],
) -> None:
    if not switches.volume:
        return

    for rule in config.volume_promotions:
        for index, item in enumerate(sale_request.items):
            if item.device_id is None or item.device_id != rule.device_id:
                continue
            if item.quantity < rule.min_quantity:
                continue
            current_discount = assigned_discount.get(item.device_id, item.discount_percent or Decimal("0"))
            if current_discount >= rule.discount_percent:
                continue
            sale_request.items[index] = item.model_copy(update={"discount_percent": rule.discount_percent})
            assigned_discount[item.device_id] = rule.discount_percent
            key = f"volume::{rule.id}"
            application = applications.get(key)
            if application is None:
                application = PromotionApplication(
                    promotion_id=rule.id,
                    promotion_type="volume",
                    description=f"Volumen mínimo {rule.min_quantity}",
                    discount_percent=rule.discount_percent,
                )
                applications[key] = application
            application.affected_items[item.device_id] = item.quantity
            device_promotions[item.device_id] = key


def _apply_combo_promotions(
    sale_request: schemas.POSSaleRequest,
    config: schemas.POSPromotionsConfig,
    switches: PromotionFeatureSwitches,
    applications: dict[str, PromotionApplication],
    assigned_discount: dict[int, Decimal],
    device_promotions: dict[int, str],
) -> None:
    if not switches.combos or not config.combo_promotions:
        return

    item_quantities: dict[int, int] = {}
    for item in sale_request.items:
        if item.device_id is None:
            continue
        item_quantities[item.device_id] = item_quantities.get(item.device_id, 0) + item.quantity

    for rule in config.combo_promotions:
        if not rule.items:
            continue
        if not _combo_is_available(rule.items, item_quantities):
            continue
        key = f"combo::{rule.id}"
        application = PromotionApplication(
            promotion_id=rule.id,
            promotion_type="combo",
            description="Combo calificado",
            discount_percent=rule.discount_percent,
        )
        for index, item in enumerate(sale_request.items):
            if item.device_id is None:
                continue
            required = next((entry.quantity for entry in rule.items if entry.device_id == item.device_id), None)
            if required is None:
                continue
            current_discount = assigned_discount.get(item.device_id, item.discount_percent or Decimal("0"))
            if current_discount >= rule.discount_percent:
                continue
            previous_key = device_promotions.get(item.device_id)
            if previous_key and previous_key in applications:
                previous_app = applications[previous_key]
                previous_app.affected_items.pop(item.device_id, None)
                if not previous_app.affected_items:
                    applications.pop(previous_key, None)
            sale_request.items[index] = item.model_copy(update={"discount_percent": rule.discount_percent})
            assigned_discount[item.device_id] = rule.discount_percent
            application.affected_items[item.device_id] = item.quantity
            device_promotions[item.device_id] = key
        if application.affected_items:
            applications[key] = application


def _combo_is_available(
    required_items: Sequence[schemas.POSComboPromotionItem],
    quantities: Mapping[int, int],
) -> bool:
    for required in required_items:
        available = quantities.get(required.device_id, 0)
        if available < required.quantity:
            return False
    return True


def _apply_coupon_promotions(
    sale_request: schemas.POSSaleRequest,
    config: schemas.POSPromotionsConfig,
    switches: PromotionFeatureSwitches,
    applications: dict[str, PromotionApplication],
    assigned_discount: dict[int, Decimal],
) -> None:
    if not switches.coupons or not sale_request.coupons:
        return

    normalized = [code.strip().upper() for code in sale_request.coupons if code.strip()]
    if not normalized:
        sale_request.coupons = []
        return

    coupon_map = {coupon.code.upper(): coupon for coupon in config.coupons}
    chosen = None
    for code in normalized:
        rule = coupon_map.get(code)
        if rule is None:
            continue
        if chosen is None or rule.discount_percent > chosen.discount_percent:
            chosen = rule
    if chosen is None:
        sale_request.coupons = []
        return

    sale_request.coupons = [chosen.code]
    sale_discount = sale_request.discount_percent or Decimal("0")
    if sale_discount < chosen.discount_percent:
        sale_request.discount_percent = chosen.discount_percent

    unassigned_items = [
        item.device_id
        for item in sale_request.items
        if item.device_id is not None and item.device_id not in assigned_discount
    ]
    applications["coupon::" + chosen.code] = PromotionApplication(
        promotion_id=chosen.code,
        promotion_type="coupon",
        description=chosen.description or "Cupón aplicado",
        discount_percent=chosen.discount_percent,
        coupon_code=chosen.code,
        affected_items={device_id: 0 for device_id in unassigned_items},
    )


def summarize_applications(
    sale: schemas.SaleResponse,
    applications: Iterable[PromotionApplication],
) -> list[schemas.POSAppliedPromotion]:
    """Convierte las promociones aplicadas en respuestas serializables para la API."""

    sale_items = {item.device_id: item for item in sale.items}
    summaries: list[schemas.POSAppliedPromotion] = []

    coupon_application: PromotionApplication | None = None
    for application in applications:
        if application.promotion_type == "coupon":
            coupon_application = application
            continue
        amount = Decimal("0")
        affected_ids: list[int] = []
        for device_id in application.affected_items:
            sale_item = sale_items.get(device_id)
            if sale_item is None:
                continue
            amount += sale_item.discount_amount
            affected_ids.append(device_id)
        summaries.append(
            schemas.POSAppliedPromotion(
                id=application.promotion_id,
                promotion_type=application.promotion_type,
                description=application.description,
                discount_percent=application.discount_percent or Decimal("0"),
                discount_amount=amount,
                affected_items=affected_ids,
                coupon_code=None,
            )
        )

    if coupon_application is not None:
        amount = Decimal("0")
        affected_ids: list[int] = []
        for device_id, sale_item in sale_items.items():
            if device_id in coupon_application.affected_items and sale_item.discount_amount > 0:
                amount += sale_item.discount_amount
                affected_ids.append(device_id)
        summaries.append(
            schemas.POSAppliedPromotion(
                id=coupon_application.promotion_id,
                promotion_type="coupon",
                description=coupon_application.description,
                discount_percent=coupon_application.discount_percent or Decimal("0"),
                discount_amount=amount,
                affected_items=affected_ids,
                coupon_code=coupon_application.coupon_code,
            )
        )

    return summaries
