from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .. import crud
from ..config import settings
from ..database import SessionLocal
from . import cash_reports


def _registry_path() -> Path:
    base_directory = Path(getattr(settings, "logs_directory", None) or "logs")
    if base_directory.exists() and base_directory.is_file():
        base_directory = base_directory.parent / f"{base_directory.name}_dir"
    base_directory.mkdir(parents=True, exist_ok=True)
    return base_directory / "pos_async_jobs.json"


_JOBS_REGISTRY_PATH = _registry_path()


@dataclass
class AsyncJob:
    """Representa un trabajo asincrónico de generación de reportes."""

    id: str
    session_id: int
    job_type: str
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    output_path: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    def mark_running(self) -> None:
        self.status = "running"
        _persist_jobs()

    def mark_completed(self, path: Path) -> None:
        self.status = "completed"
        self.output_path = str(path)
        self.finished_at = datetime.now(timezone.utc)
        _persist_jobs()

    def mark_failed(self, message: str) -> None:
        self.status = "failed"
        self.error = message
        self.finished_at = datetime.now(timezone.utc)
        _persist_jobs()


def _load_jobs() -> dict[str, AsyncJob]:
    if not _JOBS_REGISTRY_PATH.exists():
        return {}
    try:
        payload = json.loads(_JOBS_REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    jobs: dict[str, AsyncJob] = {}
    for job_data in payload.values():
        try:
            jobs[job_data["id"]] = AsyncJob(
                id=job_data["id"],
                session_id=int(job_data["session_id"]),
                job_type=job_data.get("job_type", "cash_report"),
                status=job_data.get("status", "queued"),
                output_path=job_data.get("output_path"),
                error=job_data.get("error"),
                created_at=datetime.fromisoformat(job_data["created_at"]),
                finished_at=(
                    datetime.fromisoformat(job_data["finished_at"])
                    if job_data.get("finished_at")
                    else None
                ),
            )
        except Exception:
            continue
    return jobs


def _persist_jobs() -> None:
    serializable = {job_id: asdict(job) for job_id, job in _JOBS.items()}
    for job in serializable.values():
        created_at = job.get("created_at")
        finished_at = job.get("finished_at")
        if isinstance(created_at, datetime):
            job["created_at"] = created_at.isoformat()
        if isinstance(finished_at, datetime):
            job["finished_at"] = finished_at.isoformat()
    _JOBS_REGISTRY_PATH.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


_JOBS: dict[str, AsyncJob] = _load_jobs()


def enqueue_cash_report(session_id: int) -> AsyncJob:
    job = AsyncJob(id=str(uuid4()), session_id=session_id, job_type="cash_report")
    _JOBS[job.id] = job
    _persist_jobs()
    return job


def run_cash_report_job(job_id: str) -> AsyncJob:
    job = _JOBS.get(job_id)
    if job is None:
        raise LookupError("job_not_found")

    job.mark_running()
    output_directory = Path(settings.logs_directory or "logs") / "cash_reports"
    output_directory.mkdir(parents=True, exist_ok=True)

    try:
        with SessionLocal() as session:
            cash_session = crud.get_cash_session(session, job.session_id)
            entries = crud.list_cash_entries(session, session_id=cash_session.id)
            pdf_bytes = cash_reports.render_cash_close_pdf(cash_session, entries)

        output_path = output_directory / f"cierre_{job.session_id}_{job.id}.pdf"
        output_path.write_bytes(pdf_bytes)
        job.mark_completed(output_path)
    except Exception as exc:  # pragma: no cover - ruta de error
        job.mark_failed(str(exc))
    return job


def get_job(job_id: str) -> AsyncJob:
    job = _JOBS.get(job_id)
    if job is None:
        raise LookupError("job_not_found")
    return job


def job_to_payload(job: AsyncJob) -> dict[str, object]:
    return {
        "id": job.id,
        "session_id": job.session_id,
        "job_type": job.job_type,
        "status": job.status,
        "output_path": job.output_path,
        "error": job.error,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
    }


__all__ = [
    "AsyncJob",
    "enqueue_cash_report",
    "run_cash_report_job",
    "get_job",
    "job_to_payload",
]
