"""Registrador ligero de eventos de auditoría."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

_logger = logging.getLogger("softmobile.audit")


def audit_event(
    user_id: Optional[str],
    action: str,
    resource: str,
    reason: Optional[str],
    extra: Dict[str, Any] | None = None,
) -> None:
    """Persistir un evento de auditoría en JSONL."""

    payload = {
        "ts": int(time.time() * 1000),
        "user_id": user_id or "anonymous",
        "action": action,
        "resource": resource,
        "reason": reason or "",
        "extra": extra or {},
    }
    _logger.info(json.dumps(payload, ensure_ascii=False))
