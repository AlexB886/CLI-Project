"""Acciones internas que pueden declararse en acciones.json."""

from datetime import datetime
from pathlib import Path

from tareas.acciones.registro import registrar
from tareas.modelos import ContextoAccion, ResultadoAccion, TablaContenido


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
