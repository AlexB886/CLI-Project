"""Acciones internas que pueden declararse en acciones.json."""

import re
from datetime import date, datetime
from pathlib import Path

from tareas.acciones.registro import registrar
from tareas.errores import ConfigError
from tareas.ia.errores import (
    AutenticacionProveedorIA,
    ErrorProveedorIA,
    IAnoDisponible,
    TimeoutProveedorIA,
)
from tareas.modelos import ContextoAccion, ResultadoAccion, TablaContenido

MENSAJE_OFFLINE_IA = "IA no disponible (modo offline): sigo con las acciones sin IA"


class RutaFueraDeBaseError(Exception):
    """La ruta solicitada sale de la raíz autorizada para borrar."""


def _como_ruta(valor: object) -> Path:
    if isinstance(valor, Path):
        return valor
    return Path(str(valor)).expanduser()


def tamano_legible(n: int) -> str:
    """Convierte bytes en texto: 532 B, 1.2 KB, 3.4 MB..."""
    if n < 1024:
        return f"{n} B"
    tamano = float(n)
    unidad = "B"
    for unidad in ("KB", "MB", "GB", "TB"):
        tamano /= 1024
        if tamano < 1024:
            break
    return f"{tamano:.1f} {unidad}"


@registrar("listar")
def listar(ctx: ContextoAccion) -> ResultadoAccion:
    """Lista el contenido de una carpeta en una tabla."""
    carpeta = _como_ruta(ctx.parametros.get("carpeta") or ".")
    if not carpeta.is_dir():
        return ResultadoAccion(
            codigo=1,
            error=f"«{carpeta}» no existe o no es una carpeta.",
        )

    try:
        elementos = sorted(
            carpeta.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )
    except OSError as exc:
        return ResultadoAccion(codigo=1, error=f"No se pudo leer «{carpeta}»: {exc}")

    if not elementos:
        return ResultadoAccion(
            codigo=0,
            salida=f"La carpeta «{carpeta}» está vacía.",
        )

    try:
        titulo = f"Contenido de {carpeta.resolve()}"
    except OSError:
        titulo = f"Contenido de {carpeta}"

    filas: list[tuple[str, ...]] = []
    for ruta in elementos:
        try:
            datos = ruta.stat()
        except OSError:
            continue
        es_carpeta = ruta.is_dir()
        tipo = "carpeta" if es_carpeta else (ruta.suffix.lower() or "(sin extensión)")
        tamano = "—" if es_carpeta else tamano_legible(datos.st_size)
        fecha = datetime.fromtimestamp(datos.st_mtime).strftime("%Y-%m-%d %H:%M")
        filas.append((ruta.name, tipo, tamano, fecha))

    return ResultadoAccion(
        codigo=0,
        datos=TablaContenido(
            titulo=titulo,
            columnas=("Nombre", "Tipo", "Tamaño", "Modificado"),
            filas=tuple(filas),
            alinear_derecha=(2,),
        ),
    )


@registrar("validar")
def validar(ctx: ContextoAccion) -> ResultadoAccion:
    """Comprueba que una ruta existe, es un fichero y no está vacío."""
    ruta = _como_ruta(ctx.parametros.get("ruta") or "")
    if not str(ruta):
        return ResultadoAccion(codigo=1, error="No se ha indicado ninguna ruta.")

    if not ruta.exists():
        return ResultadoAccion(codigo=1, error=f"La ruta «{ruta}» no existe.")
    if ruta.is_dir():
        return ResultadoAccion(
            codigo=1,
            error=f"«{ruta}» es una carpeta, no un fichero.",
        )
    if not ruta.is_file():
        return ResultadoAccion(
            codigo=1,
            error=f"«{ruta}» no es un fichero regular.",
        )

    try:
        tamano = ruta.stat().st_size
    except OSError as exc:
        return ResultadoAccion(codigo=1, error=f"No se pudo leer «{ruta}»: {exc}")

    if tamano == 0:
        return ResultadoAccion(codigo=1, error=f"El fichero «{ruta}» está vacío.")

    try:
        resuelta = ruta.resolve()
    except OSError:
        resuelta = ruta
    return ResultadoAccion(codigo=0, salida=f"OK {resuelta}")


@registrar("borrar")
def borrar(ctx: ContextoAccion) -> ResultadoAccion:
    """Borra un fichero. Exige simulación o confirmación previa."""
    valor_ruta = ctx.parametros.get("ruta")
    if not valor_ruta:
        return ResultadoAccion(codigo=1, error="No se ha indicado ninguna ruta.")

    ruta = _como_ruta(valor_ruta)
    base = _como_ruta(ctx.parametros.get("base") or Path.cwd()).resolve()
    if ruta.is_absolute():
        raise RutaFueraDeBaseError("No se permiten rutas absolutas para borrar.")
    try:
        ruta = (base / ruta).resolve()
        ruta.relative_to(base)
    except (ValueError, OSError) as exc:
        raise RutaFueraDeBaseError(
            f"La ruta «{valor_ruta}» queda fuera de la raíz autorizada «{base}»."
        ) from exc

    if not ruta.exists():
        return ResultadoAccion(codigo=1, error=f"La ruta «{ruta}» no existe.")
    if ruta.is_dir():
        return ResultadoAccion(
            codigo=1,
            error=f"«{ruta}» es una carpeta. Esta acción solo borra ficheros.",
        )

    try:
        tamano = ruta.stat().st_size
    except OSError as exc:
        return ResultadoAccion(codigo=1, error=f"No se pudo leer «{ruta}»: {exc}")

    if ctx.simular:
        return ResultadoAccion(
            codigo=0,
            salida=f"[simular] Se borraría «{ruta}» ({tamano_legible(tamano)}).",
        )

    try:
        ruta.unlink()
    except OSError as exc:
        return ResultadoAccion(codigo=1, error=f"No se pudo borrar «{ruta}»: {exc}")
    return ResultadoAccion(codigo=0, salida=f"Borrado «{ruta}».")


@registrar("ver")
def ver(ctx: ContextoAccion) -> ResultadoAccion:
    """Muestra el contenido de un fichero por consola."""
    ruta = _como_ruta(ctx.parametros.get("ruta") or "")
    if not str(ruta):
        return ResultadoAccion(codigo=1, error="No se ha indicado ninguna ruta.")

    if not ruta.is_file():
        return ResultadoAccion(codigo=1, error=f"«{ruta}» no es un fichero legible.")

    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return ResultadoAccion(
            codigo=1,
            error=f"«{ruta}» no es un fichero de texto (UTF-8).",
        )
    except OSError as exc:
        return ResultadoAccion(codigo=1, error=f"No se pudo leer «{ruta}»: {exc}")

    max_lineas = 200
    aviso = ""
    if len(lineas) > max_lineas:
        aviso = f"\n… ({len(lineas) - max_lineas} líneas omitidas)."
        lineas = lineas[:max_lineas]

    return ResultadoAccion(codigo=0, salida="\n".join(lineas) + aviso)


@registrar("tamano")
def tamano(ctx: ContextoAccion) -> ResultadoAccion:
    """Calcula el tamaño total de una carpeta recursivamente."""
    carpeta = _como_ruta(ctx.parametros.get("carpeta") or ".")
    if not carpeta.is_dir():
        return ResultadoAccion(
            codigo=1,
            error=f"«{carpeta}» no existe o no es una carpeta.",
        )

    total = 0
    ficheros = 0
    carpetas = 0
    for ruta in carpeta.rglob("*"):
        try:
            if ruta.is_dir():
                carpetas += 1
            elif ruta.is_file():
                total += ruta.stat().st_size
                ficheros += 1
        except OSError:
            continue

    try:
        titulo = f"Tamaño de {carpeta.resolve()}"
    except OSError:
        titulo = f"Tamaño de {carpeta}"

    return ResultadoAccion(
        codigo=0,
        datos=TablaContenido(
            titulo=titulo,
            columnas=("Elemento", "Valor"),
            filas=(
                ("Ficheros", str(ficheros)),
                ("Carpetas", str(carpetas)),
                ("Tamaño total", tamano_legible(total)),
            ),
            alinear_derecha=(1,),
        ),
    )


@registrar("resumir-ia")
def resumir_ia(ctx: ContextoAccion) -> ResultadoAccion:
    """Resume un fichero de texto con IA o informa del modo offline."""
    ruta = _como_ruta(ctx.parametros.get("ruta") or "")
    if not str(ruta) or not ruta.is_file():
        return ResultadoAccion(codigo=1, error=f"«{ruta}» no es un fichero legible.")

    try:
        texto = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ResultadoAccion(codigo=1, error=f"«{ruta}» no es un fichero de texto (UTF-8).")
    except OSError as exc:
        return ResultadoAccion(codigo=1, error=f"No se pudo leer «{ruta}»: {exc}")

    proveedor = ctx.proveedor_ia
    if proveedor is None:
        return ResultadoAccion(codigo=0, salida=MENSAJE_OFFLINE_IA)

    try:
        resumen = proveedor.generar_texto(
            f"Resume el siguiente texto en aproximadamente tres líneas:\n\n{texto}",
            "Eres un asistente que resume textos de forma fiel y concisa.",
        )
    except (ConfigError, ErrorProveedorIA):
        return ResultadoAccion(codigo=0, salida=MENSAJE_OFFLINE_IA)
    return ResultadoAccion(codigo=0, salida=resumen)


def validar_tarea_ia(respuesta: str) -> ResultadoAccion:
    """Valida y normaliza la tarea devuelta por el modelo, sin depender del proveedor."""
    campos: dict[str, str] = {}
    for linea in respuesta.splitlines():
        etiqueta, separador, valor = linea.partition(":")
        if separador:
            campos[etiqueta.strip().casefold()] = valor.strip()

    titulo = campos.get("título", "")
    prioridad = campos.get("prioridad", "")
    fecha = campos.get("fecha sugerida", "")

    if not titulo or not prioridad:
        return ResultadoAccion(
            codigo=1,
            error="La respuesta de la IA no incluye un título y una prioridad válidos.",
        )

    normalizadas = {"alta": "Alta", "media": "Media", "baja": "Baja"}
    prioridad_normalizada = normalizadas.get(prioridad.casefold())
    if prioridad_normalizada is None:
        return ResultadoAccion(
            codigo=1,
            error="La prioridad de la respuesta de la IA debe ser Alta, Media o Baja.",
        )

    if not fecha or fecha.casefold() == "sin fecha":
        fecha_normalizada = "Sin fecha"
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        return ResultadoAccion(
            codigo=1,
            error="La fecha de la respuesta de la IA debe usar el formato AAAA-MM-DD.",
        )
    else:
        try:
            date.fromisoformat(fecha)
        except ValueError:
            return ResultadoAccion(
                codigo=1,
                error="La fecha de la respuesta de la IA no existe en el calendario.",
            )
        fecha_normalizada = fecha

    salida = (
        f"Título: {titulo}\n"
        f"Prioridad: {prioridad_normalizada}\n"
        f"Fecha sugerida: {fecha_normalizada}"
    )
    return ResultadoAccion(codigo=0, salida=salida)


@registrar("tarea-ia")
def tarea_ia(ctx: ContextoAccion) -> ResultadoAccion:
    """Convierte texto libre en una tarea estructurada con IA."""
    texto = str(ctx.parametros.get("texto") or "").strip()
    if not texto:
        return ResultadoAccion(codigo=1, error="Indica el texto para crear la tarea.")

    proveedor = ctx.proveedor_ia
    if proveedor is None:
        return ResultadoAccion(codigo=0, salida=MENSAJE_OFFLINE_IA)

    try:
        propuesta = proveedor.generar_texto(
            "Convierte esta petición en una tarea. Devuelve exactamente tres líneas "
            "en texto plano y con este formato:\n"
            "Título: <título breve>\n"
            "Prioridad: <Alta, Media o Baja>\n"
            "Fecha sugerida: <AAAA-MM-DD o Sin fecha>\n\n"
            f"Petición: {texto}",
            "Eres un asistente que organiza peticiones como tareas claras y copiables. "
            "No añadas introducciones, explicaciones ni formato Markdown.",
        )
    except (ConfigError, IAnoDisponible):
        return ResultadoAccion(codigo=0, salida=MENSAJE_OFFLINE_IA)
    except AutenticacionProveedorIA:
        return ResultadoAccion(
            codigo=1,
            error="La clave de la IA del centro no es válida o no tiene acceso. Revisa la configuración.",
        )
    except TimeoutProveedorIA:
        return ResultadoAccion(
            codigo=1,
            error="La IA del centro agotó el tiempo de espera. Inténtalo de nuevo.",
        )
    except ErrorProveedorIA:
        return ResultadoAccion(
            codigo=1,
            error="La IA del centro devolvió una respuesta inválida.",
        )

    return validar_tarea_ia(propuesta)
