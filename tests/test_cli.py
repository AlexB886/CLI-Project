"""Pruebas de integración de CLI con acciones.json temporal."""

import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from tareas.cli import crear_app
from tareas.ia.nulo import ProveedorNulo


def escribir_acciones(ruta, acciones):
    ruta.write_text(
        json.dumps({"version": 1, "acciones": acciones}),
        encoding="utf-8",
    )


import re


_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def salida(resultado) -> str:
    """Reúne stdout y stderr del Result de forma explícita y portable.

    Los errores de uso y de configuración los escribe Typer/Rich en stderr.
    `resultado.output` solo incluye el stderr cuando el CliRunner mezcla ambos
    flujos, lo que no está garantizado entre versiones de Typer/Click ni entre
    plataformas. Sumar stdout y stderr hace el test robusto sin ocultar fallos.

    En CI (GITHUB_ACTIONS/FORCE_COLOR) Rich/Typer fuerza colores ANSI y el
    resaltado puede partir tokens (p. ej. ``--no-existe``) con códigos de
    escape; se eliminan para que las aserciones de contenido sean estables.
    """
    texto = f"{resultado.stdout}{resultado.stderr}"
    return _ANSI_RE.sub("", texto)


def test_cli_registra_y_ejecuta_accion_desde_json_temporal(tmp_path, monkeypatch):
    carpeta = tmp_path / "documentos"
    carpeta.mkdir()
    (carpeta / "nota.txt").write_text("nota", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "listar-temporal",
                "descripcion": "Lista una carpeta temporal",
                "tipo": "funcion",
                "ejecutar": "listar",
                "destructiva": False,
                "parametros": {"carpeta": {"tipo": "ruta", "requerido": True}},
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)
    runner = CliRunner()

    resultado = runner.invoke(crear_app(ruta), ["listar-temporal", str(carpeta)])

    assert resultado.exit_code == 0, resultado.output
    assert "nota.txt" in resultado.output


def test_cli_devuelve_codigo_de_configuracion_invalida(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    ruta.write_text("{json inválido", encoding="utf-8")
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["acciones"])

    assert resultado.exit_code == 3
    assert "JSON inválido" in salida(resultado)


def test_cli_devuelve_codigo_de_uso_para_accion_desconocida(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    escribir_acciones(ruta, [])
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["ejecutar", "no-existe"])

    assert resultado.exit_code == 2
    assert "no existe" in salida(resultado)


def test_cli_simula_borrado_sin_eliminar_fichero(tmp_path, monkeypatch):
    objetivo = tmp_path / "objetivo.txt"
    objetivo.write_text("mantener", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "borrar-temporal",
                "descripcion": "Borra un fichero temporal",
                "tipo": "funcion",
                "ejecutar": "borrar",
                "destructiva": True,
                "parametros": {
                    "ruta": {"tipo": "ruta", "requerido": True},
                    "base": {"tipo": "ruta", "por_defecto": str(tmp_path)},
                },
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(
        crear_app(ruta),
        ["borrar-temporal", "objetivo.txt", "--simular"],
    )

    assert resultado.exit_code == 0, resultado.output
    assert "Se borraría" in resultado.output
    assert objetivo.read_text(encoding="utf-8") == "mantener"


def test_cli_cancelar_confirmacion_conserva_fichero_temporal(tmp_path, monkeypatch):
    objetivo = tmp_path / "objetivo.txt"
    objetivo.write_text("mantener", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "borrar-temporal",
                "descripcion": "Borra un fichero temporal",
                "tipo": "funcion",
                "ejecutar": "borrar",
                "destructiva": True,
                "parametros": {
                    "ruta": {"tipo": "ruta", "requerido": True},
                    "base": {"tipo": "ruta", "por_defecto": str(tmp_path)},
                },
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(
        crear_app(ruta),
        ["borrar-temporal", "objetivo.txt"],
        input="n\n",
    )

    assert resultado.exit_code == 1
    assert "cancelada" in salida(resultado)
    assert objetivo.read_text(encoding="utf-8") == "mantener"


def test_cli_abortar_confirmacion_destructiva_es_cancelacion_codigo_uno(
    tmp_path, monkeypatch
):
    """Cancelar con Ctrl-D/Abort es un «no»: código 1, sin traceback, fichero intacto."""
    objetivo = tmp_path / "objetivo.txt"
    objetivo.write_text("mantener", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "borrar-temporal",
                "descripcion": "Borra un fichero temporal",
                "tipo": "funcion",
                "ejecutar": "borrar",
                "destructiva": True,
                "parametros": {
                    "ruta": {"tipo": "ruta", "requerido": True},
                    "base": {"tipo": "ruta", "por_defecto": str(tmp_path)},
                },
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["borrar-temporal", "objetivo.txt"])

    assert resultado.exit_code == 1, resultado.output
    assert "Traceback" not in salida(resultado)
    assert objetivo.read_text(encoding="utf-8") == "mantener"


def test_cli_ejecuta_comando_personalizado_de_json_temporal(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "comando-temporal",
                "descripcion": "Imprime una marca de prueba",
                "tipo": "comando",
                "ejecutar": [sys.executable, "-c", "print('comando-json-ok')"],
                "destructiva": False,
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["comando-temporal"])

    assert resultado.exit_code == 0, resultado.output
    assert "comando-json-ok" in resultado.output


def test_cli_acciones_ia_indican_modo_offline_sin_red(tmp_path, monkeypatch):
    fichero = tmp_path / "texto.txt"
    fichero.write_text("contenido sintético", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "resumir-ia-temporal",
                "descripcion": "Resume con proveedor nulo",
                "tipo": "funcion",
                "ejecutar": "resumir-ia",
                "destructiva": False,
                "ia": True,
                "parametros": {"ruta": {"tipo": "ruta", "requerido": True}},
            },
            {
                "nombre": "tarea-ia-temporal",
                "descripcion": "Crea tarea con proveedor nulo",
                "tipo": "funcion",
                "ejecutar": "tarea-ia",
                "destructiva": False,
                "ia": True,
                "parametros": {"texto": {"tipo": "texto", "requerido": True}},
            },
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)
    app = crear_app(ruta)
    runner = CliRunner()

    resumen = runner.invoke(app, ["resumir-ia-temporal", str(fichero)])
    tarea = runner.invoke(app, ["tarea-ia-temporal", "preparar exposición"])

    assert resumen.exit_code == 0, resumen.output
    assert tarea.exit_code == 0, tarea.output
    assert "modo offline" in resumen.output
    assert "modo offline" in tarea.output


def test_cli_opcion_desconocida_mensaje_humano_sin_traceback(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    escribir_acciones(ruta, [])
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["--no-existe"])

    assert resultado.exit_code == 2
    assert "Traceback" not in salida(resultado)
    assert "no-existe" in salida(resultado)


def test_cli_parametros_de_mas_mensaje_humano_sin_traceback(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "listar-temporal",
                "descripcion": "Lista una carpeta",
                "tipo": "funcion",
                "ejecutar": "listar",
                "destructiva": False,
                "parametros": {"carpeta": {"tipo": "ruta", "requerido": True}},
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["listar-temporal", "a", "b"])

    assert resultado.exit_code == 2
    assert "Traceback" not in salida(resultado)


def test_cli_config_inexistente_codigo_tres_sin_traceback(tmp_path, monkeypatch):
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(
        crear_app(tmp_path / "no-existe.json"), ["ejecutar", "cualquiera"]
    )

    assert resultado.exit_code == 3
    assert "No existe el fichero de acciones" in salida(resultado).replace("\n", " ")
    assert "Traceback" not in salida(resultado)


def test_cli_sin_clave_usa_proveedor_nulo_sin_red(tmp_path, monkeypatch):
    """Con TAREAS_API_KEY ausente el proveedor real es ProveedorNulo: cero red."""
    import tareas.ia.nulo as nulo

    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "resumir-temporal",
                "descripcion": "Resume con proveedor real simulado a nulo",
                "tipo": "funcion",
                "ejecutar": "resumir-ia",
                "destructiva": False,
                "ia": True,
                "parametros": {"ruta": {"tipo": "ruta", "requerido": True}},
            }
        ],
    )
    monkeypatch.delenv("TAREAS_API_KEY", raising=False)
    monkeypatch.setattr("tareas.ia.configuracion.Path.cwd", lambda: tmp_path)
    fichero = tmp_path / "texto.txt"
    fichero.write_text("contenido", encoding="utf-8")

    resultado = CliRunner().invoke(crear_app(ruta), ["resumir-temporal", str(fichero)])

    assert resultado.exit_code == 0, resultado.output
    assert "modo offline" in resultado.output


def test_cli_error_de_conexion_no_produce_traceback(tmp_path, monkeypatch):
    """Un fallo de red del proveedor se informa en humano, con código 0 y sin traceback."""
    from tareas.ia.errores import IAnoDisponible

    class SinConexion:
        nombre = "simulada"

        def disponible(self) -> bool:
            return False

        def generar_texto(self, peticion: str, contexto: str) -> str:
            raise IAnoDisponible("sin conexión")

        def proponer_acciones(self, peticion, contexto):
            return []

    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "resumir-temporal",
                "descripcion": "Resume sin red",
                "tipo": "funcion",
                "ejecutar": "resumir-ia",
                "destructiva": False,
                "ia": True,
                "parametros": {"ruta": {"tipo": "ruta", "requerido": True}},
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", SinConexion)
    fichero = tmp_path / "texto.txt"
    fichero.write_text("contenido", encoding="utf-8")

    resultado = CliRunner().invoke(crear_app(ruta), ["resumir-temporal", str(fichero)])

    assert resultado.exit_code == 0
    assert "modo offline" in resultado.output
    assert "Traceback" not in salida(resultado)


def test_composicion_de_acciones_sobre_una_carpeta_de_prueba(tmp_path, monkeypatch):
    """Flujo combinado real: listar → validar → tamano → ver → borrar --dry-run.

    Uses el acciones.json del repositorio: la composición se apoya en la shell
    (un comando tras otro con códigos de salida), no en un motor de pipelines.
    """
    ruta_acciones = (
        Path(__file__).resolve().parents[1] / "acciones.json"
    )
    assert ruta_acciones.is_file(), "el ejemplo requiere acciones.json en la raíz"

    apuntes = tmp_path / "apuntes"
    apuntes.mkdir()
    (apuntes / "tema1.txt").write_text("La fotosíntesis.", encoding="utf-8")
    (apuntes / "tema2.md").write_text("La mitocondria.", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)
    runner = CliRunner()

    lista = runner.invoke(crear_app(ruta_acciones), ["listar", "apuntes"])
    assert lista.exit_code == 0
    assert "tema1.txt" in lista.output and "tema2.md" in lista.output

    valido = runner.invoke(crear_app(ruta_acciones), ["validar", "apuntes/tema1.txt"])
    assert valido.exit_code == 0 and "OK" in valido.output

    roto = runner.invoke(crear_app(ruta_acciones), ["validar", "apuntes/no-existe.txt"])
    assert roto.exit_code == 1 and "no existe" in salida(roto)

    peso = runner.invoke(crear_app(ruta_acciones), ["tamano", "apuntes"])
    assert peso.exit_code == 0 and "Ficheros" in peso.output

    visto = runner.invoke(crear_app(ruta_acciones), ["ver", "apuntes/tema2.md"])
    assert visto.exit_code == 0 and "La mitocondria." in visto.output

    borrado = runner.invoke(
        crear_app(ruta_acciones), ["borrar", "apuntes/tema1.txt", "--dry-run"]
    )
    assert borrado.exit_code == 0 and "Se borraría" in borrado.output
    assert (apuntes / "tema1.txt").is_file(), "el dry-run no toca el original"
