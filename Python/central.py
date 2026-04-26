import json
import threading
from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
from shapely.geometry import Point, LineString, MultiLineString

app = Flask(__name__)

# ==================== CONFIGURACIÓN ====================
MQTT_BROKER = '10.193.248.240' # <--- Puesto igual que el ESP32
MQTT_PORT = 1883
TOPIC_ESCUCHA = "/1234/esp32_bus01/attrs"
TOPIC_ALERTA = "/1234/esp32_bus01/alert"
LIMITE_DESVIO_METROS = 300 
ruta_maestra = None

ultimo_estado = {
    "speed": 0, "temp": 0, "hum": 0, "passengers": 0, 
    "lon": 0, "lat": 0, "alerta": "OK"
}

# Cambiamos el nombre por si el antiguo Python sigue corriendo de fondo
mqtt_client = mqtt.Client("Central_Web_Dashboard_V2")

# ==================== LÓGICA GEOFENCING Y MQTT ====================
def cargar_rutas_geojson(archivo='linea1.geojson'):
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            lineas = [LineString(feat.get('geometry', {}).get('coordinates', [])) 
                      for feat in json.load(f).get('features', []) 
                      if len(feat.get('geometry', {}).get('coordinates', [])) > 1]
            if lineas: return MultiLineString(lineas)
    except Exception:
        pass
    return None

# Usamos *args para que no dé error importe la versión de Paho-MQTT que tengas
def on_connect(client, userdata, flags, *args):
    print(f"🔌 Conectado al Broker. Suscribiendo al canal: {TOPIC_ESCUCHA}...")
    client.subscribe(TOPIC_ESCUCHA)

def on_message(client, userdata, msg):
    global ultimo_estado
    try:
        payload_str = msg.payload.decode('utf-8')
        # ¡CHIVATO! Imprimirá en la consola de Python cada vez que el ESP32 hable
        print(f"📥 DATO CAZADO POR LA CENTRAL: {payload_str}")
        
        datos = json.loads(payload_str)
        
        # Actualizamos el estado
        ultimo_estado["speed"] = datos.get("speed", 0)
        ultimo_estado["temp"] = datos.get("temp", 0)
        ultimo_estado["hum"] = datos.get("hum", 0)
        ultimo_estado["passengers"] = datos.get("passengers", 0)
        
        lon = datos["location"]["coordinates"][0]
        lat = datos["location"]["coordinates"][1]
        ultimo_estado["lon"] = lon
        ultimo_estado["lat"] = lat
        
        ultimo_estado["alerta"] = "OK"

        # Comprobar automático (Aforo)
        if ultimo_estado["passengers"] >= 50:
            ultimo_estado["alerta"] = "BUS LLENO"
            client.publish(TOPIC_ALERTA, "LLENO")

        # Comprobar automático (Desvío)
        if ruta_maestra is not None:
            distancia = Point(lon, lat).distance(ruta_maestra) * 111139
            if distancia > LIMITE_DESVIO_METROS:
                ultimo_estado["alerta"] = f"DESVÍO ({int(distancia)}m)"
                client.publish(TOPIC_ALERTA, "DESVIO")
                
    except Exception as e:
        print(f"❌ Error procesando JSON: {e}")

# ==================== RUTAS WEB (FLASK) ====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/datos')
def get_datos():
    return jsonify(ultimo_estado)

@app.route('/api/alerta', methods=['POST'])
def enviar_alerta_manual():
    orden = request.json.get('orden')
    mqtt_client.publish(TOPIC_ALERTA, orden)
    return jsonify({"status": "Mensaje enviado a ESP32"})

# ==================== INICIO DEL SISTEMA ====================
if __name__ == "__main__":
    ruta_maestra = cargar_rutas_geojson('linea1.geojson')
    
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        mqtt_client.loop_start() 
        print("🚀 Levantando Dashboard Web en http://10.193.248.240:5000")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"❌ Error de red al iniciar: {e}")