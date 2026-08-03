import os
import glob
import pandas as pd
import numpy as np
import json
import datetime

# ==========================================
# CONFIGURACIÓN DE RUTAS (Basadas en ubicación del script)
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # Sube un nivel desde 04_scripts/

RAW_DATA_FOLDER = os.path.join(PROJECT_ROOT, "01_raw_data")
PROCESSED_DATA_FOLDER = os.path.join(PROJECT_ROOT, "02_processed_data")
AGGREGATED_DATA_FOLDER = os.path.join(PROJECT_ROOT, "03_aggregated_data")

# Asegurar que las carpetas de salida existan
os.makedirs(PROCESSED_DATA_FOLDER, exist_ok=True)
os.makedirs(AGGREGATED_DATA_FOLDER, exist_ok=True)

# ==========================================
# CONFIGURACIÓN DE PARÁMETROS
# ==========================================
PARAMS = {
    'outlier_min_cm': 10,
    'outlier_max_cm': 300,
    'velocidad_min_movimiento_kmh': 3.0,
    'radio_tierra_km': 6371.0
}

# ==========================================
# FUNCIÓN: Cálculo de Distancia Haversine (VECTORIZADA)
# ==========================================
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia en km entre dos puntos GPS usando la fórmula de Haversine.
    Acepta tanto escalares como arrays de numpy.
    """
    # Convertir a radianes usando numpy (funciona con arrays)
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    
    return PARAMS['radio_tierra_km'] * c

# ==========================================
# PASO 1: Cargar Archivos Crudos
# ==========================================
csv_files = glob.glob(os.path.join(RAW_DATA_FOLDER, "*.csv"))

if not csv_files:
    raise FileNotFoundError(f"No se encontraron archivos CSV en: {RAW_DATA_FOLDER}")

print(f"📂 Encontrados {len(csv_files)} archivos CSV para procesar.")
print(f"📁 Carpeta de entrada: {RAW_DATA_FOLDER}")

# ==========================================
# PASO 2: Pipeline de Limpieza (Iterar por archivo)
# ==========================================
todos_los_datos_limpios = []
total_registros_entrada = 0
total_outliers = 0
total_falsos_positivos = 0
total_nans = 0
total_km = 0.0

for file_path in csv_files:
    print(f"\n🔄 Procesando: {os.path.basename(file_path)}")
    
    # Cargar archivo
    df_raw = pd.read_csv(file_path)
    registros_entrada = len(df_raw)
    total_registros_entrada += registros_entrada
    
    # 2.1 Eliminar outliers extremos del sensor
    df_clean = df_raw[
        (df_raw['distancia_lateral_cm'] > PARAMS['outlier_min_cm']) & 
        (df_raw['distancia_lateral_cm'] < PARAMS['outlier_max_cm'])
    ].copy()
    outliers_removidos = registros_entrada - len(df_clean)
    total_outliers += outliers_removidos
    
    # 2.2 Separar datos en movimiento de datos en parada
    df_movimiento = df_clean[df_clean['velocidad_kmh'] >= PARAMS['velocidad_min_movimiento_kmh']].copy()
    falsos_positivos_parada = len(df_clean) - len(df_movimiento)
    total_falsos_positivos += falsos_positivos_parada
    
    # 2.3 Manejo de NaNs
    nans_antes = df_movimiento['distancia_lateral_cm'].isna().sum()
    df_movimiento = df_movimiento.dropna(subset=['distancia_lateral_cm', 'velocidad_kmh'])
    nans_removidos = nans_antes
    total_nans += nans_removidos
    
    # 2.4 Calcular KM reales usando Haversine (por dispositivo)
    km_archivo = 0.0
    for device_id in df_movimiento['device_id'].unique():
        df_device = df_movimiento[df_movimiento['device_id'] == device_id].sort_values('timestamp')
        
        if len(df_device) > 1:
            # Extraer arrays de coordenadas
            lat1 = df_device['lat'].iloc[:-1].values
            lon1 = df_device['lon'].iloc[:-1].values
            lat2 = df_device['lat'].iloc[1:].values
            lon2 = df_device['lon'].iloc[1:].values
            
            # Calcular distancias (ahora funciona con arrays completos)
            distancias_km = haversine_distance(lat1, lon1, lat2, lon2)
            km_archivo += np.sum(distancias_km)
    
    total_km += km_archivo
    
    # Acumular datos limpios
    todos_los_datos_limpios.append(df_movimiento)
    
    print(f"   ✓ {len(df_movimiento)} registros limpios | {outliers_removidos} outliers | {km_archivo:.2f} km")

# Concatenar todos los datos procesados
df_movimiento_total = pd.concat(todos_los_datos_limpios, ignore_index=True)

# ==========================================
# PASO 3: Guardar Datos Procesados (Capa Silver)
# ==========================================
ruta_parquet = os.path.join(PROCESSED_DATA_FOLDER, "datos_procesados.parquet")
df_movimiento_total.to_parquet(ruta_parquet, index=False)
print(f"\n✅ Datos procesados guardados: {ruta_parquet}")
print(f"   Total de registros: {len(df_movimiento_total)}")

# ==========================================
# PASO 4: Generar Metadata del Procesamiento
# ==========================================
# Calcular tasa de pérdida de datos
tasa_perdida = 0
if total_registros_entrada > 0:
    tasa_perdida = ((total_nans + total_outliers) / total_registros_entrada) * 100

metadata = {
    'fecha_procesamiento': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    'archivos_procesados': len(csv_files),
    'nombres_archivos': [os.path.basename(f) for f in csv_files],
    'registros_entrada': int(total_registros_entrada),
    'registros_salida': int(len(df_movimiento_total)),
    'outliers_removidos': int(total_outliers),
    'falsos_positivos_por_parada': int(total_falsos_positivos),
    'nans_removidos': int(total_nans),
    'tasa_perdida_datos_porcentaje': round(tasa_perdida, 2),  # ← NUEVA CLAVE
    'km_totales_escaneados': round(total_km, 2),
    'parametros_usados': PARAMS,
    'script': '01_limpieza.py',
    'version': "1.3.0"
}

ruta_metadata = os.path.join(PROCESSED_DATA_FOLDER, "metadata_limpieza.json")
with open(ruta_metadata, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=4, ensure_ascii=False)
print(f"✅ Metadata guardada: {ruta_metadata}")

print(f"\n🎉 ¡Limpieza completada!")
print(f"   - Archivos procesados: {len(csv_files)}")
print(f"   - KM totales escaneados: {total_km:.2f} km")
print(f"   - Registros limpios: {len(df_movimiento_total)}")
print(f"   - Tasa de pérdida: {tasa_perdida:.2f}%")