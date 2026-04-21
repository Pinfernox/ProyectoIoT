import requests
import json
import time

headers = {
    'fiware-service': 'openiot',
    'fiware-servicepath': '/',
    'Accept': 'application/json'
}

# Añade ?options=keyValues al final
url = 'http://localhost:1026/v2/entities/urn:ngsi-ld:Vehicle:Bus_01?options=keyValues'

print("Iniciando Monitor de FIWARE (Habitación 'openiot')...")

while True:
    try:
        response = requests.get(url, headers=headers)

        print("\n" + "="*50)
        print(f"📡 DATOS ACTUALIZADOS | HORA LOCAL: {time.strftime('%H:%M:%S')}")
        print("="*50)

        if response.status_code == 200:
            # Lo imprimimos bonito
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error de conexión con Orion: {e}")

    # Esperamos 10 segundos antes de volver a preguntar
    time.sleep(10)