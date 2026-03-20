"""Dash-specific internationalization utilities.

This module provides utilities for integrating Flask-Babel translations
with Dash components, including a language selector component and
callbacks for dynamic language switching.
"""

import os

from dash import Input, Output, callback, clientside_callback, dcc, html
import dash_bootstrap_components as dbc

from . import (
    SUPPORTED_LANGUAGES,
    get_current_language,
)


def create_language_selector(id_prefix: str = "lang") -> dbc.DropdownMenu:
    """Create a language selector dropdown component.

    Args:
        id_prefix: Prefix for component IDs to avoid conflicts.

    Returns:
        dbc.DropdownMenu: A Bootstrap dropdown menu for language selection.
    """
    return dbc.DropdownMenu(
        id=f"{id_prefix}-selector",
        label="🌐 Select language",
        children=[
            dbc.DropdownMenuItem(
                name,
                id=f"{id_prefix}-{code}",
                n_clicks=0,
            )
            for code, name in SUPPORTED_LANGUAGES.items()
        ],
        nav=False,
        in_navbar=False,
        color="link",
        toggle_style={
            "cursor": "pointer",
            "color": "#6c757d",  # Bootstrap text-muted grey
            "fontSize": "13px",
            "padding": "0",
            "textDecoration": "none",
        },
        className="p-0",
    )


def create_language_store() -> dcc.Store:
    """Create a dcc.Store component for persisting language selection.

    Returns:
        dcc.Store: A storage component for the selected language.
    """
    return dcc.Store(
        id="language-store",
        storage_type="memory",  # Use memory - we handle persistence manually via localStorage
        data=None,  # Start with None to detect browser language on first load
    )


def create_language_controls() -> list:
    """Create all components needed for language selection.

    Returns:
        list: A list of Dash components for language handling.
    """
    return [
        create_language_store(),
        # Hidden div to trigger page refresh on language change
        html.Div(id="language-refresh-trigger", style={"display": "none"}),
        # Hidden div to trigger browser language detection on initial load
        html.Div(id="browser-language-detector", style={"display": "none"}),
    ]


# Client-side callback for language persistence and page reload
# This stores the language in localStorage and cookie
# Only reloads when user explicitly changes the language (not on initial detection)
LANGUAGE_PERSISTENCE_CALLBACK = """
function(lang, previousLang) {
    console.log('PERSISTENCE CALLBACK: lang=' + lang + ', previousLang=' + previousLang);
    if (lang) {
        localStorage.setItem('trendsearth_language', lang);
        console.log('Saved to localStorage: ' + localStorage.getItem('trendsearth_language'));
        // Set cookie for server-side detection (1 year expiry)
        document.cookie = 'trendsearth_language=' + lang + ';path=/;max-age=31536000;SameSite=Lax';
        // Only reload if there was a previous language and it's different
        // This prevents reload on initial page load when browser language is detected
        if (previousLang && previousLang !== lang) {
            console.log('Reloading page...');
            // Small delay to ensure localStorage write completes
            setTimeout(function() {
                // If the URL has a lang= query parameter, update it to match
                // the new language so it won't override the selection after reload.
                // Use string replacement instead of the URL API to avoid
                // re-encoding other parameters (e.g. auth tokens).
                var href = window.location.href;
                if (/[?&]lang=/.test(href)) {
                    window.location.href = href.replace(/([?&]lang=)[^&]*/, '$1' + encodeURIComponent(lang));
                } else {
                    window.location.reload();
                }
            }, 50);
        }
    }
    // Store current language as the "previous" for next comparison
    return lang || '';
}
"""

# Client-side callback for updating dropdown label with current language
LANGUAGE_LABEL_UPDATE_CALLBACK = """
function(currentLang) {
    const langNames = {
        'en': '🌐 English',
        'ar': '🌐 العربية',
        'es': '🌐 Español',
        'fa': '🌐 فارسی',
        'fr': '🌐 Français',
        'pt': '🌐 Português',
        'ru': '🌐 Русский',
        'sw': '🌐 Kiswahili',
        'zh': '🌐 中文'
    };
    if (currentLang && langNames[currentLang]) {
        return langNames[currentLang];
    }
    return '🌐 Select language';
}
"""

# Client-side callback for browser language detection
# This detects the browser's language and sets it if supported
BROWSER_LANGUAGE_DETECTION_CALLBACK = """
function(currentLang) {
    console.log('DETECTION CALLBACK: currentLang=' + currentLang);
    console.log('localStorage value: ' + localStorage.getItem('trendsearth_language'));
    // Supported language codes
    const supportedLangs = ['en', 'ar', 'es', 'fa', 'fr', 'pt', 'ru', 'sw', 'zh'];

    // If a language is already set (from store), keep it
    if (currentLang && supportedLangs.includes(currentLang)) {
        console.log('Keeping current lang from store: ' + currentLang);
        return currentLang;
    }

    // Check localStorage first (might have been set in a previous session)
    const storedLang = localStorage.getItem('trendsearth_language');
    if (storedLang && supportedLangs.includes(storedLang)) {
        console.log('Using localStorage lang: ' + storedLang);
        return storedLang;
    }

    // Check cookie (fallback if localStorage was cleared)
    const cookieMatch = document.cookie.match(/trendsearth_language=([^;]+)/);
    if (cookieMatch) {
        const cookieLang = cookieMatch[1];
        if (supportedLangs.includes(cookieLang)) {
            console.log('Using cookie lang: ' + cookieLang);
            // Sync back to localStorage
            localStorage.setItem('trendsearth_language', cookieLang);
            return cookieLang;
        }
    }

    // Auto-detect from browser
    const browserLang = navigator.language || navigator.userLanguage || 'en';

    // Try exact match first (e.g., 'en-US' -> 'en')
    const langCode = browserLang.split('-')[0].toLowerCase();
    console.log('Detected browser lang: ' + langCode);

    if (supportedLangs.includes(langCode)) {
        // Store in localStorage and cookie for persistence
        localStorage.setItem('trendsearth_language', langCode);
        document.cookie = 'trendsearth_language=' + langCode + ';path=/;max-age=31536000;SameSite=Lax';
        return langCode;
    }

    // Default to English and save it
    console.log('Defaulting to English');
    localStorage.setItem('trendsearth_language', 'en');
    document.cookie = 'trendsearth_language=en;path=/;max-age=31536000;SameSite=Lax';
    return 'en';
}
"""


def register_language_callbacks(app):  # noqa: ARG001
    """Register language-related callbacks with the Dash app.

    Args:
        app: The Dash application instance.
    """
    from dash import State

    # Client-side callback to detect browser language on initial load
    clientside_callback(
        BROWSER_LANGUAGE_DETECTION_CALLBACK,
        Output("language-store", "data"),
        Input("language-store", "data"),
        prevent_initial_call=False,  # Run on initial load
    )

    # Client-side callback to persist language selection and reload page
    clientside_callback(
        LANGUAGE_PERSISTENCE_CALLBACK,
        Output("language-refresh-trigger", "children"),
        Input("language-store", "data"),
        State("language-refresh-trigger", "children"),
        prevent_initial_call=True,
    )

    # ID prefixes for language selectors (dashboard, login, register, reset password, standalone profile pages)
    id_prefixes = ["lang", "login-lang", "register-lang", "reset-lang", "standalone-profile-lang"]

    # Client-side callbacks to update each dropdown's label with the selected language
    for prefix in id_prefixes:
        clientside_callback(
            LANGUAGE_LABEL_UPDATE_CALLBACK,
            Output(f"{prefix}-selector", "label"),
            Input("language-store", "data"),
            prevent_initial_call=False,  # Run on initial load to show current language
        )

    # Create individual callbacks for each language option and each selector
    from dash import no_update

    for prefix in id_prefixes:
        for lang_code in SUPPORTED_LANGUAGES:

            @callback(
                Output("language-store", "data", allow_duplicate=True),
                Input(f"{prefix}-{lang_code}", "n_clicks"),
                prevent_initial_call=True,
            )
            def set_lang(n_clicks, lang=lang_code):
                if n_clicks:
                    return lang
                return no_update


def get_translation_file_path(lang_code: str = None) -> str:
    """Get the path to translation files.

    Args:
        lang_code: Optional language code for a specific language.

    Returns:
        str: The path to the translation directory or specific language file.
    """
    base_path = os.path.join(os.path.dirname(__file__), "translations")
    if lang_code:
        return os.path.join(base_path, lang_code, "LC_MESSAGES")
    return base_path


def load_client_translations(lang_code: str = None) -> dict[str, str]:
    """Load translations for client-side use (e.g., AG-Grid).

    This loads the translations into a dictionary that can be passed
    to client-side JavaScript components.

    Args:
        lang_code: The language code to load. Defaults to current language.

    Returns:
        dict: A dictionary of msgid -> msgstr translations.
    """
    if lang_code is None:
        lang_code = get_current_language()

    translations = {}
    po_path = os.path.join(get_translation_file_path(lang_code), "messages.po")

    if os.path.exists(po_path):
        try:
            # Simple PO file parser for client-side translations
            with open(po_path, encoding="utf-8") as f:
                content = f.read()

            # Parse msgid/msgstr pairs
            import re

            pattern = r'msgid\s+"(.+?)"\s*\nmsgstr\s+"(.+?)"'
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)

            for msgid, msgstr in matches:
                if msgstr:  # Only include translated strings
                    translations[msgid] = msgstr

        except OSError as e:
            print(f"Warning: Could not load translations for {lang_code}: {e}")

    return translations


def create_client_translations_store() -> dcc.Store:
    """Create a store for client-side translations.

    Returns:
        dcc.Store: A component storing translations for JavaScript access.
    """
    return dcc.Store(
        id="client-translations-store",
        data={},
    )
