"""
Functional tests for the updated GeoJSON handling functions.
"""

import json

import pytest

from trendsearth_ui.utils.geojson import (
    ensure_geojson_feature,
    extract_coordinates_from_geometry,
    get_geometry_from_geojson,
)


@pytest.fixture
def bare_geometry():
    """Test data - bare geometry object (what we expect from the API)."""
    return {
        "type": "Polygon",
        "coordinates": [[[30.0, 10.0], [40.0, 40.0], [20.0, 40.0], [10.0, 20.0], [30.0, 10.0]]],
    }


@pytest.fixture
def full_feature():
    """Test data - full GeoJSON Feature."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[30.0, 10.0], [40.0, 40.0], [20.0, 40.0], [10.0, 20.0], [30.0, 10.0]]],
        },
        "properties": {"name": "test polygon"},
    }


def test_ensure_geojson_feature_with_bare_geometry(bare_geometry):
    """Test ensure_geojson_feature function with bare geometry."""
    result = ensure_geojson_feature(bare_geometry)

    assert result is not None, "Should return a result"
    assert result.get("type") == "Feature", "Should convert to Feature"
    assert "geometry" in result, "Should have geometry"
    assert "properties" in result, "Should have properties"


def test_ensure_geojson_feature_with_full_feature(full_feature):
    """Test ensure_geojson_feature function with full GeoJSON Feature."""
    result = ensure_geojson_feature(full_feature)

    assert result is not None, "Should return a result"
    assert result.get("type") == "Feature", "Should remain a Feature"
    assert result == full_feature, "Should return the same object if already a Feature"


def test_get_geometry_from_bare_geometry(bare_geometry):
    """Test get_geometry_from_geojson function with bare geometry."""
    geometry = get_geometry_from_geojson(bare_geometry)

    assert geometry is not None, "Should extract geometry"
    assert geometry == bare_geometry, "Should return the same geometry object"


def test_get_geometry_from_full_feature(full_feature):
    """Test get_geometry_from_geojson function with full GeoJSON Feature."""
    geometry = get_geometry_from_geojson(full_feature)

    assert geometry is not None, "Should extract geometry"
    assert geometry == full_feature["geometry"], "Should extract the geometry part"


def test_extract_coordinates(bare_geometry):
    """Test coordinate extraction from geometry."""
    coords = extract_coordinates_from_geometry(bare_geometry)

    assert coords is not None, "Should extract coordinates"
    assert len(coords) > 0, "Should have coordinates"
    assert isinstance(coords, list), "Should return a list of coordinates"
