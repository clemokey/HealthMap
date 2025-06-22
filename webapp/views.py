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
        start = request.POST.get("start")
        destination = request.POST.get("destination")

        if not start or not destination:
            return render(request, "webapp/index.html", {
                "app_name": app_name,
                "subtitle": subtitle,
                "error": "Please enter both start and destination addresses.",
                "instructions": "Enter start and destination addresses to get directions and route on the map.",
                "map": generate_default_map()  # still show a map even on error
            })
        
        # Process the addresses to get instructions and map view
        processed_data = process(start, destination)
        instructions = processed_data.get("instructions", "No instructions available.")
        mapview = processed_data.get("map", generate_default_map())

        context = {
            "app_name": app_name,
            "subtitle": subtitle,
            "instructions": instructions,
            "map": mapview,
            "start": start,
            "destination": destination
        }
        return render(request, "webapp/index.html", context)

    # Default GET request — show blank/default map
    return render(request, "webapp/index.html", {
        "app_name": app_name,
        "subtitle": subtitle,
        "instructions": "Enter start and destination addresses to get directions and route on the map.",
        "map": generate_default_map()
    })


def generate_default_map():
    import folium
    # Set to your preferred initial view
    m = folium.Map(location=[47.811195, 13.033229], zoom_start=12)
    return m._repr_html_()