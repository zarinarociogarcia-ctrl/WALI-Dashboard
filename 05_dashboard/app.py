import os
import pandas as pd
import json
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Dashboard WALI - Red Vial Urbana", page_icon="🚴", layout="wide", initial_sidebar_state="expanded")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
PROCESSED_DATA = os.path.join(PROJECT_ROOT, "02_processed_data")
AGGREGATED_DATA = os.path.join(PROJECT_ROOT, "03_aggregated_data")

# ==========================================
# MAPEO DE CORREDORES (para colores en el mapa)
# ==========================================
CORREDORES_INFO = {
    "WALI-001": {"calle": "Av. Libertador", "color": "#3498db"},
    "WALI-002": {"calle": "Av. Libertador", "color": "#3498db"},
    "WALI-003": {"calle": "Av. Ignacio de la Roza", "color": "#2ecc71"},
    "WALI-004": {"calle": "Av. Ignacio de la Roza", "color": "#2ecc71"},
    "WALI-005": {"calle": "Av. España", "color": "#e74c3c"},
    "WALI-006": {"calle": "Av. España", "color": "#e74c3c"}
}

# ==========================================
# CARGA Y CÁLCULO DE DATOS
# ==========================================
@st.cache_data
def cargar_y_procesar():
    with open(os.path.join(PROCESSED_DATA, "metadata_limpieza.json"), "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    df_procesado = pd.read_parquet(os.path.join(PROCESSED_DATA, "datos_procesados.parquet"))
    df_eventos = pd.read_parquet(os.path.join(AGGREGATED_DATA, "eventos_riesgo.parquet"))
    
    # Agregar columna de calle a los eventos
    df_eventos['calle'] = df_eventos['device_id'].map(lambda x: CORREDORES_INFO.get(x, {}).get('calle', 'Desconocida'))
    df_eventos['color'] = df_eventos['device_id'].map(lambda x: CORREDORES_INFO.get(x, {}).get('color', '#95a5a6'))
    
    # Calcular KPIs
    total_eventos = len(df_eventos)
    criticos = len(df_eventos[df_eventos['distancia_minima_cm'] < 100])
    altos = len(df_eventos[(df_eventos['distancia_minima_cm'] >= 100) & (df_eventos['distancia_minima_cm'] < 150)])
    dist_promedio = df_eventos['distancia_minima_cm'].mean() if total_eventos > 0 else 0
    
    # Eventos por corredor
    eventos_por_calle = df_eventos.groupby('calle').size().to_dict()
    criticos_por_calle = df_eventos[df_eventos['distancia_minima_cm'] < 100].groupby('calle').size().to_dict()
    
    # Dispositivos únicos
    dispositivos_unicos = df_eventos['device_id'].nunique()
    corredores_unicos = df_eventos['calle'].nunique()
    
    kpis = {
        'total': total_eventos,
        'criticos': criticos,
        'altos': altos,
        'dist_promedio': dist_promedio,
        'dispositivos': dispositivos_unicos,
        'corredores': corredores_unicos,
        'eventos_por_calle': eventos_por_calle,
        'criticos_por_calle': criticos_por_calle
    }
    
    return metadata, kpis, df_procesado, df_eventos

metadata, kpis, df_procesado, df_eventos = cargar_y_procesar()

# ==========================================
# BARRA LATERAL
# ==========================================
st.sidebar.title("🚴 Dashboard WALI")
st.sidebar.markdown("**Sistema de Monitoreo de Distancia Lateral para ciclistas**")
st.sidebar.markdown("---")

st.sidebar.info("📍 **Corredores Analizados:**\n- Av. Libertador\n- Av. Ignacio de la Roza\n- Av. España")
st.sidebar.markdown("---")

vista = st.sidebar.radio("Selecciona una vista:", ["📊 1. Resumen Ejecutivo", "⚙️ 2. Control Técnico", "🗺️ 3. Mapa de Riesgo"])
st.sidebar.markdown("---")
st.sidebar.caption(f"Actualizado: {metadata['fecha_procesamiento']}")

# ==========================================
# VISTA 1: RESUMEN EJECUTIVO
# ==========================================
if vista == "📊 1. Resumen Ejecutivo":
    st.title("📊 Análisis de Red Vial Urbana: Piloto WALI")
    st.markdown("Métricas consolidadas de seguridad vial y detección de riesgos para ciclistas en corredores estratégicos.")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("️ Corredores", kpis['corredores'])
    with col2: st.metric("📏 Red Vial Mapeada", f"{metadata['km_totales_escaneados']:.1f} km")
    with col3: st.metric("⚠️ Eventos de Riesgo", kpis['total'])
    with col4: st.metric("🔴 Eventos Críticos (<1m)", kpis['criticos'])
    with col5: st.metric("📉 Integridad de Datos", f"{100 - metadata['tasa_perdida_datos_porcentaje']:.1f}%")

    st.markdown("---")
    
    # Eventos por corredor
    st.subheader(" Eventos de Riesgo por Corredor")
    col_a, col_b = st.columns(2)
    
    with col_a:
        df_eventos_calle = pd.DataFrame(list(kpis['eventos_por_calle'].items()), columns=['Corredor', 'Total Eventos'])
        fig_bar = px.bar(df_eventos_calle, x='Corredor', y='Total Eventos', 
                         color='Corredor',
                         color_discrete_map={'Av. Libertador': '#3498db', 'Av. Ignacio de la Roza': '#2ecc71', 'Av. España': '#e74c3c'},
                         text='Total Eventos')
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col_b:
        st.subheader("Distribución de Severidad en la Red")
        severidad = pd.DataFrame({
            "Categoría": ["Crítico (< 1.0 m)", "Alto (1.0 - 1.5 m)"],
            "Cantidad": [kpis['criticos'], kpis['altos']]
        })
        fig_pie = px.pie(severidad, values="Cantidad", names="Categoría", 
                         color_discrete_map={"Crítico (< 1.0 m)": "#FF4B4B", "Alto (1.0 - 1.5 m)": "#FFA500"}, hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.subheader("Complementariedad de Datos para Seguridad Vial")
    pct_critico = (kpis['criticos'] / kpis['total'] * 100) if kpis['total'] > 0 else 0
    
    st.markdown(f"""
    - **Distancia mínima promedio registrada:** {kpis['dist_promedio']:.1f} cm
    - **Proporción de eventos críticos:** {pct_critico:.1f}% del total de sobrepasos registrados.
    - **Corredores monitoreados:** {kpis['corredores']} avenidas principales de San Juan.
    
    >  **Valor para la Gestión Pública:** 
    > WALI permite identificar los corredores vailes con mayor riesgo para el ciclista. 
    > Esta capa de datos complementa los reportes tradicionales, permitiendo intervenciones preventivas en puntos críticos antes de que ocurra un accidente.
    """)

# ==========================================
# VISTA 2: CONTROL TÉCNICO
# ==========================================
elif vista == "⚙️ 2. Control Técnico":
    st.title("⚙️ Control Técnico y Calidad de Datos")
    st.markdown("Transparencia del pipeline de datos y rendimiento del hardware WALI.")
    
    try:
        col1, col2, col3, col4 = st.columns(4)
        with col1: 
            st.metric("📁 Archivos Procesados", metadata.get('archivos_procesados', 0))
        with col2: 
            st.metric(" Registros Crudos", f"{metadata.get('registros_entrada', 0):,}")
        with col3: 
            st.metric("✅ Registros Válidos", f"{metadata.get('registros_salida', 0):,}")
        with col4: 
            st.metric("🔌 Dispositivos Únicos", kpis.get('dispositivos', 0))

        st.markdown("---")
        st.subheader("Desglose de Filtrado del Pipeline")
        
        df_filtro = pd.DataFrame({
            "Etapa": ["Outliers de Sensor", "Falsos Positivos (Parada)", "Registros con NaN", "Datos Válidos Finales"],
            "Registros": [
                metadata.get('outliers_removidos', 0), 
                metadata.get('falsos_positivos_por_parada', 0), 
                metadata.get('nans_removidos', 0), 
                metadata.get('registros_salida', 0)
            ]
        })
        
        fig_bar = px.bar(df_filtro, x="Etapa", y="Registros", text="Registros", color="Etapa")
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")
        st.subheader("Distribución de Distancia Lateral (Red Completa)")
        
        if len(df_procesado) > 0:
            fig_hist = px.histogram(
                df_procesado, 
                x="distancia_lateral_cm", 
                nbins=50, 
                color_discrete_sequence=["#1f77b4"], 
                labels={"distancia_lateral_cm": "Distancia al vehículo (cm)"},
                title=f"Distribución de {len(df_procesado):,} registros procesados"
            )
            fig_hist.add_vline(x=100, line_dash="dash", line_color="red", annotation_text="Zona Crítica (<1m)")
            fig_hist.add_vline(x=150, line_dash="dash", line_color="orange", annotation_text="Umbral Normativo (1.5m)")
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.warning("⚠️ No hay datos procesados disponibles para mostrar el histograma.")
            
    except Exception as e:
        st.error(f"❌ Error al cargar la Vista 2: {str(e)}")
        st.markdown("💡 **Posibles causas:**")
        st.markdown("- El archivo `metadata_limpieza.json` no existe o está corrupto")
        st.markdown("- El archivo `datos_procesados.parquet` no existe")
        st.markdown("- Ejecutá `run_pipeline.py` primero para generar los datos")
# ==========================================
# VISTA 3: MAPA GEOESPACIAL
# ==========================================
elif vista == "🗺️ 3. Mapa de Riesgo":
    st.title("🗺️ Mapa de Calor de Riesgo Vial")
    st.markdown("Localización geoespacial de los eventos de sobrepaso peligroso detectados en los corredores piloto.")
    
    st.markdown("---")
    
    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        corredores = df_eventos['calle'].unique().tolist()
        corredor_sel = st.selectbox("Filtrar por corredor:", ["Todos"] + corredores)
    with col_f2:
        dispositivos = df_eventos['device_id'].unique().tolist()
        disp_sel = st.selectbox("Filtrar por dispositivo:", ["Todos"] + dispositivos)
    
    # Aplicar filtros
    df_mapa = df_eventos.copy()
    if corredor_sel != "Todos":
        df_mapa = df_mapa[df_mapa['calle'] == corredor_sel]
    if disp_sel != "Todos":
        df_mapa = df_mapa[df_mapa['device_id'] == disp_sel]

    st.info(f"📊 Mostrando **{len(df_mapa)}** eventos de riesgo")
    
    # Calcular centro del mapa
    if len(df_mapa) > 0:
        centro_lat = float(df_mapa['lat_promedio'].mean())
        centro_lon = float(df_mapa['lon_promedio'].mean())
    else:
        centro_lat, centro_lon = -31.535, -68.525
    
    # Crear mapa
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=13, tiles="CartoDB dark_matter")
    
    # Dibujar trayectorias por dispositivo (con colores por calle)
    if len(df_procesado) > 0:
        for disp in df_procesado['device_id'].unique():
            df_disp = df_procesado[df_procesado['device_id'] == disp]
            if len(df_disp) > 1:
                info = CORREDORES_INFO.get(disp, {"calle": "Desconocida", "color": "#95a5a6"})
                trayectoria = [[float(row['lat']), float(row['lon'])] for _, row in df_disp.iterrows()]
                folium.PolyLine(
                    locations=trayectoria, 
                    color=info['color'], 
                    weight=4, 
                    opacity=0.7, 
                    tooltip=f"{info['calle']} ({disp})"
                ).add_to(m)
    
    # Agregar marcadores de eventos
    for idx, row in df_mapa.iterrows():
        lat = float(row['lat_promedio'])
        lon = float(row['lon_promedio'])
        dist = float(row['distancia_minima_cm'])
        vel = float(row['velocidad_promedio_kmh'])
        color = row['color']
        
        if dist < 100:
            riesgo = "CRÍTICO"
            icon_size = 10
        else:
            riesgo = "ALTO"
            icon_size = 7
        
        folium.CircleMarker(
            location=[lat, lon], 
            radius=icon_size, 
            color=color, 
            fill=True, 
            fillColor=color, 
            fillOpacity=0.9,
            popup=f"<b>{riesgo}</b><br>Corredor: {row['calle']}<br>Distancia: {dist:.1f} cm<br>Velocidad: {vel:.1f} km/h<br>Dispositivo: {row['device_id']}",
            tooltip=f"{row['calle']}: {riesgo} ({dist:.0f} cm)"
        ).add_to(m)
    
    # Mostrar mapa
    st_folium(m, width=1200, height=700, key="mapa_riesgo")
    
    # Leyenda
    st.markdown("---")
    st.markdown("""
    **Leyenda:**
    - 🔵 **Línea Azul:** Av. Libertador
    - 🟢 **Línea Verde:** Av. Ignacio de la Roza
    - 🔴 **Línea Roja:** Av. España
    - ⭕ **Círculos:** Eventos de riesgo (tamaño = severidad)
    """)

st.markdown("---")
st.caption("Dashboard WALI | Sistema de Monitoreo de Distancia Lateral para ciclistas")
