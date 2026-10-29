"""Interfaz de proveedores de IA.

Un proveedor solo propone acciones en JSON. La validación y la ejecución
siempre pasan por el cargador y el motor.
"""

from typing import Protocol


class ProveedorIA(Protocol):
    """Contrato mínimo de un proveedor de IA."""

    @property
    def nombre(self) -> str:
        """Identificador del proveedor."""
        ...

    def disponible(self) -> bool:
        """Indica si el proveedor está configurado."""
        ...

    def proponer_acciones(self, peticion: str, contexto: str) -> list[dict]:
        """Devuelve propuestas sin validar ni ejecutar."""
        ...
