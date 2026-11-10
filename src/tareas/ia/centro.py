"""Proveedor compatible con la API del centro."""

import json
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from tareas.ia.errores import ErrorProveedorIA, IAnoDisponible


class ProveedorCentro:
    """Cliente para el servicio Qwen del centro."""

    nombre = "centro"
    endpoint = "https://10.100.22.107/llmapi/v1"
    modelo = "Qwen38-DualSpark"

    def __init__(self, clave: str, timeout: float = 20.0) -> None:
        if not clave:
            raise ValueError("Se requiere una clave para crear el proveedor.")
        self._clave = clave
        self._timeout = timeout

    def disponible(self) -> bool:
        """Comprueba conexión TCP y confianza TLS sin mostrar detalles sensibles."""
        url = urlsplit(self.endpoint)
        try:
            with socket.create_connection((url.hostname, url.port or 443), timeout=self._timeout) as conexion:
                contexto = ssl.create_default_context()
                with contexto.wrap_socket(conexion, server_hostname=url.hostname):
                    return True
        except (OSError, ssl.SSLError, TimeoutError):
            return False

    def proponer_acciones(self, peticion: str, contexto: str) -> list[dict]:
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
            with urlopen(solicitud, timeout=self._timeout) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise IAnoDisponible("No se pudo conectar con la IA del centro.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ErrorProveedorIA("La IA del centro devolvió una respuesta inválida.") from exc

        try:
            contenido = datos["choices"][0]["message"]["content"]
            propuestas = json.loads(contenido)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ErrorProveedorIA("La IA del centro devolvió una respuesta inválida.") from exc
        if not isinstance(propuestas, list) or not all(isinstance(item, dict) for item in propuestas):
            raise ErrorProveedorIA("La IA del centro devolvió una respuesta inválida.")
        if not propuestas:
            raise ErrorProveedorIA("La IA del centro devolvió una respuesta vacía.")
        return propuestas
