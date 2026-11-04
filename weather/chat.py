import re
from datetime import datetime, date, timedelta
from .services import geocode_city, get_current_weather, get_hourly_forecast, get_daily_forecast
from .intelligence import analyze_weather
from .llm import generate_conversational_response, generate_general_llm_response

# Pre-defined list of common Indian and global cities for reliable direct matching
COMMON_CITIES = [
    "Bhopal", "Indore", "Delhi", "New Delhi", "Mumbai", "Bangalore", "Bengaluru",
    "Hyderabad", "Chennai", "Kolkata", "Patna", "Jaipur", "Lucknow", "Kanpur",
    "Nagpur", "Pune", "Ahmedabad", "Surat", "Chandigarh", "Noida", "Gurgaon",
    "Gurugram", "Varanasi", "Agra", "Gwalior", "Jabalpur", "Ujjain", "Ranchi",
    "Bhubaneswar", "Dehradun", "Shimla", "Srinagar", "Goa", "Kochi", "Thiruvananthapuram",
    "London", "New York", "Tokyo", "Paris", "Dubai", "Singapore"
]

# Devanagari Hindi to English city name mapping for voice and Hindi text recognition
HINDI_CITY_MAP = {
    "भोपाल": "Bhopal",
    "इंदौर": "Indore",
    "दिल्ली": "Delhi",
    "नई दिल्ली": "New Delhi",
    "मुंबई": "Mumbai",
    "बम्बई": "Mumbai",
    "बैंगलोर": "Bangalore",
    "बेंगलुरु": "Bengaluru",
    "हैदराबाद": "Hyderabad",
    "चेन्नई": "Chennai",
    "कोलकाता": "Kolkata",
    "कलकत्ता": "Kolkata",
    "पटना": "Patna",
    "जयपुर": "Jaipur",
    "लखनऊ": "Lucknow",
    "कानपुर": "Kanpur",
    "नागपुर": "Nagpur",
    "पुणे": "Pune",
    "पूना": "Pune",
    "अहमदाबाद": "Ahmedabad",
    "सूरत": "Surat",
    "चंडीगढ़": "Chandigarh",
    "नोएडा": "Noida",
    "गुड़गांव": "Gurgaon",
    "गुडगांव": "Gurgaon",
    "गुरुग्राम": "Gurugram",
    "वाराणसी": "Varanasi",
    "बनारस": "Varanasi",
    "काशी": "Varanasi",
    "आगरा": "Agra",
    "ग्वालियर": "Gwalior",
    "जबलपुर": "Jabalpur",
    "उज्जैन": "Ujjain",
    "रांची": "Ranchi",
    "भुवनेश्वर": "Bhubaneswar",
    "देहरादून": "Dehradun",
    "शिमला": "Shimla",
    "श्रीनगर": "Srinagar",
    "गोवा": "Goa",
    "कोच्चि": "Kochi",
    "तिरुवनंतपुरम": "Thiruvananthapuram",
    "लंदन": "London",
    "न्यू यॉर्क": "New York",
    "टोक्यो": "Tokyo",
    "पेरिस": "Paris",
    "दुबई": "Dubai",
    "सिंगापुर": "Singapore"
}


def detect_language(text):
    """
    Detect whether the user is speaking in Hindi / Hinglish or English.
    Supports both Devanagari Unicode script (from speech recognition) and Hinglish.
    """
    if not text:
        return "en"

    # 1. Detect Devanagari script (U+0900 to U+097F)
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"

    # 2. Detect Hinglish keywords
    hindi_keywords = [
        "kya", "hogi", "hoga", "rahega", "rahegi", "kaisa", "kaisi", "kaise",
        "baarish", "barish", "mausam", "garmi", "thand", "thandi", "hawa",
        "aaj", "kal", "parso", "shaam", "sham", "subah", "dopahar", "raat",
        "batao", "bataye", "kitna", "kitni", "namaste", "chhati", "chhatri"
    ]
    lowered = text.lower()
    for word in hindi_keywords:
        if re.search(r'\b' + re.escape(word) + r'\b', lowered):
            return "hi"
    return "en"


def detect_intent(text):
    """
    Classify user message into an intent.
    Intents: 'rain', 'temperature', 'wind', 'forecast', 'greeting', 'general'
    Supports English, Hinglish, and Devanagari Hindi voice input.
    """
    lowered = text.lower()

    # Rain / Precipitation (English, Hinglish, Devanagari)
    rain_keywords = [
        "rain", "baarish", "barish", "umbrella", "drizzle", "shower",
        "thunderstorm", "chhatri", "cloud", "cloudy", "badal",
        "बारिश", "बरसात", "वर्षा", "बूंदाबांदी", "छाता", "छतरी", "बादल", "तूफान"
    ]
    if any(k in lowered for k in rain_keywords):
        return "rain"

    # Temperature / Heat / Cold (English, Hinglish, Devanagari)
    temp_keywords = [
        "temperature", "temp", "garmi", "thand", "hot", "cold", "degree",
        "celsius", "humidity", "humid", "nami", "warm", "cool",
        "तापमान", "गर्मी", "ठंड", "ठंडी", "मौसम", "डिग्री", "नमी", "गर्मी कैसी है"
    ]
    if any(k in lowered for k in temp_keywords):
        return "temperature"

    # Wind / Storm (English, Hinglish, Devanagari)
    wind_keywords = [
        "wind", "windy", "hawa", "storm", "breeze", "toofan",
        "हवा", "आंधी", "झोंका", "तेज हवा"
    ]
    if any(k in lowered for k in wind_keywords):
        return "wind"

    # Multi-day Forecast (English, Hinglish, Devanagari)
    forecast_keywords = [
        "forecast", "7 days", "week", "weekly", "agle din", "upcoming", "kal ka mausam",
        "पूर्वानुमान", "हफ्ते", "अगले दिन", "साप्ताहिक", "आने वाले दिन"
    ]
    if any(k in lowered for k in forecast_keywords):
        return "forecast"

    # Greetings / Bot info
    if re.search(r'\b(hi|hello|hey|namaste|who are you|kya kar sakte ho|help|kaise ho|kya haal|who made you|about you)\b', lowered) or any(k in lowered for k in ["नमस्ते", "प्रणाम", "हेलो", "तुम कौन हो", "मदद"]):
        return "greeting"

    return "general"


def extract_timeframe(text):
    """
    Identify specific timeframe if requested.
    Returns dict: {'day': 'today'|'tomorrow'|'all', 'time_of_day': 'morning'|'afternoon'|'evening'|'night'|None}
    Supports English (including common misspellings like 'tommorow', 'tomorow', 'tmrw'), Hinglish, and Hindi.
    """
    lowered = text.lower()
    day = "today"
    time_of_day = None

    tomorrow_patterns = [
        "tomorrow", "tommorow", "tomorow", "tommorrow", "tmrw", "2moro", "2morrow",
        "kal", "कल", "agle din", "अगले दिन", "next day"
    ]
    if any(k in lowered for k in tomorrow_patterns):
        day = "tomorrow"
    elif any(k in lowered for k in ["today", "aaj", "आज", "tonight", "this evening"]):
        day = "today"

    if any(k in lowered for k in ["evening", "shaam", "sham", "शाम", "संध्या"]):
        time_of_day = "evening"
    elif any(k in lowered for k in ["morning", "subah", "सुबह", "प्रातः"]):
        time_of_day = "morning"
    elif any(k in lowered for k in ["afternoon", "dopahar", "दोपहर"]):
        time_of_day = "afternoon"
    elif any(k in lowered for k in ["night", "raat", "रात"]):
        time_of_day = "night"

    return {"day": day, "time_of_day": time_of_day}


def extract_location(text, history=None):
    """
    Extract city/location from user question.
    Supports English, Hinglish, and Hindi (Devanagari script).
    If not found in current question, look back in conversation history.
    """
    if not text:
        return None

    # 1. Direct match on Hindi Devanagari city names
    for hindi_name, eng_name in HINDI_CITY_MAP.items():
        if hindi_name in text:
            return eng_name

    lowered = text.lower()

    # 2. Direct match on known English cities (case-insensitive boundary match)
    for city in COMMON_CITIES:
        pattern = r'\b' + re.escape(city.lower()) + r'\b'
        if re.search(pattern, lowered):
            return city

    # 3. Hindi postposition: e.g. "भोपाल में", "पटना में"
    hindi_pattern = r'([\u0900-\u097F]+)\s*(?:में|me|mein)\b'
    hindi_match = re.search(hindi_pattern, text)
    if hindi_match:
        cand = hindi_match.group(1).strip()
        if cand in HINDI_CITY_MAP:
            return HINDI_CITY_MAP[cand]
        if cand not in ["आज", "कल", "परसों", "सुबह", "शाम", "दोपहर", "रात", "मौसम", "यहाँ", "वहाँ"]:
            return cand

    # 4. English preposition patterns: "in Bhopal", "at Delhi", "for Mumbai", "mein Patna", "me Jaipur"
    patterns = [
        r'\b(?:in|at|for|near|around)\s+([A-Za-z]+)',
        r'\b([A-Za-z]+)\s+(?:mein|me)\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            # Filter out non-location words
            if candidate.lower() not in ["the", "this", "my", "our", "today", "tomorrow", "evening", "morning", "night", "hindi", "english"]:
                return candidate.capitalize()

    # 5. Check conversation history in reverse for previous location (Multi-turn support)
    if history and isinstance(history, list):
        for msg in reversed(history):
            content = msg.get("content", "")
            prev_loc = extract_location(content, history=None)
            if prev_loc:
                return prev_loc

    return None


def filter_hourly_by_timeframe(hourly_forecast, timeframe):
    """
    Filter hourly items by day (today vs tomorrow) and time_of_day.
    Uses dates present in the payload to prevent timezone / midnight boundary mismatches.
    """
    if not hourly_forecast:
        return []

    unique_dates = []
    for h in hourly_forecast:
        d = h.get("time", "").split("T")[0]
        if d and d not in unique_dates:
            unique_dates.append(d)

    if timeframe["day"] == "tomorrow":
        target_date_str = unique_dates[1] if len(unique_dates) > 1 else (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date_str = unique_dates[0] if unique_dates else datetime.now().date().strftime("%Y-%m-%d")

    matching_hours = []
    for hour in hourly_forecast:
        time_str = hour.get("time", "")
        if not time_str.startswith(target_date_str):
            continue

        try:
            hour_val = int(time_str.split("T")[1].split(":")[0])
        except (IndexError, ValueError):
            matching_hours.append(hour)
            continue

        tod = timeframe.get("time_of_day")
        if tod == "morning" and not (6 <= hour_val <= 11):
            continue
        elif tod == "afternoon" and not (12 <= hour_val <= 16):
            continue
        elif tod == "evening" and not (17 <= hour_val <= 21):
            continue
        elif tod == "night" and not (hour_val >= 22 or hour_val <= 5):
            continue

        matching_hours.append(hour)

    return matching_hours if matching_hours else hourly_forecast[:24]


def generate_rule_based_answer(city_name, intent, timeframe, lang, intelligence, current, daily, is_devanagari=False):
    """
    Deterministic rule-based response generator used as verified baseline and LLM fallback.
    Outputs natural Hindi in Devanagari script if user spoke or asked in Devanagari.
    Accurately switches between today's live conditions and tomorrow's forecast based on timeframe.
    """
    is_tomorrow = timeframe.get("day") == "tomorrow"
    tom_daily = (daily[1] if (daily and len(daily) > 1) else None) if is_tomorrow else None

    if is_devanagari:
        time_label = "कल" if is_tomorrow else "आज"
        tod_map = {"morning": "सुबह", "afternoon": "दोपहर", "evening": "शाम", "night": "रात"}
        if timeframe.get("time_of_day"):
            time_label += f" {tod_map.get(timeframe['time_of_day'], '')}"
    else:
        if is_tomorrow:
            time_label = "tomorrow" if lang == "en" else "kal"
        else:
            time_label = "today" if lang == "en" else "aaj"

        if timeframe.get("time_of_day"):
            tod_map_en = {"morning": "morning", "afternoon": "afternoon", "evening": "evening", "night": "tonight"}
            tod_map_hi = {"morning": "subah", "afternoon": "dopahar", "evening": "shaam", "night": "raat"}
            time_label += f" {tod_map_en.get(timeframe['time_of_day'], '')}" if lang == "en" else f" {tod_map_hi.get(timeframe['time_of_day'], '')}"

    if is_tomorrow and tom_daily:
        forecast_cond = tom_daily.get("condition", "Favorable")
        max_temp = tom_daily.get("temperature", {}).get("max", intelligence.get("maximum_temperature", 30))
        min_temp = tom_daily.get("temperature", {}).get("min", "N/A")
        max_rain_prob = tom_daily.get("rain_probability", intelligence.get("maximum_rain_probability", 0))
        max_wind = tom_daily.get("wind_speed", {}).get("max", intelligence.get("maximum_wind_speed", 15))
    else:
        forecast_cond = current.get("condition", "Clear") if current else "Favorable"
        max_rain_prob = intelligence.get("maximum_rain_probability", 0)
        max_temp = intelligence.get("maximum_temperature", current.get("temperature", "N/A") if current else "N/A")
        min_temp = None
        max_wind = intelligence.get("maximum_wind_speed", current.get("wind_speed", "N/A") if current else "N/A")

    if intent == "rain":
        if max_rain_prob >= 70:
            if is_devanagari:
                return f"🌧️ हाँ, {city_name} में {time_label} तेज़ बारिश की पूरी संभावना है (बारिश की संभावना: {max_rain_prob}%)। बाहर निकलते समय छाता ज़रूर साथ रखें।"
            elif lang == "hi":
                return f"🌧️ Haan, {time_label} {city_name} mein tez baarish ki poori sambhavna hai (Rain probability: {max_rain_prob}%). Bahar nikalte waqt chhatri zaroor saath rakhein."
            else:
                return f"🌧️ Yes, heavy rain is very likely in {city_name} {time_label}. The peak rain probability is {max_rain_prob}%. It is strongly advised to carry an umbrella and plan outdoor travel carefully."
        elif max_rain_prob >= 40:
            if is_devanagari:
                return f"🌦️ {city_name} में {time_label} बारिश की संभावना है (बारिश की संभावना: {max_rain_prob}%)। छाता साथ रखना बेहतर होगा।"
            elif lang == "hi":
                return f"🌦️ {city_name} mein {time_label} baarish ki sambhavna hai (Rain probability: {max_rain_prob}%). Thoda alert rahein aur chhatri saath rakhna behtar hoga."
            else:
                return f"🌦️ Rain is possible in {city_name} {time_label}. The maximum precipitation probability reaches {max_rain_prob}%. Keeping an umbrella handy is recommended."
        else:
            if is_devanagari:
                return f"☀️ {city_name} में {time_label} बारिश की संभावना न के बराबर है। अधिकतम संभावना केवल {max_rain_prob}% है। मौसम साफ रहने की उम्मीद है।"
            elif lang == "hi":
                return f"☀️ {time_label.capitalize()} {city_name} mein baarish ki sambhavna na ke barabar hai. Maximum rain probability sirf {max_rain_prob}% hai. Mausam saaf rahne ki ummeed hai."
            else:
                return f"☀️ Rain looks unlikely in {city_name} {time_label}. The maximum rain probability is only {max_rain_prob}%, with generally clear or favorable conditions."

    elif intent == "temperature":
        if is_tomorrow:
            temp_range = f"{min_temp}°C to {max_temp}°C" if min_temp != "N/A" else f"around {max_temp}°C"
            if is_devanagari:
                return f"🌡️ कल {city_name} में तापमान {min_temp}°C से {max_temp}°C के बीच रहने का अनुमान है (अधिकतम लगभग {max_temp}°C)।"
            elif lang == "hi":
                return f"🌡️ Kal {city_name} mein expected temperature {min_temp}°C se {max_temp}°C ke beech rahega (maximum lagbhag {max_temp}°C)."
            else:
                return f"🌡️ Expected temperature in {city_name} tomorrow is {temp_range} with a high around {max_temp}°C."
        else:
            current_temp = current.get("temperature") if current else max_temp
            feels_like = current.get("feels_like") if current else max_temp
            if is_devanagari:
                return f"🌡️ {city_name} में अभी तापमान लगभग {current_temp}°C है (Feels like {feels_like}°C)। {time_label} का अधिकतम तापमान {max_temp}°C तक पहुँचने का अनुमान है।"
            elif lang == "hi":
                return f"🌡️ {city_name} mein abhi temperature lagbhag {current_temp}°C hai (Feels like {feels_like}°C). {time_label.capitalize()} ka maximum temperature {max_temp}°C tak pahunchne ka anuman hai."
            else:
                return f"🌡️ The current temperature in {city_name} is {current_temp}°C (feels like {feels_like}°C). The expected maximum temperature for {time_label} is around {max_temp}°C."

    elif intent == "wind":
        if is_devanagari:
            return f"💨 {city_name} में {time_label} हवा की अधिकतम गति {max_wind} km/h तक जा सकती है। Wind risk level: {intelligence['risk']['wind']}."
        elif lang == "hi":
            return f"💨 {city_name} mein {time_label} hawa ki maximum speed {max_wind} km/h tak ja sakti hai. Wind risk level: {intelligence['risk']['wind']}."
        else:
            return f"💨 In {city_name}, expected peak wind speed {time_label} is around {max_wind} km/h with a {intelligence['risk']['wind']} wind risk level."

    elif intent == "forecast":
        if daily:
            days_summary = []
            for d in daily[:5]:
                d_date = d["date"]
                d_cond = d["condition"]
                d_max = d["temperature"]["max"]
                d_min = d["temperature"]["min"]
                d_rain = d["rain_probability"]
                days_summary.append(f"• {d_date}: {d_cond}, {d_min}°C - {d_max}°C (Rain: {d_rain}%)")
            summary_str = "\n".join(days_summary)
            if is_devanagari:
                return f"📅 {city_name} के अगले दिनों का मौसम पूर्वानुमान:\n{summary_str}"
            elif lang == "hi":
                return f"📅 {city_name} ke agle dino ka forecast:\n{summary_str}"
            else:
                return f"📅 Here is the multi-day forecast for {city_name}:\n{summary_str}"
        else:
            return f"Forecast data is currently unavailable for {city_name}."

    else:
        # General weather
        if is_tomorrow:
            temp_range = f"{min_temp}°C to {max_temp}°C" if min_temp != "N/A" else f"around {max_temp}°C"
            if is_devanagari:
                return (
                    f"🌤️ कल {city_name} में मौसम: {forecast_cond} रहने का अनुमान है। "
                    f"तापमान {temp_range} रहेगा। "
                    f"बारिश की संभावना {max_rain_prob}% और हवा की गति {max_wind} km/h रहेगी।"
                )
            elif lang == "hi":
                return (
                    f"🌤️ Kal {city_name} mein mausam: {forecast_cond} rehne ka anuman hai. "
                    f"Temperature {temp_range} rahega. "
                    f"Rain probability {max_rain_prob}% aur hawa ki speed {max_wind} km/h rahegi."
                )
            else:
                return (
                    f"🌤️ Expected weather in {city_name} tomorrow: {forecast_cond} with temperatures {temp_range}. "
                    f"Rain probability is {max_rain_prob}%, with peak wind around {max_wind} km/h."
                )
        else:
            curr_cond = current.get("condition", "Clear") if current else "Favorable"
            curr_temp = current.get("temperature", max_temp) if current else max_temp
            humidity = current.get("humidity", "N/A") if current else "N/A"
            wind = current.get("wind_speed", max_wind) if current else max_wind

            if is_devanagari:
                return (
                    f"🌤️ {city_name} में अभी मौसम: {curr_cond}, तापमान {curr_temp}°C है। "
                    f"Humidity {humidity}% और हवा की गति {wind} km/h है। "
                    f"Rain probability: {max_rain_prob}%."
                )
            elif lang == "hi":
                return (
                    f"🌤️ {city_name} mein abhi mausam: {curr_cond}, temperature {curr_temp}°C hai. "
                    f"Humidity {humidity}% aur hawa ki speed {wind} km/h hai. "
                    f"Rain probability: {max_rain_prob}%."
                )
            else:
                return (
                    f"🌤️ Current weather in {city_name}: {curr_cond} at {curr_temp}°C (Humidity: {humidity}%, Wind: {wind} km/h). "
                    f"Maximum rain probability {time_label} is {max_rain_prob}%."
                )


def generate_chat_response(message, language=None, history=None, current_city=None):
    """
    Main conversational engine:
    Processes user query -> Detects intent & location (with multi-turn history & active city) ->
    Fetches real weather facts -> Runs intelligence engine ->
    Generates response via LLM (Gemini/OpenAI) with automatic rule-based fallback.
    """
    if not message or not message.strip():
        return {
            "answer": "Please ask a weather question, e.g., 'Will it rain today in Bhopal?' or 'What is the temperature in Delhi?'",
            "intent": "unknown",
            "source": "WeatherGPT"
        }

    lang = language or detect_language(message)
    intent = detect_intent(message)
    timeframe = extract_timeframe(message)

    # Handle greetings & general capability questions
    if intent == "greeting":
        llm_greeting, llm_provider = generate_general_llm_response(message, history=history, language=lang)
        if llm_greeting:
            return {
                "answer": llm_greeting,
                "intent": "greeting",
                "source": "WeatherGPT",
                "llm_used": True,
                "provider": llm_provider,
                "recommendations": ["Try asking: 'Will it rain today?' or '7-day forecast for Delhi'"]
            }

        if lang == "hi":
            answer = (
                "Namaste! 🙏 Main WeatherGPT hoon — aapka AI Weather Assistant.\n"
                "Aap mujhse kisi bhi shehar ke mausam, baarish, temperature ya 7-din ke forecast ke baare mein pooch sakte hain.\n"
                "Example: 'Will it rain today in Bhopal?' ya 'Kal Patna mein mausam kaisa rahega?'"
            )
        else:
            answer = (
                "Hello! 👋 I am WeatherGPT — your conversational weather intelligence assistant.\n"
                "You can ask me about rainfall, current temperature, hourly forecasts, or severe weather risks for any city.\n"
                "Example: 'Will it rain this evening in Bhopal?' or 'What is the temperature in Delhi?'"
            )
        return {
            "answer": answer,
            "intent": "greeting",
            "source": "WeatherGPT",
            "llm_used": False,
            "provider": "WeatherGPT Core",
            "recommendations": ["Try asking: 'Will it rain in Bhopal today?'"]
        }

    # Extract location (using current query, multi-turn history, or active dashboard city)
    detected_city = extract_location(message, history=history)
    if not detected_city:
        detected_city = current_city or "Bhopal"

    # 1. Geocode location
    location, geo_error = geocode_city(detected_city)
    if geo_error:
        if lang == "hi":
            msg = f"Maaf kijiye, mujhe '{detected_city}' location nahi mili. Kripya shehar ka sahi naam batayein."
        else:
            msg = f"Sorry, I couldn't find the location '{detected_city}'. Please verify the city name and try again."
        return {
            "answer": msg,
            "intent": intent,
            "location": None,
            "error": geo_error,
            "source": "Open-Meteo"
        }

    lat = location["latitude"]
    lon = location["longitude"]
    city_name = location["city"]
    country_name = location["country"]

    # 2. Fetch real weather data
    current, _ = get_current_weather(lat, lon)
    hourly, _ = get_hourly_forecast(lat, lon, forecast_days=2)
    daily, _ = get_daily_forecast(lat, lon, forecast_days=7)

    # 3. Analyze weather risks using Weather Intelligence Engine
    relevant_hourly = filter_hourly_by_timeframe(hourly, timeframe) if hourly else []
    intelligence = analyze_weather(relevant_hourly if relevant_hourly else hourly[:24])

    # 4. Attempt LLM generation first
    llm_answer, llm_provider = generate_conversational_response(
        user_message=message,
        location=location,
        current=current,
        hourly_forecast=relevant_hourly,
        intelligence=intelligence,
        timeframe=timeframe,
        history=history,
        language=lang,
        daily=daily
    )

    if llm_answer:
        answer = llm_answer
        llm_used = True
        provider = llm_provider
    else:
        # Fallback to internal rule-based generator
        is_dev = bool(re.search(r'[\u0900-\u097F]', message))
        answer = generate_rule_based_answer(
            city_name=city_name,
            intent=intent,
            timeframe=timeframe,
            lang=lang,
            intelligence=intelligence,
            current=current,
            daily=daily,
            is_devanagari=is_dev
        )
        llm_used = False
        provider = "Weather Intelligence Engine"

    max_rain_prob = intelligence.get("maximum_rain_probability", 0)
    max_temp = intelligence.get("maximum_temperature", current.get("temperature", "N/A"))

    return {
        "answer": answer,
        "location": {
            "city": city_name,
            "country": country_name,
            "latitude": lat,
            "longitude": lon
        },
        "intent": intent,
        "timeframe": timeframe,
        "risks": intelligence.get("risk", {}),
        "maximum_rain_probability": max_rain_prob,
        "maximum_temperature": max_temp,
        "recommendations": intelligence.get("recommendations", []),
        "source": "Open-Meteo",
        "data_timestamp": current.get("time") if current else datetime.utcnow().isoformat(),
        "llm_used": llm_used,
        "provider": provider
    }
