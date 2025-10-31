from __future__ import annotations
import json, time, logging
from typing import Any, Optional
_logger = logging.getLogger('softmobile.audit')

def audit_event(user_id: Optional[str], action: str, resource: str, reason: Optional[str], extra: dict[str, Any] | None = None):
    data = {
        'ts': int(time.time() * 1000),
        'user_id': user_id or 'anonymous',
        'action': action,
        'resource': resource,
        'reason': reason,
        'extra': extra or {},
    }
    try:
        _logger.info(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass
