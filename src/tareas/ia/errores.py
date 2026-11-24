"""Errores controlados de los proveedores de IA."""


class ErrorProveedorIA(Exception):
    """Fallo de comunicación o de respuesta del proveedor de IA."""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        # Etapa de la cadena de repaso (p. ej. «fragmento 12 de 57») o "".
        self.etapa: str = ""


class AutenticacionProveedorIA(ErrorProveedorIA):
    """La clave no es válida o no tiene acceso al servicio del centro."""


class IAnoDisponible(ErrorProveedorIA):
    """No hay conexión válida con el proveedor."""


class TimeoutProveedorIA(ErrorProveedorIA):
    """El proveedor no respondió dentro del tiempo permitido."""


class RespuestaIAInvalida(ErrorProveedorIA):
    """La respuesta del proveedor no cumple el formato esperado."""
