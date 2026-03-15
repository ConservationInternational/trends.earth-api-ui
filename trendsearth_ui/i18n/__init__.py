"""Internationalization (i18n) support for Trends.Earth API UI.

This module provides translation support using Flask-Babel with gettext-based
PO files. It integrates with Transifex for collaborative translation management.

Usage:
    from trendsearth_ui.i18n import gettext as _, lazy_gettext as _l

    # In Python code:
    message = _("Hello, World!")

    # For lazy translation (e.g., in class attributes):
    label = _l("Submit")

Language Detection Priority:
    1. URL parameter (?lang=xx)
    2. Session cookie
    3. Accept-Language header
    4. Default language (English)
"""

import os
from typing import Optional

from flask import Flask, g, request, session
from flask_babel import Babel, force_locale, gettext, lazy_gettext, ngettext

# Supported languages - same as trends.earth main project
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ar": "العربية",  # Arabic
    "es": "Español",  # Spanish
    "fa": "فارسی",  # Farsi
    "fr": "Français",  # French
    "pt": "Português",  # Portuguese
    "ru": "Русский",  # Russian
    "sw": "Kiswahili",  # Swahili
    "zh": "中文",  # Chinese
}

DEFAULT_LANGUAGE = "en"
LANGUAGE_COOKIE_NAME = "trendsearth_language"

# Babel instance - initialized when init_i18n is called
babel: Optional[Babel] = None


def get_locale() -> str:
    """Determine the best language for the current request.

    Priority:
        1. URL parameter (?lang=xx)
        2. Browser cookie (set by JavaScript)
        3. Flask session
        4. Accept-Language header
        5. Default language

    Returns:
        str: The selected language code.
    """
    # Check URL parameter
    lang = request.args.get("lang")
    if lang and lang in SUPPORTED_LANGUAGES:
        # Store in session for persistence
        session[LANGUAGE_COOKIE_NAME] = lang
        return lang

    # Check browser cookie (set by JavaScript language selector)
    lang = request.cookies.get(LANGUAGE_COOKIE_NAME)
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # Check Flask session (server-side)
    lang = session.get(LANGUAGE_COOKIE_NAME)
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # Check Accept-Language header
    best_match = request.accept_languages.best_match(SUPPORTED_LANGUAGES.keys())
    if best_match:
        return best_match

    return DEFAULT_LANGUAGE


def get_timezone() -> str:
    """Get the timezone for the current user.

    Returns:
        str: The timezone string (e.g., 'UTC', 'America/New_York').
    """
    # First check if user has set a timezone preference
    user_tz = getattr(g, "timezone", None)
    if user_tz:
        return user_tz

    # Default to UTC
    return "UTC"


def init_i18n(app: Flask) -> Babel:
    """Initialize internationalization for the Flask application.

    Args:
        app: The Flask application instance.

    Returns:
        Babel: The configured Babel instance.
    """
    global babel

    # Configure Babel
    app.config.setdefault("BABEL_DEFAULT_LOCALE", DEFAULT_LANGUAGE)
    app.config.setdefault("BABEL_DEFAULT_TIMEZONE", "UTC")

    # Set translations directory - relative to this file
    translations_dir = os.path.join(os.path.dirname(__file__), "translations")
    app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", translations_dir)

    # Initialize Babel with locale and timezone selectors
    babel = Babel(app, locale_selector=get_locale, timezone_selector=get_timezone)

    # Register the language context processor for templates
    @app.context_processor
    def inject_i18n():
        """Inject i18n utilities into template context."""
        return {
            "current_language": get_locale(),
            "supported_languages": SUPPORTED_LANGUAGES,
            "_": gettext,
            "_l": lazy_gettext,
        }

    return babel


def set_language(lang: str) -> bool:
    """Set the language for the current session.

    Args:
        lang: The language code to set.

    Returns:
        bool: True if the language was set successfully, False otherwise.
    """
    if lang in SUPPORTED_LANGUAGES:
        session[LANGUAGE_COOKIE_NAME] = lang
        return True
    return False


def get_current_language() -> str:
    """Get the current language code.

    Returns:
        str: The current language code.
    """
    return get_locale()


def get_language_name(lang_code: str) -> str:
    """Get the display name for a language code.

    Args:
        lang_code: The language code (e.g., 'en', 'fr').

    Returns:
        str: The display name for the language.
    """
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)


# Re-export commonly used functions
__all__ = [
    "babel",
    "DEFAULT_LANGUAGE",
    "force_locale",
    "get_current_language",
    "get_language_name",
    "get_locale",
    "get_timezone",
    "gettext",
    "init_i18n",
    "lazy_gettext",
    "LANGUAGE_COOKIE_NAME",
    "ngettext",
    "set_language",
    "SUPPORTED_LANGUAGES",
]
