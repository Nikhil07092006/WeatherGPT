# 🌦️ WeatherGPT — Conversational AI for Weather Forecasting & Climate Intelligence

**Smart India Hackathon (SIH 2026) | Problem Statement SIH26068**  
*An AI-powered conversational weather intelligence platform connecting live meteorological data with predictive risk analysis and natural-language understanding.*

---

## 📌 Architecture & Design Philosophy

WeatherGPT maintains a strict, fact-grounded 3-tier architecture to eliminate AI hallucinations:

```
                       ┌───────────────────────────────┐
                       │        User Interface         │
                       │  (Dashboard, Chat, Map, Voice)│
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │       Django API Layer        │
                       │   (/api/weather/, /api/chat/) │
                       └───────┬───────────────┬───────┘
                               │               │
                               ▼               ▼
          ┌──────────────────────────┐   ┌──────────────────────────┐
          │  Open-Meteo Weather API  │   │ Conversational AI Layer  │
          │  (Factual Measurements)  │   │  (Multi-Turn Memory NLU) │
          └────────────┬─────────────┘   └─────────────┬────────────┘
                       │                               │
                       ▼                               ▼
          ┌──────────────────────────┐   ┌──────────────────────────┐
          │Weather Intelligence Engine│   │  Gemini / OpenAI API     │
          │(Heat Index, Storms, Risk)│   │  (Strict Factual Ground) │
          └────────────┬─────────────┘   └─────────────┬────────────┘
                       │                               │
                       └───────────────┬───────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │   Fact-Grounded Explanation   │
                       │  (Answers + Risks + Advisory) │
                       └───────────────────────────────┘
```

1. **Weather APIs = Facts**: Live conditions, 24-hour hourly, and 7-day forecasts from Open-Meteo.
2. **Weather Intelligence Engine = Analysis**: Rothfusz heat index regression, convective thunderstorm detection, cumulative precipitation flood risk, and peak-window timing.
3. **Conversational AI = Explanation**: Natural language responses in English or Hindi/Hinglish grounded strictly on verified facts with zero hallucinated measurements.

---

## 🌟 Key Features

- **Conversational Chatbot (`/api/chat/`)**: Natural-language weather queries with automatic intent classification (rain, temperature, wind, multi-day outlook, greetings).
- **Multi-Turn Context Memory**: Context-aware follow-ups (e.g. asking *"Will it rain there tomorrow?"* after querying Delhi).
- **External LLM Integration with Fallback**: Native support for Google Gemini (`gemini-2.5-flash`) and OpenAI (`gpt-4o-mini`) with automatic fallback to our internal deterministic engine if APIs are offline.
- **Voice Input (Speech-to-Text 🎙️)**: Browser-native voice input via the Web Speech API (supports English and Hindi).
- **Spoken Voice Output (Text-to-Speech 🔊)**: Listen to forecasts read aloud with clean pronunciation.
- **Interactive Meteorological Map (Leaflet.js 🗺️)**: Live temperature pin overlay with CartoDB Dark Matter tiles; click anywhere on the globe to inspect real-time weather.
- **Saved Favorite Places ⭐**: Instant 1-click bookmarks saved persistently in browser local storage.
- **Interactive Charts (Chart.js 📈)**: Dual-axis 24-hour temperature curve and rain probability bars.
- **Official IMD Transparency**: Clearly identifies model calculations vs. authoritative government warnings from the India Meteorological Department.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3.12, Django 6.1 | REST API, Business Logic, Routing |
| **Meteorological Data** | Open-Meteo API | Free, keyless global forecasts & geocoding |
| **Intelligence Engine**| Python (NumPy/math) | Heat Index, Storm Detection, Risk Calibration |
| **Conversational AI** | Gemini API / OpenAI API | Multi-turn language generation |
| **Frontend** | HTML5, CSS3, JavaScript (ES6) | Responsive Dark Glassmorphism UI |
| **Charts** | Chart.js 4.4 | 24-hour interactive forecast curves |
| **Maps** | Leaflet.js 1.9 | Geographic weather visualization & click exploration |
| **Voice** | Web Speech API | Client-side Speech-to-Text & Text-to-Speech |
| **Testing** | Django TestCase & unittest.mock | 13 automated tests (< 0.2s runtime) |

---

## 🚀 Quickstart & Installation

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/your-username/WeatherGPT.git
cd WeatherGPT

python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your Gemini or OpenAI API key if you wish to use external LLM generation:
```env
MAP_API_KEY=cb1_4sh9_1_90828963bd3a4e886bd43716
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=
```
*(If left blank, WeatherGPT operates seamlessly using its high-accuracy internal Intelligence Engine!)*

### 4. Run System Checks & Tests
```bash
python manage.py check
python manage.py test weather
```

### 5. Launch the Server
```bash
python manage.py runserver
```
Visit **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## 📡 API Reference

### 1. Conversational Chatbot
- **Endpoint**: `POST /api/chat/`
- **Payload**:
  ```json
  {
    "message": "Will it rain today evening in Bhopal?",
    "language": "en",
    "history": []
  }
  ```
- **Response**:
  ```json
  {
    "answer": "☀️ Rain looks unlikely in Bhopal today evening. The maximum rain probability is only 0%, with generally clear or favorable conditions.",
    "location": { "city": "Bhopal", "country": "India", "latitude": 23.25, "longitude": 77.42 },
    "intent": "rain",
    "timeframe": { "day": "today", "time_of_day": "evening" },
    "risks": { "rain": "Low", "heat": "Low", "wind": "Low", "thunderstorm": "Low" },
    "recommendations": ["Weather conditions look generally favorable."],
    "source": "Open-Meteo",
    "llm_used": false,
    "provider": "Weather Intelligence Engine"
  }
  ```

### 2. Current Conditions
- **Endpoint**: `GET /api/weather/?city=Bhopal`

### 3. Hourly Forecast & Intelligence
- **Endpoint**: `GET /api/weather/hourly/?city=Bhopal`

### 4. 7-Day Extended Forecast
- **Endpoint**: `GET /api/weather/forecast/?city=Bhopal`

---

## 🎯 Demonstration Script for Presentation

1. **City Search & Interactive Map**:
   - Search `Patna` or click a saved pill. Observe the real-time hero card, risk indicators, 24-hour dual-axis chart, and dynamic map center.
   - Click anywhere on the map (e.g. over the coast or a neighboring state) to trigger reverse geolocation and live weather updates.
2. **Conversational Intelligence**:
   - Ask: *"Will it rain today evening in Bhopal?"* — demonstrates entity extraction, timeframe filtering, and rain probability analysis.
   - Follow-up: *"What about tomorrow?"* — demonstrates multi-turn context retention.
   - Hinglish/Hindi: *"Kal Delhi mein baarish hogi kya?"* — demonstrates bilingual language detection.
3. **Voice Interaction**:
   - Click the microphone icon (`🎤`) to speak a question hands-free.
   - Click the speaker icon (`🔊`) on any response to hear the weather advisory read aloud.

---

## 📄 License & Attribution
- Built for **Smart India Hackathon (SIH 2026)**.
- Meteorological data provided by [Open-Meteo](https://open-meteo.com/) under CC BY 4.0.
- Map tiles provided by [CartoDB](https://carto.com/attributions) and [OpenStreetMap](https://www.openstreetmap.org/copyright).
