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
# COORDENADAS REALES DE 3 CALLES DE SAN JUAN
# ==========================================
calles_reales = {
    "Av_Libertador": {
        "coords": [
            (-31.53530196407478, -68.53844842279172),
            (-31.535127592615915, -68.53665526551393),
            (-31.535021162613383, -68.53519918137582),
            (-31.534827794098625, -68.53332974055824),
            (-31.534751285991607, -68.53189010195632),
            (-31.53463535283708, -68.53050091295471),
            (-31.5345997176173, -68.53032531322135),
            (-31.53446429912164, -68.52889062136497),
            (-31.53423280210299, -68.52603822593157),
            (-31.534036208859707, -68.5232290680499),
            (-31.533836820785854, -68.5204911621295),
            (-31.533532707121495, -68.51628405151673),
            (-31.53362945187212, -68.51759790245823),
            (-31.53341901235029, -68.51509487049307),
            (-31.53345734991056, -68.51337031104985),
            (-31.533494209070042, -68.5119006439835),
            (-31.533546700558844, -68.50912054475992),
            (-31.533538174857977, -68.50690409976002),
            (-31.533493071135034, -68.50466442779602)
        ],
        "devices": ["WALI-001", "WALI-002"],  # IDs únicos
        "duracion": 800,  # ~13 min
        "color_mapa": "#3498db"  # Azul para el mapa
    },
    "Av_Ignacio_de_la_Roza": {
        "coords": [
            (-31.53813527791265, -68.53813347707005),
            (-31.53802239581082, -68.53635180229205),
            (-31.537904349221932, -68.53488869468241),
            (-31.53777581659612, -68.53302813044033),
            (-31.5376780020921, -68.5315841935722),
            (-31.53757555995243, -68.53006226830908),
            (-31.537470823828546, -68.5285596214258),
            (-31.537375419580005, -68.5271464367318),
            (-31.537280009504716, -68.52573588759023)
        ],
        "devices": ["WALI-003", "WALI-004"],  # IDs únicos
        "duracion": 300,  # ~5 min
        "color_mapa": "#2ecc71"  # Verde para el mapa
    },
    "Av_España": {
        "coords": [
            (-31.52446160326113, -68.53782789857576),
            (-31.526413430307855, -68.53762346256792),
            (-31.52851081771315, -68.5374160162866),
            (-31.530594444843217, -68.53715701292678),
            (-31.5326076402412, -68.53693777830607),
            (-31.535127592615915, -68.53665526551393),
            (-31.53738231631763, -68.53642077872651),
            (-31.53861288264351, -68.5362857025558),
            (-31.53975328204252, -68.53615633365531),
            (-31.540888208816682, -68.53604412904423),
            (-31.542421924029075, -68.53585516202915),
            (-31.53406923274488, -68.53677936440393)
        ],
        "devices": ["WALI-005", "WALI-006"],  # IDs únicos
        "duracion": 240,  # ~4 min
        "color_mapa": "#e74c3c"  # Rojo para el mapa
    }
}

# ==========================================
# GENERACIÓN DE DATOS
# ==========================================
np.random.seed(42)
total_archivos = 0

for nombre_calle, config in calles_reales.items():
    print(f"\n🔄 Generando datos para: {nombre_calle}")
    
    coords = config["coords"]
    devices_list = config["devices"]
    total_registros = config["duracion"]
    
    # Interpolar ruta real
    ruta_interpolada = []
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        puntos = total_registros // (len(coords) - 1)
        for j in range(puntos):
            t = j / puntos
            lat = lat1 + t * (lat2 - lat1)
            lon = lon1 + t * (lon2 - lon1)
            ruta_interpolada.append((lat, lon))
    
    while len(ruta_interpolada) < total_registros:
        ruta_interpolada.append(ruta_interpolada[-1])
    ruta_interpolada = ruta_interpolada[:total_registros]
    
    # Timestamps
    inicio = datetime.datetime(2024, 5, 15, 8, 0, 0)
    timestamps = [inicio + datetime.timedelta(seconds=i) for i in range(total_registros)]
    devices = np.random.choice(devices_list, total_registros)
    
    # Coordenadas con ruido GPS
    latitudes = np.array([p[0] for p in ruta_interpolada]) + np.random.normal(0, 0.00003, total_registros)
    longitudes = np.array([p[1] for p in ruta_interpolada]) + np.random.normal(0, 0.00003, total_registros)
    
    # Velocidad y paradas
    velocidad = np.random.normal(17, 2, total_registros)
    num_semaforos = np.random.randint(2, 4)
    for i in range(num_semaforos):
        inicio_parada = (i + 1) * (total_registros // (num_semaforos + 1))
        velocidad[inicio_parada:inicio_parada + 15] = 0.0
    
    # Distancia lateral y eventos de riesgo
    distancia = np.random.normal(200, 15, total_registros)
    num_riesgos = np.random.randint(6, 12)
    indices_riesgo = np.random.choice(range(50, total_registros - 50), num_riesgos, replace=False)
    
    for idx in indices_riesgo:
        dur = np.random.randint(2, 4)
        min_dist = np.random.randint(60, 140)
        distancia[idx:idx+dur] = np.linspace(min_dist, 200, dur)
    
    # Falsos positivos en paradas
    indices_parada = np.where(velocidad == 0)[0]
    if len(indices_parada) > 0:
        distancia[indices_parada] = np.random.normal(40, 10, len(indices_parada))
    
    # Outliers y NaNs
    errores_idx = np.random.choice(total_registros, int(total_registros * 0.015), replace=False)
    distancia[errores_idx] = np.random.choice([0, 999], len(errores_idx))
    
    perdida_idx = np.random.choice(total_registros, int(total_registros * 0.02), replace=False)
    distancia[perdida_idx] = np.nan
    velocidad[perdida_idx] = np.nan
    
    # Batería
    bateria = np.clip(np.linspace(100, 95, total_registros) + np.random.normal(0, 0.2, total_registros), 0, 100)
    
    # Crear DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'device_id': devices,
        'lat': np.round(latitudes, 6),
        'lon': np.round(longitudes, 6),
        'velocidad_kmh': np.round(velocidad, 1),
        'distancia_lateral_cm': np.round(distancia, 1),
        'bateria_porcentaje': np.round(bateria, 1)
    })
    
    output_path = os.path.join(RAW_DATA_FOLDER, f"wali_{nombre_calle}.csv")
    df.to_csv(output_path, index=False)
    print(f"   ✅ Guardado: {output_path}")
    print(f"   📊 Registros: {total_registros} | Dispositivos: {devices_list} | Riesgos: {num_riesgos}")
    total_archivos += 1

print("\n" + "="*60)
print(f"✅ ¡Generación completada! {total_archivos} archivos creados")
print("="*60)
print("\n📌 Próximos pasos:")
print("   1. Ejecutar: run_pipeline.py")
print("   2. Ejecutar: streamlit run 05_dashboard/app.py")
