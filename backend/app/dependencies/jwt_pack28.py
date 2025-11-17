"""Dependencias específicas para la autenticación de PACK28."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .. import schemas
from ..core.roles import VALID_ROLES
from ..database import get_db
from .. import crud
from ..security import decode_token

# // [PACK28-deps]
_bearer_scheme = HTTPBearer(auto_error=False)


# // [PACK28-deps]
def verify_access_token(token: str, db=Depends(get_db)) -> schemas.TokenPayload:
    payload = decode_token(token)
    if crud.is_jwt_blacklisted(db, payload.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revocado.",
        )
    if payload.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token recibido no es de acceso.",
        )
    if payload.role and payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El rol asociado al token no es válido.",
        )
    if payload.exp <= int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de acceso ha expirado.",
        )
    return payload


# // [PACK28-deps]
async def require_verified_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> schemas.TokenPayload:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida.",
        )
    return verify_access_token(credentials.credentials)
