import os
import pandas as pd
import json
import datetime

# ==========================================
# CONFIGURACIÓN DE RUTAS (Basadas en ubicación del script)
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # Sube un nivel desde 04_scripts/

PROCESSED_DATA_FOLDER = os.path.join(PROJECT_ROOT, "02_processed_data")
AGGREGATED_DATA_FOLDER = os.path.join(PROJECT_ROOT, "03_aggregated_data")

# Asegurar que la carpeta de salida exista
os.makedirs(AGGREGATED_DATA_FOLDER, exist_ok=True)

# ==========================================
# CONFIGURACIÓN DE PARÁMETROS
# ==========================================
UMBRAL_RIESGO_CM = 150
UMBRAL_CRITICO_CM = 100

# ==========================================
# PASO 1: Cargar Datos Procesados
# ==========================================
ruta_entrada = os.path.join(PROCESSED_DATA_FOLDER, "datos_procesados.parquet")

if not os.path.exists(ruta_entrada):
    raise FileNotFoundError(
        f"No se encontró el archivo procesado: {ruta_entrada}\n"
        f"¿Ejecutaste primero 01_limpieza.py?"
    )

print("📂 Cargando datos procesados...")
print(f"📁 Archivo: {ruta_entrada}")
df_movimiento = pd.read_parquet(ruta_entrada)
print(f"✅ {len(df_movimiento)} registros cargados")

# ==========================================
# PASO 2: Detección de Eventos de Riesgo
# ==========================================
print("\n🔍 Detectando eventos de riesgo...")
print(f"   Umbral de riesgo: < {UMBRAL_RIESGO_CM} cm")
print(f"   Umbral crítico: < {UMBRAL_CRITICO_CM} cm")

# Marcar filas donde hay riesgo
df_movimiento['es_riesgo'] = df_movimiento['distancia_lateral_cm'] < UMBRAL_RIESGO_CM

# Agrupar eventos consecutivos (identificar "valles" continuos de distancia)
df_movimiento['grupo_evento'] = (df_movimiento['es_riesgo'] != df_movimiento['es_riesgo'].shift()).cumsum()

# Filtrar solo los grupos que son de riesgo y agregarlos
eventos_riesgo = df_movimiento[df_movimiento['es_riesgo']].groupby(['device_id', 'grupo_evento']).agg(
    distancia_minima_cm=('distancia_lateral_cm', 'min'),
    duracion_seg=('timestamp', 'count'),
    lat_promedio=('lat', 'mean'),
    lon_promedio=('lon', 'mean'),
    velocidad_promedio_kmh=('velocidad_kmh', 'mean')
).reset_index()

# ==========================================
# PASO 3: Guardar Eventos (Capa Gold)
# ==========================================
ruta_eventos = os.path.join(AGGREGATED_DATA_FOLDER, "eventos_riesgo.parquet")
eventos_riesgo.to_parquet(ruta_eventos, index=False)
print(f"\n✅ Eventos guardados: {ruta_eventos}")
print(f"   Total de eventos de riesgo: {len(eventos_riesgo)}")

# ==========================================
# PASO 4: Calcular KPIs de Eventos
# ==========================================
eventos_criticos = len(eventos_riesgo[eventos_riesgo['distancia_minima_cm'] < UMBRAL_CRITICO_CM])
eventos_altos = len(eventos_riesgo) - eventos_criticos

kpis_eventos = {
    'fecha_procesamiento': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    'total_eventos_riesgo': int(len(eventos_riesgo)),
    'eventos_criticos_menos_1m': int(eventos_criticos),
    'eventos_altos_1m_a_1_5m': int(eventos_altos),
    'distancia_minima_promedio_cm': round(float(eventos_riesgo['distancia_minima_cm'].mean()), 2) if len(eventos_riesgo) > 0 else 0,
    'dispositivos_con_eventos': int(eventos_riesgo['device_id'].nunique()),
    'umbral_riesgo_cm': UMBRAL_RIESGO_CM,
    'umbral_critico_cm': UMBRAL_CRITICO_CM,
    'script': '02_deteccion_eventos.py',
    'version': "1.1.0"
}

ruta_kpis = os.path.join(AGGREGATED_DATA_FOLDER, "kpis_eventos.json")
with open(ruta_kpis, "w", encoding="utf-8") as f:
    json.dump(kpis_eventos, f, indent=4, ensure_ascii=False)
print(f"✅ KPIs de eventos guardados: {ruta_kpis}")

# ==========================================
# PASO 5: Metadata de Map Matching (Placeholder)
# ==========================================
metadata_map_matching = {
    'fecha_procesamiento': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    'eventos_procesados': int(len(eventos_riesgo)),
    'map_matching_realizado': False,
    'nota': 'Pendiente de implementación con OSMnx/GeoPandas',
    'script': '03_map_matching.py',
    'version': "0.1.0-placeholder"
}

ruta_metadata_mm = os.path.join(AGGREGATED_DATA_FOLDER, "metadata_map_matching.json")
with open(ruta_metadata_mm, "w", encoding="utf-8") as f:
    json.dump(metadata_map_matching, f, indent=4, ensure_ascii=False)

print(f"\n🎉 ¡Detección de eventos completada!")
print(f"   - Eventos totales: {len(eventos_riesgo)}")
print(f"   - Eventos críticos (<1m): {eventos_criticos}")
print(f"   - Eventos altos (1-1.5m): {eventos_altos}")
if len(eventos_riesgo) > 0:
    print(f"   - Distancia mínima promedio: {eventos_riesgo['distancia_minima_cm'].mean():.2f} cm")