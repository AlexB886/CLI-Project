"""Pruebas de la normalización del maestro y composición del repaso."""

from tareas.repaso.contenidos import construir_documento, detectar_esquemas

MAESTRO = """# Introducción
Apuntes de biología.

## ESQUEMA
esquema: La célula :: unidad de la vida
Núcleo :: ADN

# Resumen por apartados
### Membrana
Regula el paso.

### Núcleo
Guarda el ADN.

# Conceptos clave
- Mitocondria: energía

# Common mistakes
- Confundir fases.

# Preguntas para el examen
1. ¿Qué hace el núcleo?
"""


def test_secciones_canonicas_en_orden() -> None:
    secciones = construir_documento(MAESTRO, [])
    titulos = [s.titulo for s in secciones]
    assert titulos == [
        "Introducción",
        "Resumen por apartados",
        "Conceptos clave",
        "Explicaciones didácticas",
        "Errores y confusiones frecuentes",
        "Repaso final de lo imprescindible",
        "Preguntas para el examen",
    ]


def test_ingles_traducido_y_subtitulos_conservados() -> None:
    secciones = {s.titulo: s for s in construir_documento(MAESTRO, [])}
    errores = secciones["Errores y confusiones frecuentes"]
    assert any("Confundir fases" in l for l in errores.cuerpo)
    resumen = secciones["Resumen por apartados"]
    assert any(l.strip().startswith("Membrana") for l in resumen.cuerpo)


def test_seccion_falta_se_avisa_sin_inventar() -> None:
    secciones = {s.titulo: s for s in construir_documento(MAESTRO, [])}
    explicaciones = secciones["Explicaciones didácticas"]
    assert len(explicaciones.cuerpo) == 1
    assert any("no generó" in l.lower() for l in explicaciones.cuerpo)


def test_bloques_esquema_no_se_repiten_como_texto() -> None:
    secciones = construir_documento(MAESTRO, detectar_esquemas(MAESTRO))
    cuerpos = {s.titulo: "\n".join(s.cuerpo) for s in secciones}
    assert "esquema:" not in cuerpos["Introducción"]
    assert "esquema:" not in cuerpos["Conceptos clave"]
    assert not any("unidad de la vida" in c for t, c in cuerpos.items() if t != "Esquemas")


def test_esquemas_detectados_del_maestro() -> None:
    esquemas = detectar_esquemas(MAESTRO)
    assert len(esquemas) == 1
    assert [e for e, _ in esquemas[0].entradas][0] == "La célula"


def test_seccion_esquemas_reutiliza_los_diagramas() -> None:
    secciones = construir_documento(MAESTRO, detectar_esquemas(MAESTRO))
    esquemas = [s for s in secciones if s.titulo == "Esquemas"]
    assert esquemas  # la sección existe aunque el cuerpo se pinte aparte
