"""Utilidades para resolver la librería ``fastapi-limiter`` real cuando está instalada."""
from __future__ import annotations

import importlib.abc
import importlib.metadata
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Optional


def load_real_module(module_name: str) -> Optional[ModuleType]:
    """Carga un módulo real de ``fastapi-limiter`` si la dependencia está instalada."""

    try:
        distribution = importlib.metadata.distribution("fastapi-limiter")
    except importlib.metadata.PackageNotFoundError:
        return None

    package_root = Path(distribution.locate_file("fastapi_limiter"))
    if not package_root.exists():
        return None

    if module_name == "fastapi_limiter":
        module_path = package_root / "__init__.py"
        search_locations = [str(package_root)]
    else:
        suffix = module_name.split(".", 1)[1]
        module_path = package_root / f"{suffix.replace('.', '/')}.py"
        search_locations = None

    if not module_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        f"_fastapi_limiter_real_{module_name.replace('.', '_')}",
        module_path,
        submodule_search_locations=search_locations,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if isinstance(loader, importlib.abc.Loader):
        loader.exec_module(module)
    else:  # pragma: no cover - compatibilidad con tipos sin ABC
        loader.exec_module(module)  # type: ignore[attr-defined]
    return module

