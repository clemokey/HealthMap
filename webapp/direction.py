# Geospatial packages
import geopandas as gpd
import geopy
from geopy.geocoders import Nominatim
from shapely.geometry import Point
import folium
import openrouteservice
from openrouteservice import convert

# General utilities
import pandas as pd
import time
import datetime
import requests
from django.utils import timezone
from datetime import timedelta

# Define functions

#Deprecated: 
def gestart_location():
    """
    Retrieve the user's current approximate geographic location using IP-based geolocation from ipinfo.io.

    This function makes a GET request to the ipinfo.io API to fetch the client's IP information,
    then extracts latitude and longitude coordinates from the 'loc' field.

    Returns:
        tuple: A tuple containing (longitude, latitude) as floats representing the user's approximate location.

    Raises:
        requests.exceptions.RequestException: If the network request fails.

    Example:
        >>> lon, lat = gestart_location()
        >>> print(f"Longitude: {lon}, Latitude: {lat}")
    """    
    res = requests.get('https://ipinfo.io/json')
    res.raise_for_status()  # Optional: raise error on bad response
    
    data = res.json()
    lat, lon = map(float, data['loc'].split(','))
    return (lon, lat)

def geocode_address(address):
    """
    Geocode a given address string into geographic coordinates using Nominatim.

    Nominatim is a search engine for OpenStreetMap data:
    https://nominatim.org/

    Parameters:
        address (str): The address or place name to geocode.

    Returns:
        location (geopy.Location or None): Geopy Location object containing
            latitude, longitude, and address details if found;
            None if the address cannot be geocoded.
    
    Example:
        >>> location = geocode_address("Brandenburg Gate, Berlin")
        >>> print(location.latitude, location.longitude)
    """
    # Initialize Nominatim geocoder (OpenStreetMap)
    geolocator = Nominatim(user_agent="healthmap")
    
    # Add delay to avoid overloading the geocoder
    time.sleep(1)
    
    # Geocode
    location = geolocator.geocode(address)
    
    # Show result
    if location:
        return location
    else:
        return "Address not found."

def get_route(start_coords, end_coords, profile='driving-car'):
    """
    Request route directions from OpenRouteService API between start and end coordinates.

    OpenRouteService (ORS) provides routing and geospatial services:
    https://openrouteservice.org/

    Parameters:
        client (openrouteservice.Client): An initialized OpenRouteService client with API key.
        start_coords (tuple): Tuple of (longitude, latitude) for the starting point.
        end_coords (tuple): Tuple of (longitude, latitude) for the destination.
        profile (str): Travel mode profile (e.g., 'driving-car', 'cycling-regular', 'foot-walking').

    Returns:
        route (dict): GeoJSON dictionary containing route geometry, instructions,
            distance, duration, and bounding box.
    
    Example:
        >>> route = get_route((13.388860, 52.517037), (13.397634, 52.529407))
        >>> print(route['features'][0]['properties']['summary'])
    """
    # Initialize the ORS client with your API key
    client = openrouteservice.Client(key='5b3ce3597851110001cf62480018545e2d1c4abeb960569d15ecb878')

    route = client.directions(
        coordinates=[start_coords, end_coords],
        profile=profile,
        format='geojson',
        instructions=True
    )
    return route

def create_route_map(route, start_coords, end_coords, zoom_start=13):
    """
    Create an interactive map displaying a route with start and end markers using Folium.

    Folium is a Python library for interactive leaflet maps:
    https://python-visualization.github.io/folium/

    Parameters:
        route_geojson (dict): GeoJSON dictionary representing the route geometry.
        start_coords (tuple): Tuple of (latitude, longitude) for the start point.
        end_coords (tuple): Tuple of (latitude, longitude) for the end point.
        zoom_start (int, optional): Initial zoom level for the map. Default is 13.

    Returns:
        folium.Map: Folium map object with the route and markers added.
    
    Example:
        >>> m = create_route_map(route, (52.517037, 13.388860), (52.529407, 13.397634))
        >>> m.save("route_map.html")
    """
    # Extract route bounding box: [min_lon, min_lat, max_lon, max_lat]
    bbox = route['features'][0]['bbox']
    
    # Create map centered around bbox center (optional for initialization)
    m = folium.Map(location=[(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2],
                   zoom_start=13)
    # Add the route to the map
    style = {
        "color": "blue",
        "weight": 6,      # line thickness
        "opacity": 0.8
    }

    folium.GeoJson(
        route,
        name="Route",
        style_function=lambda x: style
    ).add_to(m)
    
    # Add start and end markers
    folium.CircleMarker(
        location=start_coords[::-1],
        radius=8,
        color='white',
        weight=3,
        fill=True,
        fill_color='blue',
        fill_opacity=1,
        tooltip="Start"
    ).add_to(m)
    folium.Marker(location=end_coords[::-1], tooltip="Destination").add_to(m)
    
    # Fit map to route bounds
    m.fit_bounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]])  # [[min_lat, min_lon], [max_lat, max_lon]]
    
    #return embeddable HTML representation of the map
    return m._repr_html_()

def process(start, destination):
    def normalize_location(value):
        value = value.strip()
        # If it's a coordinate string like "lon, lat"
        if "," in value:
            try:
                lon, lat = map(float, value.split(","))
                return (lon, lat)
            except ValueError:
                pass  # Not valid numbers, treat as address
        
        # Otherwise assume it's an address string
        result = geocode_address(value)  # Should return an object with .longitude and .latitude
        return (result.longitude, result.latitude)

    start_coords = normalize_location(start)
    end_coords = normalize_location(destination)
    
    # Get the route 
    route = get_route(start_coords, end_coords)

    # get ETA
    summary = route['features'][0]['properties']['summary']
    distance_km = summary['distance'] / 1000
    duration_sec = summary['duration']

    eta = timezone.now() + timedelta(seconds=duration_sec)
    if eta.date() == timezone.now().date():
        eta_str = eta.strftime("%I:%M %p").lstrip("0") + " today"
    else:
        eta_str = eta.strftime("%I:%M %p").lstrip("0") + " tomorrow"

    duration = f"{duration_sec//3600} hr {(duration_sec%3600)//60} min" if duration_sec>=3600 else f"{(duration_sec%3600)//60} min"

    # Return both route map and directions as a dictionary. 
    return {
        "map": create_route_map(route, start_coords, end_coords),
        "instructions": route.get('features', [{}])[0].get('properties', {}).get('segments', [{}])[0].get('steps', []),
        "eta": eta_str,
        "duration": duration,
        "distance_km": f"{distance_km:.2f} km",
    }
   