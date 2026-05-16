"""
Tests mínimos del scheduler V2 — Fase 1 técnica.
Ejecutar con: python test_scheduler_v2.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import schedule_proyectos, primer_hueco, asignacion_mejor
from engine import normalizar_programacion_v2

_failures: list = []


def check(nombre: str, condicion: bool, detalle: str = "") -> bool:
    if condicion:
        print(f"  [OK  ] {nombre}")
    else:
        msg = f"  [FAIL] {nombre}"
        if detalle:
            msg += f"\n         → {detalle}"
        print(msg)
        _failures.append(nombre)
    return condicion


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _lineas_abc():
    return {
        "L01": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A", "TIPO_B"}},
        "L02": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A"}},
        "L03": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_B"}},
    }


def _p(pid, modelo, dur, ini_min, ent_target, linea_pref, lineas_alt,
       prioridad, firme, horas_total=None):
    return {
        "proyecto_id": pid, "modelo": modelo, "dur": dur,
        "ini_min": ini_min, "ent_target": ent_target,
        "linea_pref": linea_pref, "lineas_alt": lineas_alt,
        "prioridad": prioridad, "firme": firme, "horas_total": horas_total,
    }


# ---------------------------------------------------------------------------
# Test 1 — Dos FIRME solapados en la misma línea
# ---------------------------------------------------------------------------
def test_01_firme_firme_solape():
    print("\nTest 1: FIRME-FIRME solape en la misma línea")
    lineas = _lineas_abc()
    # P1: S10-S15  P2: S12-S15  → solapan S12-S15
    proyectos = [
        _p("P1", "TIPO_A", 6, 10, 15, "L01", [], 1, True),
        _p("P2", "TIPO_A", 4, 12, 16, "L01", [], 2, True),
    ]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    pids_asg = {a["proyecto_id"] for a in r["asignaciones"]}
    check("P1 planificado", "P1" in pids_asg)
    check("P2 planificado", "P2" in pids_asg)
    check("hay conflicto crítico", len(r["conflictos_criticos"]) > 0)
    check(
        "conflicto tipo FIRME_FIRME_SOLAPE",
        any(c["tipo"] == "FIRME_FIRME_SOLAPE" for c in r["conflictos_criticos"]),
    )
    # Semanas solapadas S12-S15 deben tener ambos proyectos
    cal = r["calendario_por_linea"].get("L01", {})
    solape_ok = all(len(cal.get(s, [])) >= 2 for s in range(12, 16))
    check(
        "calendario conserva ambos en semanas solapadas S12-S15",
        solape_ok,
        str({s: cal.get(s) for s in range(12, 16)}),
    )
    # No se recolocan (P1 y P2 siguen en sus posiciones originales)
    asg = {a["proyecto_id"]: a for a in r["asignaciones"]}
    check("P1 sem_inicio fijo en 10", asg.get("P1", {}).get("sem_inicio") == 10)
    check("P2 sem_inicio fijo en 12", asg.get("P2", {}).get("sem_inicio") == 12)


# ---------------------------------------------------------------------------
# Test 2 — FIRME que termina fuera de horizonte_fin
# ---------------------------------------------------------------------------
def test_02_firme_excede_horizonte():
    print("\nTest 2: FIRME excede horizonte_fin")
    lineas = _lineas_abc()
    # S48 + 8 - 1 = S55  > horizonte_fin=52
    proyectos = [_p("P3", "TIPO_A", 8, 48, 55, "L01", [], 1, True)]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    asg = {a["proyecto_id"]: a for a in r["asignaciones"]}
    check("P3 planificado", "P3" in asg)
    check("P3 estado FIRME", asg.get("P3", {}).get("estado") == "FIRME")
    check("P3 sem_fin = 55", asg.get("P3", {}).get("sem_fin") == 55)
    check(
        "warning 'excede horizonte' generado",
        any("excede horizonte" in w for w in r["warnings"]),
    )


# ---------------------------------------------------------------------------
# Test 3 — FLEXIBLE que no cabe dentro del horizonte_fin
# ---------------------------------------------------------------------------
def test_03_flexible_no_cabe_horizonte():
    print("\nTest 3: FLEXIBLE no cabe dentro del horizonte")
    lineas = _lineas_abc()
    # ini_min=45, dur=10 → necesita hasta S54  > horizonte_fin=52
    proyectos = [_p("P4", "TIPO_A", 10, 45, 55, "L01", [], 1, False)]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    pids_asg = {a["proyecto_id"] for a in r["asignaciones"]}
    pids_excl = {e["proyecto_id"] for e in r["excluidos"]}
    check("P4 NO planificado", "P4" not in pids_asg)
    check("P4 en excluidos", "P4" in pids_excl)
    excl = next((e for e in r["excluidos"] if e["proyecto_id"] == "P4"), {})
    check(
        "estado NO_PLANIFICABLE_SIN_HUECO_HORIZONTE",
        excl.get("estado") == "NO_PLANIFICABLE_SIN_HUECO_HORIZONTE",
    )


# ---------------------------------------------------------------------------
# Test 4 — FLEXIBLE usa línea alternativa
# ---------------------------------------------------------------------------
def test_04_flexible_usa_alternativa():
    print("\nTest 4: FLEXIBLE usa alternativa porque L01 está ocupada")
    lineas = _lineas_abc()
    # Bloquear L01 completa con un FIRME dur=52
    proyectos = [
        _p("BLOQ", "TIPO_A", 52, 1, 52, "L01", [], 1, True),
        _p("P5", "TIPO_A", 4, 1, 20, "L01", ["L02"], 2, False),
    ]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    asg = {a["proyecto_id"]: a for a in r["asignaciones"]}
    check("P5 planificado", "P5" in asg)
    check("P5 uso_alternativa = True", asg.get("P5", {}).get("uso_alternativa") is True)
    check("P5 asignado a L02", asg.get("P5", {}).get("linea_asignada") == "L02")


# ---------------------------------------------------------------------------
# Test 5 — FLEXIBLE sin ninguna línea compatible
# ---------------------------------------------------------------------------
def test_05_flexible_sin_linea_compatible():
    print("\nTest 5: FLEXIBLE sin línea compatible (modelo desconocido)")
    lineas = _lineas_abc()
    # MODELO_Z no está en ninguna lista modelos_compatibles
    proyectos = [_p("P6", "MODELO_Z", 3, 5, 10, "L01", ["L02", "L03"], 1, False)]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    pids_asg = {a["proyecto_id"] for a in r["asignaciones"]}
    pids_excl = {e["proyecto_id"] for e in r["excluidos"]}
    check("P6 NO planificado", "P6" not in pids_asg)
    check("P6 en excluidos", "P6" in pids_excl)
    excl = next((e for e in r["excluidos"] if e["proyecto_id"] == "P6"), {})
    check(
        "estado NO_PLANIFICABLE_SIN_LINEA",
        excl.get("estado") == "NO_PLANIFICABLE_SIN_LINEA",
    )


# ---------------------------------------------------------------------------
# Test 6 — Prioridad negativa → final de cola
# ---------------------------------------------------------------------------
def test_06_prioridad_negativa():
    print("\nTest 6: Prioridad negativa enviada al final de cola")
    lineas = {
        "L01": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A"}},
    }
    proyectos = [
        _p("PNEG", "TIPO_A", 2, 1, 10, "L01", [], -5,  False),
        _p("PPOS", "TIPO_A", 2, 1, 10, "L01", [],  1,  False),
    ]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    asg = {a["proyecto_id"]: a for a in r["asignaciones"]}
    check("PPOS planificado", "PPOS" in asg)
    check("PNEG planificado", "PNEG" in asg)
    sem_ppos = asg.get("PPOS", {}).get("sem_inicio", 999)
    sem_pneg = asg.get("PNEG", {}).get("sem_inicio", 999)
    check(
        "PPOS ocupa antes que PNEG (prioridad positiva gana)",
        sem_ppos < sem_pneg,
        f"sem_inicio PPOS={sem_ppos}, PNEG={sem_pneg}",
    )
    check(
        "warning prioridad negativa generado",
        any("negativa" in w for w in r["warnings"]),
    )


# ---------------------------------------------------------------------------
# Test 7 — Prioridad 0: válida con aviso suave
# ---------------------------------------------------------------------------
def test_07_prioridad_cero():
    print("\nTest 7: Prioridad 0 — válida, genera aviso suave")
    lineas = {
        "L01": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A"}},
    }
    proyectos = [_p("P0", "TIPO_A", 3, 1, 10, "L01", [], 0, False)]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    asg = {a["proyecto_id"]: a for a in r["asignaciones"]}
    check("P0 planificado", "P0" in asg)
    check(
        "aviso prioridad 0 generado",
        any("prioridad 0" in w.lower() for w in r["warnings"]),
    )


# ---------------------------------------------------------------------------
# Test 8 — Duración inválida → excluido, no rompe ejecución
# ---------------------------------------------------------------------------
def test_08_duracion_invalida():
    print("\nTest 8: Duración inválida — excluido, sin excepción")
    lineas = _lineas_abc()
    proyectos = [
        _p("PBAD",  "TIPO_A", "no_valido", 1, 10, "L01", [], 1, False),
        _p("PBAD2", "TIPO_A",  0,           1, 10, "L01", [], 1, False),
        _p("POK",   "TIPO_A",  3,           1, 10, "L01", [], 1, False),
    ]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    pids_excl = {e["proyecto_id"]: e for e in r["excluidos"]}
    pids_asg  = {a["proyecto_id"] for a in r["asignaciones"]}
    check("PBAD en excluidos", "PBAD" in pids_excl)
    check("PBAD2 en excluidos", "PBAD2" in pids_excl)
    check(
        "PBAD estado NO_PLANIFICABLE_GEOMETRICO",
        pids_excl.get("PBAD", {}).get("estado") == "NO_PLANIFICABLE_GEOMETRICO",
    )
    check("POK (dur válida) planificado", "POK" in pids_asg)


# ---------------------------------------------------------------------------
# Test 9 — horas_total vacío/None → sin error, h_sem_real=None
# ---------------------------------------------------------------------------
def test_09_horas_total_vacio():
    print("\nTest 9: horas_total vacío/None — sin excepción, h_sem_real=None")
    lineas = {
        "L01": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A"}},
    }
    proyectos = [
        _p("PH1", "TIPO_A", 3, 1, 10, "L01", [], 1, False, horas_total=None),
        _p("PH2", "TIPO_A", 3, 1, 10, "L01", [], 2, False, horas_total=""),
    ]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    asg = {a["proyecto_id"]: a for a in r["asignaciones"]}
    check("PH1 planificado", "PH1" in asg)
    check("PH2 planificado", "PH2" in asg)
    check("PH1 h_sem_real = None", asg.get("PH1", {}).get("h_sem_real") is None)
    check("PH2 h_sem_real = None", asg.get("PH2", {}).get("h_sem_real") is None)
    check("PH1 alerta_capacidad = False", asg.get("PH1", {}).get("alerta_capacidad") is False)
    check("PH2 alerta_capacidad = False", asg.get("PH2", {}).get("alerta_capacidad") is False)


# ---------------------------------------------------------------------------
# Test 10 — Determinismo: misma entrada → misma salida
# ---------------------------------------------------------------------------
def test_10_determinismo():
    print("\nTest 10: Determinismo — misma entrada, misma salida")
    lineas = _lineas_abc()
    proyectos = [
        _p("PA", "TIPO_A", 4, 1, 10, "L01", ["L02"], 1, False, horas_total=80.0),
        _p("PB", "TIPO_A", 6, 3, 15, "L01", [],      2, False),
        _p("PC", "TIPO_B", 3, 1,  8, "L03", [],      1, True),
    ]
    r1 = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)
    r2 = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    asg1 = [(a["proyecto_id"], a["linea_asignada"], a["sem_inicio"])
            for a in r1["asignaciones"]]
    asg2 = [(a["proyecto_id"], a["linea_asignada"], a["sem_inicio"])
            for a in r2["asignaciones"]]
    check("asignaciones idénticas en dos ejecuciones", asg1 == asg2,
          f"run1={asg1}  run2={asg2}")

    excl1 = sorted(e["proyecto_id"] for e in r1["excluidos"])
    excl2 = sorted(e["proyecto_id"] for e in r2["excluidos"])
    check("excluidos idénticos en dos ejecuciones", excl1 == excl2)


# ---------------------------------------------------------------------------
# Test 11 — Prioridad decimal
# ---------------------------------------------------------------------------
def test_11_prioridad_decimal():
    print("\nTest 11: Prioridad decimal")
    lineas = {
        "L01": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A"}},
    }

    # 11a: float decimal no entero → 9999 + warning
    proyectos_dec = [
        _p("P_15",  "TIPO_A", 2, 1, 10, "L01", [], 1.5,  False),
        _p("P_19S", "TIPO_A", 2, 1, 10, "L01", [], "1.9", False),
    ]
    r = schedule_proyectos(proyectos_dec, lineas, semana_actual=1, horizonte_fin=52)
    check(
        "1.5 genera warning 'decimal'",
        any("decimal" in w for w in r["warnings"]),
        str(r["warnings"]),
    )
    check(
        '"1.9" genera warning "decimal"',
        any("decimal" in w for w in r["warnings"]),
    )
    # Ambos deben planificarse (con prioridad efectiva 9999, no bloqueados)
    pids_asg = {a["proyecto_id"] for a in r["asignaciones"]}
    check("P_15 planificado (prioridad->9999)", "P_15" in pids_asg)
    check("P_19S planificado (prioridad->9999)", "P_19S" in pids_asg)

    # 11b: float entero (1.0, 2.0) → acepta, sin warning "decimal"
    proyectos_fint = [
        _p("PF10", "TIPO_A", 2, 1, 10, "L01", [], 1.0, False),
        _p("PF20", "TIPO_A", 2, 1, 10, "L01", [], 2.0, False),
    ]
    r2 = schedule_proyectos(proyectos_fint, lineas, semana_actual=1, horizonte_fin=52)
    pids_asg2 = {a["proyecto_id"] for a in r2["asignaciones"]}
    check("1.0 planificado normalmente", "PF10" in pids_asg2)
    check("2.0 planificado normalmente", "PF20" in pids_asg2)
    check(
        "1.0 y 2.0 no generan warning 'decimal'",
        not any("decimal" in w for w in r2["warnings"]),
        str(r2["warnings"]),
    )
    # PF10 (prioridad 1) debe ocupar antes que PF20 (prioridad 2)
    asg2 = {a["proyecto_id"]: a for a in r2["asignaciones"]}
    check(
        "1.0 planificado antes que 2.0 (orden prioridad correcto)",
        asg2.get("PF10", {}).get("sem_inicio", 999)
        < asg2.get("PF20", {}).get("sem_inicio", 999),
    )


# ---------------------------------------------------------------------------
# Test 12 — ini_min no numérica en FLEXIBLE
# ---------------------------------------------------------------------------
def test_12_ini_min_no_numerica():
    print("\nTest 12: ini_min no numérica en FLEXIBLE")
    lineas = {
        "L01": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A"}},
    }
    proyectos = [
        _p("PINI", "TIPO_A", 3, "abc", 20, "L01", [], 1, False),
    ]
    r = schedule_proyectos(proyectos, lineas, semana_actual=5, horizonte_fin=52)

    # No debe lanzar excepción; debe planificarse usando semana_actual como fallback
    pids_asg = {a["proyecto_id"] for a in r["asignaciones"]}
    check("PINI planificado (sin excepción)", "PINI" in pids_asg)
    check(
        "warning ini_min inválida generado",
        any("ini_min" in w for w in r["warnings"]),
        str(r["warnings"]),
    )
    asg = {a["proyecto_id"]: a for a in r["asignaciones"]}
    # Fallback a semana_actual=5 → sem_inicio debe ser >= 5
    check(
        "sem_inicio >= semana_actual (fallback correcto)",
        asg.get("PINI", {}).get("sem_inicio", 0) >= 5,
    )


# ---------------------------------------------------------------------------
# Test 13 — ent_target no numérica
# ---------------------------------------------------------------------------
def test_13_ent_target_no_numerica():
    print("\nTest 13: ent_target no numérica")
    lineas = {
        "L01": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A"}},
    }
    proyectos = [
        _p("PET", "TIPO_A", 3, 1, "no_fecha", "L01", [], 1, False),
    ]
    r = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=52)

    pids_asg = {a["proyecto_id"] for a in r["asignaciones"]}
    check("PET planificado (sin excepción)", "PET" in pids_asg)
    check(
        "warning ent_target inválida generado",
        any("ent_target" in w for w in r["warnings"]),
        str(r["warnings"]),
    )


# ---------------------------------------------------------------------------
# Test 14 — horizonte_fin inválido → retorno controlado
# ---------------------------------------------------------------------------
def test_14_horizonte_fin_invalido():
    print("\nTest 14: horizonte_fin inválido — retorno controlado")
    lineas = {
        "L01": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A"}},
    }
    proyectos = [_p("P1", "TIPO_A", 3, 1, 10, "L01", [], 1, False)]

    # 14a: string no numérico
    r_str = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin="malo")
    check(
        "horizonte_fin='malo': conflicto HORIZONTE_FIN_INVALIDO",
        any(c.get("tipo") == "HORIZONTE_FIN_INVALIDO"
            for c in r_str.get("conflictos_criticos", [])),
    )
    check(
        "horizonte_fin='malo': asignaciones vacias",
        r_str.get("asignaciones") == [],
    )

    # 14b: cero
    r_cero = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=0)
    check(
        "horizonte_fin=0: conflicto HORIZONTE_FIN_INVALIDO",
        any(c.get("tipo") == "HORIZONTE_FIN_INVALIDO"
            for c in r_cero.get("conflictos_criticos", [])),
    )

    # 14c: negativo
    r_neg = schedule_proyectos(proyectos, lineas, semana_actual=1, horizonte_fin=-10)
    check(
        "horizonte_fin=-10: conflicto HORIZONTE_FIN_INVALIDO",
        any(c.get("tipo") == "HORIZONTE_FIN_INVALIDO"
            for c in r_neg.get("conflictos_criticos", [])),
    )


# ===========================================================================
# Tests Fase 2 — normalizar_programacion_v2()
# ===========================================================================

def _fila_valida(**kw):
    """Fila base valida; se pueden sobreescribir campos via kw."""
    base = {
        "Proyecto": "P001",
        "Modelo": "SL3200",
        "Duracion": 4,
        "Semana inicio": 10,
        "Semana entrega": 20,
        "Linea": "L07",
        "Prioridad": 1,
        "Firme": "FLEXIBLE",
        "Horas": 120.0,
    }
    base.update(kw)
    return base


def test_a01_caso_valido_completo():
    print("\nTest A01: Caso valido completo")
    filas = [_fila_valida()]
    r = normalizar_programacion_v2(filas)
    check("ok=True", r["ok"] is True, str(r["errores"]))
    check("1 proyecto valido", len(r["proyectos"]) == 1)
    check("sin errores", len(r["errores"]) == 0)
    p = r["proyectos"][0]
    check("proyecto_id='P001'", p["proyecto_id"] == "P001")
    check("modelo='SL3200'", p["modelo"] == "SL3200")
    check("dur=4", p["dur"] == 4)
    check("ini_min=10", p["ini_min"] == 10)
    check("ent_target=20", p["ent_target"] == 20)
    check("linea_pref='L07'", p["linea_pref"] == "L07")
    check("firme=False", p["firme"] is False)
    check("horas_total=120.0", p["horas_total"] == 120.0)


def test_a02_alias_columnas():
    print("\nTest A02: Alias de columnas")
    filas = [{
        "Codigo": "P002",
        "Familia": "SL",
        "Duracion semanas": 3,
        "Inicio minimo": 5,
        "Entrega contractual": 15,
        "Linea preferente": "L01",
        "Urgencia": 2,
        "Firme/Flexible": "NO",
    }]
    r = normalizar_programacion_v2(filas)
    check("ok=True", r["ok"] is True, str(r["errores"]))
    check("mapeo proyecto_id", r["mapeo_columnas"]["proyecto_id"] == "Codigo")
    check("mapeo modelo", r["mapeo_columnas"]["modelo"] == "Familia")
    check("mapeo linea_pref", r["mapeo_columnas"]["linea_pref"] == "Linea preferente")
    check("mapeo prioridad", r["mapeo_columnas"]["prioridad"] == "Urgencia")


def test_a03_alias_modelo_familia():
    print("\nTest A03: Alias 'Modelo / familia' -> modelo en mayusculas")
    filas = [{
        "Proyecto": "P003",
        "Modelo / familia": "sl3200 xl",
        "Duracion": 3,
        "Semana inicio": 5,
        "Semana entrega": 15,
        "Linea": "L01",
        "Prioridad": 1,
        "Firme": "NO",
    }]
    r = normalizar_programacion_v2(filas)
    check("ok=True", r["ok"] is True, str(r["errores"]))
    check(
        "mapeo modelo -> 'Modelo / familia'",
        r["mapeo_columnas"]["modelo"] == "Modelo / familia",
    )
    check("modelo en mayusculas", r["proyectos"][0]["modelo"] == "SL3200 XL")


def test_a04_duracion_decimal_no_entera():
    print("\nTest A04: Duracion=4.5 -> error critico, proyecto no incluido")
    filas = [_fila_valida(**{"Proyecto": "P004", "Duracion": 4.5})]
    r = normalizar_programacion_v2(filas)
    check("ok=False", r["ok"] is False)
    check("proyecto no incluido", len(r["proyectos"]) == 0)
    check("error campo dur", any(e["campo"] == "dur" for e in r["errores"]))


def test_a05_semana_invalida():
    print("\nTest A05: Semana inicio='abc' -> error critico")
    filas = [_fila_valida(**{"Proyecto": "P005", "Semana inicio": "abc"})]
    r = normalizar_programacion_v2(filas)
    check("ok=False", r["ok"] is False)
    check("proyecto no incluido", len(r["proyectos"]) == 0)
    check("error campo ini_min", any(e["campo"] == "ini_min" for e in r["errores"]))


def test_a06_prioridad_mala():
    print("\nTest A06: Prioridad='Alta' -> proyecto incluido, prioridad=9999, warning")
    filas = [_fila_valida(**{"Proyecto": "P006", "Prioridad": "Alta"})]
    r = normalizar_programacion_v2(filas)
    check("ok=True (solo warning)", r["ok"] is True, str(r["errores"]))
    check("proyecto incluido", len(r["proyectos"]) == 1)
    check("prioridad=9999", r["proyectos"][0]["prioridad"] == 9999)
    check(
        "warning prioridad",
        any(w.get("campo") == "prioridad" for w in r["warnings"] if isinstance(w, dict)),
    )


def test_a07_prioridad_decimal():
    print("\nTest A07: Prioridad='1.9' -> proyecto incluido, prioridad=9999, warning decimal")
    filas = [_fila_valida(**{"Proyecto": "P007", "Prioridad": "1.9"})]
    r = normalizar_programacion_v2(filas)
    check("ok=True", r["ok"] is True)
    check("proyecto incluido", len(r["proyectos"]) == 1)
    check("prioridad=9999", r["proyectos"][0]["prioridad"] == 9999)
    check(
        "warning contiene 'decimal'",
        any("decimal" in w.get("mensaje", "") for w in r["warnings"] if isinstance(w, dict)),
    )


def test_a08_prioridad_cero():
    print("\nTest A08: Prioridad=0 -> proyecto incluido, prioridad=0, warning suave")
    filas = [_fila_valida(**{"Proyecto": "P008", "Prioridad": 0})]
    r = normalizar_programacion_v2(filas)
    check("ok=True", r["ok"] is True)
    check("proyecto incluido", len(r["proyectos"]) == 1)
    check("prioridad=0", r["proyectos"][0]["prioridad"] == 0)
    check("hay warning", len(r["warnings"]) > 0)


def test_a09_firme_reconocido():
    print("\nTest A09: firme=True para FIRME, SI, True, 1")
    for val in ["FIRME", "SI", True, "1"]:
        pid = f"P_firme_{val}"
        filas = [_fila_valida(**{"Proyecto": pid, "Firme": val})]
        r = normalizar_programacion_v2(filas)
        check(
            f"firme=True para valor={val!r}",
            len(r["proyectos"]) == 1 and r["proyectos"][0]["firme"] is True,
            str(r["errores"]),
        )


def test_a10_flexible_por_defecto():
    print("\nTest A10: Firme vacio -> firme=False, sin error")
    filas = [_fila_valida(**{"Proyecto": "P010", "Firme": ""})]
    r = normalizar_programacion_v2(filas)
    check("ok=True", r["ok"] is True, str(r["errores"]))
    check("proyecto incluido", len(r["proyectos"]) == 1)
    check("firme=False", r["proyectos"][0]["firme"] is False)


def test_a11_lineas_alt():
    print("\nTest A11: lineas_alt - separadores mixtos y eliminacion de linea_pref")
    filas = [{
        "Proyecto": "P011",
        "Modelo": "SL",
        "Duracion": 4,
        "Semana inicio": 10,
        "Semana entrega": 20,
        "Linea": "L07",
        "Lineas alternativas": "L1, L2; L3 / L4",
        "Prioridad": 1,
        "Firme": "NO",
    }]
    r = normalizar_programacion_v2(filas)
    check("ok=True", r["ok"] is True, str(r["errores"]))
    alts = r["proyectos"][0]["lineas_alt"]
    check("4 alternativas detectadas", len(alts) == 4, str(alts))
    check("L1 en alternativas", "L1" in alts)
    check("L4 en alternativas", "L4" in alts)

    # linea_pref en alt -> se elimina
    filas2 = [_fila_valida(**{
        "Proyecto": "P011B",
        "Lineas alternativas": "L07, L08",
    })]
    r2 = normalizar_programacion_v2(filas2)
    check("ok=True (b)", r2["ok"] is True, str(r2["errores"]))
    alts2 = r2["proyectos"][0]["lineas_alt"]
    check("L07 eliminada de alt (es linea_pref)", "L07" not in alts2, str(alts2))
    check("L08 permanece en alt", "L08" in alts2)
    check(
        "warning eliminacion linea_pref de alt",
        any("linea_pref" in w.get("mensaje", "") for w in r2["warnings"] if isinstance(w, dict)),
    )


def test_a12_horas_total_invalida():
    print("\nTest A12: horas_total='abc' -> proyecto incluido, horas_total=None, warning")
    filas = [_fila_valida(**{"Proyecto": "P012", "Horas": "abc"})]
    r = normalizar_programacion_v2(filas)
    check("ok=True", r["ok"] is True, str(r["errores"]))
    check("proyecto incluido", len(r["proyectos"]) == 1)
    check("horas_total=None", r["proyectos"][0]["horas_total"] is None)
    check(
        "warning horas_total",
        any(w.get("campo") == "horas_total" for w in r["warnings"] if isinstance(w, dict)),
    )


def test_a13_fila_con_error_critico():
    print("\nTest A13: Fila con error critico excluida, otras filas validas pasan")
    filas = [
        _fila_valida(**{"Proyecto": "OK01"}),
        _fila_valida(**{"Proyecto": "BAD01", "Duracion": "no_valida"}),
        _fila_valida(**{"Proyecto": "OK02"}),
    ]
    r = normalizar_programacion_v2(filas)
    check("ok=False (hay errores)", r["ok"] is False)
    pids = [p["proyecto_id"] for p in r["proyectos"]]
    check("OK01 incluido", "OK01" in pids)
    check("OK02 incluido", "OK02" in pids)
    check("BAD01 no incluido", "BAD01" not in pids)
    check(
        "error registrado para BAD01",
        any(e.get("proyecto_id") == "BAD01" for e in r["errores"]),
    )
    check("resumen filas_con_error=1", r["resumen"]["filas_con_error"] == 1)
    check("resumen proyectos_validos=2", r["resumen"]["proyectos_validos"] == 2)


def test_a14_proyecto_id_duplicado():
    print("\nTest A14: proyecto_id duplicado -> segunda aparicion es error critico")
    filas = [
        _fila_valida(**{"Proyecto": "DUP001"}),
        _fila_valida(**{"Proyecto": "DUP001"}),
        _fila_valida(**{"Proyecto": "UNICO"}),
    ]
    r = normalizar_programacion_v2(filas)
    check("ok=False (hay error duplicado)", r["ok"] is False)
    pids = [p["proyecto_id"] for p in r["proyectos"]]
    check("primera DUP001 incluida", pids.count("DUP001") == 1)
    check("UNICO incluido", "UNICO" in pids)
    check(
        "error contiene 'duplicado'",
        any("duplicado" in e.get("mensaje", "") for e in r["errores"]),
    )


def test_a15_columnas_ambiguas():
    print("\nTest A15: Columnas ambiguas -> usa primera alias, genera warning")
    filas = [{
        "Proyecto": "P015",
        "Modelo": "SL",
        "Modelo / familia": "SL_ALT",
        "Duracion": 4,
        "Semana inicio": 10,
        "Semana entrega": 20,
        "Linea": "L07",
        "Prioridad": 1,
        "Firme": "NO",
    }]
    r = normalizar_programacion_v2(filas)
    elegida = r["mapeo_columnas"]["modelo"]
    check("usa 'Modelo' (primera en alias list)", elegida == "Modelo")
    check(
        "warning de ambiguedad generado",
        any(
            "multiples columnas candidatas" in w.get("mensaje", "")
            for w in r["warnings"]
            if isinstance(w, dict)
        ),
        str(r["warnings"]),
    )


def test_a16_normalizacion_mayusculas():
    print("\nTest A16: Normalizacion a mayusculas y strip")
    fila = _fila_valida(**{
        "Proyecto": "P016",
        "Modelo": " sl ",
        "Linea": " l07 ",
    })
    fila["Lineas alternativas"] = " l08, l09 "
    r = normalizar_programacion_v2([fila])
    check("ok=True", r["ok"] is True, str(r["errores"]))
    p = r["proyectos"][0]
    check("modelo='SL'", p["modelo"] == "SL", repr(p["modelo"]))
    check("linea_pref='L07'", p["linea_pref"] == "L07", repr(p["linea_pref"]))
    check(
        "lineas_alt=['L08','L09']",
        p["lineas_alt"] == ["L08", "L09"],
        str(p["lineas_alt"]),
    )


def test_a17_integracion_con_schedule():
    print("\nTest A17: Salida de normalizar compatible con schedule_proyectos")
    filas = [
        _fila_valida(**{"Proyecto": "A17F", "Firme": "FIRME", "Modelo": "TIPO_A"}),
        _fila_valida(**{"Proyecto": "A17X", "Firme": "FLEXIBLE", "Modelo": "TIPO_A"}),
    ]
    r_norm = normalizar_programacion_v2(filas)
    check("normalizacion ok=True", r_norm["ok"] is True, str(r_norm["errores"]))
    check("2 proyectos normalizados", len(r_norm["proyectos"]) == 2)

    lineas = {
        "L07": {"capacidad_h_sem": 40.0, "modelos_compatibles": {"TIPO_A"}},
    }
    r_sched = schedule_proyectos(
        r_norm["proyectos"], lineas, semana_actual=1, horizonte_fin=52
    )
    check("schedule_proyectos sin excepcion", True)
    pids_asg = {a["proyecto_id"] for a in r_sched["asignaciones"]}
    check("A17F planificado", "A17F" in pids_asg)
    check("A17X planificado", "A17X" in pids_asg)


def test_a18_sin_columna_firme_flexible():
    """Sin columna Firme/Flexible: ok=True, firme=False, warning global."""
    print("\nTest A18: Sin columna Firme/Flexible")
    fila = {
        "Proyecto":                "P_NOFF",
        "Modelo / familia":        "SL",
        "Duracion semanas":        4,
        "Semana inicio minima":    1,
        "Semana entrega objetivo": 10,
        "Linea preferente":        "L01",
        "Prioridad":               1,
        "Horas totales":           80.0,
        # sin "Firme/Flexible"
    }
    res = normalizar_programacion_v2([fila])
    check("A18 ok=True", res["ok"] is True)
    check("A18 proyecto incluido", len(res["proyectos"]) == 1)
    check("A18 firme=False", res["proyectos"][0]["firme"] is False)
    warn_msgs = [
        w.get("mensaje", "") if isinstance(w, dict) else str(w)
        for w in res.get("warnings", [])
    ]
    check(
        "A18 warning global Firme/Flexible ausente",
        any("Firme/Flexible" in m for m in warn_msgs),
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests_fase1 = [
        test_01_firme_firme_solape,
        test_02_firme_excede_horizonte,
        test_03_flexible_no_cabe_horizonte,
        test_04_flexible_usa_alternativa,
        test_05_flexible_sin_linea_compatible,
        test_06_prioridad_negativa,
        test_07_prioridad_cero,
        test_08_duracion_invalida,
        test_09_horas_total_vacio,
        test_10_determinismo,
        test_11_prioridad_decimal,
        test_12_ini_min_no_numerica,
        test_13_ent_target_no_numerica,
        test_14_horizonte_fin_invalido,
    ]

    tests_fase2 = [
        test_a01_caso_valido_completo,
        test_a02_alias_columnas,
        test_a03_alias_modelo_familia,
        test_a04_duracion_decimal_no_entera,
        test_a05_semana_invalida,
        test_a06_prioridad_mala,
        test_a07_prioridad_decimal,
        test_a08_prioridad_cero,
        test_a09_firme_reconocido,
        test_a10_flexible_por_defecto,
        test_a11_lineas_alt,
        test_a12_horas_total_invalida,
        test_a13_fila_con_error_critico,
        test_a14_proyecto_id_duplicado,
        test_a15_columnas_ambiguas,
        test_a16_normalizacion_mayusculas,
        test_a17_integracion_con_schedule,
        test_a18_sin_columna_firme_flexible,
    ]

    print("=" * 60)
    print("  Tests Scheduler V2 - Fase 1 tecnica")
    print("=" * 60)
    for t in tests_fase1:
        try:
            t()
        except Exception as exc:
            import traceback
            print(f"  [EXCEPTION] {t.__name__}: {exc}")
            traceback.print_exc()
            _failures.append(t.__name__)

    print("\n" + "=" * 60)
    print("  Tests Scheduler V2 - Fase 2: Adaptador / Validador")
    print("=" * 60)
    for t in tests_fase2:
        try:
            t()
        except Exception as exc:
            import traceback
            print(f"  [EXCEPTION] {t.__name__}: {exc}")
            traceback.print_exc()
            _failures.append(t.__name__)

    print("\n" + "=" * 60)
    if _failures:
        print(f"  RESULTADO: {len(_failures)} check(s) fallaron:")
        for f in _failures:
            print(f"    - {f}")
        sys.exit(1)
    else:
        print("  RESULTADO: todos los checks pasaron.")
        sys.exit(0)
