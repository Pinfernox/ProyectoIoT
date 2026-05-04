#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <PubSubClient.h>

// ================= 1. CONFIGURACIÓN DE RED Y FIWARE =================
const char* ssid = "Original bro"; // Wifi Local       
const char* password = "pinfernox";      
const char* mqtt_server = "34.79.66.20";  
const int mqtt_port = 1883;

// Tópicos MQTT
const char* mqtt_topic_pub = "/1234/esp32_bus01/attrs"; // Hacia FIWARE
const char* mqtt_topic_sub = "bus/local/position";      // Escuchando el GPS 
const char* mqtt_topic_alert = "/1234/esp32_bus01/alert"; // Escuchando Alertas


float current_lat = 36.723835; 
float current_lon = -4.416324;
int current_passengers = 0;

// ================= CONFIGURACIÓN DE HARDWARE =================
const int potPin = 34;     
const int buzzerPin = 5;   
const int ledESP = 2;      
#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

WiFiClient espClient;
PubSubClient client(espClient);


// ================= RECEPCIÓN DE DATOS =================
void callback(char* topic, byte* payload, unsigned int length) {
  String incomingMessage = "";
  for (int i = 0; i < length; i++) { incomingMessage += (char)payload[i]; }
  
  Serial.print("📥 Recibido en ["); Serial.print(topic); Serial.print("]: "); Serial.println(incomingMessage);

  if (String(topic) == mqtt_topic_sub) {
    StaticJsonDocument<200> docRecibido;
    DeserializationError error = deserializeJson(docRecibido, incomingMessage);
    if (!error) {
      current_lat = docRecibido["lat"]; current_lon = docRecibido["lon"]; current_passengers = docRecibido["passengers"];
    }
  } 
  else if (String(topic) == mqtt_topic_alert) {
    display.clearDisplay(); display.setTextSize(2); display.setTextColor(WHITE); display.setCursor(0, 15);

    // ALERTA 1: AFORO SUPERADO 
    if (incomingMessage == "LLENO") {
      display.println("AFORO\nCOMPLETO!"); display.display();
      tone(buzzerPin, 2000, 150); delay(200); tone(buzzerPin, 2000, 150); delay(200); tone(buzzerPin, 2000, 150);
    } 
    // ALERTA 2: DESVÍO POR ERROR 
    else if (incomingMessage == "DESVIO_ERROR") {
      display.println("!FUERA\nDE RUTA!"); display.display();
      tone(buzzerPin, 200, 1200); 
    }
    // ALERTA 3: OBRAS 
    else if (incomingMessage == "DESVIO_OBRAS") {
      display.println("AVISO:\nOBRAS!"); display.display();
      tone(buzzerPin, 800, 300); delay(300); tone(buzzerPin, 600, 300); delay(300); tone(buzzerPin, 800, 300);
    }
    
    delay(2500); 
  }
}


// ================= FUNCIONES DE CONEXIÓN =================
void setup_wifi() {
  delay(10);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    digitalWrite(ledESP, !digitalRead(ledESP)); 
  }
  digitalWrite(ledESP, LOW); 
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Intentando conexión MQTT...");
    digitalWrite(ledESP, HIGH); 
    
    if (client.connect("ESP32Client-Bus01")) {
      Serial.println("✅ Conectado!");
      digitalWrite(ledESP, LOW); 
      client.subscribe(mqtt_topic_sub);
      client.subscribe(mqtt_topic_alert);
    } else {
      Serial.print("❌ Falló, código de error: ");
      Serial.print(client.state());
      Serial.println(" -> Intentando de nuevo en 5 seg");
      delay(5000);
    }
  }
}


// ================= ARRANQUE DEL SISTEMA =================
void setup() {
  Serial.begin(115200);
  pinMode(buzzerPin, OUTPUT);
  pinMode(ledESP, OUTPUT);
  dht.begin();

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    for(;;); 
  }
  display.ssd1306_command(SSD1306_DISPLAYON);
  display.ssd1306_command(SSD1306_SETCONTRAST);
  display.ssd1306_command(255);
  display.clearDisplay();

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  
  client.setCallback(callback); 
}


void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); 

  float speed = map(analogRead(potPin), 0, 4095, 0, 80);
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();

  if (isnan(temp) || isnan(hum)) { temp = 0.0; hum = 0.0; }

  // --- CREAR PAQUETE GIGANTE PARA FIWARE ---
  StaticJsonDocument<512> doc;
  doc["speed"] = speed;
  doc["temp"] = temp;
  doc["hum"] = hum;
  doc["passengers"] = current_passengers; 
  
  JsonObject location = doc.createNestedObject("location");
  location["type"] = "Point";
  JsonArray coordinates = location.createNestedArray("coordinates");
  coordinates.add(current_lon); 
  coordinates.add(current_lat); 
  
  char buffer[512];
  serializeJson(doc, buffer);
  
  Serial.print("📡 Publicando TODO a FIWARE: ");
  Serial.println(buffer);
  client.publish(mqtt_topic_pub, buffer);

  // --- PANTALLA OLED ---
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(0,0);
  display.println("SISTEMA BUS - ONLINE");
  display.drawLine(0, 10, 128, 10, WHITE);
  
  display.setCursor(0,20); display.printf("VEL: %.0f km/h", speed);
  display.setCursor(0,35); display.printf("TMP: %.1f C\n", temp);
  
  display.setCursor(0,50); display.printf("PASAJEROS: %d\n", current_passengers); 

  // --- LÓGICA DE ALARMAS ---
  // ALERTA 4: EXCESO DE VELOCIDAD 
  if(speed > 60) {
    display.setCursor(85, 20); display.print("!EXCESO!"); 
    display.display(); 
    
    tone(buzzerPin, 1000, 150); delay(150);
    tone(buzzerPin, 1000, 150); delay(150);
    
    digitalWrite(ledESP, HIGH); delay(100); digitalWrite(ledESP, LOW); delay(100);
    digitalWrite(ledESP, HIGH); delay(100); digitalWrite(ledESP, LOW); delay(100);
    
    unsigned long startWait = millis();
    while(millis() - startWait < 800) { client.loop(); delay(10); }

  } else {
    display.display(); 
    digitalWrite(ledESP, HIGH); 
    
    unsigned long startWait = millis();
    while(millis() - startWait < 2000) { client.loop(); delay(10); }
  }
}