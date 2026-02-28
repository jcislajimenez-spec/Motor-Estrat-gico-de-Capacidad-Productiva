import streamlit as st
import pandas as pd
from engine import (
    PlantParams,
    load_data,
    compatible_models_for_line,
    analyze_plant,
)

# =========================
# Configuración básica
# =========================

st.set_page_config(
    page_title="Capacity Planner",
    layout="wide",
)

DATA_DIR = "data"

# =========================
# Carga de datos
# =========================

@st.cache_data
def load_all_data():
    return load_data(DATA_DIR)

data = load_all_data()

# =========================
# SIDEBAR — Inputs usuario
# =========================

st.sidebar.header("Parámetros de planificación")

hours_per_week = st.sidebar.number_input(
    "Horas por semana",
    min_value=1.0,
    value=43.0,
)

turns = st.sidebar.number_input(
    "Turnos",
    min_value=1,
    value=1,
    step=1,
)

availability = st.sidebar.slider(
    "Disponibilidad",
    min_value=0.0,
    max_value=1.0,
    value=1.0,
)

efficiency = st.sidebar.slider(
    "Eficiencia",
    min_value=0.0,
    max_value=1.0,
    value=1.0,
)

plant = PlantParams(
    hours_per_week=hours_per_week,
    turns=turns,
    availability=availability,
    efficiency=efficiency,
)

# =========================
# Tabs
# =========================

tab_plan, tab_config, tab_results = st.tabs(
    ["📊 Planificación", "⚙️ Configuración (Power User)", "📈 Resultados"]
)

# =========================
# TAB 1 — Planificación
# =========================

with tab_plan:
    st.subheader("Selección de modelo por línea")

    line_to_model = {}
    demand_by_model = {}

    lines = sorted(data["stations"]["line"].unique().tolist())

    for line in lines:
        models = compatible_models_for_line(data["compat"], line)

        col1, col2, col3 = st.columns([2, 2, 2])

        with col1:
            st.markdown(f"**Línea {line}**")

        with col2:
            model = st.selectbox(
                f"Modelo ({line})",
                options=models,
                key=f"model_{line}",
            )

        with col3:
            demand = st.number_input(
                f"Demanda ({model})",
                min_value=0.0,
                value=0.0,
                key=f"demand_{line}",
            )

        line_to_model[line] = model
        demand_by_model[model] = demand

# =========================
# TAB 2 — Configuración Power User
# =========================

with tab_config:
    st.subheader("Configuración de estaciones y operarios por línea/proceso")

    stations_df = data["stations"].copy()

    edited_df = st.data_editor(
        stations_df,
        use_container_width=True,
        num_rows="dynamic",
    )

    if st.button("💾 Guardar configuración (CSV)"):
        edited_df.to_csv(
            f"{DATA_DIR}/lines_process_stations.csv",
            index=False,
        )
        st.success("Configuración guardada. Recarga la app (F5).")

# =========================
# TAB 3 — Resultados
# =========================

with tab_results:
    st.subheader("Resultados de capacidad")

    results_df = analyze_plant(
        plant=plant,
        line_to_model=line_to_model,
        demand_by_model=demand_by_model,
        data=data,
    )

    st.dataframe(results_df, use_container_width=True)
