#!/usr/bin/env python3
"""Merge translations from git history with newly generated PO files.

This script is used to recover translations that were lost when the
translation_update.yml workflow had incorrect extraction keywords. It:
1. Reads old PO files (from git history) with existing translations
2. Reads new PO files (freshly generated with correct keywords)
3. Merges them: for each msgid in new PO, copy msgstr from old PO if available
4. Preserves translator metadata and comments
5. Writes the merged PO files back to disk

Usage:
    # First, extract old PO files from git:
    cd trends.earth-api-ui
    OLD_COMMIT=$(git log --before="2026-05-03" --oneline -- trendsearth_ui/i18n/translations/*.po | head -1 | cut -d' ' -f1)

    # For each language, extract to temp directory:
    mkdir -p /tmp/old_translations
    for lang in ar es fa fr pt ru sw zh; do
        git show $OLD_COMMIT:trendsearth_ui/i18n/translations/$lang/LC_MESSAGES/messages.po > /tmp/old_translations/${lang}.po
    done

    # Run this script:
    python scripts/merge_translations.py \
        --old-dir /tmp/old_translations \
        --new-dir trendsearth_ui/i18n/translations \
        --languages ar,es,fa,fr,pt,ru,sw,zh

Requirements:
    - polib

Note:
    This script is for one-time recovery of lost translations.
    After running, commit the merged PO files and push to Transifex.
"""

import argparse
from datetime import datetime
from pathlib import Path
import sys

try:
    import polib
except ImportError:
    print("Missing dependency: polib")
    print("Install with: pip install polib")
    sys.exit(1)


def merge_po_files(old_po_path: Path, new_po_path: Path, output_po_path: Path, lang: str) -> dict:
    """Merge translations from old PO file into new PO file.

    Args:
        old_po_path: Path to old PO file with existing translations
        new_po_path: Path to new PO file with complete msgid list
        output_po_path: Path where merged PO file should be saved
        lang: Language code (for reporting)

    Returns:
        Dictionary with merge statistics
    """
    stats = {
        "language": lang,
        "total_new": 0,
        "recovered": 0,
        "missing": 0,
        "empty_in_old": 0,
    }

    # Load both PO files
    try:
        old_po = polib.pofile(str(old_po_path))
    except Exception as e:
        print(f"  ⚠️  Error reading old PO file for {lang}: {e}")
        return stats

    try:
        new_po = polib.pofile(str(new_po_path))
    except Exception as e:
        print(f"  ⚠️  Error reading new PO file for {lang}: {e}")
        return stats

    # Create mapping of msgid -> entry for quick lookup in old PO
    old_translations = {}
    for entry in old_po:
        if entry.msgid:  # Skip empty msgid (metadata entry)
            old_translations[entry.msgid] = entry

    # Track statistics
    stats["total_new"] = len([e for e in new_po if e.msgid])

    # Merge translations
    for new_entry in new_po:
        if not new_entry.msgid:
            # Skip metadata entry at the beginning of PO file
            continue

        # Look for matching msgid in old translations
        old_entry = old_translations.get(new_entry.msgid)

        if old_entry:
            # Found matching msgid in old PO file
            if old_entry.msgstr and old_entry.msgstr.strip():
                # Old entry has a non-empty translation, copy it over
                new_entry.msgstr = old_entry.msgstr
                stats["recovered"] += 1

                # Preserve translator comments (lines starting with #)
                if old_entry.comment:
                    new_entry.comment = old_entry.comment

                # Mark as fuzzy if it was fuzzy in old file
                if "fuzzy" in old_entry.flags:
                    new_entry.flags.append("fuzzy")
            else:
                # Old entry exists but msgstr is empty
                stats["empty_in_old"] += 1
        else:
            # This msgid didn't exist in old PO file (new string)
            stats["missing"] += 1

    # Update metadata in header
    new_po.metadata["PO-Revision-Date"] = datetime.now().strftime("%Y-%m-%d %H:%M%z")

    # Preserve Last-Translator from old file if available
    if old_po.metadata.get("Last-Translator"):
        new_po.metadata["Last-Translator"] = old_po.metadata["Last-Translator"]

    # Add note about merge in header comment
    merge_note = f"Translations merged from git history on {datetime.now().strftime('%Y-%m-%d')}"
    if new_po.header:
        new_po.header = new_po.header + f"\n{merge_note}\n"
    else:
        new_po.header = merge_note

    # Save merged PO file
    try:
        new_po.save(str(output_po_path))
    except Exception as e:
        print(f"  ⚠️  Error saving merged PO file for {lang}: {e}")
        return stats

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Merge translations from old PO files (git history) with new PO files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--old-dir",
        required=True,
        help="Directory containing old PO files from git history (e.g., /tmp/old_translations/)",
    )
    parser.add_argument(
        "--new-dir",
        required=True,
        help="Directory containing new PO files (e.g., trendsearth_ui/i18n/translations/)",
    )
    parser.add_argument(
        "--languages",
        required=True,
        help="Comma-separated list of language codes (e.g., ar,es,fa,fr,pt,ru,sw,zh)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without modifying files",
    )

    args = parser.parse_args()

    # Parse language list
    languages = [lang.strip() for lang in args.languages.split(",")]

    # Validate directories
    old_dir = Path(args.old_dir)
    new_dir = Path(args.new_dir)

    if not old_dir.exists():
        print(f"❌ Old directory not found: {old_dir}")
        print("Did you extract old PO files from git history?")
        return 1

    if not new_dir.exists():
        print(f"❌ New directory not found: {new_dir}")
        print("Did you run 'poetry run invoke translate-extract' and 'translate-update'?")
        return 1

    print("=" * 70)
    print("Translation Merge Tool")
    print("=" * 70)
    print(f"Old translations: {old_dir}")
    print(f"New translations: {new_dir}")
    print(f"Languages: {', '.join(languages)}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Process each language
    all_stats = []
    for lang in languages:
        print(f"Processing {lang}...")

        # Determine file paths
        # Old files are in flat structure: /tmp/old_translations/es.po
        old_po_path = old_dir / f"{lang}.po"

        # New files are in locale structure: trendsearth_ui/i18n/translations/es/LC_MESSAGES/messages.po
        new_po_path = new_dir / lang / "LC_MESSAGES" / "messages.po"
        output_po_path = new_po_path  # Overwrite the new file with merged content

        # Check if files exist
        if not old_po_path.exists():
            print(f"  ⚠️  Old PO file not found: {old_po_path}")
            continue

        if not new_po_path.exists():
            print(f"  ⚠️  New PO file not found: {new_po_path}")
            continue

        # Merge translations
        if args.dry_run:
            print(f"  [DRY RUN] Would merge {old_po_path} → {output_po_path}")
            # Still parse files to show stats
            try:
                old_po = polib.pofile(str(old_po_path))
                new_po = polib.pofile(str(new_po_path))
                old_count = len([e for e in old_po if e.msgid and e.msgstr and e.msgstr.strip()])
                new_count = len([e for e in new_po if e.msgid])
                print(f"  Old translations: {old_count}")
                print(f"  New strings: {new_count}")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")
        else:
            stats = merge_po_files(old_po_path, new_po_path, output_po_path, lang)
            all_stats.append(stats)

            print("  ✅ Merged successfully")
            print(f"     Total strings in new PO: {stats['total_new']}")
            print(f"     Recovered from old PO: {stats['recovered']}")
            print(f"     New strings (not in old): {stats['missing']}")
            print(f"     Empty in old PO: {stats['empty_in_old']}")

    # Print summary
    if not args.dry_run and all_stats:
        print()
        print("=" * 70)
        print("Merge Summary")
        print("=" * 70)
        print(f"{'Language':<10} {'Total':<8} {'Recovered':<12} {'New':<8} {'Empty Old':<12}")
        print("-" * 70)

        total_total = 0
        total_recovered = 0
        total_new = 0
        total_empty = 0

        for stats in all_stats:
            print(
                f"{stats['language']:<10} "
                f"{stats['total_new']:<8} "
                f"{stats['recovered']:<12} "
                f"{stats['missing']:<8} "
                f"{stats['empty_in_old']:<12}"
            )
            total_total += stats["total_new"]
            total_recovered += stats["recovered"]
            total_new += stats["missing"]
            total_empty += stats["empty_in_old"]

        print("-" * 70)
        print(
            f"{'TOTAL':<10} {total_total:<8} {total_recovered:<12} {total_new:<8} {total_empty:<12}"
        )

        if total_total > 0:
            recovery_rate = (total_recovered / total_total) * 100
            print()
            print(
                f"📊 Recovery rate: {recovery_rate:.1f}% ({total_recovered}/{total_total} strings)"
            )

        print()
        print("✅ Translation merge complete!")
        print()
        print("Next steps:")
        print("  1. Review the merged PO files")
        print("  2. Compile translations: poetry run invoke translate-compile")
        print("  3. Test language switching in the UI")
        print("  4. Push to Transifex: poetry run invoke translate-push")
        print("  5. Commit and push the changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
