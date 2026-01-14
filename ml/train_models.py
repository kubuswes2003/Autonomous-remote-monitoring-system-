#!/usr/bin/env python3
"""
Train Gradient Boosting Models for Weather Prediction
Trains 3 separate models: Temperature, Pressure, Humidity
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import warnings
warnings.filterwarnings('ignore')

# Konfiguracja
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette('husl')

print("="*80)
print("🤖 Trenowanie Modeli Gradient Boosting - Predykcja Pogody")
print("="*80)

# 1. Wczytanie danych
print("\n📂 Wczytywanie datasetu...")
df = pd.read_parquet('weather_ml_dataset.parquet')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"✅ Wczytano {len(df)} rekordów, {len(df.columns)} kolumn")
print(f"📅 Zakres dat: {df['timestamp'].min()} → {df['timestamp'].max()}")

# 2. Podział Train/Test
split_date = '2025-12-01'
train_df = df[df['timestamp'] < split_date].copy()
test_df = df[df['timestamp'] >= split_date].copy()

print(f"\n📊 Podział danych:")
print(f"   Train: {len(train_df)} rekordów ({len(train_df)/len(df)*100:.1f}%)")
print(f"   Test:  {len(test_df)} rekordów ({len(test_df)/len(df)*100:.1f}%)")

# 3. Przygotowanie cech
cols_to_drop = ['timestamp', 'station_name']
target_columns = ['temperature', 'pressure', 'humidity']
feature_columns = [col for col in df.columns 
                   if col not in cols_to_drop + target_columns]

X_train = train_df[feature_columns]
X_test = test_df[feature_columns]

y_train_temp = train_df['temperature']
y_test_temp = test_df['temperature']
y_train_pressure = train_df['pressure']
y_test_pressure = test_df['pressure']
y_train_humidity = train_df['humidity']
y_test_humidity = test_df['humidity']

print(f"\n📋 Liczba cech: {len(feature_columns)}")
print(f"🎯 Targety: {target_columns}")

# Czyszczenie danych - usuwanie inf i NaN
print(f"\n🧹 Czyszczenie danych...")
print(f"   Inf w X_train: {np.isinf(X_train).sum().sum()}")
print(f"   NaN w X_train: {X_train.isna().sum().sum()}")

# Zamień inf na NaN, potem wypełnij NaN medianą
X_train = X_train.replace([np.inf, -np.inf], np.nan)
X_test = X_test.replace([np.inf, -np.inf], np.nan)

# Wypełnij NaN medianą z train set
from sklearn.impute import SimpleImputer
imputer = SimpleImputer(strategy='median')
X_train = pd.DataFrame(imputer.fit_transform(X_train), columns=feature_columns, index=X_train.index)
X_test = pd.DataFrame(imputer.transform(X_test), columns=feature_columns, index=X_test.index)

print(f"✅ Dane wyczyszczone")

# 4. Trenowanie modelu TEMPERATURA
print("\n" + "="*80)
print("🌡️  TRENOWANIE MODELU: TEMPERATURA")
print("="*80)

model_temp = GradientBoostingRegressor(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    random_state=42,
    verbose=0
)

print("🚀 Trenowanie...")
model_temp.fit(X_train, y_train_temp)

y_pred_temp_train = model_temp.predict(X_train)
y_pred_temp_test = model_temp.predict(X_test)

mae_temp_train = mean_absolute_error(y_train_temp, y_pred_temp_train)
mae_temp_test = mean_absolute_error(y_test_temp, y_pred_temp_test)
rmse_temp_test = np.sqrt(mean_squared_error(y_test_temp, y_pred_temp_test))
r2_temp_test = r2_score(y_test_temp, y_pred_temp_test)

print(f"\n✅ Model temperatury wytrenowany!")
print(f"   MAE (train): {mae_temp_train:.4f}°C")
print(f"   MAE (test):  {mae_temp_test:.4f}°C  {'✅ SUPER!' if mae_temp_test < 1.0 else '⚠️ Do poprawy'}")
print(f"   RMSE (test): {rmse_temp_test:.4f}°C")
print(f"   R² (test):   {r2_temp_test:.4f}")

# 5. Trenowanie modelu CIŚNIENIE
print("\n" + "="*80)
print("🌪️  TRENOWANIE MODELU: CIŚNIENIE")
print("="*80)

model_pressure = GradientBoostingRegressor(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    random_state=42,
    verbose=0
)

print("🚀 Trenowanie...")
model_pressure.fit(X_train, y_train_pressure)

y_pred_pressure_train = model_pressure.predict(X_train)
y_pred_pressure_test = model_pressure.predict(X_test)

mae_pressure_train = mean_absolute_error(y_train_pressure, y_pred_pressure_train)
mae_pressure_test = mean_absolute_error(y_test_pressure, y_pred_pressure_test)
rmse_pressure_test = np.sqrt(mean_squared_error(y_test_pressure, y_pred_pressure_test))
r2_pressure_test = r2_score(y_test_pressure, y_pred_pressure_test)

print(f"\n✅ Model ciśnienia wytrenowany!")
print(f"   MAE (train): {mae_pressure_train:.4f} hPa")
print(f"   MAE (test):  {mae_pressure_test:.4f} hPa")
print(f"   RMSE (test): {rmse_pressure_test:.4f} hPa")
print(f"   R² (test):   {r2_pressure_test:.4f}")

# 6. Trenowanie modelu WILGOTNOŚĆ
print("\n" + "="*80)
print("💧 TRENOWANIE MODELU: WILGOTNOŚĆ")
print("="*80)

model_humidity = GradientBoostingRegressor(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    random_state=42,
    verbose=0
)

print("🚀 Trenowanie...")
model_humidity.fit(X_train, y_train_humidity)

y_pred_humidity_train = model_humidity.predict(X_train)
y_pred_humidity_test = model_humidity.predict(X_test)

mae_humidity_train = mean_absolute_error(y_train_humidity, y_pred_humidity_train)
mae_humidity_test = mean_absolute_error(y_test_humidity, y_pred_humidity_test)
rmse_humidity_test = np.sqrt(mean_squared_error(y_test_humidity, y_pred_humidity_test))
r2_humidity_test = r2_score(y_test_humidity, y_pred_humidity_test)

print(f"\n✅ Model wilgotności wytrenowany!")
print(f"   MAE (train): {mae_humidity_train:.4f}%")
print(f"   MAE (test):  {mae_humidity_test:.4f}%")
print(f"   RMSE (test): {rmse_humidity_test:.4f}%")
print(f"   R² (test):   {r2_humidity_test:.4f}")

# 7. Podsumowanie
print("\n" + "="*80)
print("🎉 PODSUMOWANIE WYNIKÓW WSZYSTKICH MODELI")
print("="*80)

results = pd.DataFrame({
    'Model': ['Temperatura', 'Ciśnienie', 'Wilgotność'],
    'MAE Train': [mae_temp_train, mae_pressure_train, mae_humidity_train],
    'MAE Test': [mae_temp_test, mae_pressure_test, mae_humidity_test],
    'RMSE Test': [rmse_temp_test, rmse_pressure_test, rmse_humidity_test],
    'R² Test': [r2_temp_test, r2_pressure_test, r2_humidity_test],
    'Jednostka': ['°C', 'hPa', '%']
})

print(results.to_string(index=False))
print("="*80)

# 8. Wizualizacje
print("\n📊 Tworzenie wizualizacji...")

# Predykcje vs Rzeczywiste
fig, axes = plt.subplots(3, 1, figsize=(16, 12))

axes[0].plot(test_df['timestamp'], y_test_temp, label='Rzeczywiste', color='red', linewidth=2, alpha=0.7)
axes[0].plot(test_df['timestamp'], y_pred_temp_test, label='Predykcja', color='blue', linewidth=2, alpha=0.7, linestyle='--')
axes[0].set_ylabel('Temperatura (°C)', fontsize=12, fontweight='bold')
axes[0].set_title(f'Temperatura - MAE: {mae_temp_test:.4f}°C, R²: {r2_temp_test:.4f}', fontsize=14, fontweight='bold')
axes[0].legend(fontsize=11)
axes[0].grid(True, alpha=0.3)

axes[1].plot(test_df['timestamp'], y_test_pressure, label='Rzeczywiste', color='green', linewidth=2, alpha=0.7)
axes[1].plot(test_df['timestamp'], y_pred_pressure_test, label='Predykcja', color='orange', linewidth=2, alpha=0.7, linestyle='--')
axes[1].set_ylabel('Ciśnienie (hPa)', fontsize=12, fontweight='bold')
axes[1].set_title(f'Ciśnienie - MAE: {mae_pressure_test:.4f} hPa, R²: {r2_pressure_test:.4f}', fontsize=14, fontweight='bold')
axes[1].legend(fontsize=11)
axes[1].grid(True, alpha=0.3)

axes[2].plot(test_df['timestamp'], y_test_humidity, label='Rzeczywiste', color='purple', linewidth=2, alpha=0.7)
axes[2].plot(test_df['timestamp'], y_pred_humidity_test, label='Predykcja', color='cyan', linewidth=2, alpha=0.7, linestyle='--')
axes[2].set_ylabel('Wilgotność (%)', fontsize=12, fontweight='bold')
axes[2].set_xlabel('Data', fontsize=12, fontweight='bold')
axes[2].set_title(f'Wilgotność - MAE: {mae_humidity_test:.4f}%, R²: {r2_humidity_test:.4f}', fontsize=14, fontweight='bold')
axes[2].legend(fontsize=11)
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('predictions_vs_actual.png', dpi=150, bbox_inches='tight')
print("✅ Wykres zapisany: predictions_vs_actual.png")

# Błędy predykcji
errors_temp = y_test_temp.values - y_pred_temp_test
errors_pressure = y_test_pressure.values - y_pred_pressure_test
errors_humidity = y_test_humidity.values - y_pred_humidity_test

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

axes[0].hist(errors_temp, bins=50, color='red', alpha=0.7, edgecolor='black')
axes[0].axvline(0, color='black', linestyle='--', linewidth=2)
axes[0].set_xlabel('Błąd (°C)', fontsize=12)
axes[0].set_ylabel('Liczba przypadków', fontsize=12)
axes[0].set_title(f'Rozkład błędów - Temperatura\nMAE: {mae_temp_test:.4f}°C', fontsize=14, fontweight='bold')
axes[0].grid(True, alpha=0.3)

axes[1].hist(errors_pressure, bins=50, color='green', alpha=0.7, edgecolor='black')
axes[1].axvline(0, color='black', linestyle='--', linewidth=2)
axes[1].set_xlabel('Błąd (hPa)', fontsize=12)
axes[1].set_ylabel('Liczba przypadków', fontsize=12)
axes[1].set_title(f'Rozkład błędów - Ciśnienie\nMAE: {mae_pressure_test:.4f} hPa', fontsize=14, fontweight='bold')
axes[1].grid(True, alpha=0.3)

axes[2].hist(errors_humidity, bins=50, color='purple', alpha=0.7, edgecolor='black')
axes[2].axvline(0, color='black', linestyle='--', linewidth=2)
axes[2].set_xlabel('Błąd (%)', fontsize=12)
axes[2].set_ylabel('Liczba przypadków', fontsize=12)
axes[2].set_title(f'Rozkład błędów - Wilgotność\nMAE: {mae_humidity_test:.4f}%', fontsize=14, fontweight='bold')
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('prediction_errors.png', dpi=150, bbox_inches='tight')
print("✅ Wykres zapisany: prediction_errors.png")

# Feature importance
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': model_temp.feature_importances_
}).sort_values('importance', ascending=False)

top_features = feature_importance.head(20)

plt.figure(figsize=(12, 8))
plt.barh(range(len(top_features)), top_features['importance'], color='steelblue')
plt.yticks(range(len(top_features)), top_features['feature'])
plt.xlabel('Importance', fontsize=12, fontweight='bold')
plt.title('Top 20 Najważniejszych Cech - Model Temperatury', fontsize=14, fontweight='bold')
plt.gca().invert_yaxis()
plt.grid(True, alpha=0.3, axis='x')
plt.tight_layout()
plt.savefig('feature_importance.png', dpi=150, bbox_inches='tight')
print("✅ Wykres zapisany: feature_importance.png")

# 9. Zapis modeli
print("\n💾 Zapisywanie modeli...")
joblib.dump(model_temp, 'model_temperature.pkl')
print("✅ Model temperatury zapisany: model_temperature.pkl")

joblib.dump(model_pressure, 'model_pressure.pkl')
print("✅ Model ciśnienia zapisany: model_pressure.pkl")

joblib.dump(model_humidity, 'model_humidity.pkl')
print("✅ Model wilgotności zapisany: model_humidity.pkl")

joblib.dump(feature_columns, 'feature_columns.pkl')
print("✅ Lista cech zapisana: feature_columns.pkl")

# 10. Podsumowanie końcowe
print("\n" + "="*80)
print("🎉 TRENOWANIE ZAKOŃCZONE SUKCESEM!")
print("="*80)
print(f"\n📊 Wytrenowano 3 modele Gradient Boosting:")
print(f"   1. Temperatura - MAE: {mae_temp_test:.4f}°C, R²: {r2_temp_test:.4f}")
print(f"   2. Ciśnienie   - MAE: {mae_pressure_test:.4f} hPa, R²: {r2_pressure_test:.4f}")
print(f"   3. Wilgotność  - MAE: {mae_humidity_test:.4f}%, R²: {r2_humidity_test:.4f}")
print(f"\n💾 Zapisane pliki:")
print(f"   • model_temperature.pkl")
print(f"   • model_pressure.pkl")
print(f"   • model_humidity.pkl")
print(f"   • feature_columns.pkl")
print(f"   • predictions_vs_actual.png")
print(f"   • prediction_errors.png")
print(f"   • feature_importance.png")
print("="*80)
