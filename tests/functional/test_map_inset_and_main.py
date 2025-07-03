"""
Tests for inset (locator) map and main map rendering with geojsons.
"""
import json

import numpy as np
import pytest

from trendsearth_ui.utils import geojson as geo_utils


def sample_geojsons():
    return [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-74.0059, 40.7128],
                        [-74.0059, 40.7628],
                        [-73.9559, 40.7628],
                        [-73.9559, 40.7128],
                        [-74.0059, 40.7128],
                    ]
                ],
            },
            "properties": {"name": "Test Area 1"},
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [-73.9857, 40.7484],
            },
            "properties": {"name": "Test Point"},
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [2.3522, 48.8566],
                            [2.3522, 48.8766],
                            [2.4022, 48.8766],
                            [2.4022, 48.8566],
                            [2.3522, 48.8566],
                        ]
                    ]
                ],
            },
            "properties": {"name": "Paris MultiPolygon"},
        },
    ]


def test_main_map_layers_and_styles():
    geojsons = sample_geojsons()
    result = geo_utils.create_map_from_geojsons(geojsons, exec_id="test")
    # Should return a list with a Div containing the map and minimap
    assert isinstance(result, list)
    div = result[0]
    assert hasattr(div, "children")
    # Check that the main map contains red polygons (by style)
    map_component = div.children[0]
    geo_layers = [
        c
        for c in map_component.children
        if hasattr(c, "options") and isinstance(getattr(c, "options", None), dict)
    ]
    assert any(
        layer.options.get("style", {}).get("color") in ["red", "#FF0000"] for layer in geo_layers
    ), "Main map should have red polygons/lines."


def test_inset_map_shows_points_and_centroids():
    geojsons = sample_geojsons()
    center = [40.74, -73.98]
    zoom = 10
    minimap_div = geo_utils.create_minimap(center, zoom, map_id="test", geojsons=geojsons)
    # Should return a Div with a minimap child
    assert hasattr(minimap_div, "children")
    minimap = minimap_div.children[0]
    # Should contain at least one marker for the point and one for the polygon centroid
    marker_count = sum(
        1
        for c in minimap.children
        if getattr(c, "__class__", None) and c.__class__.__name__ == "Marker"
    )
    assert marker_count >= 2, "Inset map should show at least two red markers (point and centroid)."


def test_inset_map_marker_positions():
    geojsons = sample_geojsons()
    center = [40.74, -73.98]
    zoom = 10
    minimap_div = geo_utils.create_minimap(center, zoom, map_id="test", geojsons=geojsons)
    minimap = minimap_div.children[0]
    # Collect marker positions
    marker_positions = [
        c.position
        for c in minimap.children
        if getattr(c, "__class__", None) and c.__class__.__name__ == "Marker"
    ]
    # The point should be present
    assert [40.7484, -73.9857] in marker_positions, "Inset map should show the point's position."
    # The polygon centroid should be close to the mean of its coordinates
    poly_coords = [
        [40.7128, -74.0059],
        [40.7628, -74.0059],
        [40.7628, -73.9559],
        [40.7128, -73.9559],
        [40.7128, -74.0059],
    ]
    arr = np.array(poly_coords)
    expected_centroid = [float(arr[:, 0].mean()), float(arr[:, 1].mean())]
    assert any(
        np.allclose(pos, expected_centroid, atol=1e-4) for pos in marker_positions
    ), "Inset map should show the polygon centroid."
