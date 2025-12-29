#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Konfiguracja MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "weather/station/data"

# Konfiguracja InfluxDB
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "my-super-secret-token"
INFLUX_ORG = "weather"
INFLUX_BUCKET = "weather_data"

# Inicjalizacja klienta InfluxDB
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✓ Połączono z MQTT brokerem")
        client.subscribe(MQTT_TOPIC)
        print(f"✓ Subskrybowano: {MQTT_TOPIC}")
    else:
        print(f"✗ Błąd połączenia. Kod: {rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        
        # Stwórz punkt danych dla InfluxDB
        point = Point("weather_measurement") \
            .tag("station_id", data['station_id']) \
            .field("temperature", float(data['sensors']['temperature'])) \
            .field("humidity", float(data['sensors']['humidity'])) \
            .field("pressure", float(data['sensors']['pressure'])) \
            .field("wind_speed", float(data['sensors']['wind_speed'])) \
            .field("wind_direction", float(data['sensors']['wind_direction'])) \
            .field("battery_voltage", float(data['battery_voltage'])) \
            .field("signal_strength", float(data['signal_strength'])) \
        
        # Zapisz do InfluxDB
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        
        print(f"✓ [{datetime.now().strftime('%H:%M:%S')}] Zapisano: "
              f"Temp={data['sensors']['temperature']}°C, "
              f"Wilg={data['sensors']['humidity']}%, "
              f"Ciśn={data['sensors']['pressure']}hPa")
        
    except Exception as e:
        print(f"✗ Błąd: {e}")

def main():
    client = mqtt.Client(client_id="mqtt_to_influx")
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"🔄 Łączenie z MQTT: {MQTT_BROKER}:{MQTT_PORT}")
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("⏳ Oczekiwanie na dane...")
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n⏹ Zatrzymywanie...")
    except Exception as e:
        print(f"✗ Błąd: {e}")
    finally:
        client.disconnect()
        influx_client.close()
        print("✓ Zatrzymano")

if __name__ == "__main__":
    main()
