"""Pruebas de conversión y resolución de parámetros del CLI."""

from pathlib import Path

import pytest

from tareas.errores import AccionNoValida
from tareas.modelos import Accion, Parametro, TipoEjecucion
from tareas.parametros import convertir, resolver_parametros


def crear_accion(parametros):
    return Accion(
        nombre="demo",
        descripcion="Acción de prueba",
        tipo=TipoEjecucion.FUNCION,
        ejecutar="demo",
        destructiva=False,
        parametros=tuple(parametros),
    )


@pytest.mark.parametrize(
    ("valor", "tipo", "esperado"),
    [
        (123, "texto", "123"),
        ("42", "entero", 42),
        ("~/notas.txt", "ruta", Path("~/notas.txt").expanduser()),
        ("sí", "booleano", True),
        ("NO", "booleano", False),
        (None, "entero", None),
    ],
)
def test_convertir_tipos_validos(valor, tipo, esperado):
    assert convertir(valor, tipo, "valor") == esperado


@pytest.mark.parametrize(
    ("valor", "tipo"),
    [
        (True, "entero"),
        ("4.2", "entero"),
        ("quizá", "booleano"),
        ("valor", "no-definido"),
    ],
)
def test_convertir_rechaza_valores_invalidos(valor, tipo):
    with pytest.raises(ValueError):
        convertir(valor, tipo, "valor")


def test_resuelve_posicionales_valores_por_defecto_y_tipos():
    accion = crear_accion(
        [
            Parametro("nombre", "texto", requerido=True),
            Parametro("intentos", "entero", por_defecto="2"),
            Parametro("activo", "booleano", por_defecto=True),
        ]
    )

    assert resolver_parametros(accion, ["Eva"]) == {
        "nombre": "Eva",
        "intentos": 2,
        "activo": True,
    }


def test_resuelve_parametro_nombrado_y_preserva_igual_en_valor():
    accion = crear_accion([Parametro("texto", "texto", requerido=True)])

    assert resolver_parametros(accion, pares=["texto=a=b"]) == {"texto": "a=b"}


@pytest.mark.parametrize(
    ("posicionales", "pares", "mensaje"),
    [
        ([], [], "Falta el parámetro obligatorio"),
        (["uno", "dos"], [], "admite 1 argumento"),
        ([], ["sin-separador"], "CLAVE=VALOR"),
        ([], ["=valor"], "nombre del parámetro"),
        ([], ["desconocido=1"], "no tiene el parámetro"),
        (["uno"], ["dato=dos"], "indicado dos veces"),
        ([], ["dato=no-entero"], "número entero"),
    ],
)
def test_resolver_parametros_rechaza_entradas_invalidas(
    posicionales,
    pares,
    mensaje,
):
    accion = crear_accion(
        [
            Parametro("dato", "entero", requerido=True),
        ]
    )

    with pytest.raises(AccionNoValida, match=mensaje):
        resolver_parametros(accion, posicionales, pares)


def test_parametro_opcional_sin_valor_se_resuelve_como_none():
    accion = crear_accion([Parametro("opcional")])

    assert resolver_parametros(accion) == {"opcional": None}


def test_varios_posicionales_se_asignan_al_parametro_rutas():
    """`repaso-ia uno.txt dos.txt` son dos apuntes, no apunte + objetivo."""
    accion = crear_accion(
        [
            Parametro("archivos", "rutas", requerido=True),
            Parametro("objetivo", "texto", por_defecto="repaso general"),
        ]
    )

    assert resolver_parametros(accion, ["uno.txt", "dos.txt"]) == {
        "archivos": ["uno.txt", "dos.txt"],
        "objetivo": "repaso general",
    }


def test_rutas_posicionales_y_valor_nombrado_repetido_se_rechaza():
    accion = crear_accion([Parametro("archivos", "rutas", requerido=True)])

    with pytest.raises(AccionNoValida, match="indicado dos veces"):
        resolver_parametros(accion, ["uno.txt"], ["archivos=dos.txt"])
