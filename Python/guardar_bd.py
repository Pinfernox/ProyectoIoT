import json
import datetime
from google.cloud import bigquery
import paho.mqtt.client as mqtt

# ==================== CONFIGURACIÓN ====================
MQTT_BROKER = '34.79.66.20'  
MQTT_PORT = 1883
TOPIC_ESCUCHA = "/1234/esp32_bus01/attrs"

DATASET_ID = 'midataset'  
TABLE_ID = 'tablaBus'      

# ==================== CONEXIÓN A BIGQUERY ====================
print("⏳ Conectando a Google BigQuery...")
bigquery_client = bigquery.Client() 
table_ref = bigquery_client.dataset(DATASET_ID).table(TABLE_ID)
table = bigquery_client.get_table(table_ref)
print("✅ Conectado a BigQuery con éxito.")

# ==================== LÓGICA MQTT ====================
def on_connect(client, userdata, flags, rc):
    print(f"🔌 Conectado al Broker MQTT. Escuchando {TOPIC_ESCUCHA}...")
    client.subscribe(TOPIC_ESCUCHA)

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode('utf-8')
        datos = json.loads(payload_str)
        
        fila = {
            "speed": datos.get("speed", 0),
            "temp": datos.get("temp", 0),
            "hum": datos.get("hum", 0),
            "passengers": datos.get("passengers", 0),
            "lon": datos["location"]["coordinates"][0],
            "lat": datos["location"]["coordinates"][1],
            "when": datetime.datetime.utcnow().isoformat() 
        }
        
        rows_to_insert = [fila]
        errores = bigquery_client.insert_rows(table, rows_to_insert)
        
        if not errores:
            print(f"💾 Guardado en BD: Velocidad {fila['speed']}km/h, Temp {fila['temp']}ºC, Pasajeros {fila['passengers']}")
        else:
            print(f"❌ Error al guardar en BigQuery: {errores}")
            
    except Exception as e:
        print(f"❌ Error procesando el mensaje: {e}")

# ==================== INICIO DEL SCRIPT ====================
mqtt_client = mqtt.Client("Suscriptor_BigQuery_V1")
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_forever()