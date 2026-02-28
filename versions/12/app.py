import streamlit as st
import pandas as pd
import os

DATA_DIR = "data"

# =========================================================
# UTILIDADES CSV
# =========================================================
@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA_DIR, name))
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
    return df

def save_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(os.path.join(DATA_DIR, name), index=False)

# =========================================================
# SIDEBAR – PARÁMETROS DE PLANIFICACIÓN
# =========================================================
st.sidebar.title("Parámetros de planificación")
hours = st.sidebar.number_input("Horas por semana", value=43.0)
turns = st.sidebar.number_input("Turnos", value=1, step=1)
availability = st.sidebar.slider("Disponibilidad", 0.0, 1.0, 1.0)
efficiency = st.sidebar.slider("Eficiencia", 0.0, 1.0, 1.0)
hours_eff = hours * turns * availability * efficiency

# =========================================================
# TÍTULO
# =========================================================
st.title("Capacidad Industrial – Versión A")
st.caption("Inputs tipo crema → Resultados tipo azul. Sin Excel. Uso interno.")

tabs = st.tabs(["📊 Planificación", "⚙️ Configuración (Power User)", "📈 Resultados"])

# =========================================================
# PLANIFICACIÓN
# =========================================================
with tabs[0]:
    times_df = load_csv("models_process_times.csv")
    stations_df = load_csv("lines_process_stations.csv")
    compat_df = load_csv("compatibility.csv")
    models_df = load_csv("models.csv")

    active_models = models_df[models_df["active"] == 1]["model"].tolist()
    lines = sorted(stations_df["line"].unique())

    st.subheader("Selección de modelo por línea")

    for line in lines:
        compat_models = compat_df[
            (compat_df["line"] == line) &
            (compat_df["model"].isin(active_models)) &
            (compat_df["compatible"] == 1)
        ]["model"].tolist()

        if not compat_models:
            st.warning(f"No hay modelos compatibles activos para {line}")
            continue

        c1, c2 = st.columns(2)
        with c1:
            st.selectbox(f"Modelo ({line})", compat_models, key=f"model_{line}")
        with c2:
            st.number_input(f"Demanda ({line})", min_value=0.0, step=1.0, key=f"demand_{line}")

# =========================================================
# CONFIGURACIÓN POWER USER
# =========================================================
with tabs[1]:

    # ---- mensajes persistentes
    for key, msg in {
        "models_saved": "Modelos guardados",
        "times_saved": "Tiempos guardados",
        "stations_saved": "Estaciones / operarios guardados",
        "compat_saved": "Compatibilidades guardadas"
    }.items():
        if st.session_state.get(key):
            st.success(msg)
            st.session_state[key] = False

    # ---- cargar datos
    models_df = load_csv("models.csv")
    times_df = load_csv("models_process_times.csv")
    stations_df = load_csv("lines_process_stations.csv")
    compat_df = load_csv("compatibility.csv")

    # =====================================================
    # 0️⃣ GESTIÓN DE MODELOS
    # =====================================================
    st.subheader("Gestión de modelos")

    edited_models = st.data_editor(
        models_df,
        num_rows="dynamic",
        use_container_width=True
    )

    if st.button("💾 Guardar modelos"):
        edited_models["active"] = pd.to_numeric(
            edited_models["active"], errors="coerce"
        ).fillna(0).astype(int)

        save_csv(edited_models, "models.csv")
        st.session_state["models_saved"] = True
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # =====================================================
    # 1️⃣ TIEMPOS POR MODELO Y PROCESO
    # =====================================================
    st.subheader("Tiempos por modelo y proceso")

    edited_times = st.data_editor(
        times_df,
        num_rows="fixed",
        use_container_width=True
    )

    if st.button("💾 Guardar tiempos"):
        edited_times["cycle_time"] = pd.to_numeric(
            edited_times["cycle_time"], errors="coerce"
        ).fillna(0)

        save_csv(edited_times, "models_process_times.csv")
        st.session_state["times_saved"] = True
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # =====================================================
    # 2️⃣ ESTACIONES Y OPERARIOS
    # =====================================================
    st.subheader("Configuración de estaciones y operarios")

    edited_stations = st.data_editor(
        stations_df,
        num_rows="fixed",
        use_container_width=True
    )

    if st.button("💾 Guardar estaciones / operarios"):
        edited_stations["stations"] = pd.to_numeric(
            edited_stations["stations"], errors="coerce"
        ).fillna(0).astype(int)

        edited_stations["operators_per_station"] = pd.to_numeric(
            edited_stations["operators_per_station"], errors="coerce"
        ).fillna(0).astype(int)

        save_csv(edited_stations, "lines_process_stations.csv")
        st.session_state["stations_saved"] = True
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # =====================================================
    # 3️⃣ COMPATIBILIDAD MODELO ↔ LÍNEA
    # =====================================================
    st.subheader("Compatibilidad modelo ↔ línea")

    lines = sorted(stations_df["line"].unique())
    active_models = models_df[models_df["active"] == 1]["model"].tolist()

    edited = []
    for line in lines:
        with st.expander(f"Línea {line}", expanded=True):
            cols = st.columns(len(active_models))
            for i, model in enumerate(active_models):
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
        st.session_state["compat_saved"] = True
        st.cache_data.clear()
        st.rerun()

# =========================================================
# RESULTADOS
# =========================================================
with tabs[2]:
    times_df = load_csv("models_process_times.csv")
    stations_df = load_csv("lines_process_stations.csv")

    st.subheader("Resultados de capacidad")
    st.caption(f"Horas efectivas planta: {hours_eff:.2f} h/semana")

    summary = []
    detail = {}

    for line in stations_df["line"].unique():
        mk = f"model_{line}"
        dk = f"demand_{line}"
        if mk not in st.session_state:
            continue

        model = st.session_state[mk]
        demand = float(st.session_state.get(dk, 0))

        t = times_df[times_df["model"] == model]
        s = stations_df[stations_df["line"] == line]

        df = pd.merge(s, t, on="process")

        df["capacity"] = (
            hours_eff *
            df["stations"] *
            df["operators_per_station"]
        ) / df["cycle_time"]

        cap = df["capacity"].min()
        bottleneck = df.loc[df["capacity"].idxmin(), "process"]

        summary.append({
            "line": line,
            "model": model,
            "demand": demand,
            "capacity_total": cap,
            "saturation_pct": 100 * demand / cap if cap > 0 else 0,
            "deficit": max(0, demand - cap),
            "bottleneck": bottleneck
        })

        detail[line] = (df, cap, bottleneck, demand)

    st.dataframe(pd.DataFrame(summary), use_container_width=True)

    st.divider()
    st.subheader("🔍 Detalle fino por línea y subproceso")

    for line, (df, cap, bottleneck, demand) in detail.items():
        with st.expander(
            f"{line} — Capacidad máx: {cap:.2f} | Cuello: {bottleneck} | Demanda: {demand}"
        ):
            st.dataframe(
                df[["process", "stations", "operators_per_station", "cycle_time", "capacity"]],
                use_container_width=True
            )

