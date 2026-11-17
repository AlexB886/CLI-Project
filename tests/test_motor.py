"""Pruebas de carga, registro, ejecución y confirmación del motor."""

import pytest

from tareas.acciones.registro import RegistroAcciones
from tareas.errores import AccionNoValida, ConfigError
from tareas.modelos import Accion, ContextoAccion, ResultadoAccion, TipoEjecucion
from tareas.motor import Motor


def crear_accion(*, destructiva=False):
    return Accion(
        nombre="demo",
        descripcion="Acción de prueba",
        tipo=TipoEjecucion.FUNCION,
        ejecutar="demo",
        destructiva=destructiva,
    )


class CargadorFalso:
    def __init__(self, acciones):
        self.acciones_configuradas = acciones
        self.llamadas = 0

    def cargar(self, ruta):
        self.llamadas += 1
        return self.acciones_configuradas


def crear_registro(llamada):
    registro = RegistroAcciones()
    registro.registrar("demo", llamada)
    return registro


def test_motor_carga_configuracion_una_sola_vez(tmp_path):
    cargador = CargadorFalso([crear_accion()])
    registro = crear_registro(lambda ctx: ResultadoAccion(salida="ok"))
    motor = Motor(tmp_path / "acciones.json", cargador=cargador, registro=registro)

    assert motor.acciones() == [crear_accion()]
    assert motor.acciones() == [crear_accion()]
    assert cargador.llamadas == 1


def test_motor_ejecuta_funcion_y_devuelve_resultado(tmp_path):
    llamadas = []
    resultado_esperado = ResultadoAccion(salida="resultado")
    registro = crear_registro(lambda ctx: llamadas.append(ctx) or resultado_esperado)
    motor = Motor(
        tmp_path / "acciones.json",
        cargador=CargadorFalso([crear_accion()]),
        registro=registro,
    )

    assert motor.ejecutar("demo") is resultado_esperado
    assert llamadas[0].parametros == {}
    assert llamadas[0].simular is False


def test_motor_rechaza_accion_no_registrada(tmp_path):
    motor = Motor(
        tmp_path / "acciones.json",
        cargador=CargadorFalso([crear_accion()]),
        registro=RegistroAcciones(),
    )

    with pytest.raises(ConfigError, match="no está registrada"):
        motor.cargar()


def test_motor_rechaza_nombres_duplicados(tmp_path):
    motor = Motor(
        tmp_path / "acciones.json",
        cargador=CargadorFalso([crear_accion(), crear_accion()]),
        registro=crear_registro(lambda ctx: ResultadoAccion()),
    )

    with pytest.raises(ConfigError, match="duplicado"):
        motor.cargar()


def test_motor_informa_accion_inexistente(tmp_path):
    motor = Motor(
        tmp_path / "acciones.json",
        cargador=CargadorFalso([crear_accion()]),
        registro=crear_registro(lambda ctx: ResultadoAccion()),
    )

    with pytest.raises(AccionNoValida, match="no existe"):
        motor.ejecutar("no-existe")


def test_motor_sugiere_nombre_parecido_sin_ocultar_las_disponibles(tmp_path):
    motor = Motor(
        tmp_path / "acciones.json",
        cargador=CargadorFalso([crear_accion()]),
        registro=crear_registro(lambda ctx: ResultadoAccion()),
    )

    with pytest.raises(AccionNoValida) as capturado:
        motor.ejecutar("demo0")

    mensaje = str(capturado.value)
    assert "no existe" in mensaje
    assert "Disponibles: demo" in mensaje
    assert "¿Querías decir" in mensaje


def test_motor_cancelacion_no_ejecuta_accion_destructiva(tmp_path):
    llamadas = []
    motor = Motor(
        tmp_path / "acciones.json",
        cargador=CargadorFalso([crear_accion(destructiva=True)]),
        registro=crear_registro(lambda ctx: llamadas.append(ctx) or ResultadoAccion()),
        confirmador=lambda accion: False,
    )

    resultado = motor.ejecutar("demo")

    assert resultado.codigo == 1
    assert resultado.error == "Operación cancelada."
    assert llamadas == []


def test_motor_simula_sin_pedir_confirmacion_y_marca_contexto(tmp_path):
    llamadas = []
    motor = Motor(
        tmp_path / "acciones.json",
        cargador=CargadorFalso([crear_accion(destructiva=True)]),
        registro=crear_registro(lambda ctx: llamadas.append(ctx) or ResultadoAccion()),
        confirmador=lambda accion: pytest.fail("No debe confirmar en simulación"),
    )

    resultado = motor.ejecutar("demo", simular=True)

    assert resultado.codigo == 0
    assert len(llamadas) == 1
    assert llamadas[0].simular is True


def test_motor_ejecuta_accion_destructiva_si_se_confirma(tmp_path):
    llamadas = []
    confirmaciones = []

    def confirmar(accion):
        confirmaciones.append(accion.nombre)
        return True

    motor = Motor(
        tmp_path / "acciones.json",
        cargador=CargadorFalso([crear_accion(destructiva=True)]),
        registro=crear_registro(lambda ctx: llamadas.append(ctx) or ResultadoAccion()),
        confirmador=confirmar,
    )

    assert motor.ejecutar("demo").codigo == 0
    assert confirmaciones == ["demo"]
    assert len(llamadas) == 1
