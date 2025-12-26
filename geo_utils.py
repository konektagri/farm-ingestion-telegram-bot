"""Geospatial utilities for province detection from coordinates."""
import json
import logging
from typing import Optional, List, Tuple
from shapely.geometry import shape, Point
from shapely.prepared import prep

from config import GEOJSON_PATH

logger = logging.getLogger(__name__)

# Cache for prepared geometries with province names
_province_geometries: List[Tuple[any, str]] = []
_geometries_loaded: bool = False


def _load_geojson() -> None:
    """Load and prepare geometries from GeoJSON file (lazy loaded on first use)."""
    global _province_geometries, _geometries_loaded
    
    if _geometries_loaded:
        return  # Already loaded
    
    try:
        with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
        
        for feature in geojson['features']:
            polygon = shape(feature['geometry'])
            prepared_polygon = prep(polygon)  # Faster containment checks
            province_name = feature['properties'].get('ADM1_EN', None)
            _province_geometries.append((prepared_polygon, province_name))
        
        _geometries_loaded = True
        logger.info(f"Loaded {len(_province_geometries)} province boundaries from GeoJSON")
    except Exception as e:
        logger.error(f"Failed to load GeoJSON file: {e}")
        raise


def get_province_from_location(lat: float, lon: float) -> Optional[str]:
    """
    Returns the province name for a given latitude and longitude.
    
    Uses lazy loading - GeoJSON is loaded on first access.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
    
    Returns:
        Province name or None if not found
    """
    # Lazy load on first access
    if not _geometries_loaded:
        _load_geojson()
    
    point = Point(lon, lat)  # Note: GeoJSON uses (lon, lat)
    
    for prepared_polygon, province_name in _province_geometries:
        if prepared_polygon.contains(point):
            return province_name
    
    return None

