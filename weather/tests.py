import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from .chat import detect_intent, detect_language, extract_location, extract_timeframe
from .intelligence import analyze_weather


class WeatherIntelligenceTests(TestCase):
    def test_analyze_weather_low_risk(self):
        sample_hourly = [
            {
                "temperature": {"value": 28.0, "unit": "°C"},
                "rain_probability": {"value": 10, "unit": "%"},
                "wind_speed": {"value": 12.0, "unit": "km/h"}
            }
        ]
        result = analyze_weather(sample_hourly)
        self.assertEqual(result["risk"]["rain"], "Low")
        self.assertEqual(result["risk"]["heat"], "Low")
        self.assertEqual(result["risk"]["wind"], "Low")
        self.assertEqual(result["maximum_rain_probability"], 10)

    def test_analyze_weather_high_rain_risk(self):
        sample_hourly = [
            {
                "temperature": {"value": 31.0, "unit": "°C"},
                "rain_probability": {"value": 85, "unit": "%"},
                "wind_speed": {"value": 15.0, "unit": "km/h"}
            }
        ]
        result = analyze_weather(sample_hourly)
        self.assertEqual(result["risk"]["rain"], "High")
        self.assertTrue(any("umbrella" in r.lower() for r in result["recommendations"]))

    def test_analyze_weather_thunderstorm_and_heat(self):
        sample_hourly = [
            {
                "temperature": {"value": 38.0, "unit": "°C"},
                "humidity": {"value": 70, "unit": "%"},
                "rain_probability": {"value": 75, "unit": "%"},
                "wind_speed": {"value": 45.0, "unit": "km/h"},
                "weather_code": 95
            }
        ]
        result = analyze_weather(sample_hourly)
        self.assertEqual(result["risk"]["thunderstorm"], "High")
        self.assertEqual(result["risk"]["heat"], "High")
        self.assertEqual(result["risk"]["wind"], "High")
        self.assertTrue(any("thunderstorm" in r.lower() for r in result["recommendations"]))
        self.assertIn("IMD", result["disclaimer"])



class WeatherNLPUnderstandingTests(TestCase):
    def test_detect_intent(self):
        self.assertEqual(detect_intent("Will it rain today?"), "rain")
        self.assertEqual(detect_intent("Kya aaj baarish hogi?"), "rain")
        self.assertEqual(detect_intent("क्या आज भोपाल में बारिश होगी?"), "rain")
        self.assertEqual(detect_intent("What is the temperature in Delhi?"), "temperature")
        self.assertEqual(detect_intent("Kitni garmi hai Bhopal me?"), "temperature")
        self.assertEqual(detect_intent("दिल्ली का तापमान कितना है?"), "temperature")
        self.assertEqual(detect_intent("How strong is the wind?"), "wind")
        self.assertEqual(detect_intent("मुंबई में आंधी आएगी क्या?"), "wind")
        self.assertEqual(detect_intent("7 day forecast for Patna"), "forecast")
        self.assertEqual(detect_intent("Hello, who are you?"), "greeting")
        self.assertEqual(detect_intent("नमस्ते WeatherGPT"), "greeting")

    def test_detect_language(self):
        self.assertEqual(detect_language("Will it rain in Bhopal?"), "en")
        self.assertEqual(detect_language("Kal Patna mein baarish hogi kya?"), "hi")
        self.assertEqual(detect_language("क्या आज बारिश होगी?"), "hi")

    def test_extract_location(self):
        self.assertEqual(extract_location("Will it rain in Bhopal?"), "Bhopal")
        self.assertEqual(extract_location("Patna mein mausam kaisa hai?"), "Patna")
        self.assertEqual(extract_location("Temperature for Mumbai today"), "Mumbai")
        self.assertEqual(extract_location("क्या आज भोपाल में बारिश होगी?"), "Bhopal")
        self.assertEqual(extract_location("दिल्ली का तापमान कितना है?"), "Delhi")
        self.assertIsNone(extract_location("Will it rain today?"))

    def test_extract_timeframe(self):
        tf1 = extract_timeframe("Will it rain today evening?")
        self.assertEqual(tf1["day"], "today")
        self.assertEqual(tf1["time_of_day"], "evening")

        tf2 = extract_timeframe("Kal subah ka mausam")
        self.assertEqual(tf2["day"], "tomorrow")
        self.assertEqual(tf2["time_of_day"], "morning")

        tf3 = extract_timeframe("क्या आज शाम बारिश होगी?")
        self.assertEqual(tf3["day"], "today")
        self.assertEqual(tf3["time_of_day"], "evening")

        tf4 = extract_timeframe("tommorow wether in Delhi")
        self.assertEqual(tf4["day"], "tomorrow")

        tf5 = extract_timeframe("tomorrow temperature")
        self.assertEqual(tf5["day"], "tomorrow")


class WeatherChatAPITests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_chat_greeting(self):
        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "greeting")
        self.assertIn("WeatherGPT", data["answer"])

    def test_chat_missing_message(self):
        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": ""}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @patch("weather.chat.geocode_city")
    @patch("weather.chat.get_current_weather")
    @patch("weather.chat.get_hourly_forecast")
    @patch("weather.chat.get_daily_forecast")
    def test_chat_rain_query(self, mock_daily, mock_hourly, mock_current, mock_geo):
        mock_geo.return_value = ({
            "city": "Bhopal",
            "country": "India",
            "latitude": 23.25,
            "longitude": 77.42
        }, None)

        mock_current.return_value = ({
            "temperature": 29.5,
            "feels_like": 31.0,
            "humidity": 55,
            "wind_speed": 12.0,
            "condition": "Partly cloudy",
            "time": "2026-10-16T12:00"
        }, None)

        mock_hourly.return_value = ([
            {
                "time": "2026-10-16T18:00",
                "temperature": {"value": 27.0, "unit": "°C"},
                "humidity": {"value": 60, "unit": "%"},
                "rain_probability": {"value": 15, "unit": "%"},
                "precipitation": {"value": 0.0, "unit": "mm"},
                "wind_speed": {"value": 10.0, "unit": "km/h"},
                "condition": "Mainly clear",
                "weather_code": 1
            }
        ], None)

        mock_daily.return_value = ([], None)

        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "Will it rain this evening in Bhopal?"}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "rain")
        self.assertEqual(data["location"]["city"], "Bhopal")
        self.assertIn("Bhopal", data["answer"])
        self.assertIn("rain", data["answer"].lower())

    def test_dashboard_view_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WeatherGPT")
        self.assertContains(response, "SIH26068")
        self.assertContains(response, "hourlyWeatherChart")
        self.assertContains(response, "cb1_4sh9_1_90828963bd3a4e886bd43716")

    def test_multiturn_location_resolution(self):
        history = [
            {"role": "user", "content": "How is the weather in Delhi?"},
            {"role": "assistant", "content": "The weather in Delhi is sunny."}
        ]
        # Follow-up message without explicit city
        resolved_city = extract_location("Will it rain tomorrow?", history=history)
        self.assertEqual(resolved_city, "Delhi")

    @patch("weather.chat.geocode_city")
    @patch("weather.chat.get_current_weather")
    @patch("weather.chat.get_hourly_forecast")
    @patch("weather.chat.get_daily_forecast")
    @patch("weather.chat.generate_conversational_response")
    def test_chat_with_llm_mock(self, mock_llm, mock_daily, mock_hourly, mock_current, mock_geo):
        mock_geo.return_value = ({
            "city": "Mumbai",
            "country": "India",
            "latitude": 19.07,
            "longitude": 72.87
        }, None)
        mock_current.return_value = ({"temperature": 32, "feels_like": 35, "condition": "Sunny", "time": "2026-10-19T10:00"}, None)
        mock_hourly.return_value = ([], None)
        mock_daily.return_value = ([], None)
        mock_llm.return_value = ("✨ Custom LLM generated weather explanation for Mumbai.", "Gemini")

        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "Tell me about Mumbai", "history": []}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["llm_used"])
        self.assertEqual(data["provider"], "Gemini")
        self.assertIn("Custom LLM generated", data["answer"])


