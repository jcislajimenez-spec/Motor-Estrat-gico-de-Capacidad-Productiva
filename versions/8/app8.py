import streamlit as st
import pandas as pd
import os

DATA_DIR = "data"

# -----------------------------
# CARGA / GUARDADO
# -----------------------------
@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA_DIR, name))

    # Normaliza strings (evita espacios raros en line/model/process)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
    return df

def save_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(os.path.join(DATA_DIR, name), index=False)

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
    # Cargar siempre desde función (cacheada), para que al limpiar cache + rerun se refresque
    times_df = load_csv("models_process_times.csv")
    stations_df = load_csv("lines_process_stations.csv")
    compat_df = load_csv("compatibility.csv")

    lines = sorted(stations_df["line"].unique())
    models = sorted(times_df["model"].unique())

    st.subheader("Selección de modelo por línea")

    line_model = {}
    line_demand = {}

    for line in lines:
        compat_models = compat_df[
            (compat_df["line"] == line) & (compat_df["compatible"].astype(int) == 1)
        ]["model"].tolist()

        # Si no hay modelos compatibles, evitamos que reviente el select
        if not compat_models:
            st.warning(f"No hay modelos compatibles activos para {line}. Revisa Configuración (Power User).")
            continue

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
    # Mensajes “verdes” persistentes tras rerun (flags)
    if st.session_state.get("stations_saved"):
        st.success("Guardado")
        st.session_state["stations_saved"] = False

    if st.session_state.get("compat_saved"):
        st.success("Compatibilidades guardadas")
        st.session_state["compat_saved"] = False

    # Cargar siempre desde función (cacheada)
    times_df = load_csv("models_process_times.csv")
    stations_df = load_csv("lines_process_stations.csv")
    compat_df = load_csv("compatibility.csv")

    lines = sorted(stations_df["line"].unique())
    models = sorted(times_df["model"].unique())

    st.subheader("Configuración de estaciones y operarios por línea/proceso")

    edited_stations = st.data_editor(
        stations_df,
        num_rows="fixed",
        use_container_width=True
    )

    if st.button("💾 Guardar estaciones / operarios"):
        # Asegurar tipos numéricos antes de guardar
        out = edited_stations.copy()
        if "stations" in out.columns:
            out["stations"] = pd.to_numeric(out["stations"], errors="coerce").fillna(0).astype(int)
        if "operators_per_station" in out.columns:
            out["operators_per_station"] = pd.to_numeric(out["operators_per_station"], errors="coerce").fillna(0).astype(int)

        save_csv(out, "lines_process_stations.csv")

        # IMPORTANTE: refrescar datos al instante
        st.session_state["stations_saved"] = True
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("Compatibilidad modelo ↔ línea")

    edited = []
    for line in lines:
        with st.expander(f"Línea {line}", expanded=True):
            cols = st.columns(len(models))
            for i, model in enumerate(models):
                row = compat_df[(compat_df["line"] == line) & (compat_df["model"] == model)]
                checked = bool(int(row.iloc[0]["compatible"])) if not row.empty else False
                value = cols[i].checkbox(model, value=checked, key=f"{line}_{model}")
                edited.append({"line": line, "model": model, "compatible": 1 if value else 0})

    if st.button("💾 Guardar compatibilidades"):
        save_csv(pd.DataFrame(edited), "compatibility.csv")

        # Refrescar para que Planificación vea el cambio sin “Rerun” manual
        st.session_state["compat_saved"] = True
        st.cache_data.clear()
        st.rerun()

# =========================================================
# RESULTADOS
# =========================================================
with tabs[2]:
    # Cargar SIEMPRE desde función (cacheada)
    # (si has guardado algo, ya hicimos clear+rerun -> esto ya vendrá fresco)
    times_df = load_csv("models_process_times.csv")
    stations_df = load_csv("lines_process_stations.csv")

    st.subheader("Resultados de capacidad")
    st.caption(f"Horas efectivas planta: {hours_eff:.2f} h/semana")

    summary_rows = []
    detail = {}

    # Recuperar lo que el usuario seleccionó en Planificación
    # (si no hay líneas seleccionadas por falta de compatibilidades, no rompemos)
    if "model_LINE_A" not in st.session_state and "model_LINE_B" not in st.session_state and "model_LINE_C" not in st.session_state:
        st.info("Selecciona modelos en la pestaña Planificación para ver resultados.")
    else:
        # reconstruir line_model/line_demand desde session_state
        # para no depender de variables de otra pestaña
        lines = sorted(stations_df["line"].unique())
        line_model = {}
        line_demand = {}
        for line in lines:
            mk = f"model_{line}"
            dk = f"demand_{line}"
            if mk in st.session_state:
                line_model[line] = st.session_state[mk]
                line_demand[line] = float(st.session_state.get(dk, 0.0))

        for line, model in line_model.items():
            demand = line_demand.get(line, 0.0)

            t = times_df[times_df["model"] == model]
            s = stations_df[stations_df["line"] == line]

            merged = pd.merge(s, t, on="process")

            merged["stations"] = pd.to_numeric(merged["stations"], errors="coerce").fillna(0)
            merged["operators_per_station"] = pd.to_numeric(merged["operators_per_station"], errors="coerce").fillna(0)
            merged["cycle_time"] = pd.to_numeric(merged["cycle_time"], errors="coerce").fillna(0)

            merged["capacity"] = (
                hours_eff * merged["stations"] * merged["operators_per_station"]
            ) / merged["cycle_time"].replace(0, pd.NA)

            merged["capacity"] = merged["capacity"].fillna(0.0)

            cap_total = float(merged["capacity"].min()) if not merged.empty else 0.0
            bottleneck = merged.loc[merged["capacity"].idxmin(), "process"] if (not merged.empty and cap_total > 0) else None

            summary_rows.append({
                "line": line,
                "model": model,
                "demand": demand,
                "capacity_total": cap_total,
                "saturation_pct": (100 * demand / cap_total) if cap_total > 0 else 0,
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
