import requests
import math
import json  

# URL de datos abiertos EMT Málaga
URL_PARADAS = "https://datosabiertos.malaga.eu/recursos/transporte/EMT/EMTLineasYParadas/lineasyparadas.geojson"

def cargar_paradas_desde_enlace():
    print("🌍 Descargando ruta oficial desde la web de la EMT...")
    
    try:
        response = requests.get(URL_PARADAS)
        
        if response.status_code == 200:
            datos = response.json()

            ida = []
            vuelta = []

            for linea in datos:
                cod = str(linea.get('codLineaStr', '')).strip()

                if cod == "1":
                    paradas = linea.get('paradas', [])

                    paradas_ordenadas = sorted(paradas, key=lambda x: x['orden'])

                    for p in paradas_ordenadas:
                        lon = p['parada']['longitud']
                        lat = p['parada']['latitud']
                        sentido = p['sentido']

                        if sentido == 1:
                            ida.append([lon, lat])
                        elif sentido == 2:
                            vuelta.append([lon, lat])

            print(f"✅ Ida: {len(ida)} paradas")
            print(f"✅ Vuelta: {len(vuelta)} paradas")

            return ida, vuelta

        else:
            print(f"❌ Error HTTP: {response.status_code}")
            return [], []

    except Exception as e:
        print(f"❌ Error: {e}")
        return [], []


def guardar_geojson(ida, vuelta):
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"sentido": "ida"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": ida
                }
            },
            {
                "type": "Feature",
                "properties": {"sentido": "vuelta"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": vuelta
                }
            }
        ]
    }

    with open("linea1.geojson", "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=4)

    print("💾 Archivo 'linea1.geojson' creado correctamente")


def distancia_haversine(lon1, lat1, lon2, lat2):
    R = 6371000  

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c



if __name__ == "__main__":
    ida, vuelta = cargar_paradas_desde_enlace()

    if ida and vuelta:
        print(f"📍 Primera parada ida: {ida[0]}")
        print(f"📍 Primera parada vuelta: {vuelta[0]}")

        # Guardar GeoJSON para visualizar en geojson.io
        guardar_geojson(ida, vuelta)
