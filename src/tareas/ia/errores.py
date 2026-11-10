"""Errores controlados de los proveedores de IA."""


class ErrorProveedorIA(Exception):
    """Fallo de comunicación o de respuesta del proveedor de IA."""


class IAnoDisponible(ErrorProveedorIA):
    """No hay conexión válida con el proveedor."""
