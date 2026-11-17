"""Pruebas del esquema y la lectura de acciones.json."""

import json

import pytest

from tareas.configuracion import CargadorAccionesJSON
from tareas.errores import ConfigError
from tareas.modelos import TipoEjecucion


def accion_valida(**cambios):
    accion = {
        "nombre": "demo",
        "descripcion": "Acción de prueba",
        "tipo": "funcion",
        "ejecutar": "demo",
        "destructiva": False,
        "parametros": {},
    }
    accion.update(cambios)
    return accion


def escribir_config(tmp_path, acciones, *, version=1):
    ruta = tmp_path / "acciones.json"
    ruta.write_text(
        json.dumps({"version": version, "acciones": acciones}),
        encoding="utf-8",
    )
    return ruta


def test_carga_accion_funcion_y_comando_validos(tmp_path):
    ruta = escribir_config(
        tmp_path,
        [
            accion_valida(
                parametros={
                    "ruta": {"tipo": "ruta", "requerido": True},
                    "intentos": {"tipo": "entero", "por_defecto": "3"},
                }
            ),
            {
                "nombre": "comando-demo",
                "descripcion": "Comando de prueba",
                "tipo": "comando",
                "ejecutar": ["printf", "%s", "hola"],
                "destructiva": False,
            },
        ],
    )

    acciones = CargadorAccionesJSON().cargar(ruta)

    assert len(acciones) == 2
    assert acciones[0].tipo is TipoEjecucion.FUNCION
    assert acciones[0].parametros[0].requerido is True
    assert acciones[1].tipo is TipoEjecucion.COMANDO
    assert acciones[1].ejecutar == ("printf", "%s", "hola")


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        ([], "raíz"),
        ({"version": True, "acciones": []}, "versión"),
        ({"version": 1, "acciones": {}}, "lista"),
    ],
)
def test_rechaza_raiz_version_o_lista_invalidas(tmp_path, datos, mensaje):
    ruta = tmp_path / "acciones.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(ConfigError, match=mensaje):
        CargadorAccionesJSON().cargar(ruta)


def test_rechaza_json_mal_formado(tmp_path):
    ruta = tmp_path / "acciones.json"
    ruta.write_text('{"version": 1,', encoding="utf-8")

    with pytest.raises(ConfigError, match="JSON inválido"):
        CargadorAccionesJSON().cargar(ruta)


def test_rechaza_archivo_ausente_y_directorio(tmp_path):
    cargador = CargadorAccionesJSON()

    with pytest.raises(ConfigError, match="No existe"):
        cargador.cargar(tmp_path / "inexistente.json")
    with pytest.raises(ConfigError, match="no es un fichero"):
        cargador.cargar(tmp_path)


@pytest.mark.parametrize(
    ("acciones", "mensaje"),
    [
        ([accion_valida(nombre="MAYUSCULAS")], "nombre.*no es válido"),
        ([accion_valida(nombre="version")], "reservado"),
        ([accion_valida(), accion_valida()], "duplicado"),
        ([accion_valida(descripcion=" ")], "descripción no vacía"),
        ([accion_valida(tipo="sistema")], "tipo no válido"),
        ([accion_valida(ejecutar=" ")], "función registrada"),
        ([accion_valida(destructiva="no")], "destructiva.*true o false"),
        ([accion_valida(ia="sí")], "ia.*true o false"),
        ([accion_valida(clave_sorpresa=True)], "claves desconocidas"),
    ],
)
def test_rechaza_definiciones_de_accion_invalidas(tmp_path, acciones, mensaje):
    ruta = escribir_config(tmp_path, acciones)

    with pytest.raises(ConfigError, match=mensaje):
        CargadorAccionesJSON().cargar(ruta)


@pytest.mark.parametrize(
    "parametro",
    [
        {"tipo": "misterioso"},
        {"tipo": "entero", "requerido": "si"},
        {"tipo": "texto", "ayuda": 4},
        {"tipo": "entero", "por_defecto": "no-numérico"},
        {"tipo": "texto", "requerido": True, "por_defecto": "valor"},
        {"tipo": "texto", "desconocido": True},
    ],
)
def test_rechaza_definiciones_de_parametro_invalidas(tmp_path, parametro):
    ruta = escribir_config(
        tmp_path,
        [accion_valida(parametros={"valor": parametro})],
    )

    with pytest.raises(ConfigError):
        CargadorAccionesJSON().cargar(ruta)


def test_rechaza_argumentos_de_comando_invalidos(tmp_path):
    for argv in ([], ["", "arg"], "printf hola"):
        ruta = escribir_config(
            tmp_path,
            [
                {
                    "nombre": "comando-demo",
                    "descripcion": "Comando",
                    "tipo": "comando",
                    "ejecutar": argv,
                    "destructiva": False,
                }
            ],
        )
        with pytest.raises(ConfigError, match="comando"):
            CargadorAccionesJSON().cargar(ruta)
