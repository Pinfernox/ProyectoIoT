import requests
import json
import time
import os
import random
from shapely.geometry import Point, LineString # <-- NUEVAS IMPORTACIONES GIS

ORION_HOST = os.getenv('ORION_HOST', 'localhost')
ENTITY_ID = 'urn:ngsi-ld:Vehicle:Bus_01'
URL_MALAGA = 'https://datosabiertos.malaga.eu/recursos/transporte/EMT/EMTlineasUbicaciones/lineasyubicacionesfiware.geojson'

pasajeros_actuales = 15

headers = {
    'fiware-service': 'openiot',
    'fiware-servicepath': '/',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# ==================== LÓGICA DE GEOFENCING (SHAPELY) ====================

def cargar_paradas_local(archivo='ruta_linea1.json'):
    print(f"📂 Cargando ruta oficial desde archivo estático ({archivo})...")
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            coordenadas_paradas = json.load(f)
            
        if len(coordenadas_paradas) > 1:
            # SHAPELY: Convertimos la lista de puntos sueltos en una LÍNEA GEOMÉTRICA CONTINUA
            ruta_linestring = LineString(coordenadas_paradas)
            print(f"✅ ¡Ruta asegurada! Creada geometría LineString con {len(coordenadas_paradas)} vértices.")
            return ruta_linestring
        else:
            print("❌ No hay suficientes puntos para crear una ruta.")
            return None
            
    except FileNotFoundError:
        print(f"❌ Error: No se encuentra el archivo {archivo}. Ejecuta primero el generador de rutas.")
        return None
    except Exception as e:
        print(f"❌ Error al leer el JSON local: {e}")
        return None

def comprobar_desvio(lon_actual, lat_actual, ruta_oficial_linestring):
    LIMITE_DESVIO_METROS = 300 
    
    # 1. SHAPELY: Creamos un punto geométrico con la posición actual del bus
    bus_ubicacion = Point(lon_actual, lat_actual)
    
    # 2. SHAPELY: Calculamos la distancia geométrica a la línea (nos la da en grados)
    distancia_grados = bus_ubicacion.distance(ruta_oficial_linestring)
    
    # 3. Convertimos los grados a metros (1 grado ≈ 111.139 km en el ecuador/meridianos)
    distancia_metros = distancia_grados * 111139
    
    if distancia_metros > LIMITE_DESVIO_METROS:
        print(f"🚨 ¡ALERTA GEOFENCING! El bus está a {int(distancia_metros)}m de la ruta oficial.")
        # ¡AQUÍ IRÁ EL AVISO DE TELEGRAM!
    else:
        print(f"📍 Ruta OK. Distancia a la línea oficial: {int(distancia_metros)}m.")

# ==================== SINCRONIZADOR FIWARE ====================

def update_bus_location(ruta_oficial):
    global pasajeros_actuales
    print("Obteniendo datos de la EMT de Málaga...")
    
    # Simular Pasajeros
    pasajeros_actuales += random.randint(-3, 5)
    pasajeros_actuales = max(0, min(50, pasajeros_actuales))
    
    try:
        response_emt = requests.get(URL_MALAGA)
        
        if response_emt.status_code == 200:
            datos_emt = response_emt.json()
            buses_linea_1 = [bus for bus in datos_emt if bus.get('lineNumber') == "1.0"]
            
            if buses_linea_1:
                coordenadas = buses_linea_1[0]['location']['coordinates']
                lon, lat = float(coordenadas[0]), float(coordenadas[1])
                print(f"Bus Línea 1 encontrado. Coordenadas: [{lon}, {lat}]")
                print(f"👥 Pasajeros a bordo: {pasajeros_actuales}")
                
                # Comprobar si se ha desviado de la ruta pasando la geometría de Shapely
                if ruta_oficial is not None:
                    comprobar_desvio(lon, lat, ruta_oficial)
                
                # Preparar JSON para FIWARE
                patch_payload = {
                    "location": {
                        "type": "geo:json",
                        "value": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        }
                    },
                    "passengers": {
                        "type": "Number",
                        "value": pasajeros_actuales
                    }
                }
                
                url_orion = f'http://{ORION_HOST}:1026/v2/entities/{ENTITY_ID}/attrs'
                response_orion = requests.patch(url_orion, data=json.dumps(patch_payload), headers=headers)
                
                if response_orion.status_code == 204:
                    print("✅ Posición y pasajeros actualizados en FIWARE.")
                else:
                    print(f"❌ Error en FIWARE: {response_orion.status_code}")
            else:
                print("No hay autobuses de la Línea 1 activos en este momento.")
        else:
            print(f"Error al contactar con Málaga: {response_emt.status_code}")
            
    except Exception as e:
        print(f"Error de conexión: {e}")

if __name__ == "__main__":
    print(f"Iniciando Sincronizador EMT Málaga -> FIWARE ({ENTITY_ID})")
    print("-" * 50)
    
    # Cargar la ruta estática y crear la geometría una sola vez al arrancar
    ruta_oficial_linea_1 = cargar_paradas_local('ruta_linea1.json')
    
    while True:
        update_bus_location(ruta_oficial_linea_1)
        print("Esperando 90 segundos para la siguiente actualización...\n")
        time.sleep(90)