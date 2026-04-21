#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <PubSubClient.h>

// ================= 1. CONFIGURACIÓN DE RED Y FIWARE =================
const char* ssid = "Original bro";         // <-- ¡Pon aquí tu WiFi!
const char* password = "pinfernox";      // <-- ¡Pon aquí tu contraseña!
const char* mqtt_server = "10.133.146.240";   // <-- IP de tu ordenador
const int mqtt_port = 1883;

// Tópicos MQTT
const char* mqtt_topic_pub = "/1234/esp32_bus01/attrs"; // Hacia FIWARE
const char* mqtt_topic_sub = "bus/local/position";      // Escuchando el GPS (Python 1)
const char* mqtt_topic_alert = "/1234/esp32_bus01/alert"; // <-- NUEVO: Escuchando Alertas (Python 2)

// ================= 2. VARIABLES DEL GEMELO DIGITAL =================
// Guardamos los últimos datos recibidos (les damos un valor inicial realista)
float current_lat = 36.723835; 
float current_lon = -4.416324;
int current_passengers = 0;

// ================= 3. CONFIGURACIÓN DE HARDWARE =================
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


// ================= 4. RECEPCIÓN DE DATOS (NUEVO CALLBACK INTELIGENTE) =================
void callback(char* topic, byte* payload, unsigned int length) {
  // Convertir el mensaje recibido en un texto (String)
  String incomingMessage = "";
  for (int i = 0; i < length; i++) {
    incomingMessage += (char)payload[i];
  }
  
  // Imprimir por dónde ha entrado el mensaje
  Serial.print("📥 Recibido en ["); Serial.print(topic); Serial.print("]: ");
  Serial.println(incomingMessage);

  // --- CASO A: VIENE DEL PROVEEDOR GPS ---
  if (String(topic) == mqtt_topic_sub) {
    StaticJsonDocument<200> docRecibido;
    DeserializationError error = deserializeJson(docRecibido, incomingMessage);

    if (!error) {
      current_lat = docRecibido["lat"];
      current_lon = docRecibido["lon"];
      current_passengers = docRecibido["passengers"];
      Serial.println("✅ Posición y pasajeros actualizados en memoria.");
    } else {
      Serial.println("❌ Error al leer el JSON de Python");
    }
  } 
  
  // --- CASO B: VIENE DE LA CENTRALITA (ALERTAS) ---
  else if (String(topic) == mqtt_topic_alert) {
    display.clearDisplay();
    display.setTextSize(2);
    display.setTextColor(WHITE);
    display.setCursor(0, 20);

    if (incomingMessage == "LLENO") {
      display.println("BUS LLENO!");
      display.display();
      // Alarma aguda y rápida
      tone(buzzerPin, 2000, 150); delay(200);
      tone(buzzerPin, 2000, 150); delay(200);
      tone(buzzerPin, 2000, 150);
    } 
    else if (incomingMessage == "DESVIO") {
      display.println("DESVIO RUTA");
      display.display();
      // Alarma grave y sostenida
      tone(buzzerPin, 300, 1000); 
    }
    
    delay(1500); // Dejar el mensaje en pantalla un momento
  }
}


// ================= 5. FUNCIONES DE CONEXIÓN =================
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
      
      // <-- NUEVO: Nos suscribimos a LOS DOS canales
      client.subscribe(mqtt_topic_sub);
      client.subscribe(mqtt_topic_alert);
    } else {
      delay(5000);
    }
  }
}


// ================= 6. ARRANQUE DEL SISTEMA =================
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


// ================= 7. BUCLE PRINCIPAL =================
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); // <- Muy importante para mantener vivo el MQTT

  // --- LECTURA FÍSICA ---
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
  
  // Mostramos también los pasajeros en la pantalla
  display.setCursor(0,50); display.printf("PASAJEROS: %d\n", current_passengers); 

  // --- LÓGICA DE ALARMAS Y ESPERAS INTELIGENTES ---
  if(speed > 60) {
    display.setCursor(85, 20); display.print("!ALERTA!"); 
    display.display(); 
    tone(buzzerPin, 440, 500); 
    
    digitalWrite(ledESP, HIGH); delay(150); digitalWrite(ledESP, LOW); delay(150);
    digitalWrite(ledESP, HIGH); delay(150); digitalWrite(ledESP, LOW); delay(150);
    
    // Espera no bloqueante (Escuchando a MQTT)
    unsigned long startWait = millis();
    while(millis() - startWait < 1400) { client.loop(); delay(10); }

  } else {
    display.display(); 
    digitalWrite(ledESP, HIGH); 
    noTone(buzzerPin);          
    
    // Espera no bloqueante de 2 segundos (Escuchando a MQTT)
    unsigned long startWait = millis();
    while(millis() - startWait < 2000) { client.loop(); delay(10); }
  }
}