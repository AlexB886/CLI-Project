"""Proveedores de IA."""

from tareas.ia.centro import ProveedorCentro
from tareas.ia.configuracion import obtener_clave
from tareas.ia.nulo import ProveedorNulo


def crear_proveedor() -> ProveedorCentro | ProveedorNulo:
    """Elige el proveedor del centro solo con clave y conexión disponibles."""
    clave = obtener_clave()
    if not clave:
        return ProveedorNulo()
    proveedor = ProveedorCentro(clave)
    return proveedor if proveedor.disponible() else ProveedorNulo()


__all__ = ["ProveedorCentro", "ProveedorNulo", "crear_proveedor"]
