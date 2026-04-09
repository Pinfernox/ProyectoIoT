import requests

headers = {
    'fiware-service': 'openiot',
    'fiware-servicepath': '/'
}

url = 'http://localhost:1026/v2/entities/urn:ngsi-ld:Vehicle:Bus_01'
response = requests.delete(url, headers=headers)

if response.status_code == 204:
    print("✅ Autobús incompleto borrado con éxito.")
else:
    print(f"Resultado: {response.status_code} - {response.text}")