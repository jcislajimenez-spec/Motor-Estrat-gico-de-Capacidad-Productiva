import streamlit as st
import pandas as pd
import os

DATA_DIR = "data"

# -----------------------------
# CARGA DE DATOS
# -----------------------------
@st.cache_data
def load_csv(name):
    return pd.read_csv(os.path.join(DATA_DIR, name))

def save_csv(df, name):
    df.to_csv(os.path.join(DATA_DIR, name), index=False)

times_df = load_csv("models_process_times.csv")
stations_df = load_csv("lines_process_stations.csv")
compat_df = load_csv("compatibility.csv")

lines = sorted(stations_df["line"].unique())
models = sorted(times_df["model"].unique())

# -----------------------------
# SIDEBAR – PARÁMETROS FIJOS
# -----------------------------
st.sidebar.title("Parámetros de planificación")

hours = st.sidebar.number_input("Horas por semana", value=43.0)
turns = st.sidebar.number_input("Turnos", value=1, step=1)
availability = st.sidebar.slider("Disponibilidad", 0.0, 1.0, 1.0)
efficiency = st.sidebar.slider("Eficiencia", 0.0, 1.0, 1.0)

hours_eff = hours * turns * availability * efficiency

# -----------------------------
# TÍTULO
# -----------------------------
st.title("Capacidad Industrial – Versión A")
st.caption("Inputs tipo crema → Resultados tipo azul. Sin Excel. Uso interno.")

tabs = st.tabs(["📊 Planificación", "⚙️ Configuración (Power User)", "📈 Resultados"])

# =========================================================
# PLANIFICACIÓN
# =========================================================
with tabs[0]:
    st.subheader("Selección de modelo por línea")

    line_model = {}
    line_demand = {}

    for line in lines:
        compat_models = compat_df[
            (compat_df["line"] == line) & (compat_df["compatible"] == 1)
        ]["model"].tolist()

        col1, col2 = st.columns(2)
        with col1:
            model = st.selectbox(
                f"Modelo ({line})",
                compat_models,
                key=f"model_{line}"
            )
        with col2:
            demand = st.number_input(
                f"Demanda ({model})",
                min_value=0.0,
                step=1.0,
                key=f"demand_{line}"
            )

        line_model[line] = model
        line_demand[line] = demand

# =========================================================
# CONFIGURACIÓN POWER USER
# =========================================================
with tabs[1]:
    st.subheader("Configuración de estaciones y operarios por línea/proceso")

    st.dataframe(stations_df, use_container_width=True)

    if st.button("💾 Guardar estaciones / operarios"):
        save_csv(stations_df, "lines_process_stations.csv")
        st.success("Guardado")

    st.divider()
    st.subheader("Compatibilidad modelo ↔ línea")

    edited = []
    for line in lines:
        with st.expander(f"Línea {line}", expanded=True):
            cols = st.columns(len(models))
            for i, model in enumerate(models):
                row = compat_df[
                    (compat_df["line"] == line) &
                    (compat_df["model"] == model)
                ]
                checked = bool(row.iloc[0]["compatible"]) if not row.empty else False
                value = cols[i].checkbox(model, value=checked, key=f"{line}_{model}")
                edited.append({
                    "line": line,
                    "model": model,
                    "compatible": 1 if value else 0
                })

    if st.button("💾 Guardar compatibilidades"):
        save_csv(pd.DataFrame(edited), "compatibility.csv")
        st.success("Compatibilidades guardadas")

# =========================================================
# RESULTADOS
# =========================================================
with tabs[2]:
    st.subheader("Resultados de capacidad")
    st.caption(f"Horas efectivas planta: {hours_eff:.2f} h/semana")

    summary_rows = []
    detail = {}

    for line, model in line_model.items():
        demand = line_demand[line]

        t = times_df[times_df["model"] == model]
        s = stations_df[stations_df["line"] == line]

        merged = pd.merge(s, t, on="process")
        merged["capacity"] = (
            hours_eff *
            merged["stations"] *
            merged["operators_per_station"]
        ) / merged["cycle_time"]

        cap_total = merged["capacity"].min()
        bottleneck = merged.loc[merged["capacity"].idxmin(), "process"]

        summary_rows.append({
            "line": line,
            "model": model,
            "demand": demand,
            "capacity_total": cap_total,
            "saturation_pct": 100 * demand / cap_total if cap_total > 0 else 0,
            "deficit": max(0, demand - cap_total),
            "bottleneck": bottleneck
        })

        detail[line] = (merged, cap_total, bottleneck, demand)

    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

    st.divider()
    st.subheader("🔍 Detalle fino por línea y subproceso")

    for line, (df, cap, bottleneck, demand) in detail.items():
        with st.expander(
            f"{line} — Capacidad máx: {cap:.2f} uds/sem | "
            f"Cuello: {bottleneck} | Demanda: {demand:.2f}"
        ):
            st.dataframe(
                df[["process", "stations", "operators_per_station", "cycle_time", "capacity"]],
                use_container_width=True
            )
