#!/usr/bin/env python3
import os
import asyncio
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

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
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_api_key_here")

class WeatherRequest(BaseModel):
    city: str

class ToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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
        if request.tool_name == "get_weather":
            return await get_current_weather(request.parameters["city"])
        elif request.tool_name == "get_forecast":
            return await get_weather_forecast(request.parameters["city"])
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.tool_name}")
    except Exception as e:
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
        
        weather_info = {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": f"{data['main']['temp']}°C",
            "feels_like": f"{data['main']['feels_like']}°C",
            "condition": data["weather"][0]["description"].title(),
            "humidity": f"{data['main']['humidity']}%",
            "pressure": f"{data['main']['pressure']} hPa",
            "wind_speed": f"{data['wind']['speed']} m/s",
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "data": weather_info,
            "formatted_response": f"""🌤️ Current Weather for {weather_info['city']}, {weather_info['country']}:

🌡️ Temperature: {weather_info['temperature']} (feels like {weather_info['feels_like']})
☁️ Condition: {weather_info['condition']}
💧 Humidity: {weather_info['humidity']}
🌪️ Pressure: {weather_info['pressure']}
💨 Wind Speed: {weather_info['wind_speed']}

Data updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
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
        
        forecast_text = f"📅 5-Day Weather Forecast for {data['city']['name']}, {data['city']['country']}:\n\n"
        
        # Group by date and take one forecast per day
        daily_forecasts = {}
        for item in data['list'][:5]:  # First 5 entries
            date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
            if date not in daily_forecasts:
                daily_forecasts[date] = item
        
        for date, forecast in daily_forecasts.items():
            day_name = datetime.fromtimestamp(forecast['dt']).strftime('%A')
            temp = forecast['main']['temp']
            desc = forecast['weather'][0]['description'].title()
            forecast_text += f"🗓️ {day_name} ({date}): {temp}°C, {desc}\n"
        
        return {
            "success": True,
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
