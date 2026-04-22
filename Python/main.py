import requests
import json
import time
import random
import paho.mqtt.client as mqtt

# ==================== CONFIGURACIÓN MQTT ====================
MQTT_BROKER = '127.0.0.1' # o 'localhost'. Así nunca fallará, cambie o no el WiFi. # <-- Tu IP local
MQTT_PORT = 1883
MQTT_TOPIC_GPS = "bus/local/position"            # Canal exclusivo para mandar datos al ESP32

# URL de datos abiertos EMT Málaga
URL_MALAGA = 'https://datosabiertos.malaga.eu/recursos/transporte/EMT/EMTlineasUbicaciones/lineasyubicacionesfiware.geojson'

pasajeros_actuales = 10

# ==================== INICIALIZAR MQTT ====================
print("🔌 Conectando al Broker MQTT local...")
mqtt_client = mqtt.Client("Python_GPS_Provider")
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start() # Arranca en segundo plano
    print("✅ Conectado al Broker MQTT con éxito.")
except Exception as e:
    print(f"❌ Error fatal al conectar al Broker MQTT: {e}")
    exit()

# ==================== OBTENCIÓN Y ENVÍO DE DATOS ====================
def update_bus_location():
    global pasajeros_actuales
    print("\n📡 Buscando posición del autobús de Málaga en vivo...")
    
    # Simular Pasajeros subiendo y bajando
    pasajeros_actuales += random.randint(-5, 7)
    pasajeros_actuales = max(0, min(50, pasajeros_actuales))

    try:
        # Añadimos un User-Agent para que el servidor de la EMT crea que somos un navegador real
        headers_web = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response_emt = requests.get(URL_MALAGA, headers=headers_web)
        
        if response_emt.status_code == 200:
            try:
                # Intentamos convertir la respuesta a JSON
                datos_emt = response_emt.json()
            except Exception as e:
                # Si falla, imprimimos los primeros 200 caracteres de lo que nos ha mandado el servidor
                print("❌ Error: La EMT no ha devuelto un JSON válido.")
                print(f"📄 Respuesta cruda del servidor: {response_emt.text[:200]}...")
                return

            # Buscamos el bus que pertenece a la línea 1
            buses_linea_1 = [bus for bus in datos_emt if bus.get('lineNumber') == "1.0"]
            
            if buses_linea_1:
                coordenadas = buses_linea_1[0]['location']['coordinates']
                lon, lat = float(coordenadas[0]), float(coordenadas[1])
                print(f"🚌 Bus Línea 1 detectado en: [{lon}, {lat}]")
                print(f"👥 Pasajeros a bordo: {pasajeros_actuales}")
                
                # --- LÓGICA MQTT ---
                payload_local = {
                    "lat": lat,
                    "lon": lon,
                    "passengers": pasajeros_actuales
                }
                
                # Publicamos en el broker
                mqtt_client.publish(MQTT_TOPIC_GPS, json.dumps(payload_local))
                print(f"📤 Datos inyectados al ESP32 por MQTT: {payload_local}")
                
            else:
                print("💤 No hay autobuses de la Línea 1 circulando en este momento.")
        else:
            print(f"❌ Error de servidor EMT: Código {response_emt.status_code}")
            
    except Exception as e:
        print(f"❌ Error general de conexión: {e}")
        
# ==================== BUCLE PRINCIPAL ====================
if __name__ == "__main__":
    print(f"=== Proveedor de Datos EMT -> ESP32 Gateway ===")
    
    while True:
        update_bus_location()
        print("⏳ Esperando 90 segundos para la próxima actualización...")
        time.sleep(90)