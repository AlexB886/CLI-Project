"""Proveedor de IA por defecto: no hay IA configurada."""

from tareas.errores import ConfigError


class ProveedorNulo:
    """Proveedor que no está disponible y no propone nada."""

    nombre = "nulo"

    def disponible(self) -> bool:
        """Siempre está desactivado."""
        return False

    def proponer_acciones(self, peticion: str, contexto: str) -> list[dict]:
        """Falla de forma explícita si alguien intenta usar IA."""
        raise ConfigError("No hay ningún proveedor de IA configurado.")
