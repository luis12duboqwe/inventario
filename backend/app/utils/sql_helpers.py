"""Utilidades para construcción de queries SQL."""
from typing import Any
from sqlalchemy.sql import ColumnElement


def token_filter(column: Any, candidate: str) -> ColumnElement[bool]:
    """
    Crea filtro SQL para búsqueda por tokens.
    
    Divide el término de búsqueda en tokens y busca coincidencias parciales
    insensibles a mayúsculas en la columna especificada.
    
    Args:
        column: Columna SQLAlchemy sobre la que filtrar
        candidate: Término de búsqueda a dividir en tokens
        
    Returns:
        Condición SQL para filtrado por tokens
        
    Example:
        >>> filter = token_filter(User.name, "John Doe")
        # Genera: column ILIKE '%john%' AND column ILIKE '%doe%'
    """
    from sqlalchemy import and_
    
    tokens = candidate.lower().strip().split()
    if not tokens:
        # Si no hay tokens, devolver condición que siempre es True
        return column.ilike("%")
    
    conditions = [column.ilike(f"%{token}%") for token in tokens]
    return and_(*conditions)
