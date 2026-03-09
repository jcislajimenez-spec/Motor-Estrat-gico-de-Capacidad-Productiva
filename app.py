import os
import sys
import streamlit as st
import pandas as pd
from PIL import Image
import psycopg2

def resource_path(relative_path: str) -> str:
    """Devuelve la ruta absoluta a un recurso.

    - En desarrollo: usa la carpeta donde está este app.py.
    - En ejecutable PyInstaller: usa la carpeta temporal sys._MEIPASS.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS  # PyInstaller onefile/onedir
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

st.set_page_config(
    page_title="Planificador de Capacidad",
    layout="wide"
)

# --- Conexión a base de datos Neon ---
DATABASE_URL = os.environ.get("DATABASE_URL")
conn = None
if DATABASE_URL:
    conn = psycopg2.connect(DATABASE_URL)

def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])

# --- Helper cacheado para consultas SQL ---
@st.cache_data
def run_query(query: str):
    if conn is None:
        return pd.DataFrame()
    return pd.read_sql(query, conn)


ASSETS_DIR = resource_path("assets")
# --- Cargar logo ---
logo = Image.open(os.path.join(ASSETS_DIR, "ingeteam_logo.jpg"))
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

DATA_DIR = resource_path("data")

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

# =========================================================
# DB IO (Neon / Postgres)
# =========================================================
def _has_db() -> bool:
    return bool(os.getenv("DATABASE_URL"))

@st.cache_data(ttl=5)
def load_table(table: str) -> pd.DataFrame:
    """
    Carga una tabla completa desde Postgres (Neon) y devuelve DataFrame.
    Si no hay DATABASE_URL, cae a CSV local (mismo nombre + .csv) para no romper.
    """
    if not _has_db():
        return load_csv(f"{table}.csv")

    c = get_connection()
    with c.cursor() as cur:
        cur.execute(f'SELECT * FROM "{table}"')
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=cols)

    # Limpieza suave (mismo criterio que CSV)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
    return df

def save_table(df: pd.DataFrame, table: str) -> None:
    """
    Sobrescribe los datos de la planta activa en Postgres.
    
    Elimina primero los registros de esa planta
    y luego inserta los nuevos.

    Evita borrar datos de otras plantas.
    """
    if not _has_db():
        save_csv(df, f"{table}.csv")
        return

    c = get_connection()
    cols = list(df.columns)
    if not cols:
        return

    placeholders = ",".join(["%s"] * len(cols))
    col_list = ",".join([f'"{cname}"' for cname in cols])

    # Convertimos NaN -> None para psycopg2
    values = [tuple(None if (pd.isna(v)) else v for v in row) for row in df[cols].itertuples(index=False, name=None)]

    with c.cursor() as cur:
        if "plant_id" in cols:
            plant_value = int(df["plant_id"].iloc[0]) if not df.empty else int(st.session_state["plant_id"])
            cur.execute(f'DELETE FROM "{table}" WHERE plant_id = %s', (plant_value,))
        else:
            cur.execute(f'TRUNCATE TABLE "{table}"')

        cur.executemany(
            f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
            values
        )
    c.commit()

    # invalidar cache de lecturas
    try:
        load_table.clear()
    except Exception:
        pass


def ensure_int(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    return out

# =========================================================
# SELECCIÓN DE PLANTA.
# =========================================================
plants_df = load_table("plants")

if plants_df.empty:
    st.sidebar.error("No hay plantas definidas en la tabla plants")
    st.stop()

plant_names = plants_df["name"].astype(str).tolist()

selected_plant_name = st.sidebar.selectbox(
    "Seleccionar planta",
    plant_names
)

plant_id = int(
    plants_df.loc[plants_df["name"] == selected_plant_name, "id"].iloc[0]
)

st.session_state["plant_id"] = plant_id

# =========================================================
# AÑADIR NUEVA PLANTA
# =========================================================
new_plant_name = st.sidebar.text_input("Nueva planta")

if st.sidebar.button("Añadir planta"):
    if new_plant_name.strip():
        next_id = int(plants_df["id"].max()) + 1 if not plants_df.empty else 1

        new_row = pd.DataFrame([{
            "id": next_id,
            "name": new_plant_name.strip()
        }])

        plants_df = pd.concat([plants_df, new_row], ignore_index=True)
        save_table(plants_df, "plants")

        st.sidebar.success("Planta añadida")
        st.rerun()
    else:
        st.sidebar.warning("Escribe un nombre de planta")
# =========================================================
# APP CONFIG
# =========================================================

st.title("Motor Estratégico de Capacidad Productiva")
st.caption("Planificación por líneas y simulación de mix")

# =========================================================
# SIDEBAR – PARÁMETROS (SIEMPRE VISIBLES)
# =========================================================
st.sidebar.header("Parámetros de planificación")

settings_df = load_table("settings")
settings_df = settings_df[settings_df["plant_id"] == plant_id]

if settings_df.empty:
    current_settings = {
        "hours_week": 43.0,
        "shifts": 1,
        "availability": 1.0,
        "efficiency": 1.0,
        "days_open_year": 250,
        "days_open_week": 5,
    }
else:
    row = settings_df.iloc[0]
    current_settings = {
        "hours_week": float(row["hours_week"]),
        "shifts": int(row["shifts"]),
        "availability": float(row["availability"]),
        "efficiency": float(row["efficiency"]),
        "days_open_year": int(row["days_open_year"]),
        "days_open_week": int(row["days_open_week"]),
    }

hours_week = st.sidebar.number_input(
    "Horas por semana",
    min_value=0.0,
    value=current_settings["hours_week"],
    step=0.5
)

shifts = st.sidebar.number_input(
    "Turnos",
    min_value=1,
    value=current_settings["shifts"],
    step=1
)

availability = st.sidebar.slider(
    "Disponibilidad",
    0.0, 1.0,
    current_settings["availability"],
    0.01
)

efficiency = st.sidebar.slider(
    "Eficiencia",
    0.0, 1.0,
    current_settings["efficiency"],
    0.01
)

st.sidebar.divider()

days_open_year = st.sidebar.number_input(
    "Días abiertos al año",
    min_value=1,
    value=current_settings["days_open_year"],
    step=1
)

days_open_week = st.sidebar.number_input(
    "Días abiertos por semana",
    min_value=1,
    max_value=7,
    value=current_settings["days_open_week"],
    step=1
)

weeks_equiv = days_open_year / max(days_open_week, 1)
hours_eff = hours_week * shifts * availability * efficiency

st.sidebar.caption(f"Horas efectivas planta: **{hours_eff:.2f} h/semana**")
st.sidebar.caption(f"Semanas equivalentes: **{weeks_equiv:.2f} sem/año**")

# ---------------------------------------------------------
# GUARDAR PARÁMETROS DE ESTA PLANTA
# ---------------------------------------------------------

if st.sidebar.button("Guardar parámetros de esta planta"):

    new_settings = pd.DataFrame([{
        "plant_id": plant_id,
        "hours_week": hours_week,
        "shifts": shifts,
        "availability": availability,
        "efficiency": efficiency,
        "days_open_year": days_open_year,
        "days_open_week": days_open_week
    }])

    save_table(new_settings, "settings")

    st.sidebar.success("Parámetros guardados para esta planta")

# =========================================================
# CARGA DATOS
# =========================================================
models_df = load_table("models")
models_df = models_df[models_df["plant_id"] == plant_id].copy()

times_df = load_table("models_process_times")
times_df = times_df[times_df["plant_id"] == plant_id].copy()

naves_df = load_table("lines_process_stations")

stations_df = load_table("lines_process_stations")
stations_df = stations_df[stations_df["plant_id"] == plant_id].copy()

compat_df = load_table("compatibility")
compat_df = compat_df[
    (compat_df["plant_id"] == plant_id)
].copy()

# Normalización mínima
models_df["model"] = models_df["model"].astype(str).str.strip()
times_df["model"] = times_df["model"].astype(str).str.strip()
stations_df["line"] = stations_df["line"].astype(str).str.strip()
compat_df["line"] = compat_df["line"].astype(str).str.strip()
compat_df["model"] = compat_df["model"].astype(str).str.strip()

models_df = ensure_int(models_df, ["active"])
compat_df = ensure_int(compat_df, ["compatible"])
stations_df = stations_df.copy()

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

    # Compatibilidad por línea base (sin nave)
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
        for nave in sorted(stations_df["nave"].astype(str).str.strip().unique().tolist()):
            st.markdown(f"#### NAVE {nave}")
            line_ids_nave = sorted(
                stations_df.loc[stations_df["nave"] == nave, "line_id"]
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

            for line_id in line_ids_nave:
                _nave, base_line = line_id.split("-", 1)
                allowed = allowed_by_line.get(base_line, [])
                if not allowed:
                    st.info(f"{line_id}: sin modelos compatibles activos (revisa compatibilidades/modelos).")
                    continue

                default_model = st.session_state.line_model.get(line_id, allowed[0])
                if default_model not in allowed:
                    default_model = allowed[0]

                m = st.selectbox(
                    f"Modelo ({line_id})",
                    options=allowed,
                    index=allowed.index(default_model),
                    key=f"sel_model_{line_id}"
                )
                st.session_state.line_model[line_id] = m

    with colR:
        st.markdown("### Demanda (UDS/SEM)")
        for nave in sorted(stations_df["nave"].astype(str).str.strip().unique().tolist()):
            st.markdown(f"#### NAVE {nave}")
            line_ids_nave = sorted(
                stations_df.loc[stations_df["nave"] == nave, "line_id"]
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )
            for line_id in line_ids_nave:
                model = st.session_state.line_model.get(line_id)
                if not model:
                    continue
                d = st.number_input(
                    f"Demanda ({line_id} – {model})",
                    min_value=0.0,
                    value=float(st.session_state.line_demand.get(line_id, 0.0)),
                    step=1.0,
                    key=f"demand_{line_id}",
                )
                st.session_state.line_demand[line_id] = d

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
        out = out.reset_index(drop=True)
        out["model"] = out["model"].astype(str).str.strip()
        out["description"] = out["description"].astype(str).str.strip()
        out["active"] = out["active"].astype(bool).astype(int)
        out["plant_id"] = plant_id
        save_table(out, "models")
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
            "cycle_time": st.column_config.NumberColumn(
                "cycle_time",
                help="Horas por unidad (HH/ud) en ese proceso.",
                min_value=0.0,
                step=0.1,
                format="%.2f"
            )
        }
    )

    if st.button("💾 Guardar tiempos"):
        out = edited_times.copy()
        out = out.reset_index(drop=True)
        out["model"] = out["model"].astype(str).str.strip()
        out["process"] = out["process"].astype(str).str.strip()
        out["cycle_time"] = pd.to_numeric(out["cycle_time"], errors="coerce").fillna(0.0)

        # evitar duplicados modelo-proceso
        out = out.drop_duplicates(subset=["model", "process"])
        out["plant_id"] = plant_id
        save_table(out, "models_process_times")

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
            "stations": st.column_config.NumberColumn("stations", min_value=0.0, step=0.1, format="%.2f"),
            "operators_per_station": st.column_config.NumberColumn("operators_per_station", min_value=0.0, step=0.1, format="%.2f"),
        }
    )

    if st.button("💾 Guardar estaciones / operarios"):
        out = edited_stations.copy()
        out = out.reset_index(drop=True)
        out["line"] = out["line"].astype(str).str.strip()
        out["process"] = out["process"].astype(str).str.strip()
        out["stations"] = pd.to_numeric(out["stations"], errors="coerce").fillna(0.0)
        out["operators_per_station"] = pd.to_numeric(out["operators_per_station"], errors="coerce").fillna(0.0)
        out["plant_id"] = plant_id
        save_table(out, "lines_process_stations")

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
    all_line_ids = sorted(stations_df["line_id"].astype(str).str.strip().unique().tolist())

    # Matriz editable por línea real (nave + línea)
    edited_rows = []

    for line_id in line_ids_nave:

        parts = line_id.split("-", 1)

        if len(parts) == 2:
            nave, base_line = parts
        else:
            nave = "N1"
            base_line = parts[0]

        st.markdown(f"### Línea {line_id}")
        with st.expander(f"Línea {line_id}", expanded=True):
            cols = st.columns(3)
            for i, m in enumerate(all_models):
                current = compat_df[
                    (compat_df["line"] == base_line) &
                    (compat_df["model"] == m) &
                    (compat_df["nave"] == nave)
                ]
                cur_val = 0
                if not current.empty:
                    cur_val = int(current.iloc[0]["compatible"])

                checked = cols[i % 3].checkbox(
                    m,
                    value=bool(cur_val),
                    key=f"compat_{line_id}_{m}"
                )

                edited_rows.append({
                    "nave": nave,
                    "line": base_line,
                    "model": m,
                    "compatible": 1 if checked else 0
                })

    if st.button("💾 Guardar compatibilidades"):
        out = pd.DataFrame(edited_rows)
        out["plant_id"] = plant_id
        save_table(out, "compatibility")
        st.session_state["compat_saved"] = True
        st.cache_data.clear()
        st.rerun()

    if st.session_state.get("compat_saved"):
        st.success("Compatibilidades guardadas")
        st.session_state["compat_saved"] = False

# =========================================================
# 3) RESULTADOS
# =========================================================

def compute_line_detail(line_id: str, model: str) -> tuple[pd.DataFrame, str, float]:
    """
    Devuelve:
    - merged detail DF con capacity por proceso
    - bottleneck process (min capacity)
    - capacity_total_week (uds/sem) (cap del cuello)
    """
    nave, line = line_id.split("-", 1)

    t = times_df[times_df["model"] == model].copy()
    s = stations_df[
        (stations_df["line"] == line) &
        (stations_df["nave"] == nave)
    ].copy()
    merged = pd.merge(s, t, on="process", how="inner")

    if merged.empty:
        return merged, "", 0.0

    merged["stations"] = pd.to_numeric(merged["stations"], errors="coerce").fillna(0)
    merged["operators_per_station"] = pd.to_numeric(merged["operators_per_station"], errors="coerce").fillna(0)
    merged["cycle_time"] = pd.to_numeric(merged["cycle_time"], errors="coerce").fillna(0.0)

    merged["capacity"] = 0.0
    mask = merged["cycle_time"] > 0
    merged.loc[mask, "capacity"] = (
        hours_eff
        * merged.loc[mask, "stations"]
        * merged.loc[mask, "operators_per_station"]
    ) / merged.loc[mask, "cycle_time"]

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

    for line_id in line_ids_nave:

        parts = line_id.split("-", 1)

        if len(parts) == 2:
            nave, base_line = parts
        else:
            nave = "N1"
            base_line = parts[0]

        model = st.session_state.line_model.get(line_id)
        if not model:
            continue
        demand_week = float(st.session_state.line_demand.get(line_id, 0.0))

        merged, bottleneck_proc, cap_week = compute_line_detail(line_id, model)

        saturation = 0.0
        deficit = 0.0
        if cap_week > 0:
            saturation = (demand_week / cap_week) * 100.0
            deficit = max(0.0, demand_week - cap_week)

        demand_year = demand_week * weeks_equiv
        cap_year = cap_week * weeks_equiv

        _tmod = times_df[times_df["model"] == model].copy()
        _tmod["cycle_time"] = pd.to_numeric(_tmod.get("cycle_time", 0.0), errors="coerce").fillna(0.0)
        total_cycle_time_model = float(_tmod["cycle_time"].sum())

        cap_hours_week = cap_week * total_cycle_time_model
        cap_hours_year = cap_hours_week * weeks_equiv

        dem_hours_week = demand_week * total_cycle_time_model
        dem_hours_year = dem_hours_week * weeks_equiv

        summary_rows.append({
            "nave": nave,
            "line": base_line,
            "line_id": line_id,
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

        detail_by_line[line_id] = (nave, base_line, model, demand_week, bottleneck_proc, merged)

    summary_df = pd.DataFrame(summary_rows)

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
            "nave": "",
            "line": "",
            "line_id": "TOTAL",
            "model": "",
            "Saturación (%)": float("nan"),
            "Déficit (UDS/SEM)": float("nan"),
            "bottleneck": "",
        })

        for c in ["nave", "line", "line_id", "model", "bottleneck"]:
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
            except Exception:
                return ""
            return "color: red; font-weight: 700;" if v >= 100 else "color: green; font-weight: 700;"

        s = s.applymap(sat_color, subset=["Saturación (%)"])
        s = s.applymap(lambda _: "color: red; font-weight: 700;", subset=["bottleneck"])

        if "line_id" in styled.columns:
            def _style_total(row):
                if str(row.get("line_id", "")) == "TOTAL":
                    return ["font-weight: 800; font-size: 18px;"] * len(row)
                return [""] * len(row)
            s = s.apply(_style_total, axis=1)

        return s

    if summary_df.empty:
        st.info("No hay resultados aún. Selecciona modelos/demanda en Planificación.")
    else:
        display_cols = [
            "nave", "line", "model",
            "Demanda (UDS/SEM)", "Capacidad (UDS/SEM)", "Saturación (%)", "Déficit (UDS/SEM)",
            "bottleneck",
            "Demanda (UDS/AÑO)", "Capacidad (UDS/AÑO)",
            "Demanda (h/SEM)", "Capacidad (h/SEM)",
            "Demanda (h/AÑO)", "Capacidad (h/AÑO)"
        ]
        total_display_df = summary_df.copy()
        total_display_df.loc[total_display_df["line_id"] == "TOTAL", ["nave", "line"]] = ["", "TOTAL"]
        st.dataframe(style_summary(total_display_df[display_cols]), use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("## 🔎 Detalle fino por línea y subproceso")
        st.caption("Desglose real por subproceso. El cuello de botella es el subproceso con menor capacidad.")

        for line_id, (nave, base_line, model, demand_week, bottleneck_proc, merged) in detail_by_line.items():
            cap_week = 0.0
            if merged is not None and not merged.empty:
                cap_week = float(merged["capacity"].min())

            header = f"{nave}-{base_line} — Modelo: {model} | Capacidad máx: {cap_week:.2f} uds/sem | Cuello: {bottleneck_proc} | Demanda: {demand_week:.2f} uds/sem"
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
                        show.style.format({"capacity": "{:.3f}"}).apply(hl_bottleneck, axis=1),
                        use_container_width=True,
                        hide_index=True
                    )

    import plotly.graph_objects as go

    st.divider()
    st.markdown("## 📊 Representación gráfica de Demanda vs Capacidad")

    if not summary_df.empty:
        df_plot = summary_df.copy()
        df_plot = df_plot[df_plot["line_id"] != "TOTAL"].copy()

        line_order = [l for l in lines if l in set(df_plot["line_id"].astype(str).tolist())]
        if "TOTAL" in set(summary_df["line_id"].astype(str).tolist()):
            line_order.append("TOTAL")

        df_plot["line_id"] = pd.Categorical(df_plot["line_id"].astype(str), categories=line_order, ordered=True)
        df_plot = df_plot.sort_values("line_id")

        st.markdown("### 🔹 Demanda vs Capacidad – UDS/SEM")
        fig1 = go.Figure()
        fig1.add_bar(x=df_plot["line_id"], y=df_plot["Demanda (UDS/SEM)"], name="Demanda", marker_color="#A6192E")
        fig1.add_bar(x=df_plot["line_id"], y=df_plot["Capacidad (UDS/SEM)"], name="Capacidad", marker_color="green")
        fig1.update_layout(barmode="group")
        st.plotly_chart(fig1, use_container_width=True, key="fig1")

        st.markdown("### 🔴 Demanda vs Capacidad – h/SEM (CRÍTICO)")
        fig2 = go.Figure()
        fig2.add_bar(x=df_plot["line_id"], y=df_plot["Demanda (h/SEM)"], name="Demanda", marker_color="#A6192E")
        fig2.add_bar(x=df_plot["line_id"], y=df_plot["Capacidad (h/SEM)"], name="Capacidad", marker_color="green")
        fig2.update_layout(barmode="group")
        st.plotly_chart(fig2, use_container_width=True, key="fig2")

        st.markdown("### 🔹 Demanda vs Capacidad – UDS/AÑO")
        fig3 = go.Figure()
        fig3.add_bar(x=df_plot["line_id"], y=df_plot["Demanda (UDS/AÑO)"], name="Demanda", marker_color="#A6192E")
        fig3.add_bar(x=df_plot["line_id"], y=df_plot["Capacidad (UDS/AÑO)"], name="Capacidad", marker_color="green")
        fig3.update_layout(barmode="group")
        st.plotly_chart(fig3, use_container_width=True, key="fig3")

        st.markdown("### 🔴 Demanda vs Capacidad – h/AÑO (CRÍTICO)")
        fig4 = go.Figure()
        fig4.add_bar(x=df_plot["line_id"], y=df_plot["Demanda (h/AÑO)"], name="Demanda", marker_color="#A6192E")
        fig4.add_bar(x=df_plot["line_id"], y=df_plot["Capacidad (h/AÑO)"], name="Capacidad", marker_color="green")
        fig4.update_layout(barmode="group")
        st.plotly_chart(fig4, use_container_width=True, key="fig4")

        st.markdown("## 🧠 Visión global planta – h/SEM")
        total_demand_h_sem = float(summary_df.loc[summary_df["line_id"] != "TOTAL", "Demanda (h/SEM)"].sum())
        total_capacity_h_sem = float(summary_df.loc[summary_df["line_id"] != "TOTAL", "Capacidad (h/SEM)"].sum())

        fig_total = go.Figure()
        fig_total.add_bar(x=["TOTAL"], y=[total_demand_h_sem], name="Demanda Total", marker_color="#A6192E")
        fig_total.add_bar(x=["TOTAL"], y=[total_capacity_h_sem], name="Capacidad Total", marker_color="green")
        fig_total.update_layout(barmode="group")
        st.plotly_chart(fig_total, use_container_width=True, key="chart_total")


with tabs[3]:
    st.subheader("Capacidad según mix")
    st.info(
        "La planta produce **horas configurables**.\n"
        "La capacidad no es un valor fijo, sino un **rango estructural** determinado por el mix posible de modelos en cada línea.\n"
        "Aquí se muestran los valores **Máximo / Promedio / Mínimo** por planta y por línea, en unidades y en horas (semana y año)."
    )

    compat_active = compat_df[(compat_df.get("compatible", 0) == 1) & (compat_df["model"].isin(active_models))].copy()
    allowed_by_line = compat_active.groupby("line")["model"].apply(list).to_dict()

    _t = times_df.copy()
    _t["cycle_time"] = pd.to_numeric(_t.get("cycle_time", 0.0), errors="coerce").fillna(0.0)
    cycle_by_model = _t.groupby("model")["cycle_time"].sum().to_dict()

    line_stats_rows = []
    capH_line_model = {}
    capU_line_model = {}
    max_h_week_by_line = {}

    for line_id in line_ids_nave:

        parts = line_id.split("-", 1)

        if len(parts) == 2:
            nave, base_line = parts
        else:
            nave = "N1"
            base_line = parts[0]

        models_allowed = allowed_by_line.get(base_line, [])
        if not models_allowed:
            continue

        capU_vals = []
        capH_vals = []
        model_for_capH = []

        for m in models_allowed:
            merged, _bn, cap_week = compute_line_detail(line_id, m)
            cap_week = float(cap_week) if cap_week else 0.0
            if cap_week <= 0:
                continue

            w_m = float(cycle_by_model.get(m, 0.0))
            cap_h_week = cap_week * w_m

            capH_line_model[(line_id, m)] = float(cap_h_week)
            capU_line_model[(line_id, m)] = float(cap_week)

            capU_vals.append(cap_week)
            capH_vals.append(cap_h_week)
            model_for_capH.append(m)

        if not capU_vals:
            continue

        import numpy as _np

        max_u = float(_np.max(capU_vals))
        min_u = float(_np.min(capU_vals))
        avg_u = float(_np.mean(capU_vals))

        max_h = float(_np.max(capH_vals))
        min_h = float(_np.min(capH_vals))
        avg_h = float(_np.mean(capH_vals))
        max_h_week_by_line[line_id] = max_h

        idx_max_h = int(_np.argmax(capH_vals))
        idx_min_h = int(_np.argmin(capH_vals))
        model_max_h = model_for_capH[idx_max_h] if capH_vals else ""
        model_min_h = model_for_capH[idx_min_h] if capH_vals else ""

        line_stats_rows.append({
            "nave": nave,
            "line": base_line,
            "line_id": line_id,
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

        plant_max_u_sem = float(line_stats_df["Max UDS/SEM"].sum())
        plant_avg_u_sem = float(line_stats_df["Prom UDS/SEM"].sum())
        plant_min_u_sem = float(line_stats_df["Min UDS/SEM"].sum())

        plant_max_h_sem = float(line_stats_df["Max h/SEM"].sum())
        plant_avg_h_sem = float(line_stats_df["Prom h/SEM"].sum())
        plant_min_h_sem = float(line_stats_df["Min h/SEM"].sum())

        plant_rows = [
            {"Escenario": "Máximo", "UDS/SEM": plant_max_u_sem, "UDS/AÑO": plant_max_u_sem * weeks_equiv, "h/SEM": plant_max_h_sem, "h/AÑO": plant_max_h_sem * weeks_equiv},
            {"Escenario": "Promedio", "UDS/SEM": plant_avg_u_sem, "UDS/AÑO": plant_avg_u_sem * weeks_equiv, "h/SEM": plant_avg_h_sem, "h/AÑO": plant_avg_h_sem * weeks_equiv},
            {"Escenario": "Mínimo", "UDS/SEM": plant_min_u_sem, "UDS/AÑO": plant_min_u_sem * weeks_equiv, "h/SEM": plant_min_h_sem, "h/AÑO": plant_min_h_sem * weeks_equiv},
        ]
        plant_df = pd.DataFrame(plant_rows)

        st.markdown("### Nivel 1 — Global planta (rango estructural)")
        st.dataframe(
            plant_df.style.format({"UDS/SEM": "{:.1f}", "UDS/AÑO": "{:.1f}", "h/SEM": "{:.1f}", "h/AÑO": "{:.1f}"}),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.markdown("### Nivel 2 — Por línea (rango estructural)")
        col_order = [
            "nave", "line",
            "Modelo Máx (h/SEM)", "Modelo Mín (h/SEM)",
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

        st.markdown("## Nivel 3 — Simulador de ocupación estructural por modelo")
        st.caption(
            "Este simulador **NO** cambia la planificación real. Solo sirve para explorar, en términos de **horas estructurales (h/sem)**, "
            "cuánto 'peso' podría llegar a ocupar cada modelo dentro del **techo estructural** de la planta."
        )

        H_max_plant = float(sum(max_h_week_by_line.values())) if max_h_week_by_line else 0.0
        st.markdown(f"**Techo estructural planta (H_max_plant):** {H_max_plant:.2f} h/sem")

        maxH_by_model = {}
        for m in cycle_by_model.keys():
            total_h = 0.0
            for line_id in lines:
                h = float(capH_line_model.get((line_id, m), 0.0) or 0.0)
                if h > 0:
                    total_h += h
            if total_h > 0:
                maxH_by_model[m] = total_h

        valid_models = sorted(maxH_by_model.keys())
        share_max_by_model = {m: (maxH_by_model[m] / H_max_plant) if H_max_plant > 0 else 0.0 for m in valid_models}

        if not valid_models or H_max_plant <= 0:
            st.info("No hay modelos válidos (capacidad estructural > 0) para construir el simulador.")
        else:
            left, right = st.columns([3.2, 1.4], gap="large")

            with right:
                st.markdown("### Agregado planta")
                total_selected_pct = 0.0

                try:
                    import plotly.express as px
                    palette = px.colors.qualitative.Plotly
                except Exception:
                    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

                segments = []
                for i, m in enumerate(valid_models):
                    max_pct = float(share_max_by_model.get(m, 0.0) * 100.0)
                    if max_pct <= 0:
                        continue
                    key = f"mix_lvl3_pct_{m}"
                    sel_pct = float(st.session_state.get(key, 0.0) or 0.0)
                    sel_pct = max(0.0, min(sel_pct, max_pct))
                    segments.append((m, sel_pct, palette[i % len(palette)]))
                    total_selected_pct += sel_pct

                exceso = max(0.0, total_selected_pct - 100.0)

                import plotly.graph_objects as go

                range_max = max(120.0, float(total_selected_pct) * 1.10)

                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=float(total_selected_pct),
                    number={"suffix": "%", "valueformat": ".2f"},
                    gauge={
                        "axis": {"range": [0, range_max]},
                        "bar": {"color": "#A6192E"},
                        "steps": [
                            {"range": [0, 100], "color": "#E8F5E9"},
                            {"range": [100, range_max], "color": "#FFEBEE"},
                        ],
                        "threshold": {"line": {"color": "black", "width": 4}, "thickness": 0.75, "value": 100},
                    },
                ))
                fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))

                st.plotly_chart(fig, use_container_width=True, key="chart_velocimetro")
                if segments:
                    fig_stack = go.Figure()
                    for m, pct, color in segments:
                        fig_stack.add_bar(y=["Planta"], x=[pct], name=m, orientation="h", marker=dict(color=color))
                    fig_stack.update_layout(
                        barmode="stack",
                        height=120,
                        margin=dict(l=10, r=10, t=10, b=10),
                        xaxis=dict(range=[0, max(100, total_selected_pct)], title="% ocupación estructural"),
                        yaxis=dict(showticklabels=False),
                        legend=dict(orientation="h"),
                    )
                    st.plotly_chart(fig_stack, use_container_width=True, key="chart_stack")

                total_h_week = H_max_plant * (total_selected_pct / 100.0)
                total_h_year = total_h_week * float(weeks_equiv)
                H_max_plant_year = H_max_plant * float(weeks_equiv)

                st.write(f"**Horas máximas/año (estructura):** {H_max_plant_year:.2f}")
                if exceso > 0:
                    st.error(f"Exceso estructural: {exceso:.2f}%")
                st.write(f"**Ocupación agregada:** {total_selected_pct:.2f}%")
                st.write(f"**Horas/sem (equivalentes):** {total_h_week:.2f}")
                st.write(f"**Horas/año (equivalentes):** {total_h_year:.2f}")

            with left:
                st.markdown("### Por modelo")
                grid_cols = 2
                rows = [valid_models[i:i+grid_cols] for i in range(0, len(valid_models), grid_cols)]

                for r_models in rows:
                    cols = st.columns(grid_cols, gap="large")
                    for j in range(grid_cols):
                        if j >= len(r_models):
                            cols[j].empty()
                            continue
                        m = r_models[j]
                        maxH = float(maxH_by_model.get(m, 0.0))
                        max_pct = float(share_max_by_model.get(m, 0.0) * 100.0)

                        with cols[j]:
                            st.markdown(f"#### {m}")
                            key = f"mix_lvl3_pct_{m}"
                            sel_pct = st.slider(
                                "Ocupación simulada (% de planta)",
                                min_value=0.0,
                                max_value=max_pct,
                                value=float(st.session_state.get(key, 0.0) or 0.0),
                                step=0.01,
                                key=key,
                                format="%.2f",
                                help="Este % es una ocupación estructural teórica (no planificación real).",
                            )

                            sel_h_week = H_max_plant * (sel_pct / 100.0)
                            sel_h_year = sel_h_week * float(weeks_equiv)

                            w_m = float(cycle_by_model.get(m, 0.0) or 0.0)
                            sel_u_week = (sel_h_week / w_m) if w_m > 0 else 0.0
                            sel_u_year = sel_u_week * float(weeks_equiv)

                            max_u_week = (maxH / w_m) if w_m > 0 else 0.0
                            max_u_year = max_u_week * float(weeks_equiv)

                            import plotly.graph_objects as go
                            fig_d = go.Figure(go.Pie(
                                labels=["Seleccionado", "Resto hasta máx"],
                                values=[sel_pct, max(0.0, max_pct - sel_pct)],
                                hole=0.65,
                                sort=False,
                                direction="clockwise",
                                textinfo="none",
                            ))
                            fig_d.update_layout(
                                height=240,
                                margin=dict(l=10, r=10, t=10, b=10),
                                showlegend=False,
                                annotations=[dict(
                                    text=f"{sel_pct:.2f}%<br><span style='font-size:12px'>máx {max_pct:.2f}%</span>",
                                    x=0.5, y=0.5, font=dict(size=16), showarrow=False
                                )]
                            )
                            st.plotly_chart(fig_d, use_container_width=True, key=f"chart_donut_{m}")

                            df_m = pd.DataFrame({
                                "": ["Seleccionado", "Máximo modelo"],
                                "Uds/sem": [sel_u_week, max_u_week],
                                "Uds/año": [sel_u_year, max_u_year],
                                "h/sem": [sel_h_week, maxH],
                                "h/año": [sel_h_year, maxH * float(weeks_equiv)],
                            })
                            df_show = df_m.copy()
                            for c in ["Uds/sem", "Uds/año", "h/sem", "h/año"]:
                                df_show[c] = df_show[c].map(lambda x: f"{float(x):.2f}")
                            st.table(df_show)
