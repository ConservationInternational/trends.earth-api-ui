"""
API mocking utilities for Playwright tests.
Provides comprehensive mocking of the Trends.Earth API endpoints.
"""

from datetime import datetime, timedelta
import json
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import Route

from .conftest import (
    generate_mock_executions_data,
    generate_mock_scripts_data,
    generate_mock_users_data,
    generate_mock_status_data,
)


def create_mock_auth_response(email: str = "test@example.com") -> Dict[str, Any]:
    """Create a mock authentication response."""
    return {
        "access_token": "mock_access_token_123456789",
        "refresh_token": "mock_refresh_token_987654321",
        "expires_in": 3600,
        "token_type": "Bearer",
        "user": {
            "id": "user_123",
            "email": email,
            "name": "Test User",
            "role": "ADMIN",
            "institution": "Test Institution",
            "country": "Test Country",
        },
    }


def create_mock_user_me_response(role: str = "ADMIN") -> Dict[str, Any]:
    """Create a mock /user/me response."""
    return {
        "data": {
            "id": "user_123",
            "email": "test@example.com",
            "name": "Test User",
            "role": role,
            "institution": "Test Institution",
            "country": "Test Country",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    }


def create_mock_refresh_response() -> Dict[str, Any]:
    """Create a mock token refresh response."""
    return {
        "access_token": "mock_refreshed_access_token_123456789",
        "expires_in": 3600,
        "token_type": "Bearer",
    }


def create_mock_logout_response() -> Dict[str, Any]:
    """Create a mock logout response."""
    return {
        "message": "Successfully logged out",
        "success": True,
    }


class APIRouteHandler:
    """Handles API route mocking for Playwright tests."""

    def __init__(self):
        self.authenticated = True  # Start as authenticated for tests
        self.current_user_role = "ADMIN"

    def handle_auth_login(self, route: Route):
        """Handle /auth/login endpoint."""
        print(f"🔐 AUTH LOGIN called: {route.request.url}")
        print(f"🔐 Request method: {route.request.method}")
        print(f"🔐 Request headers: {dict(route.request.headers)}")
        
        try:
            request_body = route.request.post_data_json
            print(f"🔐 Request body: {request_body}")
            email = request_body.get("email", "test@example.com") if request_body else None
            password = request_body.get("password", "") if request_body else None

            # Simulate authentication logic
            if email and password:
                self.authenticated = True
                response = create_mock_auth_response(email)
                print(f"✅ Auth success response: {response}")
                route.fulfill(json=response, status=200)
            else:
                print(f"❌ Auth failed - missing credentials: email={email}, password={password}")
                route.fulfill(
                    json={"error": "Invalid credentials", "message": "Email and password required"},
                    status=400,
                )
        except Exception as e:
            print(f"Error in auth login handler: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            route.fulfill(
                json={"error": "Authentication failed", "message": str(e)}, status=500
            )

    def handle_auth_refresh(self, route: Route):
        """Handle /auth/refresh endpoint."""
        try:
            request_body = route.request.post_data_json
            refresh_token = request_body.get("refresh_token", "")

            if refresh_token and refresh_token.startswith("mock_refresh_token"):
                response = create_mock_refresh_response()
                route.fulfill(json=response, status=200)
            else:
                route.fulfill(
                    json={"error": "Invalid refresh token", "message": "Token refresh failed"},
                    status=401,
                )
        except Exception as e:
            print(f"Error in auth refresh handler: {e}")
            route.fulfill(
                json={"error": "Token refresh failed", "message": str(e)}, status=500
            )

    def handle_auth_logout(self, route: Route):
        """Handle /auth/logout endpoint."""
        try:
            self.authenticated = False
            response = create_mock_logout_response()
            route.fulfill(json=response, status=200)
        except Exception as e:
            print(f"Error in auth logout handler: {e}")
            route.fulfill(json={"error": "Logout failed", "message": str(e)}, status=500)

    def handle_user_me(self, route: Route):
        """Handle /api/v1/user/me endpoint."""
        print(f"👤 USER ME called: {route.request.url}")
        print(f"👤 Request method: {route.request.method}")
        print(f"👤 Request headers: {dict(route.request.headers)}")
        
        try:
            # Check authorization header
            auth_header = route.request.headers.get("authorization", "")
            print(f"👤 Auth header: {auth_header}")
            
            if not auth_header.startswith("Bearer mock_"):
                print(f"❌ Invalid auth header for user/me")
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Invalid or missing token"},
                    status=401,
                )
                return

            if self.authenticated:
                response = create_mock_user_me_response(self.current_user_role)
                print(f"✅ User ME response: {response}")
                route.fulfill(json=response, status=200)
            else:
                print(f"❌ User not authenticated")
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Authentication required"},
                    status=401,
                )
        except Exception as e:
            print(f"Error in user me handler: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            route.fulfill(json={"error": "User info failed", "message": str(e)}, status=500)

    def handle_executions(self, route: Route):
        """Handle /api/v1/executions endpoint."""
        try:
            # Check authorization header
            auth_header = route.request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer mock_"):
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Invalid or missing token"},
                    status=401,
                )
                return

            if not self.authenticated:
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Authentication required"},
                    status=401,
                )
                return

            # Parse query parameters for pagination
            url_parts = urlparse(route.request.url)
            query_params = parse_qs(url_parts.query)

            page = int(query_params.get("page", [1])[0])
            per_page = int(query_params.get("per_page", [50])[0])
            count = min(per_page, 50)  # Limit to reasonable number for tests

            mock_data = generate_mock_executions_data(count=count, page=page, per_page=per_page)
            route.fulfill(json=mock_data, status=200)

        except Exception as e:
            print(f"Error in executions handler: {e}")
            route.fulfill(
                json={"error": "Executions fetch failed", "message": str(e)}, status=500
            )

    def handle_scripts(self, route: Route):
        """Handle /api/v1/scripts endpoint."""
        try:
            # Check authorization header
            auth_header = route.request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer mock_"):
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Invalid or missing token"},
                    status=401,
                )
                return

            if not self.authenticated:
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Authentication required"},
                    status=401,
                )
                return

            # Parse query parameters for pagination
            url_parts = urlparse(route.request.url)
            query_params = parse_qs(url_parts.query)

            page = int(query_params.get("page", [1])[0])
            per_page = int(query_params.get("per_page", [50])[0])
            count = min(per_page, 50)  # Limit to reasonable number for tests

            mock_data = generate_mock_scripts_data(count=count, page=page, per_page=per_page)
            route.fulfill(json=mock_data, status=200)

        except Exception as e:
            print(f"Error in scripts handler: {e}")
            route.fulfill(json={"error": "Scripts fetch failed", "message": str(e)}, status=500)

    def handle_users(self, route: Route):
        """Handle /api/v1/users endpoint."""
        try:
            # Check authorization header
            auth_header = route.request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer mock_"):
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Invalid or missing token"},
                    status=401,
                )
                return

            if not self.authenticated:
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Authentication required"},
                    status=401,
                )
                return

            # Only allow ADMIN users to access user list
            if self.current_user_role != "ADMIN":
                route.fulfill(
                    json={"error": "Forbidden", "message": "Admin access required"}, status=403
                )
                return

            # Parse query parameters for pagination
            url_parts = urlparse(route.request.url)
            query_params = parse_qs(url_parts.query)

            page = int(query_params.get("page", [1])[0])
            per_page = int(query_params.get("per_page", [50])[0])
            count = min(per_page, 50)  # Limit to reasonable number for tests

            mock_data = generate_mock_users_data(count=count, page=page, per_page=per_page)
            route.fulfill(json=mock_data, status=200)

        except Exception as e:
            print(f"Error in users handler: {e}")
            route.fulfill(json={"error": "Users fetch failed", "message": str(e)}, status=500)

    def handle_status(self, route: Route):
        """Handle /api/v1/status endpoint."""
        try:
            # Check authorization header
            auth_header = route.request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer mock_"):
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Invalid or missing token"},
                    status=401,
                )
                return

            if not self.authenticated:
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Authentication required"},
                    status=401,
                )
                return

            mock_data = generate_mock_status_data()
            route.fulfill(json=mock_data, status=200)

        except Exception as e:
            print(f"Error in status handler: {e}")
            route.fulfill(json={"error": "Status fetch failed", "message": str(e)}, status=500)

    def handle_user_endpoint(self, route: Route):
        """Handle /api/v1/user endpoint (fallback for user info)."""
        try:
            # Check authorization header
            auth_header = route.request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer mock_"):
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Invalid or missing token"},
                    status=401,
                )
                return

            if self.authenticated:
                # Return user data in array format (as expected by fallback code)
                user_data = create_mock_user_me_response(self.current_user_role)["data"]
                response = {"data": [user_data]}
                route.fulfill(json=response, status=200)
            else:
                route.fulfill(
                    json={"error": "Unauthorized", "message": "Authentication required"},
                    status=401,
                )
        except Exception as e:
            print(f"Error in user endpoint handler: {e}")
            route.fulfill(json={"error": "User fetch failed", "message": str(e)}, status=500)


def setup_api_mocking(page, user_role: str = "ADMIN"):
    """
    Set up comprehensive API mocking for Playwright tests.
    
    Args:
        page: Playwright page object
        user_role: Role for the mock user (ADMIN, USER, etc.)
    """
    handler = APIRouteHandler()
    handler.current_user_role = user_role

    print(f"🎭 Setting up API mocking with user role: {user_role}")

    # Authentication endpoints - the auth endpoint is at the root /auth
    page.route("**/auth", handler.handle_auth_login)
    page.route("**/auth/", handler.handle_auth_login)
    page.route("**/auth/refresh", handler.handle_auth_refresh)
    page.route("**/auth/logout", handler.handle_auth_logout)
    page.route("**/auth/logout-all", handler.handle_auth_logout)

    # API data endpoints
    page.route("**/api/v1/user/me", handler.handle_user_me)
    page.route("**/api/v1/user", handler.handle_user_endpoint)  # Fallback endpoint
    page.route("**/api/v1/executions**", handler.handle_executions)
    page.route("**/api/v1/scripts**", handler.handle_scripts)
    page.route("**/api/v1/users**", handler.handle_users)
    page.route("**/api/v1/status**", handler.handle_status)

    print("✅ API mocking setup complete")
    return handler