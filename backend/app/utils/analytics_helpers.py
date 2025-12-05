"""Utilidades para análisis estadístico y proyecciones."""
from __future__ import annotations

import math
from collections.abc import Sequence


def linear_regression(
    points: Sequence[tuple[float, float]]
) -> tuple[float, float, float]:
    """Calcula regresión lineal simple para un conjunto de puntos.
    
    Args:
        points: Secuencia de tuplas (x, y)
        
    Returns:
        Tupla (slope, intercept, r_squared)
        
    Notas:
        - Si no hay puntos, retorna (0.0, 0.0, 0.0)
        - Si hay un solo punto, retorna (0.0, y, 0.0)
        - r_squared indica qué tan bien se ajusta el modelo (0-1)
    """
    if not points:
        return 0.0, 0.0, 0.0
    if len(points) == 1:
        return 0.0, points[0][1], 0.0

    n = float(len(points))
    sum_x = sum(point[0] for point in points)
    sum_y = sum(point[1] for point in points)
    sum_xy = sum(point[0] * point[1] for point in points)
    sum_xx = sum(point[0] ** 2 for point in points)
    sum_yy = sum(point[1] ** 2 for point in points)

    denominator = (n * sum_xx) - (sum_x**2)
    if math.isclose(denominator, 0.0):
        slope = 0.0
        intercept = sum_y / n if n else 0.0
    else:
        slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
        intercept = (sum_y - (slope * sum_x)) / n

    denominator_r = ((n * sum_xx) - (sum_x**2)) * ((n * sum_yy) - (sum_y**2))
    if denominator_r <= 0 or math.isclose(denominator_r, 0.0):
        r_squared = 0.0
    else:
        numerator = ((n * sum_xy) - (sum_x * sum_y)) ** 2
        r_squared = numerator / denominator_r

    return slope, intercept, r_squared


def project_linear_sum(
    slope: float,
    intercept: float,
    start_index: int,
    horizon: int,
) -> float:
    """Proyecta la suma de valores futuros usando una tendencia lineal.
    
    Args:
        slope: Pendiente de la línea de regresión
        intercept: Intercepción de la línea de regresión
        start_index: Índice inicial para proyección
        horizon: Número de períodos a proyectar
        
    Returns:
        Suma total de valores proyectados (negativos se convierten a 0)
        
    Ejemplo:
        Si slope=2, intercept=5, start_index=10, horizon=3:
        - x=10: y = 2*10 + 5 = 25
        - x=11: y = 2*11 + 5 = 27
        - x=12: y = 2*12 + 5 = 29
        - Total = 25 + 27 + 29 = 81
    """
    total = 0.0
    for offset in range(horizon):
        x_value = float(start_index + offset)
        estimate = slope * x_value + intercept
        total += max(0.0, estimate)
    return total


def user_display_name(user: any) -> str | None:
    """Obtiene el nombre de display de un usuario.
    
    Args:
        user: Objeto usuario con atributos full_name y username
        
    Returns:
        Nombre completo si existe, username si no, None si ninguno
    """
    if user is None:
        return None
    if hasattr(user, 'full_name') and user.full_name and user.full_name.strip():
        return user.full_name.strip()
    if hasattr(user, 'username') and user.username and user.username.strip():
        return user.username.strip()
    return None
