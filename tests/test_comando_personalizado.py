"""Pruebas de comandos declarados por el usuario en configuración temporal."""

import subprocess
import sys

from tareas.acciones.comando import AccionComando
from tareas.modelos import Accion, ContextoAccion, TipoEjecucion


def crear_accion(argv):
    return Accion(
        nombre="comando-prueba",
        descripcion="Comando de prueba aislado",
        tipo=TipoEjecucion.COMANDO,
        ejecutar=tuple(argv),
        destructiva=False,
    )


def test_comando_personalizado_ejecuta_argv_sin_shell():
    accion = AccionComando(
        crear_accion([sys.executable, "-c", "print('salida segura')"])
    )

    resultado = accion.ejecutar(ContextoAccion(parametros={}))

    assert resultado.codigo == 0
    assert resultado.salida.strip() == "salida segura"
    assert resultado.error == ""


def test_comando_personalizado_simula_sin_invocar_subprocess(monkeypatch):
    def subprocess_no_esperado(*args, **kwargs):
        raise AssertionError("La simulación no debe ejecutar el comando")

    monkeypatch.setattr(subprocess, "run", subprocess_no_esperado)
    accion = AccionComando(crear_accion([sys.executable, "-c", "pass"]))

    resultado = accion.previsualizar(ContextoAccion(parametros={}, simular=True))

    assert resultado.codigo == 0
    assert "Ejecutaría:" in resultado.salida


def test_comando_personalizado_devuelve_codigo_y_stderr():
    accion = AccionComando(crear_accion([sys.executable, "-c", "pass"]))

    def ejecutar(*args, **kwargs):
        assert kwargs["shell"] is False
        return subprocess.CompletedProcess(args[0], 7, "", "fallo controlado")

    original_run = subprocess.run
    subprocess.run = ejecutar
    try:
        resultado = accion.ejecutar(ContextoAccion(parametros={}))
    finally:
        subprocess.run = original_run

    assert resultado.codigo == 7
    assert resultado.error == "fallo controlado"


def test_comando_personalizado_inexistente_devuelve_error():
    accion = AccionComando(
        crear_accion(["ejecutable-que-no-existe-tareas-test-917263"])
    )

    resultado = accion.ejecutar(ContextoAccion(parametros={}))

    assert resultado.codigo == 1
    assert "No se encontró la orden" in resultado.error
