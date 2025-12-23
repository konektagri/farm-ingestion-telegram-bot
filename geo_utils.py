import json
from shapely.geometry import shape, Point

def get_province_from_location(lat, lon, geojson_path="CambodiaProvinceBoundaries.geojson"):
    """
    Returns the province name for a given latitude and longitude using the provided GeoJSON file.
    """
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
    point = Point(lon, lat)  # Note: GeoJSON uses (lon, lat)
    for feature in geojson['features']:
        polygon = shape(feature['geometry'])
        if polygon.contains(point):
            return feature['properties'].get('ADM1_EN', None)
    return None
