"""GeoJSON utilities for map functionality."""

import json
import logging

from dash import html
import dash_leaflet as dl

from ..config import DEFAULT_MAP_TILE_PROVIDER, MAP_TILE_PROVIDERS

logger = logging.getLogger(__name__)


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
        logger.debug("create_map_from_geojsons called with geojsons type: %s", type(geojsons))

        # Initialize map layers
        map_layers = []

        # Default center (will be updated based on geojsons)
        center = [0, 0]
        zoom = 2

        if isinstance(geojsons, list):
            logger.debug("Processing list of %d geojsons", len(geojsons))
            all_coordinates = []

            for i, geojson in enumerate(geojsons):
                if isinstance(geojson, str):
                    try:
                        geojson_dict = json.loads(geojson)
                    except json.JSONDecodeError:
                        logger.debug("Failed to parse JSON string at index %d", i)
                        continue
                else:
                    geojson_dict = geojson

                # Handle FeatureCollection case
                if (
                    isinstance(geojson_dict, dict)
                    and geojson_dict.get("type") == "FeatureCollection"
                ):
                    features = geojson_dict.get("features", [])
                    for j, feature in enumerate(features):
                        feature_data = ensure_geojson_feature(feature)
                        if feature_data:
                            # Add this feature as a separate layer
                            geometry = feature_data.get("geometry")

                            # Add GeoJSON layer
                            layer = dl.GeoJSON(
                                data=feature_data,
                                id=f"geojson-{exec_id}-{i}-{j}",
                                options={
                                    "style": {
                                        "color": "#FF0000",
                                        "weight": 5,
                                        "opacity": 1.0,
                                        "fillColor": "#FF0000",
                                        "fillOpacity": 0.5,
                                        "dashArray": None,
                                    }
                                },
                                hoverStyle={"weight": 8, "color": "#0000FF", "fillOpacity": 0.7},
                            )
                            map_layers.append(layer)

                            # Extract coordinates for centering
                            if geometry and geometry.get("type") in ["Polygon", "MultiPolygon"]:
                                extracted_coords = extract_coordinates_from_geometry(geometry)
                                all_coordinates.extend(extracted_coords)

                # Handle regular geometry or feature
                elif isinstance(geojson_dict, dict):
                    # Convert bare geometry to GeoJSON Feature if needed
                    feature_data = ensure_geojson_feature(geojson_dict)

                    if feature_data:
                        geometry = feature_data.get("geometry")

                        # Add GeoJSON layer (always red)
                        layer = dl.GeoJSON(
                            data=feature_data,
                            id=f"geojson-{exec_id}-{i}",
                            options={
                                "style": {
                                    "color": "#FF0000",
                                    "weight": 5,
                                    "opacity": 1.0,
                                    "fillColor": "#FF0000",
                                    "fillOpacity": 0.5,
                                    "dashArray": None,
                                }
                            },
                            hoverStyle={"weight": 8, "color": "#0000FF", "fillOpacity": 0.7},
                        )
                        map_layers.append(layer)

                        # Also try adding a Polygon component as fallback
                        if geometry and geometry.get("type") == "Polygon":
                            coords = geometry.get("coordinates", [])
                            if coords and len(coords) > 0:
                                # Convert coordinates to [lat, lon] format for Leaflet
                                polygon_positions = []
                                for ring in coords:
                                    ring_positions = [[coord[1], coord[0]] for coord in ring]
                                    polygon_positions.append(ring_positions)

                                polygon_layer = dl.Polygon(
                                    positions=polygon_positions,
                                    color="#FF0000",
                                    weight=5,
                                    opacity=1.0,
                                    fillColor="#FF0000",
                                    fillOpacity=0.5,
                                    children=[dl.Tooltip("Area of Interest")],
                                )
                                map_layers.append(polygon_layer)

                        # Extract coordinates for centering
                        if geometry and geometry.get("type") in ["Polygon", "MultiPolygon"]:
                            extracted_coords = extract_coordinates_from_geometry(geometry)
                            all_coordinates.extend(extracted_coords)

            # Calculate center and zoom from all coordinates
            if all_coordinates:
                center_lat = sum(coord[0] for coord in all_coordinates) / len(all_coordinates)
                center_lon = sum(coord[1] for coord in all_coordinates) / len(all_coordinates)
                center = [center_lat, center_lon]

                # Calculate bounds to determine appropriate zoom level
                min_lat = min(coord[0] for coord in all_coordinates)
                max_lat = max(coord[0] for coord in all_coordinates)
                min_lon = min(coord[1] for coord in all_coordinates)
                max_lon = max(coord[1] for coord in all_coordinates)

                # Calculate the longest edge
                lat_span = max_lat - min_lat
                lon_span = max_lon - min_lon
                max_span = max(lat_span, lon_span)

                # Calculate zoom so longest edge takes up half the map width
                # Improved zoom calculation for better regional viewing
                if max_span > 0:
                    # Use a more balanced approach for different area sizes
                    import math

                    # Define zoom levels based on span ranges
                    if max_span >= 10:  # Very large areas (countries/continents)
                        zoom = max(1, min(4, int(5 - math.log10(max_span))))
                    elif max_span >= 1:  # Large regions (states/provinces)
                        zoom = max(4, min(8, int(8 - math.log10(max_span * 10))))
                    elif max_span >= 0.1:  # Medium areas (cities/counties)
                        zoom = max(8, min(12, int(12 - math.log10(max_span * 100))))
                    else:  # Small areas (neighborhoods/buildings)
                        zoom = max(12, min(18, int(16 - math.log10(max_span * 1000))))
                else:
                    zoom = 8

                logger.debug("Calculated center from %d coordinates: %s", len(all_coordinates), center)
                logger.debug("Bounds: lat(%s, %s), lon(%s, %s)", min_lat, max_lat, min_lon, max_lon)
                logger.debug("Max span: %s, calculated zoom: %s", max_span, zoom)
            else:
                logger.debug("No coordinates found, using default center")

        elif isinstance(geojsons, (dict, str)):
            logger.debug("Processing single geojson")
            # Single geojson
            if isinstance(geojsons, str):
                try:
                    parsed_data = json.loads(geojsons)
                    logger.debug("Parsed single JSON string to %s", type(parsed_data))

                    # Check if the parsed string is actually a list
                    if isinstance(parsed_data, list):
                        logger.debug(
                            "Parsed string is actually a list, redirecting to list processing"
                        )
                        # Recursively call with the parsed list
                        return create_map_from_geojsons(parsed_data, exec_id)
                    else:
                        geojson_dict = parsed_data
                except json.JSONDecodeError:
                    logger.debug("Failed to parse single JSON string")
                    return [html.P("Could not parse GeoJSON data.")]
            else:
                geojson_dict = geojsons

            # Convert bare geometry to GeoJSON Feature if needed
            feature_data = ensure_geojson_feature(geojson_dict)
            logger.debug(
                "Created single feature data: %s",
                feature_data.get('type', 'unknown') if isinstance(feature_data, dict) else type(feature_data)
            )

            # Log the geometry type and coordinates for debugging
            geometry = feature_data.get("geometry")
            if geometry:
                logger.debug("Single geometry type: %s", geometry.get('type'))
                coords = geometry.get("coordinates", [])
                if coords:
                    logger.debug(
                        "Single first few coordinates: %s",
                        coords[:2] if isinstance(coords, list) else 'Not a list'
                    )

            layer = dl.GeoJSON(
                data=feature_data,
                id=f"geojson-{exec_id}-0",
                options={
                    "style": {
                        "color": "#FF0000",
                        "weight": 5,
                        "opacity": 1.0,
                        "fillColor": "#FF0000",
                        "fillOpacity": 0.5,
                        "dashArray": None,
                    }
                },
                hoverStyle={"weight": 8, "color": "#0000FF", "fillOpacity": 0.7},
            )
            map_layers.append(layer)
            logger.debug("Added single GeoJSON layer to map_layers")

            # Also try adding a Polygon component as fallback
            geometry = get_geometry_from_geojson(feature_data)
            if geometry and geometry.get("type") == "Polygon":
                coords = geometry.get("coordinates", [])
                if coords and len(coords) > 0:
                    # Convert coordinates to [lat, lon] format for Leaflet
                    polygon_positions = []
                    for ring in coords:
                        ring_positions = [[coord[1], coord[0]] for coord in ring]
                        polygon_positions.append(ring_positions)

                    polygon_layer = dl.Polygon(
                        positions=polygon_positions,
                        color="#FF0000",
                        weight=5,
                        opacity=1.0,
                        fillColor="#FF0000",
                        fillOpacity=0.5,
                        children=[dl.Tooltip("Area of Interest")],
                    )
                    map_layers.append(polygon_layer)
                    logger.debug("Added single Polygon layer to map_layers")

            # Add a visible marker at the center as a fallback
            if geometry:
                coords = extract_coordinates_from_geometry(geometry)
                if coords:
                    center_coord = [
                        sum(coord[0] for coord in coords) / len(coords),
                        sum(coord[1] for coord in coords) / len(coords),
                    ]
                    center_marker = dl.CircleMarker(
                        center=center_coord,
                        radius=10,
                        children=[dl.Tooltip(f"Area center: {center_coord}")],
                        color="blue",
                        fill=True,
                        fillColor="blue",
                        fillOpacity=0.8,
                    )
                    map_layers.append(center_marker)
                    logger.debug("Added single center marker at %s", center_coord)

            # Extract coordinates for centering
            geometry = get_geometry_from_geojson(feature_data)
            if geometry:
                coords = extract_coordinates_from_geometry(geometry)
                if coords:
                    center_lat = sum(coord[0] for coord in coords) / len(coords)
                    center_lon = sum(coord[1] for coord in coords) / len(coords)
                    center = [center_lat, center_lon]

                    # Calculate bounds to determine appropriate zoom level
                    min_lat = min(coord[0] for coord in coords)
                    max_lat = max(coord[0] for coord in coords)
                    min_lon = min(coord[1] for coord in coords)
                    max_lon = max(coord[1] for coord in coords)

                    # Calculate the longest edge
                    lat_span = max_lat - min_lat
                    lon_span = max_lon - min_lon
                    max_span = max(lat_span, lon_span)

                    # Calculate zoom so longest edge takes up half the map width
                    # Improved zoom calculation for better regional viewing
                    if max_span > 0:
                        # Use a more balanced approach for different area sizes
                        import math

                        # Define zoom levels based on span ranges
                        if max_span >= 10:  # Very large areas (countries/continents)
                            zoom = max(1, min(4, int(5 - math.log10(max_span))))
                        elif max_span >= 1:  # Large regions (states/provinces)
                            zoom = max(4, min(8, int(8 - math.log10(max_span * 10))))
                        elif max_span >= 0.1:  # Medium areas (cities/counties)
                            zoom = max(8, min(12, int(12 - math.log10(max_span * 100))))
                        else:  # Small areas (neighborhoods/buildings)
                            zoom = max(12, min(18, int(16 - math.log10(max_span * 1000))))
                    else:
                        zoom = 8

                    logger.debug("Calculated single center: %s, zoom: %s", center, zoom)
                    logger.debug(
                        "Single bounds: lat(%s, %s), lon(%s, %s)", min_lat, max_lat, min_lon, max_lon
                    )
                    logger.debug("Single max span: %s", max_span)
        else:
            logger.debug("No valid geojsons provided or unsupported type: %s", type(geojsons))

        logger.debug("Final map_layers count: %d", len(map_layers))
        logger.debug("Final center: %s, zoom: %s", center, zoom)

        # Create the map with English-only tile layer
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

        # Create the minimap/locator map, always pass geojsons
        minimap_component = create_minimap(center, zoom, exec_id, geojsons=geojsons)

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
        maxZoom=tile_config.get("maxZoom", 18),
    )


def create_minimap(center, zoom, map_id, geojsons=None):
    """Create a small overview/locator map with red points for AOIs."""
    # Calculate appropriate zoom level for overview (typically 3-4 levels lower)
    overview_zoom = max(1, zoom - 4)
    lat_offset = 0.5 * (2 ** (10 - zoom))
    lon_offset = 0.7 * (2 ** (10 - zoom))

    # Create a polygon showing the main map's approximate bounds
    bounds_polygon = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [center[1] - lon_offset, center[0] - lat_offset],
                    [center[1] + lon_offset, center[0] - lat_offset],
                    [center[1] + lon_offset, center[0] + lat_offset],
                    [center[1] - lon_offset, center[0] + lat_offset],
                    [center[1] - lon_offset, center[0] - lat_offset],
                ]
            ],
        },
        "properties": {},
    }
    bounds_layer = dl.GeoJSON(
        data=bounds_polygon,
        id=f"bounds-{map_id}",
        options={"style": {"color": "red", "weight": 2, "fillOpacity": 0.2, "fillColor": "red"}},
    )

    # Add AOI points/centroids as red markers
    aoi_markers = []
    if geojsons is not None:
        import numpy as np

        def get_centroid(coords):
            arr = np.array(coords)
            return [float(arr[:, 0].mean()), float(arr[:, 1].mean())]

        if isinstance(geojsons, (dict, str)):
            geojsons = [geojsons]
        for geo in geojsons:
            if isinstance(geo, str):
                try:
                    geo = json.loads(geo)
                except Exception:
                    continue
            feature = ensure_geojson_feature(geo)
            geometry = get_geometry_from_geojson(feature)
            if not geometry:
                continue
            gtype = geometry.get("type")
            coords = geometry.get("coordinates", [])
            if gtype == "Point":
                # coords: [lon, lat]
                aoi_markers.append(
                    dl.Marker(
                        position=[coords[1], coords[0]],
                        children=[dl.Tooltip("AOI")],
                    )
                )
            elif gtype == "Polygon":
                # coords: [[[lon, lat], ...]]
                flat = [pt for ring in coords for pt in ring]
                if flat:
                    centroid = get_centroid([[pt[1], pt[0]] for pt in flat])
                    aoi_markers.append(
                        dl.Marker(
                            position=centroid,
                            children=[dl.Tooltip("AOI")],
                        )
                    )
            elif gtype == "MultiPolygon":
                for poly in coords:
                    flat = [pt for ring in poly for pt in ring]
                    if flat:
                        centroid = get_centroid([[pt[1], pt[0]] for pt in flat])
                        aoi_markers.append(
                            dl.Marker(
                                position=centroid,
                                children=[dl.Tooltip("AOI")],
                            )
                        )
            elif gtype == "MultiPoint":
                for pt in coords:
                    aoi_markers.append(
                        dl.Marker(
                            position=[pt[1], pt[0]],
                            children=[dl.Tooltip("AOI")],
                        )
                    )
    minimap = dl.Map(
        children=[
            get_tile_layer("carto_positron"),
            bounds_layer,
            *aoi_markers,
        ],
        style={
            "width": "225px",  # 1.5x larger than original 150px
            "height": "150px",  # 1.5x larger than original 100px
            "border": "2px solid #333",
            "borderRadius": "4px",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.3)",
        },
        center=center,
        zoom=overview_zoom,
        id=f"minimap-{map_id}",
        zoomControl=False,
        dragging=False,
    )

    # Create close button
    close_button = html.Button(
        "×",
        id={"type": "minimap-close", "index": map_id},
        style={
            "position": "absolute",
            "top": "2px",
            "right": "2px",
            "width": "20px",
            "height": "20px",
            "background": "rgba(255, 255, 255, 0.9)",
            "border": "1px solid #ccc",
            "borderRadius": "3px",
            "fontSize": "14px",
            "fontWeight": "bold",
            "cursor": "pointer",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "padding": "0",
            "lineHeight": "1",
            "zIndex": "1001",
            "color": "#666",
        },
        title="Close minimap",
        n_clicks=0,
    )

    # Return minimap container with close button
    return html.Div(
        children=[minimap, close_button],
        id={"type": "minimap-container", "index": map_id},
        style={
            "position": "absolute",
            "top": "10px",
            "right": "10px",
            "zIndex": 1000,
        },
    )
