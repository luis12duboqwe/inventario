"""Estabilización temporal del paquete de respaldo durante REC-0004.

El generador heredado reescribe metadatos cifrados varias veces dentro del ZIP.
Fernet produce ciphertext distinto en cada escritura y DEFLATE puede variar un
byte, por lo que el tamaño guardado puede oscilar. Este puente conserva todos
los artefactos y vuelve determinista únicamente la entrada de metadatos.
"""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from sqlalchemy.orm import Session

from .. import models
from . import backups, encryption


def _artifact_paths(job: models.BackupJob) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    return (
        Path(job.pdf_path),
        Path(job.archive_path),
        Path(job.json_path),
        Path(job.sql_path),
        Path(job.config_path),
        Path(job.metadata_path),
        Path(job.critical_directory),
    )


def _physical_size(job: models.BackupJob) -> int:
    pdf_path, archive_path, json_path, sql_path, config_path, metadata_path, critical_directory = _artifact_paths(job)
    return backups._calculate_total_size(
        [pdf_path, archive_path, json_path, sql_path, config_path, metadata_path, critical_directory]
    )


def _rewrite_metadata(job: models.BackupJob, total_size: int) -> None:
    metadata_path = Path(job.metadata_path)
    metadata = backups.load_backup_metadata(metadata_path)
    metadata["total_size_bytes"] = int(total_size)
    serialized = json.dumps(
        metadata,
        ensure_ascii=False,
        indent=2,
        default=backups._json_default,
    ).encode("utf-8")
    cipher = backups._resolve_cipher_for_path(metadata_path)
    if cipher is not None:
        serialized = encryption.encrypt_bytes(serialized, cipher)
    metadata_path.write_bytes(serialized)


def _rebuild_archive(job: models.BackupJob) -> None:
    pdf_path, archive_path, json_path, sql_path, config_path, metadata_path, critical_directory = _artifact_paths(job)
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as zip_file:
        zip_file.write(pdf_path, arcname=f"reportes/{pdf_path.name}")
        zip_file.write(json_path, arcname=f"datos/{json_path.name}")
        zip_file.write(sql_path, arcname=f"datos/{sql_path.name}")
        zip_file.write(config_path, arcname=f"config/{config_path.name}")
        # Los metadatos pueden estar cifrados. Guardarlos sin DEFLATE evita que
        # el IV aleatorio de Fernet cambie el tamaño comprimido entre iteraciones.
        zip_file.write(
            metadata_path,
            arcname=f"metadata/{metadata_path.name}",
            compress_type=ZIP_STORED,
        )
        for file_path in critical_directory.rglob("*"):
            if file_path.is_file():
                arcname = Path("criticos") / file_path.relative_to(critical_directory)
                zip_file.write(file_path, arcname=str(arcname))


def reconcile_backup_job(db: Session, job: models.BackupJob) -> models.BackupJob:
    candidate = _physical_size(job)
    measured = candidate
    for _ in range(8):
        _rewrite_metadata(job, candidate)
        _rebuild_archive(job)
        measured = _physical_size(job)
        if measured == candidate:
            break
        candidate = measured

    # Con ZIP_STORED para el metadato, el tamaño depende de la longitud del JSON
    # y converge una vez que el número conserva la misma cantidad de dígitos.
    if measured != candidate:
        _rewrite_metadata(job, measured)
        _rebuild_archive(job)
        measured = _physical_size(job)

    job.total_size_bytes = measured
    db.add(job)
    db.flush()
    db.refresh(job)
    return job


def generate_backup(db: Session, **kwargs) -> models.BackupJob:
    job = backups.generate_backup(db, **kwargs)
    return reconcile_backup_job(db, job)


__all__ = ["generate_backup", "reconcile_backup_job"]
