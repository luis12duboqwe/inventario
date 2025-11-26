"""Rutas dedicadas a seguridad avanzada y 2FA."""
from __future__ import annotations

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import ADMIN, GERENTE
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_reauthentication, require_roles, verify_totp

router = APIRouter(prefix="/security", tags=["seguridad"])


def _ensure_2fa_enabled() -> None:
    if not settings.enable_2fa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


@router.get("/2fa/status", response_model=schemas.TOTPStatusResponse, dependencies=[Depends(require_roles(ADMIN, GERENTE))])
def totp_status(current_user=Depends(require_roles(ADMIN, GERENTE)), db: Session = Depends(get_db)):
    _ensure_2fa_enabled()
    record = crud.get_totp_secret(db, current_user.id)
    if record is None:
        return schemas.TOTPStatusResponse(is_active=False, activated_at=None, last_verified_at=None)
    return schemas.TOTPStatusResponse(
        is_active=record.is_active,
        activated_at=record.activated_at,
        last_verified_at=record.last_verified_at,
    )


@router.post(
    "/2fa/setup",
    response_model=schemas.TOTPSetupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(ADMIN, GERENTE)), Depends(require_reauthentication)],
)
def totp_setup(
    current_user=Depends(require_roles(ADMIN, GERENTE)),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
):
    _ensure_2fa_enabled()
    secret = pyotp.random_base32()
    record = crud.provision_totp_secret(
        db,
        current_user.id,
        secret,
        performed_by_id=current_user.id,
        reason=reason,
    )
    totp = pyotp.TOTP(record.secret)
    otpauth = totp.provisioning_uri(name=current_user.username, issuer_name="Softmobile 2025")
    return schemas.TOTPSetupResponse(secret=record.secret, otpauth_url=otpauth)


@router.post(
    "/2fa/activate",
    response_model=schemas.TOTPStatusResponse,
    dependencies=[Depends(require_roles(ADMIN, GERENTE)), Depends(require_reauthentication)],
)
def totp_activate(
    payload: schemas.TOTPActivateRequest,
    current_user=Depends(require_roles(ADMIN, GERENTE)),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
):
    _ensure_2fa_enabled()
    record = crud.get_totp_secret(db, current_user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secreto TOTP no provisionado")
    if not verify_totp(record.secret, payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código TOTP inválido")
    updated = crud.activate_totp_secret(
        db,
        current_user.id,
        performed_by_id=current_user.id,
        reason=reason,
    )
    return schemas.TOTPStatusResponse(
        is_active=updated.is_active,
        activated_at=updated.activated_at,
        last_verified_at=updated.last_verified_at,
    )


@router.post(
    "/2fa/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(require_roles(ADMIN, GERENTE)), Depends(require_reauthentication)],
)
def totp_disable(
    current_user=Depends(require_roles(ADMIN, GERENTE)),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
):
    _ensure_2fa_enabled()
    crud.deactivate_totp_secret(
        db,
        current_user.id,
        performed_by_id=current_user.id,
        reason=reason,
    )
    return None


@router.get("/sessions", response_model=list[schemas.ActiveSessionResponse], dependencies=[Depends(require_roles(ADMIN, GERENTE))])
def list_sessions(
    user_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN, GERENTE)),
):
    target_user = user_id or current_user.id
    sessions = crud.list_active_sessions(
        db, user_id=target_user, limit=limit, offset=offset
    )
    return sessions


@router.post(
    "/sessions/{session_id}/revoke",
    response_model=schemas.ActiveSessionResponse,
    dependencies=[Depends(require_roles(ADMIN, GERENTE))],
)
def revoke_session_endpoint(
    payload: schemas.SessionRevokeRequest,
    session_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN, GERENTE)),
    reason: str = Depends(require_reason),
):
    session = crud.revoke_session(db, session_id, revoked_by_id=current_user.id, reason=reason or payload.reason)
    return session


__all__ = ["router"]
