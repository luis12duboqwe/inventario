"""Servicios de generación de reportes y respaldos empresariales."""
from __future__ import annotations

import enum
import json
import shutil
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Iterable, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .. import crud, models
from ..config import settings as app_settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANDATORY_COMPONENTS: set[models.BackupComponent] = {
    models.BackupComponent.DATABASE,
    models.BackupComponent.CONFIGURATION,
    models.BackupComponent.CRITICAL_FILES,
}
CRITICAL_PATHS: tuple[Path, ...] = (
    PROJECT_ROOT / "backend" / "app" / "config.py",
    PROJECT_ROOT / "backend" / "app" / "main.py",
    PROJECT_ROOT / "backend" / "app" / "security.py",
    PROJECT_ROOT / "environment.yml",
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "README.md",
)


def build_inventory_snapshot(db: Session) -> dict[str, Any]:
    """Obtiene un snapshot completo de los datos de inventario."""

    return crud.build_inventory_snapshot(db)


def _normalize_components(
    components: Iterable[models.BackupComponent | str] | None,
    *,
    include_mandatory: bool = True,
) -> list[str]:
    selected: set[models.BackupComponent] = set()
    if include_mandatory:
        selected.update(MANDATORY_COMPONENTS)
    if components:
        for component in components:
            if isinstance(component, models.BackupComponent):
                selected.add(component)
            else:
                selected.add(models.BackupComponent(str(component)))
    return sorted(component.value for component in selected)


def _build_configuration_snapshot() -> dict[str, Any]:
    snapshot = app_settings.model_dump()
    if "secret_key" in snapshot:
        snapshot["secret_key"] = "***redactado***"
    return snapshot


def _to_sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, enum.Enum):
        return _to_sql_literal(value.name)
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, datetime):
        return f"'{value.isoformat()}'"
    if isinstance(value, date):
        return f"'{value.isoformat()}'"
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    return "'" + str(value).replace("'", "''") + "'"


def _dump_database_sql(db: Session) -> bytes:
    bind = db.get_bind()
    if bind is None:
        raise RuntimeError("No se pudo obtener la conexión activa para generar el volcado SQL")

    statements: list[str] = ["BEGIN TRANSACTION;\n"]
    metadata = models.Base.metadata
    for table in metadata.sorted_tables:
        if table.name in {"backup_jobs"}:
            continue
        statements.append(f'DELETE FROM "{table.name}";\n')
        rows = db.execute(select(table)).mappings().all()
        if not rows:
            continue
        columns = ", ".join(f'"{column.name}"' for column in table.columns)
        for row in rows:
            values = ", ".join(_to_sql_literal(row[column.name]) for column in table.columns)
            statements.append(
                f'INSERT INTO "{table.name}" ({columns}) VALUES ({values});\n'
            )
    statements.append("COMMIT;\n")
    return "".join(statements).encode("utf-8")


def _collect_critical_files(destination: Path) -> list[str]:
    copied: list[str] = []
    for critical_path in CRITICAL_PATHS:
        if not critical_path.exists():
            continue
        relative = critical_path.relative_to(PROJECT_ROOT)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(critical_path, target)
        copied.append(str(relative))
    return copied


def _write_metadata(
    metadata_path: Path,
    *,
    timestamp: str,
    mode: models.BackupMode,
    notes: str | None,
    components: list[str],
    json_path: Path,
    sql_path: Path,
    pdf_path: Path,
    archive_path: Path,
    config_path: Path,
    critical_directory: Path,
    copied_files: list[str],
) -> None:
    metadata = {
        "timestamp": timestamp,
        "mode": mode.value,
        "notes": notes,
        "components": components,
        "files": {
            "json": str(json_path),
            "sql": str(sql_path),
            "pdf": str(pdf_path),
            "zip": str(archive_path),
            "config": str(config_path),
            "critical_directory": str(critical_directory),
        },
        "critical_files": copied_files,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def _calculate_total_size(paths: Iterable[Path]) -> int:
    total = 0
    for path in paths:
        if path.is_file():
            total += path.stat().st_size
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    total += file_path.stat().st_size
    return total
def _build_financial_table(devices: list[dict[str, Any]]) -> Tuple[list[list[str]], float]:
    table_data = [
        [
            "SKU",
            "Nombre",
            "Cantidad",
            "Precio",
            "Valor total",
            "IMEI",
            "Serie",
            "Marca",
            "Modelo",
            "Proveedor",
        ]
    ]
    store_total = 0.0
    for device in devices:
        unit_price = float(device.get("unit_price", 0.0))
        total_value = float(device.get("inventory_value", device["quantity"] * unit_price))
        store_total += total_value
        table_data.append(
            [
                device["sku"],
                device["name"],
                str(device["quantity"]),
                f"${unit_price:,.2f}",
                f"${total_value:,.2f}",
                device.get("imei") or "-",
                device.get("serial") or "-",
                device.get("marca") or "-",
                device.get("modelo") or "-",
                device.get("proveedor") or "-",
            ]
        )

    return table_data, store_total


def _build_catalog_detail_table(devices: list[dict[str, Any]]) -> list[list[str]]:
    detail_table_data = [
        [
            "SKU",
            "Color",
            "Capacidad (GB)",
            "Estado",
            "Lote",
            "Fecha compra",
            "Garantía (meses)",
            "Costo unitario",
            "Margen (%)",
        ]
    ]

    for device in devices:
        capacidad = device.get("capacidad_gb")
        detail_table_data.append(
            [
                device["sku"],
                device.get("color") or "-",
                str(capacidad) if capacidad is not None else "-",
                device.get("estado_comercial", "-"),
                device.get("lote") or "-",
                device.get("fecha_compra") or "-",
                str(device.get("garantia_meses", "-")),
                f"${float(device.get('costo_unitario', 0.0)):,.2f}",
                f"{float(device.get('margen_porcentaje', 0.0)):.2f}%",
            ]
        )

    return detail_table_data


def render_snapshot_pdf(snapshot: dict[str, Any]) -> bytes:
    """Construye un PDF en tema oscuro con el estado del inventario."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Softmobile - Inventario Consolidado")
    styles = getSampleStyleSheet()

    elements = [Paragraph("Softmobile 2025 — Reporte Empresarial", styles["Title"]), Spacer(1, 12)]
    generated_at = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
    elements.append(Paragraph(f"Generado automáticamente el {generated_at}", styles["Normal"]))
    elements.append(Spacer(1, 18))

    consolidated_total = 0.0

    for store in snapshot.get("stores", []):
        elements.append(Paragraph(f"Sucursal: {store['name']} ({store['timezone']})", styles["Heading2"]))
        if store.get("location"):
            elements.append(Paragraph(f"Ubicación: {store['location']}", styles["Normal"]))
        devices = store.get("devices", [])
        if not devices:
            elements.append(Paragraph("Sin dispositivos registrados", styles["Italic"]))
            elements.append(Spacer(1, 12))
            continue

        table_data, store_total = _build_financial_table(devices)

        registered_value_raw = store.get("inventory_value")
        try:
            registered_value = float(registered_value_raw) if registered_value_raw is not None else None
        except (TypeError, ValueError):
            registered_value = None

        elements.append(
            Paragraph(
                f"Valor calculado (sumatoria de dispositivos): ${store_total:,.2f}",
                styles["Normal"],
            )
        )
        if registered_value is not None:
            elements.append(
                Paragraph(
                    f"Valor registrado en sucursal: ${registered_value:,.2f}",
                    styles["Normal"],
                )
            )
        elements.append(Paragraph(f"Valor total de la sucursal: ${store_total:,.2f}", styles["Normal"]))
        elements.append(Spacer(1, 6))
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#e2e8f0")),
                    ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#38bdf8")),
                    ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#38bdf8")),
                    ("ALIGN", (2, 1), (4, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 12))

        detail_table_data = _build_catalog_detail_table(devices)

        detail_table = Table(detail_table_data, hAlign="LEFT")
        detail_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#cbd5f5")),
                    ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#38bdf8")),
                    ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#38bdf8")),
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),
                    ("ALIGN", (4, 1), (5, -1), "CENTER"),
                    ("ALIGN", (6, 1), (8, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(detail_table)
        elements.append(Spacer(1, 18))

        consolidated_total += store_total

    summary = snapshot.get("summary") or {}
    if summary:
        summary_value_raw = summary.get("inventory_value")
        try:
            summary_value = float(summary_value_raw) if summary_value_raw is not None else 0.0
        except (TypeError, ValueError):
            summary_value = 0.0

        elements.append(Paragraph("Resumen corporativo", styles["Heading2"]))
        elements.append(Paragraph(f"Sucursales auditadas: {summary.get('store_count', 0)}", styles["Normal"]))
        elements.append(
            Paragraph(
                f"Dispositivos catalogados: {summary.get('device_records', 0)}",
                styles["Normal"],
            )
        )
        elements.append(
            Paragraph(
                f"Unidades totales en inventario: {summary.get('total_units', 0)}",
                styles["Normal"],
            )
        )
        elements.append(
            Paragraph(
                f"Inventario consolidado registrado: ${summary_value:,.2f}",
                styles["Normal"],
            )
        )
        elements.append(
            Paragraph(
                f"Inventario consolidado calculado: ${consolidated_total:,.2f}",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 18))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def serialize_snapshot(snapshot: dict[str, Any]) -> bytes:
    """Serializa el snapshot en formato JSON."""

    return json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")


def _restore_database(db: Session, sql_path: Path) -> None:
    if not sql_path.exists():
        raise FileNotFoundError(str(sql_path))

    bind = db.get_bind()
    if bind is None:
        raise RuntimeError("No se pudo obtener la conexión activa para restaurar la base de datos")

    engine = bind.engine if hasattr(bind, "engine") else bind
    sql_script = sql_path.read_text(encoding="utf-8")
    if engine.dialect.name == "sqlite":
        raw_connection = engine.raw_connection()
        try:
            cursor = raw_connection.cursor()
            cursor.executescript(sql_script)
            raw_connection.commit()
        finally:
            raw_connection.close()
    else:
        statements = [segment.strip() for segment in sql_script.split(";") if segment.strip()]
        with db.begin():
            for statement in statements:
                upper = statement.upper()
                if upper in {"BEGIN TRANSACTION", "COMMIT"}:
                    continue
                db.execute(text(statement))


def generate_backup(
    db: Session,
    *,
    base_dir: str,
    mode: models.BackupMode,
    triggered_by_id: int | None,
    notes: str | None = None,
    components: Iterable[models.BackupComponent] | None = None,
    reason: str | None = None,
) -> models.BackupJob:
    """Genera los archivos de respaldo y persiste el registro en la base."""

    selected_components = _normalize_components(components, include_mandatory=True)
    snapshot = build_inventory_snapshot(db)
    pdf_bytes = render_snapshot_pdf(snapshot)
    json_bytes = serialize_snapshot(snapshot)
    sql_bytes = _dump_database_sql(db)
    config_snapshot = _build_configuration_snapshot()

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    directory = Path(base_dir)
    directory.mkdir(parents=True, exist_ok=True)

    pdf_path = directory / f"softmobile_inventario_{timestamp}.pdf"
    json_path = directory / f"softmobile_respaldo_{timestamp}.json"
    sql_path = directory / f"softmobile_respaldo_{timestamp}.sql"
    config_path = directory / f"softmobile_config_{timestamp}.json"
    metadata_path = directory / f"softmobile_respaldo_{timestamp}.meta.json"
    archive_path = directory / f"softmobile_respaldo_{timestamp}.zip"
    critical_directory = directory / f"softmobile_criticos_{timestamp}"
    critical_directory.mkdir(parents=True, exist_ok=True)

    pdf_path.write_bytes(pdf_bytes)
    json_path.write_bytes(json_bytes)
    sql_path.write_bytes(sql_bytes)
    config_path.write_text(json.dumps(config_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    copied_files = _collect_critical_files(critical_directory)
    _write_metadata(
        metadata_path,
        timestamp=timestamp,
        mode=mode,
        notes=notes,
        components=selected_components,
        json_path=json_path,
        sql_path=sql_path,
        pdf_path=pdf_path,
        archive_path=archive_path,
        config_path=config_path,
        critical_directory=critical_directory,
        copied_files=copied_files,
    )

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as zip_file:
        zip_file.write(pdf_path, arcname=f"reportes/{pdf_path.name}")
        zip_file.write(json_path, arcname=f"datos/{json_path.name}")
        zip_file.write(sql_path, arcname=f"datos/{sql_path.name}")
        zip_file.write(config_path, arcname=f"config/{config_path.name}")
        zip_file.write(metadata_path, arcname=f"metadata/{metadata_path.name}")
        for file_path in critical_directory.rglob("*"):
            if file_path.is_file():
                arcname = Path("criticos") / file_path.relative_to(critical_directory)
                zip_file.write(file_path, arcname=str(arcname))

    total_size = _calculate_total_size(
        [pdf_path, json_path, sql_path, config_path, metadata_path, archive_path, critical_directory]
    )

    job = crud.create_backup_job(
        db,
        mode=mode,
        pdf_path=str(pdf_path.resolve()),
        archive_path=str(archive_path.resolve()),
        json_path=str(json_path.resolve()),
        sql_path=str(sql_path.resolve()),
        config_path=str(config_path.resolve()),
        metadata_path=str(metadata_path.resolve()),
        critical_directory=str(critical_directory.resolve()),
        components=selected_components,
        total_size_bytes=total_size,
        notes=notes,
        triggered_by_id=triggered_by_id,
        reason=reason.strip() if reason else None,
    )
    return job


def restore_backup(
    db: Session,
    *,
    job: models.BackupJob,
    components: Iterable[models.BackupComponent] | None,
    target_directory: str | None,
    apply_database: bool,
    triggered_by_id: int | None,
    reason: str | None = None,
) -> dict[str, Any]:
    if components:
        requested_components: set[models.BackupComponent] = set()
        for component in components:
            if isinstance(component, models.BackupComponent):
                requested_components.add(component)
            else:
                requested_components.add(models.BackupComponent(str(component)))
    else:
        requested_components = {models.BackupComponent(component) for component in job.components}

    available_components = {models.BackupComponent(component) for component in job.components}
    if not available_components:
        raise ValueError("El respaldo no tiene componentes registrados para restaurar")

    unknown_components = requested_components.difference(available_components)
    if unknown_components:
        nombres = ", ".join(component.value for component in sorted(unknown_components, key=lambda c: c.value))
        raise ValueError(f"Componentes no disponibles en el respaldo: {nombres}")

    selected_components = _normalize_components(
        requested_components or available_components,
        include_mandatory=False,
    )
    job_id = int(job.id)
    archive_file = Path(job.archive_path)
    json_file = Path(job.json_path)
    sql_file = Path(job.sql_path)
    config_file = Path(job.config_path)
    metadata_file = Path(job.metadata_path)
    critical_source = Path(job.critical_directory)

    target_base = Path(target_directory) if target_directory else archive_file.parent
    restore_dir = target_base / f"restauracion_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    restore_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, str] = {}

    if json_file.exists():
        json_dest = restore_dir / json_file.name
        shutil.copy2(json_file, json_dest)
        results["json"] = str(json_dest)

    if models.BackupComponent.DATABASE.value in selected_components:
        if not sql_file.exists():
            results["database"] = "Archivo SQL no disponible"
        elif apply_database:
            _restore_database(db, sql_file)
            results["database"] = "Base de datos restaurada en la instancia activa"
        else:
            sql_dest = restore_dir / sql_file.name
            shutil.copy2(sql_file, sql_dest)
            results["database"] = str(sql_dest)

    if models.BackupComponent.CONFIGURATION.value in selected_components and config_file.exists():
        config_dest = restore_dir / config_file.name
        shutil.copy2(config_file, config_dest)
        results["configuration"] = str(config_dest)

    if metadata_file.exists():
        metadata_dest = restore_dir / metadata_file.name
        shutil.copy2(metadata_file, metadata_dest)
        results["metadata"] = str(metadata_dest)

    if archive_file.exists():
        archive_dest = restore_dir / archive_file.name
        shutil.copy2(archive_file, archive_dest)
        results["zip"] = str(archive_dest)

    if (
        models.BackupComponent.CRITICAL_FILES.value in selected_components
        and critical_source.exists()
    ):
        critical_dest = restore_dir / "archivos_criticos"
        for file_path in critical_source.rglob("*"):
            if file_path.is_file():
                destination = critical_dest / file_path.relative_to(critical_source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, destination)
        results["critical_files"] = str(critical_dest)

    crud.register_backup_restore(
        db,
        backup_id=job_id,
        triggered_by_id=triggered_by_id,
        components=selected_components,
        destination=str(restore_dir.resolve()),
        applied_database=apply_database,
        reason=reason.strip() if reason else None,
    )
    db.commit()

    return {
        "job_id": job_id,
        "componentes": [models.BackupComponent(component) for component in selected_components],
        "destino": str(restore_dir.resolve()),
        "resultados": results,
    }
