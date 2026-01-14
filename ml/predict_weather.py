#!/usr/bin/env python3
"""
Prosty skrypt do predykcji pogody używając wytrenowanych modeli
"""

import joblib
import pandas as pd
import numpy as np
from datetime import datetime

# Wczytaj modele
print("📦 Wczytywanie modeli...")
model_temp = joblib.load('model_temperature.pkl')
model_pressure = joblib.load('model_pressure.pkl')
model_humidity = joblib.load('model_humidity.pkl')
feature_columns = joblib.load('feature_columns.pkl')

print(f"✅ Modele załadowane!")
print(f"📋 Wymagane cechy: {len(feature_columns)}")

# Przykład: Wczytaj dane testowe
print("\n📂 Wczytywanie danych testowych...")
df = pd.read_parquet('weather_ml_dataset.parquet')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Weź ostatni rekord jako przykład
test_sample = df[feature_columns].iloc[-1:].copy()

print(f"\n🔮 Wykonywanie predykcji...")
temp_pred = model_temp.predict(test_sample)[0]
pressure_pred = model_pressure.predict(test_sample)[0]
humidity_pred = model_humidity.predict(test_sample)[0]

# Rzeczywiste wartości (dla porównania)
actual_temp = df['temperature'].iloc[-1]
actual_pressure = df['pressure'].iloc[-1]
actual_humidity = df['humidity'].iloc[-1]
timestamp = df['timestamp'].iloc[-1]

print("\n" + "="*60)
print(f"📅 Data: {timestamp}")
print("="*60)
print(f"\n🌡️  TEMPERATURA:")
print(f"   Predykcja:    {temp_pred:.2f}°C")
print(f"   Rzeczywista:  {actual_temp:.2f}°C")
print(f"   Błąd:         {abs(temp_pred - actual_temp):.4f}°C")

print(f"\n🌪️  CIŚNIENIE:")
print(f"   Predykcja:    {pressure_pred:.2f} hPa")
print(f"   Rzeczywista:  {actual_pressure:.2f} hPa")
print(f"   Błąd:         {abs(pressure_pred - actual_pressure):.4f} hPa")

print(f"\n💧 WILGOTNOŚĆ:")
print(f"   Predykcja:    {humidity_pred:.2f}%")
print(f"   Rzeczywista:  {actual_humidity:.2f}%")
print(f"   Błąd:         {abs(humidity_pred - actual_humidity):.4f}%")
print("="*60)

# Funkcja do użycia w innych skryptach
def predict_weather(features_df):
    """
    Przewiduje pogodę na podstawie cech
    
    Args:
        features_df: DataFrame z cechami (musi mieć wszystkie 166 kolumn)
    
    Returns:
        dict: {'temperature': float, 'pressure': float, 'humidity': float}
    """
    return {
        'temperature': model_temp.predict(features_df)[0],
        'pressure': model_pressure.predict(features_df)[0],
        'humidity': model_humidity.predict(features_df)[0]
    }

if __name__ == "__main__":
    print("\n💡 Aby użyć w swoim kodzie:")
    print("   from predict_weather import predict_weather")
    print("   prediction = predict_weather(your_features_df)")
