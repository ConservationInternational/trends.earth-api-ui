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
from pathlib import Path
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


# ---- Country dropdown utilities ----

# Path to the fallback countries JSON file
_FALLBACK_COUNTRIES_PATH = (
    Path(__file__).parent.parent / "data" / "countries_fallback.json"
)

# Cache for country options (per API environment)
_COUNTRY_OPTIONS_CACHE: TTLCache[str, list[dict]] = TTLCache(maxsize=4, ttl=3600)
_COUNTRY_OPTIONS_LOCK = Lock()


def _load_fallback_country_options() -> list[dict]:
    """Load the fallback country list from the JSON file.

    Returns:
        List of dicts with 'label' (country name) and 'value' (ISO code) keys,
        suitable for use in Dash dropdowns.
    """
    try:
        with open(_FALLBACK_COUNTRIES_PATH, encoding="utf-8") as f:
            countries = json.load(f)
        # Convert to dropdown options format
        return [{"label": c["name"], "value": c["code"]} for c in countries]
    except FileNotFoundError:
        logger.warning("Fallback countries file not found: %s", _FALLBACK_COUNTRIES_PATH)
        return []
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Error parsing fallback countries file: %s", e)
        return []


def get_country_options(
    api_environment: str | None = None,
    token: str | None = None,
    use_cache: bool = True,
) -> list[dict]:
    """Get country options for dropdowns, with API fetch and fallback support.

    This function attempts to fetch countries from the boundaries API if a token
    is provided. If the API is unavailable or returns an error, it falls back
    to the static country list.

    Args:
        api_environment: The API environment (e.g., 'production', 'staging').
                         If None, only the fallback list is used.
        token: Optional authentication token for API access.
        use_cache: Whether to use cached results (default True).

    Returns:
        List of dicts with 'label' (country name) and 'value' (ISO code) keys.
    """
    cache_key = api_environment or "fallback"

    # Check cache first
    if use_cache:
        with _COUNTRY_OPTIONS_LOCK:
            cached = _COUNTRY_OPTIONS_CACHE.get(cache_key)
            if cached is not None:
                return cached

    # Try to fetch from API if we have credentials
    if api_environment and token:
        options = _fetch_country_options_from_api(api_environment, token)
        if options:
            with _COUNTRY_OPTIONS_LOCK:
                _COUNTRY_OPTIONS_CACHE[cache_key] = options
            return options

    # Try fetching without auth (for registration flow)
    if api_environment:
        options = _fetch_country_options_from_api(api_environment, None)
        if options:
            with _COUNTRY_OPTIONS_LOCK:
                _COUNTRY_OPTIONS_CACHE[cache_key] = options
            return options

    # Fall back to static list
    logger.debug("Using fallback country list")
    fallback = _load_fallback_country_options()
    if fallback:
        with _COUNTRY_OPTIONS_LOCK:
            _COUNTRY_OPTIONS_CACHE[cache_key] = fallback
    return fallback


def _fetch_country_options_from_api(
    api_environment: str, token: str | None
) -> list[dict] | None:
    """Fetch country options from the boundaries API.

    Args:
        api_environment: The API environment.
        token: Optional authentication token.

    Returns:
        List of dropdown options, or None if fetch failed.
    """
    url = f"{get_api_base(api_environment)}/data/boundaries"
    headers = apply_default_headers()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(
            url,
            headers=headers,
            params={"level": "0", "per_page": "300"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            countries = data.get("data", [])

            options = []
            for country in countries:
                iso_code = country.get("boundaryISO", "")
                name = country.get("boundaryName", "")
                if iso_code and name:
                    options.append({"label": name, "value": iso_code})

            options.sort(key=lambda x: x["label"])
            logger.debug("Fetched %d countries from boundaries API", len(options))
            return options
        else:
            logger.warning(
                "Boundaries API returned status %d, will use fallback",
                response.status_code,
            )
            return None

    except requests.exceptions.Timeout:
        logger.warning("Boundaries API request timed out")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("Cannot connect to boundaries API")
        return None
    except Exception as e:
        logger.exception("Error fetching countries from API: %s", e)
        return None


def get_fallback_country_options() -> list[dict]:
    """Get the fallback country options (convenience function for backwards compatibility).

    Returns:
        List of dicts with 'label' and 'value' keys for Dash dropdowns.
    """
    return _load_fallback_country_options()
