from __future__ import annotations
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# =========================
# Parámetros de planta
# =========================
@dataclass
class PlantParams:
    hours_per_week: float
    turns: int
    availability: float
    efficiency: float

    @property
    def hours_effective(self) -> float:
        return float(self.hours_per_week) * int(self.turns) * float(self.availability) * float(self.efficiency)


# =========================
# Utilidades normalización
# =========================
def _norm_str(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.upper()

def _to_num(s: pd.Series) -> pd.Series:
    # Convierte "48", "48.0", "48,0" a numérico
    return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce")


# =========================
# Carga de datos
# =========================
def load_data(data_dir: str) -> Dict[str, pd.DataFrame]:
    times = pd.read_csv(f"{data_dir}/models_process_times.csv")
    stations = pd.read_csv(f"{data_dir}/lines_process_stations.csv")
    compat = pd.read_csv(f"{data_dir}/compatibility.csv")

    # Normalización fuerte de campos clave
    if "model" in times.columns:
        times["model"] = _norm_str(times["model"])
    if "process" in times.columns:
        times["process"] = _norm_str(times["process"])
    if "cycle_time" in times.columns:
        times["cycle_time"] = _to_num(times["cycle_time"])
    if "machine_time" in times.columns:
        times["machine_time"] = _to_num(times["machine_time"])
    if "labor_time" in times.columns:
        times["labor_time"] = _to_num(times["labor_time"])

    if "line" in stations.columns:
        stations["line"] = _norm_str(stations["line"])
    if "process" in stations.columns:
        stations["process"] = _norm_str(stations["process"])
    if "stations" in stations.columns:
        stations["stations"] = _to_num(stations["stations"])

    if "line" in compat.columns:
        compat["line"] = _norm_str(compat["line"])
    if "model" in compat.columns:
        compat["model"] = _norm_str(compat["model"])
    if "nave" in compat.columns:
        compat["nave"] = _norm_str(compat["nave"])
    if "compatible" in compat.columns:
        compat["compatible"] = _to_num(compat["compatible"]).fillna(0).astype(int)

    # Limpieza de filas rotas
    times = times.dropna(subset=["model", "process"])
    stations = stations.dropna(subset=["line", "process", "stations"])

    return {"times": times, "stations": stations, "compat": compat}


# =========================
# Compatibilidades
# =========================
def compatible_models_for_line(
    compat_df: pd.DataFrame,
    line: str,
    plant_id: int = None,
    nave: str = None,
) -> List[str]:
    """
    Devuelve modelos compatibles para una línea.
    ✅ FIX: Filtra por plant_id + nave + line (clave completa),
    no solo por line.
    """
    line = str(line).strip().upper()
    mask = (compat_df["line"] == line) & (compat_df["compatible"].astype(int) == 1)
    if plant_id is not None:
        mask = mask & (compat_df["plant_id"] == plant_id)
    if nave is not None:
        nave = str(nave).strip().upper()
        mask = mask & (compat_df["nave"].astype(str).str.strip().str.upper() == nave)
    sub = compat_df[mask]
    return sorted(sub["model"].unique().tolist())


# =========================
# Cálculo de capacidad
# =========================
def compute_line_capacity(
    plant: PlantParams,
    plant_id: int,
    line: str,
    model: str,
    times_df: pd.DataFrame,
    stations_df: pd.DataFrame,
) -> Dict:
    """
    Replica la lógica Excel:

    Capacidad proceso = (HorasEfectivas * estaciones * operarios_por_estacion) / tiempo_ciclo
    Capacidad línea = mínimo (cuello)
    """

    hours_eff = float(plant.hours_effective)
    line = str(line).strip().upper()
    model = str(model).strip().upper()
    line = _norm_str(pd.Series([line])).iloc[0]
    model = _norm_str(pd.Series([model])).iloc[0]


    # ✅ Alias por si vienen nombres distintos en CSV
    PROCESS_ALIASES = {
        "PTB1": "PTBI",
        "PTB": "PTBI",
        "PRETEST": "PTBI",
        "PRE-TEST": "PTBI",
        "MAINLINE": "ML",
        "MAIN LINE": "ML",
        "PREMONTAJE": "PREM",
    }

    # Copias y normalización en cálculo (por si algo se cuela)
    # Filtrar datos por planta
    t = times_df[times_df["plant_id"] == plant_id].copy()
    s = stations_df[stations_df["plant_id"] == plant_id].copy()

    t["process"] = _norm_str(t["process"]).replace(PROCESS_ALIASES)
    s["process"] = _norm_str(s["process"]).replace(PROCESS_ALIASES)

    # Filtrado por modelo y línea
    # Columnas de tiempo disponibles (retrocompatible)
    time_cols = ["process", "cycle_time"]
    if "machine_time" in t.columns:
        time_cols.append("machine_time")
    if "labor_time" in t.columns:
        time_cols.append("labor_time")

    t = t[
        (t["model"].astype(str).str.strip().str.upper() == model)
    ][time_cols].copy()

    s = s[s["line"].astype(str).str.strip().str.upper() == line][["process", "stations", "operators_per_station"]].copy()

    # Asegurar numéricos
    t["cycle_time"] = _to_num(t["cycle_time"])
    s["stations"] = _to_num(s["stations"])
    s["operators_per_station"] = _to_num(s["operators_per_station"])

    merged = pd.merge(s, t, on="process", how="inner")

    if merged.empty:
        return {
            "line": line,
            "model": model,
            "hours_effective": hours_eff,
            "capacity_total": 0.0,
            "bottleneck": None,
            "capacity_per_process": {},
            "debug": [],
            "note": "No hay procesos comunes entre estaciones (línea) y tiempos (modelo). Revisa nombres de proceso/line/model en CSV.",
        }

    # Operarios por proceso (si no existe -> 1)
    merged["operators"] = _to_num(merged["operators_per_station"]).fillna(1).astype(float)
    merged["stations"] = _to_num(merged["stations"])

    # ✅ FIX: Filtrar procesos sin estaciones o con datos inválidos antes de calcular
    merged = merged[merged["stations"].notna() & (merged["stations"] > 0)].copy()

    if merged.empty:
        return {
            "line": line,
            "model": model,
            "hours_effective": hours_eff,
            "capacity_total": 0.0,
            "bottleneck": None,
            "capacity_per_process": {},
            "debug": [],
            "note": "No hay procesos con estaciones válidas para esta línea/modelo.",
        }

    # =========================================================
    # Cálculo de capacidad: cycle_time_real
    # =========================================================
    # cycle_time_real = max(machine_time, labor_time / operators)
    # capacity = (hours_effective * stations) / cycle_time_real

    # Preparar machine_time (si no existe o nulo → 0)
    if "machine_time" in merged.columns:
        merged["machine_time"] = _to_num(merged["machine_time"]).fillna(0.0)
    else:
        merged["machine_time"] = 0.0

    # Preparar labor_time (si no existe o nulo → 0)
    if "labor_time" in merged.columns:
        merged["labor_time"] = _to_num(merged["labor_time"]).fillna(0.0)
    else:
        merged["labor_time"] = 0.0

    # Operarios efectivos (mínimo 1 para evitar división por cero)
    merged["operators"] = merged["operators"].replace(0,1).fillna(1)

    # Labor por operario
    merged["labor_per_operator"] = merged["labor_time"] / merged["operators"]

    # Cycle time real = max(machine_time, labor_per_operator)
    merged["cycle_time_real"] = merged[["machine_time", "labor_per_operator"]].max(axis=1)

    # Capacidad = (hours_eff * stations) / cycle_time_real
    merged["capacity"] = 0.0
    mask = merged["cycle_time_real"] > 0
    merged.loc[mask, "capacity"] = (hours_eff * merged.loc[mask, "stations"]) / merged.loc[mask, "cycle_time_real"]

    cap_per_process = dict(zip(merged["process"].tolist(), merged["capacity"].tolist()))
    bottleneck_process = min(cap_per_process, key=cap_per_process.get)
    cap_total = float(cap_per_process[bottleneck_process])

    # Debug
    debug_rows = []
    for _, r in merged.iterrows():
        debug_rows.append({
            "process": r["process"],
            "stations": float(r["stations"]),
            "operators": float(r["operators"]),
            "machine_time": float(r["machine_time"]),
            "labor_time": float(r["labor_time"]),
            "labor_per_operator": float(r["labor_per_operator"]),
            "cycle_time_real": float(r["cycle_time_real"]),
            "hours_eff": float(hours_eff),
            "capacity": float(r["capacity"]),
        })

    return {
        "line": line,
        "model": model,
        "hours_effective": hours_eff,
        "capacity_total": cap_total,
        "bottleneck": bottleneck_process,
        "capacity_per_process": cap_per_process,
        "debug": debug_rows,
        "note": "",
    }


# =========================
# Análisis planta
# =========================
def analyze_plant(
    plant_id: int,
    plant: PlantParams,
    line_to_model: Dict[str, str],
    demand_by_model: Dict[str, float],
    data: Dict[str, pd.DataFrame],
) -> pd.DataFrame:

    rows = []
    for line, model in line_to_model.items():
        res = compute_line_capacity(
            plant=plant,
            plant_id=plant_id,
            line=line,
            model=model,
            times_df=data["times"],
            stations_df=data["stations"],
        )

        demand = float(demand_by_model.get(model, 0.0))
        cap = float(res["capacity_total"])
        saturation = (demand / cap) if cap > 0 else None
        deficit = max(0.0, demand - cap) if cap > 0 else demand

        rows.append({
            "line": str(line).strip().upper(),
            "model": str(model).strip().upper(),
            "demand": demand,
            "capacity_total": cap,
            "saturation_pct": None if saturation is None else 100.0 * saturation,
            "deficit": deficit,
            "bottleneck": res["bottleneck"],
            "note": res["note"],
        })

    return pd.DataFrame(rows)


# ============================================================
# Scheduler V2 — núcleo puro
# Sin Streamlit · Sin session_state · Sin app.py
# ============================================================

def _normalizar_prioridad(valor) -> tuple:
    """Retorna (prioridad_int, aviso | None).

    Reglas:
    - None / NaN / vacío           → 9999 + aviso
    - texto no numérico            → 9999 + aviso
    - float decimal no entero (1.5)→ 9999 + aviso
    - float entero (1.0, 2.0)      → acepta como int equivalente
    - negativo                     → 9999 + aviso
    - 0                            → 0   + aviso suave
    - positivo                     → valor
    """
    # 1. None / NaN explícito
    try:
        if pd.isna(valor):
            return 9999, "prioridad vacía, proyecto enviado al final de la cola"
    except (TypeError, ValueError):
        pass
    # 2. Parseo a float
    try:
        f = float(str(valor).strip())
    except (ValueError, TypeError):
        return 9999, f"prioridad no numérica ({valor!r}), proyecto enviado al final de la cola"
    # 3. Float NaN resultante de parseo (p.ej. float("nan"))
    try:
        if pd.isna(f):
            return 9999, "prioridad vacía, proyecto enviado al final de la cola"
    except (TypeError, ValueError):
        pass
    # 4. Conversión a int (rechaza inf y NaN)
    try:
        p = int(f)
    except (ValueError, OverflowError):
        return 9999, f"prioridad no numérica ({valor!r}), proyecto enviado al final de la cola"
    # 5. Float decimal no entero (1.5, "1.9" → f=1.9, p=1, f!=p)
    if f != p:
        return 9999, (
            f"prioridad decimal ({valor!r}) no admitida, "
            "proyecto enviado al final de la cola"
        )
    # 6. Negativo
    if p < 0:
        return 9999, (
            f"prioridad negativa ({p}) no admitida, "
            "proyecto enviado al final de la cola"
        )
    # 7. Cero
    if p == 0:
        return 0, "prioridad 0 inusual"
    return p, None


def _to_int_safe(valor, default: int) -> int:
    """Convierte valor a int; retorna default si no es posible."""
    if valor is None:
        return default
    try:
        return int(valor)
    except (ValueError, TypeError):
        return default


def _calc_h_sem(
    horas_total,
    dur: int,
    linea_cfg: dict,
    pid: str,
    warnings_list: list,
) -> tuple:
    """Retorna (h_sem_real, alerta_capacidad). Nunca lanza excepción."""
    if horas_total is None:
        return None, False
    try:
        if pd.isna(horas_total):
            return None, False
    except (TypeError, ValueError):
        pass
    try:
        if str(horas_total).strip() == "":
            return None, False
        h = float(horas_total)
    except (ValueError, TypeError):
        return None, False

    h_sem_real = (h / dur) if dur > 0 else None
    alerta_cap = False
    if h_sem_real is not None:
        cap = linea_cfg.get("capacidad_h_sem")
        if cap is not None:
            try:
                if h_sem_real > float(cap):
                    alerta_cap = True
                    warnings_list.append(
                        f"[{pid}] alerta capacidad: {h_sem_real:.1f} h/sem > "
                        f"capacidad línea {float(cap):.1f} h/sem."
                    )
            except (ValueError, TypeError):
                pass
    return h_sem_real, alerta_cap


def _registrar_calendario(
    calendario: dict,
    intervalos: dict,
    linea: str,
    sem_inicio: int,
    sem_fin: int,
    proyecto_id: str,
) -> None:
    """Actualiza calendario_por_linea e intervalos_por_linea."""
    if linea not in calendario:
        calendario[linea] = {}
    for s in range(sem_inicio, sem_fin + 1):
        calendario[linea].setdefault(s, []).append(proyecto_id)
    intervalos.setdefault(linea, []).append((sem_inicio, sem_fin))


def primer_hueco(
    intervalos: list,
    ini_min: int,
    dur: int,
    horizonte_fin: int,
) -> Optional[int]:
    """
    Primera semana libre donde cabe el proyecto completo dentro del horizonte.

    Garantía: retorna h tal que h + dur - 1 <= horizonte_fin, o None.
    Nunca devuelve un hueco que exceda horizonte_fin.
    """
    if dur <= 0:
        return None
    ocupados = sorted(intervalos, key=lambda x: x[0])
    candidato = ini_min
    for occ_ini, occ_fin in ocupados:
        if candidato + dur - 1 > horizonte_fin:
            return None
        # El proyecto cabe completo antes de que empiece este intervalo
        if candidato + dur - 1 < occ_ini:
            break
        # Hay solapamiento: saltar después del intervalo ocupado
        if candidato <= occ_fin:
            candidato = occ_fin + 1
    if candidato + dur - 1 > horizonte_fin:
        return None
    return candidato


def asignacion_mejor(
    candidatas: list,
    dur: int,
    ent_target: int,
    linea_pref: str,
) -> Optional[Tuple]:
    """
    Elige la mejor (linea_id, sem_inicio) de la lista de candidatas.

    - delta <= 0: llega a tiempo; elige la de mayor delta (más cercana al objetivo).
    - delta > 0: todas tarde; elige la de menor delta.
    - Desempate: línea preferente > posición original > linea_id.
    """
    if not candidatas:
        return None
    scored = [
        (idx, linea_id, sem_inicio, sem_inicio + dur - 1 - ent_target)
        for idx, (linea_id, sem_inicio) in enumerate(candidatas)
    ]
    a_tiempo = [x for x in scored if x[3] <= 0]
    pool = a_tiempo if a_tiempo else scored
    if a_tiempo:
        # Mayor delta entre los <= 0 = más cercano al objetivo sin pasarse
        key = lambda x: (-x[3], x[1] != linea_pref, x[0], x[1])
    else:
        # Menor delta positivo
        key = lambda x: (x[3], x[1] != linea_pref, x[0], x[1])
    best = sorted(pool, key=key)[0]
    return best[1], best[2]


def schedule_proyectos(
    proyectos: list,
    lineas: dict,
    semana_actual: int,
    horizonte_fin: int,
) -> dict:
    """
    Scheduler macro semanal V2. Asignación exclusiva de líneas a proyectos.

    Asume entrada ya validada estructuralmente por _validate_prog_v2().
    No lanza excepciones no controladas. Devuelve resultado auditable.

    Returns:
        dict con claves: asignaciones, excluidos, calendario_por_linea,
        conflictos_criticos, warnings, auditoria_decisiones, kpis.
    """
    # ── Guard horizonte_fin ──────────────────────────────────
    # Sin horizonte válido no hay planificación fiable: retorno temprano controlado.
    try:
        horizonte_fin = int(horizonte_fin)
        if horizonte_fin <= 0:
            raise ValueError(
                f"horizonte_fin debe ser > 0, recibido: {horizonte_fin}"
            )
    except (ValueError, TypeError) as exc:
        n_proy = len(proyectos) if isinstance(proyectos, list) else 0
        return {
            "asignaciones": [], "excluidos": [], "calendario_por_linea": {},
            "conflictos_criticos": [
                {"tipo": "HORIZONTE_FIN_INVALIDO", "detalle": str(exc)}
            ],
            "warnings": [
                f"horizonte_fin inválido, planificación abortada: {exc}"
            ],
            "auditoria_decisiones": [
                "horizonte_fin inválido: planificación abortada."
            ],
            "kpis": {
                "total_proyectos": n_proy, "planificados": 0, "excluidos": 0,
                "firmes": 0, "a_tiempo": 0, "retrasados": 0,
                "conflictos_criticos": 1, "warnings": 1, "pct_a_tiempo": 0.0,
            },
        }

    asignaciones: list = []
    excluidos: list = []
    conflictos_criticos: list = []
    warnings: list = []
    auditoria: list = []
    calendario_por_linea: dict = {}   # linea -> semana -> [proyecto_id, ...]
    intervalos_por_linea: dict = {}   # linea -> [(sem_ini, sem_fin), ...]

    # ── Guard semana_actual ───────────────────────────────────
    try:
        semana_actual = int(semana_actual)
    except (ValueError, TypeError):
        warnings.append(
            f"semana_actual inválida ({semana_actual!r}), usando 1 como valor seguro."
        )
        auditoria.append(
            f"semana_actual inválida ({semana_actual!r}), sustituida por 1."
        )
        semana_actual = 1

    firmes: list = []
    flexibles_raw: list = []

    # ── Pre-validación geométrica (dur) ───────────────────────
    for p in proyectos:
        pid = p.get("proyecto_id", "<sin_id>")
        try:
            dur = int(p.get("dur", 0))
            if dur <= 0:
                raise ValueError("dur <= 0")
        except (ValueError, TypeError):
            excluidos.append({
                "proyecto_id": pid,
                "linea_asignada": None,
                "sem_inicio": None,
                "sem_fin": None,
                "delta_semanas": None,
                "estado": "NO_PLANIFICABLE_GEOMETRICO",
                "uso_alternativa": False,
                "h_sem_real": None,
                "alerta_capacidad": False,
                "motivo": f"duración inválida ({p.get('dur')!r})",
            })
            warnings.append(
                f"[{pid}] duración inválida ({p.get('dur')!r}), enviado a excluidos."
            )
            auditoria.append(f"[{pid}] excluido por duración inválida.")
            continue
        if p.get("firme", False):
            firmes.append(p)
        else:
            flexibles_raw.append(p)

    # ── FASE 1: Colocar FIRMES ────────────────────────────────
    for p in firmes:
        pid = p["proyecto_id"]
        linea = p.get("linea_pref") or ""
        sem_inicio = p.get("ini_min")
        dur = int(p["dur"])

        # Validar que la línea existe
        if not linea or linea not in lineas:
            conflictos_criticos.append({
                "tipo": "FIRME_LINEA_NO_ENCONTRADA",
                "proyecto_id": pid,
                "linea": linea,
                "detalle": f"línea preferente '{linea}' no existe en el catálogo.",
            })
            excluidos.append({
                "proyecto_id": pid,
                "linea_asignada": linea or None,
                "sem_inicio": sem_inicio,
                "sem_fin": None,
                "delta_semanas": None,
                "estado": "NO_PLANIFICABLE_LINEA_NO_ENCONTRADA",
                "uso_alternativa": False,
                "h_sem_real": None,
                "alerta_capacidad": False,
                "motivo": f"línea '{linea}' no existe en el catálogo",
            })
            auditoria.append(f"[{pid}] FIRME excluido: línea '{linea}' no encontrada.")
            continue

        # Validar que tiene inicio y es numérico
        if sem_inicio is None:
            conflictos_criticos.append({
                "tipo": "FIRME_SIN_INICIO",
                "proyecto_id": pid,
                "detalle": "ini_min es None para proyecto FIRME.",
            })
            excluidos.append({
                "proyecto_id": pid,
                "linea_asignada": linea,
                "sem_inicio": None,
                "sem_fin": None,
                "delta_semanas": None,
                "estado": "NO_PLANIFICABLE_GEOMETRICO",
                "uso_alternativa": False,
                "h_sem_real": None,
                "alerta_capacidad": False,
                "motivo": "ini_min es None en proyecto FIRME",
            })
            auditoria.append(f"[{pid}] FIRME excluido: ini_min es None.")
            continue
        try:
            sem_inicio = int(sem_inicio)
        except (ValueError, TypeError):
            raw_ini = p.get("ini_min")
            conflictos_criticos.append({
                "tipo": "FIRME_INI_MIN_INVALIDA",
                "proyecto_id": pid,
                "detalle": f"ini_min no numérica ({raw_ini!r}) en proyecto FIRME.",
            })
            excluidos.append({
                "proyecto_id": pid,
                "linea_asignada": linea,
                "sem_inicio": None,
                "sem_fin": None,
                "delta_semanas": None,
                "estado": "NO_PLANIFICABLE_GEOMETRICO",
                "uso_alternativa": False,
                "h_sem_real": None,
                "alerta_capacidad": False,
                "motivo": f"ini_min no numérica ({raw_ini!r})",
            })
            auditoria.append(
                f"[{pid}] FIRME excluido: ini_min no numérica ({raw_ini!r})."
            )
            continue

        sem_fin = sem_inicio + dur - 1
        modelo = p.get("modelo") or ""
        linea_cfg = lineas[linea]
        modelos_compat = set(linea_cfg.get("modelos_compatibles") or [])

        # Compatibilidad de modelo (solo auditoría; FIRME no se bloquea)
        if modelos_compat and modelo and modelo not in modelos_compat:
            warnings.append(
                f"[{pid}] FIRME: modelo '{modelo}' no compatible con línea '{linea}'. "
                "Planificado igualmente (realidad comprometida)."
            )
            auditoria.append(
                f"[{pid}] modelo '{modelo}' incompatible con '{linea}'; "
                "FIRME planificado sin modificar."
            )

        # Detectar conflictos FIRME-FIRME (registrar, no resolver)
        for occ_ini, occ_fin in list(intervalos_por_linea.get(linea, [])):
            if sem_inicio <= occ_fin and sem_fin >= occ_ini:
                ol_start = max(sem_inicio, occ_ini)
                ol_end = min(sem_fin, occ_fin)
                pids_solapados: set = set()
                for s in range(ol_start, ol_end + 1):
                    pids_solapados.update(
                        calendario_por_linea.get(linea, {}).get(s, [])
                    )
                for pid2 in pids_solapados:
                    conflictos_criticos.append({
                        "tipo": "FIRME_FIRME_SOLAPE",
                        "proyecto_id_1": pid,
                        "proyecto_id_2": pid2,
                        "linea": linea,
                        "detalle": (
                            f"conflicto firme-firme entre {pid} y {pid2} "
                            f"en {linea} S{ol_start}–S{ol_end}."
                        ),
                    })
                    auditoria.append(
                        f"[{pid}] conflicto firme-firme con {pid2} "
                        f"en {linea} S{ol_start}–S{ol_end}."
                    )

        # Warning si excede horizonte_fin (planificado igualmente)
        if sem_fin > horizonte_fin:
            warnings.append(
                f"[{pid}] FIRME excede horizonte visible: "
                f"termina S{sem_fin} > S{horizonte_fin}."
            )
            auditoria.append(
                f"[{pid}] FIRME planificado pero excede horizonte_fin "
                f"({sem_fin} > {horizonte_fin})."
            )

        _et = p.get("ent_target")
        if _et is None:
            ent_target = sem_fin
        else:
            try:
                ent_target = int(_et)
            except (ValueError, TypeError):
                warnings.append(
                    f"[{pid}] ent_target inválida ({_et!r}), usando sem_fin ({sem_fin})."
                )
                ent_target = sem_fin
        h_sem_real, alerta_cap = _calc_h_sem(
            p.get("horas_total"), dur, linea_cfg, pid, warnings
        )

        _registrar_calendario(
            calendario_por_linea, intervalos_por_linea,
            linea, sem_inicio, sem_fin, pid,
        )
        asignaciones.append({
            "proyecto_id": pid,
            "linea_asignada": linea,
            "sem_inicio": sem_inicio,
            "sem_fin": sem_fin,
            "delta_semanas": sem_fin - ent_target,
            "estado": "FIRME",
            "uso_alternativa": False,
            "h_sem_real": h_sem_real,
            "alerta_capacidad": alerta_cap,
            "motivo": "proyecto FIRME, posición fija",
        })
        auditoria.append(
            f"[{pid}] FIRME colocado en {linea} S{sem_inicio}–S{sem_fin}."
        )

    # ── FASE 2: Normalizar prioridades FLEXIBLES ──────────────
    flexibles: list = []
    for p in flexibles_raw:
        pid = p["proyecto_id"]
        p_int, aviso = _normalizar_prioridad(p.get("prioridad"))
        if aviso:
            warnings.append(f"[{pid}] {aviso}")
            auditoria.append(f"[{pid}] {aviso}")
        flexibles.append({**p, "_prioridad_efectiva": p_int})

    # ── FASE 3: Ordenar FLEXIBLES ─────────────────────────────
    flexibles.sort(key=lambda p: (
        p["_prioridad_efectiva"],
        _to_int_safe(p.get("ent_target"), horizonte_fin),
        _to_int_safe(p.get("ini_min"), 0),
        p.get("proyecto_id", ""),
    ))

    # ── FASE 4: Planificar FLEXIBLES ──────────────────────────
    for p in flexibles:
        pid = p["proyecto_id"]
        dur = int(p["dur"])
        raw_ini = p.get("ini_min")
        try:
            ini_efectivo = max(
                int(raw_ini) if raw_ini is not None else semana_actual,
                semana_actual,
            )
        except (ValueError, TypeError):
            warnings.append(
                f"[{pid}] ini_min inválida ({raw_ini!r}), "
                f"usando semana_actual ({semana_actual})."
            )
            auditoria.append(
                f"[{pid}] ini_min inválida ({raw_ini!r}), sustituida por semana_actual."
            )
            ini_efectivo = semana_actual

        raw_et = p.get("ent_target")
        try:
            ent_target = int(raw_et) if raw_et is not None else horizonte_fin
        except (ValueError, TypeError):
            warnings.append(
                f"[{pid}] ent_target inválida ({raw_et!r}), "
                f"usando horizonte_fin ({horizonte_fin})."
            )
            auditoria.append(
                f"[{pid}] ent_target inválida ({raw_et!r}), sustituida por horizonte_fin."
            )
            ent_target = horizonte_fin
        modelo = p.get("modelo") or ""
        linea_pref = p.get("linea_pref") or ""
        lineas_alt = list(p.get("lineas_alt") or [])
        horas_total = p.get("horas_total")

        # Construir lista de líneas candidatas (deduplicada, ordenada)
        candidatas_ids: list = []
        seen: set = set()
        for lid in ([linea_pref] + lineas_alt):
            if not lid:
                continue
            if lid in seen:
                auditoria.append(f"[{pid}] alternativa duplicada '{lid}' ignorada.")
                continue
            seen.add(lid)
            if lid not in lineas:
                auditoria.append(
                    f"[{pid}] línea '{lid}' no existe en catálogo, ignorada."
                )
                warnings.append(f"[{pid}] línea '{lid}' no encontrada en catálogo.")
                continue
            linea_cfg = lineas[lid]
            modelos_compat = set(linea_cfg.get("modelos_compatibles") or [])
            if modelos_compat and modelo and modelo not in modelos_compat:
                auditoria.append(
                    f"[{pid}] modelo '{modelo}' no compatible con '{lid}', descartada."
                )
                continue
            candidatas_ids.append(lid)

        if not candidatas_ids:
            excluidos.append({
                "proyecto_id": pid,
                "linea_asignada": None,
                "sem_inicio": None,
                "sem_fin": None,
                "delta_semanas": None,
                "estado": "NO_PLANIFICABLE_SIN_LINEA",
                "uso_alternativa": False,
                "h_sem_real": None,
                "alerta_capacidad": False,
                "motivo": "sin línea compatible en el catálogo",
            })
            auditoria.append(f"[{pid}] excluido: sin línea compatible.")
            continue

        # Buscar primer hueco en cada línea candidata
        opciones: list = []
        for lid in candidatas_ids:
            hueco = primer_hueco(
                intervalos=intervalos_por_linea.get(lid, []),
                ini_min=ini_efectivo,
                dur=dur,
                horizonte_fin=horizonte_fin,
            )
            if hueco is not None:
                opciones.append((lid, hueco))
                auditoria.append(f"[{pid}] '{lid}': primer hueco libre S{hueco}.")
            else:
                auditoria.append(
                    f"[{pid}] '{lid}': sin hueco dentro del horizonte."
                )

        if not opciones:
            excluidos.append({
                "proyecto_id": pid,
                "linea_asignada": None,
                "sem_inicio": None,
                "sem_fin": None,
                "delta_semanas": None,
                "estado": "NO_PLANIFICABLE_SIN_HUECO_HORIZONTE",
                "uso_alternativa": False,
                "h_sem_real": None,
                "alerta_capacidad": False,
                "motivo": "sin hueco dentro del horizonte",
            })
            auditoria.append(
                f"[{pid}] excluido: sin hueco en ninguna línea dentro del horizonte."
            )
            continue

        linea_elegida, sem_inicio = asignacion_mejor(
            opciones, dur, ent_target, linea_pref
        )
        sem_fin = sem_inicio + dur - 1
        delta = sem_fin - ent_target
        uso_alt = linea_elegida != linea_pref

        linea_cfg = lineas[linea_elegida]
        h_sem_real, alerta_cap = _calc_h_sem(
            horas_total, dur, linea_cfg, pid, warnings
        )

        if delta <= 0:
            estado = "A_TIEMPO_ALTERNATIVA" if uso_alt else "A_TIEMPO"
        else:
            estado = "RETRASADO"
            auditoria.append(
                f"[{pid}] retraso {delta} sem (target S{ent_target}, fin S{sem_fin})."
            )

        if uso_alt:
            auditoria.append(
                f"[{pid}] asignado a alternativa '{linea_elegida}' "
                f"(preferente '{linea_pref}' sin hueco o incompatible)."
            )

        _registrar_calendario(
            calendario_por_linea, intervalos_por_linea,
            linea_elegida, sem_inicio, sem_fin, pid,
        )
        asignaciones.append({
            "proyecto_id": pid,
            "linea_asignada": linea_elegida,
            "sem_inicio": sem_inicio,
            "sem_fin": sem_fin,
            "delta_semanas": delta,
            "estado": estado,
            "uso_alternativa": uso_alt,
            "h_sem_real": h_sem_real,
            "alerta_capacidad": alerta_cap,
            "motivo": f"planificado S{sem_inicio}–S{sem_fin} en '{linea_elegida}'",
        })
        auditoria.append(
            f"[{pid}] → '{linea_elegida}' S{sem_inicio}–S{sem_fin} [{estado}]."
        )

    # ── KPIs ──────────────────────────────────────────────────
    n_asg = len(asignaciones)
    n_a_tiempo = sum(
        1 for a in asignaciones
        if a["estado"] in ("A_TIEMPO", "A_TIEMPO_ALTERNATIVA")
    )
    kpis = {
        "total_proyectos": len(proyectos),
        "planificados": n_asg,
        "excluidos": len(excluidos),
        "firmes": sum(1 for a in asignaciones if a["estado"] == "FIRME"),
        "a_tiempo": n_a_tiempo,
        "retrasados": sum(1 for a in asignaciones if a["estado"] == "RETRASADO"),
        "conflictos_criticos": len(conflictos_criticos),
        "warnings": len(warnings),
        "pct_a_tiempo": round(100 * n_a_tiempo / n_asg, 1) if n_asg > 0 else 0.0,
    }

    return {
        "asignaciones": asignaciones,
        "excluidos": excluidos,
        "calendario_por_linea": calendario_por_linea,
        "conflictos_criticos": conflictos_criticos,
        "warnings": warnings,
        "auditoria_decisiones": auditoria,
        "kpis": kpis,
    }
