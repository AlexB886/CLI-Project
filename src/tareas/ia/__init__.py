"""Proveedores de IA."""

from tareas.ia.centro import ProveedorCentro
from tareas.ia.fabrica import crear_proveedor
from tareas.ia.nulo import ProveedorNulo

__all__ = ["ProveedorCentro", "ProveedorNulo", "crear_proveedor"]
