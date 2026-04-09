#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <PubSubClient.h>

// ================= CONFIGURACIÓN DE RED =================
const char* ssid = "Wokwi-GUEST"; // Red WiFi por defecto del simulador Wokwi
const char* password = "";

// ⚠️ ¡MUY IMPORTANTE! Pon aquí la dirección IPv4 de tu ordenador (ej. "192.168.1.33")
// No uses "localhost" ni "127.0.0.1", porque el ESP32 pensaría que es él mismo.
const char* mqtt_server = "192.168.1.14"; 
const int mqtt_port = 1883;

// Topic estándar de FIWARE IoT Agent: /<api_key>/<device_id>/attrs
const char* mqtt_topic = "/1234/esp32_bus01/attrs"; 

WiFiClient espClient;
PubSubClient client(espClient);

// ================= CONFIGURACIÓN HARDWARE =================
// Pantalla OLED
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// DHT22
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// Pines Sensores/Actuadores
const int potPin = 34;   // Acelerador
const int ledPin = 2;    // Alerta
const int buzzerPin = 5; // Alarma sonora

// ================= FUNCIONES DE RED =================
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("✅ WiFi conectado.");
  Serial.print("Dirección IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect_mqtt() {
  // Bucle hasta que estemos reconectados al broker MQTT
  while (!client.connected()) {
    Serial.print("Intentando conexión MQTT a ");
    Serial.print(mqtt_server);
    Serial.print("...");
    
    // Intentar conectar con un ID de cliente aleatorio
    String clientId = "ESP32Client-Bus01";
    if (client.connect(clientId.c_str())) {
      Serial.println(" ✅ Conectado al Broker Mosquitto!");
    } else {
      Serial.print(" ❌ Falló, rc=");
      Serial.print(client.state());
      Serial.println(" Nuevo intento en 5 segundos");
      delay(5000);
    }
  }
}

// ================= SETUP PRINCIPAL =================
void setup() {
  Serial.begin(115200);
  
  pinMode(ledPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);
  dht.begin();

  // Inicializar Pantalla I2C
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Error al iniciar OLED"));
    for(;;);
  }
  
  // Pantalla de carga
  display.clearDisplay();
  display.setTextColor(WHITE);
  display.setTextSize(1);
  display.setCursor(0,20);
  display.println("Iniciando Sistema...");
  display.display();

  // Iniciar conexiones
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

// ================= BUCLE PRINCIPAL =================
void loop() {
  // Asegurar conexión MQTT
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop(); // Mantener vivo el cliente MQTT

  // 1. Leer Sensores
  int potValue = analogRead(potPin);
  float speed = map(potValue, 0, 4095, 0, 80);
  float temp = dht.readTemperature();

  // 2. Crear Objeto JSON (Solo datos físicos para FIWARE)
  StaticJsonDocument<200> doc;
  // Los nombres "speed" y "temp" DEBEN coincidir con el script de aprovisionamiento de Python
  doc["speed"] = speed; 
  doc["temp"] = temp;

  // 3. Convertir JSON a texto y publicarlo por MQTT
  char jsonBuffer[200];
  serializeJson(doc, jsonBuffer);
  
  Serial.print("Enviando MQTT: ");
  Serial.println(jsonBuffer);
  
  client.publish(mqtt_topic, jsonBuffer);

  // 4. Mostrar en Pantalla OLED
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0,0);
  display.println("SISTEMA BUS - MUII");
  display.drawLine(0, 10, 128, 10, WHITE);
  
  display.setCursor(0,25);
  display.print("VEL:  "); display.print(speed, 0); display.println(" km/h");
  
  display.setCursor(0,45);
  display.print("TEMP: "); display.print(temp, 1); display.println(" C");
  
  display.display();

  // 5. Simulación de alerta (Si velocidad > 60)
  if(speed > 60) {
    digitalWrite(ledPin, HIGH);
    tone(buzzerPin, 440); 
    delay(100);           
    noTone(buzzerPin);    
    delay(100);           
    tone(buzzerPin, 440); 
    delay(100);
    noTone(buzzerPin);
    
    // Como el delay de arriba suma 300ms, ajustamos el retardo final para mantener ciclo de ~2s
    delay(1700); 
  } else {
    digitalWrite(ledPin, LOW);
    delay(2000); // Frecuencia de envío constante
  }
}