"""Prueba de integración: repaso-ia produce un ODT completo y bien estructurado."""

import zipfile
from pathlib import Path

import tareas.acciones.internas as internas
from tareas.modelos import ContextoAccion
from tareas.repaso.contenidos import SECCIONES_ESPERADAS

MAESTRO = """# Introducción
La fotosíntesis transforma luz en energía química.

## ESQUEMA
esquema: Fotosíntesis :: luz a energía
Fase luminosa :: agua a oxígeno
Fase oscura :: ciclo de Calvin

# Resumen por apartados
### Fase luminosa
Ocurre en los tilacoides y libera oxígeno.

### Fase oscura
Fija el carbono en el estroma.

# Conceptos clave
- Clorofila: pigmento que capta la luz
- Calvin: ciclo de fijación de carbono

# Explicaciones didácticas
Piensa en la clorofila como un panel solar.

# Tablas comparativas
tabla: Fase luminosa :: tilacoides
Fase oscura :: estroma

# Errores y confusiones frecuentes
- Creer que la fase oscura ocurre de noche.

# Repaso final de lo imprescindible
- La fotosíntesis alimenta la práctica totalidad de los ecosistemas.

# Preguntas para el examen
1. ¿Dónde ocurre la fase luminosa?
"""


class IAExitosa:
    nombre = "maestra"

    def disponible(self) -> bool:
        return True

    def generar_texto(self, peticion: str, contexto: str) -> str:
        return MAESTRO


def test_repaso_completo_con_esquemas_y_tabla(tmp_path: Path, monkeypatch) -> None:
    apuntes = tmp_path / "tema-fotosintesis.txt"
    apuntes.write_text("Apuntes de la fotosíntesis.", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    abierto: list[Path] = []
    monkeypatch.setattr(
        internas, "abrir_en_writer", lambda ruta: abierto.append(ruta) or "soffice"
    )
    resultado = internas.repaso_ia(
        ContextoAccion(
            parametros={
                "archivos": ["tema-fotosintesis.txt"],
                "objetivo": "examen tipo test",
                "abrir": True,
            },
            proveedor_ia=IAExitosa(),
            simular=False,
        )
    )
    assert resultado.codigo == 0
    assert abierto and abierto[0].is_file()

    with zipfile.ZipFile(abierto[0]) as paquete:
        content = paquete.read("content.xml").decode("utf-8")

    for titulo in SECCIONES_ESPERADAS:
        assert titulo in content, f"falta la sección {titulo}"
    assert "Fotosíntesis" in content
    assert "Fase luminosa" in content and "estroma" in content
    assert "table:table-row" in content  # la tabla comparativa es una tabla real
    assert "esquema:" not in content  # el esquema no queda como texto crudo
    assert "Fotosíntesis" in content  # el esquema viajó al ODT como lista jerárquica
    assert "panel solar" in content  # la explicación didáctica viajó al ODT
