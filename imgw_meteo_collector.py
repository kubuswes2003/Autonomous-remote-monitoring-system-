#!/usr/bin/env python3
"""
IMGW Meteo Collector - Poznań-Ławica
Pobiera dane meteorologiczne z IMGW-PIB (polski instytut) i zapisuje do InfluxDB
Nie wymaga pandas/meteostat - działa na każdym systemie!
"""

import requests
import json
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point as InfluxPoint
from influxdb_client.client.write_api import SYNCHRONOUS
import sys

# ========== KONFIGURACJA ==========

# Poznań-Ławica
STATION_ID = "station_lawica"  # BEZ polskich znaków!
STATION_NAME = "EPPO - Lotnisko Ławica"
STATION_LAT = 52.421
STATION_LNG = 16.826

# IMGW-PIB API
# Dane synoptyczne (pomiary co godzinę) ze stacji Poznań
IMGW_API_URL = "https://danepubliczne.imgw.pl/api/data/synop"

# InfluxDB
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "my-super-secret-token"
INFLUX_ORG = "weather"
INFLUX_BUCKET = "weather_data"

# ========== FUNKCJE ==========

def get_imgw_data():
    """
    Pobiera aktualne dane ze wszystkich stacji IMGW
    Szuka stacji Poznań
    """
    try:
        print(f"📡 Pobieranie danych z IMGW-PIB...")
        print(f"   URL: {IMGW_API_URL}")
        
        response = requests.get(IMGW_API_URL, timeout=30)
        response.raise_for_status()
        
        stations = response.json()
        print(f"✅ Pobrano dane z {len(stations)} stacji")
        
        # Szukaj stacji Poznań
        poznan_station = None
        for station in stations:
            station_name = station.get('stacja', '').lower()
            if 'pozna' in station_name:  # "Poznań" lub "Poznan"
                poznan_station = station
                print(f"✅ Znaleziono stację: {station.get('stacja')}")
                break
        
        if not poznan_station:
            print("❌ Nie znaleziono stacji Poznań w danych IMGW")
            print("   Dostępne stacje:")
            for s in stations[:10]:  # Pokaż pierwsze 10
                print(f"     - {s.get('stacja')}")
            return None
        
        # Wyciągnij dane
        result = {
            'timestamp': datetime.now(),  # IMGW nie daje dokładnego timestampu w API
            'station_name': poznan_station.get('stacja'),
            'temperature': parse_float(poznan_station.get('temperatura')),
            'humidity': parse_float(poznan_station.get('wilgotnosc_wzgledna')),
            'pressure': parse_float(poznan_station.get('cisnienie')),
            'wind_speed': parse_float(poznan_station.get('predkosc_wiatru')),
            'wind_direction': parse_float(poznan_station.get('kierunek_wiatru'))
        }
        
        print(f"\n📊 Dane ze stacji {result['station_name']}:")
        print(f"   🌡️  Temperatura: {result['temperature']}°C")
        print(f"   💧 Wilgotność: {result['humidity']}%")
        print(f"   ⚖️  Ciśnienie: {result['pressure']} hPa")
        print(f"   💨 Wiatr: {result['wind_speed']} m/s @ {result['wind_direction']}°")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Błąd połączenia z IMGW API: {e}")
        return None
    except Exception as e:
        print(f"❌ Błąd przetwarzania danych: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_float(value):
    """
    Bezpiecznie konwertuje wartość na float
    IMGW czasami zwraca None lub string
    """
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def save_to_influxdb(weather_data):
    """
    Zapisuje dane do InfluxDB
    """
    try:
        # Połącz z InfluxDB
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        # Przygotuj punkt danych (taka sama struktura jak LoRa)
        point = InfluxPoint("weather_measurement") \
            .tag("station_id", STATION_ID) \
            .time(weather_data['timestamp'])
        
        # Dodaj pola (tylko jeśli nie są None)
        if weather_data['temperature'] is not None:
            point.field("temperature", float(weather_data['temperature']))
        
        if weather_data['humidity'] is not None:
            point.field("humidity", float(weather_data['humidity']))
        
        if weather_data['pressure'] is not None:
            point.field("pressure", float(weather_data['pressure']))
        
        if weather_data['wind_speed'] is not None:
            point.field("wind_speed", float(weather_data['wind_speed']))
        
        if weather_data['wind_direction'] is not None:
            point.field("wind_direction", float(weather_data['wind_direction']))  # float zamiast int!
        
        # Zapisz do InfluxDB
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        
        print(f"\n✅ Zapisano do InfluxDB:")
        print(f"   Bucket: {INFLUX_BUCKET}")
        print(f"   Station: {STATION_ID}")
        print(f"   Timestamp: {weather_data['timestamp']}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Błąd zapisu do InfluxDB: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Główna funkcja
    """
    print("=" * 70)
    print(f"🌤️  IMGW Meteo Collector - {STATION_NAME}")
    print(f"⏰ Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Pobierz dane
    weather_data = get_imgw_data()
    
    if weather_data is None:
        print("❌ Nie udało się pobrać danych")
        sys.exit(1)
    
    # Zapisz do InfluxDB
    success = save_to_influxdb(weather_data)
    
    if success:
        print("=" * 70)
        print("✅ Sukces! Dane zapisane.")
        print("=" * 70)
        sys.exit(0)
    else:
        print("=" * 70)
        print("❌ Błąd! Dane nie zostały zapisane.")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    main()
