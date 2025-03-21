import os

import requests
from dotenv import load_dotenv

load_dotenv()

MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")

BASE_URL = "https://api.mapbox.com"


class MapBoxAPI:
    def __init__(self):
        pass

    def make_request(self, url, extra_params):
        params = {
            "access_token": MAPBOX_ACCESS_TOKEN,
        }
        if extra_params:
            params.update(extra_params)

        response = requests.get(f"{BASE_URL}/{url}", params=params)
        if response.status_code != 200:
            raise Exception("Failed to calculate route")

        data = response.json()

        return data

    # coords is a list of longitude, latitude
    def get_direction(self, coords, steps="true"):
        params = {
            "geometries": "polyline",
            "overview": "full",
            "steps": steps,
            "exclude": "toll,ferry",
            "annotations": "duration",
        }

        url = f"directions/v5/mapbox/driving/{coords}"

        data = self.make_request(url, params)

        return data

    def get_point_of_interest(self, poi_category, longitude, latitude):
        params = {
            "proximity": f"{longitude},{latitude}",
            "limit": 5,
            "time_deviation": 30,
            "sar_type": "isochrone",
        }
        url = f"search/searchbox/v1/category/{poi_category}"

        data = self.make_request(url, params)

        return data
