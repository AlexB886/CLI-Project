"""Interfaz de línea de órdenes: capa fina sobre el motor."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from tareas import __version__
from tareas.acciones.registro import registro
from tareas.configuracion import CargadorAccionesJSON
from tareas.errores import AccionNoValida, ConfigError
from tareas.modelos import Accion, ResultadoAccion, TablaContenido
from tareas.motor import Motor

consola = Console()
consola_err = Console(stderr=True)


@dataclass(frozen=True)
class EstadoCLI:
    """Datos compartidos entre el callback y los comandos."""

    ruta_acciones: Path


def _ruta_solicitada() -> Path | None:
    argumentos = sys.argv[1:]
    for indice, argumento in enumerate(argumentos):
        if argumento == "--acciones":
            if indice + 1 < len(argumentos):
                return Path(argumentos[indice + 1]).expanduser()
        elif argumento.startswith("--acciones="):
            return Path(argumento.split("=", 1)[1]).expanduser()

    valor_entorno = os.environ.get("TAREAS_ACCIONES")
    if valor_entorno:
        return Path(valor_entorno).expanduser()
    return None


def _ruta_por_defecto() -> Path:
    candidatos = (
        Path("acciones.json"),
        Path(__file__).resolve().parents[2] / "acciones.json",
        Path.home() / ".config" / "tareas" / "acciones.json",
    )
    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    return Path("acciones.json")


def _error(mensaje: str) -> None:
    consola_err.print(f"[red]Error:[/red] {escape(mensaje)}")


def _presentar(resultado: ResultadoAccion) -> None:
    if isinstance(resultado.datos, TablaContenido):
        tabla = Table(title=escape(resultado.datos.titulo))
        for indice, columna in enumerate(resultado.datos.columnas):
            justificacion = "right" if indice in resultado.datos.alinear_derecha else "left"
            tabla.add_column(columna, justify=justificacion)
        for fila in resultado.datos.filas:
            tabla.add_row(*(escape(valor) for valor in fila))
        consola.print(tabla)
    elif resultado.salida:
        consola.print(resultado.salida, markup=False)

    if resultado.error:
        _error(resultado.error)


def _motor(ctx: typer.Context, si: bool = False) -> Motor:
    estado = ctx.obj if isinstance(ctx.obj, EstadoCLI) else None
    ruta = estado.ruta_acciones if estado else _ruta_por_defecto()

    def confirmar(accion: Accion) -> bool:
        if si:
            return True
        return typer.confirm(
            f"La acción «{accion.nombre}» es destructiva. ¿Continuar?",
            default=False,
        )

    return Motor(ruta, confirmador=confirmar)


def _ejecutar_accion(
    ctx: typer.Context,
    nombre: str,
    posicionales: list[str] | None,
    parametros: list[str] | None,
    dry_run: bool,
    si: bool,
) -> None:
    motor = _motor(ctx, si)
    try:
        resultado = motor.ejecutar(
            nombre,
            posicionales=posicionales,
            parametros=parametros,
            simular=dry_run,
        )
    except ConfigError as exc:
        _error(str(exc))
        raise typer.Exit(code=3) from exc
    except AccionNoValida as exc:
        _error(str(exc))
        raise typer.Exit(code=2) from exc

    _presentar(resultado)
    if resultado.codigo != 0:
        raise typer.Exit(code=resultado.codigo)


def _crear_comando(accion: Accion):
    def comando(
        ctx: typer.Context,
        args: Annotated[
            list[str] | None,
            typer.Argument(help="Argumentos posicionales de la acción."),
        ] = None,
        parametros: Annotated[
            list[str] | None,
            typer.Option(
                "--param",
                "-p",
                help="Parámetro con formato CLAVE=VALOR. Se puede repetir.",
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "--simular",
                help="Previsualiza la acción sin ejecutarla.",
            ),
        ] = False,
        si: Annotated[
            bool,
            typer.Option(
                "--si",
                "-y",
                help="Confirma automáticamente las acciones destructivas.",
            ),
        ] = False,
    ) -> None:
        _ejecutar_accion(ctx, accion.nombre, args, parametros, dry_run, si)

    comando.__name__ = f"comando_{accion.nombre.replace('-', '_')}"
    comando.__doc__ = accion.descripcion
    return comando


def _acciones_iniciales(ruta: Path) -> list[Accion]:
    try:
        acciones = CargadorAccionesJSON().cargar(ruta)
        for accion in acciones:
            registro.construir(accion)
        return acciones
    except ConfigError:
        return []


def crear_app(ruta_config: Path | None = None) -> typer.Typer:
    """Construye la app y registra un comando por cada acción del JSON."""
    app = typer.Typer(
        help="tareas: automatiza tareas repetitivas con tus ficheros.",
        no_args_is_help=True,
        add_completion=False,
    )

    ruta = (ruta_config or _ruta_solicitada() or _ruta_por_defecto()).expanduser()

    for accion in _acciones_iniciales(ruta):
        app.command(name=accion.nombre)(_crear_comando(accion))

    @app.callback()
    def principal(
        ctx: typer.Context,
        ruta_acciones: Annotated[
            Path | None,
            typer.Option(
                "--acciones",
                help="Ruta del fichero de acciones (por defecto, acciones.json).",
            ),
        ] = None,
    ) -> None:
        elegida = ruta_acciones.expanduser() if ruta_acciones else ruta
        ctx.obj = EstadoCLI(ruta_acciones=elegida)

    @app.command()
    def version() -> None:
        """Muestra la versión instalada."""
        consola.print(f"tareas {__version__}")

    @app.command("acciones")
    def acciones_cmd(ctx: typer.Context) -> None:
        """Muestra las acciones declaradas en acciones.json."""
        motor = _motor(ctx)
        try:
            lista = motor.acciones()
        except ConfigError as exc:
            _error(str(exc))
            raise typer.Exit(code=3) from exc

        if not lista:
            consola.print("No hay acciones declaradas.")
            return

        tabla = Table(title=f"Acciones de {escape(str(motor.ruta))}")
        tabla.add_column("Nombre")
        tabla.add_column("Descripción")
        tabla.add_column("Tipo")
        tabla.add_column("Destructiva")
        for accion in lista:
            tabla.add_row(
                escape(accion.nombre),
                escape(accion.descripcion),
                accion.tipo.value,
                "sí" if accion.destructiva else "no",
            )
        consola.print(tabla)

    @app.command("ejecutar")
    def ejecutar_cmd(
        ctx: typer.Context,
        nombre: Annotated[
            str,
            typer.Argument(help="Nombre de la acción declarada en acciones.json."),
        ],
        args: Annotated[
            list[str] | None,
            typer.Argument(help="Argumentos posicionales de la acción."),
        ] = None,
        parametros: Annotated[
            list[str] | None,
            typer.Option(
                "--param",
                "-p",
                help="Parámetro con formato CLAVE=VALOR. Se puede repetir.",
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "--simular",
                help="Previsualiza la acción sin ejecutarla.",
            ),
        ] = False,
        si: Annotated[
            bool,
            typer.Option(
                "--si",
                "-y",
                help="Confirma automáticamente las acciones destructivas.",
            ),
        ] = False,
    ) -> None:
        """Ejecuta una acción declarada en acciones.json."""
        _ejecutar_accion(ctx, nombre, args, parametros, dry_run, si)

    return app


app = crear_app()
