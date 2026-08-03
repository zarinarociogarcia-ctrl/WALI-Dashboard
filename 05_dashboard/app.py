import os
import sys
import subprocess
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
# CONFIGURACIÓN DE RUTAS
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR) # Sube un nivel a la raíz del repo

PROCESSED_DATA = os.path.join(PROJECT_ROOT, "02_processed_data")
AGGREGATED_DATA = os.path.join(PROJECT_ROOT, "03_aggregated_data")

# Asegurar que las carpetas existan en la nube
os.makedirs(PROCESSED_DATA, exist_ok=True)
os.makedirs(AGGREGATED_DATA, exist_ok=True)

# ==========================================
# INICIALIZACIÓN AUTOMÁTICA (Clave para la Nube)
# ==========================================
def inicializar_datos():
    """Verifica si los datos existen. Si no, ejecuta el pipeline automáticamente."""
    metadata_path = os.path.join(PROCESSED_DATA, "metadata_limpieza.json")
    
    if not os.path.exists(metadata_path):
        st.warning("⚠️ Datos procesados no encontrados. Generando datos y ejecutando pipeline en la nube...")
        
        gen_script = os.path.join(PROJECT_ROOT, "generar_datos_realistas.py")
        pipeline_script = os.path.join(PROJECT_ROOT, "run_pipeline.py")
        
        try:
            # 1. Generar datos sintéticos realistas
            subprocess.run([sys.executable, gen_script], check=True, cwd=PROJECT_ROOT)
            # 2. Ejecutar el pipeline de limpieza y eventos
            subprocess.run([sys.executable, pipeline_script], check=True, cwd=PROJECT_ROOT)
            st.success("✅ Pipeline completado exitosamente en la nube.")
        except subprocess.CalledProcessError as e:
            st.error(f"❌ Error al ejecutar el pipeline: {e}")
            st.stop()

# Ejecutar la inicialización antes de cargar nada
inicializar_datos()

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
# BARRA LATERAL (Navegación)
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
# VISTA 1: RESUMEN EJECUTIVO (B2G)
# ==========================================
if vista == " 1. Resumen Ejecutivo (B2G)":
    st.title("📊 Resumen Ejecutivo: Impacto del Piloto WALI")
    st.markdown("Métricas clave para la toma de decisiones en seguridad vial y planificación urbana.")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📏 KM Escaneados", f"{metadata['km_totales_escaneados']:.1f} km")
    with col2:
        st.metric("⚠️ Eventos de Riesgo", kpis_eventos['total_eventos_riesgo'])
    with col3:
        st.metric("🔴 Eventos Críticos (<1m)", kpis_eventos['eventos_criticos_menos_1m'])
    with col4:
        st.metric("📉 Tasa de Pérdida de Datos", f"{metadata['tasa_perdida_datos_porcentaje']:.1f}%")

    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Distribución de Severidad de Eventos")
        severidad = pd.DataFrame({
            "Categoría": ["Crítico (< 1.0 m)", "Alto (1.0 - 1.5 m)"],
            "Cantidad": [kpis_eventos['eventos_criticos_menos_1m'], kpis_eventos['eventos_altos_1m_a_1_5m']]
        })
        fig_pie = px.pie(severidad, values="Cantidad", names="Categoría", 
                         color="Categoría", color_discrete_map={"Crítico (< 1.0 m)": "#FF4B4B", "Alto (1.0 - 1.5 m)": "#FFA500"},
                         hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        st.subheader("Validación de Normativa (Ley de Tránsito)")
        total_eventos = kpis_eventos['total_eventos_riesgo']
        if total_eventos > 0:
            cumplimiento = ((total_eventos - kpis_eventos['eventos_criticos_menos_1m']) / total_eventos) * 100
        else:
            cumplimiento = 100
            
        st.markdown(f"""
        - **Distancia mínima promedio en eventos:** {kpis_eventos['distancia_minima_promedio_cm']:.1f} cm
        - **Dispositivos que registraron eventos:** {kpis_eventos['dispositivos_con_eventos']}
        - **Porcentaje de eventos que NO fueron críticos:** {cumplimiento:.1f}%
        
        > 💡 *Insight:* De los {total_eventos} sobrepasos registrados a menos de 1.5m, 
        > el {100-cumplimiento:.1f}% fueron **críticos (<1m)**, representando un riesgo inminente de colisión 
        > que los sistemas tradicionales de siniestralidad no capturan ("ceguera institucional").
        """)

# ==========================================
# VISTA 2: CONTROL TÉCNICO
# ==========================================
elif vista == "️ 2. Control Técnico":
    st.title("⚙️ Control Técnico y Calidad de Datos")
    st.markdown("Métricas de funcionamiento del hardware y calidad del pipeline de datos.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📁 Archivos Procesados", metadata['archivos_procesados'])
    with col2:
        st.metric("📝 Registros Crudos", f"{metadata['registros_entrada']:,}")
    with col3:
        st.metric("✅ Registros Limpios", f"{metadata['registros_salida']:,}")

    st.markdown("---")
    st.subheader("Desglose de Filtrado del Pipeline")
    
    df_filtro = pd.DataFrame({
        "Etapa": ["Outliers de Sensor", "Falsos Positivos (Parada)", "Registros con NaN", "Datos Válidos Finales"],
        "Registros": [
            metadata['outliers_removidos'],
            metadata['falsos_positivos_por_parada'],
            metadata['nans_removidos'],
            metadata['registros_salida']
        ]
    })
    
    fig_bar = px.bar(df_filtro, x="Etapa", y="Registros", text="Registros", 
                     color="Etapa", color_discrete_sequence=px.colors.qualitative.Set2)
    fig_bar.update_traces(textposition='outside')
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    st.subheader("Distribución de Distancia Lateral (Todos los registros en movimiento)")
    fig_hist = px.histogram(df_procesado, x="distancia_lateral_cm", nbins=50, 
                            title="Histograma de Distancias Laterales Registradas",
                            labels={"distancia_lateral_cm": "Distancia (cm)"},
                            color_discrete_sequence=["#1f77b4"])
    
    fig_hist.add_vline(x=100, line_dash="dash", line_color="red", annotation_text="Crítico (<1m)")
    fig_hist.add_vline(x=150, line_dash="dash", line_color="orange", annotation_text="Umbral de Riesgo (1.5m)")
    st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================
# VISTA 3: MAPA DE RIESGO GEOESPACIAL
# ==========================================
elif vista == "🗺️ 3. Mapa de Riesgo Geoespacial":
    st.title("🗺️ Mapa de Riesgo Geoespacial")
    st.markdown("Visualización de los eventos de riesgo detectados sobre la red vial.")
    
    dispositivos = df_eventos['device_id'].unique().tolist()
    disp_seleccionado = st.selectbox("Filtrar por dispositivo:", ["Todos"] + dispositivos)
    
    if disp_seleccionado != "Todos":
        df_mapa = df_eventos[df_eventos['device_id'] == disp_seleccionado]
    else:
        df_mapa = df_eventos

    st.markdown("---")
    
    # Centrar el mapa dinámicamente
    if len(df_mapa) > 0:
        centro_lat = df_mapa['lat_promedio'].mean()
        centro_lon = df_mapa['lon_promedio'].mean()
    else:
        centro_lat, centro_lon = -31.534, -68.525 # Centro aprox de los datos reales

    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=15, tiles="CartoDB dark_matter")
    
    # Dibujar trayectoria
    if len(df_procesado) > 0:
        # Tomamos un solo dispositivo para dibujar la línea base y no saturar
        df_uno = df_procesado[df_procesado['device_id'] == df_procesado['device_id'].iloc[0]]
        trayectoria = [[row['lat'], row['lon']] for _, row in df_uno.iterrows()]
        folium.PolyLine(
            locations=trayectoria,
            color="#3498db",
            weight=4,
            opacity=0.7,
            tooltip="Trayectoria del ciclista (WALI-001)"
        ).add_to(m)

    # Agregar marcadores de eventos
    for idx, row in df_mapa.iterrows():
        if row['distancia_minima_cm'] < 100:
            color = "#e74c3c" # Rojo
            riesgo = "CRÍTICO"
        else:
            color = "#f39c12" # Naranja
            riesgo = "ALTO"
            
        folium.CircleMarker(
            location=[row['lat_promedio'], row['lon_promedio']],
            radius=7,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.8,
            popup=f"<b>Riesgo: {riesgo}</b><br>Distancia: {row['distancia_minima_cm']:.1f} cm<br>Velocidad: {row['velocidad_promedio_kmh']:.1f} km/h<br>Dispositivo: {row['device_id']}",
            tooltip=f"{riesgo}: {row['distancia_minima_cm']:.0f} cm"
        ).add_to(m)

    st_folium(m, width=1000, height=600)
    
    st.markdown("""
    > **Leyenda del Mapa:**
    > - 🔴 **Puntos Rojos:** Eventos críticos (distancia < 1.0 m). Riesgo inminente de colisión.
    > -  **Puntos Naranjas:** Eventos de riesgo alto (1.0 m a 1.5 m). Incumplimiento de la distancia de sobrepaso seguro.
    > - 🔵 **Línea Azul:** Trayectoria registrada por el dispositivo.
    """)

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.caption("Dashboard desarrollado para el proyecto WALI | Pipeline de Datos de Movilidad Urbana")
