from __future__ import annotations
from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse

from ..acl import require_roles

router = APIRouter(prefix="/auditfile", tags=["auditoría-file"], dependencies=[Depends(require_roles('ADMIN'))])

LOG_PATH = Path('logs/audit.jsonl')


def _tail_lines(path: Path, lines: int) -> str:
    if not path.exists():
        return ""
    # Simple tail: read last ~1MB and split
    chunk_size = 1_000_000
    with path.open('rb') as f:
        f.seek(0, 2)
        size = f.tell()
        offset = max(0, size - chunk_size)
        f.seek(offset)
        data = f.read().decode('utf-8', errors='ignore')
    rows = data.splitlines()[-lines:]
    return "\n".join(rows) + ("\n" if rows else "")


@router.get('/tail', response_class=PlainTextResponse)
def tail(lines: int = Query(default=200, ge=1, le=5000)) -> str:
    return _tail_lines(LOG_PATH, lines)


@router.get('/download')
def download() -> StreamingResponse:
    if not LOG_PATH.exists():
        raise HTTPException(status_code=404, detail='No hay logs')

    def iterfile() -> Iterator[bytes]:
        with LOG_PATH.open('rb') as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(iterfile(), media_type='text/plain', headers={'Content-Disposition': 'attachment; filename=audit.jsonl'})
