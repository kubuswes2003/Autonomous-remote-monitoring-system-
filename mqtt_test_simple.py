import paho.mqtt.client as mqtt
from datetime import datetime

MQTT_BROKER = "10.58.40.99"
MQTT_PORT = 1883
MQTT_USERNAME = "dabrowskiego536"
MQTT_PASSWORD = "Dabrowskiego196105070320032004"
MQTT_TOPIC = "application/bcb75d00-e41b-4f24-9891-2d26072205e2/device/ac1f09fffe19fc8a/event/up"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ POŁĄCZONO!")
        client.subscribe(MQTT_TOPIC)
        print(f"📡 Nasłuchiwanie na: {MQTT_TOPIC}")
        print("\n" + "="*70)
        print("⏳ CZEKAM NA DANE...")
        print("="*70 + "\n")
    else:
        print(f"❌ Błąd połączenia: {rc}")

def on_message(client, userdata, msg):
    print("\n" + "🎉"*20)
    print(f"📨 DANE PRZYSZŁY! [{datetime.now().strftime('%H:%M:%S')}]")
    print("🎉"*20)
    print(f"\n📍 Topic: {msg.topic}")
    print(f"📦 Długość: {len(msg.payload)} bytes")
    print(f"\n💾 RAW PAYLOAD:")
    print(msg.payload)
    print(f"\n📝 JAKO TEKST:")
    try:
        print(msg.payload.decode('utf-8'))
    except:
        print("(nie da się zdekodować jako tekst)")
    print("\n" + "="*70 + "\n")

def main():
    print("🔍 PROSTY TEST MQTT - Tylko wyświetlanie")
    print(f"🌐 Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"👤 User: {MQTT_USERNAME}")
    print("\nNaciśnij Ctrl+C aby zatrzymać\n")
    
    client = mqtt.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n⛔ STOP")
    except Exception as e:
        print(f"\n❌ BŁĄD: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
