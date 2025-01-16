from django.shortcuts import render
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import requests

def geocode_location(location_name):
    """
    Geocode a location name to latitude and longitude using Open-Meteo geocoding API.
    """
    geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": location_name}
    response = requests.get(geocode_url, params=params)
    if response.status_code == 200 and response.json().get("results"):
        result = response.json()["results"][0]
        return result["latitude"], result["longitude"]
    return None, None

def weather_archive(request):
    weather_data = None
    error_message = None

    if request.method == "POST":
        location_name = request.POST.get("location_name", "")
        start_date = request.POST.get("start_date", "1949-01-01")
        end_date = request.POST.get("end_date", "1949-12-31")

        # Geocode the location
        latitude, longitude = geocode_location(location_name)
        if latitude is None or longitude is None:
            error_message = f"Could not find coordinates for location '{location_name}'."
        else:
            # Setup Open-Meteo API client with cache and retry
            cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
            retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
            openmeteo = openmeteo_requests.Client(session=retry_session)

            # Request parameters for daily data
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": [
                    "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
                    "apparent_temperature_max", "apparent_temperature_min", "apparent_temperature_mean",
                    "daylight_duration", "precipitation_sum", "rain_sum", "snowfall_sum",
                    "precipitation_hours", "wind_speed_10m_max", "wind_gusts_10m_max",
                    "wind_direction_10m_dominant", "shortwave_radiation_sum"
                ],
            }

            # Fetch data from API
            responses = openmeteo.weather_api(url, params=params)
            response = responses[0]

            # Process daily data
            daily = response.Daily()
            daily_data = {
                "date": pd.date_range(
                    start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                    end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=daily.Interval()),
                    inclusive="left"
                ),
                "temperature_2m_max": daily.Variables(0).ValuesAsNumpy(),
                "temperature_2m_min": daily.Variables(1).ValuesAsNumpy(),
                "temperature_2m_mean": daily.Variables(2).ValuesAsNumpy(),
                "apparent_temperature_max": daily.Variables(3).ValuesAsNumpy(),
                "apparent_temperature_min": daily.Variables(4).ValuesAsNumpy(),
                "apparent_temperature_mean": daily.Variables(5).ValuesAsNumpy(),
                "daylight_duration": daily.Variables(6).ValuesAsNumpy(),
                "precipitation_sum": daily.Variables(7).ValuesAsNumpy(),
                "rain_sum": daily.Variables(8).ValuesAsNumpy(),
                "snowfall_sum": daily.Variables(9).ValuesAsNumpy(),
                "precipitation_hours": daily.Variables(10).ValuesAsNumpy(),
                "wind_speed_10m_max": daily.Variables(11).ValuesAsNumpy(),
                "wind_gusts_10m_max": daily.Variables(12).ValuesAsNumpy(),
                "wind_direction_10m_dominant": daily.Variables(13).ValuesAsNumpy(),
                "shortwave_radiation_sum": daily.Variables(14).ValuesAsNumpy(),
            }

            # Convert to DataFrame for rendering in HTML
            weather_data = pd.DataFrame(daily_data).to_dict(orient="records")

    return render(request, "weather_archive.html", {
        "weather_data": weather_data,
        "error_message": error_message,
    })
