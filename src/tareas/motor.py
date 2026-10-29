"""Motor que carga las acciones y las ejecuta."""

from pathlib import Path

from tareas.acciones.registro import RegistroAcciones, registro as registro_global
from tareas.configuracion import CargadorAccionesJSON
from tareas.errores import AccionNoValida, ConfigError
from tareas.modelos import Accion, ContextoAccion, ResultadoAccion
from tareas.parametros import resolver_parametros
from tareas.puertos import CargadorAcciones, Confirmador, EjecutorAccion


class Motor:
    """Orquesta carga, parámetros, dry-run y confirmación."""

    def __init__(
        self,
        ruta: Path,
        cargador: CargadorAcciones | None = None,
        registro: RegistroAcciones | None = None,
        confirmador: Confirmador | None = None,
    ) -> None:
        self._ruta = ruta.expanduser()
        self._cargador = cargador or CargadorAccionesJSON()
        self._registro = registro or registro_global
        self._confirmador = confirmador or (lambda accion: False)
        self._acciones: dict[str, Accion] | None = None
        self._ejecutores: dict[str, EjecutorAccion] = {}

    @property
    def ruta(self) -> Path:
        """Fichero de acciones que usa este motor."""
        return self._ruta

    def cargar(self) -> None:
        """Carga y valida las acciones una sola vez."""
        if self._acciones is not None:
            return

        acciones = self._cargador.cargar(self._ruta)
        acciones_por_nombre: dict[str, Accion] = {}
        ejecutores: dict[str, EjecutorAccion] = {}
        for accion in acciones:
            if accion.nombre in acciones_por_nombre:
                raise ConfigError(f"El nombre de acción «{accion.nombre}» está duplicado.")
            ejecutores[accion.nombre] = self._registro.construir(accion)
            acciones_por_nombre[accion.nombre] = accion

        self._acciones = acciones_por_nombre
        self._ejecutores = ejecutores

    def acciones(self) -> list[Accion]:
        """Devuelve las acciones declaradas, en orden."""
        self.cargar()
        return list(self._acciones.values())

    def obtener(self, nombre: str) -> Accion:
        """Busca una acción por nombre."""
        self.cargar()
        try:
            return self._acciones[nombre]
        except KeyError as exc:
            disponibles = ", ".join(sorted(self._acciones)) or "ninguna"
            raise AccionNoValida(
                f"La acción «{nombre}» no existe. Disponibles: {disponibles}."
            ) from exc

    def ejecutar(
        self,
        nombre: str,
        posicionales: list[str] | None = None,
        parametros: list[str] | None = None,
        simular: bool = False,
    ) -> ResultadoAccion:
        """Ejecuta una acción aplicando dry-run y confirmación."""
        self.cargar()
        accion = self.obtener(nombre)
        valores = resolver_parametros(accion, posicionales, parametros)

        if accion.destructiva and not simular:
            if not self._confirmador(accion):
                return ResultadoAccion(codigo=1, error="Operación cancelada.")

        contexto = ContextoAccion(parametros=valores, simular=simular)
        ejecutor = self._ejecutores[nombre]
        if simular:
            return ejecutor.previsualizar(contexto)
        return ejecutor.ejecutar(contexto)
