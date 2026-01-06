#!/usr/bin/env python3
"""
LoRa Receiver Bridge
Odbiera dane z LoRa (10.58.40.99) i przekazuje do lokalnego MQTT (localhost)
w formacie kompatybilnym z emulatorami.
"""

import paho.mqtt.client as mqtt
import json
import base64
from datetime import datetime

# ========== KONFIGURACJA ZDALNEGO BROKERA (LoRa) ==========
REMOTE_MQTT_BROKER = "10.58.40.99"
REMOTE_MQTT_PORT = 1883
REMOTE_MQTT_USERNAME = "dabrowskiego536"
REMOTE_MQTT_PASSWORD = "Dabrowskiego196105070320032004"
REMOTE_MQTT_TOPIC = "application/bcb75d00-e41b-4f24-9891-2d26072205e2/device/ac1f09fffe19fc8a/event/up"

# ========== KONFIGURACJA LOKALNEGO BROKERA ==========
LOCAL_MQTT_BROKER = "localhost"
LOCAL_MQTT_PORT = 1883
LOCAL_MQTT_TOPIC = "weather/station/data"

# ========== DEKODERY ==========

def decode_packet_0x01(payload_hex):
    """Power Module - napięcia cel i temperatury"""
    if len(payload_hex) < 14 or payload_hex[0:2] != "01":
        return None
    
    cell1 = int(payload_hex[2:6], 16) / 1000.0
    cell2 = int(payload_hex[6:10], 16) / 1000.0
    cell3 = int(payload_hex[10:14], 16) / 1000.0
    
    result = {
        "packet_type": "0x01",
        "cell1_voltage": cell1,
        "cell2_voltage": cell2,
        "cell3_voltage": cell3,
        "battery_voltage": (cell1 + cell2 + cell3)
    }
    
    if len(payload_hex) >= 22:
        result["temp_bms"] = int(payload_hex[14:18], 16) / 100.0
        result["temp_charger"] = int(payload_hex[18:22], 16) / 100.0
    
    return result

def decode_packet_0x02(payload_hex):
    """Weather Data - temperatura, wilgotność"""
    if len(payload_hex) < 14 or payload_hex[0:2] != "02":
        return None
    
    return {
        "packet_type": "0x02",
        "temperature": int(payload_hex[2:6], 16) / 100.0,
        "humidity": int(payload_hex[6:10], 16) / 100.0,
        "temp_bmp390": int(payload_hex[10:14], 16) / 100.0
    }

def decode_packet_0x12(payload_hex):
    """Light + Pressure"""
    if len(payload_hex) < 14 or payload_hex[0:2] != "12":
        return None
    
    result = {
        "packet_type": "0x12",
        "lux": int(payload_hex[2:10], 16),
        "white_ratio": int(payload_hex[10:14], 16) / 100.0
    }
    
    if len(payload_hex) >= 18:
        result["pressure"] = int(payload_hex[14:18], 16) / 100.0
    
    return result

def decode_sudden_packet(payload_hex):
    """Sudden packets (0x22, 0x32, etc.)"""
    if len(payload_hex) < 6:
        return None
    
    packet_type = payload_hex[0:2]
    
    sudden_map = {
        "22": ("humidity", 100.0), "32": ("temperature", 100.0),
        "42": ("temp_bmp390", 100.0), "52": ("lux", 1.0),
        "62": ("white_ratio", 100.0), "72": ("pressure", 100.0)
    }
    
    if packet_type not in sudden_map:
        return None
    
    field, divisor = sudden_map[packet_type]
    value = int(payload_hex[2:6], 16) / divisor
    
    return {
        "packet_type": f"0x{packet_type}",
        "sudden_field": field,
        "sudden_value": value
    }

# ========== KLIENTY MQTT ==========

local_client = mqtt.Client(client_id="lora_bridge_local")
message_count = 0

def on_local_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Połączono z lokalnym MQTT ({LOCAL_MQTT_BROKER})")
    else:
        print(f"❌ Błąd lokalnego MQTT: {rc}")

def on_remote_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Połączono z LoRa MQTT ({REMOTE_MQTT_BROKER})")
        print(f"📡 Nasłuchiwanie: {REMOTE_MQTT_TOPIC}")
        print("=" * 70)
        client.subscribe(REMOTE_MQTT_TOPIC)
    else:
        print(f"❌ Błąd LoRa MQTT: {rc}")

def on_remote_message(client, userdata, msg):
    global message_count
    message_count += 1
    
    try:
        data = json.loads(msg.payload.decode())
        
        if 'data' not in data:
            return
        
        payload_hex = base64.b64decode(data['data']).hex().upper()
        
        # Device info
        device_info = data.get('deviceInfo', {})
        dev_eui = device_info.get('devEui', 'UNKNOWN')
        device_name = device_info.get('deviceName', 'LoRa Station')
        
        # Station ID: "Station " + last 6 chars of DevEUI
        station_id = f"Station {dev_eui[-6:].upper()}"
        
        # Location
        lat, lng = 52.4064, 16.9252
        if 'rxInfo' in data and len(data['rxInfo']) > 0:
            rx_info = data['rxInfo'][0]
            if 'location' in rx_info:
                lat = rx_info['location'].get('latitude', lat)
                lng = rx_info['location'].get('longitude', lng)
        
        # Signal
        rssi = -100
        snr = 0
        if 'rxInfo' in data and len(data['rxInfo']) > 0:
            rssi = data['rxInfo'][0].get('rssi', -100)
            snr = data['rxInfo'][0].get('snr', 0)
        
        # Dekoduj
        decoded = None
        for decoder in [decode_packet_0x01, decode_packet_0x02, decode_packet_0x12, decode_sudden_packet]:
            decoded = decoder(payload_hex)
            if decoded:
                break
        
        if not decoded:
            print(f"⚠️  [{message_count}] Nieznany packet: 0x{payload_hex[0:2]}")
            return
        
        # Przygotuj JSON w formacie emulatorów
        output = {
            "station_id": station_id,
            "timestamp": datetime.now().isoformat(),
            "sensors": {
                "temperature": 20.0,
                "humidity": 50.0,
                "pressure": 1013.25,
                "wind_speed": 0.0,
                "wind_direction": 0.0
            },
            "battery_voltage": 4.0,
            "signal_strength": rssi,
            "lat": lat,
            "lng": lng,
            "location": device_name,
            "is_lora": True,
            "lora_metadata": {
                "dev_eui": dev_eui,
                "device_name": device_name,
                "snr": snr,
                "packet_type": decoded['packet_type']
            }
        }
        
        # Wypełnij danymi z pakietu
        if decoded['packet_type'] == '0x01':
            output['battery_voltage'] = decoded.get('battery_voltage', 4.0)
            output['lora_metadata']['cell1_voltage'] = decoded['cell1_voltage']
            output['lora_metadata']['cell2_voltage'] = decoded['cell2_voltage']
            output['lora_metadata']['cell3_voltage'] = decoded['cell3_voltage']
            if 'temp_bms' in decoded:
                output['lora_metadata']['temp_bms'] = decoded['temp_bms']
            if 'temp_charger' in decoded:
                output['lora_metadata']['temp_charger'] = decoded['temp_charger']
        
        elif decoded['packet_type'] == '0x02':
            output['sensors']['temperature'] = decoded['temperature']
            output['sensors']['humidity'] = decoded['humidity']
            output['lora_metadata']['temp_bmp390'] = decoded['temp_bmp390']
        
        elif decoded['packet_type'] == '0x12':
            output['lora_metadata']['lux'] = decoded['lux']
            output['lora_metadata']['white_ratio'] = decoded['white_ratio']
            if 'pressure' in decoded:
                output['sensors']['pressure'] = decoded['pressure']
        
        elif decoded['packet_type'].startswith('0x'):
            field = decoded['sudden_field']
            value = decoded['sudden_value']
            if field in ['temperature', 'humidity', 'pressure']:
                output['sensors'][field] = value
            output['lora_metadata']['sudden_reading'] = {
                'field': field,
                'value': value
            }
        
        # Wyślij do lokalnego MQTT
        result = local_client.publish(LOCAL_MQTT_TOPIC, json.dumps(output))
        
        if result.rc == 0:
            print(f"📤 [{message_count}] {decoded['packet_type']} → {station_id}")
        else:
            print(f"❌ [{message_count}] Błąd wysyłania: {result.rc}")
        
    except Exception as e:
        print(f"❌ Błąd przetwarzania: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🚀 LoRa → MQTT Bridge")
    print(f"📡 LoRa: {REMOTE_MQTT_BROKER}:{REMOTE_MQTT_PORT}")
    print(f"💾 Local: {LOCAL_MQTT_BROKER}:{LOCAL_MQTT_PORT}")
    print("\nNaciśnij Ctrl+C aby zatrzymać\n")
    
    # Lokalny klient
    local_client.on_connect = on_local_connect
    try:
        local_client.connect(LOCAL_MQTT_BROKER, LOCAL_MQTT_PORT, 60)
        local_client.loop_start()
    except Exception as e:
        print(f"❌ Błąd lokalnego MQTT: {e}")
        return
    
    # Zdalny klient
    remote_client = mqtt.Client(client_id="lora_bridge_remote")
    remote_client.username_pw_set(REMOTE_MQTT_USERNAME, REMOTE_MQTT_PASSWORD)
    remote_client.on_connect = on_remote_connect
    remote_client.on_message = on_remote_message
    
    try:
        remote_client.connect(REMOTE_MQTT_BROKER, REMOTE_MQTT_PORT, 60)
        remote_client.loop_forever()
    except KeyboardInterrupt:
        print("\n⛔ Zatrzymywanie...")
    except Exception as e:
        print(f"\n❌ Błąd: {e}")
    finally:
        remote_client.disconnect()
        local_client.loop_stop()
        local_client.disconnect()
        print("👋 Zamknięto")

if __name__ == "__main__":
    main()
