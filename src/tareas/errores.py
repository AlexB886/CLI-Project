"""Excepciones propias de tareas."""


class TareasError(Exception):
    """Error base de la aplicación."""


class ConfigError(TareasError):
    """La configuración de acciones no es válida."""


class AccionNoValida(TareasError):
    """La acción solicitada no existe o no se puede invocar."""
