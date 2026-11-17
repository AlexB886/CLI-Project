"""Fábricas de proveedores de IA a partir de la configuración local."""

from tareas.ia.centro import ProveedorCentro
from tareas.ia.configuracion import obtener_clave
from tareas.ia.nulo import ProveedorNulo


def crear_proveedor() -> ProveedorCentro | ProveedorNulo:
    """Crea el proveedor del centro si hay clave configurada."""
    clave = obtener_clave()
    if not clave:
        return ProveedorNulo()
    return ProveedorCentro(clave)
