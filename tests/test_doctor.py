"""Pruebas del diagnóstico de instalación y configuración."""

import json

from typer.testing import CliRunner

from tareas.cli import crear_app


def escribir_acciones(ruta, acciones):
    ruta.write_text(
        json.dumps({"version": 1, "acciones": acciones}),
        encoding="utf-8",
    )


def accion_listar():
    return {
        "nombre": "listar",
        "descripcion": "Lista una carpeta",
        "tipo": "funcion",
        "ejecutar": "listar",
        "destructiva": False,
    }


def test_doctor_muestra_estado_sin_revelar_la_clave(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    escribir_acciones(ruta, [accion_listar()])
    monkeypatch.setenv("TAREAS_API_KEY", "clave-sintetica-secreta")
    monkeypatch.delenv("TAREAS_CA_BUNDLE", raising=False)

    resultado = CliRunner().invoke(crear_app(ruta), ["doctor"])

    assert resultado.exit_code == 0, resultado.output
    assert "Correcta" in resultado.output
    assert "Acciones declaradas" in resultado.output
    assert "configurada" in resultado.output
    assert "clave-sintetica-secreta" not in resultado.output
    assert "no se comprueba" in resultado.output.casefold()


def test_doctor_informa_configuracion_invalida_sin_traceback(tmp_path, monkeypatch):
    # el diagnóstico lee la config como el proveedor: aísslalo del .env del proyecto
    monkeypatch.chdir(tmp_path)
    ruta = tmp_path / "acciones.json"
    ruta.write_text("{no-json", encoding="utf-8")
    monkeypatch.delenv("TAREAS_API_KEY", raising=False)
    monkeypatch.delenv("TAREAS_CA_BUNDLE", raising=False)

    resultado = CliRunner().invoke(crear_app(ruta), ["doctor"])

    assert resultado.exit_code == 0
    assert "JSON inválido" in resultado.output
    assert "Traceback" not in resultado.output
    assert "no configurada" in resultado.output


def test_doctor_indica_si_la_ca_configurada_existe(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    escribir_acciones(ruta, [accion_listar()])
    certificado = tmp_path / "ca.crt"
    certificado.write_text("certificado sintético", encoding="utf-8")
    monkeypatch.delenv("TAREAS_API_KEY", raising=False)
    monkeypatch.setenv("TAREAS_CA_BUNDLE", str(certificado))
    runner = CliRunner()
    app = crear_app(ruta)

    presente = runner.invoke(app, ["doctor"])
    certificado.unlink()
    ausente = runner.invoke(app, ["doctor"])

    assert "Fichero presente" in presente.output
    assert "Fichero no encontrado" in ausente.output
    assert str(certificado) not in presente.output
