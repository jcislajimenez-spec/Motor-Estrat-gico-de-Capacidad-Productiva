import os
import streamlit as st
import pandas as pd

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


def ensure_float(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0).astype(float)
    return out


# =========================================================
# Cálculo por línea/modelo
# =========================================================
def compute_line_detail(line: str, model: str, stations_df: pd.DataFrame, times_df: pd.DataFrame):
    """
    stations_df: line, process, stations, operators_per_station
    times_df: model, process, cycle_time   (cycle_time en HORAS)
    """
    # --- AQUÍ ESTABA TU ERROR: NO EXISTE stations_df["model"] ---
    s = stations_df[stations_df["line"] == line].copy()

    t = times_df[times_df["model"] == model].copy()

    merged = pd.merge(
        s,
        t,
        on="process",
        how="left"
    )

    merged = ensure_int(merged, ["stations", "operators_per_station"])
    merged = ensure_float(merged, ["cycle_time"])

    # Capacidad por proceso (uds/sem): (horas_semana * turnos * estaciones * operarios) / cycle_time
    # Nota: Esto te da capacidad por proceso; el cuello es el mínimo.
    merged["cap_process"] = (
        st.session_state["hours_week"] * st.session_state["shifts"] *
        merged["stations"] * merged["operators_per_station"]
    ) / merged["cycle_time"].replace({0: pd.NA})

    merged["cap_process"] = merged["cap_process"].fillna(0.0)

    cap_week = float(merged["cap_process"].min()) if len(merged) else 0.0
    bottleneck = str(merged.loc[merged["cap_process"].idxmin(), "process"]) if len(merged) and cap_week > 0 else "-"

    return merged, bottleneck, cap_week


def work_content_total(merged: pd.DataFrame) -> float:
    """Suma de cycle_time (en horas) de todos los subprocesos del modelo en esa línea."""
    if merged is None or merged.empty:
        return 0.0
    ct = pd.to_numeric(merged["cycle_time"], errors="coerce").fillna(0.0)
    return float(ct.sum())


def capacity_hours_for_output(merged: pd.DataFrame, output_units: float) -> float:
    """Horas necesarias para producir `output_units` unidades (work content total * unidades)."""
    return float(output_units) * work_content_total(merged)


# =========================================================
# UI
# =========================================================
st.set_page_config(page_title="Capacidad Industrial – Versión A", layout="wide")

st.title("Capacidad Industrial – Versión A (líneas + modelos + compatibilidades)")
st.caption("Inputs tipo 'crema' → Resultados tipo 'azul'. Sin Excel. Uso interno.")

# ---------------------------------------------------------
# Load CSVs
# ---------------------------------------------------------
models_df = load_csv("models.csv")
stations_df = load_csv("lines_process_stations.csv")
times_df = load_csv("models_process_times.csv")
compat_df = load_csv("compatibility.csv")

# Normalizaciones mínimas
models_df = models_df.rename(columns={c: c.strip() for c in models_df.columns})
stations_df = stations_df.rename(columns={c: c.strip() for c in stations_df.columns})
times_df = times_df.rename(columns={c: c.strip() for c in times_df.columns})
compat_df = compat_df.rename(columns={c: c.strip() for c in compat_df.columns})

# Aseguramos columnas clave
required_models_cols = {"model", "description", "active"}
if not required_models_cols.issubset(set(models_df.columns)):
    st.error(f"models.csv debe tener columnas {sorted(required_models_cols)}. Ahora tiene: {list(models_df.columns)}")
    st.stop()

required_stations_cols = {"line", "process", "stations", "operators_per_station"}
if not required_stations_cols.issubset(set(stations_df.columns)):
    st.error(f"lines_process_stations.csv debe tener columnas {sorted(required_stations_cols)}. Ahora tiene: {list(stations_df.columns)}")
    st.stop()

required_times_cols = {"model", "process", "cycle_time"}
if not required_times_cols.issubset(set(times_df.columns)):
    st.error(f"models_process_times.csv debe tener columnas {sorted(required_times_cols)}. Ahora tiene: {list(times_df.columns)}")
    st.stop()

# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------
tabs = st.tabs(["📊 Planificación", "⚙️ Configuración (Power User)", "📈 Resultados"])


# =========================================================
# PLANIFICACIÓN (izquierda)
# =========================================================
with tabs[0]:
    st.subheader("Parámetros de planificación")

    col_left, col_right = st.columns([1, 2], gap="large")

    with col_left:
        # Guardamos en session_state para que lo use compute_line_detail()
        st.session_state.setdefault("hours_week", 43.0)
        st.session_state.setdefault("shifts", 1)
        st.session_state.setdefault("availability", 1.0)
        st.session_state.setdefault("efficiency", 1.0)
        st.session_state.setdefault("days_open_year", 250)
        st.session_state.setdefault("days_open_week", 5)

        st.session_state["hours_week"] = st.number_input("Horas por semana", min_value=0.0, max_value=200.0, value=float(st.session_state["hours_week"]), step=1.0, format="%.2f")
        st.session_state["shifts"] = st.number_input("Turnos", min_value=1, max_value=10, value=int(st.session_state["shifts"]), step=1)

        st.session_state["availability"] = st.slider("Disponibilidad", min_value=0.0, max_value=1.0, value=float(st.session_state["availability"]), step=0.01)
        st.session_state["efficiency"] = st.slider("Eficiencia", min_value=0.0, max_value=1.0, value=float(st.session_state["efficiency"]), step=0.01)

        st.session_state["days_open_year"] = st.number_input("Días abiertos al año", min_value=0, max_value=366, value=int(st.session_state["days_open_year"]), step=1)
        st.session_state["days_open_week"] = st.number_input("Días abiertos a la semana", min_value=1, max_value=7, value=int(st.session_state["days_open_week"]), step=1)

        weeks_open_year = (st.session_state["days_open_year"] / st.session_state["days_open_week"]) if st.session_state["days_open_week"] else 0.0
        st.metric("Semanas abiertas/año (auto)", f"{weeks_open_year:.1f}")

    with col_right:
        st.info(
            "Planificación lista. La capacidad (UDS/SEM) se calcula por subproceso y el cuello de botella es el mínimo. "
            "Las horas (h/sem y h/año) se calculan **sobre capacidad máxima** como: "
            "**work content total (suma cycle_time) × capacidad (UDS/SEM)**."
        )


# =========================================================
# CONFIGURACIÓN (POWER USER)
# =========================================================
with tabs[1]:
    st.subheader("Configuración (power user)")
    st.caption("Aquí se mantienen tiempos, estaciones y compatibilidades. Usuario normal NO debería tocar esto.")

    # ---- 1) Gestión de modelos (models.csv) ----
    st.markdown("### Gestión de modelos (`models.csv`)")

    models_edit = st.data_editor(
        models_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "active": st.column_config.CheckboxColumn("active", help="Activar/desactivar modelo"),
            "model": st.column_config.TextColumn("model"),
            "description": st.column_config.TextColumn("description"),
        },
    )

    if st.button("💾 Guardar modelos (CSV)"):
        save_csv(models_edit, "models.csv")
        st.success("Modelos guardados ✅")
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # ---- 2) Tiempos por modelo y proceso (models_process_times.csv) ----
    st.markdown("### Tiempos por modelo y proceso (`models_process_times.csv`)")

    times_edit = st.data_editor(
        times_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "model": st.column_config.TextColumn("model"),
            "process": st.column_config.TextColumn("process"),
            "cycle_time": st.column_config.NumberColumn("cycle_time (h)", help="En HORAS", step=0.1, format="%.2f"),
        },
    )

    if st.button("💾 Guardar tiempos (CSV)"):
        save_csv(times_edit, "models_process_times.csv")
        st.success("Tiempos guardados ✅")
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # ---- 3) Configuración línea ↔ estaciones / operarios (lines_process_stations.csv) ----
    st.markdown("### Estaciones y operarios por línea/proceso (`lines_process_stations.csv`)")

    stations_edit = st.data_editor(
        stations_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "line": st.column_config.TextColumn("line"),
            "process": st.column_config.TextColumn("process"),
            "stations": st.column_config.NumberColumn("stations", step=1, format="%d"),
            "operators_per_station": st.column_config.NumberColumn("operators_per_station", step=1, format="%d"),
        },
    )

    if st.button("💾 Guardar estaciones/operarios (CSV)"):
        save_csv(stations_edit, "lines_process_stations.csv")
        st.success("Estaciones/operarios guardados ✅")
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # ---- 4) Compatibilidades (compatibility.csv) ----
    st.markdown("### Compatibilidad modelo ↔ línea (`compatibility.csv`)")
    st.caption("Marca qué modelos pueden ir en qué líneas (checks).")

    compat_edit = st.data_editor(
        compat_df,
        num_rows="dynamic",
        use_container_width=True,
    )

    if st.button("💾 Guardar compatibilidades (CSV)"):
        save_csv(compat_edit, "compatibility.csv")
        st.success("Compatibilidades guardadas ✅")
        st.cache_data.clear()
        st.rerun()


# =========================================================
# RESULTADOS
# =========================================================
with tabs[2]:
    st.subheader("Resultados de capacidad")

    # Horas efectivas planta (lo mostramos)
    hours_eff_week = st.session_state["hours_week"] * st.session_state["availability"] * st.session_state["efficiency"]
    st.caption(f"Horas efectivas planta: {hours_eff_week:.2f} h/semana")

    # Modelos activos
    models_active = models_df.copy()
    models_active["active"] = pd.to_numeric(models_active["active"], errors="coerce").fillna(0).astype(int)
    models_active = models_active[models_active["active"] == 1]["model"].tolist()

    # Líneas desde stations_df
    lines_list = sorted(stations_df["line"].unique().tolist())

    # Demanda: si tu CSV de capability/demand vive en otro sitio, aquí solo demo:
    # En tu versión actual la demanda viene de la propia tabla de inputs (en otro bloque),
    # así que si no tienes esa tabla aquí, lo dejamos a 0.
    # Si ya tienes un demand_df en tu app “buena”, integra aquí el merge como lo tenías.
    demand_map = {}  # { (line, model): demand_week }

    # Semanas abiertas/año
    days_open_year = st.session_state["days_open_year"]
    days_open_week = st.session_state["days_open_week"]
    weeks_open_year = (days_open_year / days_open_week) if days_open_week else 0.0

    summary_rows = []

    for line in lines_list:
        # Para cada línea, si hay compatibilidades: recorremos modelos compatibles; si no, usamos activos
        candidate_models = models_active

        # Si compatibility tiene columnas line/model compatibles:
        # Intentamos inferir: si existe columna 'line' y 'model' y 'compatible' (o similar)
        if {"line", "model"}.issubset(set(compat_df.columns)):
            # caso tabla tipo larga
            if "compatible" in compat_df.columns:
                cm = compat_df[(compat_df["line"] == line) & (compat_df["model"].isin(models_active)) & (compat_df["compatible"] == 1)]["model"].tolist()
                if len(cm):
                    candidate_models = cm
            else:
                # si solo hay line/model en filas, asumimos que esas filas representan compatibles
                cm = compat_df[(compat_df["line"] == line) & (compat_df["model"].isin(models_active))]["model"].tolist()
                if len(cm):
                    candidate_models = cm

        for model in candidate_models:
            merged, bottleneck, cap_week = compute_line_detail(line, model, stations_df, times_df)

            # DEMANDA (uds/sem): si no hay, 0
            demand_week = float(demand_map.get((line, model), 0.0))

            # SATURACIÓN y DÉFICIT
            sat = (demand_week / cap_week * 100.0) if cap_week > 0 else 0.0
            deficit_week = max(0.0, demand_week - cap_week)

            # ANUAL (uds/año)
            demand_year = demand_week * weeks_open_year
            cap_year = cap_week * weeks_open_year

            # HORAS sobre CAPACIDAD MÁXIMA (tu definición)
            cap_hours_week = capacity_hours_for_output(merged, cap_week)
            cap_hours_year = cap_hours_week * weeks_open_year

            summary_rows.append({
                "line": line,
                "model": model,
                "Demanda (UDS/SEM)": demand_week,
                "Capacidad (UDS/SEM)": cap_week,
                "Saturación (%)": sat,
                "Déficit (UDS/SEM)": deficit_week,
                "bottleneck": bottleneck,
                "Demanda (UDS/A)": demand_year,
                "Capacidad (UDS/A)": cap_year,
                "Horas cap. (h/sem)": cap_hours_week,
                "Horas cap. (h/año)": cap_hours_year,
            })

    results_df = pd.DataFrame(summary_rows)

    if results_df.empty:
        st.warning("No hay datos para calcular resultados. Revisa CSVs y compatibilidades.")
        st.stop()

    # Redondeos (1 decimal donde toca)
    for col in ["Capacidad (UDS/SEM)", "Saturación (%)", "Déficit (UDS/SEM)", "Demanda (UDS/SEM)",
                "Demanda (UDS/A)", "Capacidad (UDS/A)", "Horas cap. (h/sem)", "Horas cap. (h/año)"]:
        if col in results_df.columns:
            results_df[col] = pd.to_numeric(results_df[col], errors="coerce").fillna(0.0)

    # Formato: 1 decimal en esas columnas
    def fmt_1(x):
        try:
            return f"{float(x):.1f}"
        except Exception:
            return x

    # Saturación con %
    def fmt_pct(x):
        try:
            return f"{float(x):.1f}%"
        except Exception:
            return x

    # Styling
    def color_sat(val):
        try:
            v = float(val)
            return "color: red;" if v > 100 else "color: green;"
        except Exception:
            return ""

    def color_bottleneck(_):
        return "background-color: #fde2e2; color: #b00020; font-weight: 600;"

    styled = results_df.style

    if "Saturación (%)" in results_df.columns:
        styled = styled.applymap(color_sat, subset=["Saturación (%)"]).format({"Saturación (%)": fmt_pct})

    for c in ["Demanda (UDS/SEM)", "Capacidad (UDS/SEM)", "Déficit (UDS/SEM)",
              "Demanda (UDS/A)", "Capacidad (UDS/A)", "Horas cap. (h/sem)", "Horas cap. (h/año)"]:
        if c in results_df.columns:
            styled = styled.format({c: fmt_1})

    if "bottleneck" in results_df.columns:
        styled = styled.applymap(lambda _: color_bottleneck(_), subset=["bottleneck"])

    st.dataframe(styled, use_container_width=True)

    st.divider()

    # ---- Detalle fino por línea y subproceso (expander) ----
    st.subheader("🔍 Detalle fino por línea y subproceso")

    for line in sorted(results_df["line"].unique().tolist()):
        # pillamos el primer modelo de esa línea para mostrar detalle (puedes hacerlo por selector si quieres)
        sub = results_df[results_df["line"] == line].copy()
        if sub.empty:
            continue

        # Si hay varios modelos, mostramos uno por expander interno
        for _, row in sub.iterrows():
            model = row["model"]
            merged, bottleneck, cap_week = compute_line_detail(line, model, stations_df, times_df)

            header = f"{line} — {model} | Capacidad máx: {cap_week:.1f} uds/sem | Cuello: {bottleneck}"
            with st.expander(header, expanded=False):
                show = merged.copy()
                # columnas ordenadas bonitas
                cols_order = ["process", "stations", "operators_per_station", "cycle_time", "cap_process"]
                cols_order = [c for c in cols_order if c in show.columns]
                show = show[cols_order]

                # Redondeos
                if "cycle_time" in show.columns:
                    show["cycle_time"] = show["cycle_time"].map(lambda x: float(x) if pd.notna(x) else 0.0)
                if "cap_process" in show.columns:
                    show["cap_process"] = show["cap_process"].map(lambda x: float(x) if pd.notna(x) else 0.0)

                st.dataframe(show, use_container_width=True)
