import os
import pandas as pd
import json
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Dashboard WALI - Piloto de Movilidad",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CONFIGURACIÓN DE RUTAS (Funciona en Local y Nube)
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR) # Sube un nivel a la raíz del repo

PROCESSED_DATA = os.path.join(PROJECT_ROOT, "02_processed_data")
AGGREGATED_DATA = os.path.join(PROJECT_ROOT, "03_aggregated_data")

# ==========================================
# CARGA DE DATOS
# ==========================================
@st.cache_data
def cargar_datos():
    with open(os.path.join(PROCESSED_DATA, "metadata_limpieza.json"), "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    with open(os.path.join(AGGREGATED_DATA, "kpis_eventos.json"), "r", encoding="utf-8") as f:
        kpis_eventos = json.load(f)
    
    df_procesado = pd.read_parquet(os.path.join(PROCESSED_DATA, "datos_procesados.parquet"))
    df_eventos = pd.read_parquet(os.path.join(AGGREGATED_DATA, "eventos_riesgo.parquet"))
    
    return metadata, kpis_eventos, df_procesado, df_eventos

metadata, kpis_eventos, df_procesado, df_eventos = cargar_datos()

# ==========================================
# BARRA LATERAL
# ==========================================
st.sidebar.title("🚴 Dashboard WALI")
st.sidebar.markdown("**Sistema de Monitoreo de Distancia Lateral**")
st.sidebar.markdown("---")

vista = st.sidebar.radio(
    "Selecciona una vista:",
    ["📊 1. Resumen Ejecutivo (B2G)", "⚙️ 2. Control Técnico", "🗺️ 3. Mapa de Riesgo Geoespacial"]
)

st.sidebar.markdown("---")
st.sidebar.info(f"Última actualización:\n{metadata['fecha_procesamiento']}")

# ==========================================
# VISTA 1: RESUMEN EJECUTIVO
# ==========================================
if vista == "📊 1. Resumen Ejecutivo (B2G)":
    st.title("📊 Resumen Ejecutivo: Impacto del Piloto WALI")
    st.markdown("Métricas clave para la toma de decisiones en seguridad vial y planificación urbana.")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric(" KM Escaneados", f"{metadata['km_totales_escaneados']:.1f} km")
    with col2: st.metric("⚠️ Eventos de Riesgo", kpis_eventos['total_eventos_riesgo'])
    with col3: st.metric("🔴 Eventos Críticos (<1m)", kpis_eventos['eventos_criticos_menos_1m'])
    with col4: st.metric("📉 Tasa de Pérdida", f"{metadata['tasa_perdida_datos_porcentaje']:.1f}%")

    st.markdown("---")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Distribución de Severidad")
        severidad = pd.DataFrame({
            "Categoría": ["Crítico (< 1.0 m)", "Alto (1.0 - 1.5 m)"],
            "Cantidad": [kpis_eventos['eventos_criticos_menos_1m'], kpis_eventos['eventos_altos_1m_a_1_5m']]
        })
        fig_pie = px.pie(severidad, values="Cantidad", names="Categoría", 
                         color_discrete_map={"Crítico (< 1.0 m)": "#FF4B4B", "Alto (1.0 - 1.5 m)": "#FFA500"}, hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        st.subheader("Validación de Normativa")
        total_eventos = kpis_eventos['total_eventos_riesgo']
        cumplimiento = ((total_eventos - kpis_eventos['eventos_criticos_menos_1m']) / total_eventos * 100) if total_eventos > 0 else 100
        st.markdown(f"""
        - **Distancia mínima promedio:** {kpis_eventos['distancia_minima_promedio_cm']:.1f} cm
        - **Eventos NO críticos:** {cumplimiento:.1f}%
        > 💡 *Insight:* El {100-cumplimiento:.1f}% de los sobrepasos fueron **críticos (<1m)**, demostrando la 'ceguera institucional' de los sistemas tradicionales.
        """)

# ==========================================
# VISTA 2: CONTROL TÉCNICO
# ==========================================
elif vista == "⚙️ 2. Control Técnico":
    st.title("⚙️ Control Técnico y Calidad de Datos")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric(" Archivos", metadata['archivos_procesados'])
    with col2: st.metric("📝 Registros Crudos", f"{metadata['registros_entrada']:,}")
    with col3: st.metric("✅ Registros Limpios", f"{metadata['registros_salida']:,}")

    st.markdown("---")
    st.subheader("Desglose de Filtrado")
    df_filtro = pd.DataFrame({
        "Etapa": ["Outliers", "Falsos Positivos (Parada)", "NaNs", "Datos Válidos"],
        "Registros": [metadata['outliers_removidos'], metadata['falsos_positivos_por_parada'], metadata['nans_removidos'], metadata['registros_salida']]
    })
    fig_bar = px.bar(df_filtro, x="Etapa", y="Registros", text="Registros", color="Etapa")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Distribución de Distancia Lateral")
    fig_hist = px.histogram(df_procesado, x="distancia_lateral_cm", nbins=50, color_discrete_sequence=["#1f77b4"])
    fig_hist.add_vline(x=100, line_dash="dash", line_color="red", annotation_text="Crítico (<1m)")
    fig_hist.add_vline(x=150, line_dash="dash", line_color="orange", annotation_text="Riesgo (1.5m)")
    st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================
# VISTA 3: MAPA GEOESPACIAL
# ==========================================
elif vista == "🗺️ 3. Mapa de Riesgo Geoespacial":
    st.title("️ Mapa de Riesgo Geoespacial")
    
    dispositivos = df_eventos['device_id'].unique().tolist()
    disp_seleccionado = st.selectbox("Filtrar por dispositivo:", ["Todos"] + dispositivos)
    df_mapa = df_eventos[df_eventos['device_id'] == disp_seleccionado] if disp_seleccionado != "Todos" else df_eventos

    st.markdown("---")
    
    centro_lat = df_mapa['lat_promedio'].mean() if len(df_mapa) > 0 else -31.534
    centro_lon = df_mapa['lon_promedio'].mean() if len(df_mapa) > 0 else -68.525

    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=15, tiles="CartoDB dark_matter")
    
    # Trayectoria
    if len(df_procesado) > 0:
        df_uno = df_procesado[df_procesado['device_id'] == df_procesado['device_id'].iloc[0]]
        trayectoria = [[row['lat'], row['lon']] for _, row in df_uno.iterrows()]
        folium.PolyLine(locations=trayectoria, color="#3498db", weight=4, opacity=0.7).add_to(m)

    # Eventos
    for idx, row in df_mapa.iterrows():
        color = "#e74c3c" if row['distancia_minima_cm'] < 100 else "#f39c12"
        riesgo = "CRÍTICO" if row['distancia_minima_cm'] < 100 else "ALTO"
        folium.CircleMarker(
            location=[row['lat_promedio'], row['lon_promedio']], radius=7, color=color, fill=True, fillColor=color, fillOpacity=0.8,
            popup=f"<b>{riesgo}</b><br>Dist: {row['distancia_minima_cm']:.1f} cm<br>Vel: {row['velocidad_promedio_kmh']:.1f} km/h"
        ).add_to(m)

    st_folium(m, width=1000, height=600)
    st.markdown("🔴 **Rojo:** < 1.0m (Crítico) | 🟠 **Naranja:** 1.0m - 1.5m (Alto) | 🔵 **Azul:** Trayectoria")

st.markdown("---")
st.caption("Dashboard desarrollado para el proyecto WALI | Pipeline de Datos de Movilidad Urbana")
