"""Cargador y validador del fichero acciones.json."""

import json
import re
from pathlib import Path
from typing import Any

from tareas.errores import ConfigError
from tareas.modelos import Accion, Parametro, TipoEjecucion
from tareas.parametros import TIPOS_VALIDOS, convertir

NOMBRE_ACCION = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
NOMBRE_PARAMETRO = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
CLAVES_ACCION = {
    "nombre",
    "descripcion",
    "tipo",
    "ejecutar",
    "destructiva",
    "parametros",
}
CLAVES_PARAMETRO = {"tipo", "requerido", "por_defecto", "ayuda"}
NOMBRES_RESERVADOS = {"version", "acciones", "ejecutar"}


class CargadorAccionesJSON:
    """Lee acciones.json y comprueba todo su esquema."""

    def cargar(self, ruta: Path) -> list[Accion]:
        """Devuelve las acciones validadas o lanza ConfigError."""
        ruta = ruta.expanduser()
        if not ruta.exists():
            raise ConfigError(f"No existe el fichero de acciones «{ruta}».")
        if not ruta.is_file():
            raise ConfigError(f"«{ruta}» no es un fichero.")

        try:
            texto = ruta.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ConfigError(f"No se pudo leer «{ruta}»: {exc}") from exc

        try:
            datos = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"JSON inválido en «{ruta}», línea {exc.lineno}, "
                f"columna {exc.colno}: {exc.msg}."
            ) from exc

        if not isinstance(datos, dict):
            raise ConfigError("La raíz de acciones.json debe ser un objeto JSON.")
        version = datos.get("version")
        if isinstance(version, bool) or version != 1:
            raise ConfigError("La versión de acciones.json debe ser 1.")

        lista = datos.get("acciones")
        if not isinstance(lista, list):
            raise ConfigError("«acciones» debe ser una lista.")

        acciones: list[Accion] = []
        nombres: set[str] = set()
        for indice, elemento in enumerate(lista, start=1):
            accion = self._leer_accion(elemento, indice, nombres)
            acciones.append(accion)
        return acciones

    def _leer_accion(
        self,
        elemento: Any,
        indice: int,
        nombres: set[str],
    ) -> Accion:
        if not isinstance(elemento, dict):
            raise ConfigError(f"La acción #{indice} debe ser un objeto JSON.")

        desconocidas = set(elemento) - CLAVES_ACCION
        if desconocidas:
            raise ConfigError(
                f"La acción #{indice} tiene claves desconocidas: "
                f"{', '.join(sorted(desconocidas))}."
            )

        for clave in ("nombre", "descripcion", "tipo", "ejecutar", "destructiva"):
            if clave not in elemento:
                raise ConfigError(
                    f"La acción #{indice} no tiene la clave obligatoria «{clave}»."
                )

        nombre = elemento["nombre"]
        if not isinstance(nombre, str) or not NOMBRE_ACCION.fullmatch(nombre):
            raise ConfigError(
                f"El nombre de la acción #{indice} no es válido: usa minúsculas, "
                "números, guiones o guiones bajos."
            )
        if nombre in NOMBRES_RESERVADOS:
            raise ConfigError(
                f"El nombre de acción «{nombre}» está reservado por el CLI."
            )
        if nombre in nombres:
            raise ConfigError(f"El nombre de acción «{nombre}» está duplicado.")
        nombres.add(nombre)

        descripcion = elemento["descripcion"]
        if not isinstance(descripcion, str) or not descripcion.strip():
            raise ConfigError(
                f"La acción «{nombre}» debe tener una descripción no vacía."
            )

        tipo_valor = elemento["tipo"]
        if not isinstance(tipo_valor, str):
            raise ConfigError(
                f"La acción «{nombre}» tiene un tipo no válido: "
                "usa «funcion» o «comando»."
            )
        try:
            tipo = TipoEjecucion(tipo_valor)
        except ValueError as exc:
            raise ConfigError(
                f"La acción «{nombre}» tiene un tipo no válido: "
                "usa «funcion» o «comando»."
            ) from exc

        ejecutar = self._leer_ejecucion(nombre, tipo, elemento["ejecutar"])

        destructiva = elemento["destructiva"]
        if not isinstance(destructiva, bool):
            raise ConfigError(
                f"«destructiva» de la acción «{nombre}» debe ser true o false."
            )

        parametros = self._leer_parametros(
            nombre, elemento.get("parametros", {})
        )
        return Accion(
            nombre=nombre,
            descripcion=descripcion.strip(),
            tipo=tipo,
            ejecutar=ejecutar,
            destructiva=destructiva,
            parametros=parametros,
        )

    def _leer_ejecucion(
        self,
        nombre: str,
        tipo: TipoEjecucion,
        valor: Any,
    ) -> str | tuple[str, ...]:
        if tipo is TipoEjecucion.FUNCION:
            if not isinstance(valor, str) or not valor.strip():
                raise ConfigError(
                    f"La acción «{nombre}» debe indicar una función registrada "
                    "como texto."
                )
            return valor.strip()

        if not isinstance(valor, list) or not valor:
            raise ConfigError(
                f"La acción «{nombre}» debe indicar un comando como lista no vacía."
            )
        if any(not isinstance(argumento, str) or not argumento for argumento in valor):
            raise ConfigError(
                f"El comando de «{nombre}» debe contener solo textos no vacíos."
            )
        return tuple(valor)

    def _leer_parametros(
        self,
        nombre_accion: str,
        valor: Any,
    ) -> tuple[Parametro, ...]:
        if valor is None:
            return ()
        if not isinstance(valor, dict):
            raise ConfigError(
                f"«parametros» de la acción «{nombre_accion}» debe ser un objeto."
            )

        parametros: list[Parametro] = []
        for nombre, datos in valor.items():
            if not isinstance(nombre, str) or not NOMBRE_PARAMETRO.fullmatch(nombre):
                raise ConfigError(
                    f"El parámetro «{nombre}» de «{nombre_accion}» no es un "
                    "nombre válido."
                )
            if not isinstance(datos, dict):
                raise ConfigError(
                    f"El parámetro «{nombre}» de «{nombre_accion}» debe ser "
                    "un objeto."
                )

            desconocidas = set(datos) - CLAVES_PARAMETRO
            if desconocidas:
                raise ConfigError(
                    f"El parámetro «{nombre}» de «{nombre_accion}» tiene claves "
                    f"desconocidas: {', '.join(sorted(desconocidas))}."
                )

            tipo = datos.get("tipo", "texto")
            if not isinstance(tipo, str) or tipo not in TIPOS_VALIDOS:
                raise ConfigError(
                    f"El parámetro «{nombre}» de «{nombre_accion}» tiene un tipo "
                    f"no válido. Usa: {', '.join(sorted(TIPOS_VALIDOS))}."
                )

            requerido = datos.get("requerido", False)
            if not isinstance(requerido, bool):
                raise ConfigError(
                    f"«requerido» del parámetro «{nombre}» de «{nombre_accion}» "
                    "debe ser true o false."
                )

            ayuda = datos.get("ayuda", "")
            if not isinstance(ayuda, str):
                raise ConfigError(
                    f"«ayuda» del parámetro «{nombre}» de «{nombre_accion}» "
                    "debe ser texto."
                )

            tiene_defecto = "por_defecto" in datos
            por_defecto = datos.get("por_defecto")
            if requerido and tiene_defecto:
                raise ConfigError(
                    f"El parámetro «{nombre}» de «{nombre_accion}» no puede ser "
                    "requerido y tener valor por defecto a la vez."
                )
            if por_defecto is not None:
                try:
                    convertir(por_defecto, tipo, nombre)
                except ValueError as exc:
                    raise ConfigError(
                        f"Valor por defecto inválido en «{nombre}» de "
                        f"«{nombre_accion}»: {exc}"
                    ) from exc

            parametros.append(
                Parametro(
                    nombre=nombre,
                    tipo=tipo,
                    requerido=requerido,
                    por_defecto=por_defecto,
                    ayuda=ayuda,
                )
            )
        return tuple(parametros)
