#!/usr/bin/env python3
"""
Multi-Step Weather Forecasting - Rolling Window Prediction
Przewiduje pogodę na wiele godzin do przodu (1-48h)
"""

import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("🔮 Multi-Step Weather Forecasting - Rolling Window")
print("="*80)

# Wczytaj modele
print("\n📦 Wczytywanie modeli...")
model_temp = joblib.load('model_temperature.pkl')
model_pressure = joblib.load('model_pressure.pkl')
model_humidity = joblib.load('model_humidity.pkl')
feature_columns = joblib.load('feature_columns.pkl')
print("✅ Modele załadowane!")

def prepare_features(df_history):
    """
    Przygotowuje cechy z historii pomiarów
    
    Args:
        df_history: DataFrame z kolumnami [timestamp, temperature, pressure, humidity, wind_speed, wind_direction]
                    Musi zawierać co najmniej 24 rekordy
    
    Returns:
        DataFrame z 166 cechami
    """
    df = df_history.copy()
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Weź ostatni rekord jako bazę
    latest = df.iloc[-1:].copy()
    
    # 1. Cechy czasowe
    latest['hour'] = latest['timestamp'].dt.hour
    latest['day'] = latest['timestamp'].dt.day
    latest['month'] = latest['timestamp'].dt.month
    latest['day_of_week'] = latest['timestamp'].dt.dayofweek
    latest['day_of_year'] = latest['timestamp'].dt.dayofyear
    latest['week_of_year'] = latest['timestamp'].dt.isocalendar().week
    latest['hour_sin'] = np.sin(2 * np.pi * latest['hour'] / 24)
    latest['hour_cos'] = np.cos(2 * np.pi * latest['hour'] / 24)
    latest['month_sin'] = np.sin(2 * np.pi * latest['month'] / 12)
    latest['month_cos'] = np.cos(2 * np.pi * latest['month'] / 12)
    latest['is_weekend'] = (latest['day_of_week'] >= 5).astype(int)
    
    # 2. Lagi
    lag_columns = ['temperature', 'pressure', 'humidity', 'wind_speed', 'wind_direction']
    lag_periods = [1, 3, 6, 12, 24]
    
    for col in lag_columns:
        for lag in lag_periods:
            if len(df) > lag:
                latest[f'{col}_lag_{lag}h'] = df[col].iloc[-lag-1]
            else:
                latest[f'{col}_lag_{lag}h'] = df[col].iloc[0]  # Fallback
    
    # 3. Rolling statistics
    rolling_windows = [3, 6, 12, 24]
    for col in lag_columns:
        for window in rolling_windows:
            window_size = min(window, len(df))
            latest[f'{col}_rolling_mean_{window}h'] = df[col].iloc[-window_size:].mean()
            latest[f'{col}_rolling_std_{window}h'] = df[col].iloc[-window_size:].std()
            latest[f'{col}_rolling_min_{window}h'] = df[col].iloc[-window_size:].min()
            latest[f'{col}_rolling_max_{window}h'] = df[col].iloc[-window_size:].max()
    
    # 4. Trendy (deltas)
    delta_periods = [1, 3, 6, 12, 24]
    for col in lag_columns:
        for period in delta_periods:
            if len(df) > period:
                latest[f'{col}_delta_{period}h'] = df[col].iloc[-1] - df[col].iloc[-period-1]
                if col != 'wind_direction':
                    prev_val = df[col].iloc[-period-1]
                    if prev_val != 0:
                        latest[f'{col}_pct_change_{period}h'] = ((df[col].iloc[-1] - prev_val) / prev_val * 100)
                    else:
                        latest[f'{col}_pct_change_{period}h'] = 0
            else:
                latest[f'{col}_delta_{period}h'] = 0
                if col != 'wind_direction':
                    latest[f'{col}_pct_change_{period}h'] = 0
    
    # 5. Dodatkowe cechy meteorologiczne
    if 'temperature' in latest.columns and 'humidity' in latest.columns:
        temp = latest['temperature'].iloc[0]
        hum = latest['humidity'].iloc[0]
        
        a = 17.27
        b = 237.7
        alpha = ((a * temp) / (b + temp)) + np.log(hum / 100.0)
        latest['dew_point'] = (b * alpha) / (a - alpha)
        latest['heat_index'] = temp + 0.5555 * (6.11 * np.exp(5417.7530 * ((1/273.16) - (1/(273.15 + temp)))) * (hum/100) - 10)
        latest['temp_dewpoint_diff'] = temp - latest['dew_point']
    
    # Wypełnij brakujące cechy zerami
    for col in feature_columns:
        if col not in latest.columns:
            latest[col] = 0
    
    # Zamień inf/NaN na 0
    latest = latest.replace([np.inf, -np.inf], 0)
    latest = latest.fillna(0)
    
    return latest[feature_columns]


def predict_multi_step(df_history, hours_ahead=24):
    """
    Przewiduje pogodę na wiele godzin do przodu używając rolling window
    
    Args:
        df_history: DataFrame z historią ostatnich 24h
        hours_ahead: Ile godzin do przodu przewidzieć (1-48)
    
    Returns:
        DataFrame z predykcjami [timestamp, temperature, pressure, humidity, wind_speed, wind_direction]
    """
    # Kopia historii
    history = df_history.copy()
    history = history.sort_values('timestamp').reset_index(drop=True)
    
    # Lista predykcji
    predictions = []
    
    print(f"\n🔮 Przewidywanie na {hours_ahead} godzin do przodu...")
    print(f"📅 Start: {history['timestamp'].iloc[-1]}")
    
    for step in range(1, hours_ahead + 1):
        # 1. Przygotuj cechy z aktualnej historii
        features = prepare_features(history)
        
        # 2. Przewidź następną godzinę
        temp_pred = model_temp.predict(features)[0]
        pressure_pred = model_pressure.predict(features)[0]
        humidity_pred = model_humidity.predict(features)[0]
        
        # 3. Timestamp dla predykcji
        next_timestamp = history['timestamp'].iloc[-1] + timedelta(hours=1)
        
        # 4. Utwórz nowy rekord (predykcja staje się "faktem")
        new_record = pd.DataFrame({
            'timestamp': [next_timestamp],
            'temperature': [temp_pred],
            'pressure': [pressure_pred],
            'humidity': [humidity_pred],
            'wind_speed': [history['wind_speed'].iloc[-1]],  # Zakładamy stałą prędkość wiatru
            'wind_direction': [history['wind_direction'].iloc[-1]]  # Zakładamy stały kierunek
        })
        
        # 5. Dodaj do historii (rolling window)
        history = pd.concat([history, new_record], ignore_index=True)
        
        # 6. Zapisz predykcję
        predictions.append({
            'step': step,
            'timestamp': next_timestamp,
            'temperature': temp_pred,
            'pressure': pressure_pred,
            'humidity': humidity_pred,
            'wind_speed': new_record['wind_speed'].iloc[0],
            'wind_direction': new_record['wind_direction'].iloc[0]
        })
        
        # Progress
        if step % 6 == 0 or step == hours_ahead:
            print(f"   ⏳ Krok {step}/{hours_ahead}: {next_timestamp.strftime('%Y-%m-%d %H:%M')} - T={temp_pred:.2f}°C")
    
    print(f"✅ Predykcja zakończona!")
    
    return pd.DataFrame(predictions)


# DEMO: Wczytaj dane historyczne i przewiduj
if __name__ == "__main__":
    print("\n📂 Wczytywanie danych historycznych...")
    
    # Wczytaj dataset
    df = pd.read_parquet('weather_ml_dataset.parquet')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Weź ostatnie 48h jako historię (więcej = lepsze cechy)
    history = df[['timestamp', 'temperature', 'pressure', 'humidity', 'wind_speed', 'wind_direction']].tail(48).copy()
    
    print(f"✅ Historia: {len(history)} rekordów")
    print(f"   Od: {history['timestamp'].iloc[0]}")
    print(f"   Do: {history['timestamp'].iloc[-1]}")
    
    # Przewiduj 24h do przodu
    predictions = predict_multi_step(history, hours_ahead=24)
    
    # Wyświetl wyniki
    print("\n" + "="*80)
    print("📊 WYNIKI PREDYKCJI (pierwsze 12h)")
    print("="*80)
    print(predictions[['timestamp', 'temperature', 'pressure', 'humidity']].head(12).to_string(index=False))
    
    # Zapisz do pliku
    output_file = 'weather_forecast_24h.csv'
    predictions.to_csv(output_file, index=False)
    print(f"\n💾 Pełna predykcja zapisana do: {output_file}")
    
    # Porównanie z rzeczywistością (jeśli dostępne)
    if len(df) > len(history):
        print("\n" + "="*80)
        print("🎯 PORÓWNANIE Z RZECZYWISTOŚCIĄ (pierwsze 6h)")
        print("="*80)
        
        actual = df[['timestamp', 'temperature', 'pressure', 'humidity']].iloc[len(history):len(history)+6].reset_index(drop=True)
        pred_subset = predictions[['timestamp', 'temperature', 'pressure', 'humidity']].head(6).reset_index(drop=True)
        
        comparison = pd.DataFrame({
            'Timestamp': actual['timestamp'],
            'Temp_Actual': actual['temperature'],
            'Temp_Pred': pred_subset['temperature'],
            'Temp_Error': abs(actual['temperature'] - pred_subset['temperature']),
            'Press_Actual': actual['pressure'],
            'Press_Pred': pred_subset['pressure'],
            'Press_Error': abs(actual['pressure'] - pred_subset['pressure'])
        })
        
        print(comparison.to_string(index=False))
        
        print(f"\n📈 Średnie błędy (pierwsze 6h):")
        print(f"   Temperatura: {comparison['Temp_Error'].mean():.4f}°C")
        print(f"   Ciśnienie: {comparison['Press_Error'].mean():.4f} hPa")
    
    print("\n" + "="*80)
    print("💡 Jak użyć w swoim kodzie:")
    print("="*80)
    print("""
from predict_multi_step import predict_multi_step

# Przygotuj historię (ostatnie 24-48h)
history_df = pd.DataFrame({
    'timestamp': [...],
    'temperature': [...],
    'pressure': [...],
    'humidity': [...],
    'wind_speed': [...],
    'wind_direction': [...]
})

# Przewiduj 24h do przodu
forecast = predict_multi_step(history_df, hours_ahead=24)

# Użyj predykcji
for _, row in forecast.iterrows():
    print(f"{row['timestamp']}: {row['temperature']:.1f}°C")
    """)
    print("="*80)
