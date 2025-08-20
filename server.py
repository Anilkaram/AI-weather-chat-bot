#!/usr/bin/env python3
import os
import sys
import logging
import pytz
import uvicorn
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def validate_timezone():
    """Validate that the timezone is correctly configured"""
    timezone_name = os.getenv("TIMEZONE")
    
    if not timezone_name:
        logging.warning("TIMEZONE environment variable not set. Defaulting to UTC.")
        return "UTC"
    
    try:
        # Verify the timezone is valid
        tz = pytz.timezone(timezone_name)
        
        # Get current time in various formats for logging
        utc_now = datetime.now(timezone.utc)
        now = datetime.now(tz)
        
        logging.info(f"Timezone configuration successful: {timezone_name}")
        logging.info(f"UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logging.info(f"Local time in {timezone_name}: {now.strftime('%Y-%m-%d %H:%M:%S %Z (%z)')}")
        logging.info(f"Offset from UTC: {now.strftime('%z')}")
        
        return timezone_name
        
    except pytz.exceptions.UnknownTimeZoneError:
        logging.error(f"Invalid timezone: {timezone_name}")
        logging.error("Please set a valid timezone in your .env file.")
        logging.error("Common timezones: Asia/Kolkata, America/New_York, Europe/London, etc.")
        logging.error("See the TIMEZONE_HELP.md file for more information")
        
        # Fallback to UTC
        logging.warning("Falling back to UTC timezone")
        return "UTC"
    except Exception as e:
        logging.error(f"Error setting timezone: {str(e)}")
        logging.warning("Falling back to UTC timezone")
        return "UTC"

def start_server():
    """Start the weather server"""
    # Validate timezone before importing the server module
    timezone_name = validate_timezone()
    
    # Set environment variable to be used by the server
    if timezone_name != os.getenv("TIMEZONE"):
        os.environ["TIMEZONE"] = timezone_name
    
    try:
        # Import the server module after timezone validation
        from weather_server_http import app
        
        # Run the server
        uvicorn.run(app, host="0.0.0.0", port=3001)
    except Exception as e:
        logging.error(f"Failed to start server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    logging.info("Starting Weather Bot Server")
    
    # Check for API key
    if not os.getenv("OPENWEATHER_API_KEY"):
        logging.error("OPENWEATHER_API_KEY environment variable not set")
        logging.error("Please set this in your .env file")
        sys.exit(1)
    
    # Start the server
    start_server()
