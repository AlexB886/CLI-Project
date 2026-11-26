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
from tareas.repaso.contenidos import (
    construir_documento,
    detectar_esquemas,
    esquema_de_bloques,
)
from tareas.repaso.escritorio import EscritorioNoDisponible, abrir_en_writer
from tareas.repaso.fragmentacion import SintesisError, sintetizar
from tareas.repaso.lectura import cargar_documentos
from tareas.repaso.odt import escribir_odt
from tareas.repaso.seguridad import (
    RutaFueraDeBaseError,
    con_etapa,
    fuera_de_base,
    objetivo_normal,
    ruta_dentro_de_base,
    ruta_salida,
)

__all__ = [
    "MENSAJE_OFFLINE_IA",
    "RutaFueraDeBaseError",
    "listar",
    "validar",
    "borrar",
    "ver",
    "tamano",
    "tamano_legible",
    "resumir_ia",
    "tarea_ia",
    "validar_tarea_ia",
    "repaso_ia",
]

MENSAJE_OFFLINE_IA = "IA no disponible (modo offline): sigo con las acciones sin IA"


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
    ruta = ruta_dentro_de_base(ruta, base, absolute=True)

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

    max_lineas = 200
    try:
        lineas: list[str] = []
        truncado = False
        with ruta.open(encoding="utf-8", errors="strict") as fichero:
            for linea in fichero:
                if len(lineas) >= max_lineas:
                    truncado = True
                    break
                lineas.append(linea.rstrip("\n"))
    except UnicodeDecodeError:
        return ResultadoAccion(
            codigo=1,
            error=f"«{ruta}» no es un fichero de texto (UTF-8).",
        )
    except OSError as exc:
        return ResultadoAccion(codigo=1, error=f"No se pudo leer «{ruta}»: {exc}")

    aviso = ""
    if truncado:
        aviso = "\n… (más líneas: usa `sed -n '201,400p' para continuar)."
    elif len(lineas) > max_lineas:
        aviso = f"\n… ({len(lineas) - max_lineas} líneas omitidas)."
        lineas = lineas[:max_lineas]

    return ResultadoAccion(codigo=0, salida="\n".join(lineas) + aviso)


@registrar("tamano")
def tamano(ctx: ContextoAccion) -> ResultadoAccion:
    """Calcula el tamaño total de una carpeta, recursivo y sin seguir enlaces."""
    carpeta = _como_ruta(ctx.parametros.get("carpeta") or ".")
    if not carpeta.is_dir():
        return ResultadoAccion(
            codigo=1,
            error=f"«{carpeta}» no existe o no es una carpeta.",
        )

    import os

    total = 0
    ficheros = 0
    carpetas = 0
    omitidos = 0
    for raiz, nombres_dir, nombres_fich in os.walk(carpeta, followlinks=False):
        carpeta_actual = Path(raiz)
        for nombre in nombres_dir:
            ruta = carpeta_actual / nombre
            if ruta.is_symlink():
                omitidos += 1
            else:
                carpetas += 1
        for nombre in nombres_fich:
            ruta = carpeta_actual / nombre
            try:
                if ruta.is_symlink() or not ruta.is_file():
                    omitidos += 1
                    continue
                total += ruta.stat().st_size
                ficheros += 1
            except OSError:
                omitidos += 1

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
                *(
                    (("No contabilizados (enlaces o permisos)", str(omitidos)),)
                    if omitidos
                    else ()
                ),
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


@registrar("repaso-ia")
def repaso_ia(ctx: ContextoAccion) -> ResultadoAccion:
    """Genera un documento de repaso ODT con IA y lo abre en LibreOffice Writer."""
    brutos = ctx.parametros.get("archivos") or []
    if isinstance(brutos, (str, Path)):
        brutos = [brutos]
    archivos = [Path(str(r)).expanduser() for r in brutos]
    if not archivos:
        return ResultadoAccion(codigo=1, error="Indica al menos un documento de apuntes.")

    try:
        base = Path(str(ctx.parametros.get("base") or Path.cwd())).expanduser().resolve()
    except OSError as exc:
        return ResultadoAccion(codigo=1, error=f"No se pudo resolver la raíz autorizada: {exc}")
    for ruta in archivos:
        absoluta = ruta if ruta.is_absolute() else base / ruta
        try:
            resuelta = absoluta.resolve()
        except OSError:
            resuelta = absoluta
        if fuera_de_base(resuelta, base):
            return ResultadoAccion(
                codigo=1,
                error=f"El apunte «{ruta}» está fuera de la raíz autorizada «{base}».",
            )

    proveedor = ctx.proveedor_ia
    if proveedor is None:
        return ResultadoAccion(codigo=0, salida=MENSAJE_OFFLINE_IA)

    informes: list[str] = []
    documentos = cargar_documentos(archivos, informes)
    ilegibles = [r for r in archivos if all(d.origen != r for d in documentos)]

    def avisos(texto: str) -> None:
        print(texto, flush=True)

    def _es_tty() -> bool:
        import sys

        return sys.stdout.isatty()

    if ilegibles:
        nombres = ", ".join(str(r) for r in ilegibles)
        avisos(f"Atención: no se pudieron leer {nombres}.")
    if not documentos:
        detalle = " ".join(informes) or "Ningún documento contenía texto legible."
        return ResultadoAccion(
            codigo=1,
            error=f"No hay apuntes que repasar: {detalle}",
        )

    objetivo = objetivo_normal(str(ctx.parametros.get("objetivo") or ""))
    paralelo = max(1, min(8, int(ctx.parametros.get("paralelo") or 3)))

    nombre_parametro = str(ctx.parametros.get("nombre") or "").strip()
    titulo = nombre_parametro or documentos[0].origen.stem
    nombre = re.sub(r"[^\w\- ]+", "", titulo).strip().replace(" ", "-")
    salida = ctx.parametros.get("salida")
    destino = ruta_salida(
        Path(str(salida)) if salida else documentos[0].origen.parent, base
    )
    if destino.suffix.lower() == ".odt":
        destino = destino.parent

    ruta_final = destino / f"{nombre}.odt"
    numero = 1
    try:
        while ruta_final.exists():
            numero += 1
            ruta_final = destino / f"{nombre}_{numero}.odt"
    except OSError as exc:
        return ResultadoAccion(
            codigo=1,
            error=f"No se pudo comprobar la carpeta de destino «{destino}»: {exc}",
        )

    if ctx.simular:
        nombres = ", ".join(d.origen.name for d in documentos)
        aviso_omisiones = f" Omitidos: {len(ilegibles)}." if ilegibles else ""
        return ResultadoAccion(
            codigo=0,
            salida=(
                f"[simular] Se generaría «{ruta_final}» a partir de {nombres} "
                f"con objetivo «{objetivo}» "
                f"y se abriría en LibreOffice Writer.{aviso_omisiones}"
            ),
        )

    texto = "\n\n".join(d.texto for d in documentos)
    from tareas.visual import Progreso

    if len(texto.strip()) <= 9_000:
        progreso = Progreso(1, "Analizando los apuntes", imprimir=avisos)
    else:
        from tareas.repaso.fragmentacion import LONGITUD_FRAGMENTO, fragmentar

        progreso = Progreso(
            len(fragmentar(texto)) + 1, "Analizando los apuntes", imprimir=avisos
        )
    try:
        maestro = sintetizar(
            texto,
            generar=proveedor.generar_texto,
            objetivo=objetivo,
            informar=avisos if not _es_tty() else None,
            progreso=progreso,
            paralelo=paralelo,
        )
    except SintesisError as exc:
        return ResultadoAccion(codigo=1, error=f"{exc} {exc.detalle}".strip())
    except AutenticacionProveedorIA as exc:
        return ResultadoAccion(
            codigo=1,
            error=con_etapa(
                "La clave de la IA del centro no es válida o no tiene acceso. Revisa la configuración.",
                exc,
            ),
        )
    except TimeoutProveedorIA as exc:
        return ResultadoAccion(
            codigo=1,
            error=con_etapa(
                "La IA del centro agotó el tiempo de espera. Inténtalo de nuevo.", exc
            ),
        )
    except ErrorProveedorIA as exc:
        return ResultadoAccion(
            codigo=1,
            error=con_etapa(
                "La IA del centro devolvió una respuesta inválida.", exc
            ),
        )

    esquemas = detectar_esquemas(maestro)
    if not esquemas:
        respaldo = esquema_de_bloques(maestro, f"Repaso: {titulo}")
        if respaldo is not None:
            esquemas = [respaldo]

    secciones = construir_documento(maestro, esquemas)
    fuentes = [d.origen.name for d in documentos]
    generado = datetime.now().strftime("%d/%m/%Y %H:%M")

    try:
        escribir_odt(
            ruta_final,
            f"Repaso: {titulo}",
            f"Objetivo de estudio: {objetivo}",
            secciones,
            esquemas,
            fuentes,
            generado,
        )
    except OSError as exc:
        return ResultadoAccion(codigo=1, error=f"No se pudo escribir «{ruta_final}»: {exc}")

    mensajes = [f"Repaso generado en «{ruta_final}»."]
    if numero > 1:
        mensajes.append(
            f"«{nombre}.odt» ya existía; se guardó como «{ruta_final.name}» sin tocarlo."
        )
    for informe in informes:
        mensajes.append(f"Aviso: {informe}")

    abrir = ctx.parametros.get("abrir", True)
    if abrir:
        try:
            programa = abrir_en_writer(ruta_final)
            mensajes.append(f"Abriendo el repaso en {programa}…")
        except EscritorioNoDisponible as exc:
            mensajes.append(f"No se pudo abrir automáticamente: {exc} Ruta: {ruta_final}")
    else:
        mensajes.append(f"Abre el repaso con: libreoffice --writer {ruta_final}")

    return ResultadoAccion(codigo=0, salida="\n".join(mensajes))

