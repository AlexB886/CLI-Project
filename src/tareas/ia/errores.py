"""Errores controlados de los proveedores de IA."""


class ErrorProveedorIA(Exception):
    """Fallo de comunicación o de respuesta del proveedor de IA."""


class IAnoDisponible(ErrorProveedorIA):
    """No hay conexión válida con el proveedor."""


class TimeoutProveedorIA(ErrorProveedorIA):
    """El proveedor no respondió dentro del tiempo permitido."""


class RespuestaIAInvalida(ErrorProveedorIA):
    """La respuesta del proveedor no cumple el formato esperado."""
