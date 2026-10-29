"""Resolución y conversión de los parámetros de una acción."""

from pathlib import Path
from typing import Any

from tareas.errores import AccionNoValida
from tareas.modelos import Accion

TIPOS_VALIDOS = {"texto", "entero", "ruta", "booleano"}


def convertir(valor: Any, tipo: str, nombre: str) -> Any:
    """Convierte un valor de CLI o JSON al tipo declarado."""
    if valor is None:
        return None
    if tipo == "texto":
        return str(valor)
    if tipo == "entero":
        if isinstance(valor, bool):
            raise ValueError(f"El parámetro «{nombre}» debe ser un número entero.")
        try:
            return int(valor)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"El parámetro «{nombre}» debe ser un número entero.") from exc
    if tipo == "ruta":
        return Path(str(valor)).expanduser()
    if tipo == "booleano":
        if isinstance(valor, bool):
            return valor
        texto = str(valor).strip().lower()
        if texto in {"1", "true", "si", "sí", "yes", "y"}:
            return True
        if texto in {"0", "false", "no", "n"}:
            return False
        raise ValueError(f"El parámetro «{nombre}» debe ser verdadero o falso.")
    raise ValueError(f"El tipo «{tipo}» del parámetro «{nombre}» no es válido.")


def resolver_parametros(
    accion: Accion,
    posicionales: list[str] | None = None,
    pares: list[str] | None = None,
) -> dict[str, Any]:
    """Mezcla posicionales, CLAVE=VALOR y valores por defecto."""
    valores: dict[str, Any] = {}
    parametros = list(accion.parametros)
    posicionales = posicionales or []
    pares = pares or []

    if len(posicionales) > len(parametros):
        raise AccionNoValida(
            f"La acción «{accion.nombre}» admite {len(parametros)} argumento(s) "
            f"posicional(es) y se han recibido {len(posicionales)}."
        )

    for parametro, valor in zip(parametros, posicionales):
        valores[parametro.nombre] = valor

    for par in pares:
        if "=" not in par:
            raise AccionNoValida(
                f"Parámetro inválido «{par}»: usa el formato CLAVE=VALOR."
            )
        clave, valor = par.split("=", 1)
        clave = clave.strip()
        if not clave:
            raise AccionNoValida("El nombre del parámetro no puede estar vacío.")
        parametro = next((p for p in parametros if p.nombre == clave), None)
        if parametro is None:
            raise AccionNoValida(
                f"La acción «{accion.nombre}» no tiene el parámetro «{clave}»."
            )
        if clave in valores:
            raise AccionNoValida(f"El parámetro «{clave}» se ha indicado dos veces.")
        valores[clave] = valor

    resultado: dict[str, Any] = {}
    for parametro in parametros:
        if parametro.nombre in valores:
            try:
                resultado[parametro.nombre] = convertir(
                    valores[parametro.nombre], parametro.tipo, parametro.nombre
                )
            except ValueError as exc:
                raise AccionNoValida(str(exc)) from exc
        elif parametro.por_defecto is not None:
            try:
                resultado[parametro.nombre] = convertir(
                    parametro.por_defecto, parametro.tipo, parametro.nombre
                )
            except ValueError as exc:
                raise AccionNoValida(str(exc)) from exc
        elif parametro.requerido:
            raise AccionNoValida(
                f"Falta el parámetro obligatorio «{parametro.nombre}» "
                f"para la acción «{accion.nombre}»."
            )
        else:
            resultado[parametro.nombre] = None

    return resultado
