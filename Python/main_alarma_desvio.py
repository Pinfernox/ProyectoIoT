import requests
import json
import time
import random
import paho.mqtt.client as mqtt

# ==================== CONFIGURACIÓN MQTT ====================
MQTT_BROKER = '34.79.66.20'
MQTT_PORT = 1883
MQTT_TOPIC_GPS = "bus/local/position"     # Canal exclusivo para mandar datos al ESP32

# URL de datos abiertos EMT Málaga
URL_MALAGA = 'https://datosabiertos.malaga.eu/recursos/transporte/EMT/EMTlineasUbicaciones/lineasyubicacionesfiware.geojson'

# ==================== VARIABLES GLOBALES ====================
pasajeros_actuales = 10
ultima_lon = None  
ultima_lat = None  

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
    global pasajeros_actuales, ultima_lon, ultima_lat
    
    print("\n📡 Buscando posición del autobús de Málaga en vivo...")

    try:
        headers_web = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response_emt = requests.get(URL_MALAGA, headers=headers_web)
        
        if response_emt.status_code == 200:
            try:
                datos_emt = response_emt.json()
            except Exception as e:
                print("❌ Error: La EMT no ha devuelto un JSON válido.")
                print(f"📄 Respuesta cruda del servidor: {response_emt.text[:200]}...")
                return

            # Buscamos el bus que pertenece a la línea 1
            buses_linea_1 = [bus for bus in datos_emt if bus.get('lineNumber') == "1.0"]
            
            if buses_linea_1:
                coordenadas = buses_linea_1[0]['location']['coordinates']
                #lon, lat = float(coordenadas[0]), float(coordenadas[1])
                lon, lat = float(coordenadas[0]) + 0.02, float(coordenadas[1])                

                if lon != ultima_lon or lat != ultima_lat:
                    print(f"🚌 Bus Línea 1 EN MOVIMIENTO detectado en: [{lon}, {lat}]")
                    pasajeros_actuales += random.randint(-4, 8)
                    pasajeros_actuales = max(0, min(50, pasajeros_actuales))
                    ultima_lon = lon
                    ultima_lat = lat
                else:
                    print(f"🛑 Bus Línea 1 PARADO en: [{lon}, {lat}]. El aforo se mantiene.")
                
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
        print("⏳ Esperando 10 segundos para la próxima actualización...")
        time.sleep(10)