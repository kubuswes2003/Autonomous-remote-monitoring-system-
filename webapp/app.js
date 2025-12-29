// Konfiguracja stacji
const stations = [
    {
        id: "WEATHER_STATION_01",
        name: "Station 01 - Strzeszyn",
        lat: 52.443196,
        lng: 16.879174,
        location: "Strzeszyn, Poznań"
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
    map = L.map('map').setView([52.443196, 16.879174], 13);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    stations.forEach(station => {
        addStationMarker(station);
    });
}

function addStationMarker(station) {
    const marker = L.marker([station.lat, station.lng], {
        title: station.name
    }).addTo(map);
    
    marker.bindPopup(`
        <b>${station.name}</b><br>
        ${station.location}<br>
        <button onclick="selectStation('${station.id}')">Zobacz dane</button>
    `);
    
    marker.on('click', () => {
        selectStation(station.id);
    });
    
    markers[station.id] = marker;
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

function handleDataUpdate(data) {
    currentData[data.station_id] = {
        ...data,
        receivedAt: Date.now()
    };
    
    if (currentStation === data.station_id) {
        updateCurrentView(data);
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

// ========== DROPDOWNS (LIKE GRAFANA) ==========
function initDropdowns() {
    // Toggle dropdown on button click
    document.querySelectorAll('.time-range-button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            const chartType = button.dataset.chart;
            const menu = document.querySelector(`.time-range-menu[data-chart="${chartType}"]`);
            
            // Close all other dropdowns
            document.querySelectorAll('.time-range-menu').forEach(m => {
                if (m !== menu) m.classList.remove('active');
            });
            
            // Toggle this dropdown
            menu.classList.toggle('active');
        });
    });
    
    // Select option
    document.querySelectorAll('.time-range-option').forEach(option => {
        option.addEventListener('click', (e) => {
            const hours = parseInt(option.dataset.range);
            const menu = option.closest('.time-range-menu');
            const chartType = menu.dataset.chart;
            const button = document.querySelector(`.time-range-button[data-chart="${chartType}"]`);
            
            // Update selected state
            menu.querySelectorAll('.time-range-option').forEach(opt => {
                opt.classList.remove('selected');
            });
            option.classList.add('selected');
            
            // Update button text
            button.textContent = option.textContent;
            
            // Close dropdown
            menu.classList.remove('active');
            
            // Load chart with new range
            if (currentStation) {
                loadChart(chartType, hours);
            }
        });
    });
    
    // Close dropdowns when clicking outside
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

// ========== CURRENT VIEW (NO SPARKLINES) ==========
function updateCurrentView(data) {
    document.getElementById('loading-current').style.display = 'none';
    const container = document.getElementById('current-data');
    container.style.display = 'block';
    
    const receivedTime = data.receivedAt || Date.now();
    const age = Date.now() - receivedTime;
    const freshness = age < 30000 ? 'fresh' : (age < 300000 ? 'stale' : 'offline');
    const timeAgo = Math.floor(age / 1000);
    const timeText = timeAgo < 60 ? `${timeAgo}s temu` : 
                     timeAgo < 3600 ? `${Math.floor(timeAgo/60)}min temu` : 
                     `${Math.floor(timeAgo/3600)}h temu`;
    
    container.innerHTML = `
        <!-- Temperature -->
        <div class="parameter-card">
            <div class="parameter-header">
                <div class="parameter-label">
                    <span class="parameter-icon">🌡️</span>
                    <span>Temperatura</span>
                </div>
            </div>
            <div class="parameter-value">${data.sensors.temperature.toFixed(1)}°C</div>
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
            <div class="parameter-value">${data.sensors.humidity.toFixed(1)}%</div>
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
            <div class="parameter-value">${data.sensors.pressure.toFixed(1)} hPa</div>
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
            <div class="parameter-value">${data.sensors.wind_speed.toFixed(1)} m/s</div>
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
                <span class="info-value">${data.sensors.wind_direction}°</span>
            </div>
        </div>
    `;
}

// ========== CHARTS (4 SEPARATE) ==========
function loadAllCharts() {
    // Load each chart with its default range (from selected option)
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
        } else {
            console.warn(`Brak danych dla ${chartType}`);
        }
    } catch (error) {
        console.error(`Błąd ładowania ${chartType}:`, error);
    }
}

// Fetch from InfluxDB
async function fetchInfluxData(stationId, field, hours) {
    const query = `
        from(bucket: "${INFLUX_CONFIG.bucket}")
        |> range(start: -${hours}h)
        |> filter(fn: (r) => r["_measurement"] == "weather_measurement")
        |> filter(fn: (r) => r["_field"] == "${field}")
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
        // Skip comments
        if (line.startsWith('#')) {
            continue;
        }
        
        // Skip header line
        if (line.includes('_time') && line.includes('_value')) {
            headerFound = true;
            continue;
        }
        
        // Skip first line with column names if we haven't found header yet
        if (!headerFound && line.includes(',result,')) {
            headerFound = true;
            continue;
        }
        
        // Skip empty lines
        if (!line.trim()) continue;
        
        const parts = line.split(',');
        if (parts.length < 7) continue;
        
        try {
            // CSV format: ,result,table,_start,_stop,_time,_value,...
            // Indices:     0   1     2     3      4     5     6
            const timeIdx = 5;
            const valueIdx = 6;
            
            const time = parts[timeIdx];
            const value = parseFloat(parts[valueIdx]);
            
            if (time && !isNaN(value)) {
                data.push({ time: time, value: value });
            }
        } catch (e) {
            // Skip malformed lines
            continue;
        }
    }
    
    console.log(`Parsed ${data.length} data points`);
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
                        label: function(context) {
                            return context.parsed.y.toFixed(1) + unit;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
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
