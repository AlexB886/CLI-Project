"""Recogida de datos de diagnóstico, sin red ni acceso a secretos."""

from pathlib import Path

from tareas import __version__
from tareas.configuracion import CargadorAccionesJSON
from tareas.errores import ConfigError
from tareas.modelos import TablaContenido
from tareas.puertos import CargadorAcciones


def recolectar(
    ruta: Path,
    *,
    clave_configurada: bool,
    ruta_ca: str | None,
    cargador: CargadorAcciones | None = None,
) -> TablaContenido:
    """Devuelve el estado de la instalación como tabla para la consola."""
    selector = cargador or CargadorAccionesJSON()
    try:
        acciones = selector.cargar(ruta)
    except ConfigError as exc:
        estado = f"Error: {exc}"
        nombres: tuple[str, ...] = ()
        con_ia: tuple[str, ...] = ()
    else:
        estado = "Correcta"
        nombres = tuple(accion.nombre for accion in acciones)
        con_ia = tuple(accion.nombre for accion in acciones if accion.ia)

    if not ruta_ca:
        certificado = "No configurada"
    elif Path(ruta_ca).expanduser().is_file():
        certificado = "Fichero presente"
    else:
        certificado = "Fichero no encontrado"

    filas = (
        ("Versión", __version__),
        ("Fichero de acciones", str(ruta)),
        ("Configuración", estado),
        ("Acciones declaradas", str(len(nombres))),
        ("Acciones con IA", ", ".join(con_ia) or "ninguna"),
        ("Clave de IA (entorno)", "configurada" if clave_configurada else "no configurada"),
        ("Certificado CA (entorno)", certificado),
        ("Conexión", "No se comprueba; las acciones sin IA funcionan offline"),
    )
    return TablaContenido(
        titulo="Diagnóstico de TAREAS",
        columnas=("Elemento", "Estado"),
        filas=filas,
    )
