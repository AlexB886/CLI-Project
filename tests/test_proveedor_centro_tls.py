
"""Pruebas TLS del proveedor del centro."""

import socket
import ssl
from unittest.mock import MagicMock, patch

import pytest

from tareas.ia.centro import ProveedorCentro


def crear_proveedor():
    return ProveedorCentro("clave-de-prueba", timeout=5)


def test_disponible_devuelve_true_si_tls_funciona():
    proveedor = crear_proveedor()

    conexion = MagicMock()
    conexion.__enter__.return_value = conexion

    contexto = MagicMock()
    contexto.wrap_socket.return_value.__enter__.return_value = None

    with (
        patch(
            "tareas.ia.centro.socket.create_connection",
            return_value=conexion,
        ),
        patch(
            "tareas.ia.centro.ssl.create_default_context",
            return_value=contexto,
        ),
    ):
        assert proveedor.disponible() is True

    contexto.wrap_socket.assert_called_once_with(
        conexion,
        server_hostname="10.100.22.107",
    )


@pytest.mark.parametrize(
    "error",
    [
        OSError("Error de conexión"),
        ssl.SSLError("Error TLS"),
        TimeoutError("Tiempo agotado"),
    ],
)
def test_disponible_devuelve_false_si_falla_la_conexion(error):
    proveedor = crear_proveedor()

    with patch(
        "tareas.ia.centro.socket.create_connection",
        side_effect=error,
    ):
        assert proveedor.disponible() is False


def test_disponible_devuelve_false_si_falla_el_certificado():
    proveedor = crear_proveedor()

    conexion = MagicMock()
    conexion.__enter__.return_value = conexion

    contexto = MagicMock()
    contexto.wrap_socket.side_effect = ssl.SSLError(
        "Certificado no válido"
    )

    with (
        patch(
            "tareas.ia.centro.socket.create_connection",
            return_value=conexion,
        ),
        patch(
            "tareas.ia.centro.ssl.create_default_context",
            return_value=contexto,
        ),
    ):
        assert proveedor.disponible() is False
