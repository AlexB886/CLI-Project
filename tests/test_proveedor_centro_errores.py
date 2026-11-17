"""Pruebas de clasificación de fallos HTTP y de transporte del proveedor."""

import json
import socket
import ssl
from urllib.error import HTTPError, URLError
from unittest.mock import MagicMock, patch

import pytest

from tareas.ia.centro import ProveedorCentro
from tareas.ia.errores import ErrorProveedorIA, IAnoDisponible, TimeoutProveedorIA


def crear_proveedor():
    proveedor = ProveedorCentro("clave-sintetica-no-real", timeout=1)
    proveedor._contexto_tls = MagicMock(spec=ssl.SSLContext)
    return proveedor


def respuesta_http(contenido):
    respuesta = MagicMock()
    respuesta.__enter__.return_value = respuesta
    respuesta.read.return_value = json.dumps(
        {"choices": [{"message": {"content": contenido}}]}
    ).encode("utf-8")
    return respuesta


@pytest.mark.parametrize("estado", [401, 403])
def test_http_sin_autorizacion_se_clasifica_como_autenticacion(estado):
    proveedor = crear_proveedor()
    error_http = HTTPError(proveedor.endpoint, estado, "Unauthorized", {}, None)

    with patch("tareas.ia.centro.urlopen", side_effect=error_http):
        with pytest.raises(ErrorProveedorIA) as capturado:
            proveedor.generar_texto("hola", "contexto")

    assert type(capturado.value).__name__ == "AutenticacionProveedorIA"
    assert "clave-sintetica-no-real" not in str(capturado.value)


def test_timeout_del_transporte_se_clasifica_como_timeout():
    proveedor = crear_proveedor()

    with patch("tareas.ia.centro.urlopen", side_effect=socket.timeout()):
        with pytest.raises(TimeoutProveedorIA):
            proveedor.generar_texto("hola", "contexto")


def test_timeout_envuelto_en_urlerror_se_clasifica_como_timeout():
    proveedor = crear_proveedor()

    with patch(
        "tareas.ia.centro.urlopen",
        side_effect=URLError(socket.timeout("interno")),
    ):
        with pytest.raises(TimeoutProveedorIA):
            proveedor.generar_texto("hola", "contexto")


def test_error_de_transporte_se_clasifica_como_no_disponible():
    proveedor = crear_proveedor()

    with patch(
        "tareas.ia.centro.urlopen",
        side_effect=URLError("conexión rechazada"),
    ):
        with pytest.raises(IAnoDisponible):
            proveedor.generar_texto("hola", "contexto")


@pytest.mark.parametrize("contenido", [""])
def test_respuesta_vacia_se_clasifica_como_invalida(contenido):
    proveedor = crear_proveedor()

    with patch(
        "tareas.ia.centro.urlopen",
        return_value=respuesta_http(contenido),
    ):
        with pytest.raises(ErrorProveedorIA):
            proveedor.generar_texto("hola", "contexto")


def test_respuesta_valida_del_modelo_se_devuelve_sin_cambios():
    proveedor = crear_proveedor()

    with patch(
        "tareas.ia.centro.urlopen",
        return_value=respuesta_http("respuesta válida"),
    ):
        assert proveedor.generar_texto("hola", "contexto") == "respuesta válida"


def test_proponer_acciones_devuelve_la_lista_validada():
    proveedor = crear_proveedor()
    propuestas = [{"nombre": "listar"}]

    with patch(
        "tareas.ia.centro.urlopen",
        return_value=respuesta_http(json.dumps(propuestas)),
    ):
        assert proveedor.proponer_acciones("hola", "contexto") == propuestas


@pytest.mark.parametrize(
    "error, tipo_esperado",
    [
        (
            HTTPError(ProveedorCentro.endpoint, 401, "Unauthorized", {}, None),
            "AutenticacionProveedorIA",
        ),
        (URLError(socket.timeout("interno")), "TimeoutProveedorIA"),
        (URLError("conexión rechazada"), "IAnoDisponible"),
        (socket.timeout("interno"), "TimeoutProveedorIA"),
    ],
)
def test_proponer_acciones_clasifica_los_mismos_errores(error, tipo_esperado):
    proveedor = crear_proveedor()

    with patch("tareas.ia.centro.urlopen", side_effect=error):
        with pytest.raises(ErrorProveedorIA) as capturado:
            proveedor.proponer_acciones("hola", "contexto")

    assert type(capturado.value).__name__ == tipo_esperado


def test_proponer_acciones_rechaza_contenido_que_no_es_lista_json():
    proveedor = crear_proveedor()

    with patch(
        "tareas.ia.centro.urlopen",
        return_value=respuesta_http("no-json"),
    ):
        with pytest.raises(ErrorProveedorIA):
            proveedor.proponer_acciones("hola", "contexto")


@pytest.mark.parametrize("estado", [500, 503])
def test_error_http_del_servidor_no_se_confunde_con_autenticacion(estado):
    proveedor = crear_proveedor()
    error_http = HTTPError(proveedor.endpoint, estado, "Server Error", {}, None)

    with patch("tareas.ia.centro.urlopen", side_effect=error_http):
        with pytest.raises(IAnoDisponible):
            proveedor.generar_texto("hola", "contexto")


@pytest.mark.parametrize(
    "error, fragmento, detalle",
    [
        (
            HTTPError(ProveedorCentro.endpoint, 403, "Forbidden", {}, None),
            "clave",
            "Forbidden",
        ),
        (socket.timeout("detalle-timeout"), "tiempo", "detalle-timeout"),
        (URLError("detalle-red"), "conectar", "detalle-red"),
    ],
)
def test_mensajes_son_humanos_y_no_revelan_detalles(error, fragmento, detalle):
    proveedor = crear_proveedor()

    with patch("tareas.ia.centro.urlopen", side_effect=error):
        with pytest.raises(ErrorProveedorIA) as capturado:
            proveedor.generar_texto("hola", "contexto")

    mensaje = str(capturado.value)
    assert fragmento in mensaje.casefold()
    assert detalle not in mensaje
    assert "clave-sintetica-no-real" not in mensaje


def test_respuesta_json_malformada_tiene_mensaje_humano():
    proveedor = crear_proveedor()
    respuesta = MagicMock()
    respuesta.__enter__.return_value = respuesta
    respuesta.read.return_value = b"{no-json"

    with patch("tareas.ia.centro.urlopen", return_value=respuesta):
        with pytest.raises(ErrorProveedorIA) as capturado:
            proveedor.generar_texto("hola", "contexto")

    mensaje = str(capturado.value)
    assert "respuesta" in mensaje.casefold()
    assert "clave-sintetica-no-real" not in mensaje
