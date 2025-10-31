from __future__ import annotations
from fastapi import Depends, HTTPException, status

try:
    # security module that exposes get_current_user(UserOut) -> user with 'role' attr
    from .security import get_current_user
except Exception:  # fallback offline dev
    def get_current_user():
        class _U: role = "INVITADO"; id = "anonymous"
        return _U()

ALLOWED = {"ADMIN", "GERENTE", "OPERADOR", "INVITADO"}


def require_roles(*roles: str):
    allowed = set(roles) if roles else ALLOWED

    def _dep(user = Depends(get_current_user)):
        role = getattr(user, "role", "INVITADO")
        if role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
        return user

    return _dep
