# ESP32 Sensor with Blynk IoT

This project reads sensor data every **15 seconds** and sends it to the Blynk App. It also triggers alerts for high values.

## 1. Blynk Setup (Required)
You need to create a **Template** in the Blynk Cloud Console.

### Create Datastreams (Virtual Pins)
| Virtual Pin | Name | Data Type | Units |
| :--- | :--- | :--- | :--- |
| **V3** | Temperature | Double | °C |
| **V4** | Humidity | Double | % |
| **V5** | Air Quality | Double | PPM |
| **V6** | Distance | Double | cm |

### Set Up Events (For Alerts)
Go to **Events** tab in your Template and add these:
1.  **Event Code**: `temp_alert` (Name: High Temperature)
2.  **Event Code**: `air_alert` (Name: Poor Air Quality)
3.  **Event Code**: `proximity_alert` (Name: Object Too Close)

Enable **"Send to Timeline"** and **"Push Notification"** for these events to get alerts on your phone.

## 2. Code Configuration
Open `SensorRead.ino` and update the top section:

```cpp
#define BLYNK_TEMPLATE_ID "TMPLxxxxxx"      // Copy from Blynk Console
#define BLYNK_TEMPLATE_NAME "Device Name"   // Copy from Blynk Console
#define BLYNK_AUTH_TOKEN "YourAuthToken"    // Copy from Blynk Console

char ssid[] = "YourNetworkName";   // Your WiFi Name
char pass[] = "YourPassword";      // Your WiFi Password
```

## 3. Upload & Run
1.  Upload the code.
2.  Open Serial Monitor.
3.  Wait for **"Connected to Blynk"**.
4.  Check your phone app for live data!
