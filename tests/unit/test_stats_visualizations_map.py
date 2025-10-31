"""Tests for the user geographic map visualization utilities."""

from typing import cast

from dash import dcc

from trendsearth_ui.utils.boundaries_utils import CountryIsoResolver
from trendsearth_ui.utils.stats_visualizations import create_user_geographic_map


def _extract_locations(graph_component) -> list[str]:
    """Helper to read ISO locations from the rendered graph."""

    assert isinstance(graph_component, dcc.Graph)
    figure = graph_component.figure
    assert figure and getattr(figure, "data", None)
    trace = figure.data[0]
    locations = getattr(trace, "locations", None) or trace["locations"]
    return list(locations)


def test_geographic_map_prefers_full_country_dataset_over_top_list():
    """If the API returns both full country data and a top list, use all countries."""

    payload = {
        "data": {
            "geographic_distribution": {
                "countries": {"United States": 10, "Kenya": 5},
            }
        }
    }

    graph = create_user_geographic_map(payload, iso_resolver=None)
    assert isinstance(graph, dcc.Graph)
    locations = _extract_locations(cast(dcc.Graph, graph))

    assert set(locations) == {"USA", "KEN"}


def test_geographic_map_accepts_iso_codes_without_resolver():
    """ISO-3 keys should still render even if the resolver could not be loaded."""

    payload = {
        "data": {
            "geographic_distribution": {
                "countries": {"USA": 7, "KEN": 2},
            }
        }
    }

    graph = create_user_geographic_map(payload, iso_resolver=None)
    assert isinstance(graph, dcc.Graph)
    locations = _extract_locations(cast(dcc.Graph, graph))

    assert set(locations) == {"USA", "KEN"}


def test_geographic_map_resolves_dem_rep_congo_variant():
    """Common abbreviations like 'Dem. Rep. Congo' should map to COD."""

    payload = {
        "data": {
            "geographic_distribution": {
                "countries": {"Dem. Rep. Congo": 12},
            }
        }
    }

    graph = create_user_geographic_map(payload, iso_resolver=None)
    assert isinstance(graph, dcc.Graph)
    locations = _extract_locations(cast(dcc.Graph, graph))

    assert locations == ["COD"]


def test_iso_override_applies_when_resolver_available():
    """Overrides should still win when a resolver is provided."""

    resolver = CountryIsoResolver(
        release_type="test",
        last_updated=None,
        _variant_map={},
        _display_names={
            "COD": "Democratic Republic of the Congo",
            "SSD": "South Sudan",
            "CAF": "Central African Republic",
        },
    )

    payload = {
        "data": {
            "geographic_distribution": {
                "countries": {
                    "Dem. Rep. Congo": 5,
                    "S. Sudan": 4,
                    "Central African Rep.": 3,
                }
            }
        }
    }

    graph = create_user_geographic_map(payload, iso_resolver=resolver)
    assert isinstance(graph, dcc.Graph)
    locations = sorted(_extract_locations(cast(dcc.Graph, graph)))

    assert locations == ["CAF", "COD", "SSD"]


def test_geographic_map_resolves_central_african_and_south_sudan_variants():
    """Ensure CAF and SSD abbreviations resolve from common short forms."""

    payload = {
        "data": {
            "geographic_distribution": {
                "countries": {
                    "Central African Rep.": 4,
                    "S. Sudan": 3,
                },
            }
        }
    }

    graph = create_user_geographic_map(payload, iso_resolver=None)
    assert isinstance(graph, dcc.Graph)
    locations = sorted(_extract_locations(cast(dcc.Graph, graph)))

    assert locations == ["CAF", "SSD"]


def test_geographic_map_resolves_nbsp_variant():
    """Non-breaking space variants should resolve to SSD."""

    payload = {
        "data": {
            "geographic_distribution": {
                "countries": {
                    "S.\u00a0Sudan": 2,
                    "S Sudan": 1,
                }
            }
        }
    }

    graph = create_user_geographic_map(payload, iso_resolver=None)
    assert isinstance(graph, dcc.Graph)
    locations = sorted(_extract_locations(cast(dcc.Graph, graph)))

    assert locations == ["SSD"]
