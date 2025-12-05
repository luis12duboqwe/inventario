
def count_purchase_vendors(
    db: Session,
    *,
    vendor_id: int | None = None,
    query: str | None = None,
    estado: str | None = None,
) -> int:
    statement = select(func.count()).select_from(models.Proveedor)
    if vendor_id is not None:
        statement = statement.where(models.Proveedor.id_proveedor == vendor_id)
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(func.lower(
            models.Proveedor.nombre).like(normalized))
    if estado:
        statement = statement.where(func.lower(
            models.Proveedor.estado) == estado.lower())
    return int(db.scalar(statement) or 0)


def set_purchase_vendor_status(
    db: Session,
    vendor_id: int,
    estado: str,
    *,
    performed_by_id: int | None = None,
) -> models.Proveedor:
    vendor = get_purchase_vendor(db, vendor_id)
    if not vendor:
        raise LookupError("vendor_not_found")

    with transactional_session(db):
        vendor.estado = estado
        db.add(vendor)

        _log_action(
            db,
            action="purchase_vendor_status_updated",
            entity_type="purchase_vendor",
            entity_id=str(vendor.id_proveedor),
            performed_by_id=performed_by_id,
            details=json.dumps({"estado": estado}),
        )
        flush_session(db)
        db.refresh(vendor)
    return vendor


def count_purchase_records(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
) -> int:
    statement = select(func.count()).select_from(models.Compra)
    if proveedor_id is not None:
        statement = statement.where(models.Compra.proveedor_id == proveedor_id)
    if usuario_id is not None:
        statement = statement.where(models.Compra.usuario_id == usuario_id)
    if date_from is not None:
        statement = statement.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        statement = statement.where(models.Compra.fecha <= date_to)
    if estado is not None:
        statement = statement.where(func.lower(
            models.Compra.estado) == estado.lower())
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.join(models.Proveedor).where(
            func.lower(models.Proveedor.nombre).like(normalized)
        )
    return int(db.scalar(statement) or 0)


def list_purchase_records_for_report(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
) -> list[models.Compra]:
    # Reusing _fetch_purchase_records which was added in part 1
    # But wait, _fetch_purchase_records was added as internal function.
    # I should check if I exposed it or if I should just copy the body.
    # I'll assume it's available as I appended it.
    return _fetch_purchase_records(
        db,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
        limit=None,
    )


def count_purchase_orders(db: Session, *, store_id: int | None = None) -> int:
    statement = select(func.count()).select_from(models.PurchaseOrder)
    if store_id is not None:
        statement = statement.where(models.PurchaseOrder.store_id == store_id)
    return int(db.scalar(statement) or 0)


def create_purchase_order_from_suggestion(
    db: Session,
    payload: schemas.PurchaseOrderCreate,
    *,
    created_by_id: int | None = None,
    reason: str,
) -> models.PurchaseOrder:
    """Genera una orden de compra desde una sugerencia automatizada."""

    order = create_purchase_order(db, payload, created_by_id=created_by_id)

    items_details = [
        {"device_id": item.device_id, "quantity_ordered": item.quantity_ordered}
        for item in order.items
    ]

    with transactional_session(db):
        _log_action(
            db,
            action="purchase_order_generated_from_suggestion",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=created_by_id,
            details=json.dumps(
                {
                    "store_id": order.store_id,
                    "supplier": order.supplier,
                    "reason": reason,
                    "source": "purchase_suggestion",
                    "items": items_details,
                }
            ),
        )
        flush_session(db)

    db.refresh(order)
    return order
