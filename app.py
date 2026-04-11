import os
import sys
import time  # TIMING — quitar tras Fase 3.2
import streamlit as st
import pandas as pd
from PIL import Image
import psycopg2
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

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
def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


ASSETS_DIR = resource_path("assets")
# --- Cargar logo ---
@st.cache_data
def _load_logo():
    return Image.open(os.path.join(ASSETS_DIR, "ingeteam_logo.jpg"))

logo = _load_logo()
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

@st.cache_data(ttl=60)
def load_table(table: str) -> pd.DataFrame:
    """
    Carga una tabla completa desde Postgres (Neon) y devuelve DataFrame.
    Si no hay DATABASE_URL, cae a CSV local (mismo nombre + .csv) para no romper.
    """
    if not _has_db():
        return load_csv(f"{table}.csv")

    c = get_connection()
    try:
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
    finally:
        c.close()

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
    try:
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
                # Seguridad: asegurar que solo guardamos datos de la planta correcta
                df = df[df["plant_id"] == plant_value].copy()
                values = [tuple(None if (pd.isna(v)) else v for v in row) for row in df[cols].itertuples(index=False, name=None)]
                cur.execute(f'DELETE FROM "{table}" WHERE plant_id = %s', (plant_value,))
            else:
                cur.execute(f'TRUNCATE TABLE "{table}"')

            cur.executemany(
                f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
                values
            )
        c.commit()
    finally:
        c.close()

    # invalidar cache de lecturas
    try:
        load_table.clear()
        load_plant_data.clear()
        load_all_plants_data.clear()
    except Exception:
        pass


def ensure_int(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    return out


@st.cache_data(ttl=60)
def load_plant_data(plant_id: int):
    models_df = load_table("models")
    models_df = models_df[models_df["plant_id"] == plant_id].copy()
    models_df["model"] = models_df["model"].astype(str).str.strip()
    models_df = ensure_int(models_df, ["active"])

    times_df = load_table("models_process_times")
    times_df = times_df[times_df["plant_id"] == plant_id].copy()
    times_df["model"] = times_df["model"].astype(str).str.strip()

    stations_df = load_table("lines_process_stations")
    stations_df = stations_df[stations_df["plant_id"] == plant_id].copy()
    stations_df["line"] = stations_df["line"].astype(str).str.strip()
    stations_df["nave"] = stations_df["nave"].astype(str).str.strip()
    stations_df["line_id"] = stations_df["nave"] + "-" + stations_df["line"]

    compat_df = load_table("compatibility")
    compat_df = compat_df[compat_df["plant_id"] == plant_id].copy()
    compat_df["line"] = compat_df["line"].astype(str).str.strip()
    compat_df["model"] = compat_df["model"].astype(str).str.strip()
    compat_df["nave"] = compat_df["nave"].astype(str).str.strip()
    compat_df["line_id"] = compat_df["nave"] + "-" + compat_df["line"]
    compat_df = ensure_int(compat_df, ["compatible"])

    active_models = models_df.loc[models_df["active"] == 1, "model"].tolist()

    line_ids_nave = sorted(
        stations_df["line_id"].astype(str).str.strip().unique().tolist()
    )

    return {
        "models_df": models_df,
        "times_df": times_df,
        "stations_df": stations_df,
        "compat_df": compat_df,
        "active_models": active_models,
        "line_ids_nave": line_ids_nave,
    }


@st.cache_data
def compute_plant_structural_capacity(
    p_id: int,
    p_name: str,
    all_settings: pd.DataFrame,
    all_models: pd.DataFrame,
    all_times: pd.DataFrame,
    all_stations: pd.DataFrame,
    all_compat: pd.DataFrame,
    shifts_override: int = None,
) -> dict:
    """Calcula capacidad estructural (max/prom/min) para una planta.
    Si shifts_override tiene valor, fuerza ese número de turnos (solo para vista Global)."""

    # Obtener settings de la planta
    p_settings = all_settings[all_settings["plant_id"] == p_id]
    if p_settings.empty:
        p_hours_week = 43.0
        p_shifts = 1
        p_availability = 1.0
        p_efficiency = 1.0
        p_days_year = 250
        p_days_week = 5
    else:
        row = p_settings.iloc[0]
        p_hours_week = float(row.get("hours_week", 43.0))
        p_shifts = int(row.get("shifts", 1))
        p_availability = float(row.get("availability", 1.0))
        p_efficiency = float(row.get("efficiency", 1.0))
        p_days_year = int(row.get("days_open_year", 250))
        p_days_week = int(row.get("days_open_week", 5))

    # Si hay override de turnos (selector global), usarlo en lugar de p_shifts
    effective_shifts = shifts_override if shifts_override else p_shifts
    p_hours_eff = p_hours_week * effective_shifts * p_availability * p_efficiency
    p_weeks_equiv = p_days_year / max(p_days_week, 1)

    # Filtrar datos por planta
    p_models = all_models[all_models["plant_id"] == p_id].copy()
    p_times = all_times[all_times["plant_id"] == p_id].copy()
    p_stations = all_stations[all_stations["plant_id"] == p_id].copy()
    p_compat = all_compat[all_compat["plant_id"] == p_id].copy()

    if p_models.empty or p_stations.empty:
        return {
            "plant_id": p_id, "plant_name": p_name,
            "hours_eff": p_hours_eff, "weeks_equiv": p_weeks_equiv,
            "max_u_sem": 0.0, "prom_u_sem": 0.0, "min_u_sem": 0.0,
            "max_u_year": 0.0, "prom_u_year": 0.0, "min_u_year": 0.0,
            "max_h_sem": 0.0, "prom_h_sem": 0.0, "min_h_sem": 0.0,
            "max_h_year": 0.0, "prom_h_year": 0.0, "min_h_year": 0.0,
            "lines_count": 0, "line_stats": [],
        }

    # Normalización
    p_models["model"] = p_models["model"].astype(str).str.strip()
    p_times["model"] = p_times["model"].astype(str).str.strip()
    p_stations["line"] = p_stations["line"].astype(str).str.strip()
    p_compat["line"] = p_compat["line"].astype(str).str.strip()
    p_compat["model"] = p_compat["model"].astype(str).str.strip()
    p_compat["nave"] = p_compat["nave"].astype(str).str.strip()
    p_compat["line_id"] = p_compat["nave"] + "-" + p_compat["line"]

    p_models = ensure_int(p_models, ["active"])
    p_compat = ensure_int(p_compat, ["compatible"])

    active_models_p = p_models.loc[p_models["active"] == 1, "model"].tolist()

    if not active_models_p:
        return {
            "plant_id": p_id, "plant_name": p_name,
            "hours_eff": p_hours_eff, "weeks_equiv": p_weeks_equiv,
            "max_u_sem": 0.0, "prom_u_sem": 0.0, "min_u_sem": 0.0,
            "max_u_year": 0.0, "prom_u_year": 0.0, "min_u_year": 0.0,
            "max_h_sem": 0.0, "prom_h_sem": 0.0, "min_h_sem": 0.0,
            "max_h_year": 0.0, "prom_h_year": 0.0, "min_h_year": 0.0,
            "lines_count": 0, "line_stats": [],
        }

    # Compatibilidades activas
    compat_active_p = p_compat[(p_compat["compatible"] == 1) & (p_compat["model"].isin(active_models_p))].copy()
    allowed_by_line_p = compat_active_p.groupby("line_id")["model"].apply(list).to_dict()

    # Cycle times por modelo
    _t = p_times.copy()
    _t["cycle_time"] = pd.to_numeric(_t["cycle_time"], errors="coerce").fillna(0.0)
    cycle_by_model_p = _t.groupby("model")["cycle_time"].sum().to_dict()

    # Pre-convertir tipos numéricos una sola vez
    p_times["cycle_time"] = pd.to_numeric(p_times["cycle_time"], errors="coerce").fillna(0.0)

    if "machine_time" in p_times.columns:
        p_times["machine_time"] = pd.to_numeric(p_times["machine_time"], errors="coerce").fillna(0.0)
    else:
        p_times["machine_time"] = 0.0

    if "labor_time" in p_times.columns:
        p_times["labor_time"] = pd.to_numeric(p_times["labor_time"], errors="coerce").fillna(0.0)
    else:
        p_times["labor_time"] = 0.0

    p_stations["stations"] = pd.to_numeric(p_stations["stations"], errors="coerce").fillna(0)
    p_stations["operators_per_station"] = pd.to_numeric(p_stations["operators_per_station"], errors="coerce").fillna(0)

    # Pre-indexar tiempos por modelo
    _time_cols = ["process", "cycle_time", "machine_time", "labor_time"]
    times_by_model = {m: grp[_time_cols] for m, grp in p_times.groupby("model")}

    # Pre-indexar estaciones por line_id
    stations_by_line = {lid: grp[["process", "stations", "operators_per_station"]]
                        for lid, grp in p_stations.groupby("line_id")}

    # Line IDs
    line_ids_p = sorted(p_stations["line_id"].astype(str).str.strip().unique().tolist())

    line_stats_rows = []

    for line_id in line_ids_p:
        parts = line_id.split("-", 1)
        if len(parts) == 2:
            nave, base_line = parts
        else:
            nave = "N1"
            base_line = parts[0]

        models_allowed = allowed_by_line_p.get(line_id, [])
        if not models_allowed:
            continue

        capU_vals = []
        capH_vals = []

        s = stations_by_line.get(line_id)
        if s is None or s.empty:
            continue

        for m in models_allowed:
            t = times_by_model.get(m)
            if t is None or t.empty:
                continue

            merged = pd.merge(s, t, on="process", how="inner")

            if merged.empty:
                continue

            productive = merged[(merged["stations"] > 0)].copy()
            if productive.empty:
                continue

            ops = productive["operators_per_station"].clip(lower=1.0)
            labor_per_op = productive["labor_time"] / ops
            ctr = pd.concat([productive["machine_time"], labor_per_op], axis=1).max(axis=1)

            valid = ctr > 0
            if not valid.any():
                continue

            cap_values = (p_hours_eff * productive.loc[valid, "stations"]) / ctr[valid]

            cap_min = float(cap_values.min())
            if cap_min <= 0:
                continue

            w_m = float(cycle_by_model_p.get(m, 0.0))

            capU_vals.append(cap_min)
            capH_vals.append(cap_min * w_m)

        if not capU_vals:
            continue

        line_stats_rows.append({
            "line_id": line_id, "nave": nave, "line": base_line,
            "max_u": float(np.max(capU_vals)),
            "prom_u": float(np.mean(capU_vals)),
            "min_u": float(np.min(capU_vals)),
            "max_h": float(np.max(capH_vals)),
            "prom_h": float(np.mean(capH_vals)),
            "min_h": float(np.min(capH_vals)),
        })

    if not line_stats_rows:
        return {
            "plant_id": p_id, "plant_name": p_name,
            "hours_eff": p_hours_eff, "weeks_equiv": p_weeks_equiv,
            "max_u_sem": 0.0, "prom_u_sem": 0.0, "min_u_sem": 0.0,
            "max_u_year": 0.0, "prom_u_year": 0.0, "min_u_year": 0.0,
            "max_h_sem": 0.0, "prom_h_sem": 0.0, "min_h_sem": 0.0,
            "max_h_year": 0.0, "prom_h_year": 0.0, "min_h_year": 0.0,
            "lines_count": 0, "line_stats": [],
        }

    # Agregar por planta
    max_u_sem  = sum(r["max_u"]  for r in line_stats_rows)
    prom_u_sem = sum(r["prom_u"] for r in line_stats_rows)
    min_u_sem  = sum(r["min_u"]  for r in line_stats_rows)
    max_h_sem  = sum(r["max_h"]  for r in line_stats_rows)
    prom_h_sem = sum(r["prom_h"] for r in line_stats_rows)
    min_h_sem  = sum(r["min_h"]  for r in line_stats_rows)

    return {
        "plant_id": p_id, "plant_name": p_name,
        "hours_eff": p_hours_eff, "weeks_equiv": p_weeks_equiv,
        "max_u_sem": max_u_sem, "prom_u_sem": prom_u_sem, "min_u_sem": min_u_sem,
        "max_u_year": max_u_sem * p_weeks_equiv,
        "prom_u_year": prom_u_sem * p_weeks_equiv,
        "min_u_year": min_u_sem * p_weeks_equiv,
        "max_h_sem": max_h_sem, "prom_h_sem": prom_h_sem, "min_h_sem": min_h_sem,
        "max_h_year": max_h_sem * p_weeks_equiv,
        "prom_h_year": prom_h_sem * p_weeks_equiv,
        "min_h_year": min_h_sem * p_weeks_equiv,
        "lines_count": len(line_stats_rows),
        "line_stats": line_stats_rows,
    }


@st.cache_data(show_spinner=False)
def compute_all_plants_structural_capacity(
    all_data: dict,
    shifts_override: int = None,
) -> list:
    """Calcula capacidad estructural para TODAS las plantas en una sola llamada cacheada.
    all_data se hashea UNA sola vez en lugar de 5 DataFrames × N plantas."""
    results = []
    for _, plant_row in all_data["plants"].iterrows():
        p_id = int(plant_row["id"])
        p_name = str(plant_row["name"])
        result = compute_plant_structural_capacity(
            p_id, p_name,
            all_data["settings"], all_data["models"], all_data["times"],
            all_data["stations"], all_data["compat"],
            shifts_override=shifts_override,
        )
        results.append(result)
    return results


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
# SIDEBAR – NAVEGACIÓN
# =========================================================
_PAGES = [
    "🌐 Global",
    "📊 Planificación",
    "⚙️ Configuración (Power User)",
    "📈 Resultados",
    "🧭 Capacidad según mix",
]
st.sidebar.radio("Pantalla:", _PAGES, key="active_tab")

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
# TIMING D — load_plant_data (corre en cada rerun, debe ser <5 ms si cachea bien)
_t0_D = time.perf_counter()
_pd = load_plant_data(plant_id)
_ms_D = round((time.perf_counter() - _t0_D) * 1000, 1)
st.sidebar.caption(f"⏱ load_plant_data: {_ms_D} ms")

models_df     = _pd["models_df"]
times_df      = _pd["times_df"]
stations_df   = _pd["stations_df"]
compat_df     = _pd["compat_df"]
active_models = _pd["active_models"]
line_ids_nave = _pd["line_ids_nave"]

# Líneas disponibles (derivadas de stations_df)
lines = sorted(stations_df["line"].unique().tolist())

# Compatibilidad activa — calculada una sola vez, compartida por Tab 1 y Tab 4
compat_active = compat_df[(compat_df["compatible"] == 1) & (compat_df["model"].isin(active_models))]
allowed_by_line = compat_active.groupby("line_id")["model"].apply(list).to_dict()

# =========================================================
# Inicialización segura de session_state de planificación
# Debe estar a nivel de módulo (fuera de cualquier tab) para que Resultados
# y Capacidad según mix no rompan al entrar sin pasar por Planificación.
# =========================================================
if "line_model" not in st.session_state:
    st.session_state.line_model = {}
if "line_demand" not in st.session_state:
    st.session_state.line_demand = {}
_pid_init = st.session_state["plant_id"]
if _pid_init not in st.session_state.line_model:
    st.session_state.line_model[_pid_init] = {}
if _pid_init not in st.session_state.line_demand:
    st.session_state.line_demand[_pid_init] = {}

# =========================================================
# Capacidad por modelo y planta (cacheada a nivel de módulo)
# =========================================================
@st.cache_data(show_spinner=False)
def compute_model_capacity_by_plant(model_name: str, p_id: int, all_data: dict, shifts_override: int = None) -> dict:
    """Calcula capacidad de un modelo específico en una planta."""
    p_settings = all_data["settings"][all_data["settings"]["plant_id"] == p_id]
    if p_settings.empty:
        p_hours_eff = 43.0
        p_weeks_equiv = 50.0
    else:
        row = p_settings.iloc[0]
        p_hours_week = float(row.get("hours_week", 43.0))
        p_shifts = int(row.get("shifts", 1))
        p_availability = float(row.get("availability", 1.0))
        p_efficiency = float(row.get("efficiency", 1.0))
        p_days_year = int(row.get("days_open_year", 250))
        p_days_week = int(row.get("days_open_week", 5))
        effective_shifts = shifts_override if shifts_override else p_shifts
        p_hours_eff = p_hours_week * effective_shifts * p_availability * p_efficiency
        p_weeks_equiv = p_days_year / max(p_days_week, 1)

    p_times = all_data["times"][all_data["times"]["plant_id"] == p_id].copy()
    p_stations = all_data["stations"][all_data["stations"]["plant_id"] == p_id].copy()
    p_compat = all_data["compat"][all_data["compat"]["plant_id"] == p_id].copy()

    p_times["model"] = p_times["model"].astype(str).str.strip()
    p_compat["model"] = p_compat["model"].astype(str).str.strip()
    p_compat["line"] = p_compat["line"].astype(str).str.strip()
    p_compat["nave"] = p_compat["nave"].astype(str).str.strip()
    p_compat["line_id"] = p_compat["nave"] + "-" + p_compat["line"]
    p_compat = ensure_int(p_compat, ["compatible"])

    # Líneas compatibles con este modelo (por line_id)
    compat_line_ids = p_compat[(p_compat["model"] == model_name) & (p_compat["compatible"] == 1)]["line_id"].tolist()

    if not compat_line_ids:
        return {"cap_u_sem": 0.0, "cap_h_sem": 0.0}

    # Cycle time del modelo
    model_times = p_times[p_times["model"] == model_name].copy()
    model_times["cycle_time"] = pd.to_numeric(model_times["cycle_time"], errors="coerce").fillna(0.0)
    total_cycle = float(model_times["cycle_time"].sum())

    line_ids = p_stations["line_id"].astype(str).str.strip().unique().tolist()

    total_cap_u = 0.0
    total_cap_h = 0.0

    for line_id in line_ids:
        if line_id not in compat_line_ids:
            continue

        t = model_times.copy()
        s = p_stations[p_stations["line_id"] == line_id].copy()

        merged = pd.merge(s, t, on="process", how="inner")

        if merged.empty:
            continue

        merged["stations"] = pd.to_numeric(merged["stations"], errors="coerce").fillna(0)
        merged["operators_per_station"] = pd.to_numeric(merged["operators_per_station"], errors="coerce").fillna(0).clip(lower=1.0)
        for _tc in ("machine_time", "labor_time"):
            if _tc in merged.columns:
                merged[_tc] = pd.to_numeric(merged[_tc], errors="coerce").fillna(0.0)
            else:
                merged[_tc] = 0.0

        productive = merged[merged["stations"] > 0].copy()
        if productive.empty:
            continue

        labor_per_op = productive["labor_time"] / productive["operators_per_station"]
        ctr = pd.concat([productive["machine_time"], labor_per_op], axis=1).max(axis=1)
        valid = ctr > 0
        if not valid.any():
            continue

        cap_final = (p_hours_eff * productive.loc[valid, "stations"]) / ctr[valid]

        if cap_final.empty or cap_final.min() <= 0:
            continue

        cap_u = float(cap_final.min())
        cap_h = cap_u * total_cycle

        total_cap_u += cap_u
        total_cap_h += cap_h

    return {
        "cap_u_sem": total_cap_u,
        "cap_h_sem": total_cap_h,
        "weeks_equiv": p_weeks_equiv,
    }


# =========================================================
# Carga global multiplanta (cacheada a nivel de módulo)
# =========================================================
@st.cache_data(ttl=300)
def load_all_plants_data():
    """Carga datos de todas las plantas para el análisis global."""
    all_plants = load_table("plants")
    all_settings = load_table("settings")
    all_models = load_table("models")
    all_times = load_table("models_process_times")
    all_stations = load_table("lines_process_stations")
    all_compat = load_table("compatibility")

    return {
        "plants": all_plants,
        "settings": all_settings,
        "models": all_models,
        "times": all_times,
        "stations": all_stations,
        "compat": all_compat,
    }


# =========================================================
# 0) GLOBAL - VISIÓN MULTIPLANTA
# =========================================================

if st.session_state.active_tab == "🌐 Global":
    st.subheader("🌐 Visión Global Multiplanta")
    st.info("Esta vista muestra información agregada de **TODAS las plantas** simultáneamente, independiente del selector de planta del sidebar.")
    
    # --- Cargar TODOS los datos de TODAS las plantas ---
    all_data = load_all_plants_data()

    # --- Calcular capacidad para TODAS las plantas ---
    # Selector global de turnos (solo afecta a esta pestaña)
    st.markdown("### 📊 Selector de Escenario")
    
    col_esc1, col_esc2, col_esc3 = st.columns([1, 1, 2])
    with col_esc1:
        escenario = st.radio(
            "Escenario de capacidad:",
            ["Máximo", "Promedio", "Mínimo"],
            index=1,  # Promedio por defecto
            horizontal=True,
            key="global_escenario"
        )
    with col_esc2:
        turnos_option = st.radio(
            "Turnos (simulación global):",
            ["Config. actual", "1 turno", "2 turnos", "3 turnos"],
            index=0,
            horizontal=True,
            key="global_turnos"
        )
    
    # Mapear selección de turnos a valor numérico (None = usar config de cada planta)
    _turnos_map = {"Config. actual": None, "1 turno": 1, "2 turnos": 2, "3 turnos": 3}
    shifts_override = _turnos_map[turnos_option]
    
    # TIMING A — compute_all_plants_structural_capacity (todas las plantas)
    _t0_A = time.perf_counter()
    global_results = compute_all_plants_structural_capacity(all_data, shifts_override)
    _ms_A = round((time.perf_counter() - _t0_A) * 1000, 1)
    with st.expander("⏱ Tiempos [staging]", expanded=False):
        st.caption(f"compute_all_plants_structural_capacity × {len(global_results)} plantas: **{_ms_A} ms**")
        st.caption("< 10 ms = cache hit  |  > 200 ms = miss o trabajo real")

    # Mapear escenario a columnas
    esc_map = {
        "Máximo": ("max_u_sem", "max_u_year", "max_h_sem", "max_h_year"),
        "Promedio": ("prom_u_sem", "prom_u_year", "prom_h_sem", "prom_h_year"),
        "Mínimo": ("min_u_sem", "min_u_year", "min_h_sem", "min_h_year"),
    }
    u_sem_col, u_year_col, h_sem_col, h_year_col = esc_map[escenario]
    
    if shifts_override:
        st.caption(f"⚠️ Simulación: todas las plantas con **{shifts_override} turno(s)**")
    
    st.divider()
    
    # =====================================================
    # 2️⃣ RESUMEN GLOBAL DE CAPACIDAD
    # =====================================================
    st.markdown("### 📈 Resumen Global de Capacidad")
    st.caption(f"Escenario: **{escenario}**" + (f" | Turnos: **{shifts_override}**" if shifts_override else ""))
    
    # Construir DataFrame de resumen
    resumen_rows = []
    for r in global_results:
        resumen_rows.append({
            "PLANTA": r["plant_name"],
            "LÍNEAS": r["lines_count"],
            "CAP. LÍNEA (uds/sem)": r[u_sem_col],
            "CAP. LÍNEA (uds/año)": r[u_year_col],
            "CAPACIDAD (h/sem)": r[h_sem_col],
            "CAPACIDAD (h/año)": r[h_year_col],
        })
    
    resumen_df = pd.DataFrame(resumen_rows)
    
    # Añadir fila TOTAL
    total_row = {
        "PLANTA": "TOTAL",
        "LÍNEAS": int(resumen_df["LÍNEAS"].sum()),
        "CAP. LÍNEA (uds/sem)": resumen_df["CAP. LÍNEA (uds/sem)"].sum(),
        "CAP. LÍNEA (uds/año)": resumen_df["CAP. LÍNEA (uds/año)"].sum(),
        "CAPACIDAD (h/sem)": resumen_df["CAPACIDAD (h/sem)"].sum(),
        "CAPACIDAD (h/año)": resumen_df["CAPACIDAD (h/año)"].sum(),
    }
    resumen_df = pd.concat([resumen_df, pd.DataFrame([total_row])], ignore_index=True)
    
    # Estilo para la tabla
    def style_resumen(df):
        def highlight_total(row):
            if row["PLANTA"] == "TOTAL":
                return ["font-weight: bold; background-color: #f0f0f0;"] * len(row)
            return [""] * len(row)
        return df.style.apply(highlight_total, axis=1).format({
            "CAP. LÍNEA (uds/sem)": "{:.1f}",
            "CAP. LÍNEA (uds/año)": "{:.1f}",
            "CAPACIDAD (h/sem)": "{:.1f}",
            "CAPACIDAD (h/año)": "{:.1f}",
        })
    
    st.dataframe(style_resumen(resumen_df), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # =====================================================
    # 3️⃣ DISPONIBILIDAD Y % USO
    # =====================================================
    st.markdown("### ⚡ Capacidad vs Disponibilidad")
    st.caption("Introduce la disponibilidad anual (horas) para cada planta.")
    
    # Inicializar disponibilidad en session_state
    if "global_disponibilidad" not in st.session_state:
        st.session_state.global_disponibilidad = {}
    
    # Crear inputs de disponibilidad
    disp_cols = st.columns(min(len(global_results), 4))
    for i, r in enumerate(global_results):
        col_idx = i % len(disp_cols)
        with disp_cols[col_idx]:
            default_disp = st.session_state.global_disponibilidad.get(r["plant_name"], r["max_h_year"] * 1.2)
            disp_value = st.number_input(
                f"Disp. {r['plant_name']} (h/año)",
                min_value=0.0,
                value=float(default_disp),
                step=1000.0,
                key=f"disp_{r['plant_name']}"
            )
            st.session_state.global_disponibilidad[r["plant_name"]] = disp_value
    
    # Tabla Capacidad vs Disponibilidad
    cap_disp_rows = []
    for r in global_results:
        cap_h_year = r[h_year_col]
        disp_h_year = st.session_state.global_disponibilidad.get(r["plant_name"], 0.0)
        pct_uso = (cap_h_year / disp_h_year * 100) if disp_h_year > 0 else 0.0
        
        cap_disp_rows.append({
            "PLANTA": r["plant_name"],
            "Capacidad (h/año)": cap_h_year,
            "Disponibilidad (h/año)": disp_h_year,
            "% USO CAPACIDAD": pct_uso,
        })
    
    cap_disp_df = pd.DataFrame(cap_disp_rows)
    
    # Añadir total
    total_cap = cap_disp_df["Capacidad (h/año)"].sum()
    total_disp = cap_disp_df["Disponibilidad (h/año)"].sum()
    total_pct = (total_cap / total_disp * 100) if total_disp > 0 else 0.0
    
    cap_disp_df = pd.concat([cap_disp_df, pd.DataFrame([{
        "PLANTA": "TOTAL",
        "Capacidad (h/año)": total_cap,
        "Disponibilidad (h/año)": total_disp,
        "% USO CAPACIDAD": total_pct,
    }])], ignore_index=True)
    
    def style_cap_disp(df):
        def color_pct(val):
            try:
                v = float(val)
                if v >= 100:
                    return "color: red; font-weight: bold;"
                elif v >= 80:
                    return "color: orange; font-weight: bold;"
                else:
                    return "color: green; font-weight: bold;"
            except:
                return ""
        
        def highlight_total(row):
            if row["PLANTA"] == "TOTAL":
                return ["font-weight: bold; background-color: #f0f0f0;"] * len(row)
            return [""] * len(row)
        
        return df.style.apply(highlight_total, axis=1).map(
            color_pct, subset=["% USO CAPACIDAD"]
        ).format({
            "Capacidad (h/año)": "{:,.1f}",
            "Disponibilidad (h/año)": "{:,.1f}",
            "% USO CAPACIDAD": "{:.1f}%",
        })
    
    st.dataframe(style_cap_disp(cap_disp_df), use_container_width=True, hide_index=True)
    
    # Gráfico de barras
    fig_cap_disp = go.Figure()
    plants_no_total = [r["PLANTA"] for r in cap_disp_rows]
    caps = [r["Capacidad (h/año)"] for r in cap_disp_rows]
    disps = [r["Disponibilidad (h/año)"] for r in cap_disp_rows]
    
    fig_cap_disp.add_bar(x=plants_no_total, y=caps, name="Capacidad", marker_color="#A6192E")
    fig_cap_disp.add_bar(x=plants_no_total, y=disps, name="Disponibilidad", marker_color="#2E75B6")
    fig_cap_disp.update_layout(
        barmode="group",
        title="Capacidad vs Disponibilidad por Planta (h/año)",
        height=400,
    )
    st.plotly_chart(fig_cap_disp, use_container_width=True, key="chart_cap_disp_global")
    
    st.divider()
    
    # =====================================================
    # 4️⃣ RESUMEN POR MODELO
    # =====================================================
    st.markdown("### 🔧 Capacidad por Modelo")
    
    # Obtener todos los modelos activos de todas las plantas
    all_active_models = set()
    for _, plant_row in all_data["plants"].iterrows():
        p_id = int(plant_row["id"])
        p_models = all_data["models"][all_data["models"]["plant_id"] == p_id]
        p_models = ensure_int(p_models.copy(), ["active"])
        active_m = p_models.loc[p_models["active"] == 1, "model"].astype(str).str.strip().tolist()
        all_active_models.update(active_m)
    
    all_active_models = sorted(list(all_active_models))
    
    if all_active_models:
        selected_model = st.selectbox(
            "Seleccionar modelo:",
            ["Todos los modelos"] + all_active_models,
            key="global_model_filter"
        )
        
        if selected_model != "Todos los modelos":
            # Mostrar capacidad del modelo seleccionado en todas las plantas
            model_rows = []
            for _, plant_row in all_data["plants"].iterrows():
                p_id = int(plant_row["id"])
                p_name = str(plant_row["name"])
                
                cap_data = compute_model_capacity_by_plant(selected_model, p_id, all_data, shifts_override=shifts_override)
                
                model_rows.append({
                    "PLANTA": p_name,
                    "Capacidad (uds/sem)": cap_data["cap_u_sem"],
                    "Capacidad (uds/año)": cap_data["cap_u_sem"] * cap_data.get("weeks_equiv", 50),
                    "Capacidad (h/sem)": cap_data["cap_h_sem"],
                    "Capacidad (h/año)": cap_data["cap_h_sem"] * cap_data.get("weeks_equiv", 50),
                })
            
            model_df = pd.DataFrame(model_rows)
            
            # Añadir total
            model_df = pd.concat([model_df, pd.DataFrame([{
                "PLANTA": "TOTAL",
                "Capacidad (uds/sem)": model_df["Capacidad (uds/sem)"].sum(),
                "Capacidad (uds/año)": model_df["Capacidad (uds/año)"].sum(),
                "Capacidad (h/sem)": model_df["Capacidad (h/sem)"].sum(),
                "Capacidad (h/año)": model_df["Capacidad (h/año)"].sum(),
            }])], ignore_index=True)
            
            st.markdown(f"**Modelo seleccionado:** {selected_model}")
            st.dataframe(
                model_df.style.format({
                    "Capacidad (uds/sem)": "{:.1f}",
                    "Capacidad (uds/año)": "{:.1f}",
                    "Capacidad (h/sem)": "{:.1f}",
                    "Capacidad (h/año)": "{:.1f}",
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Selecciona un modelo específico para ver su capacidad en todas las plantas.")
    else:
        st.warning("No hay modelos activos en ninguna planta.")
    
    st.divider()
    
    # =====================================================
    # 5️⃣ PANEL DE MODIFICACIONES
    # =====================================================
    col_left, col_right = st.columns([2, 1])
    
    with col_right:
        st.markdown("### 🔧 Modificaciones Necesarias")
        st.caption("Registro de mejoras planificadas")
        
        # Inicializar modificaciones en session_state
        if "global_modificaciones" not in st.session_state:
            st.session_state.global_modificaciones = []
        
        # Mostrar modificaciones existentes
        for i, mod in enumerate(st.session_state.global_modificaciones):
            with st.expander(f"📌 {mod['nombre']}", expanded=False):
                st.write(f"**Planta:** {mod['planta']}")
                st.write(f"**Horas estimadas:** {mod['horas']} h")
                if st.button("🗑️ Eliminar", key=f"del_mod_{i}"):
                    st.session_state.global_modificaciones.pop(i)
                    st.rerun()
        
        # Añadir nueva modificación
        with st.expander("➕ Añadir modificación", expanded=False):
            new_mod_nombre = st.text_input("Nombre de la modificación", key="new_mod_nombre")
            new_mod_planta = st.selectbox(
                "Planta",
                [p["name"] for _, p in all_data["plants"].iterrows()],
                key="new_mod_planta"
            )
            new_mod_horas = st.number_input("Horas estimadas", min_value=0, value=10, key="new_mod_horas")
            
            if st.button("Añadir", key="btn_add_mod"):
                if new_mod_nombre.strip():
                    st.session_state.global_modificaciones.append({
                        "nombre": new_mod_nombre.strip(),
                        "planta": new_mod_planta,
                        "horas": new_mod_horas,
                    })
                    st.rerun()
        
        # Resumen de hitos
        st.markdown("---")
        st.markdown("### 📊 Resumen de Hitos")
        total_mods = len(st.session_state.global_modificaciones)
        total_horas_mods = sum(m["horas"] for m in st.session_state.global_modificaciones)
        
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            st.metric("Nº Hitos", total_mods)
        with col_h2:
            st.metric("Horas Totales", f"{total_horas_mods} h")
    
    with col_left:
        # =====================================================
        # 6️⃣ % USO LÍNEAS POR PLANTA
        # =====================================================
        st.markdown("### 📊 Distribución de Capacidad por Planta")
        
        # Gráfico de tarta
        plant_names_chart = [r["plant_name"] for r in global_results if r[h_year_col] > 0]
        plant_caps_chart = [r[h_year_col] for r in global_results if r[h_year_col] > 0]
        
        if plant_caps_chart:
            fig_pie = go.Figure(go.Pie(
                labels=plant_names_chart,
                values=plant_caps_chart,
                hole=0.4,
                textinfo="label+percent",
                marker=dict(colors=px.colors.qualitative.Set2),
            ))
            fig_pie.update_layout(
                title=f"Distribución de Capacidad ({escenario}) - h/año",
                height=400,
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="chart_pie_global")
        
        # Tabla de % uso líneas
        st.markdown("### 📋 Uso de Líneas por Planta")
        
        uso_lineas_rows = []
        total_lineas = sum(r["lines_count"] for r in global_results)
        
        for r in global_results:
            pct_lineas = (r["lines_count"] / total_lineas * 100) if total_lineas > 0 else 0
            uso_lineas_rows.append({
                "PLANTA": r["plant_name"],
                "Nº Líneas": r["lines_count"],
                "% del Total": pct_lineas,
                "Cap. Media/Línea (h/sem)": r[h_sem_col] / r["lines_count"] if r["lines_count"] > 0 else 0,
            })
        
        uso_lineas_df = pd.DataFrame(uso_lineas_rows)
        st.dataframe(
            uso_lineas_df.style.format({
                "% del Total": "{:.1f}%",
                "Cap. Media/Línea (h/sem)": "{:.1f}",
            }),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# 1) PLANIFICACIÓN
# =========================================================

if st.session_state.active_tab == "📊 Planificación":
    st.subheader("Selección de modelo por línea")

    # Session state anidado por planta: line_model[plant_id][line_id], line_demand[plant_id][line_id]
    if "line_model" not in st.session_state:
        st.session_state.line_model = {}
    if "line_demand" not in st.session_state:
        st.session_state.line_demand = {}

    _pid = st.session_state["plant_id"]
    if _pid not in st.session_state.line_model:
        st.session_state.line_model[_pid] = {}
    if _pid not in st.session_state.line_demand:
        st.session_state.line_demand[_pid] = {}

    colL, colR = st.columns([1.1, 1.0], gap="large")

    with colL:
        st.markdown("### Selección")
        for nave in sorted(stations_df["nave"].astype(str).str.strip().unique().tolist()):
            st.markdown(f"#### NAVE {nave}")
            nave_line_ids = sorted(
                stations_df.loc[stations_df["nave"] == nave, "line_id"]
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

            for line_id in nave_line_ids:
                allowed = allowed_by_line.get(line_id, [])
                if not allowed:
                    st.info(f"{line_id}: sin modelos compatibles activos (revisa compatibilidades/modelos).")
                    continue

                default_model = (
                    st.session_state.line_model
                    .get(_pid, {})
                    .get(line_id, allowed[0])
                )
                if default_model not in allowed:
                    default_model = allowed[0]

                m = st.selectbox(
                    f"Modelo ({line_id})",
                    options=allowed,
                    index=allowed.index(default_model),
                    key=f"sel_model_{_pid}_{line_id}"
                )
                st.session_state.line_model[_pid][line_id] = m

    with colR:
        st.markdown("### Demanda (UDS/SEM)")
        for nave in sorted(stations_df["nave"].astype(str).str.strip().unique().tolist()):
            st.markdown(f"#### NAVE {nave}")
            nave_line_ids = sorted(
                stations_df.loc[stations_df["nave"] == nave, "line_id"]
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )
            for line_id in nave_line_ids:
                model = (
                    st.session_state.line_model
                    .get(_pid, {})
                    .get(line_id)
                )
                if not model:
                    continue
                d = st.number_input(
                    f"Demanda ({line_id} – {model})",
                    min_value=0.0,
                    value=float(
                        st.session_state.line_demand
                        .get(_pid, {})
                        .get(line_id, 0.0)
                    ),
                    step=1.0,
                    key=f"demand_{_pid}_{line_id}",
                )
                st.session_state.line_demand[_pid][line_id] = d

# =========================================================
# 2) CONFIGURACIÓN (POWER USER)
# =========================================================
if st.session_state.active_tab == "⚙️ Configuración (Power User)":
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

    if st.session_state.get("models_saved"):
        st.success("Modelos guardados")
        st.session_state["models_saved"] = False

    st.divider()

    # --- B) Tiempos por modelo y proceso
    st.markdown("## Tiempos por modelo y proceso (models_process_times.csv)")

    st.info(
        "**Machine time** = tiempo automático fijo no reducible "
        "(test automático, horno, robot, ciclo máquina). No depende del nº de operarios.\n\n"
        "**Labor time** = horas-hombre secuenciales necesarias por unidad "
        "(preparación, conexión, montaje manual, supervisión, retirada).\n\n"
        "La capacidad se calcula mediante:\n\n"
        "`cycle_time_real = max(machine_time, labor_time / operarios)`\n\n"
        "`capacity = (horas_efectivas × estaciones) / cycle_time_real`"
        "\n\nEn procesos manuales puros, machine_time puede ser 0."
    )

    edited_times = st.data_editor(
        times_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "cycle_time": st.column_config.NumberColumn(
                "cycle_time",
                help="Tiempo de ciclo legacy (HH/ud). Se mantiene por compatibilidad.",
                min_value=0.0,
                step=0.01,
                format="%.2f"
            ),
            "machine_time": st.column_config.NumberColumn(
                "machine_time",
                help="Tiempo automático fijo no reducible (HH/ud). Puede ser 0 en procesos manuales.",
                min_value=0.0,
                step=0.01,
                format="%.2f"
            ),
            "labor_time": st.column_config.NumberColumn(
                "labor_time",
                help="Horas-hombre secuenciales necesarias por unidad (HH/ud).",
                min_value=0.0,
                step=0.01,
                format="%.2f"
            ),
        }
    )

    if st.button("💾 Guardar tiempos"):
        out = edited_times.copy()
        out = out.reset_index(drop=True)
        out["model"] = out["model"].astype(str).str.strip()
        out["process"] = out["process"].astype(str).str.strip()
        out["cycle_time"] = pd.to_numeric(out["cycle_time"], errors="coerce").fillna(0.0)

        # machine_time y labor_time: si vienen vacíos, convertir a 0.0
        # IMPORTANTE: machine_time = 0 es válido en procesos manuales
        if "machine_time" in out.columns:
            out["machine_time"] = pd.to_numeric(out["machine_time"], errors="coerce").fillna(0.0)
        else:
            out["machine_time"] = 0.0

        if "labor_time" in out.columns:
            out["labor_time"] = pd.to_numeric(out["labor_time"], errors="coerce").fillna(0.0)
        else:
            out["labor_time"] = 0.0

        # evitar duplicados modelo-proceso
        out = out.drop_duplicates(subset=["model", "process"])
        out["plant_id"] = plant_id

        # Validación mínima: avisar si algún proceso tiene ambos tiempos a 0
        if "machine_time" in out.columns and "labor_time" in out.columns:
            bad = out[(out["machine_time"] == 0.0) & (out["labor_time"] == 0.0)]
            if not bad.empty:
                st.session_state["times_warning"] = (
                    f"⚠️ {len(bad)} proceso(s) con machine_time=0 y labor_time=0. "
                    "Esos procesos tendrán capacidad calculada = 0."
                )

        save_table(out, "models_process_times")

        st.session_state["times_saved"] = True

    if st.session_state.get("times_warning"):
        st.warning(st.session_state["times_warning"])
        st.session_state["times_warning"] = None

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
        out["nave"] = out["nave"].astype(str).str.strip()
        out["process"] = out["process"].astype(str).str.strip()
        out["stations"] = pd.to_numeric(out["stations"], errors="coerce").fillna(0.0)
        out["operators_per_station"] = pd.to_numeric(out["operators_per_station"], errors="coerce").fillna(0.0)
        # Reconstruir line_id para mantener coherencia
        out["line_id"] = out["nave"] + "-" + out["line"]
        out["plant_id"] = plant_id

        # Validación mínima: avisar si hay filas con stations=0
        zero_st = out[out["stations"] == 0.0]
        if not zero_st.empty:
            st.session_state["stations_warning"] = (
                f"⚠️ {len(zero_st)} fila(s) con stations=0. "
                "Esas filas serán ignoradas en el cálculo de capacidad."
            )

        save_table(out, "lines_process_stations")

        st.session_state["stations_saved"] = True

    if st.session_state.get("stations_warning"):
        st.warning(st.session_state["stations_warning"])
        st.session_state["stations_warning"] = None

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

    for line_id in all_line_ids:

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
                    key=f"compat_{plant_id}_{line_id}_{m}"
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

    if st.session_state.get("compat_saved"):
        st.success("Compatibilidades guardadas")
        st.session_state["compat_saved"] = False

# =========================================================
# 3) RESULTADOS
# =========================================================

def _apply_capacity(merged: pd.DataFrame, h_eff: float) -> pd.DataFrame:
    """Calcula capacidad usando cycle_time_real = max(machine_time, labor_time/operators).
    capacity = (h_eff * stations) / cycle_time_real"""
    m = merged.copy()
    m["stations"] = pd.to_numeric(m["stations"], errors="coerce").fillna(0)
    m["operators_per_station"] = pd.to_numeric(m["operators_per_station"], errors="coerce").fillna(0).clip(lower=1.0)

    for col in ("machine_time", "labor_time"):
        if col in m.columns:
            m[col] = pd.to_numeric(m[col], errors="coerce").fillna(0.0)
        else:
            m[col] = 0.0

    m["labor_per_operator"] = m["labor_time"] / m["operators_per_station"]
    m["cycle_time_real"] = m[["machine_time", "labor_per_operator"]].max(axis=1)

    m["capacity"] = 0.0
    mask = (m["cycle_time_real"] > 0) & (m["stations"] > 0)
    m.loc[mask, "capacity"] = (h_eff * m.loc[mask, "stations"]) / m.loc[mask, "cycle_time_real"]

    return m


@st.cache_data(show_spinner=False)
def _compute_line_base(
    line_id: str,
    model: str,
    times_df_param: pd.DataFrame,
    stations_df_param: pd.DataFrame,
) -> pd.DataFrame:
    """Merge + normalización + cycle_time_real, sin hours_eff.
    Caché estable ante cambios de sliders (disponibilidad, eficiencia, turnos).
    Llamada internamente por compute_line_detail."""
    t = times_df_param[times_df_param["model"] == model].copy()
    s = stations_df_param[stations_df_param["line_id"] == line_id].copy()
    merged = pd.merge(s, t, on="process", how="inner")
    if merged.empty:
        return merged
    m = merged.copy()
    m["stations"] = pd.to_numeric(m["stations"], errors="coerce").fillna(0)
    m["operators_per_station"] = pd.to_numeric(m["operators_per_station"], errors="coerce").fillna(0).clip(lower=1.0)
    for col in ("machine_time", "labor_time"):
        if col in m.columns:
            m[col] = pd.to_numeric(m[col], errors="coerce").fillna(0.0)
        else:
            m[col] = 0.0
    m["labor_per_operator"] = m["labor_time"] / m["operators_per_station"]
    m["cycle_time_real"] = m[["machine_time", "labor_per_operator"]].max(axis=1)
    return m


@st.cache_data(show_spinner=False)
def compute_line_detail(
    line_id: str,
    model: str,
    times_df_param: pd.DataFrame,
    stations_df_param: pd.DataFrame,
    hours_eff_param: float,
) -> tuple[pd.DataFrame, str, float]:
    """
    Devuelve:
    - merged detail DF con capacity por proceso
    - bottleneck process (min capacity)
    - capacity_total_week (uds/sem) (cap del cuello)

    El trabajo pesado (merge + normalización) lo hace _compute_line_base,
    que cachea sin hours_eff. Solo la multiplicación final depende de hours_eff_param.
    """
    base = _compute_line_base(line_id, model, times_df_param, stations_df_param)

    if base.empty:
        return base, "", 0.0

    merged = base.copy()
    merged["capacity"] = 0.0
    mask = (merged["cycle_time_real"] > 0) & (merged["stations"] > 0)
    merged.loc[mask, "capacity"] = (hours_eff_param * merged.loc[mask, "stations"]) / merged.loc[mask, "cycle_time_real"]

    # Solo considerar procesos productivos para el cuello de botella:
    productive = merged[mask].copy()

    if productive.empty or productive["capacity"].dropna().empty:
        return merged, "", 0.0

    bottleneck_row = productive.loc[productive["capacity"].idxmin()]
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
    if "cycle_time" in m.columns:
        m["cycle_time"] = pd.to_numeric(m["cycle_time"], errors="coerce").fillna(0.0)
    else:
        m["cycle_time"] = 0.0

    hours_proc = output_units * m["cycle_time"]
    hours_proc = pd.to_numeric(hours_proc, errors="coerce").fillna(0.0)

    return float(hours_proc.sum())


@st.cache_data(show_spinner=False)
def _precompute_all_bases_for_tab4(
    times_df: pd.DataFrame,
    stations_df: pd.DataFrame,
    line_ids_tuple: tuple,
    allowed_by_line_tuple: tuple,
) -> dict:
    """Pre-computa merge+normalize para todas las combinaciones (line_id, model) de Tab 4.
    times_df y stations_df se hashean UNA SOLA VEZ en lugar de N×M veces.
    Sin hours_eff → caché estable ante cambios de sliders (disponibilidad, eficiencia, turnos)."""
    allowed_dict = {k: list(v) for k, v in allowed_by_line_tuple}
    result = {}
    for line_id in line_ids_tuple:
        models = allowed_dict.get(line_id, [])
        if not models:
            continue
        s = stations_df[stations_df["line_id"] == line_id].copy()
        if s.empty:
            continue
        s["stations"] = pd.to_numeric(s["stations"], errors="coerce").fillna(0)
        s["operators_per_station"] = pd.to_numeric(s["operators_per_station"], errors="coerce").fillna(0).clip(lower=1.0)
        for m in models:
            t = times_df[times_df["model"] == m].copy()
            merged = pd.merge(s, t, on="process", how="inner")
            if merged.empty:
                continue
            for col in ("machine_time", "labor_time"):
                if col in merged.columns:
                    merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)
                else:
                    merged[col] = 0.0
            merged["labor_per_operator"] = merged["labor_time"] / merged["operators_per_station"]
            merged["cycle_time_real"] = merged[["machine_time", "labor_per_operator"]].max(axis=1)
            result[(line_id, m)] = merged
    return result


if st.session_state.active_tab == "📈 Resultados":
    st.subheader("Resultados de capacidad")
    st.caption(f"Horas efectivas planta: {hours_eff:.2f} h/semana")

    summary_rows = []
    detail_by_line = {}

    all_line_ids = sorted(
        stations_df["line_id"]
        .astype(str)
        .str.strip()
        .unique()
       .tolist()
    )

    _tc = times_df.copy()
    _tc["cycle_time"] = pd.to_numeric(_tc["cycle_time"], errors="coerce").fillna(0.0)
    cycle_time_by_model = _tc.groupby("model")["cycle_time"].sum().to_dict()

    # TIMING C — compute_line_detail × líneas asignadas (Tab Resultados)
    _t0_C = time.perf_counter()
    for line_id in all_line_ids:

        parts = line_id.split("-", 1)

        if len(parts) == 2:
            nave, base_line = parts
        else:
            nave = "N1"
            base_line = parts[0]

        model = (
            st.session_state.line_model
            .get(st.session_state["plant_id"], {})
            .get(line_id)
        )
        if not model:
            continue

        demand_week = float(
            st.session_state.line_demand
            .get(st.session_state["plant_id"], {})
            .get(line_id, 0.0)
        )

        merged, bottleneck_proc, cap_week = compute_line_detail(line_id, model, times_df, stations_df, hours_eff)

        saturation = 0.0
        deficit = 0.0
        if cap_week > 0:
            saturation = (demand_week / cap_week) * 100.0
            deficit = max(0.0, demand_week - cap_week)

        demand_year = demand_week * weeks_equiv
        cap_year = cap_week * weeks_equiv

        total_cycle_time_model = cycle_time_by_model.get(model, 0.0)

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

    _ms_C = round((time.perf_counter() - _t0_C) * 1000, 1)
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

        s = s.map(sat_color, subset=["Saturación (%)"])
        s = s.map(lambda _: "color: red; font-weight: 700;", subset=["bottleneck"])

        # Detectar fila TOTAL por columna 'line' (ya que display_cols no incluye line_id)
        def _style_total(row):
            if str(row.get("line", "")) == "TOTAL":
                return ["font-weight: bold; font-size: 16px; background-color: #f0f0f0;"] * len(row)
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
                productive_m = merged[(merged["cycle_time_real"] > 0) & (merged["stations"] > 0)]
                if not productive_m.empty:
                    cap_week = float(productive_m["capacity"].min())

            header = f"{nave}-{base_line} — Modelo: {model} | Capacidad máx: {cap_week:.2f} uds/sem | Cuello: {bottleneck_proc} | Demanda: {demand_week:.2f} uds/sem"
            with st.expander(header, expanded=False):
                if merged is None or merged.empty:
                    st.warning("No hay datos suficientes (revisa estaciones o tiempos).")
                else:
                    _detail_cols = ["process", "stations", "operators_per_station"]
                    if "machine_time" in merged.columns:
                        _detail_cols.append("machine_time")
                    if "labor_time" in merged.columns:
                        _detail_cols.append("labor_time")
                    if "labor_per_operator" in merged.columns:
                        _detail_cols.append("labor_per_operator")
                    if "cycle_time_real" in merged.columns:
                        _detail_cols.append("cycle_time_real")
                    _detail_cols.append("capacity")
                    show = merged[[c for c in _detail_cols if c in merged.columns]].copy()
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

    st.divider()
    st.markdown("## 📊 Representación gráfica de Demanda vs Capacidad")

    if not summary_df.empty:
        df_plot = summary_df.copy()
        df_plot = df_plot[df_plot["line_id"] != "TOTAL"].copy()

        line_order = sorted(df_plot["line_id"].astype(str).unique().tolist())

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

    with st.expander("⏱ Tiempos [staging]", expanded=False):
        st.caption(f"Loop compute_line_detail (Tab Resultados, líneas asignadas): **{_ms_C} ms**")
        st.caption("< 10 ms = cache hit  |  > 200 ms = miss o trabajo real")


if st.session_state.active_tab == "🧭 Capacidad según mix":
    st.subheader("Capacidad según mix")
    st.info(
        "La planta produce **horas configurables**.\n"
        "La capacidad no es un valor fijo, sino un **rango estructural** determinado por el mix posible de modelos en cada línea.\n"
        "Aquí se muestran los valores **Máximo / Promedio / Mínimo** por planta y por línea, en unidades y en horas (semana y año)."
    )

    _t = times_df.copy()
    _t["cycle_time"] = pd.to_numeric(_t["cycle_time"], errors="coerce").fillna(0.0)
    cycle_by_model = _t.groupby("model")["cycle_time"].sum().to_dict()

    line_stats_rows = []
    capH_line_model = {}
    capU_line_model = {}
    max_h_week_by_line = {}

    # TIMING B — precompute + loop Tab 4 (Capacidad según mix)
    _t0_B = time.perf_counter()

    # Pre-computar bases UNA VEZ: times_df y stations_df hasheados 1 vez en lugar de N×M
    _all_bases = _precompute_all_bases_for_tab4(
        times_df,
        stations_df,
        tuple(sorted(line_ids_nave)),
        tuple(sorted((k, tuple(v)) for k, v in allowed_by_line.items())),
    )

    for line_id in line_ids_nave:

        parts = line_id.split("-", 1)

        if len(parts) == 2:
            nave, base_line = parts
        else:
            nave = "N1"
            base_line = parts[0]

        models_allowed = allowed_by_line.get(line_id, [])
        if not models_allowed:
            continue

        capU_vals = []
        capH_vals = []
        model_for_capH = []

        for m in models_allowed:
            _base = _all_bases.get((line_id, m))
            if _base is None or _base.empty:
                continue
            _prod = _base[(_base["cycle_time_real"] > 0) & (_base["stations"] > 0)]
            if _prod.empty:
                continue
            _cap_vals = (hours_eff * _prod["stations"]) / _prod["cycle_time_real"]
            cap_week = float(_cap_vals.min()) if not _cap_vals.empty and _cap_vals.min() > 0 else 0.0
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

        max_u = float(np.max(capU_vals))
        min_u = float(np.min(capU_vals))
        avg_u = float(np.mean(capU_vals))

        max_h = float(np.max(capH_vals))
        min_h = float(np.min(capH_vals))
        avg_h = float(np.mean(capH_vals))
        max_h_week_by_line[line_id] = max_h

        idx_max_h = int(np.argmax(capH_vals))
        idx_min_h = int(np.argmin(capH_vals))
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

    _ms_B = round((time.perf_counter() - _t0_B) * 1000, 1)
    with st.expander("⏱ Tiempos [staging]", expanded=False):
        st.caption(f"Loop compute_line_detail (Tab Capacidad según mix, N×M): **{_ms_B} ms**")
        st.caption("< 10 ms = cache hit  |  > 200 ms = miss o trabajo real")

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
            for line_id in line_ids_nave:
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

                palette = px.colors.qualitative.Plotly

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

                            # Uso del potenciómetro (% del recorrido del slider)
                            pct_of_slider = (sel_pct / max_pct * 100.0) if max_pct > 0 else 0.0
                            st.caption(f"🎚️ Uso del potenciómetro: **{pct_of_slider:.0f}%**")

                            # Equivalencias dinámicas
                            st.markdown(
                                f"<div style='background:#f8f9fa;padding:8px 12px;border-radius:6px;font-size:13px;margin-bottom:8px;'>"
                                f"<b>Equivalente aproximado</b><br>"
                                f"Uds/sem: <b>{sel_u_week:.2f}</b> · Uds/año: <b>{sel_u_year:.2f}</b><br>"
                                f"h/sem: <b>{sel_h_week:.2f}</b> · h/año: <b>{sel_h_year:.2f}</b>"
                                f"</div>",
                                unsafe_allow_html=True
                            )

                            max_u_week = (maxH / w_m) if w_m > 0 else 0.0
                            max_u_year = max_u_week * float(weeks_equiv)

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
