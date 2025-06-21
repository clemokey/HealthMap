from django.shortcuts import render
from django.views import generic
from django.http import HttpResponse
from .direction import process

# Index view for the webapp
def index(request):
    address = "Karl-Adrian-Straße 1, 5020 Salzburg, Austria"
    instructions = process(address, "instructions")
    mapview = process(address,)
    context = {
        "instructions": instructions,
        "map": mapview
    }
    return render(request, "webapp/index.html", context)