import os
import streamlit as st
import pandas as pd
from PIL import Image


st.set_page_config(
    page_title="Planificador de Capacidad",
    layout="wide"
)

# --- Cargar logo ---
logo = Image.open("assets/ingeteam_logo.jpg")
st.sidebar.image(logo, use_container_width=True)

st.markdown("""
<style>
/* Fondo general */
.main {
    background-color: #FFFFFF;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #FFFFFF;
}

/* Títulos principales */
h1, h2, h3 {
    color: #A6192E;
    font-family: "Trade Gothic", sans-serif;
    font-weight: bold;
}

/* Texto general */
body, p, div {
    color: #000000;
    font-family: "Trade Gothic", sans-serif;
}

/* Subtítulos y textos secundarios */
.small-text {
    color: #63666A;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-weight: bold;
    color: #63666A;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #A6192E;
    border-bottom: 3px solid #A6192E;
}

/* Tabla */
thead tr th {
    background-color: #F5F5F5;
    color: #63666A;
    font-weight: bold;
}

/* Saturaciones en rojo corporativo */
.red-text {
    color: #A6192E;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

DATA_DIR = "data"

# =========================================================
# CSV IO (robusto para Windows/acentos)
# =========================================================
@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, name)
    # Intento UTF-8 (incl. BOM), y si falla, latin1 (muy común en Excel/Windows)
    for enc in ("utf-8-sig", "utf-8", "latin1"):
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except UnicodeDecodeError:
            df = None
    if df is None:
        # último recurso: que reviente con mensaje claro
        df = pd.read_csv(path)

    # Limpieza suave
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
    return df


def save_csv(df: pd.DataFrame, name: str) -> None:
    path = os.path.join(DATA_DIR, name)
    # Guardamos SIEMPRE como utf-8-sig para compatibilidad con Excel
    df.to_csv(path, index=False, encoding="utf-8-sig")


def ensure_int(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    return out


# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(page_title="Capacidad Industrial – Versión A", layout="wide")

st.title("Capacidad Industrial – Versión A (líneas + modelos + compatibilidades)")
st.caption("Inputs tipo 'crema' → Resultados tipo azul. Sin Excel. Uso interno.")

# =========================================================
# SIDEBAR – PARÁMETROS (SIEMPRE VISIBLES)
# =========================================================
st.sidebar.header("Parámetros de planificación")

hours_week = st.sidebar.number_input("Horas por semana", min_value=0.0, value=43.0, step=0.5)
shifts = st.sidebar.number_input("Turnos", min_value=1, value=1, step=1)
availability = st.sidebar.slider("Disponibilidad", 0.0, 1.0, 1.0, 0.01)
efficiency = st.sidebar.slider("Eficiencia", 0.0, 1.0, 1.0, 0.01)

st.sidebar.divider()
days_open_year = st.sidebar.number_input("Días abiertos al año", min_value=1, value=250, step=1)
days_open_week = st.sidebar.number_input("Días abiertos por semana", min_value=1, max_value=7, value=5, step=1)

weeks_equiv = days_open_year / max(days_open_week, 1)
hours_eff = hours_week * shifts * availability * efficiency

st.sidebar.caption(f"Horas efectivas planta: **{hours_eff:.2f} h/semana**")
st.sidebar.caption(f"Semanas equivalentes: **{weeks_equiv:.2f} sem/año**")

# =========================================================
# CARGA DATOS
# =========================================================
models_df = load_csv("models.csv")
times_df = load_csv("models_process_times.csv")
stations_df = load_csv("lines_process_stations.csv")
compat_df = load_csv("compatibility.csv")

# Normalización mínima
models_df["model"] = models_df["model"].astype(str).str.strip()
times_df["model"] = times_df["model"].astype(str).str.strip()
stations_df["line"] = stations_df["line"].astype(str).str.strip()
compat_df["line"] = compat_df["line"].astype(str).str.strip()
compat_df["model"] = compat_df["model"].astype(str).str.strip()

models_df = ensure_int(models_df, ["active"])
compat_df = ensure_int(compat_df, ["compatible"])
stations_df = ensure_int(stations_df, ["stations", "operators_per_station"])

# Modelos activos (lista oficial de la app)
active_models = models_df.loc[models_df["active"] == 1, "model"].tolist()

# Líneas disponibles (derivadas de stations_df)
lines = sorted(stations_df["line"].unique().tolist())

# =========================================================
# TABS
# =========================================================
tabs = st.tabs(["📊 Planificación", "⚙️ Configuración (Power User)", "📈 Resultados", "🧭 Capacidad según mix"])

# =========================================================
# 1) PLANIFICACIÓN
# =========================================================
with tabs[0]:
    st.subheader("Selección de modelo por línea")

    # Construimos un “catálogo” de compatibilidad: por línea → lista de modelos permitidos
    compat_active = compat_df[(compat_df["compatible"] == 1) & (compat_df["model"].isin(active_models))].copy()
    allowed_by_line = compat_active.groupby("line")["model"].apply(list).to_dict()

    # Session state para selections
    if "line_model" not in st.session_state:
        st.session_state.line_model = {}
    if "line_demand" not in st.session_state:
        st.session_state.line_demand = {}

    colL, colR = st.columns([1.1, 1.0], gap="large")

    with colL:
        st.markdown("### Selección")
        for line in lines:
            allowed = allowed_by_line.get(line, [])
            if not allowed:
                st.info(f"{line}: sin modelos compatibles activos (revisa compatibilidades/modelos).")
                continue

            default_model = st.session_state.line_model.get(line, allowed[0])
            if default_model not in allowed:
                default_model = allowed[0]

            m = st.selectbox(
                f"Modelo ({line})",
                options=allowed,
                index=allowed.index(default_model),
                key=f"sel_model_{line}"
            )
            st.session_state.line_model[line] = m

    with colR:
        st.markdown("### Demanda (UDS/SEM)")
        for line in lines:
            model = st.session_state.line_model.get(line)
            if not model:
                continue
            d = st.number_input(
                f"Demanda ({line} – {model})",
                min_value=0.0,
                value=float(st.session_state.line_demand.get(line, 0.0)),
                step=1.0,
                key=f"demand_{line}",
            )
            st.session_state.line_demand[line] = d

# =========================================================
# 2) CONFIGURACIÓN (POWER USER)
# =========================================================
with tabs[1]:
    st.subheader("Configuración (power user)")
    st.caption("Aquí se mantienen modelos, tiempos, estaciones y compatibilidades. Usuario normal NO debería tocar esto.")

    # --- A) Gestión de modelos (checkbox)
    st.markdown("## Gestión de modelos (models.csv)")

    models_editor = models_df.copy()
    models_editor["active"] = models_editor["active"].astype(int).clip(0, 1).astype(bool)

    edited_models = st.data_editor(
        models_editor,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "active": st.column_config.CheckboxColumn("active", help="Modelo activo (aparece en la app).")
        }
    )

    if st.button("💾 Guardar modelos"):
        out = edited_models.copy()
        out["model"] = out["model"].astype(str).str.strip()
        out["description"] = out["description"].astype(str).str.strip()
        out["active"] = out["active"].astype(bool).astype(int)
        save_csv(out, "models.csv")
        st.session_state["models_saved"] = True
        st.cache_data.clear()
        st.rerun()

    if st.session_state.get("models_saved"):
        st.success("Modelos guardados")
        st.session_state["models_saved"] = False

    st.divider()

    # --- B) Tiempos por modelo y proceso
    st.markdown("## Tiempos por modelo y proceso (models_process_times.csv)")

    edited_times = st.data_editor(
        times_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "cycle_time": st.column_config.NumberColumn("cycle_time", help="Horas por unidad (HH/ud) en ese proceso.")
        }
    )

    if st.button("💾 Guardar tiempos"):
        out = edited_times.copy()
        out["model"] = out["model"].astype(str).str.strip()
        out["process"] = out["process"].astype(str).str.strip()
        out["cycle_time"] = pd.to_numeric(out["cycle_time"], errors="coerce").fillna(0.0)
        save_csv(out, "models_process_times.csv")
        st.session_state["times_saved"] = True
        st.cache_data.clear()
        st.rerun()

    if st.session_state.get("times_saved"):
        st.success("Tiempos guardados")
        st.session_state["times_saved"] = False

    st.divider()

    # --- C) Estaciones / operarios por línea y proceso
    st.markdown("## Configuración de estaciones y operarios por línea/proceso (lines_process_stations.csv)")

    edited_stations = st.data_editor(
        stations_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "stations": st.column_config.NumberColumn("stations", min_value=0, step=1),
            "operators_per_station": st.column_config.NumberColumn("operators_per_station", min_value=0, step=1),
        }
    )

    if st.button("💾 Guardar estaciones / operarios"):
        out = edited_stations.copy()
        out["line"] = out["line"].astype(str).str.strip()
        out["process"] = out["process"].astype(str).str.strip()
        out["stations"] = pd.to_numeric(out["stations"], errors="coerce").fillna(0).astype(int)
        out["operators_per_station"] = pd.to_numeric(out["operators_per_station"], errors="coerce").fillna(0).astype(int)
        save_csv(out, "lines_process_stations.csv")
        st.session_state["stations_saved"] = True
        st.cache_data.clear()
        st.rerun()

    if st.session_state.get("stations_saved"):
        st.success("Guardado")
        st.session_state["stations_saved"] = False

    st.divider()

    # --- D) Compatibilidad modelo ↔ línea (checkbox)
    st.markdown("## Compatibilidad modelo ↔ línea (compatibility.csv)")

    # Sólo mostramos modelos existentes en models.csv (da igual activos o no: compat se define aquí)
    all_models = sorted(models_df["model"].astype(str).str.strip().unique().tolist())
    all_lines = sorted(stations_df["line"].astype(str).str.strip().unique().tolist())

    # Matriz editable por línea
    edited_rows = []
    for line in all_lines:
        st.markdown(f"### Línea {line}")
        with st.expander(f"Línea {line}", expanded=True):
            cols = st.columns(3)
            for i, m in enumerate(all_models):
                current = compat_df[
                    (compat_df["line"] == line) & (compat_df["model"] == m)
                ]
                cur_val = 0
                if not current.empty:
                    cur_val = int(current.iloc[0]["compatible"])

                checked = cols[i % 3].checkbox(m, value=bool(cur_val), key=f"compat_{line}_{m}")
                edited_rows.append({"line": line, "model": m, "compatible": 1 if checked else 0})

    if st.button("💾 Guardar compatibilidades"):
        out = pd.DataFrame(edited_rows)
        save_csv(out, "compatibility.csv")
        st.session_state["compat_saved"] = True
        st.cache_data.clear()
        st.rerun()

    if st.session_state.get("compat_saved"):
        st.success("Compatibilidades guardadas")
        st.session_state["compat_saved"] = False

# =========================================================
# 3) RESULTADOS
# =========================================================
def compute_line_detail(line: str, model: str) -> tuple[pd.DataFrame, str, float]:
    """
    Devuelve:
    - merged detail DF con capacity por proceso
    - bottleneck process (min capacity)
    - capacity_total_week (uds/sem) (cap del cuello)
    """
    t = times_df[times_df["model"] == model].copy()
    s = stations_df[stations_df["line"] == line].copy()
    merged = pd.merge(s, t, on="process", how="inner")

    if merged.empty:
        return merged, "", 0.0

    merged["stations"] = pd.to_numeric(merged["stations"], errors="coerce").fillna(0)
    merged["operators_per_station"] = pd.to_numeric(merged["operators_per_station"], errors="coerce").fillna(0)
    merged["cycle_time"] = pd.to_numeric(merged["cycle_time"], errors="coerce").fillna(0.0)

    # Capacidad uds/sem por proceso (con tu fórmula ya validada)
    # capacity = hours_eff * stations * operators / cycle_time
    merged["capacity"] = 0.0
    mask = merged["cycle_time"] > 0
    merged.loc[mask, "capacity"] = (hours_eff * merged.loc[mask, "stations"] * merged.loc[mask, "operators_per_station"]) / merged.loc[mask, "cycle_time"]

    # Si no hay ninguna capacidad válida (todo 0 o NaN), evitamos idxmin() (da ValueError)
    if merged["capacity"].dropna().empty:
        return merged, "", 0.0

    bottleneck_row = merged.loc[merged["capacity"].idxmin()]
    bottleneck_proc = str(bottleneck_row["process"])
    cap_week = float(bottleneck_row["capacity"])

    return merged, bottleneck_proc, cap_week


def capacity_hours_for_output(merged: pd.DataFrame, output_units: float) -> float:
    """
    Capacidad (h/SEM) y (h/AÑO) = **horas-hombre (HH)** necesarias para producir `output_units`.

    En TU modelo:
    - `cycle_time` está en **HH/ud**
    - NO se multiplica por operarios (si no, duplicas HH)

    Regla:
        HH_total = sum_procesos( output_units * cycle_time )
    """
    if merged is None or merged.empty or output_units <= 0:
        return 0.0

    m = merged.copy()
    m["cycle_time"] = pd.to_numeric(m.get("cycle_time", 0.0), errors="coerce").fillna(0.0)

    hours_proc = output_units * m["cycle_time"]
    hours_proc = pd.to_numeric(hours_proc, errors="coerce").fillna(0.0)

    return float(hours_proc.sum())


with tabs[2]:
    st.subheader("Resultados de capacidad")
    st.caption(f"Horas efectivas planta: {hours_eff:.2f} h/semana")

    summary_rows = []
    detail_by_line = {}

    for line in lines:
        model = st.session_state.line_model.get(line)
        if not model:
            continue
        demand_week = float(st.session_state.line_demand.get(line, 0.0))

        merged, bottleneck_proc, cap_week = compute_line_detail(line, model)

        saturation = 0.0
        deficit = 0.0
        if cap_week > 0:
            saturation = (demand_week / cap_week) * 100.0
            deficit = max(0.0, demand_week - cap_week)

        demand_year = demand_week * weeks_equiv
        cap_year = cap_week * weeks_equiv

        # Capacidad en horas: Capacidad (uds) * carga total del modelo (suma de cycle_time por procesos)
        # (En Excel: Capacidad hrs/sem = Capacidad uds/sem * SUM(cycle_time_model))

        # Demanda en horas: Demanda (uds) * carga total del modelo (suma de cycle_time por procesos)
        _tmod = times_df[times_df["model"] == model].copy()
        _tmod["cycle_time"] = pd.to_numeric(_tmod.get("cycle_time", 0.0), errors="coerce").fillna(0.0)
        total_cycle_time_model = float(_tmod["cycle_time"].sum())

        cap_hours_week = cap_week * total_cycle_time_model
        cap_hours_year = cap_hours_week * weeks_equiv


        dem_hours_week = demand_week * total_cycle_time_model
        dem_hours_year = dem_hours_week * weeks_equiv

        summary_rows.append({
            "line": line,
            "model": model,
            "Demanda (UDS/SEM)": demand_week,
            "Capacidad (UDS/SEM)": cap_week,
            "Saturación (%)": saturation,
            "Déficit (UDS/SEM)": deficit,
            "bottleneck": bottleneck_proc,
            "Demanda (UDS/AÑO)": demand_year,
            "Capacidad (UDS/AÑO)": cap_year,
            "Demanda (h/SEM)": dem_hours_week,
            "Capacidad (h/SEM)": cap_hours_week,
            "Demanda (h/AÑO)": dem_hours_year,
            "Capacidad (h/AÑO)": cap_hours_year,
        })

        detail_by_line[line] = (model, demand_week, bottleneck_proc, merged)

    summary_df = pd.DataFrame(summary_rows)

    # --- Fila TOTAL (sumatorio de demanda/capacidad en uds y horas) ---
    if not summary_df.empty:
        _sum_cols = [
            "Demanda (UDS/SEM)", "Capacidad (UDS/SEM)",
            "Demanda (UDS/AÑO)", "Capacidad (UDS/AÑO)",
            "Demanda (h/SEM)", "Capacidad (h/SEM)",
            "Demanda (h/AÑO)", "Capacidad (h/AÑO)",
        ]
        for c in _sum_cols:
            if c in summary_df.columns:
                summary_df[c] = pd.to_numeric(summary_df[c], errors="coerce")

        total_row = {c: float(summary_df[c].sum(skipna=True)) if c in summary_df.columns else 0.0 for c in _sum_cols}
        total_row.update({
            "line": "TOTAL",
            "model": "",
            "Saturación (%)": float("nan"),
            "Déficit (UDS/SEM)": float("nan"),
            "bottleneck": "",
        })

        # Asegurar que existen las columnas de texto aunque estén vacías en casos raros
        for c in ["line", "model", "bottleneck"]:
            if c not in summary_df.columns:
                summary_df[c] = ""

        summary_df = pd.concat([summary_df, pd.DataFrame([total_row])], ignore_index=True)

    def style_summary(df: pd.DataFrame):
        styled = df.copy()

        fmt_cols_1 = [
            "Demanda (UDS/SEM)", "Capacidad (UDS/SEM)", "Déficit (UDS/SEM)",
            "Demanda (UDS/AÑO)", "Capacidad (UDS/AÑO)",
            "Demanda (h/SEM)", "Capacidad (h/SEM)",
            "Demanda (h/AÑO)", "Capacidad (h/AÑO)"
        ]
        for c in fmt_cols_1:
            if c in styled.columns:
                styled[c] = pd.to_numeric(styled[c], errors="coerce")

        styled["Saturación (%)"] = pd.to_numeric(styled["Saturación (%)"], errors="coerce")

        s = styled.style.format({
            **{c: "{:.1f}" for c in fmt_cols_1 if c in styled.columns},
            "Saturación (%)": "{:.1f} %"
        })

        def sat_color(val):
            try:
                v = float(val)
            except:
                return ""
            return "color: red; font-weight: 700;" if v >= 100 else "color: green; font-weight: 700;"

        s = s.applymap(sat_color, subset=["Saturación (%)"])
        s = s.applymap(lambda _: "color: red; font-weight: 700;", subset=["bottleneck"])

        # Fila TOTAL: negrita + tamaño mayor (como en Excel del ejemplo)
        if "line" in styled.columns:
            def _style_total(row):
                if str(row.get("line", "")) == "TOTAL":
                    return ["font-weight: 800; font-size: 18px;"] * len(row)
                return [""] * len(row)

            s = s.apply(_style_total, axis=1)

        return s

    if summary_df.empty:
        st.info("No hay resultados aún. Selecciona modelos/demanda en Planificación.")
    else:
        st.dataframe(style_summary(summary_df), use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("## 🔎 Detalle fino por línea y subproceso")
        st.caption("Desglose real por subproceso. El cuello de botella es el subproceso con menor capacidad.")

        for line, (model, demand_week, bottleneck_proc, merged) in detail_by_line.items():
            cap_week = 0.0
            if merged is not None and not merged.empty:
                cap_week = float(merged["capacity"].min())

            header = f"{line} — Modelo: {model} | Capacidad máx: {cap_week:.2f} uds/sem | Cuello: {bottleneck_proc} | Demanda: {demand_week:.2f} uds/sem"
            with st.expander(header, expanded=False):
                if merged is None or merged.empty:
                    st.warning("No hay datos suficientes (revisa estaciones o tiempos).")
                else:
                    show = merged[["process", "stations", "operators_per_station", "cycle_time", "capacity"]].copy()
                    show["capacity"] = pd.to_numeric(show["capacity"], errors="coerce").fillna(0.0)

                    def hl_bottleneck(row):
                        if str(row["process"]) == str(bottleneck_proc):
                            return ["background-color: #ffe6e6; font-weight: 700; color: #b00000;"] * len(row)
                        return [""] * len(row)

                    st.dataframe(
                        show.style
                            .format({"capacity": "{:.3f}"})
                            .apply(hl_bottleneck, axis=1),
                        use_container_width=True,
                        hide_index=True
                    )


# =========================================================
# 4) CAPACIDAD SEGÚN MIX (FASE 1)
# =========================================================
    import plotly.express as px
    import plotly.graph_objects as go

    st.divider()
    st.markdown("## 📊 Representación gráfica de Demanda vs Capacidad")

    if not summary_df.empty:

        # Quitamos TOTAL para gráficos por línea
        df_plot = summary_df[summary_df["line"] != "TOTAL"].copy()

        # =========================
        # 1️⃣ SEMANAL – UNIDADES
        # =========================
        st.markdown("### 🔹 Demanda vs Capacidad – UDS/SEM")

        fig1 = go.Figure()
        fig1.add_bar(
            x=df_plot["line"],
            y=df_plot["Demanda (UDS/SEM)"],
            name="Demanda",
            marker_color="#A6192E"
        )
        fig1.add_bar(
            x=df_plot["line"],
            y=df_plot["Capacidad (UDS/SEM)"],
            name="Capacidad",
            marker_color="green"
        )
        fig1.update_layout(barmode="group")
        st.plotly_chart(fig1, use_container_width=True)

        # =========================
        # 2️⃣ SEMANAL – HORAS (CLAVE)
        # =========================
        st.markdown("### 🔴 Demanda vs Capacidad – h/SEM (CRÍTICO)")

        fig2 = go.Figure()
        fig2.add_bar(
            x=df_plot["line"],
            y=df_plot["Demanda (h/SEM)"],
            name="Demanda",
            marker_color="#A6192E"
        )
        fig2.add_bar(
            x=df_plot["line"],
            y=df_plot["Capacidad (h/SEM)"],
            name="Capacidad",
            marker_color="green"
        )
        fig2.update_layout(barmode="group")
        st.plotly_chart(fig2, use_container_width=True)

        # =========================
        # 3️⃣ ANUAL – UNIDADES
        # =========================
        st.markdown("### 🔹 Demanda vs Capacidad – UDS/AÑO")

        fig3 = go.Figure()
        fig3.add_bar(
            x=df_plot["line"],
            y=df_plot["Demanda (UDS/AÑO)"],
            name="Demanda",
            marker_color="#A6192E"
        )
        fig3.add_bar(
            x=df_plot["line"],
            y=df_plot["Capacidad (UDS/AÑO)"],
            name="Capacidad",
            marker_color="green"
        )
        fig3.update_layout(barmode="group")
        st.plotly_chart(fig3, use_container_width=True)

        # =========================
        # 4️⃣ ANUAL – HORAS (CLAVE)
        # =========================
        st.markdown("### 🔴 Demanda vs Capacidad – h/AÑO (CRÍTICO)")

        fig4 = go.Figure()
        fig4.add_bar(
            x=df_plot["line"],
            y=df_plot["Demanda (h/AÑO)"],
            name="Demanda",
            marker_color="#A6192E"
        )
        fig4.add_bar(
            x=df_plot["line"],
            y=df_plot["Capacidad (h/AÑO)"],
            name="Capacidad",
            marker_color="green"
        )
        fig4.update_layout(barmode="group")
        st.plotly_chart(fig4, use_container_width=True)

        # =========================
        # 5️⃣ VISIÓN GLOBAL TOTAL (HORAS SEMANALES)
        # =========================
        st.markdown("## 🧠 Visión global planta – h/SEM")

        total_row = summary_df[summary_df["line"] == "TOTAL"]

        if not total_row.empty:
            fig_total = go.Figure()
            fig_total.add_bar(
                x=["TOTAL"],
                y=total_row["Demanda (h/SEM)"],
                name="Demanda Total",
                marker_color="#A6192E"
            )
            fig_total.add_bar(
                x=["TOTAL"],
                y=total_row["Capacidad (h/SEM)"],
                name="Capacidad Total",
                marker_color="green"
            )
            fig_total.update_layout(barmode="group")
            st.plotly_chart(fig_total, use_container_width=True)
with tabs[3]:
    st.subheader("Capacidad según mix")
    st.info(
        "La planta produce **horas configurables**.\n"
        "La capacidad no es un valor fijo, sino un **rango estructural** determinado por el mix posible de modelos en cada línea.\n"
        "Aquí se muestran los valores **Máximo / Promedio / Mínimo** por planta y por línea, en unidades y en horas (semana y año)."
    )

    # Compatibilidades activas (mismos criterios que en Planificación)
    compat_active = compat_df[(compat_df.get("compatible", 0) == 1) & (compat_df["model"].isin(active_models))].copy()
    allowed_by_line = compat_active.groupby("line")["model"].apply(list).to_dict()

    # Carga total por modelo (SUM(cycle_time) = HH/ud total del modelo)
    _t = times_df.copy()
    _t["cycle_time"] = pd.to_numeric(_t.get("cycle_time", 0.0), errors="coerce").fillna(0.0)
    cycle_by_model = _t.groupby("model")["cycle_time"].sum().to_dict()

    line_stats_rows = []

    # Guardamos capacidades por (línea, modelo) para reutilizar en NIVEL 3 (Fase 2)
    capH_line_model = {}  # horas/semana estructurales por línea y modelo
    capU_line_model = {}  # uds/semana por línea y modelo (no imprescindible, pero útil)


    for line in lines:
        models_allowed = allowed_by_line.get(line, [])
        if not models_allowed:
            continue

        capU_vals = []
        capH_vals = []
        capU_year_vals = []
        capH_year_vals = []
        model_for_capU = []
        model_for_capH = []

        for m in models_allowed:
            merged, _bn, cap_week = compute_line_detail(line, m)
            cap_week = float(cap_week) if cap_week else 0.0
            if cap_week <= 0:
                continue

            w_m = float(cycle_by_model.get(m, 0.0))
            cap_h_week = cap_week * w_m

            # Guardar para Nivel 3
            capH_line_model[(line, m)] = float(cap_h_week)
            capU_line_model[(line, m)] = float(cap_week)


            capU_vals.append(cap_week)
            capH_vals.append(cap_h_week)
            capU_year_vals.append(cap_week * weeks_equiv)
            capH_year_vals.append(cap_h_week * weeks_equiv)
            model_for_capU.append(m)
            model_for_capH.append(m)

        if not capU_vals:
            continue

        import numpy as _np

        # Max / Min / Avg por línea (solo con capacidades > 0)
        max_u = float(_np.max(capU_vals))
        min_u = float(_np.min(capU_vals))
        avg_u = float(_np.mean(capU_vals))

        max_h = float(_np.max(capH_vals))
        min_h = float(_np.min(capH_vals))
        avg_h = float(_np.mean(capH_vals))

        # Modelos que dan max/min (en horas, que es lo crítico)
        idx_max_h = int(_np.argmax(capH_vals))
        idx_min_h = int(_np.argmin(capH_vals))
        model_max_h = model_for_capH[idx_max_h] if capH_vals else ""
        model_min_h = model_for_capH[idx_min_h] if capH_vals else ""

        line_stats_rows.append({
            "line": line,
            "Modelo Máx (h/SEM)": model_max_h,
            "Modelo Mín (h/SEM)": model_min_h,
            "Max UDS/SEM": max_u,
            "Prom UDS/SEM": avg_u,
            "Min UDS/SEM": min_u,
            "Max UDS/AÑO": max_u * weeks_equiv,
            "Prom UDS/AÑO": avg_u * weeks_equiv,
            "Min UDS/AÑO": min_u * weeks_equiv,
            "Max h/SEM": max_h,
            "Prom h/SEM": avg_h,
            "Min h/SEM": min_h,
            "Max h/AÑO": max_h * weeks_equiv,
            "Prom h/AÑO": avg_h * weeks_equiv,
            "Min h/AÑO": min_h * weeks_equiv,
        })

    if not line_stats_rows:
        st.warning("No hay combinaciones válidas para calcular el rango. Revisa compatibilidades, estaciones y/o tiempos.")
    else:
        line_stats_df = pd.DataFrame(line_stats_rows)

        # ----------------------------
        # NIVEL 1 — GLOBAL PLANTA
        # ----------------------------
        plant_max_u_sem = float(line_stats_df["Max UDS/SEM"].sum())
        plant_avg_u_sem = float(line_stats_df["Prom UDS/SEM"].sum())
        plant_min_u_sem = float(line_stats_df["Min UDS/SEM"].sum())

        plant_max_h_sem = float(line_stats_df["Max h/SEM"].sum())
        plant_avg_h_sem = float(line_stats_df["Prom h/SEM"].sum())
        plant_min_h_sem = float(line_stats_df["Min h/SEM"].sum())

        plant_rows = [
            {
                "Escenario": "Máximo",
                "UDS/SEM": plant_max_u_sem,
                "UDS/AÑO": plant_max_u_sem * weeks_equiv,
                "h/SEM": plant_max_h_sem,
                "h/AÑO": plant_max_h_sem * weeks_equiv,
            },
            {
                "Escenario": "Promedio",
                "UDS/SEM": plant_avg_u_sem,
                "UDS/AÑO": plant_avg_u_sem * weeks_equiv,
                "h/SEM": plant_avg_h_sem,
                "h/AÑO": plant_avg_h_sem * weeks_equiv,
            },
            {
                "Escenario": "Mínimo",
                "UDS/SEM": plant_min_u_sem,
                "UDS/AÑO": plant_min_u_sem * weeks_equiv,
                "h/SEM": plant_min_h_sem,
                "h/AÑO": plant_min_h_sem * weeks_equiv,
            },
        ]
        plant_df = pd.DataFrame(plant_rows)

        st.markdown("### Nivel 1 — Global planta (rango estructural)")
        st.dataframe(
            plant_df.style.format({
                "UDS/SEM": "{:.1f}",
                "UDS/AÑO": "{:.1f}",
                "h/SEM": "{:.1f}",
                "h/AÑO": "{:.1f}",
            }),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # ----------------------------
        # NIVEL 2 — POR LÍNEA
        # ----------------------------
        st.markdown("### Nivel 2 — Por línea (rango estructural)")

        # Orden columnas (legible)
        col_order = [
            "line",
            "Modelo Máx (h/SEM)",
            "Modelo Mín (h/SEM)",
            "Max UDS/SEM", "Prom UDS/SEM", "Min UDS/SEM",
            "Max UDS/AÑO", "Prom UDS/AÑO", "Min UDS/AÑO",
            "Max h/SEM", "Prom h/SEM", "Min h/SEM",
            "Max h/AÑO", "Prom h/AÑO", "Min h/AÑO",
        ]
        for c in col_order:
            if c not in line_stats_df.columns:
                line_stats_df[c] = ""

        line_stats_df = line_stats_df[col_order].copy()

        st.dataframe(
            line_stats_df.style.format({
                "Max UDS/SEM": "{:.1f}", "Prom UDS/SEM": "{:.1f}", "Min UDS/SEM": "{:.1f}",
                "Max UDS/AÑO": "{:.1f}", "Prom UDS/AÑO": "{:.1f}", "Min UDS/AÑO": "{:.1f}",
                "Max h/SEM": "{:.1f}", "Prom h/SEM": "{:.1f}", "Min h/SEM": "{:.1f}",
                "Max h/AÑO": "{:.1f}", "Prom h/AÑO": "{:.1f}", "Min h/AÑO": "{:.1f}",
            }),
            use_container_width=True,
            hide_index=True
        )