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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Weather MCP Server", version="1.0.0")

# Enable CORS for n8n integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get OpenWeatherMap API key
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Configure timezone from environment variable or default to IST
timezone_name = os.getenv("TIMEZONE", "Asia/Kolkata")
LOCAL_TIMEZONE = pytz.timezone(timezone_name)

# Log detailed timezone information for debugging
now_local = datetime.now(LOCAL_TIMEZONE)
now_utc = datetime.now(timezone.utc)
offset = now_local.strftime('%z')
formatted_offset = f"{offset[:3]}:{offset[3:]}"

logging.info("=" * 50)
logging.info(f"TIMEZONE CONFIGURATION")
logging.info("=" * 50)
logging.info(f"Environment TIMEZONE: {timezone_name}")
logging.info(f"System timezone: {datetime.now().astimezone().tzinfo.tzname(None)}")
logging.info(f"Configured timezone: {LOCAL_TIMEZONE.zone}")
logging.info(f"Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
logging.info(f"Current local time: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
logging.info(f"UTC offset: {formatted_offset}")
logging.info("=" * 50)

class WeatherRequest(BaseModel):
    city: str

class ToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

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
            "available_zones": {
                "system": datetime.now().astimezone().tzinfo.tzname(None),
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
        
        if request.tool_name == "get_weather":
            city = request.parameters["city"]
            logging.info(f"Getting weather for {city}")
            result = await get_current_weather(city)
            logging.info(f"Weather data retrieved successfully for {city}")
            return result
        elif request.tool_name == "get_forecast":
            city = request.parameters["city"]
            logging.info(f"Getting forecast for {city}")
            return await get_weather_forecast(city)
        else:
            logging.warning(f"Unknown tool requested: {request.tool_name}")
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.tool_name}")
    except Exception as e:
        logging.error(f"Error executing tool {request.tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_current_weather(city: str):
    """Get current weather from OpenWeatherMap API"""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Convert OpenWeather timestamp (Unix timestamp in seconds, UTC) to local timezone
        local_time = datetime.fromtimestamp(data['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE)
        
        # Log the conversion for debugging
        logging.info(f"Weather data timestamp conversion:")
        logging.info(f"  Original UTC timestamp: {data['dt']}")
        logging.info(f"  Converted to {LOCAL_TIMEZONE.zone}: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Get the timezone difference for display
        utc_offset = local_time.strftime('%z')  # Format: +HHMM or -HHMM
        
        # Format: Insert a colon between hours and minutes in timezone offset
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

async def get_weather_forecast(city: str):
    """Get 5-day weather forecast"""
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Log timezone information for debugging
        logging.info(f"Forecast data received for {city}. Converting from UTC to {LOCAL_TIMEZONE.zone}")
        
        # Get the timezone name and offset for display
        utc_offset = datetime.now(LOCAL_TIMEZONE).strftime('%z')  # Format: +HHMM or -HHMM
        formatted_offset = f"{utc_offset[:3]}:{utc_offset[3:]}"
        timezone_info = f" (Times in {LOCAL_TIMEZONE.zone}, UTC{formatted_offset})"
        
        # Get the timezone name and offset for display
        utc_offset = datetime.now(LOCAL_TIMEZONE).strftime('%z')  # Format: +HHMM or -HHMM
        formatted_offset = f"{utc_offset[:3]}:{utc_offset[3:]}"
        timezone_info = f" (Timezone: {LOCAL_TIMEZONE.zone}, UTC{formatted_offset})"
        
        forecast_text = f"📅 5-Day Weather Forecast for {data['city']['name']}, {data['city']['country']}:\n\n"
        
        # Group by date and take one forecast per day
        daily_forecasts = {}
        for item in data['list']:
            # Convert timestamp to local timezone - OpenWeather API uses Unix timestamps in UTC
            dt = datetime.fromtimestamp(item['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE)
            date = dt.strftime('%Y-%m-%d')
            
            # Only store one forecast per day (the first one we encounter)
            if date not in daily_forecasts:
                daily_forecasts[date] = item
                logging.info(f"Adding forecast for {date}, local time: {dt.strftime('%H:%M:%S')}")
                
                # Stop after we have 5 days
                if len(daily_forecasts) >= 5:
                    break
        
        # Format the forecast text in a nicer format
        for date, forecast in sorted(daily_forecasts.items()):
            # Convert timestamp to local timezone
            dt = datetime.fromtimestamp(forecast['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE)
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
            forecast_text += f"  ⏰ Time: {time_str}\n\n"
        
        # Add a note about the timezone for clarity
        forecast_text += f"All times shown in {LOCAL_TIMEZONE.zone} (UTC{formatted_offset})."
        
        return {
            "success": True,
            "data": {
                "city": data["city"]["name"],
                "country": data["city"]["country"],
                "timezone": LOCAL_TIMEZONE.zone,
                "forecasts": [
                    {
                        "date": date,
                        "day": datetime.fromtimestamp(forecast['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE).strftime('%A'),
                        "time": datetime.fromtimestamp(forecast['dt'], tz=timezone.utc).astimezone(LOCAL_TIMEZONE).strftime('%H:%M'),
                        "temperature": f"{forecast['main']['temp']}°C",
                        "description": forecast['weather'][0]['description'].title()
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
