"""Utilidades de cifrado simétrico para artefactos sensibles."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from cryptography.fernet import Fernet, InvalidToken


def _read_or_create_key(key_path: Path) -> bytes:
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    os.chmod(key_path, 0o600)
    return key


def build_fernet(key_path: str | Path) -> Fernet:
    """Obtiene una instancia Fernet usando la llave almacenada en disco."""

    path = Path(key_path).expanduser().resolve()
    key = _read_or_create_key(path)
    return Fernet(key)


def encrypt_bytes(payload: bytes, cipher: Fernet) -> bytes:
    """Cifra datos arbitrarios usando Fernet."""

    return cipher.encrypt(payload)


def decrypt_bytes(payload: bytes, cipher: Fernet) -> bytes:
    """Descifra datos, propagando errores si la firma no es válida."""

    return cipher.decrypt(payload)


def decrypt_bytes_best_effort(payload: bytes, cipher: Fernet | None) -> bytes:
    """Devuelve el contenido descifrado cuando es posible.

    Permite procesar respaldos históricos no cifrados devolviendo el payload
    original si no es posible descifrarlo.
    """

    if cipher is None:
        return payload
    try:
        return decrypt_bytes(payload, cipher)
    except InvalidToken:
        return payload


def _transform_file(path: Path, transform: Callable[[bytes], bytes]) -> None:
    original = path.read_bytes()
    transformed = transform(original)
    path.write_bytes(transformed)


def encrypt_file_in_place(path: Path, cipher: Fernet) -> None:
    """Cifra el archivo indicado reemplazando su contenido."""

    _transform_file(path, lambda data: encrypt_bytes(data, cipher))


def decrypt_file_contents(path: Path, cipher: Fernet | None) -> bytes:
    """Obtiene el contenido descifrado de un archivo si aplica."""

    return decrypt_bytes_best_effort(path.read_bytes(), cipher)

