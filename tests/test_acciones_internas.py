"""Pruebas de las acciones internas con ficheros temporales."""

from pathlib import Path

import pytest

from tareas.acciones.internas import (
    MENSAJE_OFFLINE_IA,
    RutaFueraDeBaseError,
    borrar,
    listar,
    resumir_ia,
    tamano,
    tarea_ia,
    validar,
    ver,
)
from tareas.ia.errores import IAnoDisponible
from tareas.ia.nulo import ProveedorNulo
from tareas.modelos import ContextoAccion


class ProveedorDePrueba:
    nombre = "prueba"

    def __init__(self, respuesta=None, error=None):
        self.respuesta = respuesta
        self.error = error
        self.llamadas = []

    def disponible(self):
        return True

    def generar_texto(self, peticion, contexto):
        self.llamadas.append((peticion, contexto))
        if self.error:
            raise self.error
        return self.respuesta

    def proponer_acciones(self, peticion, contexto):
        raise NotImplementedError


def contexto(**parametros):
    return ContextoAccion(parametros=parametros)


def test_listar_muestra_elementos_de_carpeta_temporal(tmp_path):
    (tmp_path / "nota.txt").write_text("hola", encoding="utf-8")
    (tmp_path / "subcarpeta").mkdir()

    resultado = listar(contexto(carpeta=tmp_path))

    assert resultado.codigo == 0
    assert resultado.datos.titulo.startswith("Contenido de ")
    nombres = {fila[0] for fila in resultado.datos.filas}
    assert nombres == {"nota.txt", "subcarpeta"}


def test_listar_rechaza_ruta_que_no_es_carpeta(tmp_path):
    resultado = listar(contexto(carpeta=tmp_path / "ausente"))

    assert resultado.codigo == 1
    assert "no existe o no es una carpeta" in resultado.error


def test_validar_cubre_fichero_vacio_directorio_y_ausente(tmp_path):
    fichero = tmp_path / "contenido.txt"
    fichero.write_text("contenido", encoding="utf-8")
    vacio = tmp_path / "vacio.txt"
    vacio.write_text("", encoding="utf-8")

    assert validar(contexto(ruta=fichero)).codigo == 0
    assert "está vacío" in validar(contexto(ruta=vacio)).error
    assert "es una carpeta" in validar(contexto(ruta=tmp_path)).error
    assert "no existe" in validar(contexto(ruta=tmp_path / "no.txt")).error


def test_ver_devuelve_texto_y_rechaza_utf8_invalido(tmp_path):
    texto = tmp_path / "texto.txt"
    texto.write_text("línea uno\nlínea dos", encoding="utf-8")
    binario = tmp_path / "binario.txt"
    binario.write_bytes(b"\xff\xfe")

    assert ver(contexto(ruta=texto)).salida == "línea uno\nlínea dos"
    assert "no es un fichero de texto" in ver(contexto(ruta=binario)).error


def test_ver_limita_salida_a_doscientas_lineas(tmp_path):
    fichero = tmp_path / "muchas-lineas.txt"
    fichero.write_text("\n".join(str(i) for i in range(205)), encoding="utf-8")

    resultado = ver(contexto(ruta=fichero))

    assert resultado.salida.startswith("0\n1\n")
    # streaming: no carga el fichero entero, avisa de continuación y no pasa de 200
    assert "más líneas" in resultado.salida and "sed" in resultado.salida
    assert "200" not in resultado.salida


def test_tamano_suma_ficheros_y_carpetas_temporales(tmp_path):
    carpeta = tmp_path / "datos"
    subcarpeta = carpeta / "sub"
    subcarpeta.mkdir(parents=True)
    (carpeta / "uno.txt").write_bytes(b"123")
    (subcarpeta / "dos.txt").write_bytes(b"4567")

    resultado = tamano(contexto(carpeta=carpeta))

    assert resultado.codigo == 0
    assert ("Ficheros", "2") in resultado.datos.filas
    assert ("Carpetas", "1") in resultado.datos.filas
    assert ("Tamaño total", "7 B") in resultado.datos.filas


def test_borrar_simulacion_no_elimina_y_borrado_real_solo_temporal(tmp_path):
    fichero = tmp_path / "objetivo.txt"
    fichero.write_text("conservar hasta confirmar", encoding="utf-8")

    simulacion = borrar(
        ContextoAccion(
            parametros={"ruta": "objetivo.txt", "base": tmp_path},
            simular=True,
        )
    )
    assert "Se borraría" in simulacion.salida
    assert fichero.exists()

    resultado = borrar(contexto(ruta="objetivo.txt", base=tmp_path))
    assert resultado.codigo == 0
    assert not fichero.exists()


def test_borrar_rechaza_traversal_y_directorio(tmp_path):
    fuera = tmp_path.parent / f"{tmp_path.name}-fuera.txt"
    fuera.write_text("se conserva", encoding="utf-8")
    carpeta = tmp_path / "carpeta"
    carpeta.mkdir()

    try:
        with pytest.raises(RutaFueraDeBaseError):
            borrar(contexto(ruta=f"../{fuera.name}", base=tmp_path))
        assert borrar(contexto(ruta="carpeta", base=tmp_path)).codigo == 1
        assert fuera.read_text(encoding="utf-8") == "se conserva"
    finally:
        fuera.unlink()


@pytest.mark.parametrize("accion_ia", ["resumir", "tarea"])
def test_acciones_ia_en_modo_offline_no_hacen_red(tmp_path, accion_ia):
    proveedor = ProveedorNulo()
    if accion_ia == "resumir":
        fichero = tmp_path / "texto.txt"
        fichero.write_text("texto de prueba", encoding="utf-8")
        resultado = resumir_ia(
            ContextoAccion(parametros={"ruta": fichero}, proveedor_ia=proveedor)
        )
    else:
        resultado = tarea_ia(
            ContextoAccion(parametros={"texto": "preparar exposición"}, proveedor_ia=proveedor)
        )

    assert resultado.codigo == 0
    assert resultado.salida == MENSAJE_OFFLINE_IA


def test_resumir_ia_envia_contenido_y_presenta_respuesta(tmp_path):
    fichero = tmp_path / "texto.txt"
    fichero.write_text("contenido sintético", encoding="utf-8")
    proveedor = ProveedorDePrueba(respuesta="resumen válido")

    resultado = resumir_ia(
        ContextoAccion(parametros={"ruta": fichero}, proveedor_ia=proveedor)
    )

    assert resultado.salida == "resumen válido"
    assert len(proveedor.llamadas) == 1
    assert "contenido sintético" in proveedor.llamadas[0][0]


def test_tarea_ia_devuelve_propuesta_valida_del_proveedor():
    proveedor = ProveedorDePrueba(
        respuesta=(
            "Título: Preparar exposición\n"
            "Prioridad: Media\n"
            "Fecha sugerida: 2030-04-05"
        )
    )

    resultado = tarea_ia(
        ContextoAccion(
            parametros={"texto": "preparar exposición"},
            proveedor_ia=proveedor,
        )
    )

    assert "Prioridad: Media" in resultado.salida
    assert "Fecha sugerida: 2030-04-05" in resultado.salida


def test_errores_de_proveedor_ia_se_muestran_como_offline(tmp_path):
    fichero = tmp_path / "texto.txt"
    fichero.write_text("contenido", encoding="utf-8")
    proveedor = ProveedorDePrueba(error=IAnoDisponible("error simulado"))

    resultado = resumir_ia(
        ContextoAccion(parametros={"ruta": fichero}, proveedor_ia=proveedor)
    )

    assert resultado.salida == MENSAJE_OFFLINE_IA


def test_ruta_vacia_da_mensaje_explicito_en_validar_ver_y_resumir():
    """`Path('')` es '.', así que comprobar `str(ruta)` nunca detectaba la ausencia."""
    for accion in (validar, ver, resumir_ia):
        resultado = accion(contexto(ruta=""))

        assert resultado.codigo == 1
        assert resultado.error == "No se ha indicado ninguna ruta."
