"""
Functional tests for map functionality including GeoJSON parsing and map creation.
"""

import json
from unittest.mock import patch

import pytest

from trendsearth_ui.utils.geojson import extract_coordinates_from_geometry


# Test data - sample GeoJSON features
@pytest.fixture
def test_geojsons():
    """Sample GeoJSON features for testing."""
    return [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-74.0059, 40.7128],  # New York area
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
                "coordinates": [-73.9857, 40.7484],  # Times Square
            },
            "properties": {"name": "Test Point"},
        },
    ]


@pytest.fixture
def test_geojson_string():
    """Sample GeoJSON as string for testing."""
    return json.dumps(
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [2.3522, 48.8566],  # Paris area
                        [2.3522, 48.8766],
                        [2.4022, 48.8766],
                        [2.4022, 48.8566],
                        [2.3522, 48.8566],
                    ]
                ],
            },
            "properties": {"name": "Paris Test Area"},
        }
    )


def test_extract_coordinates_from_polygon():
    """Test coordinate extraction from polygon geometry."""
    polygon_geometry = {
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
    }

    coords = extract_coordinates_from_geometry(polygon_geometry)
    assert coords is not None, "Should extract coordinates from polygon"
    assert len(coords) > 0, "Should have coordinates"


def test_extract_coordinates_from_point():
    """Test coordinate extraction from point geometry."""
    point_geometry = {"type": "Point", "coordinates": [-73.9857, 40.7484]}

    coords = extract_coordinates_from_geometry(point_geometry)
    assert coords is not None, "Should extract coordinates from point"
    assert len(coords) == 2, "Point should have 2 coordinates"
    assert coords[0] == -73.9857, "Longitude should match"
    assert coords[1] == 40.7484, "Latitude should match"


def test_geojson_parsing(test_geojsons, test_geojson_string):
    """Test that GeoJSON data can be parsed correctly."""
    # Test list of GeoJSON features
    assert len(test_geojsons) == 2, "Should have 2 test features"
    assert test_geojsons[0]["type"] == "Feature", "First item should be a Feature"
    assert test_geojsons[1]["type"] == "Feature", "Second item should be a Feature"

    # Test GeoJSON string parsing
    parsed = json.loads(test_geojson_string)
    assert parsed["type"] == "Feature", "Parsed GeoJSON should be a Feature"
    assert "geometry" in parsed, "Should have geometry"
    assert "properties" in parsed, "Should have properties"


def test_polygon_coordinates_structure(test_geojsons):
    """Test that polygon coordinates have the correct structure."""
    polygon_feature = test_geojsons[0]  # First feature is a polygon
    geometry = polygon_feature["geometry"]

    assert geometry["type"] == "Polygon", "Should be a Polygon type"
    assert "coordinates" in geometry, "Should have coordinates"
    assert len(geometry["coordinates"]) > 0, "Should have coordinate rings"
    assert len(geometry["coordinates"][0]) >= 4, "Polygon ring should have at least 4 points"

    # First and last coordinates should be the same (closed ring)
    first_coord = geometry["coordinates"][0][0]
    last_coord = geometry["coordinates"][0][-1]
    assert first_coord == last_coord, "Polygon ring should be closed"


def test_point_coordinates_structure(test_geojsons):
    """Test that point coordinates have the correct structure."""
    point_feature = test_geojsons[1]  # Second feature is a point
    geometry = point_feature["geometry"]

    assert geometry["type"] == "Point", "Should be a Point type"
    assert "coordinates" in geometry, "Should have coordinates"
    assert len(geometry["coordinates"]) == 2, "Point should have exactly 2 coordinates"
    assert isinstance(geometry["coordinates"][0], (int, float)), "Longitude should be numeric"
    assert isinstance(geometry["coordinates"][1], (int, float)), "Latitude should be numeric"


def test_map_modal_callback_simulation(test_geojsons):
    """Test the logic that would be used in the map modal callback."""
    # Simulate execution params data with geojsons field
    mock_params_dict = {"geojsons": test_geojsons, "other_param": "some value"}

    mock_params_string = json.dumps(mock_params_dict, default=str)

    # Test parsing from dict
    geojsons_from_dict = mock_params_dict.get("geojsons")
    assert geojsons_from_dict is not None, "Should extract geojsons from dict"
    assert len(geojsons_from_dict) == 2, "Should have 2 GeoJSON features"

    # Test parsing from JSON string
    try:
        parsed_params = json.loads(mock_params_string)
        geojsons_from_string = parsed_params.get("geojsons")
        assert geojsons_from_string is not None, "Should extract geojsons from JSON string"
    except json.JSONDecodeError:
        pytest.fail("Should be able to parse JSON string")
