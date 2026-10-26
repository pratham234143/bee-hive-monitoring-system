#define BLYNK_TEMPLATE_ID "TMPL3LXU8Vb3w"
#define BLYNK_TEMPLATE_NAME "BeeHive"
#define BLYNK_AUTH_TOKEN                                                       \
  "NVqVU82XKWW52hAzFg1x_r2V_2MWM7cS" // REPLACE with your Auth Token

#define BLYNK_PRINT Serial

#include "DHT.h"
#include <BlynkSimpleEsp32.h>
#include <WiFi.h>

// --- WiFi Credentials ---
char ssid[] = "iqooo z9 5g";   // REPLACE with your WiFi SSID
char pass[] = "Pinealien844@"; // REPLACE with your WiFi Password

// --- Pin Definitions ---
#define DHTPIN 4      // DHT11 Data Pin
#define DHTTYPE DHT11 // DHT 11 Sensor Type
#define MQ135_PIN 34  // Analog Pin for MQ135
#define TRIG_PIN 5    // HC-SR04 Trigger Pin
#define ECHO_PIN 18   // HC-SR04 Echo Pin

// --- Thresholds for Alerts ---
const float TEMP_THRESHOLD = 35.0; // Degrees Celsius
const int PPM_THRESHOLD = 1000;    // PPM (Air Quality)
const int DISTANCE_THRESHOLD = 10; // cm (Too close)

DHT dht(DHTPIN, DHTTYPE);
BlynkTimer timer;

// --- Sensor Reading Function ---
void sendSensorData() {
  // 1. Read DHT11
  float h = dht.readHumidity();
  float t = dht.readTemperature(); // Celsius

  if (isnan(h) || isnan(t)) {
    Serial.println(F("Failed to read from DHT sensor!"));
  } else {
    // Send to Blynk
    Blynk.virtualWrite(V3, t); // V0 for Temperature
    Blynk.virtualWrite(V4, h); // V1 for Humidity

    // Check Thresholds
    if (t > TEMP_THRESHOLD) {
      Blynk.logEvent("temp_alert",
                     String("High Temperature Detected: ") + t + "C");
    }
  }

  // 2. Read MQ135 (3.3V Logic)
  int mq135Value = analogRead(MQ135_PIN);
  float mq135Voltage = mq135Value * (3.3 / 4095.0);
  float Rs = 0;
  if (mq135Voltage > 0) {
    Rs = (3.3 / mq135Voltage - 1) * 10;
  }
  float R0 = 10.0;
  float ratio = Rs / R0;
  float ppm = 116.602 * pow(ratio, -2.769);

  // Send to Blynk
  Blynk.virtualWrite(V5, ppm); // V2 for Air Quality (PPM)

  // Check Thresholds
  if (ppm > PPM_THRESHOLD) {
    Blynk.logEvent("air_alert", String("Poor Air Quality! PPM: ") + ppm);
  }

  // 3. Read HC-SR04
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH);
  float distanceCm = duration * 0.034 / 2;

  // Send to Blynk
  Blynk.virtualWrite(V6, distanceCm); // V3 for Distance

  // Check Thresholds
  if (distanceCm > 0 && distanceCm < DISTANCE_THRESHOLD) {
    Blynk.logEvent("proximity_alert",
                   String("Object too close: ") + distanceCm + "cm");
  }

  // Debug Print
  Serial.print(F("T: "));
  Serial.print(t);
  Serial.print(F("C | H: "));
  Serial.print(h);
  Serial.print(F("% | PPM: "));
  Serial.print(ppm);
  Serial.print(F(" | Dist: "));
  Serial.println(distanceCm);
}

void setup() {
  Serial.begin(115200);

  // Initialize Sensors
  dht.begin();
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(MQ135_PIN, INPUT);

  // Initialize Blynk
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);

  // Setup a function to be called every 15000 ms (15 seconds)
  timer.setInterval(15000L, sendSensorData);
}

void loop() {
  Blynk.run();
  timer.run();
}
