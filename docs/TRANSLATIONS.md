# Translation Guide for Trends.Earth API UI

This document provides instructions for managing translations in the Trends.Earth API UI application.

## Overview

The application uses [Flask-Babel](https://flask-babel.tkte.ch/) for internationalization (i18n) with gettext-based PO/POT files. Translations are managed through [Transifex](https://www.transifex.com/) for collaborative translation management.

## Supported Languages

The following languages are supported (same as the main trends.earth project):

| Code | Language  |
|------|-----------|
| en   | English   |
| ar   | العربية (Arabic) |
| es   | Español (Spanish) |
| fa   | فارسی (Farsi) |
| fr   | Français (French) |
| pt   | Português (Portuguese) |
| ru   | Русский (Russian) |
| sw   | Kiswahili (Swahili) |
| zh   | 中文 (Chinese) |

## Project Structure

```
trendsearth_ui/
├── i18n/
│   ├── __init__.py          # Main i18n module with Flask-Babel integration
│   ├── dash_i18n.py         # Dash-specific i18n utilities
│   └── translations/
│       ├── messages.pot     # Template file with English source strings
│       ├── en/LC_MESSAGES/  # English translations
│       ├── es/LC_MESSAGES/  # Spanish translations
│       ├── fr/LC_MESSAGES/  # French translations
│       └── .../             # Other languages
```

## Using Translations in Code

### Marking Strings for Translation

```python
from trendsearth_ui.i18n import gettext as _, lazy_gettext as _l

# Immediate translation (use in functions)
message = _("Hello, World!")

# Lazy translation (use in class attributes, module-level constants)
label = _l("Submit")
```

### In Dash Components

```python
from trendsearth_ui.i18n import gettext as _

# In layout functions
html.H1(_("Dashboard"))
dbc.Button(_("Login"), id="login-btn")
```

## Translation Workflow

### Local Development

1. **Extract strings** from source code:
   ```bash
   invoke translate-extract
   ```

2. **Update PO files** with new strings:
   ```bash
   invoke translate-update
   ```

3. **Edit translations** manually in `trendsearth_ui/i18n/translations/<lang>/LC_MESSAGES/messages.po`

4. **Compile translations** to MO files:
   ```bash
   invoke translate-compile
   ```

5. **Check status** of translations:
   ```bash
   invoke translate-status
   ```

### Available Invoke Tasks

| Task | Description |
|------|-------------|
| `invoke translate-extract` | Extract translatable strings from source code |
| `invoke translate-update` | Update PO files from POT template |
| `invoke translate-compile` | Compile PO files to MO format |
| `invoke translate-pull` | Pull translations from Transifex |
| `invoke translate-push` | Push source strings to Transifex |
| `invoke translate-status` | Show translation completion status |
| `invoke translate-init --language XX` | Initialize a new language |

### Using Transifex

1. **Setup**: Ensure `TX_TOKEN` environment variable is set with your Transifex API token.

2. **Push new strings** to Transifex:
   ```bash
   invoke translate-push
   ```

3. **Pull translated strings** from Transifex:
   ```bash
   invoke translate-pull
   ```

## GitHub Workflows

### Automated Translation Sync

The `translation_update.yml` workflow runs automatically on Monday, Wednesday, and Friday at 4 AM UTC. It:

1. Extracts new translatable strings from source code
2. Updates PO files from the POT template
3. Pulls latest translations from Transifex
4. Pushes new source strings to Transifex
5. Compiles translations
6. Creates a PR with updated translation files

### Machine Translation

The `machine_translation.yml` workflow can be manually triggered to prepopulate translations using Google Cloud Translation API:

1. Go to Actions → Machine translation
2. Select target languages (or leave empty for all)
3. Choose whether to overwrite existing translations
4. Run the workflow

**Note**: Machine translations are marked as "fuzzy" and should be reviewed by human translators before deployment.

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TX_TOKEN` | Transifex API token |
| `TX_HOSTNAME` | Transifex hostname (optional) |
| `GOOGLE_TRANSLATE_CREDENTIALS` | Google Cloud credentials JSON for machine translation |
| `SECRET_KEY` | Flask secret key for session management |

### Transifex Configuration

The `.tx/config` file contains the Transifex project configuration:

```ini
[o:conservation-international:p:trendsearth-api-ui:r:messages]
file_filter = trendsearth_ui/i18n/translations/<lang>/LC_MESSAGES/messages.po
source_file = trendsearth_ui/i18n/translations/messages.pot
source_lang = en
type = PO
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/languages` | GET | Get list of supported languages |
| `/api/set-language/<lang>` | GET | Set user's preferred language |

## Adding a New Language

1. Initialize the new language:
   ```bash
   invoke translate-init --language XX
   ```

2. Update `.tx/config` if using Transifex

3. Add the language to `SUPPORTED_LANGUAGES` in `trendsearth_ui/i18n/__init__.py`

4. Translate the strings in the new PO file

5. Compile and test

## Best Practices

1. **Use meaningful message IDs**: Keep English strings descriptive and consistent.

2. **Avoid string concatenation**: Use placeholders instead.
   ```python
   # Good
   _("Hello, %(name)s!") % {"name": username}
   
   # Bad
   _("Hello, ") + username + "!"
   ```

3. **Handle plurals properly**: Use `ngettext` for pluralized strings.
   ```python
   from trendsearth_ui.i18n import ngettext
   msg = ngettext("%(num)d item", "%(num)d items", count) % {"num": count}
   ```

4. **Keep translations context-aware**: Add comments for translators when meaning is ambiguous.

5. **Test with RTL languages**: Arabic and Farsi are right-to-left languages; ensure the UI handles them properly.

## Troubleshooting

### Translations not appearing

1. Ensure MO files are compiled: `invoke translate-compile`
2. Restart the application
3. Check the language is properly detected (cookies, URL parameter, Accept-Language header)

### Babel extraction not finding strings

1. Ensure `babel.cfg` includes your source files
2. Use `_()` or `_l()` for marking strings
3. Run `invoke translate-extract -v` for verbose output

### Transifex sync failing

1. Check `TX_TOKEN` is set correctly
2. Verify the project exists on Transifex
3. Check `.tx/config` resource names match Transifex
