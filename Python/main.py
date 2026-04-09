import requests
import json
import time
import os

ORION_HOST = os.getenv('ORION_HOST', 'localhost')
ENTITY_ID = 'urn:ngsi-ld:Vehicle:Bus_01'  # El ID de tu autobús en FIWARE
URL_MALAGA = 'https://datosabiertos.malaga.eu/recursos/transporte/EMT/EMTlineasUbicaciones/lineasyubicacionesfiware.geojson'

# Headers para actualizar atributos (PATCH)
headers = {
    'fiware-service': 'openiot',
    'fiware-servicepath': '/',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

def update_bus_location():
    print("Obteniendo datos de la EMT de Málaga...")
    try:
        # 1. Consultar la API de la EMT
        response_emt = requests.get(URL_MALAGA)
        
        if response_emt.status_code == 200:
            datos_emt = response_emt.json()
            
            # 2. Filtrar para quedarnos solo con la Línea 1.0
            buses_linea_1 = [bus for bus in datos_emt if bus.get('lineNumber') == "1.0"]
            
            if buses_linea_1:
                # Cogemos el primer autobús de la línea 1 para seguirlo
                bus_objetivo = buses_linea_1[0]
                coordenadas = bus_objetivo['location']['coordinates']
                
                print(f"Bus encontrado en Línea 1. Coordenadas: {coordenadas}")
                
                # 3. Preparamos el JSON SOLO con el atributo que queremos actualizar
                # FIWARE actualizará 'location' y dejará intactos 'speed' y 'temp' del ESP32
                patch_payload = {
                    "location": {
                        "type": "geo:json",
                        "value": {
                            "type": "Point",
                            "coordinates": [float(coordenadas[0]), float(coordenadas[1])]
                        }
                    }
                }
                
                # 4. Enviar la actualización a FIWARE Orion mediante PATCH
                url_orion = f'http://{ORION_HOST}:1026/v2/entities/{ENTITY_ID}/attrs'
                response_orion = requests.patch(url_orion, data=json.dumps(patch_payload), headers=headers)
                
                if response_orion.status_code == 204:
                    print("✅ Posición actualizada correctamente en FIWARE.")
                else:
                    print(f"❌ Error en FIWARE: {response_orion.status_code} - {response_orion.text}")
            else:
                print("No hay autobuses de la Línea 1 activos en este momento.")
        else:
            print(f"Error al contactar con Málaga: {response_emt.status_code}")
            
    except Exception as e:
        print(f"Error de conexión: {e}")

if __name__ == "__main__":
    print(f"Iniciando Sincronizador EMT Málaga -> FIWARE ({ENTITY_ID})")
    print("-" * 50)
    
    while True:
        update_bus_location()
        print("Esperando 90 segundos para la siguiente actualización...\n")
        time.sleep(90)