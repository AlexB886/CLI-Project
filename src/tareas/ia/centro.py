
"""Proveedor compatible con la API del centro."""

import json
import os
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from tareas.ia.errores import (
    AutenticacionProveedorIA,
    ErrorProveedorIA,
    IAnoDisponible,
    TimeoutProveedorIA,
)

_MENSAJE_AUTENTICACION = "La clave no es válida o no tiene acceso a la IA del centro."
_MENSAJE_NO_DISPONIBLE = "No se pudo conectar con la IA del centro."
_MENSAJE_TIMEOUT = "La IA del centro agotó el tiempo de espera."
_MENSAJE_RESPUESTA_INVALIDA = "La IA del centro devolvió una respuesta inválida."


class ProveedorCentro:
    """Cliente para el servicio Qwen del centro."""

    nombre = "centro"
    endpoint = "https://10.100.22.107/llmapi/v1"
    modelo = "Qwen38-DualSpark-low"

    def __init__(self, clave: str, timeout: float = 120.0) -> None:
        if not clave:
            raise ValueError("Se requiere una clave para crear el proveedor.")

        self._clave = clave
        self._timeout = timeout
        self._contexto_tls: ssl.SSLContext | None = None

    def _crear_contexto_tls(self) -> ssl.SSLContext:
        """Crea una vez el contexto TLS y lo reutiliza en las conexiones."""
        if self._contexto_tls is not None:
            return self._contexto_tls

        certificado = os.environ.get("TAREAS_CA_BUNDLE")

        if certificado:
            self._contexto_tls = ssl.create_default_context(cafile=certificado)
        else:
            self._contexto_tls = ssl.create_default_context()

        return self._contexto_tls

    @staticmethod
    def _traducir_error(exc: Exception) -> ErrorProveedorIA:
        """Convierte fallos de red y de respuesta en errores propios del proveedor."""
        if isinstance(exc, HTTPError) and exc.code in (401, 403):
            return AutenticacionProveedorIA(_MENSAJE_AUTENTICACION)

        motivo = getattr(exc, "reason", None)
        if isinstance(exc, (TimeoutError, socket.timeout)) or isinstance(
            motivo, (TimeoutError, socket.timeout)
        ):
            return TimeoutProveedorIA(_MENSAJE_TIMEOUT)

        if isinstance(exc, (HTTPError, URLError, OSError)):
            return IAnoDisponible(_MENSAJE_NO_DISPONIBLE)

        return ErrorProveedorIA(_MENSAJE_RESPUESTA_INVALIDA)

    def disponible(self) -> bool:
        """Comprueba conexión TCP y confianza TLS."""
        url = urlsplit(self.endpoint)

        try:
            with socket.create_connection(
                (url.hostname, url.port or 443),
                timeout=self._timeout,
            ) as conexion:
                contexto = self._crear_contexto_tls()

                with contexto.wrap_socket(
                    conexion,
                    server_hostname=url.hostname,
                ):
                    return True

        except (OSError, ssl.SSLError, TimeoutError):
            return False

    def proponer_acciones(
        self,
        peticion: str,
        contexto: str,
    ) -> list[dict]:
        """Envía la petición y valida que la respuesta sea una lista JSON."""
        cuerpo = json.dumps(
            {
                "model": self.modelo,
                "messages": [
                    {"role": "system", "content": contexto},
                    {"role": "user", "content": peticion},
                ],
            }
        ).encode("utf-8")

        solicitud = Request(
            f"{self.endpoint}/chat/completions",
            data=cuerpo,
            headers={
                "Authorization": f"Bearer {self._clave}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                solicitud,
                timeout=self._timeout,
                context=self._crear_contexto_tls(),
            ) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))

        except (
            HTTPError,
            URLError,
            TimeoutError,
            socket.timeout,
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise self._traducir_error(exc) from exc

        try:
            contenido = datos["choices"][0]["message"]["content"]
            propuestas = json.loads(contenido)

        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ErrorProveedorIA(_MENSAJE_RESPUESTA_INVALIDA) from exc

        if not isinstance(propuestas, list) or not all(
            isinstance(item, dict) for item in propuestas
        ):
            raise ErrorProveedorIA(_MENSAJE_RESPUESTA_INVALIDA)

        if not propuestas:
            raise ErrorProveedorIA(
                "La IA del centro devolvió una respuesta vacía."
            )

        return propuestas

    def generar_texto(self, peticion: str, contexto: str) -> str:
        """Genera texto libre y valida la respuesta."""
        cuerpo = json.dumps(
            {
                "model": self.modelo,
                "messages": [
                    {"role": "system", "content": contexto},
                    {"role": "user", "content": peticion},
                ],
            }
        ).encode("utf-8")

        solicitud = Request(
            f"{self.endpoint}/chat/completions",
            data=cuerpo,
            headers={
                "Authorization": f"Bearer {self._clave}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                solicitud,
                timeout=self._timeout,
                context=self._crear_contexto_tls(),
            ) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))

        except (
            HTTPError,
            URLError,
            TimeoutError,
            socket.timeout,
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise self._traducir_error(exc) from exc

        try:
            texto = datos["choices"][0]["message"]["content"]

        except (KeyError, IndexError, TypeError) as exc:
            raise ErrorProveedorIA(_MENSAJE_RESPUESTA_INVALIDA) from exc

        if not isinstance(texto, str):
            raise ErrorProveedorIA(_MENSAJE_RESPUESTA_INVALIDA)

        texto = texto.strip()

        if not texto:
            raise ErrorProveedorIA(
                "La IA del centro devolvió una respuesta vacía."
            )

        return texto
