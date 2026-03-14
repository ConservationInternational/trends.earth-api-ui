#!/usr/bin/env python3
"""Machine translation script using Google Cloud Translation API.

This script reads untranslated strings from PO files and uses Google Cloud
Translation API to provide machine translations. It can be used to prepopulate
translations before human review.

Usage:
    python scripts/machine_translate.py \
        --source-lang en \
        --target-langs es,fr,ar \
        --pot-file trendsearth_ui/i18n/translations/messages.pot \
        --translations-dir trendsearth_ui/i18n/translations

Requirements:
    - google-cloud-translate
    - polib
    - GOOGLE_APPLICATION_CREDENTIALS environment variable set

Note:
    Machine translations are provided as a starting point and should be
    reviewed by human translators before deployment.
"""

import argparse
import os
from pathlib import Path
import sys

try:
    from google.cloud import translate_v2 as translate
    import polib
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install google-cloud-translate polib")
    sys.exit(1)


# Language code mapping: Internal code -> Google Translate code
LANGUAGE_CODE_MAP = {
    "ar": "ar",  # Arabic
    "es": "es",  # Spanish
    "fa": "fa",  # Farsi/Persian
    "fr": "fr",  # French
    "pt": "pt",  # Portuguese
    "ru": "ru",  # Russian
    "sw": "sw",  # Swahili
    "zh": "zh-CN",  # Chinese (Simplified)
}


def get_translate_client():
    """Create and return a Google Cloud Translation client."""
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("Warning: GOOGLE_APPLICATION_CREDENTIALS not set")
        print("Using default credentials if available")
    return translate.Client()


def translate_text(client, text: str, source_lang: str, target_lang: str) -> str:
    """Translate text using Google Cloud Translation API.

    Args:
        client: Google Cloud Translation client
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code

    Returns:
        Translated text
    """
    if not text or not text.strip():
        return ""

    # Map language codes to Google Translate codes
    google_target = LANGUAGE_CODE_MAP.get(target_lang, target_lang)

    try:
        result = client.translate(
            text,
            source_language=source_lang,
            target_language=google_target,
        )
        return result["translatedText"]
    except Exception as e:
        print(f"  Warning: Translation failed for '{text[:50]}...': {e}")
        return ""


def process_po_file(
    client,
    po_path: Path,
    source_lang: str,
    target_lang: str,
    overwrite: bool = False,
) -> tuple[int, int]:
    """Process a PO file and add machine translations.

    Args:
        client: Google Cloud Translation client
        po_path: Path to the PO file
        source_lang: Source language code
        target_lang: Target language code
        overwrite: Whether to overwrite existing translations

    Returns:
        Tuple of (translated_count, skipped_count)
    """
    if not po_path.exists():
        print(f"  Warning: PO file not found: {po_path}")
        return 0, 0

    po = polib.pofile(str(po_path))
    translated = 0
    skipped = 0

    for entry in po:
        # Skip if msgid is empty
        if not entry.msgid or not entry.msgid.strip():
            continue

        # Skip if already translated and not overwriting
        if entry.msgstr and entry.msgstr.strip() and not overwrite:
            skipped += 1
            continue

        # Skip plural forms for now (they need special handling)
        if entry.msgid_plural:
            continue

        # Translate
        translation = translate_text(client, entry.msgid, source_lang, target_lang)
        if translation:
            entry.msgstr = translation
            # Mark as fuzzy to indicate machine translation
            if "fuzzy" not in entry.flags:
                entry.flags.append("fuzzy")
            translated += 1

    # Save the file
    po.save()

    return translated, skipped


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Prepopulate translations using Google Cloud Translation API"
    )
    parser.add_argument(
        "--source-lang",
        default="en",
        help="Source language code (default: en)",
    )
    parser.add_argument(
        "--target-langs",
        required=True,
        help="Comma-separated list of target language codes",
    )
    parser.add_argument(
        "--pot-file",
        type=Path,
        required=True,
        help="Path to the POT template file",
    )
    parser.add_argument(
        "--translations-dir",
        type=Path,
        required=True,
        help="Path to the translations directory",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing translations",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.pot_file.exists():
        print(f"Error: POT file not found: {args.pot_file}")
        sys.exit(1)

    if not args.translations_dir.exists():
        print(f"Error: Translations directory not found: {args.translations_dir}")
        sys.exit(1)

    # Parse target languages
    target_langs = [lang.strip() for lang in args.target_langs.split(",")]

    print(f"Source language: {args.source_lang}")
    print(f"Target languages: {', '.join(target_langs)}")
    print(f"Overwrite existing: {args.overwrite}")
    print()

    # Initialize translation client
    try:
        client = get_translate_client()
    except Exception as e:
        print(f"Error initializing translation client: {e}")
        sys.exit(1)

    # Process each target language
    total_translated = 0
    total_skipped = 0

    for target_lang in target_langs:
        print(f"Processing {target_lang}...")

        # Find the PO file
        po_path = args.translations_dir / target_lang / "LC_MESSAGES" / "messages.po"

        if not po_path.exists():
            print(f"  Creating new PO file for {target_lang}")
            # Create from POT template
            po_path.parent.mkdir(parents=True, exist_ok=True)
            pot = polib.pofile(str(args.pot_file))
            pot.metadata["Language"] = target_lang
            pot.save(str(po_path))

        translated, skipped = process_po_file(
            client,
            po_path,
            args.source_lang,
            target_lang,
            args.overwrite,
        )

        print(f"  Translated: {translated}, Skipped: {skipped}")
        total_translated += translated
        total_skipped += skipped

    print()
    print(f"Total translated: {total_translated}")
    print(f"Total skipped: {total_skipped}")


if __name__ == "__main__":
    main()
