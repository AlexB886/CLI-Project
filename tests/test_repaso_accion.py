"""Pruebas integrales de la acción repaso-ia (IA simulada, sin Writer real)."""

import zipfile
from datetime import datetime
from pathlib import Path

import pytest

import tareas.acciones.internas as internas
from tareas.ia.errores import AutenticacionProveedorIA, IAnoDisponible, TimeoutProveedorIA
from tareas.modelos import ContextoAccion
from tareas.repaso.escritorio import EscritorioNoDisponible

MAESTRO = """# Introducción
La célula es la unidad de la vida.

## ESQUEMA
esquema: La célula :: unidad de la vida
Núcleo :: guarda el ADN

# Resumen por apartados
### Membrana
Regula el paso de sustancias.

# Conceptos clave
- Mitocondria: produce energía

# Errores y confusiones frecuentes
- Confundir membrana con pared.

# Repaso final de lo imprescindible
- La célula es la unidad de la vida.

# Preguntas para el examen
1. ¿Qué hace la membrana?
"""


class IAControlada:
    """Proveedor simulado configurable: respuesta fija o excepción."""

    nombre = "simulada"

    def __init__(self, respuesta: str = MAESTRO, error: Exception | None = None) -> None:
        self.respuesta = respuesta
        self.error = error
        self.llamadas = 0

    def disponible(self) -> bool:
        return self.error is None

    def generar_texto(self, peticion: str, contexto: str) -> str:
        self.llamadas += 1
        if self.error is not None:
            raise self.error
        return self.respuesta

    def proponer_acciones(self, peticion, contexto):  # pragma: no cover
        return []


def _ctx(tmp_path: Path, archivos: list[Path], ia, **extras) -> ContextoAccion:
    parametros = {"archivos": [str(a) for a in archivos], "base": str(tmp_path)}
    parametros.update(extras)
    return ContextoAccion(parametros=parametros, proveedor_ia=ia, simular=False)


def _con_ia(monkeypatch, tmp_path, archivos, ia, **extras):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        internas, "abrir_en_writer", lambda ruta: (_ for _ in ()).throw(EscritorioNoDisponible("no instalado"))
    )
    return internas.repaso_ia(_ctx(tmp_path, archivos, ia, **extras))


def _apuntes(tmp_path: Path, nombre: str = "tema.txt", texto: str = "La fotosíntesis ocurre en los cloroplastos.") -> Path:
    ruta = tmp_path / nombre
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def test_rutas_relativas_se_leen_desde_la_base_no_desde_el_cwd(
    monkeypatch, tmp_path
) -> None:
    """`--base` debe cambiar también la lectura, no solo la comprobación."""
    base = tmp_path / "documentos"
    base.mkdir()
    (base / "apuntes.txt").write_text(
        "La fotosíntesis ocurre en los cloroplastos.", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    ctx = ContextoAccion(
        parametros={
            "archivos": ["apuntes.txt"],
            "base": str(base),
            "abrir": False,
        },
        proveedor_ia=IAControlada(),
    )

    resultado = internas.repaso_ia(ctx)

    assert resultado.codigo == 0, resultado.error
    assert (base / "apuntes.odt").is_file()


def test_apuntes_validos_generan_un_odt_y_lo_reportan(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path)
    resultado = _con_ia(monkeypatch, tmp_path, [apuntes], IAControlada(), abrir=False)
    assert resultado.codigo == 0
    assert "tema.odt" in resultado.salida
    odt = tmp_path / "tema.odt"
    assert odt.is_file()
    with zipfile.ZipFile(odt) as paquete:
        assert "mimetype" in paquete.namelist()


def test_archivo_inexistente_no_genera_nada(monkeypatch, tmp_path) -> None:
    resultado = _con_ia(monkeypatch, tmp_path, [tmp_path / "no-existe.txt"], IAControlada(), abrir=False)
    assert resultado.codigo == 1
    assert "no existe" in resultado.error
    assert list(tmp_path.glob("*.odt")) == []


def test_texto_vacio_informa_sin_generar(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path, texto="   ")
    resultado = _con_ia(monkeypatch, tmp_path, [apuntes], IAControlada(), abrir=False)
    assert resultado.codigo == 1
    assert "no contiene texto" in resultado.error
    assert list(tmp_path.glob("*.odt")) == []


def test_documento_largo_se_sintetiza_por_partes(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path, texto=("La fotosíntesis ocurre en los cloroplastos.\n\n" * 900))
    ia = IAControlada()
    _con_ia(monkeypatch, tmp_path, [apuntes], ia, abrir=False)
    assert ia.llamadas > 1  # fragmentos + maestro, nunca un único envío


def test_error_del_proveedor_no_rompe_ni_deja_parciales(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path)
    ia = IAControlada(error=IAnoDisponible("fuera"))
    resultado = _con_ia(monkeypatch, tmp_path, [apuntes], ia, abrir=False)
    assert resultado.codigo == 1
    assert "IA del centro" in resultado.error or "fuera" in resultado.error
    assert list(tmp_path.glob("*.odt")) == []


def test_timeout_del_proveedor_es_un_error_controlado(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path)
    ia = IAControlada(error=TimeoutProveedorIA("fin"))
    resultado = _con_ia(monkeypatch, tmp_path, [apuntes], ia, abrir=False)
    assert resultado.codigo == 1
    assert "espera" in resultado.error


def test_clave_invalida_distingue_autenticacion(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path)
    ia = IAControlada(error=AutenticacionProveedorIA("401"))
    resultado = _con_ia(monkeypatch, tmp_path, [apuntes], ia, abrir=False)
    assert resultado.codigo == 1
    assert "clave" in resultado.error.lower()


def test_nombre_de_salida_repetido_no_sobrescribe(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path)
    primero = tmp_path / "tema.odt"
    primero.write_text("documento previo del usuario", encoding="utf-8")
    resultado = _con_ia(monkeypatch, tmp_path, [apuntes], IAControlada(), abrir=False)
    assert resultado.codigo == 0
    assert primero.read_text(encoding="utf-8") == "documento previo del usuario"
    assert (tmp_path / "tema_2.odt").is_file()
    assert "ya existía" in resultado.salida


def test_base_no_resoluble_es_error_humano(monkeypatch, tmp_path) -> None:
    """Un OSError al resolver la raíz (p. ej. ruta circular) no produce traceback."""
    apuntes = _apuntes(tmp_path)
    monkeypatch.chdir(tmp_path)
    original = Path.resolve

    def resolver_roto(self, *a, **k):
        if str(self).startswith(str(tmp_path)):
            raise OSError(40, "circular loop")
        return original(self, *a, **k)

    monkeypatch.setattr(Path, "resolve", resolver_roto)
    resultado = internas.repaso_ia(_ctx(tmp_path, [apuntes], IAControlada(), abrir=False))
    assert resultado.codigo == 1
    assert "raíz autorizada" in resultado.error


def test_comprobar_destino_con_permiso_denegado_es_error_humano(monkeypatch, tmp_path) -> None:
    """Un EPERM al comprobar ficheros previos (carpeta de red) no produce traceback."""
    apuntes = _apuntes(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(internas.Path, "exists", _exists_que_falla_en_odt)
    resultado = internas.repaso_ia(_ctx(tmp_path, [apuntes], IAControlada(), abrir=False))
    assert resultado.codigo == 1
    assert "carpeta de destino" in resultado.error


def _exists_que_falla_en_odt(self) -> bool:
    if str(self).endswith(".odt"):
        raise PermissionError(1, "Operation not permitted")
    return Path.is_file(self) or Path.is_dir(self)


def test_sin_libreoffice_informa_y_deja_usar_a_mano(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        internas, "abrir_en_writer",
        lambda ruta: (_ for _ in ()).throw(EscritorioNoDisponible("LibreOffice no está instalado")),
    )
    resultado = internas.repaso_ia(_ctx(tmp_path, [apuntes], IAControlada(), abrir=True))
    assert resultado.codigo == 0
    assert "no se pudo abrir" in resultado.salida.lower() or "manualmente" in resultado.salida.lower()
    assert "libreoffice" in resultado.salida


def test_sin_ia_configurada_modo_offline(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path)
    monkeypatch.chdir(tmp_path)
    resultado = internas.repaso_ia(_ctx(tmp_path, [apuntes], None, abrir=False))
    assert resultado.codigo == 0
    assert "offline" in resultado.salida


def test_dry_run_no_lee_ni_escribe_nada(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path)
    ctx = _ctx(tmp_path, [apuntes], IAControlada(), abrir=False)
    ctx = ContextoAccion(parametros=dict(ctx.parametros), simular=True, proveedor_ia=ctx.proveedor_ia)
    resultado = internas.repaso_ia(ctx)
    assert resultado.codigo == 0
    assert "[simular]" in resultado.salida
    assert list(tmp_path.glob("*.odt")) == []


def test_los_apuntes_originales_no_se_tocan(monkeypatch, tmp_path) -> None:
    apuntes = _apuntes(tmp_path)
    antes = apuntes.read_bytes()
    _con_ia(monkeypatch, tmp_path, [apuntes], IAControlada(), abrir=False)
    assert apuntes.read_bytes() == antes


def test_varios_documentos_se_analizan_juntos(monkeypatch, tmp_path) -> None:
    a = _apuntes(tmp_path, "tema1.txt", "La mitocondria produce energía.")
    b = _apuntes(tmp_path, "tema2.txt", "El núcleo guarda el ADN.")
    ia = IAControlada()
    _con_ia(monkeypatch, tmp_path, [a, b], ia, abrir=False)
    assert ia.llamadas >= 1
    assert (tmp_path / "tema1.odt").is_file()
    with zipfile.ZipFile(tmp_path / "tema1.odt") as paquete:
        content = paquete.read("content.xml").decode("utf-8")
    assert "tema1.txt" in content and "tema2.txt" in content
