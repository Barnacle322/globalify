import os

import googlemaps

google_maps_secret = os.getenv("_GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=google_maps_secret)

weights = {"bias": 0.3, "industry": 0.25, "round": 0.1, "location": 0.25, "exits": 0.1}

pass_score = 0.51


def check_weights(weights):
    total_weight = sum(weights.values())
    try:
        if total_weight != 1.0:
            raise ValueError("The weights must sum to 1.0")
    except ValueError as e:
        print(e)


check_weights(weights)


def geocode_location(location):
    try:
        geocoded_location = gmaps.geocode(location)  # type: ignore
        if geocoded_location:
            return f"{geocoded_location[0].get('geometry').get('location').get('lat')},{geocoded_location[0].get('geometry').get('location').get('lng')}"
        else:
            return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None
