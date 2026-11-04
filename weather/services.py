import requests

WEATHER_CONDITIONS = {
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


def geocode_city(city_name):
    """
    Search for a city using Open-Meteo Geocoding API.
    Returns (location_dict, None) on success or (None, error_str) on failure.
    """
    if not city_name or not city_name.strip():
        return None, "City name cannot be empty"

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name.strip(),
        "count": 1,
        "language": "en",
        "format": "json"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.RequestException:
        return None, "Could not connect to location service"

    if response.status_code != 200:
        return None, "Unable to find location"

    data = response.json()
    if "results" not in data or not data["results"]:
        return None, f"Location '{city_name}' not found"

    location = data["results"][0]
    return {
        "city": location.get("name"),
        "country": location.get("country"),
        "admin1": location.get("admin1"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude")
    }, None


def get_current_weather(latitude, longitude):
    """
    Fetch current weather metrics for given latitude and longitude.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
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
        response = requests.get(url, params=params, timeout=10)
    except requests.RequestException:
        return None, "Could not connect to weather service"

    if response.status_code != 200:
        return None, "Unable to retrieve weather data"

    data = response.json()
    current = data.get("current", {})
    weather_code = current.get("weather_code", 0)

    return {
        "temperature": current.get("temperature_2m"),
        "temperature_unit": "°C",
        "feels_like": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_speed_unit": "km/h",
        "weather_code": weather_code,
        "condition": WEATHER_CONDITIONS.get(weather_code, "Unknown"),
        "time": current.get("time")
    }, None


def get_hourly_forecast(latitude, longitude, forecast_days=2):
    """
    Fetch hourly weather forecast formatted for analysis and display.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
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
        "forecast_days": forecast_days,
        "timezone": "auto"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.RequestException:
        return None, "Could not connect to weather service"

    if response.status_code != 200:
        return None, "Unable to retrieve hourly weather"

    data = response.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    hourly_forecast = []
    for i in range(len(times)):
        weather_code = hourly["weather_code"][i]
        hourly_forecast.append({
            "time": times[i],
            "temperature": {
                "value": hourly["temperature_2m"][i],
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
            "condition": WEATHER_CONDITIONS.get(weather_code, "Unknown"),
            "weather_code": weather_code
        })

    return hourly_forecast, None


def get_daily_forecast(latitude, longitude, forecast_days=7):
    """
    Fetch daily weather forecast.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
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
        "forecast_days": forecast_days,
        "timezone": "auto"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.RequestException:
        return None, "Could not connect to weather service"

    if response.status_code != 200:
        return None, "Unable to retrieve daily forecast"

    data = response.json()
    daily = data.get("daily", {})
    times = daily.get("time", [])

    daily_forecast = []
    for i in range(len(times)):
        weather_code = daily["weather_code"][i]
        daily_forecast.append({
            "date": times[i],
            "temperature": {
                "max": daily["temperature_2m_max"][i],
                "min": daily["temperature_2m_min"][i],
                "unit": "°C"
            },
            "condition": WEATHER_CONDITIONS.get(weather_code, "Unknown"),
            "weather_code": weather_code,
            "precipitation": {
                "amount": daily["precipitation_sum"][i],
                "unit": "mm"
            },
            "rain_probability": daily["precipitation_probability_max"][i],
            "wind_speed": {
                "max": daily["wind_speed_10m_max"][i],
                "unit": "km/h"
            },
            "sunrise": daily["sunrise"][i],
            "sunset": daily["sunset"][i]
        })

    return daily_forecast, None
