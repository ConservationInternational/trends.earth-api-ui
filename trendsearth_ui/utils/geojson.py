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
        print(f"DEBUG: create_map_from_geojsons called with geojsons type: {type(geojsons)}")
        if isinstance(geojsons, list):
            print(f"DEBUG: geojsons is a list with {len(geojsons)} items")
        elif isinstance(geojsons, dict):
            print(f"DEBUG: geojsons is a dict with keys: {list(geojsons.keys())}")
        elif isinstance(geojsons, str):
            print(f"DEBUG: geojsons is a string with length: {len(geojsons)}")
        else:
            print(f"DEBUG: geojsons is of unexpected type: {type(geojsons)}")

        # Initialize map layers
        map_layers = []

        # Default center (will be updated based on geojsons)
        center = [0, 0]
        zoom = 2

        if isinstance(geojsons, list):
            print(f"DEBUG: Processing list of {len(geojsons)} geojsons")
            all_coordinates = []

            for i, geojson in enumerate(geojsons):
                print(f"DEBUG: Processing geojson {i}: {type(geojson)}")
                if isinstance(geojson, str):
                    try:
                        geojson_dict = json.loads(geojson)
                        print(f"DEBUG: Parsed JSON string to {type(geojson_dict)}")
                    except json.JSONDecodeError:
                        print("DEBUG: Failed to parse JSON string")
                        continue
                else:
                    geojson_dict = geojson

                # Handle FeatureCollection case
                if (
                    isinstance(geojson_dict, dict)
                    and geojson_dict.get("type") == "FeatureCollection"
                ):
                    print(
                        f"DEBUG: Found FeatureCollection with {len(geojson_dict.get('features', []))} features"
                    )
                    features = geojson_dict.get("features", [])
                    for j, feature in enumerate(features):
                        print(f"DEBUG: Processing feature {j} from FeatureCollection")
                        feature_data = ensure_geojson_feature(feature)
                        if feature_data:
                            # Add this feature as a separate layer
                            geometry = feature_data.get("geometry")
                            if geometry:
                                print(f"DEBUG: Feature {j} geometry type: {geometry.get('type')}")
                                coords = geometry.get("coordinates", [])
                                if coords:
                                    print(
                                        f"DEBUG: Feature {j} first few coordinates: {coords[:2] if isinstance(coords, list) else 'Not a list'}"
                                    )

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
                            print(f"DEBUG: Added GeoJSON layer {i}-{j} to map_layers")

                            # Extract coordinates for centering
                            if geometry and geometry.get("type") in ["Polygon", "MultiPolygon"]:
                                extracted_coords = extract_coordinates_from_geometry(geometry)
                                all_coordinates.extend(extracted_coords)
                                print(
                                    f"DEBUG: Extracted {len(extracted_coords)} coordinates from feature {j}"
                                )

                # Handle regular geometry or feature
                elif isinstance(geojson_dict, dict):
                    # Convert bare geometry to GeoJSON Feature if needed
                    feature_data = ensure_geojson_feature(geojson_dict)
                    print(
                        f"DEBUG: Created feature data: {feature_data.get('type', 'unknown') if isinstance(feature_data, dict) else type(feature_data)}"
                    )

                    if feature_data:
                        # Debug: Print the geometry type and coordinates
                        geometry = feature_data.get("geometry")
                        if geometry:
                            print(f"DEBUG: Geometry type: {geometry.get('type')}")
                            coords = geometry.get("coordinates", [])
                            if coords:
                                print(
                                    f"DEBUG: First few coordinates: {coords[:2] if isinstance(coords, list) else 'Not a list'}"
                                )

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
                        print(f"DEBUG: Added GeoJSON layer {i} to map_layers")

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
                                print(f"DEBUG: Added Polygon layer {i} to map_layers")

                        # Extract coordinates for centering
                        if geometry and geometry.get("type") in ["Polygon", "MultiPolygon"]:
                            extracted_coords = extract_coordinates_from_geometry(geometry)
                            all_coordinates.extend(extracted_coords)
                            print(
                                f"DEBUG: Extracted {len(extracted_coords)} coordinates from geojson {i}"
                            )
                else:
                    print(f"DEBUG: Skipping non-dict geojson_dict: {type(geojson_dict)}")

            # Calculate center from all coordinates
            if all_coordinates:
                center_lat = sum(coord[0] for coord in all_coordinates) / len(all_coordinates)
                center_lon = sum(coord[1] for coord in all_coordinates) / len(all_coordinates)
                center = [center_lat, center_lon]
                zoom = 10  # Reasonable zoom for viewing polygons
                print(f"DEBUG: Calculated center from {len(all_coordinates)} coordinates: {center}")
            else:
                print("DEBUG: No coordinates found, using default center")

        elif isinstance(geojsons, (dict, str)):
            print("DEBUG: Processing single geojson")
            # Single geojson
            if isinstance(geojsons, str):
                try:
                    parsed_data = json.loads(geojsons)
                    print(f"DEBUG: Parsed single JSON string to {type(parsed_data)}")

                    # Check if the parsed string is actually a list
                    if isinstance(parsed_data, list):
                        print(
                            "DEBUG: Parsed string is actually a list, redirecting to list processing"
                        )
                        # Recursively call with the parsed list
                        return create_map_from_geojsons(parsed_data, exec_id)
                    else:
                        geojson_dict = parsed_data
                except json.JSONDecodeError:
                    print("DEBUG: Failed to parse single JSON string")
                    return [html.P("Could not parse GeoJSON data.")]
            else:
                geojson_dict = geojsons

            # Convert bare geometry to GeoJSON Feature if needed
            feature_data = ensure_geojson_feature(geojson_dict)
            print(
                f"DEBUG: Created single feature data: {feature_data.get('type', 'unknown') if isinstance(feature_data, dict) else type(feature_data)}"
            )

            # Debug: Print the geometry type and coordinates
            geometry = feature_data.get("geometry")
            if geometry:
                print(f"DEBUG: Single geometry type: {geometry.get('type')}")
                coords = geometry.get("coordinates", [])
                if coords:
                    print(
                        f"DEBUG: Single first few coordinates: {coords[:2] if isinstance(coords, list) else 'Not a list'}"
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
            print("DEBUG: Added single GeoJSON layer to map_layers")

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
                    print("DEBUG: Added single Polygon layer to map_layers")

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
                    print(f"DEBUG: Added single center marker at {center_coord}")

            # Extract coordinates for centering
            geometry = get_geometry_from_geojson(feature_data)
            if geometry:
                coords = extract_coordinates_from_geometry(geometry)
                if coords:
                    center_lat = sum(coord[0] for coord in coords) / len(coords)
                    center_lon = sum(coord[1] for coord in coords) / len(coords)
                    center = [center_lat, center_lon]
                    zoom = 9  # Lower zoom for better overview
                    print(f"DEBUG: Calculated single center: {center}, zoom: {zoom}")
        else:
            print(f"DEBUG: No valid geojsons provided or unsupported type: {type(geojsons)}")

        print(f"DEBUG: Final map_layers count: {len(map_layers)}")
        print(f"DEBUG: Final center: {center}, zoom: {zoom}")

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
        zoomControl=False,
        dragging=False,
    )
    return html.Div(
        children=[minimap], style={"position": "relative", "width": "0px", "height": "0px"}
    )
