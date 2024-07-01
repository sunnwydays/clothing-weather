import sqlite3, requests, datetime, json

database = 'clothing_data.db'

with sqlite3.connect(database) as conn:
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ClothingWeather (
        Date DATE,
        Time INT,
        Location TEXT,
        WeatherData TEXT,
        ClothingData TEXT,
        SportsData TEXT,
        OtherData TEXT,
        ActivityData TEXT
    )
    ''')
    conn.commit()

# function to geocode city to get latitude and longitude
def geocode_city(city):
    geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=2&language=en"
    try:
        response = requests.get(geocode_url)
        response.raise_for_status()
        geocode_data = response.json()
        if 'results' not in geocode_data or not geocode_data['results']:
            raise ValueError('No results found for the specified city.')
        latitude = geocode_data['results'][0]['latitude']
        longitude = geocode_data['results'][0]['longitude']
        return (latitude, longitude)
    except requests.RequestException as e:
        print(f"Geocoding API request error: {e}")
        raise
    except ValueError as e:
        print(e)
        raise

# function to fetch weather data
def get_weather(location, hour):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={location[0]}&longitude={location[1]}&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,cloud_cover_low,visibility,et0_fao_evapotranspiration,wind_speed_10m,wind_direction_10m,wind_gusts_10m&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,daylight_duration,sunshine_duration,uv_index_max,shortwave_radiation_sum&timezone=auto&forecast_days=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()

        return {
            "temperature": weather_data['hourly']['temperature_2m'][hour],
            "humidity": weather_data['hourly']['relative_humidity_2m'][hour],
            "apparent_temperature": weather_data['hourly']['apparent_temperature'][hour],
            "precipitation_probability": weather_data['hourly']['precipitation_probability'][hour],
            "precipitation": weather_data['hourly']['precipitation'][hour],
            "weather_code": weather_data['hourly']['weather_code'][hour],
            "cloud_cover_low": weather_data['hourly']['cloud_cover_low'][hour],
            "visibility": weather_data['hourly']['visibility'][hour],
            "et0": weather_data['hourly']['et0_fao_evapotranspiration'][hour],
            "wind_speed": weather_data['hourly']['wind_speed_10m'][hour],
            "wind_direction": weather_data['hourly']['wind_direction_10m'][hour],
            "wind_gusts": weather_data['hourly']['wind_gusts_10m'][hour],
            "daily_max": weather_data['daily']['temperature_2m_max'][0],
            "daily_min": weather_data['daily']['temperature_2m_min'][0],
            "sunrise": weather_data['daily']['sunrise'][0].split("T")[1],
            "sunset": weather_data['daily']['sunset'][0].split("T")[1],
            "daylight_duration": weather_data['daily']['daylight_duration'][0],
            "sunshine_duration": weather_data['daily']['sunshine_duration'][0],
            "uv_index_max": weather_data['daily']['uv_index_max'][0],
            "shortwave_radiation_sum": weather_data['daily']['shortwave_radiation_sum'][0]
        }
    except requests.RequestException as e:
        print(f"Weather API request error: {e}")
        raise

weather_emojis = {
    0: "🌞",
    1: "🌤️",
    2: "⛅",
    3: "🌥️",
    45: "🌫️",
    48: "🌫️",
    51: "💧",
    52: "💧",
    53: "💧",
    54: "💧",
    55: "💧",
    56: "💧",
    57: "💧",
    61: "💧",
    63: "🌧️",
    65: "🌊",
    66: "☔",
    67: "☔",
    71: "❄️",
    73: "🌨️",
    75: "☃️",
    77: "🌨️",
    80: "🚿",
    81: "🚿",
    85: "🚿",
    86: "🚿",
    95: "⚡",
    96: "🌩️",
    97: "⛈️",
}

# function to add data to SQLite database
def add_data(date, time, location, weather, outerwear, bottoms, footwear, accessories, sports, activities, other_data=None, database=database):
    with sqlite3.connect(database) as conn:
        cursor = conn.cursor()
        # Convert dictionaries to JSON strings
        weather_json = json.dumps(weather)
        clothing_json = json.dumps({
            "outerwear": outerwear,
            "bottoms": bottoms,
            "footwear": footwear,
            "accessories": accessories,
        })
        sports_json = json.dumps(sports)
        activity_json = json.dumps(activities)
        cursor.execute('''
        INSERT INTO ClothingWeather (
                        Date, 
                        Time, 
                        Location, 
                        WeatherData,
                        ClothingData,
                        SportsData,
                        OtherData,
                        ActivityData
                    )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, time, location, weather_json, clothing_json, sports_json, other_data, activity_json))
        print("Data added successfully.")
        conn.commit()
    
def remove_last_entry(database=database):
    """
    Removes the last entry from the ClothingWeather table.

    Parameters:
    - database: str, the path to the SQLite database file.
    """
    with sqlite3.connect(database) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ClothingWeather WHERE rowid = (SELECT MAX(rowid) FROM ClothingWeather)")
        conn.commit()

# functions to get user input
def get_hour_input(remove_last_entry):
    while True:
        time = input("- Enter the hour (HH) [must be today] or leave blank for current hour: ")
        if time == "delete":
            remove_last_entry()
            exit()
        if not time:
            return int(datetime.datetime.now().strftime('%H'))
        try:
            time = int(time)
            if 0 <= time <= 23:
                return time
            print("Invalid hour. Must be between 0 and 23.")
        except ValueError:
            print("Invalid input. Must be an integer.")

def get_location_input():
    location_input = input("- Enter the location (City, Country) or leave blank for Markham: ")
    location = location_input if location_input else "Markham, Canada"
    return location

def get_clothing_input(options, prompt):
    while True:
        selection = input(f"- {prompt} ({', '.join(options.keys())}): ").strip()
        if not selection:
            match prompt:
                case "Bottoms":
                    options["athletic"] = True
                case "Footwear":
                    options["running"] = True
                case "Activity":
                    options["walking"] = True
                case _:
                    return
            return
        selected_items = [item.strip().lower() for item in selection.split(',')]
        for item in selected_items:
            if item not in options.keys():
                print(f"Invalid option '{item}'. Choose from the provided options.")
                break
            options[item] = True
        else:
            return

def get_sport_input(prompt):
    while True:
        suitable = input(f"- Suitable for {prompt} (Y/n): ").strip().lower()
        if not suitable or suitable == 'y':
            return True
        if suitable == 'n':
            return False        
        print("Invalid input. Must be 'y' or 'n'.")

# ask user for details
date = datetime.datetime.now().strftime('%Y-%m-%d')
time = get_hour_input(remove_last_entry)
location = get_location_input()
print("Fetching weather data...")

# Geocode
try:
    location_coords = geocode_city(location)
except Exception as e:
    print(f"Error: {e}")
    conn.close()
    exit()

# Fetch weather data
try:
    weather = get_weather(location_coords, time)
except Exception as e:
    print(f"Error fetching temperature: {e}")
    conn.close()
    exit()

print(f'''Weather on {date} at {time}:XX in {location}:
Temperature: {weather["temperature"]}°C
Apparent Temperature: {weather["apparent_temperature"]}°C
Precipitation Probability: {weather["precipitation_probability"]}%
Precipitation: {weather["precipitation"]}mm
Code: {weather["weather_code"]} {weather_emojis.get(weather["weather_code"], '❓')}
Low Cloud Cover: {weather["cloud_cover_low"]}%
Visibility: {weather["visibility"]} m
Wind Speed: {weather["wind_speed"]} m/s
''')

# clothing options
outerwear = {option: False for option in ["none", "thin sweater", "sweater", "windbreaker", "jacket", "heavy jacket"]}
bottoms = {option: False for option in ["athletic", "shorts", "sweatpants", "cold pants"]}
footwear = {option: False for option in ["running", "cold running", "boots"]}
accessories = {option: False for option in ["none", "sun sleeves", "sunglasses", "hat", "gloves", "scarf"]}

print("Select your clothing items (comma separated if multiple) or leave blank for first option.")
get_clothing_input(outerwear, "Outerwear")
get_clothing_input(bottoms, "Bottoms")
get_clothing_input(footwear, "Footwear")
get_clothing_input(accessories, "Accessories")

print("What activity were you doing?")
activities = {option: False for option in ["walking", "running", "frisbee", "cycling", "other"]}
get_clothing_input(activities, "Activity")

print("What sports would you play sports in this weather?")
sports = {}
sports['running'] = get_sport_input("running")
sports['frisbee'] = get_sport_input("frisbee")
sports['cycling'] = get_sport_input("cycling")

add_data(date, time, location, weather, outerwear, bottoms, footwear, accessories, sports, activities)

# print(f'''Weather on {date} at {time}:XX in {location}:
# Temperature: {weather["temperature"]}°C
# Humidity: {weather["humidity"]}%
# Apparent Temperature: {weather["apparent_temperature"]}°C
# Precipitation Probability: {weather["precipitation_probability"]}%
# Precipitation: {weather["precipitation"]}mm
# Code: {weather["weather_code"]} {weather_emojis.get(weather["weather_code"], '❓')}
# Low Cloud Cover: {weather["cloud_cover_low"]}%
# Visibility: {weather["visibility"]} m
# Reference Evapotranspiration: {weather["et0"]} mm
# Wind Speed: {weather["wind_speed"]} m/s
# Wind Direction: {weather["wind_direction"]}°
# Wind Gusts: {weather["wind_gusts"]} m/s
# Daily Max: {weather["daily_max"]}°C
# Daily Min: {weather["daily_min"]}°C
# Sunrise: {weather["sunrise"]}
# Sunset: {weather["sunset"]}
# Daylight Duration: {weather["daylight_duration"]} s
# Sunshine Duration: {weather["sunshine_duration"]} s
# UV Index Max: {weather["uv_index_max"]}
# Shortwave Radiation Sum: {weather["shortwave_radiation_sum"]} MJ/m²
# ''')

# update the json column
# UPDATE ClothingWeather
# SET SportsData = '{"running": true, "frisbee": false, "cycling": false}'
# WHERE date = '2024-06-20' and time = 11;