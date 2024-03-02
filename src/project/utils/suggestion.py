import os

import googlemaps

from .typesense_helpers.typesense_search import search

gmaps = googlemaps.Client(key=os.getenv("_GOOGLE_MAPS_API_KEY"))


WEIGHTS = {"bias": 0.3, "industry": 0.25, "round": 0.07, "location": 0.25, "exits": 0.07, "completeness": 0.06}


def check_weights(weights: dict[str, float]) -> None:
    if sum(weights.values()) != 1.0:
        print("!!! The weights must sum to 1.0 !!!")


def geocode_location(location: str, skip_gcloud: bool = False) -> dict[str, str] | None:
    raise Exception("Sent an event")
    if not location:
        return {"coordinates": "", "country_name": ""}
    print(f"Searching Typesense: {location}")
    try:
        search_lookup = search("cities", q=location, query_by="city, city_ascii, country, admin_name")
        if search_lookup and int(search_lookup.get("found", "0")) > 0:
            results = search_lookup.get("hits", [])
            first_result = results[0].get("document")
            coordinates = f"{first_result.get('latitude')},{first_result.get('longitude')}"
            country_name = first_result.get("country")
            print(f"Typesense search results: {coordinates}, {country_name}")
            return {"coordinates": coordinates, "country_name": country_name}
        else:
            print("No search results found")
    except Exception as e:
        print(f"Search error: {e}")
        print("Attempting to use Google Maps API for geocoding")

    if skip_gcloud:
        print("Skipping Google Maps API")
        return None

    print(f"Using Google Maps API for geocoding: {location}")
    try:
        geocoded_location = gmaps.geocode(location)  # type: ignore
        if geocoded_location:
            coordinates = f"{geocoded_location[0].get('geometry').get('location').get('lat')},{geocoded_location[0].get('geometry').get('location').get('lng')}"
            for item in geocoded_location[0].get("address_components"):
                if item.get("types")[0] == "country":
                    country_name = item.get("long_name")
                    break
            print(f"Geocoded location: {coordinates}, {country_name}")
            return {"coordinates": coordinates, "country_name": country_name}  # type: ignore
        else:
            print("No geocoded location found")
            return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None
