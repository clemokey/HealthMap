# Geospatial packages
import geopandas as gpd
import geopy
import os
from geopy.geocoders import Nominatim
from shapely.geometry import Point
import folium
from folium import plugins
from folium.plugins import MarkerCluster
import openrouteservice
from openrouteservice import convert
import requests

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
    # load health data
    URL = "https://bamideleoke.dev/assets/health.json"

    # Fetch JSON from URL
    resp = requests.get(URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # Handle FeatureCollection vs list
    features = data["features"] if isinstance(data, dict) and data.get("type") == "FeatureCollection" else data

    # Extract route bounding box: [min_lon, min_lat, max_lon, max_lat]
    bbox = route['features'][0]['bbox']
    
    # Create map centered around bbox center (optional for initialization)
    m = folium.Map(location=[(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2], zoom_start=13)

    # add basemaps
    folium.TileLayer(
        'CartoDB positron', name='Carto Light (Positron)', show=True, control=True
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='&copy; Esri & contributors',
        name='Esri World Imagery',
        overlay=False, show=False, control=True
    ).add_to(m)

    # Add the route to the map as a polyline with arrows
    coords = route["features"][0]["geometry"]["coordinates"]
    coords_latlng = [(lat, lon) for lon, lat in coords]

    # Outline (thicker, drawn first)
    polyline1 = folium.PolyLine(
        coords_latlng,
        color="#05458F",
        weight=12
    ).add_to(m)

    # Main route (thinner, drawn on top)
    polyline = folium.PolyLine(
        coords_latlng,
        color="#237BDF",
        weight=8,
    ).add_to(m)

    # Add arrows (> every ~100px along line)
    plugins.PolyLineTextPath(
        polyline,
        "          >          ",
        repeat=True,
        offset=6,
        attributes={"font-size": "14", "fill": "white", "font-weight": "bold"}
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

    
    AMENITY_COLOR = {'pharmacy': '#af6745', 'health_centre': '#da0be4', 'dentist': "#2b800f", 'doctors': '#8414e0', 'veterinary': '#b41483', 'social_facility': '#49902c', 'nursing_home': '#e985b6', 'clinic': "#e20171", 'hospital': '#ed9166'}
    DEFAULT_COLOR = "#666666"

    cluster = MarkerCluster(
        name="Health Facilities", 
        spiderfyOnMaxZoom=True,
        showCoverageOnHover=False
    ).add_to(m)

    for feat in features:
        lon, lat = [round(c, 6) for c in feat["geometry"]["coordinates"][:2]]
        props = feat.get("properties", {})
        amenity = (props.get("amenity") or "").lower()
        color = AMENITY_COLOR.get(amenity, DEFAULT_COLOR)

        name = props.get("name", "Unknown")
        addr = ", ".join(filter(None, [
            props.get("addr_street"),
            props.get("addr_housenumber"),
            props.get("addr_postcode"),
            props.get("addr_city"),
        ]))

        popup_html = f"""
            <div style="font-family:Arial, sans-serif; border-radius:12px;">
                <div style="background:{color}; color:white; border-top-radius:12px; padding:8px 12px; font-size:14px;
                            font-weight:bold; text-align:center; margin:0 !important">
                    {name}
                </div>

                <!-- Body -->
                <div style="padding:10px 12px; font-size:13px; color:#333; line-height:1.4;">
                    <b>Amenity:</b> {amenity or 'N/A'}<br>
                    {addr if addr else ''}<br>
                    {f'<b>Opening hours:</b> {props.get("opening_hours")}' if props.get("opening_hours") else ''}
                    {f'<br><a href="{props.get("website")}" target="_blank" style="color:{color};text-decoration:none;">🌐 Website</a>' if props.get("website") else ''}
                </div>

                <!-- Footer -->
                <div style="padding:10px; text-align:center; background:#f9f9f9; border-bottom-radius:12px; border-top:1px solid #eee;">
                    <button onclick="setDestination({lon}, {lat})"
                        style="background:{color}; color:white; border:none; font-size:13px;
                            padding:5px 10px; font-size: small; border-radius:5px; cursor:pointer;
                            box-shadow:0 2px 4px rgba(0,0,0,.2);">
                        Navigate Here
                    </button>
                </div>
            </div>
        """


        folium.CircleMarker(
            [lat, lon],
            radius=6,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.9
        ).add_to(cluster).add_child(folium.Popup(popup_html, max_width=200))

    # Legend (unchanged)
    legend_items = "".join(
        f'<div><span class="swatch" style="background:{col}"></span>{key.title()}</div>'
        for key, col in AMENITY_COLOR.items()
    )
    legend_html = f"""
    <style>
    .legend-box {{
    position: absolute; bottom: 16px; left: 16px; z-index: 9999;
    background: white; padding: 10px 12px; border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,.15); font: 12px/1.2 Arial, sans-serif;
    }}
    .legend-box .title {{ font-weight: 700; margin-bottom: 6px; }}
    .legend-box .swatch {{
    display:inline-block; width:12px; height:12px; border-radius:50%;
    margin-right:8px; vertical-align:middle; border:1px solid rgba(0,0,0,.2);
    }}
    .legend-box div {{ margin: 4px 0; white-space: nowrap; }}
    </style>
    <div class="legend-box">
    <div class="title">Legend</div>
    {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    js = """
    <script>
    function setDestination(lat, lng) {
        var field = parent.document.getElementById("destination");
        if (field) {
            field.value = lat + "," + lng;
            field.focus();
        } else {
            alert("Destination field not found!");
        }
    }
    </script>
    """
    m.get_root().html.add_child(folium.Element(js))

    # Toggle UI
    folium.LayerControl(position='topright', collapsed=True).add_to(m)

    #return embeddable HTML representation of the map
    return m._repr_html_()

def generate_default_map():
    # Create a default map centered at a specific location with the health facilities layer
    # Set to your preferred initial view
    # load health data
    URL = "https://bamideleoke.dev/assets/health.json"

    # Fetch JSON from URL
    resp = requests.get(URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # Handle FeatureCollection vs list
    features = data["features"] if isinstance(data, dict) and data.get("type") == "FeatureCollection" else data
    
    # Create map centered around bbox center (optional for initialization)
    m = folium.Map(location=[47.811195, 13.033229], zoom_start=13)

    # add basemaps
    folium.TileLayer(
        'CartoDB positron', name='Carto Light (Positron)', show=True, control=True
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='&copy; Esri & contributors',
        name='Esri World Imagery',
        overlay=False, show=False, control=True
    ).add_to(m)

    AMENITY_COLOR = {'pharmacy': '#af6745', 'health_centre': '#da0be4', 'dentist': "#2b800f", 'doctors': '#8414e0', 'veterinary': '#b41483', 'social_facility': '#49902c', 'nursing_home': '#e985b6', 'clinic': "#e20171", 'hospital': '#ed9166'}
    DEFAULT_COLOR = "#666666"

    cluster = MarkerCluster(
        name="Health Facilities", 
        spiderfyOnMaxZoom=True,
        showCoverageOnHover=False
    ).add_to(m)

    for feat in features:
        lon, lat = [round(c, 6) for c in feat["geometry"]["coordinates"][:2]]
        props = feat.get("properties", {})
        amenity = (props.get("amenity") or "").lower()
        color = AMENITY_COLOR.get(amenity, DEFAULT_COLOR)

        name = props.get("name", "Unknown")
        addr = ", ".join(filter(None, [
            props.get("addr_street"),
            props.get("addr_housenumber"),
            props.get("addr_postcode"),
            props.get("addr_city"),
        ]))

        popup_html = f"""
            <div style="font-family:Arial, sans-serif; border-radius:12px;">
                <div style="background:{color}; color:white; border-top-radius:12px; padding:8px 12px; font-size:14px;
                            font-weight:bold; text-align:center; margin:0 !important">
                    {name}
                </div>

                <!-- Body -->
                <div style="padding:10px 12px; font-size:13px; color:#333; line-height:1.4;">
                    <b>Amenity:</b> {amenity or 'N/A'}<br>
                    {addr if addr else ''}<br>
                    {f'<b>Opening hours:</b> {props.get("opening_hours")}' if props.get("opening_hours") else ''}
                    {f'<br><a href="{props.get("website")}" target="_blank" style="color:{color};text-decoration:none;">🌐 Website</a>' if props.get("website") else ''}
                </div>

                <!-- Footer -->
                <div style="padding:10px; text-align:center; background:#f9f9f9; border-bottom-radius:12px; border-top:1px solid #eee;">
                    <button onclick="setDestination({lon}, {lat})"
                        style="background:{color}; color:white; border:none; font-size:13px;
                            padding:5px 10px; font-size: small; border-radius:5px; cursor:pointer;
                            box-shadow:0 2px 4px rgba(0,0,0,.2);">
                        Navigate Here
                    </button>
                </div>
            </div>
        """


        folium.CircleMarker(
            [lat, lon],
            radius=6,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.9
        ).add_to(cluster).add_child(folium.Popup(popup_html, max_width=200))

    # Legend (unchanged)
    legend_items = "".join(
        f'<div><span class="swatch" style="background:{col}"></span>{key.title()}</div>'
        for key, col in AMENITY_COLOR.items()
    )
    legend_html = f"""
    <style>
    .legend-box {{
    position: absolute; bottom: 16px; left: 16px; z-index: 9999;
    background: white; padding: 10px 12px; border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,.15); font: 12px/1.2 Arial, sans-serif;
    }}
    .legend-box .title {{ font-weight: 700; margin-bottom: 6px; }}
    .legend-box .swatch {{
    display:inline-block; width:12px; height:12px; border-radius:50%;
    margin-right:8px; vertical-align:middle; border:1px solid rgba(0,0,0,.2);
    }}
    .legend-box div {{ margin: 4px 0; white-space: nowrap; }}
    </style>
    <div class="legend-box">
    <div class="title">Legend</div>
    {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    js = """
    <script>
    function setDestination(lat, lng) {
        var field = parent.document.getElementById("destination");
        if (field) {
            field.value = lat + "," + lng;
            field.focus();
        } else {
            alert("Destination field not found!");
        }
    }
    </script>
    """
    m.get_root().html.add_child(folium.Element(js))

    # Toggle UI
    folium.LayerControl(position='topright', collapsed=True).add_to(m)

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
   