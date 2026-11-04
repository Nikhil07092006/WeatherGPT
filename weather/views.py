import requests
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .intelligence import analyze_weather
from .chat import generate_chat_response

def weather_home(request):

    # Get city from URL
    # Example: /api/weather/?city=Bhopal
    city = request.GET.get("city", "Bhopal")

    # ==========================================
    # STEP 1: Find city latitude and longitude
    # ==========================================

    geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"

    geocoding_params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    try:
        geo_response = requests.get(
            geocoding_url,
            params=geocoding_params,
            timeout=10
        )
    except requests.RequestException:
        return JsonResponse({
            "error": "Could not connect to weather service"
        }, status=503)

    if geo_response.status_code != 200:
        return JsonResponse({
            "error": "Unable to find location"
        }, status=500)

    geo_data = geo_response.json()

    # Check whether city exists
    if "results" not in geo_data or not geo_data["results"]:
        return JsonResponse({
            "error": f"Location '{city}' not found"
        }, status=404)

    location = geo_data["results"][0]

    latitude = location["latitude"]
    longitude = location["longitude"]

    # ==========================================
    # STEP 2: Get real weather data
    # ==========================================

    weather_url = "https://api.open-meteo.com/v1/forecast"

    weather_params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m"
        ),

        "timezone": "auto"
    }

    try:
        weather_response = requests.get(
            weather_url,
            params=weather_params,
            timeout=10
        )
    except requests.RequestException:
        return JsonResponse({
            "error": "Could not connect to weather service"
        }, status=503)

    if weather_response.status_code != 200:
        return JsonResponse({
            "error": "Unable to retrieve weather data"
        }, status=500)

    weather_data = weather_response.json()

    current = weather_data["current"]

    # ==========================================
    # STEP 3: Convert weather code into text
    # ==========================================

    weather_conditions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",

        45: "Fog",
        48: "Depositing rime fog",

        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",

        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",

        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",

        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",

        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    weather_code = current["weather_code"]

    condition = weather_conditions.get(
        weather_code,
        "Unknown"
    )

    # ==========================================
    # STEP 4: Return weather information
    # ==========================================

    return JsonResponse({

        "location": {
            "city": location.get("name"),
            "country": location.get("country"),
            "latitude": latitude,
            "longitude": longitude
        },

        "weather": {

            "temperature": current["temperature_2m"],
            "temperature_unit": "°C",

            "feels_like": current["apparent_temperature"],

            "humidity": current["relative_humidity_2m"],

            "precipitation": current["precipitation"],

            "wind_speed": current["wind_speed_10m"],
            "wind_speed_unit": "km/h",

            "condition": condition,

            "weather_code": weather_code
        },

        "source": "Open-Meteo"
    })
def weather_forecast(request):

    # Get city from URL
    # Example: /api/weather/forecast/?city=Bhopal
    city = request.GET.get("city", "Bhopal")

    # ==========================================
    # STEP 1: Find city coordinates
    # ==========================================

    geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"

    geocoding_params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    try:
        geo_response = requests.get(
            geocoding_url,
            params=geocoding_params,
            timeout=10
        )
    except requests.RequestException:
        return JsonResponse({
            "error": "Could not connect to location service"
        }, status=503)

    if geo_response.status_code != 200:
        return JsonResponse({
            "error": "Unable to find location"
        }, status=500)

    geo_data = geo_response.json()

    if "results" not in geo_data or not geo_data["results"]:
        return JsonResponse({
            "error": f"Location '{city}' not found"
        }, status=404)

    location = geo_data["results"][0]

    latitude = location["latitude"]
    longitude = location["longitude"]

    # ==========================================
    # STEP 2: Get 7-day forecast
    # ==========================================

    weather_url = "https://api.open-meteo.com/v1/forecast"

    weather_params = {
        "latitude": latitude,
        "longitude": longitude,

        "daily": (
            "weather_code,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_sum,"
            "precipitation_probability_max,"
            "wind_speed_10m_max,"
            "sunrise,"
            "sunset"
        ),

        "forecast_days": 7,
        "timezone": "auto"
    }

    try:
        weather_response = requests.get(
            weather_url,
            params=weather_params,
            timeout=10
        )
    except requests.RequestException:
        return JsonResponse({
            "error": "Could not connect to weather service"
        }, status=503)

    if weather_response.status_code != 200:
        return JsonResponse({
            "error": "Unable to retrieve forecast"
        }, status=500)

    weather_data = weather_response.json()

    daily = weather_data["daily"]

    # ==========================================
    # STEP 3: Weather code descriptions
    # ==========================================

    weather_conditions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",

        45: "Fog",
        48: "Depositing rime fog",

        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",

        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",

        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",

        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",

        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    # ==========================================
    # STEP 4: Build clean forecast
    # ==========================================

    forecast = []

    for i in range(len(daily["time"])):

        weather_code = daily["weather_code"][i]

        day_data = {
            "date": daily["time"][i],

            "temperature": {
                "max": daily["temperature_2m_max"][i],
                "min": daily["temperature_2m_min"][i],
                "unit": "°C"
            },

            "condition": weather_conditions.get(
                weather_code,
                "Unknown"
            ),

            "weather_code": weather_code,

            "precipitation": {
                "amount": daily["precipitation_sum"][i],
                "unit": "mm"
            },

            "rain_probability": daily[
                "precipitation_probability_max"
            ][i],

            "wind_speed": {
                "max": daily["wind_speed_10m_max"][i],
                "unit": "km/h"
            },

            "sunrise": daily["sunrise"][i],
            "sunset": daily["sunset"][i]
        }

        forecast.append(day_data)

    # ==========================================
    # STEP 5: Return response
    # ==========================================

    return JsonResponse({

        "location": {
            "city": location.get("name"),
            "country": location.get("country"),
            "latitude": latitude,
            "longitude": longitude
        },

        "forecast_days": 7,

        "forecast": forecast,

        "source": "Open-Meteo"
    })
def hourly_weather(request):

    # Get city from URL
    # Example: /api/weather/hourly/?city=Bhopal
    city = request.GET.get("city", "Bhopal")

    # ==========================================
    # STEP 1: Find city coordinates
    # ==========================================

    geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"

    geocoding_params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    try:
        geo_response = requests.get(
            geocoding_url,
            params=geocoding_params,
            timeout=10
        )
    except requests.RequestException:
        return JsonResponse({
            "error": "Could not connect to location service"
        }, status=503)

    if geo_response.status_code != 200:
        return JsonResponse({
            "error": "Unable to find location"
        }, status=500)

    geo_data = geo_response.json()

    if "results" not in geo_data or not geo_data["results"]:
        return JsonResponse({
            "error": f"Location '{city}' not found"
        }, status=404)

    location = geo_data["results"][0]

    latitude = location["latitude"]
    longitude = location["longitude"]

    # ==========================================
    # STEP 2: Get hourly weather
    # ==========================================

    weather_url = "https://api.open-meteo.com/v1/forecast"

    weather_params = {
        "latitude": latitude,
        "longitude": longitude,

        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation_probability,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m"
        ),

        "forecast_days": 2,
        "timezone": "auto"
    }

    try:
        weather_response = requests.get(
            weather_url,
            params=weather_params,
            timeout=10
        )
    except requests.RequestException:
        return JsonResponse({
            "error": "Could not connect to weather service"
        }, status=503)

    if weather_response.status_code != 200:
        return JsonResponse({
            "error": "Unable to retrieve hourly weather"
        }, status=500)

    weather_data = weather_response.json()

    hourly = weather_data["hourly"]

    # ==========================================
    # STEP 3: Weather descriptions
    # ==========================================

    weather_conditions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    # ==========================================
    # STEP 4: Take next 24 hours
    # ==========================================

    hourly_forecast = []

    for i in range(min(24, len(hourly["time"]))):

        weather_code = hourly["weather_code"][i]

        hour_data = {
            "time": hourly["time"][i],

            "temperature": {
                "value": hourly["temperature_2m"][i],
                "unit": "°C"
            },

            "feels_like": {
                "value": hourly["apparent_temperature"][i],
                "unit": "°C"
            },

            "humidity": {
                "value": hourly["relative_humidity_2m"][i],
                "unit": "%"
            },

            "rain_probability": {
                "value": hourly["precipitation_probability"][i],
                "unit": "%"
            },

            "precipitation": {
                "value": hourly["precipitation"][i],
                "unit": "mm"
            },

            "wind_speed": {
                "value": hourly["wind_speed_10m"][i],
                "unit": "km/h"
            },

            "condition": weather_conditions.get(
                weather_code,
                "Unknown"
            ),

            "weather_code": weather_code
        }

        hourly_forecast.append(hour_data)

    # ==========================================
    # STEP 5: Analyze weather
    # ==========================================

    intelligence = analyze_weather(hourly_forecast)

    # ==========================================
    # STEP 6: Return weather + intelligence
    # ==========================================

    return JsonResponse({
        "location": {
            "city": location.get("name"),
            "country": location.get("country"),
            "latitude": latitude,
            "longitude": longitude
        },

        "forecast_hours": len(hourly_forecast),
        "hourly_forecast": hourly_forecast,
        "intelligence": intelligence,
        "source": "Open-Meteo"
    })


# ==========================================
# STEP 7: WeatherGPT Conversational Chat API
# ==========================================

@csrf_exempt
def chat_view(request):
    """
    POST /api/chat/ or GET /api/chat/?message=...
    Conversational weather query endpoint.
    Accepts JSON body: {"message": "Will it rain in Bhopal?", "language": "en"}
    """
    message = ""
    language = None
    history = []
    current_city = None

    if request.method == "POST":
        try:
            if request.body:
                data = json.loads(request.body.decode("utf-8"))
                message = data.get("message", "")
                language = data.get("language")
                history = data.get("history", [])
                current_city = data.get("current_city")
            else:
                message = request.POST.get("message", "")
                language = request.POST.get("language")
                history = json.loads(request.POST.get("history", "[]"))
                current_city = request.POST.get("current_city")
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({
                "error": "Invalid JSON format in request body"
            }, status=400)
    elif request.method == "GET":
        message = request.GET.get("message", "")
        language = request.GET.get("language")
        current_city = request.GET.get("current_city")
    else:
        return JsonResponse({
            "error": "Method not allowed. Use POST or GET."
        }, status=405)

    if not message:
        return JsonResponse({
            "error": "Missing 'message' parameter. Please provide a query like 'Will it rain today in Bhopal?'"
        }, status=400)

    response_data = generate_chat_response(message, language=language, history=history, current_city=current_city)
    return JsonResponse(response_data)


# ==========================================
# STEP 8: WeatherGPT Frontend Dashboard View
# ==========================================

def dashboard_view(request):
    """
    Renders the WeatherGPT interactive web dashboard.
    """
    from django.conf import settings
    map_api_key = getattr(settings, 'MAP_API_KEY', 'cb1_4sh9_1_90828963bd3a4e886bd43716')
    return render(request, "weather/index.html", {"map_api_key": map_api_key})

