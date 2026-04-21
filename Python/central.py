import json
import time
import paho.mqtt.client as mqtt
from shapely.geometry import Point, LineString, MultiLineString

# ==================== CONFIGURACIÓN ====================
MQTT_BROKER = '127.0.0.1' # o 'localhost'. Así nunca fallará, cambie o no el WiFi. # <-- Tu IP local
MQTT_PORT = 1883

# Canales de comunicación
TOPIC_ESCUCHA = "/1234/esp32_bus01/attrs"  # Lo que dice el ESP32
TOPIC_ALERTA = "/1234/esp32_bus01/alert"   # Órdenes hacia el ESP32

LIMITE_DESVIO_METROS = 300 
ruta_maestra = None

# ==================== CARGAR MAPA GEOJSON ====================
def cargar_rutas_geojson(archivo='linea1.geojson'):
    print(f"🗺️ Cargando mapa oficial ({archivo})...")
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            
        lineas = []
        for feature in geojson_data.get('features', []):
            coords = feature.get('geometry', {}).get('coordinates', [])
            if len(coords) > 1:
                lineas.append(LineString(coords))
                
        if lineas:
            print("✅ Mapa cargado y listo para supervisión.")
            return MultiLineString(lineas)
    except Exception as e:
        print(f"❌ Error al leer el GeoJSON: {e}")
    return None

# ==================== LÓGICA DEL BROKER MQTT ====================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("🔌 Conectado al Broker MQTT como 'Centralita'")
        client.subscribe(TOPIC_ESCUCHA)
        print(f"🎧 Escuchando telemetría del bus en: {TOPIC_ESCUCHA}")
    else:
        print(f"❌ Error al conectar, código: {rc}")

def on_message(client, userdata, msg):
    # Esta función se dispara AUTOMÁTICAMENTE cada vez que el ESP32 habla
    try:
        payload = msg.payload.decode('utf-8')
        datos = json.loads(payload)
        
        # Extraemos los datos del paquete que mandó el ESP32
        velocidad = datos.get("speed", 0)
        pasajeros = datos.get("passengers", 0)
        
        # Extraer coordenadas (GeoJSON Point format: [lon, lat])
        lon = datos["location"]["coordinates"][0]
        lat = datos["location"]["coordinates"][1]
        
        print(f"\n🚌 DATOS RECIBIDOS -> Vel: {velocidad}km/h | Pax: {pasajeros} | Pos: [{lon}, {lat}]")
        
        # 1. Comprobar Aforo
        if pasajeros >= 50:
            print("🚨 CENTRAL: ¡Bus LLENO! Mandando orden de alerta al ESP32.")
            client.publish(TOPIC_ALERTA, "LLENO")

        # 2. Comprobar Geofencing
        if ruta_maestra is not None:
            bus_ubicacion = Point(lon, lat)
            distancia_metros = bus_ubicacion.distance(ruta_maestra) * 111139
            
            if distancia_metros > LIMITE_DESVIO_METROS:
                print(f"🚨 CENTRAL: ¡Desvío detectado! ({int(distancia_metros)}m). Mandando alerta.")
                client.publish(TOPIC_ALERTA, "DESVIO")
            else:
                print(f"📍 Ruta OK. Desviación: {int(distancia_metros)}m.")

    except Exception as e:
        print(f"⚠️ Error al procesar el mensaje: {e}")

# ==================== INICIO DEL SISTEMA ====================
if __name__ == "__main__":
    print("=== INICIANDO CENTRAL DE SUPERVISIÓN ===")
    
    # 1. Cargar el mapa geométrico
    ruta_maestra = cargar_rutas_geojson('linea1.geojson')
    
    # 2. Conectar al MQTT y quedarse escuchando indefinidamente
    client = mqtt.Client("Central_Supervisor")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        client.loop_forever() # Mantiene el script vivo escuchando
    except KeyboardInterrupt:
        print("\n🛑 Centralita apagada.")
    except Exception as e:
        print(f"❌ Error de red: {e}")