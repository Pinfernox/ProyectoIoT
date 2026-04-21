import requests
import json
import os

ORION_HOST = os.getenv('ORION_HOST', 'localhost')

json_dict = {
    "id": "urn:ngsi-ld:Vehicle:Bus_01",
    "type": "Vehicle",
    "vehicleType": { "type": "Text", "value": "bus" },
    "speed": { "type": "Number", "value": 0 },
    "temp": { "type": "Number", "value": 0 },
    "humidity": { "type": "Number", "value": 0},
    "passengers": { "type": "Number", "value": 0},
    "location": {
        "type": "geo:json",
        "value": {
            "type": "Point",
            "coordinates": [-4.416324, 36.723835] 
        }
    }
}

headers = {
    'fiware-service': 'openiot',
    'fiware-servicepath': '/',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
url = f'http://{ORION_HOST}:1026/v2/entities'

print(f"Creando entidad en FIWARE: {json_dict['id']}...")
response = requests.post(url, data=json.dumps(json_dict), headers=headers)

if response.status_code == 201:
    print("✅ Autobús inicializado correctamente en Orion.")
elif response.status_code == 422:
    print("⚠️ La entidad ya existe. No es necesario volver a crearla.")
else:
    print(f"❌ Error {response.status_code}: {response.text}")