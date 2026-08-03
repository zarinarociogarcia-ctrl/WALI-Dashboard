import pandas as pd
import numpy as np
import datetime
import os

# ==========================================
# CONFIGURACIÓN DE RUTAS
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RAW_DATA_FOLDER = os.path.join(PROJECT_ROOT, "01_raw_data")
os.makedirs(RAW_DATA_FOLDER, exist_ok=True)

# ==========================================
# COORDENADAS REALES DE CALLE LIBERTADOR (SAN JUAN)
# ==========================================
# Extraídas de tu dataset GIS. Ordenadas por FID para seguir el recorrido.
ruta_real = [
    (-31.53530196407478, -68.53844842279172),  # FID 1
    (-31.535127592615915, -68.53665526551393),  # FID 2
    (-31.535021162613383, -68.53519918137582),  # FID 3
    (-31.534827794098625, -68.53332974055824),  # FID 4
    (-31.534751285991607, -68.53189010195632),  # FID 5
    (-31.53463535283708, -68.53050091295471),   # FID 6
    (-31.5345997176173, -68.53032531322135),    # FID 7
    (-31.53446429912164, -68.52889062136497),   # FID 8
    (-31.53423280210299, -68.52603822593157),   # FID 9
    (-31.534036208859707, -68.5232290680499),   # FID 10
    (-31.533836820785854, -68.5204911621295),   # FID 11
    (-31.533532707121495, -68.51628405151673),  # FID 12
    (-31.53362945187212, -68.51759790245823),   # FID 13 (Pequeña curva)
    (-31.53341901235029, -68.51509487049307),   # FID 14
    (-31.53345734991056, -68.51337031104985),   # FID 15
    (-31.533494209070042, -68.5119006439835),   # FID 16
    (-31.533546700558844, -68.50912054475992),  # FID 17
    (-31.533538174857977, -68.50690409976002),  # FID 18
    (-31.533493071135034, -68.50466442779602)   # FID 19
]

# ==========================================
# PARÁMETROS DE SIMULACIÓN
# ==========================================
np.random.seed(42)

# Ajustado a ~12 minutos (0.21 horas) para que la velocidad sea realista (~18 km/h)
# para un tramo de ~3.8 km.
duracion_horas = 0.21 
frecuencia_hz = 1
total_registros = int(duracion_horas * 3600 * frecuencia_hz)
num_devices = 3

# Interpolar puntos a lo largo de la ruta real
ruta_interpolada = []
for i in range(len(ruta_real) - 1):
    lat1, lon1 = ruta_real[i]
    lat2, lon2 = ruta_real[i + 1]
    puntos_segmento = total_registros // (len(ruta_real) - 1)
    for j in range(puntos_segmento):
        t = j / puntos_segmento
        lat = lat1 + t * (lat2 - lat1)
        lon = lon1 + t * (lon2 - lon1)
        ruta_interpolada.append((lat, lon))

while len(ruta_interpolada) < total_registros:
    ruta_interpolada.append(ruta_interpolada[-1])
ruta_interpolada = ruta_interpolada[:total_registros]

# ==========================================
# GENERAR DATOS
# ==========================================
inicio = datetime.datetime(2024, 5, 15, 8, 0, 0)
timestamps = [inicio + datetime.timedelta(seconds=i) for i in range(total_registros)]
devices = np.random.choice([f'WALI-{str(i).zfill(3)}' for i in range(1, num_devices + 1)], total_registros)

# Coordenadas con ruido GPS realista (3-5 metros)
latitudes = np.array([p[0] for p in ruta_interpolada]) + np.random.normal(0, 0.00003, total_registros)
longitudes = np.array([p[1] for p in ruta_interpolada]) + np.random.normal(0, 0.00003, total_registros)

# Velocidad: ciclista urbano (15-20 km/h) con 3 paradas en semáforos
velocidad = np.random.normal(17, 2, total_registros)
for i in range(3):
    inicio_parada = (i + 1) * (total_registros // 4)
    velocidad[inicio_parada:inicio_parada + 20] = 0.0

# Distancia lateral: base segura 200 cm
distancia = np.random.normal(200, 15, total_registros)

# Inyectar eventos de riesgo (sobrepasos < 1.5m)
num_eventos_riesgo = 15
indices_riesgo = np.random.choice(range(50, total_registros - 50), num_eventos_riesgo, replace=False)

for idx in indices_riesgo:
    duracion_evento = np.random.randint(2, 5)
    distancia_minima = np.random.randint(60, 140)
    valle = np.linspace(distancia_minima, 200, duracion_evento)
    distancia[idx:idx + duracion_evento] = valle

# Falsos positivos en paradas
indices_parada = np.where(velocidad == 0)[0]
distancia[indices_parada] = np.random.normal(40, 10, len(indices_parada))

# Outliers del sensor
errores_idx = np.random.choice(range(total_registros), int(total_registros * 0.015), replace=False)
distancia[errores_idx] = np.random.choice([0, 999], len(errores_idx))

# Pérdida de datos (NaN)
perdida_idx = np.random.choice(range(total_registros), int(total_registros * 0.02), replace=False)
distancia[perdida_idx] = np.nan
velocidad[perdida_idx] = np.nan

# Batería
bateria = np.clip(np.linspace(100, 95, total_registros) + np.random.normal(0, 0.2, total_registros), 0, 100)

# ==========================================
# CREAR Y GUARDAR DATAFRAME
# ==========================================
df = pd.DataFrame({
    'timestamp': timestamps,
    'device_id': devices,
    'lat': np.round(latitudes, 6),
    'lon': np.round(longitudes, 6),
    'velocidad_kmh': np.round(velocidad, 1),
    'distancia_lateral_cm': np.round(distancia, 1),
    'bateria_porcentaje': np.round(bateria, 1)
})

output_path = os.path.join(RAW_DATA_FOLDER, "wali_datos_realistas.csv")
df.to_csv(output_path, index=False)

print(f"✅ Datos realistas generados: {output_path}")
print(f"   Total de registros: {len(df)}")
print(f"   Duración simulada: {duracion_horas*60:.1f} minutos")
print(f"   Ruta: Calle Libertador (Datos GIS reales)")
print(f"   Eventos de riesgo inyectados: {num_eventos_riesgo}")