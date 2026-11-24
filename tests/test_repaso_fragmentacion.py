"""Pruebas de la fragmentación y la síntesis por etapas (sin IA real)."""

from tareas.ia.errores import TimeoutProveedorIA
import pytest

from tareas.repaso.fragmentacion import (
    LONGITUD_FRAGMENTO,
    SintesisError,
    fragmentar,
    sintetizar,
)


class GrabadoraIA:
    """Proveedor simulado que guarda las peticiones y responde un maestro."""

    def __init__(self, respuesta: str) -> None:
        self.respuesta = respuesta
        self.peticiones: list[str] = []

    def generar_texto(self, peticion: str, contexto: str) -> str:
        self.peticiones.append(peticion)
        return self.respuesta


def test_texto_corto_va_directo_a_la_ia() -> None:
    ia = GrabadoraIA("# Introducción\ncontenido")
    resultado = sintetizar("texto breve", ia.generar_texto)
    assert len(ia.peticiones) == 1
    assert "texto breve" in ia.peticiones[0]
    assert resultado == "# Introducción\ncontenido"


def test_texto_largo_se_fragmenta_y_sintetiza_por_etapas() -> None:
    parrafos = ["Palabra " + "x " * 900 for _ in range(6)]
    texto = "\n\n".join(parrafos)
    fragmentos = fragmentar(texto)
    assert len(fragmentos) >= 2
    assert all(len(f) <= LONGITUD_FRAGMENTO for f in fragmentos)

    ia = GrabadoraIA("# Resumen\n- idea")
    sintetizar(texto, ia.generar_texto)
    # uno por fragmento + uno final que integra el maestro
    assert len(ia.peticiones) == len(fragmentos) + 1
    assert "Integra estas síntesis" in ia.peticiones[-1]


def test_el_maestro_no_es_una_union_copia_de_fragmentos() -> None:
    texto = "\n\n".join(["contenido " * 800 for _ in range(4)])
    ia = GrabadoraIA("# Repaso final\n- consolidado")
    maestro = sintetizar(texto, ia.generar_texto)
    assert maestro == "# Repaso final\n- consolidado"


def test_objetivo_de_estudio_viaja_en_la_peticion() -> None:
    ia = GrabadoraIA("# X\ny")
    sintetizar("hola", ia.generar_texto, objetivo="examen tipo test")
    assert "examen tipo test" in ia.peticiones[0]


def test_texto_vacio_no_llama_a_la_ia() -> None:
    ia = GrabadoraIA("# X\ny")
    try:
        sintetizar("   ", ia.generar_texto)
        raise AssertionError("debería fallar")
    except SintesisError as exc:
        assert "no contienen texto" in str(exc).lower()
    assert ia.peticiones == []


def test_timeout_de_la_ia_es_controlado() -> None:
    class IATimeout(GrabadoraIA):
        def generar_texto(self, peticion: str, contexto: str) -> str:
            raise TimeoutProveedorIA("fin")

    with pytest.raises(TimeoutProveedorIA):
        sintetizar("algo", IATimeout("").generar_texto)


def test_progresso_se_informa_para_el_usuario() -> None:
    visto: list[str] = []
    ia = GrabadoraIA("# Intro\nok")
    texto = "\n\n".join(["contenido " * 800 for _ in range(4)])
    sintetizar(texto, ia.generar_texto, informar=visto.append)
    assert any("fragmento" in m.lower() for m in visto)
    assert any("fragmento" in m.lower() and "1 de" in m for m in visto)


def test_maestro_en_texto_plano_gana_estructura() -> None:
    ia = GrabadoraIA("todo en texto plano sin encabezados")
    maestro = sintetizar("apuntes", ia.generar_texto)
    assert maestro.startswith("# Resumen por apartados")
