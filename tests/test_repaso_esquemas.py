"""Pruebas de los esquemas locales deterministas de repaso-ia."""

from tareas.repaso.esquemas import dibujar, detectar


def test_detecta_mapa_conceptual_con_cajas() -> None:
    esquema = detectar(
        "esquema: La célula :: unidad de la vida\nMembrana :: regula el paso"
    )
    assert esquema is not None
    assert esquema.tipo == "esquema"
    lineas = dibujar(esquema)
    unidos = "\n".join(lineas)
    assert "La célula" in unidos
    assert "┌" in unidos and "└" in unidos  # cajas cerradas
    assert "▼" in unidos  # conexión entre bloques


def test_timeline_con_fechas_detectadas() -> None:
    esquema = detectar("1492 :: viaje\n1789 :: revolución")
    assert esquema is not None and esquema.tipo == "timeline"
    assert "●" in dibujar(esquema)[0]


def test_tabla_equivalente_conserva_la_info() -> None:
    esquema = detectar("tabla: Reptil :: sangre fría\nAve :: plumas")
    assert esquema is not None and esquema.tipo == "tabla"
    tabla = esquema.tabla
    assert tabla[0] == list(esquema.columnas)
    assert ["Reptil", "sangre fría"] in tabla


def test_especificacion_insuficiente_devuelve_none() -> None:
    assert detectar("solo una línea suelta") is None
    assert detectar("") is None


def test_detalles_largos_se_cortan_sin_romper_la_caja() -> None:
    largo = "x " * 80
    esquema = detectar(f"esquema: A :: {largo}\nB :: d")
    assert esquema is not None
    for linea in dibujar(esquema):
        assert len(linea) <= 46


def test_sin_servicios_externos() -> None:
    # dibujar y detectar son funciones puras locales: sin red, sin binarios.
    esquema = detectar("lista: Raíz :: tronco\nRamas :: hojas")
    assert esquema.tipo == "lista"
