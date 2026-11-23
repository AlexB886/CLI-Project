"""Regresiones de validación de la tarea estructurada devuelta por IA."""

import pytest

from tareas.acciones import internas
from tareas.acciones.internas import MENSAJE_OFFLINE_IA, tarea_ia
from tareas.errores import ConfigError
from tareas.ia.errores import (
    AutenticacionProveedorIA,
    ErrorProveedorIA,
    IAnoDisponible,
    RespuestaIAInvalida,
    TimeoutProveedorIA,
)
from tareas.modelos import ContextoAccion


class ProveedorSimulado:
    nombre = "simulado"

    def __init__(self, respuesta=None, error=None):
        self.respuesta = respuesta
        self.error = error

    def disponible(self):
        return True

    def generar_texto(self, peticion, contexto):
        if self.error is not None:
            raise self.error
        return self.respuesta

    def proponer_acciones(self, peticion, contexto):
        raise NotImplementedError


def ejecutar(respuesta, *, texto="preparar presentación"):
    return tarea_ia(
        ContextoAccion(
            parametros={"texto": texto},
            proveedor_ia=ProveedorSimulado(respuesta=respuesta),
        )
    )


def respuesta_tarea(fecha="2028-02-29", *, titulo="Preparar presentación", prioridad="Alta"):
    return (
        f"Título: {titulo}\n"
        f"Prioridad: {prioridad}\n"
        f"Fecha sugerida: {fecha}"
    )


def test_tarea_ia_acepta_fecha_iso_valida_y_normaliza_prioridad():
    resultado = ejecutar(respuesta_tarea(prioridad="aLtA"))

    assert resultado.codigo == 0
    assert resultado.salida == (
        "Título: Preparar presentación\n"
        "Prioridad: Alta\n"
        "Fecha sugerida: 2028-02-29"
    )


@pytest.mark.parametrize("fecha", ["29/02/2028", "2028-2-9", "mañana", "20280229"])
def test_tarea_ia_rechaza_fecha_que_no_usa_iso_completo(fecha):
    resultado = ejecutar(respuesta_tarea(fecha))

    assert resultado.codigo == 1
    assert "fecha" in resultado.error.casefold()
    assert "Qwen" not in resultado.error


@pytest.mark.parametrize("fecha", ["2027-02-29", "2028-13-01", "2028-04-31"])
def test_tarea_ia_rechaza_fechas_imposibles(fecha):
    resultado = ejecutar(respuesta_tarea(fecha))

    assert resultado.codigo == 1
    assert "fecha" in resultado.error.casefold()
    assert "offline" not in resultado.error.casefold()


@pytest.mark.parametrize(
    "respuesta",
    [
        "Título: Preparar presentación\nPrioridad: Alta",
        "Título: Preparar presentación\nPrioridad: Alta\nFecha sugerida:",
        "Título: Preparar presentación\nPrioridad: Alta\nFecha sugerida: Sin fecha",
    ],
)
def test_fecha_ausente_o_vacia_se_convierte_en_sin_fecha_sin_inventar(respuesta):
    resultado = ejecutar(respuesta)

    assert resultado.codigo == 0
    assert resultado.salida.endswith("Fecha sugerida: Sin fecha")


@pytest.mark.parametrize(
    "respuesta",
    [
        "Prioridad: Alta\nFecha sugerida: 2028-02-29",
        "Título: Preparar presentación\nFecha sugerida: 2028-02-29",
        "Título: \nPrioridad: Alta\nFecha sugerida: 2028-02-29",
        "Título: Preparar presentación\nPrioridad: \nFecha sugerida: 2028-02-29",
    ],
)
def test_tarea_ia_rechaza_titulo_o_prioridad_ausentes_o_vacios(respuesta):
    resultado = ejecutar(respuesta)

    assert resultado.codigo == 1
    assert "respuesta" in resultado.error.casefold()
    assert "offline" not in resultado.error.casefold()


def test_tarea_ia_rechaza_prioridad_fuera_del_conjunto_permitido():
    resultado = ejecutar(respuesta_tarea(prioridad="Urgente"))

    assert resultado.codigo == 1
    assert "prioridad" in resultado.error.casefold()


def test_texto_de_usuario_vacio_se_rechaza_antes_de_llamar_al_proveedor():
    proveedor = ProveedorSimulado(respuesta=respuesta_tarea())

    resultado = tarea_ia(
        ContextoAccion(parametros={"texto": "  "}, proveedor_ia=proveedor)
    )

    assert resultado.codigo == 1
    assert "Indica el texto" in resultado.error


@pytest.mark.parametrize("error", [None, ConfigError("sin proveedor")])
def test_falta_de_configuracion_conserva_modo_offline(error):
    proveedor = None if error is None else ProveedorSimulado(error=error)

    resultado = tarea_ia(
        ContextoAccion(
            parametros={"texto": "preparar presentación"},
            proveedor_ia=proveedor,
        )
    )

    assert resultado.codigo == 0
    assert "configur" in resultado.salida.casefold() or resultado.salida == MENSAJE_OFFLINE_IA


def test_problema_de_conexion_no_se_confunde_con_fecha_invalida():
    proveedor = ProveedorSimulado(error=IAnoDisponible("sin conexión"))

    resultado = tarea_ia(
        ContextoAccion(
            parametros={"texto": "preparar presentación"},
            proveedor_ia=proveedor,
        )
    )

    assert resultado.codigo == 0
    assert "conexión" in resultado.salida.casefold() or resultado.salida == MENSAJE_OFFLINE_IA
    assert "fecha" not in resultado.error.casefold()


def test_timeout_se_identifica_sin_exponer_detalles_tecnicos():
    proveedor = ProveedorSimulado(error=TimeoutProveedorIA("detalle interno"))

    resultado = tarea_ia(
        ContextoAccion(
            parametros={"texto": "preparar presentación"},
            proveedor_ia=proveedor,
        )
    )

    assert resultado.codigo != 0
    assert "tiempo" in resultado.error.casefold() or "espera" in resultado.error.casefold()
    assert "detalle interno" not in resultado.error


def test_respuesta_de_proveedor_invalida_no_se_presenta_como_offline():
    resultado = ejecutar("no es una propuesta estructurada")

    assert resultado.codigo != 0
    assert "respuesta" in resultado.error.casefold()
    assert "offline" not in resultado.error.casefold()


@pytest.mark.parametrize(
    "prioridad, esperada",
    [("aLtA", "Alta"), ("MEDIA", "Media"), ("baja", "Baja")],
)
def test_validar_tarea_ia_es_determinista_y_normaliza_prioridades(prioridad, esperada):
    respuesta = respuesta_tarea(prioridad=prioridad)

    primero = internas.validar_tarea_ia(respuesta)
    segundo = internas.validar_tarea_ia(respuesta)

    assert primero == segundo
    assert primero.codigo == 0
    assert f"Prioridad: {esperada}" in primero.salida
    assert respuesta == respuesta_tarea(prioridad=prioridad)


@pytest.mark.parametrize("respuesta", ["", "   \n ", ":\n:\n:"])
def test_validar_tarea_ia_rechaza_respuestas_vacias(respuesta):
    resultado = internas.validar_tarea_ia(respuesta)

    assert resultado.codigo == 1
    assert "respuesta" in resultado.error.casefold()
    assert "offline" not in resultado.error.casefold()


def test_validar_tarea_ia_ignora_campos_desconocidos_sin_inventar():
    respuesta = (
        "Título: Preparar presentación\n"
        "Prioridad: Media\n"
        "Fecha sugerida: Sin fecha\n"
        "Notas: inventar algo"
    )

    resultado = internas.validar_tarea_ia(respuesta)

    assert resultado.codigo == 0
    assert "inventar" not in resultado.salida
    assert resultado.salida.endswith("Fecha sugerida: Sin fecha")


def test_autenticacion_no_se_presenta_como_error_de_conexion():
    proveedor = ProveedorSimulado(error=AutenticacionProveedorIA("clave inválida"))

    resultado = tarea_ia(
        ContextoAccion(
            parametros={"texto": "preparar presentación"},
            proveedor_ia=proveedor,
        )
    )

    assert resultado.codigo == 1
    assert "clave" in resultado.error.casefold()
    assert "conexión" not in resultado.error.casefold()
    assert "offline" not in resultado.error.casefold()


def test_timeout_no_se_presenta_como_error_de_conexion():
    proveedor = ProveedorSimulado(error=TimeoutProveedorIA("detalle interno"))

    resultado = tarea_ia(
        ContextoAccion(
            parametros={"texto": "preparar presentación"},
            proveedor_ia=proveedor,
        )
    )

    assert resultado.codigo == 1
    assert "tiempo" in resultado.error.casefold()
    assert "conexión" not in resultado.error.casefold()
    assert "detalle interno" not in resultado.error


@pytest.mark.parametrize(
    "error",
    [ErrorProveedorIA("detalle técnico"), RespuestaIAInvalida("otro detalle")],
)
def test_fallo_de_respuesta_del_proveedor_no_se_presenta_como_offline(error):
    proveedor = ProveedorSimulado(error=error)

    resultado = tarea_ia(
        ContextoAccion(
            parametros={"texto": "preparar presentación"},
            proveedor_ia=proveedor,
        )
    )

    assert resultado.codigo == 1
    assert "respuesta" in resultado.error.casefold()
    assert "offline" not in resultado.error.casefold()
    assert "detalle" not in resultado.error.casefold()
