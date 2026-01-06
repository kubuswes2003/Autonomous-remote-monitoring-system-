// Konfiguracja stacji - ZMIENIONE: const → let
let stations = [
    {
        id: "WEATHER_STATION_01",
        name: "Station 01 - Strzeszyn",
        lat: 52.443196,
        lng: 16.879174,
        location: "Strzeszyn, Poznań",
        type: "emulator"
    },
    {
        id: "WEATHER_STATION_02",
        name: "Station 02 - Winogrady",
        lat: 52.433196,
        lng: 16.889174,
        location: "Winogrady, Poznań",
        type: "emulator"
    },
    {
        id: "WEATHER_STATION_03",
        name: "Station 03 - Rataje",
        lat: 52.423196,
        lng: 16.949174,
        location: "Rataje, Poznań",
        type: "emulator"
    }
];

// Konfiguracja InfluxDB
const INFLUX_CONFIG = {
    url: 'http://10.58.40.97:8086',
    token: 'my-super-secret-token',
    org: 'weather',
    bucket: 'weather_data'
};

// Stan aplikacji
let map = null;
let markers = {};
let currentStation = null;
let mqttClient = null;
let currentData = {};
let charts = {
    temp: null,
    humidity: null,
    pressure: null,
    wind: null
};

// Inicjalizacja
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initMQTT();
    initTabs();
    initStationSelector();
    initDropdowns();
});

// ========== MAPA ==========
function initMap() {
    console.log('🗺️ Inicjalizacja mapy...');

    map = L.map('map').setView([52.4064, 16.9252], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    markers = {};

    stations.forEach((station, index) => {
        console.log(`  ${index + 1}. ${station.id} → [${station.lat}, ${station.lng}]`);

        const marker = L.marker([station.lat, station.lng])
            .bindPopup(`
                <div style="min-width: 200px;">
                    <h3>${station.name}</h3>
                    <p><strong>ID:</strong> ${station.id}</p>
                    <p><strong>Lokalizacja:</strong> ${station.location}</p>
                    <button onclick="selectStation('${station.id}')" style="
                        padding: 8px 16px;
                        background: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        margin-top: 8px;
                    ">Wybierz stację</button>
                </div>
            `)
            .addTo(map);

        markers[station.id] = marker;
    });

    console.log(`✅ Dodano ${Object.keys(markers).length} markerów na mapę`);

    setTimeout(() => {
        const bounds = L.latLngBounds(
            stations.map(s => [s.lat, s.lng])
        );
        map.fitBounds(bounds, { padding: [50, 50] });
        console.log('🎯 Wycentrowano mapę na wszystkie stacje');
    }, 500);
}

// ========== MQTT ==========
function initMQTT() {
    mqttClient = mqtt.connect('ws://10.58.40.97:9001');

    const statusDot = document.getElementById('mqtt-status');
    const statusText = document.getElementById('mqtt-status-text');

    mqttClient.on('connect', () => {
        console.log('✓ Połączono z MQTT');
        statusDot.classList.remove('disconnected');
        statusText.textContent = 'Połączono';

        mqttClient.subscribe('weather/station/data');
    });

    mqttClient.on('error', (error) => {
        console.error('✗ Błąd MQTT:', error);
        statusDot.classList.add('disconnected');
        statusText.textContent = 'Rozłączono';
    });

    mqttClient.on('message', (topic, message) => {
        try {
            const data = JSON.parse(message.toString());
            handleDataUpdate(data);
        } catch (e) {
            console.error('Błąd parsowania:', e);
        }
    });
}

// ========== OBSŁUGA DANYCH - ZMIENIONE ==========
function handleDataUpdate(data) {
    // Sprawdź czy stacja istnieje, jeśli nie - dodaj
    if (!markers[data.station_id] && data.lat && data.lng) {
        addNewStation(data);
    }
    
    // Zaktualizuj lokalizację jeśli się zmieniła
    updateStationLocation(data);

    currentData[data.station_id] = {
        ...data,
        receivedAt: Date.now()
    };

    if (currentStation === data.station_id) {
        updateCurrentView(data);
    }
}

// ========== NOWA FUNKCJA: Dodawanie stacji ==========
function addNewStation(data) {
    console.log(`✨ Dodawanie nowej stacji: ${data.station_id}`);

    const newStation = {
        id: data.station_id,
        name: data.station_id,
        lat: data.lat,
        lng: data.lng,
        location: data.location || "Nieznana lokalizacja",
        type: data.is_lora ? "lora" : "emulator",
        color: data.is_lora ? "#9C27B0" : "#4CAF50"
    };

    stations.push(newStation);

    const marker = L.marker([newStation.lat, newStation.lng])
        .bindPopup(`
            <div style="min-width: 200px;">
                <h3>${newStation.name}</h3>
                <p><strong>ID:</strong> ${newStation.id}</p>
                <p><strong>Lokalizacja:</strong> ${newStation.location}</p>
                <p><strong>Typ:</strong> ${newStation.type === 'lora' ? '📡 LoRa' : '🖥️ Emulator'}</p>
                <button onclick="selectStation('${newStation.id}')" style="
                    padding: 8px 16px;
                    background: ${newStation.color};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-top: 8px;
                ">Wybierz stację</button>
            </div>
        `)
        .addTo(map);

    markers[newStation.id] = marker;

    const select = document.getElementById('station-select');
    const option = document.createElement('option');
    option.value = newStation.id;
    option.textContent = newStation.name;
    select.appendChild(option);

    console.log(`✅ Stacja ${newStation.id} dodana`);
}

// ========== NOWA FUNKCJA: Aktualizacja lokalizacji ==========
function updateStationLocation(data) {
    if (!data.lat || !data.lng) return;
    
    const station = stations.find(s => s.id === data.station_id);
    if (!station) return;
    
    const latChanged = Math.abs(station.lat - data.lat) > 0.0001;
    const lngChanged = Math.abs(station.lng - data.lng) > 0.0001;
    
    if (latChanged || lngChanged) {
        console.log(`📍 Aktualizacja lokalizacji ${data.station_id}: ${data.lat}, ${data.lng}`);
        
        station.lat = data.lat;
        station.lng = data.lng;
        station.location = data.location || station.location;
        
        if (markers[data.station_id]) {
            markers[data.station_id].setLatLng([data.lat, data.lng]);
        }
    }
}

// ========== TABS ==========
function initTabs() {
    const tabs = document.querySelectorAll('.tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });

    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    const targetPane = document.getElementById(`${tabName}-pane`);
    if (targetPane) {
        targetPane.classList.add('active');
    }

    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    if (tabName === 'charts' && currentStation) {
        loadAllCharts();
    }
}

// ========== DROPDOWNS ==========
function initDropdowns() {
    document.querySelectorAll('.time-range-button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            const chartType = button.dataset.chart;
            const menu = document.querySelector(`.time-range-menu[data-chart="${chartType}"]`);

            document.querySelectorAll('.time-range-menu').forEach(m => {
                if (m !== menu) m.classList.remove('active');
            });

            menu.classList.toggle('active');
        });
    });

    document.querySelectorAll('.time-range-option').forEach(option => {
        option.addEventListener('click', (e) => {
            const hours = parseInt(option.dataset.range);
            const menu = option.closest('.time-range-menu');
            const chartType = menu.dataset.chart;
            const button = document.querySelector(`.time-range-button[data-chart="${chartType}"]`);

            menu.querySelectorAll('.time-range-option').forEach(opt => {
                opt.classList.remove('selected');
            });
            option.classList.add('selected');

            button.textContent = option.textContent;

            menu.classList.remove('active');

            if (currentStation) {
                loadChart(chartType, hours);
            }
        });
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.time-range-menu').forEach(menu => {
            menu.classList.remove('active');
        });
    });
}

// ========== STATION SELECTION ==========
function initStationSelector() {
    const select = document.getElementById('station-select');

    select.addEventListener('change', (e) => {
        const stationId = e.target.value;
        if (stationId) {
            selectStation(stationId);
        }
    });
}

function selectStation(stationId) {
    currentStation = stationId;

    document.getElementById('station-select').value = stationId;
    document.getElementById('welcome-pane').style.display = 'none';

    switchTab('current');

    if (currentData[stationId]) {
        updateCurrentView(currentData[stationId]);
    } else {
        document.getElementById('loading-current').style.display = 'block';
        document.getElementById('current-data').style.display = 'none';
    }

    const station = stations.find(s => s.id === stationId);
    if (station) {
        map.setView([station.lat, station.lng], 15);
        markers[stationId].openPopup();
    }
}

// ========== CURRENT VIEW - ZMIENIONE (z dodatkowymi danymi LoRa) ==========
function updateCurrentView(data) {
    document.getElementById('loading-current').style.display = 'none';
    const container = document.getElementById('current-data');
    container.style.display = 'block';

    const receivedTime = data.receivedAt || Date.now();
    const age = Date.now() - receivedTime;
    const freshness = age < 30000 ? 'fresh' : (age < 300000 ? 'stale' : 'offline');
    const timeAgo = Math.floor(age / 1000);
    const timeText = timeAgo < 60 ? `${timeAgo}s temu` :
        timeAgo < 3600 ? `${Math.floor(timeAgo / 60)}min temu` :
            `${Math.floor(timeAgo / 3600)}h temu`;

    // Helper function dla wartości (N/A jeśli brak)
    const displayValue = (value, unit = '') => {
        if (value === null || value === undefined || value === 0.0) {
            return 'N/A';
        }
        return typeof value === 'number' ? value.toFixed(1) + unit : value + unit;
    };

    container.innerHTML = `
        <!-- Temperature -->
        <div class="parameter-card">
            <div class="parameter-header">
                <div class="parameter-label">
                    <span class="parameter-icon">🌡️</span>
                    <span>Temperatura</span>
                </div>
            </div>
            <div class="parameter-value">${displayValue(data.sensors.temperature, '°C')}</div>
            <div class="parameter-time">
                <div class="freshness-indicator ${freshness}"></div>
                ${timeText}
            </div>
        </div>
        
        <!-- Humidity -->
        <div class="parameter-card">
            <div class="parameter-header">
                <div class="parameter-label">
                    <span class="parameter-icon">💧</span>
                    <span>Wilgotność</span>
                </div>
            </div>
            <div class="parameter-value">${displayValue(data.sensors.humidity, '%')}</div>
            <div class="parameter-time">
                <div class="freshness-indicator ${freshness}"></div>
                ${timeText}
            </div>
        </div>
        
        <!-- Pressure -->
        <div class="parameter-card">
            <div class="parameter-header">
                <div class="parameter-label">
                    <span class="parameter-icon">⏲️</span>
                    <span>Ciśnienie</span>
                </div>
            </div>
            <div class="parameter-value">${displayValue(data.sensors.pressure, ' hPa')}</div>
            <div class="parameter-time">
                <div class="freshness-indicator ${freshness}"></div>
                ${timeText}
            </div>
        </div>
        
        <!-- Wind -->
        <div class="parameter-card">
            <div class="parameter-header">
                <div class="parameter-label">
                    <span class="parameter-icon">💨</span>
                    <span>Wiatr</span>
                </div>
            </div>
            <div class="parameter-value">${displayValue(data.sensors.wind_speed, ' m/s')}</div>
            <div class="parameter-time">
                <div class="freshness-indicator ${freshness}"></div>
                ${timeText}
            </div>
        </div>
        
        <!-- System Info -->
        <div class="system-info">
            <h3>📊 Informacje systemowe</h3>
            <div class="info-row">
                <span class="info-label">Stacja:</span>
                <span class="info-value">${data.station_id}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Bateria:</span>
                <span class="info-value">${data.battery_voltage.toFixed(2)}V</span>
            </div>
            <div class="info-row">
                <span class="info-label">Sygnał:</span>
                <span class="info-value">${data.signal_strength} dBm</span>
            </div>
            <div class="info-row">
                <span class="info-label">Kierunek wiatru:</span>
                <span class="info-value">${displayValue(data.sensors.wind_direction, '°')}</span>
            </div>
        </div>
    `;
    
    // ========== DODATKOWE DANE LoRa ==========
    if (data.is_lora && data.lora_metadata) {
        const meta = data.lora_metadata;
        let loraHtml = `
            <div class="system-info" style="margin-top: 20px;">
                <h3>📡 Dodatkowe dane LoRa</h3>
        `;
        
        if (meta.cell1_voltage) {
            loraHtml += `
                <div class="info-row">
                    <span class="info-label">🔋 Cell 1:</span>
                    <span class="info-value">${meta.cell1_voltage.toFixed(3)}V</span>
                </div>
                <div class="info-row">
                    <span class="info-label">🔋 Cell 2:</span>
                    <span class="info-value">${meta.cell2_voltage.toFixed(3)}V</span>
                </div>
                <div class="info-row">
                    <span class="info-label">🔋 Cell 3:</span>
                    <span class="info-value">${meta.cell3_voltage.toFixed(3)}V</span>
                </div>
            `;
        }
        
        if (meta.temp_bms) {
            loraHtml += `
                <div class="info-row">
                    <span class="info-label">🌡️ Temp BMS:</span>
                    <span class="info-value">${meta.temp_bms.toFixed(2)}°C</span>
                </div>
            `;
        }
        
        if (meta.temp_charger) {
            loraHtml += `
                <div class="info-row">
                    <span class="info-label">🌡️ Temp Charger:</span>
                    <span class="info-value">${meta.temp_charger.toFixed(2)}°C</span>
                </div>
            `;
        }
        
        if (meta.temp_bmp390) {
            loraHtml += `
                <div class="info-row">
                    <span class="info-label">🌡️ Temp BMP390:</span>
                    <span class="info-value">${meta.temp_bmp390.toFixed(2)}°C</span>
                </div>
            `;
        }
        
        if (meta.lux !== undefined) {
            loraHtml += `
                <div class="info-row">
                    <span class="info-label">💡 Lux:</span>
                    <span class="info-value">${meta.lux}</span>
                </div>
            `;
        }
        
        if (meta.white_ratio) {
            loraHtml += `
                <div class="info-row">
                    <span class="info-label">⚪ White Ratio:</span>
                    <span class="info-value">${meta.white_ratio.toFixed(2)}</span>
                </div>
            `;
        }
        
        loraHtml += `</div>`;
        container.innerHTML += loraHtml;
    }
}

// ========== CHARTS ==========
function loadAllCharts() {
    loadChart('temp', getSelectedRange('temp'));
    loadChart('humidity', getSelectedRange('humidity'));
    loadChart('pressure', getSelectedRange('pressure'));
    loadChart('wind', getSelectedRange('wind'));
}

function getSelectedRange(chartType) {
    const menu = document.querySelector(`.time-range-menu[data-chart="${chartType}"]`);
    const selected = menu.querySelector('.time-range-option.selected');
    return parseInt(selected.dataset.range);
}

async function loadChart(chartType, hours) {
    if (!currentStation) return;

    const fieldMap = {
        temp: 'temperature',
        humidity: 'humidity',
        pressure: 'pressure',
        wind: 'wind_speed'
    };

    const labelMap = {
        temp: 'Temperatura (°C)',
        humidity: 'Wilgotność (%)',
        pressure: 'Ciśnienie (hPa)',
        wind: 'Wiatr (m/s)'
    };

    const unitMap = {
        temp: '°C',
        humidity: '%',
        pressure: ' hPa',
        wind: ' m/s'
    };

    const colorMap = {
        temp: { border: '#667eea', bg: 'rgba(102, 126, 234, 0.1)' },
        humidity: { border: '#48bb78', bg: 'rgba(72, 187, 120, 0.1)' },
        pressure: { border: '#f6ad55', bg: 'rgba(246, 173, 85, 0.1)' },
        wind: { border: '#a0aec0', bg: 'rgba(160, 174, 192, 0.1)' }
    };

    const field = fieldMap[chartType];
    const label = labelMap[chartType];
    const unit = unitMap[chartType];
    const colors = colorMap[chartType];

    try {
        const data = await fetchInfluxData(currentStation, field, hours);

        if (data && data.length > 0) {
            const labels = data.map(point => {
                const date = new Date(point.time);
                if (hours <= 3) {
                    return date.getHours().toString().padStart(2, '0') + ':' +
                        date.getMinutes().toString().padStart(2, '0');
                } else if (hours <= 24) {
                    return date.getHours().toString().padStart(2, '0') + ':' +
                        date.getMinutes().toString().padStart(2, '0');
                } else {
                    return date.getDate() + '/' + (date.getMonth() + 1) + ' ' +
                        date.getHours().toString().padStart(2, '0') + ':00';
                }
            });
            const values = data.map(point => point.value);

            renderChart(chartType, labels, values, label, unit, colors);
        }
    } catch (error) {
        console.error(`Błąd ładowania ${chartType}:`, error);
    }
}

async function fetchInfluxData(stationId, field, hours) {
    const query = `
        from(bucket: "${INFLUX_CONFIG.bucket}")
        |> range(start: -${hours}h)
        |> filter(fn: (r) => r["_measurement"] == "weather_measurement")
        |> filter(fn: (r) => r["_field"] == "${field}")
        |> filter(fn: (r) => r["station_id"] == "${stationId}")
        |> aggregateWindow(every: ${hours >= 168 ? '2h' : hours >= 48 ? '1h' : hours >= 24 ? '30m' : hours >= 6 ? '10m' : '5m'}, fn: mean, createEmpty: false)
        |> yield(name: "mean")
    `;

    try {
        const response = await fetch(`${INFLUX_CONFIG.url}/api/v2/query?org=${INFLUX_CONFIG.org}`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${INFLUX_CONFIG.token}`,
                'Content-Type': 'application/vnd.flux',
                'Accept': 'application/csv'
            },
            body: query
        });

        if (!response.ok) {
            throw new Error(`InfluxDB error: ${response.status}`);
        }

        const csv = await response.text();
        return parseInfluxCSV(csv);
    } catch (error) {
        console.error('Błąd zapytania InfluxDB:', error);
        return null;
    }
}

function parseInfluxCSV(csv) {
    const lines = csv.trim().split('\n');
    const data = [];
    let headerFound = false;

    for (let line of lines) {
        if (line.startsWith('#')) continue;
        if (line.includes('_time') && line.includes('_value')) {
            headerFound = true;
            continue;
        }
        if (!headerFound && line.includes(',result,')) {
            headerFound = true;
            continue;
        }
        if (!line.trim()) continue;

        const parts = line.split(',');
        if (parts.length < 7) continue;

        try {
            const time = parts[5];
            const value = parseFloat(parts[6]);

            if (time && !isNaN(value)) {
                data.push({ time: time, value: value });
            }
        } catch (e) {
            continue;
        }
    }

    return data;
}

function renderChart(chartType, labels, data, label, unit, colors) {
    const canvasId = chartType === 'temp' ? 'tempChart' :
        chartType === 'humidity' ? 'humidityChart' :
            chartType === 'pressure' ? 'pressureChart' : 'windChart';

    const ctx = document.getElementById(canvasId).getContext('2d');

    if (charts[chartType]) {
        charts[chartType].destroy();
    }

    charts[chartType] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: colors.border,
                backgroundColor: colors.bg,
                tension: 0.4,
                fill: true,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return context.parsed.y.toFixed(1) + unit;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function (value) {
                            return value.toFixed(1) + unit;
                        }
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    }
                }
            }
        }
    });
}
