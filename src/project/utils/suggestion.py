from geopy import Nominatim

weights = {"bias": 0, "industry": 0, "round": 0, "location": 1, "exits": 0}

pass_score = 0.4

geolocator = Nominatim(user_agent="src")


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
        geocoded_location = geolocator.geocode(location)
        if geocoded_location:
            return f"{geocoded_location.latitude},{geocoded_location.longitude}"  # type: ignore
        else:
            return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None
