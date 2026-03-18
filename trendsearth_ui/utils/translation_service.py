"""Translation service using Google Cloud Translation API.

This module provides machine translation functionality for news items
using the Google Cloud Translation API v2.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

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

# Languages that need translation (excludes English which is the source)
TRANSLATABLE_LANGUAGES = list(LANGUAGE_CODE_MAP.keys())

# Language display names
LANGUAGE_NAMES = {
    "en": "English",
    "ar": "العربية (Arabic)",
    "es": "Español (Spanish)",
    "fa": "فارسی (Farsi)",
    "fr": "Français (French)",
    "pt": "Português (Portuguese)",
    "ru": "Русский (Russian)",
    "sw": "Kiswahili (Swahili)",
    "zh": "中文 (Chinese)",
}

# Global translate client (lazy initialized)
_translate_client = None


def _get_credentials_from_env() -> Optional[dict]:
    """Get Google Cloud credentials from environment variable.

    Looks for GOOGLE_TRANSLATE_CREDENTIALS which should contain
    the JSON service account credentials as a string.

    Returns:
        Parsed credentials dict or None if not available.
    """
    creds_json = os.environ.get("GOOGLE_TRANSLATE_CREDENTIALS")
    if not creds_json:
        logger.warning("GOOGLE_TRANSLATE_CREDENTIALS environment variable not set")
        return None

    try:
        return json.loads(creds_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GOOGLE_TRANSLATE_CREDENTIALS: {e}")
        return None


def get_translate_client():
    """Get or create the Google Cloud Translation client.

    Uses credentials from GOOGLE_TRANSLATE_CREDENTIALS environment variable.

    Returns:
        Google Cloud Translation client or None if credentials unavailable.
    """
    global _translate_client

    if _translate_client is not None:
        return _translate_client

    try:
        from google.cloud import translate_v2 as translate
        from google.oauth2 import service_account
    except ImportError:
        logger.error(
            "google-cloud-translate not installed. Install with: pip install google-cloud-translate"
        )
        return None

    # Try to get credentials from environment variable
    creds_dict = _get_credentials_from_env()
    if creds_dict:
        try:
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            _translate_client = translate.Client(credentials=credentials)
            logger.info("Google Translate client initialized with credentials")
            return _translate_client
        except Exception as e:
            logger.error(f"Failed to create credentials from env: {e}")

    # Fallback: try default credentials (e.g., GOOGLE_APPLICATION_CREDENTIALS file)
    try:
        _translate_client = translate.Client()
        logger.info("Google Translate client initialized with default credentials")
        return _translate_client
    except Exception as e:
        logger.error(f"Failed to create Google Translate client: {e}")
        return None


def translate_text(
    text: str,
    target_lang: str,
    source_lang: str = "en",
) -> Optional[str]:
    """Translate text using Google Cloud Translation API.

    Args:
        text: Text to translate
        target_lang: Target language code (e.g., 'es', 'fr', 'zh')
        source_lang: Source language code (default: 'en')

    Returns:
        Translated text or None if translation failed.
    """
    if not text or not text.strip():
        return ""

    client = get_translate_client()
    if not client:
        logger.error("Translation client not available")
        return None

    # Map to Google Translate language code
    google_target = LANGUAGE_CODE_MAP.get(target_lang, target_lang)

    # Preserve newlines by replacing with <br> tags
    # Using HTML format ensures Google Translate preserves the tags
    preserved_text = text.replace("\n", "<br/>")

    try:
        result = client.translate(
            preserved_text,
            source_language=source_lang,
            target_language=google_target,
            format_="html",  # Use HTML format to preserve <br> tags
        )
        translated = result.get("translatedText", "")
        # Google Translate may escape HTML entities, decode them
        import html

        translated = html.unescape(translated)
        # Restore newlines from <br> tags (handle both <br> and <br/>)
        translated = translated.replace("<br/>", "\n").replace("<br>", "\n")
        return translated
    except Exception as e:
        logger.error(f"Translation failed for '{target_lang}': {e}")
        return None


def translate_news_item(
    title: str,
    message: str,
    link_text: Optional[str] = None,
    target_lang: str = "es",
    source_lang: str = "en",
) -> Optional[dict]:
    """Translate a news item (title, message, link_text) to target language.

    Args:
        title: News item title
        message: News item message (markdown)
        link_text: Optional link text
        target_lang: Target language code
        source_lang: Source language code (default: 'en')

    Returns:
        Dictionary with translated fields or None if translation failed.
    """
    translated_title = translate_text(title, target_lang, source_lang)
    if translated_title is None:
        return None

    translated_message = translate_text(message, target_lang, source_lang)
    if translated_message is None:
        return None

    result = {
        "title": translated_title,
        "message": translated_message,
        "is_machine_translated": True,
    }

    if link_text:
        translated_link = translate_text(link_text, target_lang, source_lang)
        if translated_link:
            result["link_text"] = translated_link

    return result


def translate_to_all_languages(
    title: str,
    message: str,
    link_text: Optional[str] = None,
    source_lang: str = "en",
) -> dict[str, dict]:
    """Translate a news item to all supported languages.

    Args:
        title: News item title
        message: News item message (markdown)
        link_text: Optional link text
        source_lang: Source language code (default: 'en')

    Returns:
        Dictionary mapping language codes to translated content.
        Failed translations are omitted from the result.
    """
    translations = {}

    for lang in TRANSLATABLE_LANGUAGES:
        if lang == source_lang:
            continue

        result = translate_news_item(
            title=title,
            message=message,
            link_text=link_text,
            target_lang=lang,
            source_lang=source_lang,
        )

        if result:
            translations[lang] = result
            logger.info(f"Translated to {lang}: {result['title'][:50]}...")
        else:
            logger.warning(f"Failed to translate to {lang}")

    return translations


def is_translation_available() -> bool:
    """Check if translation service is available.

    Returns:
        True if Google Translate credentials are configured and client works.
    """
    client = get_translate_client()
    if not client:
        return False

    # Try a simple translation to verify it works
    try:
        result = client.translate("test", source_language="en", target_language="es")
        return bool(result.get("translatedText"))
    except Exception as e:
        logger.error(f"Translation service check failed: {e}")
        return False
