
def _purchase_record_statement():
    return (
        select(models.Compra)
        .options(
            joinedload(models.Compra.proveedor),
            joinedload(models.Compra.usuario),
            joinedload(models.Compra.detalles).joinedload(
                models.DetalleCompra.producto),
        )
        .order_by(models.Compra.fecha.desc(), models.Compra.id_compra.desc())
    )


def _apply_purchase_record_filters(
    statement,
    *,
    proveedor_id: int | None,
    usuario_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    estado: str | None,
    query: str | None,
):
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
    return statement


def _fetch_purchase_records(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.Compra]:
    statement = _purchase_record_statement()
    statement = _apply_purchase_record_filters(
        statement,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
    )
    if limit is not None:
        statement = statement.limit(limit)
    if offset:
        statement = statement.offset(offset)
    return list(db.scalars(statement).unique())
