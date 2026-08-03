import subprocess
import sys
import os
import time
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE RUTAS
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

SCRIPTS = [
    os.path.join(SCRIPT_DIR, "01_limpieza.py"),
    os.path.join(SCRIPT_DIR, "02_deteccion_eventos.py"),
    os.path.join(SCRIPT_DIR, "03_map_matching.py")
]

# ==========================================
# FUNCIÓN: Ejecutar un script con captura de errores
# ==========================================
def ejecutar_script(script_path):
    if not os.path.exists(script_path):
        return False, f"Script no encontrado: {script_path}", ""
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,  # ← Capturar stdout y stderr
            text=True,
            check=True,
            cwd=PROJECT_ROOT
        )
        return True, result.stdout, ""
    except subprocess.CalledProcessError as e:
        # Capturar el error completo
        error_msg = f"Error código {e.returncode}\n\nSTDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}"
        return False, e.stdout, e.stderr
    except Exception as e:
        return False, "", str(e)

# ==========================================
# EJECUCIÓN DEL PIPELINE
# ==========================================
print("=" * 70)
print("🚀 PIPELINE WALI - INICIO DE EJECUCIÓN")
print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📂 Raíz del proyecto: {PROJECT_ROOT}")
print("=" * 70)

inicio_total = time.time()
resultados = []

for i, script in enumerate(SCRIPTS, 1):
    print(f"\n{'─' * 70}")
    print(f"▶️  [{i}/{len(SCRIPTS)}] Ejecutando: {os.path.basename(script)}")
    print(f"{'─' * 70}")
    
    inicio_script = time.time()
    exitoso, stdout, stderr = ejecutar_script(script)
    duracion_script = time.time() - inicio_script
    
    # Mostrar la salida del script
    if stdout:
        print(stdout)
    
    resultados.append({
        'script': os.path.basename(script),
        'exitoso': exitoso,
        'duracion': duracion_script,
        'stderr': stderr
    })
    
    if exitoso:
        print(f"\n✅ {os.path.basename(script)} completado en {duracion_script:.2f}s")
    else:
        print(f"\n❌ ERROR en {os.path.basename(script)}")
        if stderr:
            print(f"\n{'─' * 70}")
            print("DETALLE DEL ERROR:")
            print(f"{'─' * 70}")
            print(stderr)
            print(f"{'─' * 70}")
        print("\n⛔ Pipeline detenido debido a error.")
        break

# ==========================================
# RESUMEN FINAL
# ==========================================
duracion_total = time.time() - inicio_total

print(f"\n{'=' * 70}")
print("📊 RESUMEN DE EJECUCIÓN")
print(f"{'=' * 70}")

for res in resultados:
    estado = "✅" if res['exitoso'] else "❌"
    print(f"{estado} {res['script']} ({res['duracion']:.2f}s)")

print(f"\n⏱️  Tiempo total: {duracion_total:.2f}s")

if all(r['exitoso'] for r in resultados):
    print(f"\n🎉 ¡PIPELINE COMPLETADO EXITOSAMENTE!")
    print(f"   Los datos están listos para el dashboard en:")
    print(f"   - 02_processed_data/datos_procesados.parquet")
    print(f"   - 03_aggregated_data/eventos_riesgo.parquet")
else:
    print(f"\n⚠️  Pipeline completado con errores.")
    sys.exit(1)

print(f"{'=' * 70}")