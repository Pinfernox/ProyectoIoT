import requests
import math
import json  

# El enlace directo a los datos abiertos de la EMT
URL_PARADAS = "https://datosabiertos.malaga.eu/recursos/transporte/EMT/EMTLineasYParadas/lineasyparadas.geojson"

def cargar_paradas_desde_enlace():
    print("🌍 Descargando ruta oficial desde la web de la EMT...")
    try:
        # Hacemos la petición a la web
        response = requests.get(URL_PARADAS)
        
        if response.status_code == 200:
            datos = response.json()
            coordenadas_paradas = []
            
            # Buscamos la línea 1
            for linea in datos:
                # Comprobamos diferentes posibles nombres del campo ID
                cod = str(linea.get('codLinea', '')).strip()
                user_cod = str(linea.get('userCodLinea', '')).strip()
                cod_str = str(linea.get('codLineaStr', '')).strip()
                
                if "1" in [cod, user_cod, cod_str] or "1.0" in [cod, user_cod, cod_str]:
                    for parada in linea.get('paradas', []):
                        # Extraemos [Longitud, Latitud]
                        lon = parada['parada']['longitud']
                        lat = parada['parada']['latitud']
                        coordenadas_paradas.append([lon, lat])
                        
            print(f"✅ Éxito: {len(coordenadas_paradas)} paradas de la Línea 1 extraídas.")
            
            # --- NUEVO: GUARDAR EN ARCHIVO JSON LOCAL ---
            if len(coordenadas_paradas) > 0:
                nombre_archivo = "ruta_linea1.json"
                try:
                    with open(nombre_archivo, 'w', encoding='utf-8') as f:
                        # json.dump escribe la lista directamente al archivo con un formato bonito (indent=4)
                        json.dump(coordenadas_paradas, f, indent=4)
                    print(f"💾 Archivo '{nombre_archivo}' creado y guardado correctamente en tu carpeta.")
                except Exception as e:
                    print(f"⚠️ Aviso: No se pudo guardar el archivo local: {e}")
            # --------------------------------------------
            
            return coordenadas_paradas
        else:
            print(f"❌ Error al conectar con la EMT. Código HTTP: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error de conexión o procesamiento: {e}")
        return []

# Fórmula del Haversine para calcular la distancia en metros entre dos coordenadas GPS
def distancia_haversine(lon1, lat1, lon2, lat2):
    R = 6371000  # Radio de la Tierra en metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

# Prueba rápida del script
if __name__ == "__main__":
    paradas = cargar_paradas_desde_enlace()
    if paradas:
        print(f"Ejemplo de coordenada parada 1: {paradas[0]}")