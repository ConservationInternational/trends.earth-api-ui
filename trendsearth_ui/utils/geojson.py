"""GeoJSON utilities for map functionality."""

import json

from dash import html
import dash_leaflet as dl

from ..config import DEFAULT_MAP_TILE_PROVIDER, MAP_TILE_PROVIDERS


def ensure_geojson_feature(geojson_data):
    """Ensure the geojson data is a proper GeoJSON Feature.

    If it's a bare geometry (has type and coordinates), wrap it as a Feature.
    If it's already a Feature or FeatureCollection, return as-is.
    """
    if not isinstance(geojson_data, dict):
        return geojson_data

    geom_types = {"Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"}

    # If it's already a Feature or FeatureCollection, return as-is
    if geojson_data.get("type") in {"Feature", "FeatureCollection"}:
        return geojson_data

    # If it's a bare geometry object, wrap it as a Feature
    if geojson_data.get("type") in geom_types and "coordinates" in geojson_data:
        return {"type": "Feature", "geometry": geojson_data, "properties": {}}

    # Return as-is if we can't determine the type
    return geojson_data


def get_geometry_from_geojson(geojson_data):
    """Extract geometry from a GeoJSON object (Feature, FeatureCollection, or bare geometry)."""
    if not isinstance(geojson_data, dict):
        return None

    geom_types = {"Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"}

    # If it's a Feature, return the geometry
    if geojson_data.get("type") == "Feature":
        return geojson_data.get("geometry")

    # If it's a FeatureCollection, return the first feature's geometry
    if geojson_data.get("type") == "FeatureCollection":
        features = geojson_data.get("features", [])
        if features and len(features) > 0:
            return features[0].get("geometry")

    # If it's a bare geometry, return it directly
    if geojson_data.get("type") in geom_types:
        return geojson_data

    return None


def extract_coordinates_from_geometry(geometry):
    """Extract coordinate pairs from a GeoJSON geometry."""
    coords = []
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geom_type == "Point":
        if len(coordinates) >= 2:
            coords.append([coordinates[1], coordinates[0]])  # [lat, lon]
    elif geom_type == "LineString":
        for coord in coordinates:
            if len(coord) >= 2:
                coords.append([coord[1], coord[0]])  # [lat, lon]
    elif geom_type == "Polygon":
        for ring in coordinates:
            for coord in ring:
                if len(coord) >= 2:
                    coords.append([coord[1], coord[0]])  # [lat, lon]
    elif geom_type == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                for coord in ring:
                    if len(coord) >= 2:
                        coords.append([coord[1], coord[0]])  # [lat, lon]

    return coords


def create_map_from_geojsons(geojsons, exec_id):
    """Create a Leaflet map from geojsons data."""
    try:
        # Initialize map layers
        map_layers = []

        # Default center (will be updated based on geojsons)
        center = [0, 0]
        zoom = 2

        if isinstance(geojsons, list):
            all_coordinates = []

            for i, geojson in enumerate(geojsons):
                if isinstance(geojson, str):
                    try:
                        geojson_dict = json.loads(geojson)
                    except json.JSONDecodeError:
                        continue
                else:
                    geojson_dict = geojson

                if isinstance(geojson_dict, dict):
                    # Convert bare geometry to GeoJSON Feature if needed
                    feature_data = ensure_geojson_feature(geojson_dict)

                    # Add GeoJSON layer
                    layer = dl.GeoJSON(
                        data=feature_data,
                        id=f"geojson-{i}",
                        options={"style": {"color": "red", "weight": 2, "fillOpacity": 0.2}},
                        hoverStyle={"weight": 3, "color": "blue"},
                    )
                    map_layers.append(layer)

                    # Extract coordinates for centering
                    geometry = get_geometry_from_geojson(feature_data)
                    if geometry:
                        coords = extract_coordinates_from_geometry(geometry)
                        all_coordinates.extend(coords)

            # Calculate center from all coordinates
            if all_coordinates:
                center_lat = sum(coord[0] for coord in all_coordinates) / len(all_coordinates)
                center_lon = sum(coord[1] for coord in all_coordinates) / len(all_coordinates)
                center = [center_lat, center_lon]
                zoom = 10  # Reasonable zoom for showing the area

        elif isinstance(geojsons, (dict, str)):
            # Single geojson
            if isinstance(geojsons, str):
                try:
                    geojson_dict = json.loads(geojsons)
                except json.JSONDecodeError:
                    return [html.P("Could not parse GeoJSON data.")]
            else:
                geojson_dict = geojsons

            # Convert bare geometry to GeoJSON Feature if needed
            feature_data = ensure_geojson_feature(geojson_dict)

            layer = dl.GeoJSON(
                data=feature_data,
                id="geojson-0",
                options={"style": {"color": "red", "weight": 2, "fillOpacity": 0.2}},
                hoverStyle={"weight": 3, "color": "blue"},
            )
            map_layers.append(layer)

            # Extract coordinates for centering
            geometry = get_geometry_from_geojson(feature_data)
            if geometry:
                coords = extract_coordinates_from_geometry(geometry)
                if coords:
                    center_lat = sum(coord[0] for coord in coords) / len(coords)
                    center_lon = sum(coord[1] for coord in coords) / len(coords)
                    center = [center_lat, center_lon]
                    zoom = 10  # Create the map with English-only tile layer
        map_component = dl.Map(
            children=[
                get_tile_layer(),  # Uses configured English-only tile provider
                *map_layers,
            ],
            style={"width": "100%", "height": "600px"},
            center=center,
            zoom=zoom,
            id=f"map-{exec_id}",
        )

        # Create the minimap/locator map
        minimap_component = create_minimap(center, zoom, exec_id)

        # Return both the main map and the minimap in a container
        return [
            html.Div(
                children=[map_component, minimap_component],
                style={"position": "relative", "width": "100%", "height": "600px"},
            )
        ]

    except Exception as e:
        return [html.P(f"Error creating map: {str(e)}")]


def get_tile_layer(provider_name=None):
    """Get a configured tile layer for English-language maps.

    Args:
        provider_name (str, optional): Name of the tile provider to use.
                                     If None, uses DEFAULT_MAP_TILE_PROVIDER.

    Returns:
        dl.TileLayer: Configured tile layer component.
    """
    provider = provider_name or DEFAULT_MAP_TILE_PROVIDER

    if provider not in MAP_TILE_PROVIDERS:
        provider = DEFAULT_MAP_TILE_PROVIDER

    tile_config = MAP_TILE_PROVIDERS[provider]

    return dl.TileLayer(
        url=tile_config["url"],
        attribution=tile_config["attribution"],
        subdomains=tile_config.get("subdomains", ["a", "b", "c"]),
        maxZoom=tile_config.get("maxZoom", 18),
    )


def create_minimap(center, zoom, map_id):
    """Create a small overview/locator map.

    Args:
        center (list): [lat, lon] center coordinates for the main map
        zoom (int): Zoom level of the main map
        map_id (str): ID for the map container

    Returns:
        html.Div: Container with the minimap
    """
    # Calculate appropriate zoom level for overview (typically 3-4 levels lower)
    overview_zoom = max(1, zoom - 4)
    # Create a simple polygon to show the approximate area of the main map
    # Calculate rough bounds based on zoom level (this is approximate)
    lat_offset = 0.5 * (2 ** (10 - zoom))  # Rough calculation
    lon_offset = 0.7 * (2 ** (10 - zoom))  # Rough calculation

    # Create a polygon showing the main map's approximate bounds
    bounds_polygon = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [center[1] - lon_offset, center[0] - lat_offset],  # Southwest [lon, lat]
                    [center[1] + lon_offset, center[0] - lat_offset],  # Southeast [lon, lat]
                    [center[1] + lon_offset, center[0] + lat_offset],  # Northeast [lon, lat]
                    [center[1] - lon_offset, center[0] + lat_offset],  # Northwest [lon, lat]
                    [center[1] - lon_offset, center[0] - lat_offset],  # Close polygon [lon, lat]
                ]
            ],
        },
        "properties": {},
    }

    # Create a GeoJSON layer showing the main map's bounds
    bounds_layer = dl.GeoJSON(
        data=bounds_polygon,
        options={"style": {"color": "red", "weight": 2, "fillOpacity": 0.2, "fillColor": "red"}},
    )
    # Create the minimap with minimal interactions
    minimap = dl.Map(
        children=[
            get_tile_layer("carto_positron"),  # Use light tiles for overview
            bounds_layer,
        ],
        style={
            "width": "150px",
            "height": "100px",
            "position": "absolute",
            "top": "10px",
            "right": "10px",
            "zIndex": 1000,
            "border": "2px solid #333",
            "borderRadius": "4px",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.3)",
        },
        center=center,
        zoom=overview_zoom,
        id=f"minimap-{map_id}",
        # Disable most interactions on the minimap
        zoomControl=False,
        dragging=False,
    )

    return html.Div(
        children=[minimap], style={"position": "relative", "width": "0px", "height": "0px"}
    )
