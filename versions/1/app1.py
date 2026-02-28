import streamlit as st
import pandas as pd

from engine import (
    PlantParams,
    load_data,
    compatible_models_for_line,
    analyze_plant,
    compute_line_capacity,
)

st.set_page_config(page_title="Capacidad Industrial – Versión A", layout="wide")

DATA_DIR = "data"


@st.cache_data
def _load():
    return load_data(DATA_DIR)


data = _load()

# =========================
# CABECERA
# =========================
st.title("Capacidad Industrial – Versión A (líneas + modelos + compatibilidades)")
st.caption("Inputs tipo 'crema' → Resultados tipo 'azul'. Sin Excel. Uso interno.")

# =========================
# ESTADO
# =========================
if "plant_params" not in st.session_state:
    st.session_state.plant_params = {
        "hours_per_week": 40.0,
        "turns": 2,
        "availability": 0.95,
        "efficiency": 0.85,
    }

if "demand_table" not in st.session_state:
    models = sorted(data["times"]["model"].unique().tolist())
    st.session_state.demand_table = pd.DataFrame({"model": models, "demand": [0.0] * len(models)})

if "line_to_model" not in st.session_state:
    lines = sorted(data["stations"]["line"].unique().tolist())
    # Si una línea no tiene compatibilidades, evitamos crash
    tmp = {}
    for ln in lines:
        compat_models = compatible_models_for_line(data["compat"], ln)
        tmp[ln] = compat_models[0] if compat_models else ""
    st.session_state.line_to_model = tmp

tabs = st.tabs(["Inputs (crema)", "Configuración (power user)", "Resultados (azul)"])

# =========================
# TAB 1: INPUTS (CREMA)
# =========================
with tabs[0]:
    st.subheader("Inputs (crema)")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.session_state.plant_params["hours_per_week"] = st.number_input(
            "Horas/semana (base)",
            min_value=1.0,
            max_value=200.0,
            value=float(st.session_state.plant_params["hours_per_week"]),
            step=1.0,
        )
    with c2:
        st.session_state.plant_params["turns"] = st.number_input(
            "Turnos",
            min_value=1,
            max_value=3,
            value=int(st.session_state.plant_params["turns"]),
            step=1,
        )
    with c3:
        st.session_state.plant_params["availability"] = st.number_input(
            "Disponibilidad (0–1)",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.plant_params["availability"]),
            step=0.01,
        )
    with c4:
        st.session_state.plant_params["efficiency"] = st.number_input(
            "Eficiencia (0–1)",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.plant_params["efficiency"]),
            step=0.01,
        )

    st.markdown("---")

    st.subheader("Selección de modelo por línea")
    lines = sorted(data["stations"]["line"].unique().tolist())

    for ln in lines:
        compat_models = compatible_models_for_line(data["compat"], ln)
        if not compat_models:
            st.warning(f"No hay modelos compatibles definidos para la línea {ln}. Revisa 'compatibility.csv'.")
            continue

        current = st.session_state.line_to_model.get(ln, compat_models[0])
        st.session_state.line_to_model[ln] = st.selectbox(
            f"{ln} → Modelo",
            options=compat_models,
            index=compat_models.index(current) if current in compat_models else 0,
            key=f"sel_{ln}",
        )

    st.markdown("---")

    st.subheader("Demanda PMP por modelo (editable)")
    st.caption("Edita la columna demand. Esa demanda se aplica al modelo cuando lo selecciones en una línea.")
    st.session_state.demand_table = st.data_editor(
        st.session_state.demand_table,
        num_rows="fixed",
        use_container_width=True,
    )

    st.info("Cuando pases a la pestaña 'Resultados (azul)', se calculará con estos inputs.")

# =========================
# TAB 2: CONFIG (POWER USER)
# =========================
with tabs[1]:
    st.subheader("Configuración (power user)")
    st.caption("Aquí se mantienen tiempos, estaciones y compatibilidades. Usuario normal NO debería tocar esto.")

    st.markdown("### Tiempos por modelo y proceso (`models_process_times.csv`)")
    times_edit = st.data_editor(data["times"], use_container_width=True)
    if st.button("Guardar tiempos (CSV)"):
        times_edit.to_csv(f"{DATA_DIR}/models_process_times.csv", index=False)
        st.cache_data.clear()
        st.success("Guardado. Recarga la página (F5) para aplicar.")

    st.markdown("### Estaciones por línea y proceso (`lines_process_stations.csv`)")
    stations_edit = st.data_editor(data["stations"], use_container_width=True)
    if st.button("Guardar estaciones (CSV)"):
        stations_edit.to_csv(f"{DATA_DIR}/lines_process_stations.csv", index=False)
        st.cache_data.clear()
        st.success("Guardado. Recarga la página (F5) para aplicar.")

    st.markdown("### Compatibilidad modelo–línea (`compatibility.csv`)")
    compat_edit = st.data_editor(data["compat"], use_container_width=True)
    if st.button("Guardar compatibilidades (CSV)"):
        compat_edit.to_csv(f"{DATA_DIR}/compatibility.csv", index=False)
        st.cache_data.clear()
        st.success("Guardado. Recarga la página (F5) para aplicar.")

# =========================
# TAB 3: RESULTADOS (AZUL)
# =========================
with tabs[2]:
    st.subheader("Resultados (azul)")

    plant = PlantParams(
        hours_per_week=float(st.session_state.plant_params["hours_per_week"]),
        turns=int(st.session_state.plant_params["turns"]),
        availability=float(st.session_state.plant_params["availability"]),
        efficiency=float(st.session_state.plant_params["efficiency"]),
    )

    demand_by_model = {
        str(r["model"]).strip(): float(r["demand"])
        for _, r in st.session_state.demand_table.iterrows()
    }

    # Recalcular con datos actuales de disco/cache
    data_live = load_data(DATA_DIR)

    res_df = analyze_plant(
        plant=plant,
        line_to_model=st.session_state.line_to_model,
        demand_by_model=demand_by_model,
        data=data_live,
    )

    st.markdown(f"**Horas efectivas (planta):** {plant.hours_effective:.2f} h/semana")
    st.dataframe(res_df, use_container_width=True)

    # =========================
    # C) DETALLE POR LÍNEA + SUBPROCESO (CON ENCABEZADO “BONITO”)
    # =========================
    st.markdown("---")
    st.markdown("## 🔎 Detalle fino por línea y subproceso")
    st.caption("Aquí ves el desglose real por subproceso. El cuello de botella es el subproceso con menor capacidad.")

    # Para que el orden sea consistente con la tabla resumen, iteramos sobre res_df
    for _, row in res_df.iterrows():
        ln = str(row["line"])
        model = str(row["model"])
        dmd = float(row["demand"]) if row["demand"] is not None else 0.0
        cap_total = float(row["capacity_total"]) if row["capacity_total"] is not None else 0.0
        bottleneck = row["bottleneck"]

        # Encabezado “molón” por línea
        header = (
            f"**{ln}** — Modelo: `{model}`  |  "
            f"Capacidad máx: **{cap_total:.2f} uds/sem**  |  "
            f"Cuello: **{bottleneck}**  |  "
            f"Demanda: **{dmd:.2f} uds/sem**"
        )

        with st.expander(header, expanded=False):
            detail = compute_line_capacity(
                plant=plant,
                line=ln,
                model=model,
                times_df=data_live["times"],
                stations_df=data_live["stations"],
            )

            if float(detail.get("capacity_total", 0.0)) <= 0:
                st.warning(detail.get("note", "") or "No se pudo calcular detalle para esta línea/modelo.")
                continue

            cap_pp = pd.DataFrame(
                {
                    "process": list(detail["capacity_per_process"].keys()),
                    "capacity_uds_sem": list(detail["capacity_per_process"].values()),
                }
            ).sort_values("capacity_uds_sem", ascending=True)

            # Resumen “compacto” dentro también, por si alguien lo abre y no mira el header
            st.markdown(
                f"**Resumen:** Capacidad máx **{detail['capacity_total']:.2f}** uds/sem · "
                f"Cuello **{detail['bottleneck']}** · "
                f"Demanda **{dmd:.2f}** uds/sem"
            )

            st.dataframe(cap_pp, use_container_width=True)
