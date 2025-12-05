"""Utilidades para gestión de usuarios."""
from typing import Iterable
from ..core.roles import ADMIN, GERENTE, OPERADOR, INVITADO


def select_primary_role(role_names: Iterable[str]) -> str:
    """
    Selecciona el rol primario de un usuario basado en prioridad.
    
    Los roles se priorizan en el siguiente orden:
    1. ADMIN (más privilegios)
    2. GERENTE
    3. OPERADOR
    4. INVITADO (menos privilegios)
    
    Args:
        role_names: Conjunto de nombres de roles asignados al usuario
        
    Returns:
        Nombre del rol con mayor prioridad
        
    Example:
        >>> select_primary_role(['OPERADOR', 'GERENTE'])
        'GERENTE'
    """
    role_set = set(role_names)
    
    # Prioridad de roles de mayor a menor
    priority_order = [ADMIN, GERENTE, OPERADOR, INVITADO]
    
    for role in priority_order:
        if role in role_set:
            return role
    
    # Si no hay roles conocidos, retornar el primero disponible
    # o OPERADOR como fallback
    return next(iter(role_set)) if role_set else OPERADOR


def build_role_assignments(
    role_names: Iterable[str],
) -> dict[str, bool]:
    """
    Construye diccionario de asignaciones de roles.
    
    Args:
        role_names: Nombres de roles asignados
        
    Returns:
        Diccionario con flags booleanos para cada rol conocido
        
    Example:
        >>> build_role_assignments(['ADMIN', 'GERENTE'])
        {'is_admin': True, 'is_gerente': True, 'is_operador': False, 'is_invitado': False}
    """
    role_set = set(role_names)
    
    return {
        "is_admin": ADMIN in role_set,
        "is_gerente": GERENTE in role_set,
        "is_operador": OPERADOR in role_set,
        "is_invitado": INVITADO in role_set,
    }
