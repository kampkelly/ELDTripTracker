import polyline
from django.contrib.gis.geos import LineString, Point


class Distance:
    def get_point_at_distance(self, route_polyline, target_distance_miles):
        """Find point along route at specified distance from start"""
        accumulated = 0.0
        route_geometry = LineString(polyline.decode(route_polyline, 5))
        coords = route_geometry.coords
        target_distance_deg = target_distance_miles / 69.047  # Convert to degrees

        for i in range(len(coords) - 1):
            start = Point(coords[i][0], coords[i][1])
            end = Point(coords[i + 1][0], coords[i + 1][1])
            segment_length = start.distance(end)

            if accumulated + segment_length >= target_distance_deg:
                fraction = (target_distance_deg - accumulated) / segment_length
                dx = end.x - start.x
                dy = end.y - start.y
                return Point(
                    start.x + fraction * dx, start.y + fraction * dy, srid=4326
                )
            accumulated += segment_length

        return Point(coords[-1][0], coords[-1][1], srid=4326)

    def interpolate_point(self, route_geometry, fraction):
        """Precise point interpolation along route geometry using Shapely's interpolate."""
        line_string = route_geometry
        if fraction < 0 or fraction > 1:
            raise ValueError("Fraction must be between 0 and 1")

        total_length = line_string.length
        target_length = total_length * fraction

        interpolated_point = line_string.interpolate(target_length)

        # returns longitude, latitude
        return Point(interpolated_point.y, interpolated_point.x, srid=4326)
