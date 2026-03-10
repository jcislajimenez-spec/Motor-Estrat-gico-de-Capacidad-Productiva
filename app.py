import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import psycopg2
import plotly.graph_objects as go
import plotly.express as px

# --- Configuración de página ---
st.set_page_config(
    page_title="Planificador de Capacidad Ingeteam",
    layout="wide"
)

def resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

# --- Conexión a base de datos ---
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL)

@st.cache_data(ttl=60)
def run_query(query: str):
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# --- Estilos Corporativos ---
st.markdown("""
<style>
    .main { background-color: #FFFFFF; }
    h1, h2, h3 { color: #A6192E; font-family: "Trade Gothic", sans-serif; font-weight: bold; }
    .stMetric { background-color: #F8F9FA; padding: 15px; border-radius: 10px; border-left: 5px solid #A6192E; }
</style>
""", unsafe_allow_html=True)

# --- Carga de Logo ---
try:
    ASSETS_DIR = resource_path("assets")
    logo = Image.open(os.path.join(ASSETS_DIR, "ingeteam_logo.jpg"))
    st.sidebar.image(logo, use_container_width=True)
except:
    st.sidebar.title("INGETEAM")

# =========================================================
# IO FUNCTIONS
# =========================================================
def load_table(table: str) -> pd.DataFrame:
    if not DATABASE_URL:
        # Fallback a CSV si no hay DB
        path = os.path.join(resource_path("data"), f"{table}.csv")
        return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    
    conn = get_connection()
    df = pd.read_sql(f'SELECT * FROM "{table}"', conn)
    conn.close()
    return df

def save_table(df: pd.DataFrame, table: str, plant_id_val: int = None):
    if not DATABASE_URL: return
    
    conn = get_connection()
    cols = list(df.columns)
    placeholders = ",".join(["%s"] * len(cols))
    col_list = ",".join([f'"{c}"' for c in cols])
    values = [tuple(None if pd.isna(v) else v for v in row) for row in df.itertuples(index=False, name=None)]

    with conn.cursor() as cur:
        if "plant_id" in cols and plant_id_val:
            cur.execute(f'DELETE FROM "{table}" WHERE plant_id = %s', (plant_id_val,))
        elif table != "plants": # No truncar la tabla de plantas
            cur.execute(f'TRUNCATE TABLE "{table}"')
        
        cur.executemany(f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})', values)
    conn.commit()
    conn.close()
    st.cache_data.clear()

# =========================================================
# SELECCIÓN DE PLANTA
# =========================================================
plants_df = load_table("plants")
if plants_df.empty:
    st.error("Base de datos vacía.")
    st.stop()

selected_plant_name = st.sidebar.selectbox("Seleccionar Planta", plants_df["name"].unique())
plant_id = int(plants_df.loc[plants_df["name"] == selected_plant_name, "id"].iloc[0])
st.session_state["plant_id"] = plant_id

# =========================================================
# PARÁMETROS Y DISPONIBILIDAD
# =========================================================
st.sidebar.header("Configuración de Disponibilidad")
settings_df = load_table("settings")
plant_settings = settings_df[settings_df["plant_id"] == plant_id]

if plant_settings.empty:
    defaults = {"hours_week": 40.0, "shifts": 2, "availability": 0.9, "efficiency": 0.85, "days_year": 250}
else:
    s = plant_settings.iloc[0]
    defaults = {"hours_week": s["hours_week"], "shifts": s["shifts"], "availability": s["availability"], "efficiency": s["efficiency"], "days_year": s.get("days_open_year", 250)}

h_week = st.sidebar.number_input("Horas/Semana", value=float(defaults["hours_week"]))
shifts = st.sidebar.number_input("Turnos", value=int(defaults["shifts"]))
avail = st.sidebar.slider("Disponibilidad", 0.0, 1.0, float(defaults["availability"]))
eff = st.sidebar.slider("Eficiencia", 0.0, 1.0, float(defaults["efficiency"]))

hours_eff_week = h_week * shifts * avail * eff
hours_eff_year = hours_eff_week * (defaults["days_year"] / 5) # Estimación anual

st.sidebar.metric("Disponibilidad Semanal", f"{hours_eff_week:.1f} h")
st.sidebar.metric("Disponibilidad Anual", f"{hours_eff_year:.0f} h")

# =========================================================
# TABS PRINCIPALES
# =========================================================
tabs = st.tabs(["🌍 Global", "📊 Planificación", "📈 Resultados", "🧭 Mix & Capacidad"])

# --- TAB GLOBAL (NUEVO) ---
with tabs[0]:
    st.header("🌍 Resumen Ejecutivo Global")
    
    all_settings = load_table("settings")
    all_plants = load_table("plants")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Plantas", len(all_plants))
    col2.metric("Disponibilidad Media", f"{all_settings['availability'].mean()*100:.1f}%")
    col3.metric("Eficiencia Media", f"{all_settings['efficiency'].mean()*100:.1f}%")

    st.subheader("Capacidad Máxima vs Mínima por Planta")
    # Aquí iría la lógica de agregación de todas las plantas
    st.dataframe(all_plants, use_container_width=True)

# --- TAB PLANIFICACIÓN (CORREGIDO) ---
with tabs[1]:
    st.subheader(f"Planificación: {selected_plant_name}")
    stations_df = load_table("lines_process_stations")
    plant_stations = stations_df[stations_df["plant_id"] == plant_id]
    
    if plant_stations.empty:
        st.warning("No hay líneas configuradas para esta planta.")
    else:
        # CORRECCIÓN: Filtrado correcto por Nave
        for nave_id in sorted(plant_stations["nave"].unique()):
            st.markdown(f"### 🏭 Nave {nave_id}")
            nave_lines = plant_stations[plant_stations["nave"] == nave_id]["line_id"].unique()
            
            cols = st.columns(len(nave_lines) if len(nave_lines) < 4 else 4)
            for i, l_id in enumerate(nave_lines):
                with cols[i % 4]:
                    st.selectbox(f"Modelo {l_id}", ["Modelo A", "Modelo B"], key=f"mod_{l_id}")
                    st.number_input(f"Demanda {l_id}", min_value=0, key=f"dem_{l_id}")

# --- TAB RESULTADOS ---
with tabs[2]:
    st.subheader("📈 Análisis de Capacidad vs Disponibilidad")
    
    # Simulación de datos para el summary solicitado
    res_data = {
        "Línea": ["L1", "L2", "L3"],
        "Capacidad (h/año)": [1500, 2000, 1800],
        "Disponibilidad (h/año)": [hours_eff_year] * 3,
        "Hitos": [2, 5, 3]
    }
    df_res = pd.DataFrame(res_data)
    df_res["Utilización %"] = (df_res["Capacidad (h/año)"] / df_res["Disponibilidad (h/año)"]) * 100
    
    st.dataframe(df_res.style.highlight_max(axis=0, color='#FFEBEE'), use_container_width=True)
    
    st.subheader("🛠️ Modificaciones y Mejoras")
    st.info("Resumen de modificaciones cuantificadas en tiempo (HH)")
    # Placeholder para tabla de modificaciones
    st.table(pd.DataFrame({"Modificación": ["Cambio de utillaje", "Mejora software"], "Tiempo Est. (h)": [120, 45]}))

# --- TAB MIX ---
with tabs[3]:
    st.subheader("🧭 Capacidad Estructural según Mix")
    # Lógica de simulación de Plotly (Velocímetro)
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = eff * 100,
        title = {'text': "Ocupación de Planta %"},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#A6192E"}}
    ))
    st.plotly_chart(fig)

st.sidebar.divider()
if st.sidebar.button("🚀 Sincronizar con Base de Datos"):
    st.cache_data.clear()
    st.success("Datos actualizados.")