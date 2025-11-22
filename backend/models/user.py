"""Modelo de usuario unificado.

Este módulo preserva la ruta histórica ``backend.models.user`` pero expone el
modelo principal ``backend.app.models.User`` que mapea la tabla ``usuarios`` y
sus roles asociados.
"""
from backend.app.models import User

__all__ = ["User"]
