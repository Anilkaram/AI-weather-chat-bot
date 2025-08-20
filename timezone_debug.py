#!/usr/bin/env python3
import os
import sys
import pytz
from datetime import datetime, timezone
import argparse
import requests

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 50)
    print(" " * 5 + title)
    print("=" * 50)

def check_system_timezone():
    """Check and print system timezone information"""
    print_header("SYSTEM TIMEZONE INFORMATION")
    
    # Get system timezone
    system_tz = datetime.now().astimezone().tzinfo
    
    print(f"System timezone name: {system_tz.tzname(None)}")
    print(f"Current system time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get current UTC time
    utc_now = datetime.now(timezone.utc)
    print(f"Current UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Calculate offset
    local_now = datetime.now()
    utc_offset = local_now.astimezone().utcoffset().total_seconds() / 3600
    print(f"UTC offset: {utc_offset:+.1f} hours")

def check_env_timezone():
    """Check environment variable timezone setting"""
    print_header("ENVIRONMENT VARIABLE CHECK")
    
    # Check if TIMEZONE is set
    timezone_name = os.getenv("TIMEZONE")
    
    if not timezone_name:
        print("WARNING: TIMEZONE environment variable is not set.")
        print("The server will default to UTC.")
        return
    
    print(f"TIMEZONE environment variable: {timezone_name}")
    
    # Validate the timezone
    try:
        tz = pytz.timezone(timezone_name)
        now = datetime.now(tz)
        print(f"✓ Valid timezone: {timezone_name}")
        print(f"Current time in {timezone_name}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"UTC offset: {now.strftime('%z')}")
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"✗ ERROR: Invalid timezone: {timezone_name}")
        print("Please use a valid timezone identifier.")

def list_common_timezones():
    """List some common timezone options"""
    print_header("COMMON TIMEZONE OPTIONS")
    
    common_zones = [
        ("Asia/Kolkata", "India"),
        ("America/New_York", "US Eastern"),
        ("America/Chicago", "US Central"),
        ("America/Denver", "US Mountain"),
        ("America/Los_Angeles", "US Pacific"),
        ("Europe/London", "United Kingdom"),
        ("Europe/Berlin", "Central Europe"),
        ("Europe/Paris", "France"),
        ("Asia/Tokyo", "Japan"),
        ("Asia/Singapore", "Singapore"),
        ("Australia/Sydney", "Eastern Australia")
    ]
    
    print("Here are some common timezone options you can use:")
    print("\nTimezone               Current Time             Region")
    print("-" * 70)
    
    for tz_name, region in common_zones:
        try:
            tz = pytz.timezone(tz_name)
            now = datetime.now(tz)
            time_str = now.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{tz_name:22} {time_str:24} {region}")
        except Exception:
            print(f"{tz_name:22} [Error getting time]      {region}")
    
    print("\nTo use one of these timezones, set in your .env file:")
    print('TIMEZONE=Asia/Kolkata  # Replace with your desired timezone')

def test_timestamp_conversion():
    """Test OpenWeather API timestamp conversion"""
    print_header("TIMESTAMP CONVERSION TEST")
    
    # Create a sample timestamp (current time in UTC)
    utc_timestamp = int(datetime.now(timezone.utc).timestamp())
    print(f"Sample UTC timestamp: {utc_timestamp}")
    
    # Get timezone from environment or use UTC
    timezone_name = os.getenv("TIMEZONE", "UTC")
    try:
        local_tz = pytz.timezone(timezone_name)
    except:
        print(f"Invalid timezone: {timezone_name}, using UTC")
        local_tz = pytz.UTC
    
    # Convert timestamp to datetime in UTC, then to local timezone
    dt_utc = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    dt_local = dt_utc.astimezone(local_tz)
    
    print(f"\nTimestamp converted to UTC time: {dt_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"UTC time converted to {local_tz.zone}: {dt_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Offset from UTC: {dt_local.strftime('%z')}")
    
    print("\nThis simulates how the weather server converts OpenWeather timestamps.")

def check_server_health(url="http://localhost:3001/health"):
    """Check the weather server health endpoint"""
    print_header("SERVER HEALTH CHECK")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✓ Server is running")
            print(f"\nServer timezone: {data['timezone']['name']}")
            print(f"Server time: {data['timezone']['formatted_time']}")
            print(f"UTC offset: {data['timezone']['offset']}")
            
            if 'env_setting' in data['timezone']:
                print(f"Environment setting: {data['timezone']['env_setting']}")
            
            if 'timezone_test' in data:
                print("\nTimestamp conversion test:")
                print(f"UTC timestamp: {data['timezone_test']['utc_timestamp']}")
                print(f"Converted time: {data['timezone_test']['converted_time']}")
        else:
            print(f"✗ Server returned status code: {response.status_code}")
    except requests.RequestException as e:
        print("✗ Could not connect to the weather server")
        print(f"  Error: {str(e)}")
        print("\nMake sure the server is running with:")
        print("  docker-compose up -d")

def main():
    parser = argparse.ArgumentParser(description="Weather Bot Timezone Debugging Tool")
    parser.add_argument("--server", default="http://localhost:3001/health", help="Server health endpoint URL")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument("--system", action="store_true", help="Check system timezone")
    parser.add_argument("--env", action="store_true", help="Check environment timezone")
    parser.add_argument("--list", action="store_true", help="List common timezones")
    parser.add_argument("--convert", action="store_true", help="Test timestamp conversion")
    parser.add_argument("--health", action="store_true", help="Check server health")
    
    args = parser.parse_args()
    
    # If no specific arguments, run all checks
    if not (args.system or args.env or args.list or args.convert or args.health):
        args.all = True
    
    print("Weather Bot Timezone Debugging Tool")
    print("----------------------------------")
    
    if args.all or args.system:
        check_system_timezone()
    
    if args.all or args.env:
        check_env_timezone()
    
    if args.all or args.list:
        list_common_timezones()
    
    if args.all or args.convert:
        test_timestamp_conversion()
    
    if args.all or args.health:
        check_server_health(args.server)
    
    print("\nFor more help, see TIMEZONE_HELP.md")

if __name__ == "__main__":
    main()
