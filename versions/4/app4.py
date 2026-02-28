import streamlit as st
import pandas as pd
from dataclasses import dataclass
from pathlib import Path

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Capacidad Industrial – Versión A",
    layout="wide",
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

TIMES_FILE = DATA_DIR / "models_process_times.csv"
STATIONS_FILE = DATA_DIR / "lines_process_stations.csv"

# =========================
# DATA CLASSES
# =========================
@dataclass
class PlantParams:
    hours_per_week: float
    turns: int
    availability: float
    efficiency: float

    @property
    def hours_effective(self) -> float:
        return self.hours_per_week * self.turns * self.availability * self.efficiency


# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_times():
    return pd.read_csv(TIMES_FILE)

@st.cache_data
def load_stations():
    return pd.read_csv(STATIONS_FILE)


# =========================
# CAPACITY ENGINE
# =========================
def compute_line_capacity(plant, line, model, times_df, stations_df):
    hours_eff = plant.hours_effective

    t = times_df[times_df["model"] == model][["process", "cycle_time"]]
    s = stations_df[stations_df["line"] == line][
        ["process", "stations", "operators_per_station"]
    ]

    merged = pd.merge(s, t, on="process", how="inner")

    if merged.empty:
        return None

    merged["capacity"] = (
        hours_eff
        * merged["stations"]
        * merged["operators_per_station"]
        / merged["cycle_time"]
    )

    cap_per_process = dict(zip(merged["process"], merged["capacity"]))
    bottleneck = min(cap_per_process, key=cap_per_process.get)
    cap_total = cap_per_process[bottleneck]

    return {
        "capacity_total": cap_total,
        "bottleneck": bottleneck,
        "capacity_per_process": cap_per_process,
    }


# =========================
# UI – TITLE
# =========================
st.title("Capacidad Industrial – Versión A")
st.caption("Inputs tipo crema → Resultados tipo azul. Sin Excel. Uso interno.")

tabs = st.tabs(["📊 Planificación", "⚙️ Configuración (Power User)", "📈 Resultados"])


# =========================
# TAB 1 – PLANIFICACIÓN
# =========================
with tabs[0]:
    st.subheader("Parámetros de planificación")

    colL, colR = st.columns([1, 3])

    with colL:
        hours = st.number_input("Horas por semana", 1.0, 168.0, 43.0)
        turns = st.number_input("Turnos", 1, 3, 1)
        availability = st.slider("Disponibilidad", 0.0, 1.0, 1.0, 0.01)
        efficiency = st.slider("Eficiencia", 0.0, 1.0, 1.0, 0.01)

    plant = PlantParams(hours, turns, availability, efficiency)

    st.divider()
    st.subheader("Selección de modelo por línea")

    times_df = load_times()
    stations_df = load_stations()

    lines = sorted(stations_df["line"].unique())
    models = sorted(times_df["model"].unique())

    line_to_model = {}
    demand_by_model = {}

    for line in lines:
        c1, c2, c3 = st.columns([1, 2, 2])
        with c1:
            st.markdown(f"**{line}**")
        with c2:
            model = st.selectbox(
                f"Modelo ({line})",
                models,
                key=f"model_{line}",
            )
        with c3:
            demand = st.number_input(
                f"Demanda ({model})",
                min_value=0.0,
                step=1.0,
                key=f"demand_{line}",
            )

        line_to_model[line] = model
        demand_by_model[model] = demand


# =========================
# TAB 2 – POWER USER
# =========================
with tabs[1]:
    st.subheader("Configuración de estaciones y operarios por línea / proceso")

    stations_df_edit = stations_df.copy()

    edited = st.data_editor(
        stations_df_edit,
        num_rows="dynamic",
        use_container_width=True,
    )

    if st.button("💾 Guardar configuración (CSV)"):
        edited.to_csv(STATIONS_FILE, index=False)
        st.cache_data.clear()
        st.success("Configuración guardada correctamente.")


# =========================
# TAB 3 – RESULTS
# =========================
with tabs[2]:
    st.subheader("Resultados de capacidad")

    results = []
    details = []

    for line, model in line_to_model.items():
        res = compute_line_capacity(
            plant,
            line,
            model,
            times_df,
            stations_df,
        )
        if res is None:
            continue

        demand = demand_by_model.get(model, 0.0)
        cap = res["capacity_total"]

        results.append({
            "line": line,
            "model": model,
            "demand": demand,
            "capacity_total": cap,
            "saturation_pct": (demand / cap * 100) if cap > 0 else 0,
            "deficit": max(0.0, demand - cap),
            "bottleneck": res["bottleneck"],
        })

        details.append({
            "line": line,
            "model": model,
            "demand": demand,
            "capacity_total": cap,
            "bottleneck": res["bottleneck"],
            "per_process": res["capacity_per_process"],
        })

    results_df = pd.DataFrame(results)
    st.dataframe(results_df, use_container_width=True)

    st.divider()
    st.subheader("🔎 Detalle fino por línea y subproceso")

    for d in details:
        with st.expander(
            f"{d['line']} — Modelo: {d['model']} | "
            f"Capacidad máx: {d['capacity_total']:.2f} uds/sem | "
            f"Cuello: {d['bottleneck']} | "
            f"Demanda: {d['demand']:.2f}"
        ):
            df = pd.DataFrame(
                [
                    {"process": p, "capacity": c}
                    for p, c in d["per_process"].items()
                ]
            )
            st.dataframe(df, use_container_width=True)
