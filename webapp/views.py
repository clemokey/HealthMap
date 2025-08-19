from django.shortcuts import render
from django.views import generic
from django.http import HttpResponse
from .direction import process
from django.apps import apps

# Create your views here.
def index(request):
    app_name = apps.get_app_config('webapp').verbose_name
    subtitle = apps.get_app_config('webapp').app_subtitle

    if request.method == "POST":
        start = request.POST.get("start", "").strip()
        destination = request.POST.get("destination", "").strip()

        if not start or not destination:
            # Missing input
            context = {
                "app_name": app_name,
                "subtitle": subtitle,
                "error": "Please enter both start and destination addresses.",
                "instructions": [],
                "instructions_message": "Enter start and destination addresses to get directions and route on the map.",
                "map": generate_default_map(),
                "start": start,
                "destination": destination,
            }
            return render(request, "webapp/index.html", context)

        try:
            # Process the addresses
            processed_data = process(start, destination)
            instructions = processed_data.get("instructions", [])
            mapview = processed_data.get("map", generate_default_map())
            eta = processed_data.get("eta", None)
            distance_km = processed_data.get("distance_km", 0)
            duration = processed_data.get("duration", "")

            context = {
                "app_name": app_name,
                "subtitle": subtitle,
                "eta": eta,
                "distance_km": distance_km,
                "duration": duration,
                "instructions": instructions,
                "map": mapview,
                "start": start,
                "destination": destination,
            }
        except Exception as e:
            # Invalid input or failed processing
            context = {
                "app_name": app_name,
                "subtitle": subtitle,
                "error": f"Invalid address or coordinates. Please check your input. {e}",
                "instructions": [],
                "instructions_messge": "Enter start and destination addresses to get directions and route on the map.",
                "map": generate_default_map(),
                "start": start,
                "destination": destination,
            }

        return render(request, "webapp/index.html", context)

    # GET request — show blank/default map
    context = {
        "app_name": app_name,
        "subtitle": subtitle,
        "instructions": [],
        "instructions_message": "Enter start and destination addresses to get directions and route on the map.",
        "map": generate_default_map(),
    }
    return render(request, "webapp/index.html", context)


def generate_default_map():
    import folium
    # Set to your preferred initial view
    m = folium.Map(location=[47.811195, 13.033229], zoom_start=12)
    return m._repr_html_()