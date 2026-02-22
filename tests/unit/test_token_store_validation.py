"""Test fix for SchemaTypeValidationError caused by list-wrapped single output in auto_refresh_token.

The auto_refresh_token callback previously declared its single output as a list:
    [Output("token-store", "data", allow_duplicate=True)]

This caused Dash's SchemaTypeValidationError when the callback returned a plain string
(the new access token), because Dash's grouping validator expected a tuple/list to match
the list output schema.

The fix removes the list wrapper so Dash treats this as a single (non-multi) output,
allowing plain values to be returned directly.
"""

import pytest

from trendsearth_ui.app import app


class TestTokenStoreCallbackOutputSchema:
    """Test that the auto_refresh_token callback has a non-multi output schema."""

    def test_auto_refresh_token_output_is_single_not_list(self):
        """Verify auto_refresh_token is registered with a single Output, not a list.

        With the old list-wrapped output [Output("token-store", "data")], Dash would
        raise SchemaTypeValidationError when the callback returned a plain string token.
        The fix removes the list wrapper so the output is a single Output.
        """
        # Find the auto_refresh_token callback – it is the only single-output
        # (non-multi) callback whose output is token-store.data
        single_output_token_cbs = [
            cb_id
            for cb_id in app.callback_map
            if cb_id.startswith("token-store.data@") and "..." not in cb_id
        ]

        assert len(single_output_token_cbs) == 1, (
            "Expected exactly one single-output token-store.data callback "
            f"(auto_refresh_token); found: {single_output_token_cbs}"
        )

        cb_id = single_output_token_cbs[0]
        cb_info = app.callback_map[cb_id]
        output = cb_info["output"]

        # The output should NOT be a list – it must be a single Output object
        assert not isinstance(output, list), (
            "auto_refresh_token output must be a single Output, not a list. "
            "A list output causes SchemaTypeValidationError when the callback "
            "returns a plain string token."
        )

    def test_auto_refresh_token_function_returns_plain_value(self):
        """Verify that auto_refresh_token returns a plain value, not a tuple/list.

        The callback should return either no_update or a plain string token.
        Both are valid for a single-output callback and would have caused
        SchemaTypeValidationError with the old list-wrapped output schema.
        """
        from unittest.mock import patch

        from dash import no_update

        # Find the underlying function (use __wrapped__ to bypass the Dash decorator)
        single_output_token_cbs = [
            cb_id
            for cb_id in app.callback_map
            if cb_id.startswith("token-store.data@") and "..." not in cb_id
        ]
        cb_info = app.callback_map[single_output_token_cbs[0]]
        auto_refresh_token_fn = cb_info["callback"].__wrapped__

        # Test: no current token → returns no_update (not a tuple)
        result = auto_refresh_token_fn(None)
        assert result is no_update
        assert not isinstance(result, (list, tuple))

        # Test: token that does not need refreshing → returns no_update (not a tuple)
        with patch("trendsearth_ui.callbacks.auth.should_refresh_token", return_value=False):
            result = auto_refresh_token_fn("some.valid.token")
        assert result is no_update
        assert not isinstance(result, (list, tuple))
