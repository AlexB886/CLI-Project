
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


def test_contexto_tls_usa_tareas_ca_bundle_configurada(monkeypatch, tmp_path):
    certificado = tmp_path / "centro.crt"
    certificado.write_text("certificado de prueba", encoding="utf-8")
    monkeypatch.setenv("TAREAS_CA_BUNDLE", str(certificado))

    contexto = MagicMock()
    with patch(
        "tareas.ia.centro.ssl.create_default_context",
        return_value=contexto,
    ) as crear_contexto:
        assert crear_proveedor()._crear_contexto_tls() is contexto

    crear_contexto.assert_called_once_with(cafile=str(certificado))


def test_contexto_tls_usa_tareas_ca_bundle_del_fichero_env_local(monkeypatch, tmp_path):
    """Sin variable de entorno, la CA puede venir del .env local (con ~ expandida)."""
    certificado = tmp_path / "centro.crt"
    certificado.write_text("certificado de prueba", encoding="utf-8")
    (tmp_path / ".env").write_text(
        f'TAREAS_API_KEY=clave-sintetica\nTAREAS_CA_BUNDLE="{certificado}"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("TAREAS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("TAREAS_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    from tareas.ia.configuracion import obtener_variable

    assert obtener_variable("TAREAS_CA_BUNDLE") == str(tmp_path / certificado.name)

    contexto = MagicMock()
    with patch(
        "tareas.ia.centro.ssl.create_default_context",
        return_value=contexto,
    ) as crear_contexto:
        from tareas.ia.fabrica import crear_proveedor

        assert crear_proveedor()._crear_contexto_tls() is contexto

    crear_contexto.assert_called_once_with(cafile=str(tmp_path / certificado.name))


def test_contexto_tls_mantiene_almacen_sistema_sin_ca(monkeypatch, tmp_path):
    monkeypatch.delenv("TAREAS_CA_BUNDLE", raising=False)
    monkeypatch.chdir(tmp_path)  # sin .env local que aporte la CA
    contexto = MagicMock()

    with patch(
        "tareas.ia.centro.ssl.create_default_context",
        return_value=contexto,
    ) as crear_contexto:
        assert crear_proveedor()._crear_contexto_tls() is contexto

    crear_contexto.assert_called_once_with()


def test_contexto_tls_se_reutiliza_en_la_instancia(monkeypatch, tmp_path):
    certificado = tmp_path / "centro.crt"
    certificado.write_text("certificado de prueba", encoding="utf-8")
    monkeypatch.setenv("TAREAS_CA_BUNDLE", str(certificado))
    contexto = MagicMock()
    proveedor = crear_proveedor()

    with patch(
        "tareas.ia.centro.ssl.create_default_context",
        return_value=contexto,
    ) as crear_contexto:
        primero = proveedor._crear_contexto_tls()
        segundo = proveedor._crear_contexto_tls()

    assert primero is segundo is contexto
    crear_contexto.assert_called_once_with(cafile=str(certificado))
