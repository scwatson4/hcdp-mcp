"""Shared constants and helpers for HCDP MCP tools."""

import math

ISLAND_EXTENTS = {
    "oahu": "oa",
    "big_island": "bi",
    "maui": "mn",
    "kauai": "ka",
    "molokai": "mn",
    "lanai": "mn",
    "statewide": "statewide"
}

CITY_LOCATIONS = {
    # Main Hawaiian Islands
    "honolulu": {"lat": 21.3069, "lng": -157.8583, "island": "oahu"},
    "hilo": {"lat": 19.7241, "lng": -155.0868, "island": "big_island"},
    "kona": {"lat": 19.6393, "lng": -155.9969, "island": "big_island"},
    "kahului": {"lat": 20.8893, "lng": -156.4729, "island": "maui"},
    "lihue": {"lat": 21.9811, "lng": -159.3711, "island": "kauai"},
    "kaunakakai": {"lat": 21.0905, "lng": -157.0226, "island": "molokai"},
    "lanai_city": {"lat": 20.8264, "lng": -156.9182, "island": "lanai"},
    # American Samoa
    "pago_pago": {"lat": -14.2794, "lng": -170.7006, "island": "tutuila"}
}

ISLAND_REPRESENTATIVE_POINTS = {
    "oahu": {
        "Honolulu (South)": {"lat": 21.3069, "lng": -157.8583},
        "Kaneohe (Windward)": {"lat": 21.4111, "lng": -157.7967},
        "Kapolei (Leeward)": {"lat": 21.3358, "lng": -158.0561},
        "Wahiawa (Central)": {"lat": 21.5028, "lng": -158.0236},
        "North Shore": {"lat": 21.5956, "lng": -158.1070}
    },
    "big_island": {
        "Hilo (East/Wet)": {"lat": 19.7241, "lng": -155.0868},
        "Kona (West/Dry)": {"lat": 19.6393, "lng": -155.9969},
        "Waimea (Upcountry)": {"lat": 20.0201, "lng": -155.6677},
        "Volcano (Highland/Wet)": {"lat": 19.4315, "lng": -155.2323},
        "South Point": {"lat": 18.9136, "lng": -155.6793}
    },
    "maui": {
        "Kahului (Central)": {"lat": 20.8893, "lng": -156.4729},
        "Hana (East/Wet)": {"lat": 20.7575, "lng": -155.9884},
        "Lahaina (West/Dry)": {"lat": 20.8783, "lng": -156.6825},
        "Kula (Upcountry)": {"lat": 20.7922, "lng": -156.3267}
    },
    "kauai": {
        "Lihue (East)": {"lat": 21.9811, "lng": -159.3711},
        "Poipu (South)": {"lat": 21.8817, "lng": -159.4580},
        "Princeville (North)": {"lat": 22.2201, "lng": -159.4831},
        "Waimea (West)": {"lat": 21.9568, "lng": -159.6698},
        "Kokee (Mountain)": {"lat": 22.1264, "lng": -159.6467}
    },
    "molokai": {
        "Kaunakakai (South)": {"lat": 21.0905, "lng": -157.0226},
        "Kualapuu (Central)": {"lat": 21.1611, "lng": -157.0683},
        "Halawa (East)": {"lat": 21.1578, "lng": -156.7442}
    },
    "lanai": {
        "Lanai City": {"lat": 20.8264, "lng": -156.9182},
        "Manele (South)": {"lat": 20.7389, "lng": -156.8886}
    },
    "statewide": {
        "Honolulu (Oahu)": {"lat": 21.3069, "lng": -157.8583},
        "Hilo (Big Island)": {"lat": 19.7241, "lng": -155.0868},
        "Kahului (Maui)": {"lat": 20.8893, "lng": -156.4729},
        "Lihue (Kauai)": {"lat": 21.9811, "lng": -159.3711}
    }
}

ISLAND_BOUNDS = {
    "oahu": (21.2, 21.8, -158.3, -157.6),
    "big_island": (18.9, 20.3, -156.1, -154.8),
    "maui": (20.5, 21.1, -156.7, -155.9),
    "kauai": (21.8, 22.3, -159.8, -159.2),
    "molokai": (21.0, 21.3, -157.3, -156.7),
    "lanai": (20.7, 21.0, -157.0, -156.8)
}


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate Haversine distance between two points in km."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
