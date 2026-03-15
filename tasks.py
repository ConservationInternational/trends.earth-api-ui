"""Invoke tasks for Trends.Earth API UI development.

This module provides automation tasks for building, testing, and managing
translations using the invoke task runner.

Usage:
    invoke --list              # List all available tasks
    invoke translate-extract   # Extract translatable strings
    invoke translate-update    # Update PO files from POT
    invoke translate-compile   # Compile PO files to MO
    invoke translate-pull      # Pull translations from Transifex
    invoke translate-push      # Push source strings to Transifex
"""

import os
from pathlib import Path
import subprocess
import sys

from invoke import Collection, Context, task

# Project paths
PROJECT_ROOT = Path(__file__).parent
TRANSLATIONS_DIR = PROJECT_ROOT / "trendsearth_ui" / "i18n" / "translations"
POT_FILE = TRANSLATIONS_DIR / "messages.pot"
BABEL_CFG = PROJECT_ROOT / "babel.cfg"

# Supported languages (same as trends.earth)
SUPPORTED_LANGUAGES = ["ar", "en", "es", "fa", "fr", "pt", "ru", "sw", "zh"]


def check_command(command: str) -> bool:
    """Check if a command is available in the system PATH."""
    try:
        subprocess.run(
            [command, "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


###############################################################################
# Translation Tasks
###############################################################################


@task(
    help={
        "verbose": "Show verbose output",
    }
)
def translate_extract(c: Context, verbose: bool = False):
    """Extract translatable strings from source code into POT file.

    This creates/updates the messages.pot template file with all translatable
    strings found in the Python source code.
    """
    print("Extracting translatable strings...")

    cmd = [
        "pybabel",
        "extract",
        "-k",
        "_",
        "-k",
        "_g",
        "-k",
        "_l",
        "-k",
        "gettext",
        "-k",
        "lazy_gettext",
        "-o",
        str(POT_FILE),
        "trendsearth_ui/",
    ]

    if verbose:
        cmd.append("-v")

    result = c.run(" ".join(cmd), warn=True)

    if result.ok:
        print(f"Successfully extracted strings to {POT_FILE}")
    else:
        print("Failed to extract strings")
        sys.exit(1)


@task(
    help={
        "language": "Specific language to update (default: all)",
        "no_fuzzy": "Don't use fuzzy matching",
    }
)
def translate_update(c: Context, language: str = None, no_fuzzy: bool = True):
    """Update PO files from the POT template.

    This merges new translatable strings from the POT file into the PO files
    for each language.
    """
    languages = [language] if language else SUPPORTED_LANGUAGES

    print("Updating PO files from POT template...")

    for lang in languages:
        po_dir = TRANSLATIONS_DIR / lang / "LC_MESSAGES"
        po_file = po_dir / "messages.po"

        if not po_file.exists():
            print(f"  Initializing new language: {lang}")
            po_dir.mkdir(parents=True, exist_ok=True)
            cmd = [
                "pybabel",
                "init",
                "-i",
                str(POT_FILE),
                "-d",
                str(TRANSLATIONS_DIR),
                "-l",
                lang,
            ]
        else:
            print(f"  Updating: {lang}")
            cmd = [
                "pybabel",
                "update",
                "-i",
                str(POT_FILE),
                "-d",
                str(TRANSLATIONS_DIR),
                "-l",
                lang,
            ]
            if no_fuzzy:
                cmd.append("--no-fuzzy-matching")

        result = c.run(" ".join(cmd), warn=True)

        if not result.ok:
            print(f"  Warning: Failed to update {lang}")


@task
def translate_compile(c: Context):
    """Compile PO files to MO files.

    This compiles the human-readable PO files into binary MO files that are
    used at runtime.
    """
    print("Compiling translation files...")

    cmd = [
        "pybabel",
        "compile",
        "-d",
        str(TRANSLATIONS_DIR),
    ]

    result = c.run(" ".join(cmd), warn=True)

    if result.ok:
        print("Successfully compiled translations")
    else:
        print("Failed to compile translations")
        sys.exit(1)


@task(
    help={
        "force": "Force download regardless of timestamps",
    }
)
def translate_pull(c: Context, force: bool = False):
    """Pull translations from Transifex.

    Downloads the latest translations from Transifex. Requires TX_TOKEN
    environment variable to be set.
    """
    if not os.environ.get("TX_TOKEN"):
        print("Warning: TX_TOKEN environment variable not set")
        print("Set TX_TOKEN to your Transifex API token")

    print("Pulling translations from Transifex...")

    cmd = ["tx", "pull"]
    if force:
        cmd.append("-f")

    result = c.run(" ".join(cmd), warn=True)

    if result.ok:
        # Compile after pulling
        translate_compile(c)
        print("Successfully pulled and compiled translations")
    else:
        print("Failed to pull translations from Transifex")


@task(
    help={
        "force": "Force push regardless of timestamps",
    }
)
def translate_push(c: Context, force: bool = False):
    """Push source strings to Transifex.

    Uploads the POT file to Transifex for translation. Requires TX_TOKEN
    environment variable to be set.
    """
    if not os.environ.get("TX_TOKEN"):
        print("Warning: TX_TOKEN environment variable not set")
        print("Set TX_TOKEN to your Transifex API token")

    # First extract and update
    translate_extract(c)
    translate_update(c)

    print("Pushing source strings to Transifex...")

    cmd = ["tx", "push", "-s"]
    if force:
        cmd.append("-f")

    result = c.run(" ".join(cmd), warn=True)

    if result.ok:
        print("Successfully pushed source strings to Transifex")
    else:
        print("Failed to push to Transifex")


@task
def translate_status(c: Context):  # noqa: ARG001
    """Show translation status for all languages.

    Displays completion statistics for each language.
    """
    print("Translation status:")
    print("-" * 60)

    try:
        import polib
    except ImportError:
        print("Error: polib not installed. Run: pip install polib")
        return

    for lang in SUPPORTED_LANGUAGES:
        po_file = TRANSLATIONS_DIR / lang / "LC_MESSAGES" / "messages.po"

        if not po_file.exists():
            print(f"  {lang}: Not initialized")
            continue

        po = polib.pofile(str(po_file))
        total = len([e for e in po if e.msgid])
        translated = len(po.translated_entries())
        fuzzy = len(po.fuzzy_entries())
        untranslated = len(po.untranslated_entries())

        pct = (translated / total) * 100 if total > 0 else 0

        print(
            f"  {lang}: {translated}/{total} ({pct:.1f}%) - fuzzy: {fuzzy}, untranslated: {untranslated}"
        )


@task
def translate_init(c: Context, language: str):
    """Initialize a new language for translation.

    Args:
        language: The language code to initialize (e.g., 'de' for German)
    """
    if not language:
        print("Error: Language code required")
        print("Usage: invoke translate-init --language de")
        return

    print(f"Initializing new language: {language}")

    po_dir = TRANSLATIONS_DIR / language / "LC_MESSAGES"
    po_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pybabel",
        "init",
        "-i",
        str(POT_FILE),
        "-d",
        str(TRANSLATIONS_DIR),
        "-l",
        language,
    ]

    result = c.run(" ".join(cmd), warn=True)

    if result.ok:
        print(f"Successfully initialized {language}")
        print(f"Edit: {po_dir / 'messages.po'}")
    else:
        print(f"Failed to initialize {language}")


###############################################################################
# Development Tasks
###############################################################################


@task
def dev(c: Context):
    """Run the development server."""
    print("Starting development server...")
    c.run(f"{sys.executable} -m trendsearth_ui.app", pty=True)


@task
def test(c: Context, coverage: bool = True, verbose: bool = True):
    """Run the test suite."""
    cmd = [sys.executable, "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=trendsearth_ui", "--cov-report=html"])

    c.run(" ".join(cmd))


@task
def lint(c: Context, fix: bool = False):
    """Run linting checks."""
    cmd = ["ruff", "check", "trendsearth_ui/", "tests/"]

    if fix:
        cmd.append("--fix")

    c.run(" ".join(cmd))


@task
def format(c: Context, check: bool = False):
    """Format code with ruff."""
    cmd = ["ruff", "format", "trendsearth_ui/", "tests/"]

    if check:
        cmd.append("--check")

    c.run(" ".join(cmd))


###############################################################################
# Task Collections
###############################################################################

# Create the namespace
ns = Collection()

# Add translation tasks with shorter names
translate = Collection("translate")
translate.add_task(translate_extract, name="extract")
translate.add_task(translate_update, name="update")
translate.add_task(translate_compile, name="compile")
translate.add_task(translate_pull, name="pull")
translate.add_task(translate_push, name="push")
translate.add_task(translate_status, name="status")
translate.add_task(translate_init, name="init")

ns.add_collection(translate)

# Add development tasks
ns.add_task(dev)
ns.add_task(test)
ns.add_task(lint)
ns.add_task(format, name="format")

# Also add translate tasks at top level for convenience
ns.add_task(translate_extract)
ns.add_task(translate_update)
ns.add_task(translate_compile)
ns.add_task(translate_pull)
ns.add_task(translate_push)
ns.add_task(translate_status)
ns.add_task(translate_init)
