from __future__ import annotations
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List


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
    if "compatible" in compat.columns:
        compat["compatible"] = _to_num(compat["compatible"]).fillna(0).astype(int)

    # Limpieza de filas rotas
    times = times.dropna(subset=["model", "process", "cycle_time"])
    stations = stations.dropna(subset=["line", "process", "stations"])

    return {"times": times, "stations": stations, "compat": compat}


# =========================
# Compatibilidades
# =========================
def compatible_models_for_line(compat_df: pd.DataFrame, line: str) -> List[str]:
    line = str(line).strip().upper()
    sub = compat_df[(compat_df["line"] == line) & (compat_df["compatible"].astype(int) == 1)]
    return sorted(sub["model"].unique().tolist())


# =========================
# Cálculo de capacidad
# =========================
def compute_line_capacity(
    plant: PlantParams,
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

    # ✅ Operarios fijos por proceso (para validar contra Excel)
    OPERARIOS_POR_PROCESO = {
        "PREM": 1,
        "ML": 2,
        "PTBI": 2,
    }

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
    t = times_df.copy()
    s = stations_df.copy()

    t["process"] = _norm_str(t["process"]).replace(PROCESS_ALIASES)
    s["process"] = _norm_str(s["process"]).replace(PROCESS_ALIASES)

    # Filtrado por modelo y línea
    t = t[t["model"].astype(str).str.strip().str.upper() == model][["process", "cycle_time"]].copy()
    s = s[s["line"].astype(str).str.strip().str.upper() == line][["process", "stations"]].copy()

    # Asegurar numéricos
    t["cycle_time"] = _to_num(t["cycle_time"])
    s["stations"] = _to_num(s["stations"])

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
    merged["operators"] = merged["process"].map(OPERARIOS_POR_PROCESO).fillna(1).astype(float)

    # ✅ Fórmula Excel (tal cual)
    merged["capacity"] = (hours_eff * merged["stations"] * merged["operators"]) / merged["cycle_time"]

    cap_per_process = dict(zip(merged["process"].tolist(), merged["capacity"].tolist()))
    bottleneck_process = min(cap_per_process, key=cap_per_process.get)
    cap_total = float(cap_per_process[bottleneck_process])

    # Debug útil (para que veas exactamente qué está usando)
    debug_rows = []
    for _, r in merged.iterrows():
        debug_rows.append({
            "process": r["process"],
            "stations": float(r["stations"]),
            "operators": float(r["operators"]),
            "cycle_time": float(r["cycle_time"]),
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
    plant: PlantParams,
    line_to_model: Dict[str, str],
    demand_by_model: Dict[str, float],
    data: Dict[str, pd.DataFrame],
) -> pd.DataFrame:

    rows = []
    for line, model in line_to_model.items():
        res = compute_line_capacity(
            plant=plant,
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


