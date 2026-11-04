def calculate_heat_index(temp_c, humidity):
    """
    Compute approximate Heat Index / Apparent Temperature in Celsius
    using Rothfusz regression equation for temperatures >= 27°C (80°F).
    """
    if temp_c < 27 or humidity < 40:
        return temp_c

    # Convert C to F
    T = (temp_c * 9/5) + 32
    R = humidity

    c1 = -42.379
    c2 = 2.04901523
    c3 = 10.14333127
    c4 = -0.22475541
    c5 = -0.00683783
    c6 = -0.05481717
    c7 = 0.00122874
    c8 = 0.00085282
    c9 = -0.00000199

    hi_f = (
        c1 + (c2 * T) + (c3 * R) + (c4 * T * R) +
        (c5 * T * T) + (c6 * R * R) + (c7 * T * T * R) +
        (c8 * T * R * R) + (c9 * T * T * R * R)
    )

    # Convert back to Celsius
    return round((hi_f - 32) * 5/9, 1)


def analyze_weather(hourly_data):
    """
    Advanced Weather Intelligence Engine:
    Analyzes hourly meteorological parameters (temperature, humidity, precipitation,
    probabilities, wind, WMO codes) to generate calibrated risk levels,
    time-window peak risk detections, and actionable advisories.
    """
    rain_risk = "Low"
    heat_risk = "Low"
    wind_risk = "Low"
    thunderstorm_detected = False

    max_temperature = 0
    min_temperature = 100
    max_rain_probability = 0
    max_wind_speed = 0
    max_heat_index = 0
    total_precipitation = 0.0

    rain_risk_hours = []

    # -----------------------------------------
    # Analyze all hourly data
    # -----------------------------------------
    for hour in hourly_data:
        temperature = hour.get("temperature", {}).get("value", 0)
        rain_probability = hour.get("rain_probability", {}).get("value", 0)
        wind_speed = hour.get("wind_speed", {}).get("value", 0)
        humidity = hour.get("humidity", {}).get("value", 50)
        precip = hour.get("precipitation", {}).get("value", 0.0)
        wmo_code = hour.get("weather_code", 0)
        time_str = hour.get("time", "")

        max_temperature = max(max_temperature, temperature)
        min_temperature = min(min_temperature, temperature)
        max_rain_probability = max(max_rain_probability, rain_probability)
        max_wind_speed = max(max_wind_speed, wind_speed)
        total_precipitation += precip

        # Check for thunderstorms (codes 95, 96, 99)
        if wmo_code in [95, 96, 99]:
            thunderstorm_detected = True

        # Compute heat index
        hi = calculate_heat_index(temperature, humidity)
        max_heat_index = max(max_heat_index, hi)

        # Track hours with elevated rain probability
        if rain_probability >= 40:
            try:
                hour_val = time_str.split("T")[1][:5]
                rain_risk_hours.append(hour_val)
            except (IndexError, ValueError):
                pass

    if min_temperature == 100:
        min_temperature = max_temperature

    # -----------------------------------------
    # 1. Rain Risk Calibration
    # -----------------------------------------
    if max_rain_probability >= 70 or total_precipitation >= 15.0:
        rain_risk = "High"
    elif max_rain_probability >= 40 or total_precipitation >= 5.0:
        rain_risk = "Moderate"
    else:
        rain_risk = "Low"

    # -----------------------------------------
    # 2. Heat / Cold Risk Calibration (Heat Index Aware)
    # -----------------------------------------
    if max_heat_index >= 42 or max_temperature >= 40:
        heat_risk = "High"
    elif max_heat_index >= 36 or max_temperature >= 35:
        heat_risk = "Moderate"
    else:
        heat_risk = "Low"

    cold_risk = "High" if min_temperature <= 5 else ("Moderate" if min_temperature <= 10 else "Low")

    # -----------------------------------------
    # 3. Wind Risk Calibration
    # -----------------------------------------
    if max_wind_speed >= 40:
        wind_risk = "High"
    elif max_wind_speed >= 25:
        wind_risk = "Moderate"
    else:
        wind_risk = "Low"

    # -----------------------------------------
    # 4. Generate Actionable Recommendations
    # -----------------------------------------
    recommendations = []

    if thunderstorm_detected:
        recommendations.append(
            "⚡ Thunderstorm and lightning risk detected. Seek safe indoor shelter and avoid open fields."
        )

    if rain_risk == "High":
        if total_precipitation >= 20.0:
            recommendations.append(
                "Heavy rainfall and localized waterlogging possible. Avoid low-lying roads and carry waterproof gear."
            )
        else:
            recommendations.append(
                "Carry an umbrella and avoid unnecessary outdoor travel during peak rain hours."
            )
    elif rain_risk == "Moderate":
        recommendations.append("Keep an umbrella handy as scattered showers are possible.")

    if heat_risk == "High":
        recommendations.append(
            f"Extreme heat index reaching {max_heat_index}°C. Drink plenty of water and avoid strenuous outdoor activity between 12 PM - 4 PM."
        )
    elif heat_risk == "Moderate":
        recommendations.append(
            "Stay hydrated and avoid prolonged exposure to afternoon heat."
        )

    if cold_risk in ["High", "Moderate"] and heat_risk == "Low":
        recommendations.append(
            f"Cold temperatures expected (low of {min_temperature}°C). Wear warm protective layers."
        )

    if wind_risk == "High":
        recommendations.append(
            f"High wind gusts up to {max_wind_speed} km/h expected. Secure loose outdoor objects and stay clear of trees or billboards."
        )
    elif wind_risk == "Moderate":
        recommendations.append("Moderate winds expected. Favorable for most outdoor activities.")

    if not recommendations:
        recommendations.append("Weather conditions look generally favorable.")

    # Time window for rain if detected
    rain_window = None
    if rain_risk_hours:
        rain_window = f"{rain_risk_hours[0]} to {rain_risk_hours[-1]}"

    return {
        "risk": {
            "rain": rain_risk,
            "heat": heat_risk,
            "wind": wind_risk,
            "cold": cold_risk,
            "thunderstorm": "High" if thunderstorm_detected else "Low"
        },
        "maximum_temperature": max_temperature,
        "minimum_temperature": min_temperature,
        "maximum_rain_probability": max_rain_probability,
        "maximum_wind_speed": max_wind_speed,
        "maximum_heat_index": max_heat_index,
        "total_precipitation_mm": round(total_precipitation, 1),
        "peak_rain_window": rain_window,
        "recommendations": recommendations,
        "disclaimer": "Forecast-derived risk index computed from Open-Meteo numerical weather predictions. For official disaster alerts in India, consult IMD."
    }