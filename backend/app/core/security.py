"""Funciones de seguridad y autenticación centralizadas."""
from __future__ import annotations

from passlib.context import CryptContext

# Contexto de hashing para PINs de supervisores
_PIN_CONTEXT = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt_sha256", "bcrypt"], deprecated="auto"
)


def verify_supervisor_pin_hash(hashed: str, candidate: str) -> bool:
    """Verifica un PIN de supervisor contra su hash.
    
    Args:
        hashed: Hash del PIN almacenado
        candidate: PIN candidato a verificar
        
    Returns:
        True si el PIN es válido, False en caso contrario
    """
    try:
        return _PIN_CONTEXT.verify(candidate, hashed)
    except ValueError:
        return False


def hash_supervisor_pin(pin: str) -> str:
    """Genera un hash seguro para un PIN de supervisor.
    
    Args:
        pin: PIN en texto plano
        
    Returns:
        Hash del PIN
    """
    return _PIN_CONTEXT.hash(pin)
