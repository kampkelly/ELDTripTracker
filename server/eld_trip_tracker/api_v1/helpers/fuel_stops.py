from api_v1.helpers.distance import Distance
from api_v1.lib.logger import general_logger
from api_v1.lib.mapbox import MapBoxAPI


class FuelStop:
    def __init__(self):
        self.distance = Distance()
        self.mapbox_api = MapBoxAPI()

    def find_optimal_fuel_stop(self, route_geometry, max_distance):
        """Find best fuel station within search window using Mapbox"""
        try:
            # Get the ideal target point
            target_point = self.distance.get_point_at_distance(
                route_geometry, max_distance
            )

            data = self.mapbox_api.get_point_of_interest(
                "gas_station", target_point.y, target_point.x
            )

            stations = data.get("features", [])
            if stations:
                return stations[0], target_point
            else:
                return None, target_point

        except Exception as e:
            # replace with logger
            general_logger.error(f"Fuel station search failed: {str(e)}")
            raise e
