// WeatherGPT Frontend Client
let weatherChart = null;
let weatherMap = null;
let mapMarker = null;
let chatHistory = [];
let currentCityName = "Bhopal";

const FAVORITES_STORAGE_KEY = "weathergpt_favorites_list";
const MAP_API_KEY = window.MAP_API_KEY || "cb1_4sh9_1_90828963bd3a4e886bd43716";

// Weather code to icon/emoji helper
function getWeatherIcon(code) {
    if (code === 0) return "☀️";
    if (code === 1 || code === 2) return "🌤️";
    if (code === 3) return "☁️";
    if (code === 45 || code === 48) return "🌫️";
    if (code >= 51 && code <= 55) return "🌦️";
    if (code >= 61 && code <= 65) return "🌧️";
    if (code >= 71 && code <= 77) return "❄️";
    if (code >= 80 && code <= 82) return "🌧️";
    if (code >= 95) return "⛈️";
    return "🌤️";
}

// Format date into human readable string
function formatDay(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function formatHour(timeStr) {
    const d = new Date(timeStr);
    return d.toLocaleTimeString("en-US", { hour: "numeric", hour12: true });
}

// Update Risk Badge Color
function setRiskBadge(elementId, riskLevel) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = riskLevel || "Low";
    el.className = "risk-badge badge mt-1 ";
    if (riskLevel === "High") {
        el.classList.add("bg-danger");
    } else if (riskLevel === "Moderate") {
        el.classList.add("bg-warning", "text-dark");
    } else {
        el.classList.add("bg-success");
    }
}

// ==========================================
// Saved Favorites (Local Storage)
// ==========================================

function getSavedFavorites() {
    try {
        const stored = localStorage.getItem(FAVORITES_STORAGE_KEY);
        return stored ? JSON.parse(stored) : ["Bhopal", "Patna", "Delhi"];
    } catch {
        return ["Bhopal", "Patna", "Delhi"];
    }
}

function saveFavorite(cityName) {
    if (!cityName) return;
    const favs = getSavedFavorites();
    if (!favs.some(f => f.toLowerCase() === cityName.toLowerCase())) {
        favs.push(cityName);
        localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favs));
    }
    renderFavoritesBar();
    updateFavoriteButton(cityName);
}

function removeFavorite(cityName) {
    let favs = getSavedFavorites();
    favs = favs.filter(f => f.toLowerCase() !== cityName.toLowerCase());
    localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favs));
    renderFavoritesBar();
    updateFavoriteButton(currentCityName);
}

function isCityFavorited(cityName) {
    const favs = getSavedFavorites();
    return favs.some(f => f.toLowerCase() === (cityName || "").toLowerCase());
}

function updateFavoriteButton(cityName) {
    currentCityName = cityName;
    const btn = document.getElementById("save-favorite-btn");
    const icon = document.getElementById("favorite-icon");
    const label = document.getElementById("save-favorite-text");
    if (!btn || !icon || !label) return;

    if (isCityFavorited(cityName)) {
        icon.className = "bi bi-star-fill text-warning";
        label.textContent = "Saved";
        btn.classList.add("btn-warning", "text-dark");
        btn.classList.remove("btn-outline-warning");
    } else {
        icon.className = "bi bi-star";
        label.textContent = "Save";
        btn.classList.remove("btn-warning", "text-dark");
        btn.classList.add("btn-outline-warning");
    }
}

function renderFavoritesBar() {
    const favBar = document.getElementById("favorites-bar");
    const favList = document.getElementById("favorites-list");
    if (!favBar || !favList) return;

    const favs = getSavedFavorites();
    if (favs.length === 0) {
        favBar.classList.add("d-none");
        return;
    }

    favBar.classList.remove("d-none");
    favList.innerHTML = "";

    favs.forEach(city => {
        const pill = document.createElement("span");
        pill.className = "fav-pill";
        pill.innerHTML = `
            <span class="fav-city-name">${city}</span>
            <button type="button" class="fav-remove-btn" title="Remove">&times;</button>
        `;
        pill.querySelector(".fav-city-name").addEventListener("click", () => {
            document.getElementById("city-input").value = city;
            fetchCityWeather(city);
        });
        pill.querySelector(".fav-remove-btn").addEventListener("click", (e) => {
            e.stopPropagation();
            removeFavorite(city);
        });
        favList.appendChild(pill);
    });
}

// ==========================================
// Interactive Leaflet Map Module
// ==========================================

function updateWeatherMap(lat, lon, cityName, temp, condition) {
    if (!lat || !lon) return;

    const mapContainer = document.getElementById("weather-map");
    if (!mapContainer || typeof L === 'undefined') return;

    if (!weatherMap) {
        const darkBaseLayer = L.tileLayer(`https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=${MAP_API_KEY}`, {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
            subdomains: 'abcd',
            maxZoom: 19
        });

        const voyagerBaseLayer = L.tileLayer(`https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${MAP_API_KEY}`, {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
            subdomains: 'abcd',
            maxZoom: 19
        });

        const osmBaseLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        });

        const precipLayer = L.tileLayer(`https://tile.openweathermap.org/map/precipitation_new/{z}/{x}/{y}.png?appid=${MAP_API_KEY}`, {
            attribution: '&copy; OpenWeatherMap &bull; API Key Connected',
            maxZoom: 18,
            opacity: 0.7
        });

        const cloudsLayer = L.tileLayer(`https://tile.openweathermap.org/map/clouds_new/{z}/{x}/{y}.png?appid=${MAP_API_KEY}`, {
            attribution: '&copy; OpenWeatherMap &bull; API Key Connected',
            maxZoom: 18,
            opacity: 0.6
        });

        const windLayer = L.tileLayer(`https://tile.openweathermap.org/map/wind_new/{z}/{x}/{y}.png?appid=${MAP_API_KEY}`, {
            attribution: '&copy; OpenWeatherMap &bull; API Key Connected',
            maxZoom: 18,
            opacity: 0.6
        });

        weatherMap = L.map('weather-map', {
            zoomControl: true,
            scrollWheelZoom: false,
            layers: [darkBaseLayer]
        }).setView([lat, lon], 10);

        const baseMaps = {
            "🌙 Dark Tactical (CARTO)": darkBaseLayer,
            "🌍 Clean Color (CARTO)": voyagerBaseLayer,
            "🗺️ OpenStreetMap": osmBaseLayer
        };

        const overlayMaps = {
            "🌧️ Precipitation Radar": precipLayer,
            "☁️ Cloud Cover": cloudsLayer,
            "💨 Wind Speed": windLayer
        };

        L.control.layers(baseMaps, overlayMaps, { position: 'topright' }).addTo(weatherMap);

        // Click on Map to explore location
        weatherMap.on('click', async (e) => {
            const clickedLat = e.latlng.lat;
            const clickedLon = e.latlng.lng;
            try {
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${clickedLat}&lon=${clickedLon}&format=json`);
                if (res.ok) {
                    const data = await res.json();
                    const addr = data.address || {};
                    const resolvedCity = addr.city || addr.town || addr.village || addr.county || addr.state_district || "Selected Location";
                    document.getElementById("city-input").value = resolvedCity;
                    fetchCityWeather(resolvedCity);
                }
            } catch (err) {
                console.warn("Reverse geocode failed:", err);
            }
        });
    } else {
        weatherMap.setView([lat, lon], 10);
    }

    if (mapMarker) {
        weatherMap.removeLayer(mapMarker);
    }

    const customIcon = L.divIcon({
        className: 'custom-map-pin',
        html: `<div style="background:linear-gradient(135deg, #2563eb, #6366f1); color:#fff; border-radius:20px; padding:3px 9px; font-weight:700; font-size:11px; white-space:nowrap; box-shadow:0 0 10px rgba(99,102,241,0.6); border:1px solid rgba(255,255,255,0.3); display:inline-flex; align-items:center; gap:4px;">
                <span>📍 ${cityName}</span> <span>${Math.round(temp)}°C</span>
               </div>`,
        iconSize: [80, 26],
        iconAnchor: [40, 13]
    });

    mapMarker = L.marker([lat, lon], { icon: customIcon }).addTo(weatherMap);
    mapMarker.bindPopup(`<b>${cityName}</b><br>${condition}<br>Temperature: ${Math.round(temp)}°C`).openPopup();

    setTimeout(() => {
        weatherMap.invalidateSize();
    }, 200);
}

// ==========================================
// Fetch all weather data for a city
// ==========================================

async function fetchCityWeather(city) {
    const loader = document.getElementById("dashboard-loader");
    const content = document.getElementById("dashboard-content");
    const errorBox = document.getElementById("dashboard-error");

    loader.classList.remove("d-none");
    content.classList.add("d-none");
    errorBox.classList.add("d-none");

    try {
        const [currentRes, hourlyRes, forecastRes] = await Promise.all([
            fetch(`/api/weather/?city=${encodeURIComponent(city)}`),
            fetch(`/api/weather/hourly/?city=${encodeURIComponent(city)}`),
            fetch(`/api/weather/forecast/?city=${encodeURIComponent(city)}`)
        ]);

        if (!currentRes.ok) {
            const errData = await currentRes.json().catch(() => ({}));
            throw new Error(errData.error || `City '${city}' not found.`);
        }

        const currentData = await currentRes.json();
        const hourlyData = await hourlyRes.json();
        const forecastData = await forecastRes.json();

        renderCurrentWeather(currentData);
        renderIntelligence(hourlyData.intelligence || {});
        renderHourly(hourlyData.hourly_forecast || []);
        renderDaily(forecastData.forecast || []);

        content.classList.remove("d-none");
    } catch (err) {
        errorBox.textContent = err.message || "Failed to fetch weather data. Please try again.";
        errorBox.classList.remove("d-none");
    } finally {
        loader.classList.add("d-none");
    }
}

// Render Current Weather Hero Card
function renderCurrentWeather(data) {
    const loc = data.location || {};
    const w = data.weather || {};

    document.getElementById("current-city-name").textContent = loc.city || "Unknown";
    document.getElementById("current-country").textContent = loc.country || "";
    document.getElementById("current-temperature").textContent = Math.round(w.temperature ?? 0);
    document.getElementById("current-condition").textContent = `${getWeatherIcon(w.weather_code)} ${w.condition || "Clear"}`;
    document.getElementById("current-feels-like").textContent = Math.round(w.feels_like ?? w.temperature ?? 0);
    document.getElementById("current-humidity").textContent = `${w.humidity ?? 0}%`;
    document.getElementById("current-wind").textContent = `${w.wind_speed ?? 0} km/h`;
    document.getElementById("current-precip").textContent = `${w.precipitation ?? 0} mm`;

    const now = new Date();
    document.getElementById("current-date-time").textContent = `${now.toLocaleDateString("en-US", { weekday: 'long', month: 'short', day: 'numeric' })} • Live update`;

    // Update Interactive Map and Favorite State
    if (loc.latitude && loc.longitude) {
        updateWeatherMap(loc.latitude, loc.longitude, loc.city, w.temperature, w.condition);
    }
    updateFavoriteButton(loc.city);
}

// Render Weather Intelligence Engine Results
function renderIntelligence(intel) {
    const risks = intel.risk || { rain: "Low", heat: "Low", wind: "Low" };
    setRiskBadge("rain-risk-badge", risks.rain);
    setRiskBadge("heat-risk-badge", risks.heat);
    setRiskBadge("wind-risk-badge", risks.wind);

    document.getElementById("intel-max-rain").textContent = intel.maximum_rain_probability ?? 0;
    document.getElementById("intel-max-temp").textContent = intel.maximum_temperature ?? "--";
    document.getElementById("intel-max-wind").textContent = intel.maximum_wind_speed ?? "--";

    const recList = document.getElementById("recommendations-list");
    recList.innerHTML = "";
    const recs = intel.recommendations || ["Weather conditions look generally favorable."];
    recs.forEach(rec => {
        const li = document.createElement("li");
        li.textContent = rec;
        recList.appendChild(li);
    });

    const windowSpan = document.getElementById("intel-window-span");
    if (windowSpan) {
        let details = [];
        if (intel.peak_rain_window) {
            details.push(`🌧️ Elevated Rain Window: ${intel.peak_rain_window}`);
        }
        if (intel.maximum_heat_index && intel.maximum_heat_index > intel.maximum_temperature) {
            details.push(`🌡️ Peak Heat Index: ${intel.maximum_heat_index}°C`);
        }
        if (intel.total_precipitation_mm && intel.total_precipitation_mm > 0) {
            details.push(`💧 24h Total Precip: ${intel.total_precipitation_mm} mm`);
        }
        windowSpan.textContent = details.length ? details.join(" • ") : "Favorable conditions across forecast window";
    }
}

// Render 24-Hour Forecast Chart & Horizontal Strip
function renderHourly(hourlyList) {
    const next24 = hourlyList.slice(0, 24);

    // Render strip
    const strip = document.getElementById("hourly-strip");
    strip.innerHTML = "";

    const labels = [];
    const temps = [];
    const rainProbs = [];

    next24.forEach((h, index) => {
        const timeLabel = formatHour(h.time);
        labels.push(timeLabel);
        temps.push(h.temperature.value);
        rainProbs.push(h.rain_probability.value);

        const pill = document.createElement("div");
        pill.className = `hourly-pill ${index === 0 ? "now" : ""}`;
        pill.innerHTML = `
            <div class="small text-muted">${index === 0 ? "Now" : timeLabel}</div>
            <div class="fs-5 my-1">${getWeatherIcon(h.weather_code)}</div>
            <div class="fw-bold small">${Math.round(h.temperature.value)}°C</div>
            <div class="text-info small" style="font-size:0.7rem;">💧${h.rain_probability.value}%</div>
        `;
        strip.appendChild(pill);
    });

    // Render Chart.js
    const ctx = document.getElementById("hourlyWeatherChart").getContext("2d");
    if (weatherChart) {
        weatherChart.destroy();
    }

    weatherChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Temperature (°C)",
                    data: temps,
                    borderColor: "#38bdf8",
                    backgroundColor: "rgba(56, 189, 248, 0.1)",
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 2,
                    pointHoverRadius: 5,
                    yAxisID: "y"
                },
                {
                    label: "Rain Probability (%)",
                    data: rainProbs,
                    type: "bar",
                    backgroundColor: "rgba(99, 102, 241, 0.4)",
                    borderColor: "#6366f1",
                    borderWidth: 1,
                    borderRadius: 4,
                    yAxisID: "y1"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(15, 23, 42, 0.9)",
                    titleColor: "#f8fafc",
                    bodyColor: "#94a3b8",
                    borderColor: "rgba(255, 255, 255, 0.1)",
                    borderWidth: 1,
                    padding: 10
                }
            },
            scales: {
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94a3b8", font: { size: 10 }, maxTicksLimit: 12 }
                },
                y: {
                    type: "linear",
                    position: "left",
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#38bdf8", callback: v => `${v}°C` }
                },
                y1: {
                    type: "linear",
                    position: "right",
                    min: 0,
                    max: 100,
                    grid: { drawOnChartArea: false },
                    ticks: { color: "#818cf8", callback: v => `${v}%` }
                }
            }
        }
    });
}

// Render 7-Day Extended Outlook
function renderDaily(dailyList) {
    const container = document.getElementById("daily-forecast-container");
    container.innerHTML = "";

    dailyList.forEach((d, idx) => {
        const col = document.createElement("div");
        col.className = "col-md-6 col-xl-4";
        col.innerHTML = `
            <div class="daily-card d-flex align-items-center justify-content-between">
                <div>
                    <div class="fw-bold small">${idx === 0 ? "Today" : formatDay(d.date)}</div>
                    <div class="text-muted small">${getWeatherIcon(d.weather_code)} ${d.condition}</div>
                </div>
                <div class="text-end">
                    <div class="fw-bold text-light">${Math.round(d.temperature.max)}° / <span class="text-muted">${Math.round(d.temperature.min)}°</span></div>
                    <div class="text-info small" style="font-size: 0.72rem;">💧 ${d.rain_probability}% • 💨 ${Math.round(d.wind_speed.max)} km/h</div>
                </div>
            </div>
        `;
        container.appendChild(col);
    });
}

// ==========================================
// Text-to-Speech (Web Speech API)
// ==========================================

function speakAnswer(rawText, lang, btnEl) {
    if (!('speechSynthesis' in window)) {
        alert("Text-to-Speech is not supported in this browser.");
        return;
    }

    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        if (btnEl) btnEl.innerHTML = '<i class="bi bi-volume-up-fill"></i>';
        return;
    }

    const cleanText = rawText
        .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
        .replace(/[*#_~`]/g, '')
        .replace(/\[.*?\]/g, '')
        .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Use Hindi voice only for actual Devanagari script; use Indian English for Hinglish/English text
    if (/[\u0900-\u097F]/.test(cleanText)) {
        utterance.lang = 'hi-IN';
    } else {
        utterance.lang = 'en-IN';
    }

    if (btnEl) {
        btnEl.innerHTML = '<i class="bi bi-stop-circle-fill text-danger"></i>';
        utterance.onend = () => {
            btnEl.innerHTML = '<i class="bi bi-volume-up-fill"></i>';
        };
        utterance.onerror = () => {
            btnEl.innerHTML = '<i class="bi bi-volume-up-fill"></i>';
        };
    }

    window.speechSynthesis.speak(utterance);
}

// ==========================================
// WeatherGPT AI Assistant Chat Logic
// ==========================================

async function sendChatMessage(query, isVoice = false) {
    if (!query || !query.trim()) return;

    // Cancel any ongoing text-to-speech
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }

    const messagesContainer = document.getElementById("chat-messages");
    const typingIndicator = document.getElementById("chat-typing");
    const langSelect = document.getElementById("chat-lang");
    const selectedLang = langSelect.value === "auto" ? null : langSelect.value;

    // 1. Append User Message Bubble
    const userBubble = document.createElement("div");
    userBubble.className = "chat-bubble user-bubble";
    userBubble.textContent = query;
    messagesContainer.appendChild(userBubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Record user message in conversational memory
    chatHistory.push({ role: "user", content: query });

    // 2. Show Typing Indicator
    typingIndicator.classList.remove("d-none");
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const response = await fetch("/api/chat/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: query,
                language: selectedLang,
                current_city: currentCityName,
                history: chatHistory.slice(-6)
            })
        });

        const data = await response.json();

        // Record bot response in conversational memory
        if (data.answer) {
            chatHistory.push({ role: "assistant", content: data.answer });
        }

        // 3. Append Bot Message Bubble
        const botBubble = document.createElement("div");
        botBubble.className = "chat-bubble bot-bubble";

        let riskPillsHtml = "";
        if (data.risks) {
            riskPillsHtml = `
                <div class="d-flex gap-1 mt-2 flex-wrap">
                    <span class="badge bg-secondary" style="font-size:0.7rem;">Rain: ${data.risks.rain || "Low"}</span>
                    <span class="badge bg-secondary" style="font-size:0.7rem;">Heat: ${data.risks.heat || "Low"}</span>
                    <span class="badge bg-secondary" style="font-size:0.7rem;">Wind: ${data.risks.wind || "Low"}</span>
                </div>
            `;
        }

        let recsHtml = "";
        if (data.recommendations && data.recommendations.length > 0) {
            recsHtml = `<div class="mt-2 text-warning small"><i class="bi bi-lightbulb me-1"></i>${data.recommendations[0]}</div>`;
        }

        const providerBadge = data.llm_used
            ? `<span class="badge bg-primary-subtle text-info border border-info-subtle" style="font-size:0.65rem;">✨ ${data.provider}</span>`
            : `<span class="badge bg-secondary-subtle text-light border border-secondary" style="font-size:0.65rem;">⚡ ${data.provider || "Intelligence Engine"}</span>`;

        botBubble.innerHTML = `
            <div class="bubble-header d-flex align-items-center justify-content-between mb-1 gap-2">
                <div class="d-flex align-items-center gap-1">
                    <i class="bi bi-robot text-info"></i>
                    <span class="fw-semibold small">WeatherGPT</span>
                    ${providerBadge}
                </div>
                <div class="d-flex align-items-center gap-1">
                    ${data.location ? `<span class="badge bg-dark border border-secondary text-info" style="font-size:0.68rem;">📍 ${data.location.city}</span>` : ""}
                    <button type="button" class="btn btn-xs btn-outline-secondary speak-btn py-0 px-1 text-light border-secondary" title="Listen to response">
                        <i class="bi bi-volume-up-fill"></i>
                    </button>
                </div>
            </div>
            <div class="bubble-content" style="white-space: pre-line;">${data.answer}</div>
            ${riskPillsHtml}
            ${recsHtml}
        `;
        messagesContainer.appendChild(botBubble);

        // Attach Text-to-Speech event
        const speakBtn = botBubble.querySelector(".speak-btn");
        if (speakBtn) {
            speakBtn.addEventListener("click", () => {
                speakAnswer(data.answer, selectedLang || (data.intent === "greeting" ? "en" : "hi"), speakBtn);
            });
        }

        // Gemini / ChatGPT Voice Feature: If question was asked via voice, auto-speak the answer!
        if (isVoice && data.answer) {
            setTimeout(() => {
                speakAnswer(data.answer, selectedLang || (data.intent === "greeting" ? "en" : "hi"), speakBtn);
            }, 300);
        }

        // If the chat returned a city, also update the dashboard view for that city!
        if (data.location && data.location.city) {
            const currentSearchCity = document.getElementById("city-input").value.trim().toLowerCase();
            if (currentSearchCity !== data.location.city.toLowerCase()) {
                document.getElementById("city-input").value = data.location.city;
                fetchCityWeather(data.location.city);
            }
        }
    } catch (err) {
        const errorBubble = document.createElement("div");
        errorBubble.className = "chat-bubble bot-bubble text-danger";
        errorBubble.textContent = "Sorry, I encountered an error while processing your request. Please try again.";
        messagesContainer.appendChild(errorBubble);
    } finally {
        typingIndicator.classList.add("d-none");
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// ==========================================
// Speech-to-Text (Voice Recognition)
// ==========================================

function normalizeVoiceTranscript(text, lang) {
    if (!text) return "";
    let clean = text.trim();
    if (lang === "en-IN") {
        const replacements = [
            [/\bbho\s*pal\b/gi, "Bhopal"],
            [/\bbhoopal\b/gi, "Bhopal"],
            [/\bvocal\b/gi, "Bhopal"],
            [/\bin\s*dore\b/gi, "Indore"],
            [/\bin\s*door\b/gi, "Indore"],
            [/\bdel\s*hi\b/gi, "Delhi"],
            [/\bpat\s*na\b/gi, "Patna"],
            [/\bmum\s*bai\b/gi, "Mumbai"],
            [/\bbang\s*lore\b/gi, "Bangalore"],
            [/\bvar\s*na\s*si\b/gi, "Varanasi"],
            [/\btrain\s+today\b/gi, "rain today"],
            [/\brange\s+today\b/gi, "rain today"],
            [/\bweather\s+in\s+vocal\b/gi, "weather in Bhopal"],
            [/\bin\s+vocal\b/gi, "in Bhopal"],
            [/\bwhether\b/gi, "weather"],
            [/\btemprature\b/gi, "temperature"]
        ];
        replacements.forEach(([rgx, rep]) => {
            clean = clean.replace(rgx, rep);
        });
    }
    return clean;
}

function setupVoiceInput() {
    const micBtn = document.getElementById("voice-input-btn");
    const langPill = document.getElementById("voice-lang-pill");
    const chatInput = document.getElementById("chat-input");
    const langSelect = document.getElementById("chat-lang");

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        if (micBtn) {
            micBtn.title = "Voice recognition not supported in this browser (Please use Chrome or Edge)";
            micBtn.classList.add("opacity-50");
        }
        if (langPill) langPill.classList.add("d-none");
        return;
    }

    let activeRecognition = null;
    let isListening = false;
    let currentVoiceLang = (langSelect && langSelect.value === "hi") ? "hi" : "en";
    let silenceTimer = null;
    let hasSpoken = false;
    let alreadyDispatched = false;
    const SILENCE_DETECTION_DELAY = 1200; // 1.2s silence after speech marks question asking as finished

    // Helper to update UI language indicators
    function setVoiceLanguage(lang) {
        currentVoiceLang = lang;
        if (langSelect) langSelect.value = lang;
        if (langPill) {
            langPill.textContent = lang === "hi" ? "🇮🇳 HI" : "🇬🇧 EN";
            langPill.title = lang === "hi" 
                ? "Voice language: Hindi (Click to switch to English)" 
                : "Voice language: English (Click to switch to Hindi)";
        }
        if (!isListening) {
            chatInput.placeholder = lang === "hi" 
                ? "सवाल पूछें या बोलें उदा. 'क्या आज भोपाल में बारिश होगी?'..." 
                : "Ask or speak e.g. 'Will it rain today in Bhopal?'...";
        }
    }

    // Toggle pill click event
    if (langPill) {
        langPill.addEventListener("click", () => {
            const nextLang = currentVoiceLang === "hi" ? "en" : "hi";
            setVoiceLanguage(nextLang);
            if (isListening && activeRecognition) {
                activeRecognition.stop();
            }
        });
    }

    // Header dropdown change event
    if (langSelect) {
        langSelect.addEventListener("change", () => {
            setVoiceLanguage(langSelect.value === "hi" ? "hi" : "en");
        });
    }

    // Initialize display
    setVoiceLanguage(currentVoiceLang);

    micBtn.addEventListener("click", () => {
        // Cancel ongoing TTS if speaking
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }

        if (isListening) {
            if (silenceTimer) clearTimeout(silenceTimer);
            if (activeRecognition) {
                try {
                    activeRecognition.stop();
                } catch (e) {}
            }
            return;
        }

        // Create a fresh SpeechRecognition session
        try {
            activeRecognition = new SpeechRecognition();
        } catch (err) {
            console.error("Failed to create SpeechRecognition:", err);
            return;
        }

        const bcpLang = currentVoiceLang === "hi" ? "hi-IN" : "en-IN";
        activeRecognition.lang = bcpLang;
        activeRecognition.continuous = true;
        activeRecognition.interimResults = true;
        activeRecognition.maxAlternatives = 1;

        let capturedFinal = "";
        hasSpoken = false;
        alreadyDispatched = false;

        activeRecognition.onstart = () => {
            isListening = true;
            micBtn.classList.add("mic-recording");
            chatInput.placeholder = currentVoiceLang === "hi" 
                ? "🔴 हिंदी में सुन रहे हैं... बोलिए..." 
                : "🔴 Listening... Speak your question now...";
        };

        activeRecognition.onresult = (event) => {
            let finalStr = "";
            let interimStr = "";
            for (let i = 0; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalStr += event.results[i][0].transcript;
                } else {
                    interimStr += event.results[i][0].transcript;
                }
            }
            capturedFinal = finalStr;
            const liveText = finalStr || interimStr;
            const cleanText = normalizeVoiceTranscript(liveText, bcpLang);
            chatInput.value = cleanText;

            if (cleanText.trim().length > 0) {
                hasSpoken = true;

                // ChatGPT / Gemini Voice VAD: Reset silence timer whenever user speaks
                if (silenceTimer) clearTimeout(silenceTimer);
                silenceTimer = setTimeout(() => {
                    // Speech ended: automatically stop and dispatch question
                    if (isListening && activeRecognition) {
                        try {
                            activeRecognition.stop();
                        } catch (e) {}
                    }
                }, SILENCE_DETECTION_DELAY);
            }
        };

        activeRecognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            if (event.error === "not-allowed") {
                chatInput.placeholder = "Microphone blocked. Allow microphone access in browser settings.";
            } else if (event.error === "no-speech") {
                chatInput.placeholder = "No speech detected. Click mic to speak again.";
            } else if (event.error === "network") {
                chatInput.placeholder = "Speech service network error. Check your internet connection.";
            }
        };

        activeRecognition.onend = () => {
            isListening = false;
            micBtn.classList.remove("mic-recording");
            if (silenceTimer) {
                clearTimeout(silenceTimer);
                silenceTimer = null;
            }

            const textToSend = normalizeVoiceTranscript(capturedFinal.trim() || chatInput.value.trim(), bcpLang);

            // Automatically send question if speech was detected (just like Gemini & ChatGPT)
            if (textToSend && hasSpoken && !alreadyDispatched) {
                alreadyDispatched = true;
                chatInput.value = textToSend;
                chatInput.placeholder = "⚡ Sending question...";

                setTimeout(() => {
                    sendChatMessage(textToSend, true);
                    chatInput.value = "";
                    setVoiceLanguage(currentVoiceLang);
                }, 150);
            } else {
                setVoiceLanguage(currentVoiceLang);
            }
        };

        try {
            capturedFinal = "";
            chatInput.value = "";
            activeRecognition.start();
        } catch (err) {
            console.error("Speech recognition start failed:", err);
            isListening = false;
            micBtn.classList.remove("mic-recording");
        }
    });
}

// ==========================================
// Gemini Live Hands-Free Duplex Voice Mode
// ==========================================

let isGeminiLiveOpen = false;
let geminiLiveRecognition = null;
let geminiLiveSpeaking = false;
let geminiLiveSilenceTimer = null;
let currentLiveLang = "en";

function setupGeminiLiveMode() {
    const liveBtn = document.getElementById("gemini-live-btn");
    const liveModal = document.getElementById("gemini-live-modal");
    const closeBtn = document.getElementById("close-live-btn");
    const stopBtn = document.getElementById("stop-live-btn");
    const toggleLangBtn = document.getElementById("toggle-live-lang-btn");
    const toggleLangText = document.getElementById("toggle-live-lang-text");
    const langBadge = document.getElementById("live-lang-badge");
    const statusText = document.getElementById("live-status-text");
    const orbWrapper = document.getElementById("live-orb-wrapper");
    const userSpeechEl = document.getElementById("live-user-speech");
    const botSpeechEl = document.getElementById("live-bot-speech");
    const orbIcon = document.getElementById("live-orb-icon");

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        if (liveBtn) {
            liveBtn.title = "Gemini Live voice requires Chrome or Edge";
            liveBtn.classList.add("opacity-50");
        }
        return;
    }

    function setLiveOrbState(state, message) {
        if (!orbWrapper) return;
        orbWrapper.classList.remove("orb-listening", "orb-thinking", "orb-speaking");

        if (state === "listening") {
            orbWrapper.classList.add("orb-listening");
            if (orbIcon) orbIcon.className = "bi bi-mic-fill";
            if (statusText) statusText.textContent = message || (currentLiveLang === "hi" ? "सुन रहे हैं... बोलिए..." : "Listening... Speak naturally...");
        } else if (state === "thinking") {
            orbWrapper.classList.add("orb-thinking");
            if (orbIcon) orbIcon.className = "bi bi-cpu-fill";
            if (statusText) statusText.textContent = message || "Analyzing meteorological data...";
        } else if (state === "speaking") {
            orbWrapper.classList.add("orb-speaking");
            if (orbIcon) orbIcon.className = "bi bi-soundwave";
            if (statusText) statusText.textContent = message || "Speaking...";
        }
    }

    function updateLiveLangUI() {
        if (langBadge) langBadge.textContent = currentLiveLang === "hi" ? "🇮🇳 HI" : "🇬🇧 EN";
        if (toggleLangText) toggleLangText.textContent = currentLiveLang === "hi" ? "🇬🇧 English" : "🇮🇳 Hindi";
        const mainPill = document.getElementById("voice-lang-pill");
        const mainSelect = document.getElementById("chat-lang");
        if (mainPill) mainPill.textContent = currentLiveLang === "hi" ? "🇮🇳 HI" : "🇬🇧 EN";
        if (mainSelect) mainSelect.value = currentLiveLang;
    }

    function startLiveRecognition() {
        if (!isGeminiLiveOpen || geminiLiveSpeaking) return;

        if (geminiLiveRecognition) {
            try { geminiLiveRecognition.stop(); } catch (e) {}
            geminiLiveRecognition = null;
        }

        try {
            geminiLiveRecognition = new SpeechRecognition();
        } catch (e) {
            console.error("Gemini Live recognition error:", e);
            return;
        }

        const bcpLang = currentLiveLang === "hi" ? "hi-IN" : "en-IN";
        geminiLiveRecognition.lang = bcpLang;
        geminiLiveRecognition.continuous = true;
        geminiLiveRecognition.interimResults = true;
        geminiLiveRecognition.maxAlternatives = 1;

        let liveFinalText = "";
        let hasSpokenInTurn = false;

        geminiLiveRecognition.onstart = () => {
            setLiveOrbState("listening");
        };

        geminiLiveRecognition.onresult = (event) => {
            if (!isGeminiLiveOpen || geminiLiveSpeaking) return;

            let finalStr = "";
            let interimStr = "";
            for (let i = 0; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalStr += event.results[i][0].transcript;
                } else {
                    interimStr += event.results[i][0].transcript;
                }
            }
            liveFinalText = finalStr;
            const currentSpeech = normalizeVoiceTranscript(finalStr || interimStr, bcpLang);
            if (userSpeechEl && currentSpeech) {
                userSpeechEl.innerHTML = `<span class="fw-semibold text-light">${currentSpeech}</span>`;
            }

            if (currentSpeech.trim().length > 0) {
                hasSpokenInTurn = true;
                if (geminiLiveSilenceTimer) clearTimeout(geminiLiveSilenceTimer);

                // When user pauses for 1.1s, automatically send question!
                geminiLiveSilenceTimer = setTimeout(() => {
                    if (isGeminiLiveOpen && !geminiLiveSpeaking && hasSpokenInTurn) {
                        try {
                            geminiLiveRecognition.stop();
                        } catch (e) {}
                    }
                }, 1100);
            }
        };

        geminiLiveRecognition.onerror = (event) => {
            console.warn("Gemini Live STT error:", event.error);
            if (event.error === "not-allowed") {
                if (statusText) statusText.textContent = "Microphone access blocked.";
            }
        };

        geminiLiveRecognition.onend = () => {
            if (geminiLiveSilenceTimer) {
                clearTimeout(geminiLiveSilenceTimer);
                geminiLiveSilenceTimer = null;
            }

            if (!isGeminiLiveOpen || geminiLiveSpeaking) return;

            const textToProcess = normalizeVoiceTranscript(liveFinalText.trim(), bcpLang);
            if (hasSpokenInTurn && textToProcess) {
                dispatchLiveQuery(textToProcess);
            } else {
                // Keep listening loop active
                setTimeout(() => {
                    if (isGeminiLiveOpen && !geminiLiveSpeaking) {
                        startLiveRecognition();
                    }
                }, 300);
            }
        };

        try {
            geminiLiveRecognition.start();
        } catch (err) {
            console.error("Gemini Live start failed:", err);
        }
    }

    async function dispatchLiveQuery(query) {
        setLiveOrbState("thinking");
        if (botSpeechEl) botSpeechEl.innerHTML = '<span class="text-muted"><i class="bi bi-cpu-fill me-1"></i>Analyzing data...</span>';

        try {
            const response = await fetch("/api/chat/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: query,
                    language: currentLiveLang,
                    current_city: currentCityName,
                    history: chatHistory.slice(-6)
                })
            });

            const data = await response.json();
            const answer = data.answer || "I could not find weather details for that query.";

            // Save in chat history
            chatHistory.push({ role: "user", content: query });
            chatHistory.push({ role: "assistant", content: answer });

            // Update underlying dashboard city if detected
            if (data.location && data.location.city) {
                document.getElementById("city-input").value = data.location.city;
                fetchCityWeather(data.location.city);
            }

            // Display in Live Modal
            if (botSpeechEl) botSpeechEl.innerHTML = `<span>${answer}</span>`;

            // Speak answer using Gemini Live Voice
            speakLiveAnswer(answer);

        } catch (err) {
            console.error("Live query error:", err);
            if (botSpeechEl) botSpeechEl.textContent = "Sorry, I had trouble retrieving weather data.";
            setTimeout(() => {
                if (isGeminiLiveOpen) startLiveRecognition();
            }, 1000);
        }
    }

    function speakLiveAnswer(rawText) {
        if (!('speechSynthesis' in window)) {
            setTimeout(() => { if (isGeminiLiveOpen) startLiveRecognition(); }, 1500);
            return;
        }

        window.speechSynthesis.cancel();
        geminiLiveSpeaking = true;
        setLiveOrbState("speaking");

        const cleanText = rawText
            .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
            .replace(/[*#_~`]/g, '')
            .replace(/\[.*?\]/g, '')
            .trim();

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;

        if (/[\u0900-\u097F]/.test(cleanText) || currentLiveLang === "hi") {
            utterance.lang = "hi-IN";
        } else {
            utterance.lang = "en-IN";
        }

        utterance.onend = () => {
            geminiLiveSpeaking = false;
            // DUPLEX LOOP: As soon as Gemini Live finishes speaking, resume listening immediately!
            if (isGeminiLiveOpen) {
                if (userSpeechEl) userSpeechEl.innerHTML = '<span class="text-muted fst-italic">Listening... Speak your next question...</span>';
                setTimeout(() => {
                    if (isGeminiLiveOpen && !geminiLiveSpeaking) {
                        startLiveRecognition();
                    }
                }, 400);
            }
        };

        utterance.onerror = () => {
            geminiLiveSpeaking = false;
            if (isGeminiLiveOpen) {
                setTimeout(startLiveRecognition, 400);
            }
        };

        window.speechSynthesis.speak(utterance);
    }

    function openLiveSession() {
        isGeminiLiveOpen = true;
        geminiLiveSpeaking = false;
        liveModal.classList.remove("d-none");
        updateLiveLangUI();
        if (userSpeechEl) userSpeechEl.innerHTML = '<span class="text-muted fst-italic">Listening... Speak your weather query...</span>';
        if (botSpeechEl) botSpeechEl.innerHTML = '';
        startLiveRecognition();
    }

    function closeLiveSession() {
        isGeminiLiveOpen = false;
        geminiLiveSpeaking = false;
        if (geminiLiveSilenceTimer) clearTimeout(geminiLiveSilenceTimer);
        if (geminiLiveRecognition) {
            try { geminiLiveRecognition.stop(); } catch (e) {}
            geminiLiveRecognition = null;
        }
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        liveModal.classList.add("d-none");
    }

    // Attach Click Handlers
    if (liveBtn) liveBtn.addEventListener("click", openLiveSession);
    if (closeBtn) closeBtn.addEventListener("click", closeLiveSession);
    if (stopBtn) stopBtn.addEventListener("click", closeLiveSession);
    if (toggleLangBtn) {
        toggleLangBtn.addEventListener("click", () => {
            currentLiveLang = currentLiveLang === "hi" ? "en" : "hi";
            updateLiveLangUI();
            if (isGeminiLiveOpen && !geminiLiveSpeaking) {
                startLiveRecognition();
            }
        });
    }
}

// ==========================================
// Event Listeners on Page Load
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
    // Search Form Submit
    const searchForm = document.getElementById("search-form");
    const cityInput = document.getElementById("city-input");

    searchForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const city = cityInput.value.trim();
        if (city) {
            fetchCityWeather(city);
        }
    });

    // Quick City Buttons
    document.querySelectorAll(".quick-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            const city = pill.getAttribute("data-city");
            cityInput.value = city;
            fetchCityWeather(city);
        });
    });

    // Save Favorite City Button Click
    const saveFavBtn = document.getElementById("save-favorite-btn");
    if (saveFavBtn) {
        saveFavBtn.addEventListener("click", () => {
            if (isCityFavorited(currentCityName)) {
                removeFavorite(currentCityName);
            } else {
                saveFavorite(currentCityName);
            }
        });
    }

    // Chat Form Submit
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");

    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if (msg) {
            sendChatMessage(msg);
            chatInput.value = "";
        }
    });

    // Quick Prompt Buttons
    document.querySelectorAll(".prompt-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            const prompt = pill.getAttribute("data-prompt");
            chatInput.value = prompt;
            sendChatMessage(prompt);
            chatInput.value = "";
        });
    });

    // Clear Conversation Memory
    const clearChatBtn = document.getElementById("clear-chat-btn");
    if (clearChatBtn) {
        clearChatBtn.addEventListener("click", () => {
            chatHistory = [];
            if (window.speechSynthesis) window.speechSynthesis.cancel();
            const messagesContainer = document.getElementById("chat-messages");
            messagesContainer.innerHTML = `
                <div class="chat-bubble bot-bubble mb-3">
                    <div class="bubble-header d-flex align-items-center gap-1 mb-1">
                        <i class="bi bi-robot text-info"></i>
                        <span class="fw-semibold small">WeatherGPT</span>
                    </div>
                    <div class="bubble-content">
                        Conversation memory reset. 👋 How can I help you with weather intelligence today?
                    </div>
                </div>
            `;
        });
    }

    // Initialize Voice Recognition
    setupVoiceInput();

    // Initialize Gemini Live Mode
    setupGeminiLiveMode();

    // Initialize Favorites Bar
    renderFavoritesBar();

    // Initial Weather Load for default city: Bhopal
    fetchCityWeather("Bhopal");
});
