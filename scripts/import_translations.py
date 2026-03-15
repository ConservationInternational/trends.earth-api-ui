#!/usr/bin/env python3
"""Import translations from trends.earth Qt .ts files to trends.earth-api-ui .po files.

This script extracts translation pairs from Qt Linguist .ts files and uses them
to populate gettext .po files for matching strings.
"""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

import polib

# Paths
TRENDS_EARTH_I18N = Path(__file__).parent.parent.parent / "trends.earth" / "LDMP" / "i18n"
API_UI_TRANSLATIONS = Path(__file__).parent.parent / "trendsearth_ui" / "i18n" / "translations"

# Language mapping from trends.earth codes to api-ui codes
LANGUAGE_MAP = {
    "ar": "ar",
    "es": "es",
    "fa": "fa",
    "fr": "fr",
    "pt": "pt",
    "ru": "ru",
    "sw": "sw",
    "zh": "zh",
}


def parse_ts_file(ts_path: Path) -> dict[str, str]:
    """Parse a Qt .ts file and return a dict of source -> translation pairs."""
    translations = {}

    try:
        tree = ET.parse(ts_path)
        root = tree.getroot()

        for message in root.iter("message"):
            source_elem = message.find("source")
            translation_elem = message.find("translation")

            if source_elem is not None and translation_elem is not None:
                source = source_elem.text or ""
                translation = translation_elem.text or ""

                # Skip empty translations or unfinished ones
                if translation and translation_elem.get("type") != "unfinished":
                    # Clean up the source text (remove HTML, normalize whitespace)
                    source_clean = clean_string(source)
                    if source_clean:
                        translations[source_clean] = clean_string(translation)

    except Exception as e:
        print(f"Error parsing {ts_path}: {e}")

    return translations


def clean_string(s: str) -> str:
    """Clean and normalize a string for matching."""
    if not s:
        return ""
    # Remove leading/trailing whitespace
    s = s.strip()
    # Normalize internal whitespace
    s = re.sub(r"\s+", " ", s)
    return s


def update_po_file(po_path: Path, translations: dict[str, str]) -> int:
    """Update a .po file with translations from the dictionary.

    Returns the number of translations added.
    """
    if not po_path.exists():
        print(f"  PO file not found: {po_path}")
        return 0

    po = polib.pofile(str(po_path))
    updated = 0

    # Check both regular and obsolete entries
    all_entries = list(po) + list(po.obsolete_entries())

    for entry in all_entries:
        msgid = entry.msgid

        # Skip if already translated
        if entry.msgstr:
            continue

        # Try to find a matching translation
        if msgid in translations:
            entry.msgstr = translations[msgid]
            updated += 1
        else:
            # Try case-insensitive match
            for source, translation in translations.items():
                if source.lower() == msgid.lower():
                    entry.msgstr = translation
                    updated += 1
                    break

    if updated > 0:
        po.save()

    return updated


def main():
    """Main entry point."""
    print("Importing translations from trends.earth to trends.earth-api-ui...")
    print(f"Source: {TRENDS_EARTH_I18N}")
    print(f"Target: {API_UI_TRANSLATIONS}")
    print()

    if not TRENDS_EARTH_I18N.exists():
        print(f"Error: trends.earth i18n directory not found: {TRENDS_EARTH_I18N}")
        return

    total_updated = 0

    for ts_code, po_code in LANGUAGE_MAP.items():
        ts_file = TRENDS_EARTH_I18N / f"LDMP_{ts_code}.ts"
        po_file = API_UI_TRANSLATIONS / po_code / "LC_MESSAGES" / "messages.po"

        if not ts_file.exists():
            print(f"  Skipping {ts_code}: .ts file not found")
            continue

        print(f"Processing {ts_code}...")

        # Parse the .ts file
        translations = parse_ts_file(ts_file)
        print(f"  Found {len(translations)} translations in .ts file")

        # Update the .po file
        updated = update_po_file(po_file, translations)
        print(f"  Updated {updated} strings in .po file")

        total_updated += updated

    print()
    print(f"Total translations imported: {total_updated}")


if __name__ == "__main__":
    main()
