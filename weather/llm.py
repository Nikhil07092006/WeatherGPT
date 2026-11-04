import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def build_system_prompt():
    return (
        "You are WeatherGPT, an intelligent, empathetic, and conversational weather assistant built for SIH 2026 Problem SIH26068.\n"
        "You are provided with real-time verified meteorological data from Open-Meteo and risk assessments from the Weather Intelligence Engine.\n\n"
        "STRICT GROUNDING & BEHAVIOR RULES:\n"
        "1. Base your meteorological facts strictly on the provided factual data and intelligence risk assessments.\n"
        "2. NEVER invent, hallucinate, or contradict temperature values, rain percentages, wind speeds, or risk levels.\n"
        "3. Provide direct, helpful, and actionable advice (e.g. carrying an umbrella, wearing light/warm clothing, hydration, morning walk or travel recommendations).\n"
        "4. Tone: Friendly, conversational, warm, and natural. Use relevant weather emojis (☀️, 🌧️, 🌡️, 💨, ☔, etc.).\n"
        "5. Avoid robotic meta-talk like 'According to the facts provided above' or '[City not specified]'. Speak directly and confidently to the user.\n"
        "6. Language Adaptability: If the user asks in Hindi (Devanagari script), reply in natural, polite Hindi in Devanagari script (e.g., 'हाँ, आज भोपाल में बारिश की संभावना बहुत कम है...'). If the user asks in Hinglish (Roman script), reply in natural Hinglish. If in English, reply in fluent English."
    )


def format_context_for_llm(location, current, hourly_forecast, intelligence, timeframe, daily=None):
    """
    Format retrieved facts into a clean structured block for LLM grounding.
    Includes both live conditions and verified tomorrow / multi-day forecast.
    """
    loc_str = f"{location.get('city', 'Unknown')}, {location.get('country', '')}"
    curr_str = (
        f"Temperature: {current.get('temperature')}°C (Feels like: {current.get('feels_like')}°C), "
        f"Condition: {current.get('condition')}, Humidity: {current.get('humidity')}%, "
        f"Precipitation: {current.get('precipitation')}mm, Wind Speed: {current.get('wind_speed')} km/h"
    )

    risks = intelligence.get("risk", {})
    risk_str = f"Rain Risk: {risks.get('rain')}, Heat Risk: {risks.get('heat')}, Wind Risk: {risks.get('wind')}"
    peaks_str = (
        f"Peak Rain Probability: {intelligence.get('maximum_rain_probability')}% | "
        f"Max Temperature: {intelligence.get('maximum_temperature')}°C | "
        f"Max Wind Speed: {intelligence.get('maximum_wind_speed')} km/h"
    )

    recs_str = "\n".join([f"- {r}" for r in intelligence.get("recommendations", [])])

    tomorrow_str = "N/A"
    if daily and len(daily) > 1:
        t = daily[1]
        tomorrow_str = (
            f"Date: {t.get('date')}, Expected Condition: {t.get('condition')}, "
            f"Max Temp: {t.get('temperature', {}).get('max')}°C, "
            f"Min Temp: {t.get('temperature', {}).get('min')}°C, "
            f"Max Rain Probability: {t.get('rain_probability')}%, "
            f"Max Wind: {t.get('wind_speed', {}).get('max')} km/h"
        )

    hourly_sample = []
    if hourly_forecast:
        step = max(1, len(hourly_forecast) // 8)
        for h in hourly_forecast[::step][:8]:
            t = h.get("time", "")
            temp = h.get("temperature", {}).get("value")
            rain = h.get("rain_probability", {}).get("value")
            cond = h.get("condition")
            hourly_sample.append(f"{t}: {cond}, {temp}°C, {rain}% rain")

    hourly_summary = "; ".join(hourly_sample)

    return (
        f"FACTUAL WEATHER DATA (Source: Open-Meteo):\n"
        f"Location: {loc_str}\n"
        f"Timeframe Queried: {timeframe.get('day', 'today')} {timeframe.get('time_of_day') or ''}\n"
        f"Tomorrow's Verified Forecast: {tomorrow_str}\n"
        f"Today's Live Conditions: {curr_str}\n"
        f"Weather Intelligence Risk Analysis: {risk_str}\n"
        f"Intelligence Metrics: {peaks_str}\n"
        f"Official Recommendations:\n{recs_str}\n"
        f"Hourly Timeline Sample: {hourly_summary}\n"
    )


def call_gemini_api(api_key, user_message, context_facts, history=None, language=None):
    """
    Calls Google Gemini API (generateContent) using standard HTTP requests.
    Tries gemini-2.0-flash, with gemini-1.5-flash as fallback.
    """
    system_instruction = build_system_prompt()
    if language == "hi":
        system_instruction += "\nUser prefers response in natural Hindi/Hinglish."
    elif language == "en":
        system_instruction += "\nUser prefers response in English."

    contents = []

    # Include recent conversation turns if provided
    if history and isinstance(history, list):
        for msg in history[-4:]:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}]
            })

    current_prompt = (
        f"{context_facts}\n\n"
        f"User Question: {user_message}\n\n"
        f"Answer using the factual weather data above:"
    )

    contents.append({
        "role": "user",
        "parts": [{"text": current_prompt}]
    })

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048
        }
    }

    # Attempt with current official Gemini models
    for model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=25
            )
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if text_part:
                        return text_part.strip(), f"Gemini ({model_name})"
            else:
                logger.warning(f"Gemini API ({model_name}) returned status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"Gemini API ({model_name}) call failed: {e}")

    return None, None


def call_openai_api(api_key, user_message, context_facts, history=None, language=None):
    """
    Calls OpenAI Chat Completions API using standard HTTP requests.
    """
    url = "https://api.openai.com/v1/chat/completions"
    system_msg = build_system_prompt()
    if language == "hi":
        system_msg += "\nUser prefers response in Hindi/Hinglish."
    elif language == "en":
        system_msg += "\nUser prefers response in English."

    messages = [{"role": "system", "content": system_msg}]

    if history and isinstance(history, list):
        for msg in history[-4:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})

    prompt = (
        f"{context_facts}\n\n"
        f"User Question: {user_message}\n\n"
        f"Answer using the factual weather data above:"
    )
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 500
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            timeout=12
        )
        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                text_part = choices[0].get("message", {}).get("content", "")
                if text_part:
                    return text_part.strip(), "OpenAI"
        else:
            logger.warning(f"OpenAI API returned status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        logger.warning(f"OpenAI API call failed: {e}")

    return None, None


def generate_conversational_response(user_message, location, current, hourly_forecast, intelligence, timeframe, history=None, language=None, daily=None):
    """
    Attempts to generate an LLM-powered conversational answer grounded in verified facts.
    Returns (answer_text, provider_name) or (None, None) if LLM is unavailable.
    """
    context_facts = format_context_for_llm(location, current, hourly_forecast, intelligence, timeframe, daily=daily)

    gemini_key = getattr(settings, "GEMINI_API_KEY", "")
    openai_key = getattr(settings, "OPENAI_API_KEY", "")

    if gemini_key:
        answer, provider = call_gemini_api(gemini_key, user_message, context_facts, history, language)
        if answer:
            return answer, provider

    if openai_key:
        answer, provider = call_openai_api(openai_key, user_message, context_facts, history, language)
        if answer:
            return answer, provider

    return None, None


def generate_general_llm_response(user_message, history=None, language=None):
    """
    Handles general greeting or assistant-capability queries via LLM.
    """
    intro_context = (
        "CONTEXT: You are WeatherGPT, an AI Weather Assistant developed for SIH 2026 Problem SIH26068.\n"
        "Capabilities: Real-time weather, 24-hour hourly graphs, 7-day forecast, rain/heat/wind risk analysis, "
        "interactive Leaflet maps with CARTO & OpenWeather radar layers, voice input & text-to-speech, Hindi & English support."
    )
    gemini_key = getattr(settings, "GEMINI_API_KEY", "")
    openai_key = getattr(settings, "OPENAI_API_KEY", "")

    if gemini_key:
        answer, provider = call_gemini_api(gemini_key, user_message, intro_context, history, language)
        if answer:
            return answer, provider

    if openai_key:
        answer, provider = call_openai_api(openai_key, user_message, intro_context, history, language)
        if answer:
            return answer, provider

    return None, None

