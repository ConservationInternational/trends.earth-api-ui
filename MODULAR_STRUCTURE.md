# Trends.Earth API Dashboard - Modular Structure

This document describes the refactored modular structure of the Trends.Earth API Dashboard.

## Project Structure

```
trendsearth_ui/
├── __init__.py
├── app.py                 # Main application entry point
├── config.py             # Configuration constants and settings
├── components/           # UI component definitions
│   ├── __init__.py
│   ├── layout.py         # Main layout, login, and dashboard layouts
│   ├── modals.py         # Modal components (JSON, edit user/script, map)
│   └── tabs.py           # Tab content components
├── callbacks/            # Dash callback functions
│   ├── __init__.py       # Callback registration coordinator
│   ├── auth.py           # Authentication and navigation callbacks
│   ├── tabs.py           # Tab rendering callbacks
│   ├── executions.py     # Executions table and refresh callbacks
│   ├── modals.py         # JSON/logs modal callbacks
│   ├── map.py            # Map modal callbacks
│   ├── profile.py        # Profile and password change callbacks
│   ├── edit.py           # Edit user/script modal callbacks
│   └── refresh.py        # Log refresh and countdown callbacks
└── utils/                # Utility functions
    ├── __init__.py
    ├── helpers.py        # General utility functions
    ├── geojson.py        # GeoJSON and map utilities
    └── json_utils.py     # JSON rendering utilities
```

## Key Components

### Main Application (`app.py`)
- Initializes Flask server and Dash app
- Imports and sets up the main layout
- Registers all callbacks
- Contains health check and favicon routes
- Application entry point

### Configuration (`config.py`)
- API URLs and endpoints
- App title and branding
- Default values (page sizes, refresh intervals)
- Logo URLs and styling constants

### Components Package
- **`layout.py`**: Main application layout with stores and modals, login page, dashboard layout
- **`modals.py`**: All modal components (JSON viewer, edit forms, map display)
- **`tabs.py`**: Content for each tab (executions, users, scripts, profile, status)

### Callbacks Package
- **`__init__.py`**: Coordinates registration of all callback modules
- **`auth.py`**: Login authentication and page navigation
- **`tabs.py`**: Tab content rendering based on active tab
- **`executions.py`**: Executions table data loading and refresh
- **`modals.py`**: Modal open/close and content loading
- **`map.py`**: Map modal for execution area visualization
- **`profile.py`**: User profile updates and password changes
- **`edit.py`**: Edit modal open/close for users and scripts
- **`refresh.py`**: Auto-refresh functionality for logs and data

### Utils Package
- **`helpers.py`**: Date parsing, table data processing, user info fetching
- **`geojson.py`**: GeoJSON processing and map creation utilities
- **`json_utils.py`**: JSON tree rendering for modal display

## Benefits of Modular Structure

1. **Maintainability**: Code is organized by functionality making it easier to locate and modify specific features
2. **Reusability**: Components and utilities can be easily reused across different parts of the application
3. **Testing**: Individual modules can be tested in isolation
4. **Collaboration**: Multiple developers can work on different modules without conflicts
5. **Scalability**: New features can be added by creating new modules following the established patterns

## Usage

To run the application:

```bash
python trendsearth_ui/app.py
```

The modular structure is fully compatible with the original monolithic application and maintains all existing functionality while improving code organization and maintainability.

## Migration Notes

- Original `app.py` has been backed up as `app_backup.py`
- All functionality has been preserved and moved to appropriate modules
- No external API changes - the application interface remains the same
- All callback IDs and component IDs remain unchanged for compatibility
