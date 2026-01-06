#!/usr/bin/env python3
"""
Odbiera dane LoRa od kolegi, dekoduje i zapisuje do InfluxDB
"""

import paho.mqtt.client as mqtt
import json
import base64
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ========== MQTT ==========
MQTT_BROKER = "10.58.40.99"
MQTT_PORT = 1883
MQTT_USERNAME = "dabrowskiego536"
MQTT_PASSWORD = "Dabrowskiego196105070320032004"
MQTT_TOPIC = "application/bcb75d00-e41b-4f24-9891-2d26072205e2/device/ac1f09fffe19fc8a/event/up"

# ========== INFLUXDB ==========
INFLUX_URL = "http://10.58.40.97:8086"
INFLUX_TOKEN = "my-super-secret-token"
INFLUX_ORG = "weather"
INFLUX_BUCKET = "weather_data"

# Inicjalizacja InfluxDB
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

def decode_packet_0x02(payload_hex):
    """
    Dekoduje packet 0x02: SHT45 temp, humidity, BMP390 temp
    Format: 02 0A12 11AB 09A1
    """
    if len(payload_hex) < 14:
        return None
    
    packet_type = payload_hex[0:2]
    
    if packet_type != "02":
        return None
    
    # Wyciągnij wartości (2 bajty = 4 znaki hex)
    temp_sht45_hex = payload_hex[2:6]
    humidity_hex = payload_hex[6:10]
    temp_bmp390_hex = payload_hex[10:14]
    
    # Konwertuj hex na int i podziel przez 100
    temp_sht45 = int(temp_sht45_hex, 16) / 100.0
    humidity = int(humidity_hex, 16) / 100.0
    temp_bmp390 = int(temp_bmp390_hex, 16) / 100.0
    
    return {
        "temperature": temp_sht45,
        "humidity": humidity,
        "temp_bmp390": temp_bmp390
    }

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Połączono z MQTT!")
        print(f"📡 Nasłuchiwanie: {MQTT_TOPIC}")
        print("="*70)
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"❌ Błąd połączenia: {rc}")

def on_message(client, userdata, msg):
    try:
        # Parsuj JSON z ChirpStack
        data = json.loads(msg.payload.decode())
        
        # Wyciągnij payload
        if 'data' not in data:
            return
        
        payload_b64 = data['data']
        payload_bytes = base64.b64decode(payload_b64)
        payload_hex = payload_bytes.hex().upper()
        
        print(f"\n📨 [{datetime.now().strftime('%H:%M:%S')}]")
        print(f"📦 Payload HEX: {payload_hex}")
        
        # Dekoduj packet 0x02
        decoded = decode_packet_0x02(payload_hex)
        
        if decoded:
            print(f"✅ Zdekodowano:")
            print(f"   🌡️  Temperatura: {decoded['temperature']:.2f}°C")
            print(f"   💧 Wilgotność:   {decoded['humidity']:.2f}%")
            print(f"   🌡️  Temp BMP390:  {decoded['temp_bmp390']:.2f}°C")

            # Wyciągnij metadane LoRa
            rssi = data['rxInfo'][0]['rssi']
            snr = data['rxInfo'][0]['snr']
            
            # Zapisz do InfluxDB
            point = Point("weather_measurement") \
                .tag("station_id", "LORA_STATION") \
                .field("temperature", decoded['temperature']) \
                .field("humidity", decoded['humidity']) \
                .field("pressure", 1013.25) \
                .field("wind_speed", 0.0) \
                .field("wind_direction", 0) \
                .field("rssi", float(rssi)) \
                .field("snr", float(snr)) \
                .field("battery_voltage", 4.2) \
                .field("signal_strength", float(rssi)) \
                .time(datetime.utcnow())
            
            print(f"📶 RSSI: {rssi} dBm, SNR: {snr} dB")
            
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            print("💾 Zapisano do InfluxDB (station_id: LORA_STATION)")
        else:
            print(f"⚠️  Nieznany typ packetu: 0x{payload_hex[0:2]}")
        
        print("-"*70)
        
    except Exception as e:
        print(f"❌ Błąd: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🚀 LoRa Receiver - Odbieranie danych od kolegi")
    print(f"📡 Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"💾 InfluxDB: {INFLUX_URL}")
    print("\nNaciśnij Ctrl+C aby zatrzymać\n")
    
    client = mqtt.Client(client_id="lora_receiver")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n⛔ Zatrzymywanie...")
    except Exception as e:
        print(f"\n❌ Błąd: {e}")
    finally:
        client.disconnect()
        influx_client.close()
        print("👋 Zamknięto")

if __name__ == "__main__":
    main()
