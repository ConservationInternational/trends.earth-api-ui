"""Helpers for retrieving administrative boundary metadata and resolving ISO codes.

This module fetches the geoBoundaries hierarchy exposed by the Trends.Earth API and
builds a fuzzy-searchable index that can be reused by visualizations which need to
map free-form country names to ISO-3 codes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from difflib import get_close_matches
import json
import logging
import re
from threading import Lock

from cachetools import TTLCache
import requests

from ..config import get_api_base
from .http_client import apply_default_headers

logger = logging.getLogger(__name__)

# Cache the resolver for 30 days per API environment and release type.
_BOUNDARIES_CACHE: TTLCache[str, CountryIsoResolver] = TTLCache(maxsize=4, ttl=2_592_000)
_CACHE_LOCK = Lock()

_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")
_FUZZY_CUTOFF = 0.83

COUNTRY_NAME_OVERRIDES: dict[str, str] = {
    "China": "CHN",
    "Mozambique": "MOZ",
    "United States": "USA",
    "United States of America": "USA",
    "Canada": "CAN",
    "United Kingdom": "GBR",
    "Germany": "DEU",
    "France": "FRA",
    "Japan": "JPN",
    "Brazil": "BRA",
    "India": "IND",
    "Australia": "AUS",
    "South Africa": "ZAF",
    "Mexico": "MEX",
    "Russia": "RUS",
    "Italy": "ITA",
    "Spain": "ESP",
    "Netherlands": "NLD",
    "Sweden": "SWE",
    "Norway": "NOR",
    "Denmark": "DNK",
    "Finland": "FIN",
    "Kenya": "KEN",
    "Nigeria": "NGA",
    "Egypt": "EGY",
    "Argentina": "ARG",
    "Chile": "CHL",
    "Peru": "PER",
    "Colombia": "COL",
    "Ecuador": "ECU",
    "Bolivia": "BOL",
    "Venezuela": "VEN",
    "Thailand": "THA",
    "Indonesia": "IDN",
    "Philippines": "PHL",
    "Malaysia": "MYS",
    "Singapore": "SGP",
    "Vietnam": "VNM",
    "South Korea": "KOR",
    "Republic of Korea": "KOR",
    "Turkey": "TUR",
    "Poland": "POL",
    "Czech Republic": "CZE",
    "Hungary": "HUN",
    "Romania": "ROU",
    "Bulgaria": "BGR",
    "Greece": "GRC",
    "Portugal": "PRT",
    "Belgium": "BEL",
    "Austria": "AUT",
    "Switzerland": "CHE",
    "Ireland": "IRL",
    "New Zealand": "NZL",
    "Israel": "ISR",
    "Morocco": "MAR",
    "Algeria": "DZA",
    "Tunisia": "TUN",
    "Ghana": "GHA",
    "Ethiopia": "ETH",
    "Tanzania": "TZA",
    "Uganda": "UGA",
    "Rwanda": "RWA",
    "Zambia": "ZMB",
    "Zimbabwe": "ZWE",
    "Botswana": "BWA",
    "Namibia": "NAM",
    "Madagascar": "MDG",
    "Swaziland": "SWZ",
    "Eswatini": "SWZ",
    "Cape Verde": "CPV",
    "Ivory Coast": "CIV",
    "Cote d'Ivoire": "CIV",
    "Laos": "LAO",
    "Moldova": "MDA",
    "North Macedonia": "MKD",
    "Macedonia": "MKD",
    "Vatican": "VAT",
    "Holy See": "VAT",
    "Palestine": "PSE",
    "Syria": "SYR",
    "Syrian Arab Republic": "SYR",
    "Burma": "MMR",
    "Myanmar": "MMR",
    "Brunei": "BRN",
    "Sao Tome and Principe": "STP",
    "Timor Leste": "TLS",
    "East Timor": "TLS",
    "Iran": "IRN",
    "Islamic Republic of Iran": "IRN",
    "Gambia": "GMB",
    "The Gambia": "GMB",
    "Bahamas": "BHS",
    "The Bahamas": "BHS",
    "Taiwan": "TWN",
    "Democratic Republic of the Congo": "COD",
    "Democratic Republic of Congo": "COD",
    "Democratic Republic Congo": "COD",
    "Dem. Rep. Congo": "COD",
    "Congo Democratic Republic": "COD",
    "Central African Republic": "CAF",
    "Central African Rep.": "CAF",
    "Central African Rep": "CAF",
    "S. Sudan": "SSD",
    "S Sudan": "SSD",
    "South Sudan": "SSD",
}

COUNTRY_NAME_OVERRIDES.update(
    {
        "North Korea": "PRK",
        "Democratic People's Republic of Korea": "PRK",
        "United Republic of Tanzania": "TZA",
        "Bolivia Plurinational State of": "BOL",
        "Bolivia (Plurinational State of)": "BOL",
        "Viet Nam": "VNM",
        "Iran (Islamic Republic of)": "IRN",
    }
)


def _normalize(name: str | None) -> str:
    """Normalize a country name for fuzzy comparisons."""

    if not name:
        return ""
    lowered = name.strip().lower()
    if not lowered:
        return ""
    cleaned = _NORMALIZE_PATTERN.sub(" ", lowered)
    return " ".join(cleaned.split())


def _generate_name_variants(name: str) -> set[str]:
    """Generate common variants for a boundary name to improve matching."""

    variants: set[str] = set()
    if not name:
        return variants

    candidates: set[str] = {name, name.replace("’", "'")}
    if "(" in name:
        candidates.add(name.split("(")[0].strip())
    if "," in name:
        candidates.add(name.split(",")[0].strip())
    if " - " in name:
        candidates.update(part.strip() for part in name.split("-") if part.strip())
    if "/" in name:
        candidates.update(part.strip() for part in name.split("/") if part.strip())

    for candidate in candidates:
        if candidate:
            variants.add(candidate)
            stripped = candidate.replace("'", "")
            if stripped:
                variants.add(stripped)

    return {variant for variant in variants if variant}


@dataclass
class CountryIsoResolver:
    """Resolve free-form country names to ISO-3 codes using boundary metadata."""

    release_type: str
    last_updated: str | None
    _variant_map: dict[str, str]
    _display_names: dict[str, str]

    def resolve(self, country_name: str) -> str | None:
        """Resolve a country name (or ISO code) to a normalized ISO-3 code."""

        if not country_name:
            return None

        normalized = _normalize(country_name)
        if not normalized:
            return None

        iso_code = self._variant_map.get(normalized)
        if iso_code:
            return iso_code

        match_candidates = get_close_matches(
            normalized,
            list(self._variant_map.keys()),
            n=1,
            cutoff=_FUZZY_CUTOFF,
        )
        if match_candidates:
            candidate = match_candidates[0]
            matched_iso = self._variant_map.get(candidate)
            if matched_iso:
                logger.debug(
                    "Fuzzy matched country name '%s' to boundary variant '%s' -> %s",
                    country_name,
                    candidate,
                    matched_iso,
                )
                return matched_iso

        return None

    def display_name(self, iso_code: str) -> str:
        """Return the canonical boundary name for an ISO code."""

        if not iso_code:
            return ""
        return self._display_names.get(iso_code.upper(), iso_code.upper())

    @property
    def iso_codes(self) -> frozenset[str]:
        """Return the set of ISO codes contained in the resolver."""

        return frozenset(self._display_names.keys())


def _build_resolver(
    boundaries: Iterable[dict], release_type: str, last_updated: str | None
) -> CountryIsoResolver:
    """Build a resolver from the hierarchical boundaries payload."""

    variant_map: dict[str, str] = {}
    display_names: dict[str, str] = {}

    for entry in boundaries:
        try:
            iso_raw = entry.get("boundaryISO")
            name_raw = entry.get("boundaryName")
        except AttributeError:
            continue

        if not iso_raw or not name_raw:
            continue

        iso_code = str(iso_raw).upper()
        display_names.setdefault(iso_code, str(name_raw))

        variants = _generate_name_variants(str(name_raw))
        variants.add(str(name_raw))
        variants.add(iso_code)
        variants.add(iso_code.lower())

        for variant in variants:
            normalized = _normalize(variant)
            if normalized:
                variant_map[normalized] = iso_code

    iso_set = set(display_names.keys())

    for override_name, override_iso in COUNTRY_NAME_OVERRIDES.items():
        if override_iso.upper() in iso_set:
            variant_map[_normalize(override_name)] = override_iso.upper()

    return CountryIsoResolver(
        release_type=release_type,
        last_updated=last_updated,
        _variant_map=variant_map,
        _display_names=display_names,
    )


def get_country_iso_resolver(
    token: str,
    api_environment: str,
    release_type: str = "gbOpen",
) -> CountryIsoResolver | None:
    """Fetch (or retrieve from cache) the country ISO resolver for the given environment."""

    if not token:
        logger.warning("Cannot fetch boundaries without an authentication token")
        return None

    cache_key = f"{api_environment}:{release_type}"
    with _CACHE_LOCK:
        cached = _BOUNDARIES_CACHE.get(cache_key)
        if cached is not None:
            return cached

    resolver = _fetch_resolver(token, api_environment, release_type)
    if resolver is not None:
        with _CACHE_LOCK:
            _BOUNDARIES_CACHE[cache_key] = resolver
    return resolver


def _fetch_resolver(
    token: str, api_environment: str, release_type: str
) -> CountryIsoResolver | None:
    """Fetch boundary metadata from the API and build a resolver."""

    url = f"{get_api_base(api_environment)}/data/boundaries/list"
    headers = apply_default_headers({"Authorization": f"Bearer {token}"})
    params = {"release_type": release_type}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to fetch boundaries list: %s", exc)
        return None

    if response.status_code != 200:
        logger.warning(
            "Boundaries endpoint returned status %s: %s",
            response.status_code,
            response.text[:200],
        )
        return None

    try:
        payload = response.json()
    except json.JSONDecodeError:
        logger.warning("Boundaries endpoint returned non-JSON response")
        return None

    boundaries = payload.get("boundaries")
    if not isinstance(boundaries, list):
        logger.warning("Unexpected boundaries payload structure: %s", type(boundaries))
        return None

    last_updated = payload.get("last_updated")
    resolver = _build_resolver(boundaries, release_type, last_updated)
    logger.info(
        "Fetched %s boundary entries for release '%s' (last updated %s)",
        len(boundaries),
        release_type,
        last_updated,
    )
    return resolver


def clear_country_iso_cache() -> int:
    """Clear the cached country ISO resolvers."""

    with _CACHE_LOCK:
        cleared = len(_BOUNDARIES_CACHE)
        _BOUNDARIES_CACHE.clear()
        return cleared
