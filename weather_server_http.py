#!/usr/bin/env python3
import os
import asyncio
import requests
import logging
from datetime import datetime, timezone
import pytz
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logging.info("✓ Environment variables loaded from .env file")
except ImportError:
    logging.warning("python-dotenv not installed. Using system environment variables only.")
except Exception as e:
    logging.warning(f"Could not load .env file: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Weather MCP Server", version="1.0.0")

# Enable CORS for n8n integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5678", "http://localhost:8080"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Restrict methods
    allow_headers=["*"],
)

# Get OpenWeatherMap API key
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not OPENWEATHER_API_KEY:
    logging.error("⚠️ ERROR: No OpenWeatherMap API key found in environment variables.")
    logging.error("Please set OPENWEATHER_API_KEY in your .env file or environment variables.")
    logging.error("You can get a free API key from https://openweathermap.org/api")
    raise ValueError("Missing OPENWEATHER_API_KEY environment variable")

# Configure timezone from environment variable or default to IST
timezone_name = os.getenv("TIMEZONE", "Asia/Kolkata").strip()
LOCAL_TIMEZONE = pytz.timezone(timezone_name)

logging.info("✓ API Key configured successfully")
logging.info(f"✓ Timezone configured: {LOCAL_TIMEZONE.zone}")

def determine_forecast_days(time_param: str) -> int:
    """Determine number of forecast days based on user's time parameter"""
    if not time_param:
        return 5  # default to 5 days if no time specified
    
    time_param = time_param.lower().strip()
    
    # Tomorrow queries
    if "tomorrow" in time_param:
        return 1
    
    # Today queries (current weather, but if they ask for forecast today, give 1 day)
    if "today" in time_param or "now" in time_param:
        return 1
    
    # Next few days
    if "next 2 days" in time_param or "2 days" in time_param:
        return 2
    if "next 3 days" in time_param or "3 days" in time_param:
        return 3
    if "next 4 days" in time_param or "4 days" in time_param:
        return 4
    
    # Week-related queries
    if "week" in time_param or "7 days" in time_param:
        return 5  # OpenWeatherMap free tier gives 5 days max
    
    # Default forecast
    if "5 days" in time_param or "5-day" in time_param:
        return 5
    
    # Extract number patterns like "next 6 days", "6 day forecast", etc.
    import re
    number_match = re.search(r'(\d+)\s*days?', time_param)
    if number_match:
        requested_days = int(number_match.group(1))
        # OpenWeatherMap free tier supports up to 5 days
        return min(requested_days, 5)
    
    # Default to 5 days for general forecast requests
    return 5

class WeatherRequest(BaseModel):
    city: str

class ToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    
class WebhookRequest(BaseModel):
    message: str
    timestamp: str
    preferCurrentWeather: bool = False

@app.get("/health")
async def health_check():
    now = datetime.now(LOCAL_TIMEZONE)
    utc_now = datetime.now(timezone.utc)
    
    # Get environment variable setting
    env_timezone = os.getenv("TIMEZONE", "Not set")
    
    # Calculate offset with formatting
    offset_str = now.strftime("%z")
    formatted_offset = f"{offset_str[:3]}:{offset_str[3:]}" if len(offset_str) >= 5 else offset_str
    
    # Sample timestamp conversion for troubleshooting
    test_utc_timestamp = datetime.now(timezone.utc).timestamp()
    converted_time = datetime.fromtimestamp(test_utc_timestamp, tz=timezone.utc).astimezone(LOCAL_TIMEZONE)
    
    # Also test OpenWeather-style timestamp (they provide Unix timestamp in seconds)
    mock_openweather_timestamp = int(datetime.now(timezone.utc).timestamp())
    openweather_converted = datetime.fromtimestamp(mock_openweather_timestamp, tz=timezone.utc).astimezone(LOCAL_TIMEZONE)
    
    return {
        "status": "healthy", 
        "timestamp": now.isoformat(),
        "timezone": {
            "name": LOCAL_TIMEZONE.zone,
            "env_setting": env_timezone,
            "offset": formatted_offset,
            "formatted_time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "utc_time": utc_now.strftime("%Y-%m-%d %H:%M:%S UTC")
        },
        "timezone_test": {
            "utc_timestamp": test_utc_timestamp,
            "converted_time": converted_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "conversion_method": "datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(LOCAL_TIMEZONE)",
            "openweather_mock": {
                "timestamp": mock_openweather_timestamp,
                "converted_time": openweather_converted.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "time_12h_format": openweather_converted.strftime("%I:%M %p")
            },
            "available_zones": {
                "system": datetime.now().astimezone().tzinfo.tzname(None),
                "current_tz": LOCAL_TIMEZONE.zone,
                "utc": "UTC",
                "ist": "Asia/Kolkata", 
                "est": "America/New_York",
                "pst": "America/Los_Angeles"
            }
        }
    }

@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    return {
        "tools": [
            {
                "name": "get_weather",
                "description": "Get current weather information for a city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The name of the city"
                        }
                    },
                    "required": ["city"]
                }
            },
            {
                "name": "get_forecast",
                "description": "Get 5-day weather forecast for a city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The name of the city"
                        }
                    },
                    "required": ["city"]
                }
            },
            {
                "name": "get_tomorrow_forecast",
                "description": "Get tomorrow's weather forecast for a city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The name of the city"
                        }
                    },
                    "required": ["city"]
                }
            }
        ]
    }

@app.post("/tools/execute")
async def execute_tool(request: ToolRequest):
    """Execute a specific MCP tool"""
    try:
        # Log the request with timezone information
        now = datetime.now(LOCAL_TIMEZONE)
        logging.info(f"Received tool request: {request.tool_name} at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logging.info(f"Request parameters: {request.parameters}")
        
        # Extract city
        city = request.parameters.get("city")
        if not city:
            logging.error("Missing city parameter")
            raise HTTPException(status_code=400, detail="Missing city parameter")
        
        # Log detailed parameter analysis
        time_param = request.parameters.get("time", "")
        logging.info(f"🔍 DEBUG: tool_name={request.tool_name}")
        logging.info(f"🔍 DEBUG: city={city}")
        logging.info(f"🔍 DEBUG: time_param='{time_param}'")
        logging.info(f"🔍 DEBUG: all_parameters={dict(request.parameters)}")
        
        # Direct fix for n8n integration
        # This is the most reliable way to fix the issue
        
        # Log the request parameters for debugging
        logging.info(f"Request tool_name: {request.tool_name}")
        logging.info(f"Request parameters: {request.parameters}")
        
        # For n8n integration, use the tool_name that's sent
        # The n8n workflow has been updated to send the correct tool based on the query
        if request.tool_name == "get_weather":
            logging.info(f"Getting current weather for {city}")
            result = await get_current_weather(city)
            logging.info("Returning current weather")
            return result
        elif request.tool_name == "get_forecast":
            # Extract time parameter to determine number of days
            time_param = request.parameters.get("time", "").lower()
            logging.info(f"🔍 FORECAST DEBUG: Raw time_param before processing: '{request.parameters.get('time')}'")
            logging.info(f"🔍 FORECAST DEBUG: Lowercase time_param: '{time_param}'")
            days = determine_forecast_days(time_param)
            logging.info(f"🔍 FORECAST DEBUG: determine_forecast_days('{time_param}') returned: {days}")
            logging.info(f"Getting {days}-day forecast for {city} based on time: '{time_param}'")
            result = await get_weather_forecast(city, days=days)
            logging.info(f"Returning {days}-day forecast")
            return result
        elif request.tool_name == "get_tomorrow_forecast":
            logging.info(f"Getting tomorrow's forecast for {city}")
            result = await get_weather_forecast(city, days=1)
            logging.info("Returning tomorrow's forecast")
            return result
        else:
            logging.warning(f"Unknown tool requested: {request.tool_name}")
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.tool_name}")
    except Exception as e:
        logging.error(f"Error executing tool {request.tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_current_weather(city: str):
    """Get current weather from OpenWeatherMap API"""
    try:
        logging.info(f"Getting current weather for city: '{city}'")
        
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Convert OpenWeather timestamp to local timezone
        local_time = datetime.fromtimestamp(data['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE)
        
        # Get the timezone difference for display
        utc_offset = local_time.strftime('%z')  # Format: +HHMM or -HHMM
        formatted_offset = f"{utc_offset[:3]}:{utc_offset[3:]}"
        
        weather_info = {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": f"{data['main']['temp']}°C",
            "feels_like": f"{data['main']['feels_like']}°C",
            "condition": data["weather"][0]["description"].title(),
            "humidity": f"{data['main']['humidity']}%",
            "pressure": f"{data['main']['pressure']} hPa",
            "wind_speed": f"{data['wind']['speed']} m/s",
            "timestamp": local_time.isoformat(),
            "timezone": LOCAL_TIMEZONE.zone,
            "formatted_time": local_time.strftime('%Y-%m-%d %H:%M:%S'),
            "timezone_offset": formatted_offset
        }
        
        # Get current local time in the configured timezone
        current_time_in_tz = datetime.now(LOCAL_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
        
        # Get day names
        day_name = local_time.strftime("%A")
        
        # Format the time for clearer display
        time_12h = local_time.strftime('%I:%M %p')
        
        return {
            "success": True,
            "data": weather_info,
            "formatted_response": f"""🌤️ Current Weather for {weather_info['city']}, {weather_info['country']}:

🌡️ Temperature: {weather_info['temperature']} (feels like {weather_info['feels_like']})
☁️ Condition: {weather_info['condition']}
💧 Humidity: {weather_info['humidity']}
🌪️ Pressure: {weather_info['pressure']}
💨 Wind Speed: {weather_info['wind_speed']}

📅 {day_name}, {local_time.strftime('%d %b %Y')}
⏰ Local time: {time_12h}
🌐 Timezone: {LOCAL_TIMEZONE.zone} (UTC{formatted_offset})"""
        }
        
    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to fetch weather data: {str(e)}",
            "formatted_response": f"Sorry, I couldn't get weather data for {city}. Please check the city name and try again."
        }

@app.post("/webhook/weather-chat")
async def webhook_handler(request: WebhookRequest):
    """Handle incoming webhook requests from the chat UI"""
    try:
        message = request.message.lower()
        
        # Extract city from the message
        city = extract_city_from_message(message)
        if not city:
            return "I couldn't determine which city you're asking about. Please specify a city name."
        
        # Determine if we should show current weather or forecast
        # Check if the user specifically requested today's weather
        if request.preferCurrentWeather:
            logging.info(f"User asked about today's weather for {city}")
            result = await get_current_weather(city)
            return result["formatted_response"]
        else:
            # Check if the message contains any forecast-related terms
            forecast_terms = ["forecast", "week", "5 day", "5-day", "days", "tomorrow", "future", "next"]
            is_forecast_query = any(term in message for term in forecast_terms)
            
            if is_forecast_query:
                logging.info(f"User asked about forecast for {city}")
                result = await get_weather_forecast(city)
                return result["formatted_response"]
            else:
                # Default to current weather if it's not clearly a forecast request
                logging.info(f"Defaulting to current weather for {city}")
                result = await get_current_weather(city)
                return result["formatted_response"]
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"

def extract_city_from_message(message: str) -> str:
    """Extract city name from user message"""
    # List of common weather question patterns
    patterns = [
        r"weather (?:in|at|for) ([A-Za-z\s]+)(?:\?|$|\.)",
        r"(?:in|at) ([A-Za-z\s]+) (?:weather|temperature|forecast)(?:\?|$|\.)",
        r"(?:will it|is it|how is it|how's) (?:raining|rain|sunny|cloudy|hot|cold|warm) (?:in|at) ([A-Za-z\s]+)(?:\?|$|\.)",
        r"(?:what's|what is) (?:the weather|it) like (?:in|at) ([A-Za-z\s]+)(?:\?|$|\.)",
        r"weather (?:of|for) ([A-Za-z\s]+)(?:\?|$|\.)",
        r"([A-Za-z\s]+) (?:weather|forecast|temperature)(?:\?|$|\.)"
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1).strip()
    
    # Look for city names directly in the message if patterns don't match
    # This is a simplified approach, for a real solution would need a database of city names
    words = message.split()
    for word in words:
        if word[0].isupper() or word in ["london", "paris", "tokyo", "delhi", "hyderabad", "chennai", "mumbai"]:
            return word.capitalize()
    
    return None

async def get_weather_forecast(city: str, days: int = 5):
    """Get weather forecast for specified number of days (1-5 days)"""
    try:
        if days == 1:
            logging.info(f"Getting tomorrow's forecast for city: '{city}'")
            forecast_title = f"📅 Tomorrow's Weather Forecast for"
        else:
            logging.info(f"Getting {days}-day forecast for city: '{city}'")
            forecast_title = f"📅 {days}-Day Weather Forecast for"
        
        url = f"http://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Get the timezone name and offset for display (only once)
        utc_offset = datetime.now(LOCAL_TIMEZONE).strftime('%z')  # Format: +HHMM or -HHMM
        formatted_offset = f"{utc_offset[:3]}:{utc_offset[3:]}"
        timezone_info = f" (Times in {LOCAL_TIMEZONE.zone}, UTC{formatted_offset})"
        
        forecast_text = f"{forecast_title} {data['city']['name']}, {data['city']['country']}:\n\n"
        
        # Group by date and take one forecast per day
        daily_forecasts = {}
        current_date = datetime.now(LOCAL_TIMEZONE).strftime('%Y-%m-%d')
        
        for item in data['list']:
            # Convert timestamp to local timezone - OpenWeather API uses Unix timestamps in UTC
            dt = datetime.fromtimestamp(item['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE)
            date = dt.strftime('%Y-%m-%d')
            
            # For 1-day forecast (tomorrow), skip today's data
            if days == 1 and date == current_date:
                continue
            
            # Only store one forecast per day (the first one we encounter)
            if date not in daily_forecasts:
                daily_forecasts[date] = item
                logging.info(f"Adding forecast for {date}, local time: {dt.strftime('%H:%M:%S')}")
                
                # Stop after we have the requested number of days
                if len(daily_forecasts) >= days:
                    break
        
        # Format the forecast text in a nicer format
        for date, forecast in sorted(daily_forecasts.items()):
            # Convert timestamp to local timezone - clearly documented
            utc_time = datetime.fromtimestamp(forecast['dt'], tz=timezone.utc)
            dt = utc_time.astimezone(LOCAL_TIMEZONE)
            
            logging.info(f"Forecast timestamp conversion for {date}:")
            logging.info(f"  UTC time: {utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            logging.info(f"  Local time ({LOCAL_TIMEZONE.zone}): {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            day_name = dt.strftime('%A')
            date_str = dt.strftime('%d %b %Y')
            time_str = dt.strftime('%I:%M %p')  # 12-hour format with AM/PM
            temp = forecast['main']['temp']
            feels_like = forecast['main']['feels_like']
            desc = forecast['weather'][0]['description'].title()
            humidity = forecast['main']['humidity']
            pressure = forecast['main']['pressure']
            
            # Add emoji and nicer formatting
            forecast_text += f"🗓️ {day_name}, {date_str}:\n"
            forecast_text += f"  🌡️ Temperature: {temp}°C (feels like {feels_like}°C)\n"
            forecast_text += f"  ☁️ Condition: {desc}\n"
            forecast_text += f"  💧 Humidity: {humidity}%\n"
            forecast_text += f"  🌪️ Pressure: {pressure} hPa\n"
            forecast_text += f"  ⏰ Time: {time_str} ({LOCAL_TIMEZONE.zone})\n\n"
        
        # Add a note about the timezone for clarity
        # Add a clear note about the timezone for users
        forecast_text += f"All times shown in {LOCAL_TIMEZONE.zone} (UTC{formatted_offset})."
        
        return {
            "success": True,
            "data": {
                "city": data["city"]["name"],
                "country": data["city"]["country"],
                "timezone": LOCAL_TIMEZONE.zone,
                "timezone_offset": formatted_offset,
                "forecasts": [
                    {
                        "date": date,
                        "day": datetime.fromtimestamp(forecast['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE).strftime('%A'),
                        "time": datetime.fromtimestamp(forecast['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE).strftime('%H:%M'),
                        "time_12h": datetime.fromtimestamp(forecast['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE).strftime('%I:%M %p'),
                        "temperature": f"{forecast['main']['temp']}°C",
                        "description": forecast['weather'][0]['description'].title(),
                        "timestamp_utc": forecast['dt'],
                        "formatted_datetime": datetime.fromtimestamp(forecast['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z')
                    } for date, forecast in sorted(daily_forecasts.items())
                ]
            },
            "formatted_response": forecast_text
        }
        
    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to fetch forecast data: {str(e)}",
            "formatted_response": f"Sorry, I couldn't get forecast data for {city}."
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
