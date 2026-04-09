import requests
import json

IOTA_URL_SERVICES = 'http://localhost:4041/iot/services'
IOTA_URL_DEVICES = 'http://localhost:4041/iot/devices'

headers = {
    'fiware-service': 'openiot',
    'fiware-servicepath': '/',
    'Content-Type': 'application/json'
}

# 1. Crear el Grupo de Servicio (Definir la API Key '1234')
payload_service = {
    "services": [
        {
            "apikey": "1234",
            "cbroker": "http://orion:1026",
            "entity_type": "Vehicle",
            "resource": ""
        }
    ]
}

print("1. Creando Grupo de Servicio (API Key 1234)...")
resp_service = requests.post(IOTA_URL_SERVICES, headers=headers, data=json.dumps(payload_service))
if resp_service.status_code == 201 or resp_service.status_code == 409:
    print(" ✅ Grupo de servicio OK.")
else:
    print(f" ❌ Error Servicio: {resp_service.text}")

# 2. Registrar el Dispositivo ESP32
payload_device = {
    "devices": [
        {
            "device_id": "esp32_bus01",
            "entity_name": "urn:ngsi-ld:Vehicle:Bus_01",
            "entity_type": "Vehicle",
            "protocol": "IoTA-JSON",
            "transport": "MQTT",
            "timezone": "Europe/Madrid",
            "attributes": [
                { "object_id": "speed", "name": "speed", "type": "Number" },
                { "object_id": "temp", "name": "temp", "type": "Number" }
            ]
        }
    ]
}

print("2. Registrando Dispositivo ESP32...")
resp_device = requests.post(IOTA_URL_DEVICES, headers=headers, data=json.dumps(payload_device))
if resp_device.status_code == 201:
    print(" ✅ Dispositivo registrado OK. ¡Fusión de datos lista!")
elif resp_device.status_code == 409:
    print(" ⚠️ El dispositivo ya existía en esta base de datos.")
else:
    print(f" ❌ Error Dispositivo: {resp_device.text}")