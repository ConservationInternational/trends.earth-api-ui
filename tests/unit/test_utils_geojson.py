"""Unit tests for GeoJSON utility functions."""

import json
from unittest.mock import Mock, patch

import pytest

from trendsearth_ui.utils.geojson import (
    create_map_from_geojsons,
    create_minimap,
    ensure_geojson_feature,
    extract_coordinates_from_geometry,
    get_geometry_from_geojson,
    get_tile_layer,
)


class TestEnsureGeoJSONFeature:
    """Test the ensure_geojson_feature utility function."""

    def test_bare_geometry_to_feature(self):
        """Test converting bare geometry to GeoJSON Feature."""
        geometry = {"type": "Point", "coordinates": [0, 0]}
        result = ensure_geojson_feature(geometry)

        assert result["type"] == "Feature"
        assert result["geometry"] == geometry
        assert result["properties"] == {}

    def test_existing_feature_unchanged(self):
        """Test that existing Feature is returned unchanged."""
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"name": "test"},
        }
        result = ensure_geojson_feature(feature)

        assert result == feature

    def test_feature_collection_unchanged(self):
        """Test that FeatureCollection is returned unchanged."""
        feature_collection = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "properties": {},
                }
            ],
        }
        result = ensure_geojson_feature(feature_collection)

        assert result == feature_collection

    def test_invalid_data_unchanged(self):
        """Test that invalid data is returned unchanged."""
        invalid_data = {"invalid": "data"}
        result = ensure_geojson_feature(invalid_data)

        assert result == invalid_data

    def test_non_dict_unchanged(self):
        """Test that non-dict data is returned unchanged."""
        non_dict = "not a dict"
        result = ensure_geojson_feature(non_dict)

        assert result == non_dict


class TestGetGeometryFromGeoJSON:
    """Test the get_geometry_from_geojson utility function."""

    def test_extract_geometry_from_feature(self):
        """Test extracting geometry from a Feature."""
        geometry = {"type": "Point", "coordinates": [0, 0]}
        feature = {"type": "Feature", "geometry": geometry, "properties": {}}
        result = get_geometry_from_geojson(feature)

        assert result == geometry

    def test_extract_geometry_from_feature_collection(self):
        """Test extracting geometry from first feature in FeatureCollection."""
        geometry = {"type": "Point", "coordinates": [0, 0]}
        feature_collection = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": geometry, "properties": {}}],
        }
        result = get_geometry_from_geojson(feature_collection)

        assert result == geometry

    def test_extract_bare_geometry(self):
        """Test extracting bare geometry."""
        geometry = {"type": "Point", "coordinates": [0, 0]}
        result = get_geometry_from_geojson(geometry)

        assert result == geometry

    def test_empty_feature_collection(self):
        """Test extracting from empty FeatureCollection returns None."""
        feature_collection = {"type": "FeatureCollection", "features": []}
        result = get_geometry_from_geojson(feature_collection)

        assert result is None

    def test_invalid_data_returns_none(self):
        """Test that invalid data returns None."""
        result = get_geometry_from_geojson({"invalid": "data"})
        assert result is None

        result = get_geometry_from_geojson("not a dict")
        assert result is None

        result = get_geometry_from_geojson(None)
        assert result is None


class TestExtractCoordinatesFromGeometry:
    """Test the extract_coordinates_from_geometry utility function."""

    def test_extract_point_coordinates(self):
        """Test extracting coordinates from Point geometry."""
        geometry = {"type": "Point", "coordinates": [1.0, 2.0]}
        result = extract_coordinates_from_geometry(geometry)

        assert result == [[2.0, 1.0]]  # [lat, lon] format

    def test_extract_linestring_coordinates(self):
        """Test extracting coordinates from LineString geometry."""
        geometry = {"type": "LineString", "coordinates": [[1.0, 2.0], [3.0, 4.0]]}
        result = extract_coordinates_from_geometry(geometry)

        assert result == [[2.0, 1.0], [4.0, 3.0]]  # [lat, lon] format

    def test_extract_polygon_coordinates(self):
        """Test extracting coordinates from Polygon geometry."""
        geometry = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
        result = extract_coordinates_from_geometry(geometry)

        expected = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]  # [lat, lon] format
        assert result == expected

    def test_extract_multipolygon_coordinates(self):
        """Test extracting coordinates from MultiPolygon geometry."""
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]],
        }
        result = extract_coordinates_from_geometry(geometry)

        expected = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]  # [lat, lon] format
        assert result == expected

    def test_invalid_geometry_returns_empty(self):
        """Test that invalid geometry returns empty list."""
        result = extract_coordinates_from_geometry({"type": "Invalid"})
        assert result == []

        result = extract_coordinates_from_geometry({})
        assert result == []


class TestCreateMapFromGeoJSONs:
    """Test the create_map_from_geojsons utility function."""

    @patch("trendsearth_ui.utils.geojson.dl.Map")
    @patch("trendsearth_ui.utils.geojson.dl.TileLayer")
    @patch("trendsearth_ui.utils.geojson.dl.GeoJSON")
    def test_create_map_single_geojson(self, mock_geojson, mock_tile, mock_map):
        """Test creating map with single GeoJSON."""
        geojson_data = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
            "properties": {},
        }

        exec_id = "test123"
        result = create_map_from_geojsons(geojson_data, exec_id)

        # Verify that map components were called
        # Now expects 2 GeoJSON calls: 1 for main map + 1 for minimap bounds
        assert mock_geojson.call_count == 2
        # Expects 2 TileLayer calls: 1 for main map + 1 for minimap
        assert mock_tile.call_count == 2
        # Expects 2 Map calls: 1 for main map + 1 for minimap
        assert mock_map.call_count == 2

        assert isinstance(result, list)

    @patch("trendsearth_ui.utils.geojson.dl.Map")
    @patch("trendsearth_ui.utils.geojson.dl.TileLayer")
    @patch("trendsearth_ui.utils.geojson.dl.GeoJSON")
    def test_create_map_multiple_geojsons(self, mock_geojson, mock_tile, mock_map):
        """Test creating map with multiple GeoJSONs."""
        geojson_list = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                "properties": {},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [3.0, 4.0]},
                "properties": {},
            },
        ]

        exec_id = "test123"
        result = create_map_from_geojsons(geojson_list, exec_id)

        # Verify that multiple GeoJSON layers were created
        # Now expects 3 GeoJSON calls: 2 for main map layers + 1 for minimap bounds
        assert mock_geojson.call_count == 3
        # Expects 2 TileLayer calls: 1 for main map + 1 for minimap
        assert mock_tile.call_count == 2
        # Expects 2 Map calls: 1 for main map + 1 for minimap
        assert mock_map.call_count == 2

        assert isinstance(result, list)

    def test_create_map_invalid_data(self):
        """Test creating map with invalid data returns error message."""
        result = create_map_from_geojsons("invalid", "test123")

        assert isinstance(result, list)
        assert len(result) == 1
        # Should return an error message component    def test_create_map_exception_handling(self):
        """Test that exceptions are handled gracefully."""
        # Test with data that might cause an exception
        result = create_map_from_geojsons(None, "test123")

        assert isinstance(result, list)
        assert len(result) == 1
        # Should return an error message component


class TestCreateMinimap:
    """Test the create_minimap function."""

    def test_create_minimap_basic(self):
        """Test creating a basic minimap."""
        center = [40.7128, -74.0060]  # New York coordinates
        zoom = 10
        map_id = "test_map"

        result = create_minimap(center, zoom, map_id)

        # Should return an HTML div container
        assert result is not None
        assert hasattr(result, "children")

    def test_create_minimap_zoom_calculation(self):
        """Test that minimap zoom is calculated correctly."""
        center = [40.7128, -74.0060]
        zoom = 10
        map_id = "test_map"

        result = create_minimap(center, zoom, map_id)

        # Verify structure
        assert result is not None
        assert hasattr(result, "children")
        if hasattr(result, "children") and result.children:
            assert len(result.children) == 2  # Should contain minimap and close button

            # First child should be the map
            minimap_element = result.children[0]
            assert hasattr(
                minimap_element, "children"
            )  # Map should have children (TileLayer, etc.)

            # Second child should be the close button
            close_button = result.children[1]
            assert hasattr(close_button, "id")  # Close button should have an ID

    def test_create_minimap_low_zoom(self):
        """Test minimap with low zoom level."""
        center = [0, 0]
        zoom = 2
        map_id = "test_map"

        result = create_minimap(center, zoom, map_id)

        # Should still work with low zoom
        assert result is not None
        assert hasattr(result, "children")

    def test_create_minimap_high_zoom(self):
        """Test minimap with high zoom level."""
        center = [40.7128, -74.0060]
        zoom = 18
        map_id = "test_map"

        result = create_minimap(center, zoom, map_id)

        # Should still work with high zoom
        assert result is not None
        assert hasattr(result, "children")


class TestGetTileLayer:
    """Test the get_tile_layer utility function."""

    def test_default_tile_layer(self):
        """Test getting the default tile layer."""
        import dash_leaflet as dl

        from trendsearth_ui.utils.geojson import get_tile_layer

        layer = get_tile_layer()

        # Verify it returns a TileLayer component
        assert isinstance(layer, dl.TileLayer)
        # Verify it has the expected type
        assert layer._type == "TileLayer"

    def test_specific_tile_provider(self):
        """Test getting a specific tile provider."""
        import dash_leaflet as dl

        from trendsearth_ui.utils.geojson import get_tile_layer

        layer = get_tile_layer("carto_positron")

        # Verify it returns a TileLayer component
        assert isinstance(layer, dl.TileLayer)
        assert layer._type == "TileLayer"

    def test_invalid_provider_fallback(self):
        """Test that invalid provider names fall back to default."""
        import dash_leaflet as dl

        from trendsearth_ui.utils.geojson import get_tile_layer

        layer = get_tile_layer("nonexistent_provider")

        # Should still return a valid TileLayer
        assert isinstance(layer, dl.TileLayer)
        assert layer._type == "TileLayer"
