"""Proveedor compatible con la API del centro."""

import json
import os
import re
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from tareas.ia.configuracion import obtener_variable
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


def _bytes(valor: bytes | str) -> bytes:
    if isinstance(valor, bytes):
        return valor
    return str(valor).encode("utf-8", errors="replace")


def _sanear(etapa: str) -> str:
    """Quita de la etapa cualquier texto que se parezca a una credencial."""
    texto = re.sub(
        r"(?i)(bearer\s+|api[_-]?key[\"']?\s*[:=]\s*[\"']?|authorization[\"']?\s*[:=]\s*[\"']?)"
        r"[^\s,;\"'}]+",
        r"\1[oculto]",
        etapa,
    )
    texto = re.sub(r"\b(sk|key|token)[-_][A-Za-z0-9]{6,}\b", "[oculto]", texto)
    texto = re.sub(r"[A-Za-z0-9+/=]{40,}", "[fragmento-omitido]", texto)
    return texto


def _resumen_respuesta(cruda: bytes, maximo: int = 300) -> str:
    """Extracto legible de la respuesta cruda, apto para depurar fallos.

    Se limita a `maximo` caracteres, se sanean posibles credenciales y solo
    sirve para diagnosticar forma de respuestas, nunca para volcar contenido.
    """
    texto = cruda.decode("utf-8", errors="replace")
    texto = " ".join(texto.split())
    if len(texto) > maximo:
        texto = texto[:maximo] + "…"
    return _sanear(texto)


class ProveedorCentro:
    """Cliente para el servicio Qwen del centro."""

    nombre = "centro"
    endpoint = "https://10.100.22.107/llmapi/v1"
    modelo = "Qwen38-DualSpark-low"

    # Secretos conocidos que nunca deben aparecer en un mensaje de error.
    _TOKENS_SENSIBLES: tuple[str, ...] = ()

    def __init__(self, clave: str, timeout: float = 120.0) -> None:
        if not clave:
            raise ValueError("Se requiere una clave para crear el proveedor.")

        self._clave = clave
        self._timeout = timeout
        self._contexto_tls: ssl.SSLContext | None = None
        self._TOKENS_SENSIBLES = (clave,)

    def _crear_contexto_tls(self) -> ssl.SSLContext:
        """Crea una vez el contexto TLS y lo reutiliza en las conexiones."""
        if self._contexto_tls is not None:
            return self._contexto_tls

        certificado = obtener_variable("TAREAS_CA_BUNDLE")

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

    def _resumen(self, cruda: bytes) -> str:
        """Extracto saneado: incluye la propia clave entre los términos a ocultar."""
        resumen = _resumen_respuesta(cruda)
        for token in self._TOKENS_SENSIBLES:
            if token:
                resumen = resumen.replace(token, "[oculto]")
        return resumen

    def _solicitar(self, peticion: str, contexto: str) -> tuple[dict, bytes]:
        """Envía la petición de chat y devuelve el JSON y el cuerpo crudo."""
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
                crudo = respuesta.read()

        except (
            HTTPError,
            URLError,
            TimeoutError,
            socket.timeout,
            OSError,
        ) as exc:
            raise self._traducir_error(exc) from exc

        try:
            datos = json.loads(crudo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            error = ErrorProveedorIA(_MENSAJE_RESPUESTA_INVALIDA)
            error.etapa = f"respuesta no JSON ({self._resumen(crudo)})"
            raise error from exc

        return datos, crudo

    def _contenido(self, datos: dict, referencia: bytes | str = "") -> str:
        """Valida la estructura de chat y devuelve el contenido en texto.

        `referencia` es el cuerpo crudo de la respuesta, que solo se usa para
        construir el mensaje de diagnóstico cuando la estructura es inválida.
        """
        error_invalida = ErrorProveedorIA(_MENSAJE_RESPUESTA_INVALIDA)
        try:
            texto = datos["choices"][0]["message"]["content"]

        except (KeyError, IndexError, TypeError) as exc:
            error_invalida.etapa = (
                f"faltan los campos de la respuesta ({self._resumen(_bytes(referencia))})"
            )
            raise error_invalida from exc

        if not isinstance(texto, str):
            error_invalida.etapa = f"el contenido no es texto ({type(texto).__name__})"
            raise error_invalida

        texto = texto.strip()

        if not texto:
            error_invalida.etapa = f"respuesta vacía ({self._resumen(_bytes(referencia))})"
            raise error_invalida

        return texto

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
        datos, crudo = self._solicitar(peticion, contexto)
        contenido = self._contenido(datos, crudo)

        try:
            propuestas = json.loads(contenido)

        except json.JSONDecodeError as exc:
            error = ErrorProveedorIA(_MENSAJE_RESPUESTA_INVALIDA)
            error.etapa = f"propuestas no JSON ({self._resumen(contenido.encode('utf-8', 'replace'))})"
            raise error from exc

        if not isinstance(propuestas, list) or not all(
            isinstance(item, dict) for item in propuestas
        ):
            error = ErrorProveedorIA(_MENSAJE_RESPUESTA_INVALIDA)
            error.etapa = "propuestas fuera de formato"
            raise error

        if not propuestas:
            raise ErrorProveedorIA(
                "La IA del centro devolvió una respuesta vacía."
            )

        return propuestas

    def generar_texto(self, peticion: str, contexto: str) -> str:
        """Genera texto libre y valida la respuesta."""
        datos, crudo = self._solicitar(peticion, contexto)
        return self._contenido(datos, crudo)
