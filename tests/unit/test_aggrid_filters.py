"""Tests for the AG-Grid filter building utilities."""

from trendsearth_ui.utils.aggrid import (
    _build_single_filter,
    build_aggrid_request_params,
    build_filter_clause,
)


class TestBuildSingleFilter:
    """Test individual filter clause building."""

    def test_text_contains(self):
        config = {"filterType": "text", "type": "contains", "filter": "emissions"}
        result = _build_single_filter("script_name", config)
        assert result == "script_name like '%emissions%'"

    def test_text_equals(self):
        config = {"filterType": "text", "type": "equals", "filter": "RUNNING"}
        result = _build_single_filter("status", config)
        assert result == "status='RUNNING'"

    def test_text_starts_with(self):
        config = {"filterType": "text", "type": "startsWith", "filter": "avoided"}
        result = _build_single_filter("script_name", config)
        assert result == "script_name like 'avoided%'"

    def test_text_ends_with(self):
        config = {"filterType": "text", "type": "endsWith", "filter": "emissions"}
        result = _build_single_filter("script_name", config)
        assert result == "script_name like '%emissions'"

    def test_text_not_equals(self):
        config = {"filterType": "text", "type": "notEquals", "filter": "FAILED"}
        result = _build_single_filter("status", config)
        assert result == "status!='FAILED'"

    def test_text_empty_filter_returns_none(self):
        config = {"filterType": "text", "type": "contains", "filter": ""}
        result = _build_single_filter("script_name", config)
        assert result is None

    def test_text_whitespace_only_returns_none(self):
        config = {"filterType": "text", "type": "contains", "filter": "   "}
        result = _build_single_filter("script_name", config)
        assert result is None

    def test_text_escapes_sql_quotes(self):
        config = {"filterType": "text", "type": "contains", "filter": "test'script"}
        result = _build_single_filter("script_name", config)
        assert result == "script_name like '%test''script%'"

    def test_text_escapes_like_wildcards(self):
        config = {"filterType": "text", "type": "contains", "filter": "test%script"}
        result = _build_single_filter("script_name", config)
        assert result == "script_name like '%test\\%script%'"

    def test_number_equals(self):
        config = {"filterType": "number", "type": "equals", "filter": 50}
        result = _build_single_filter("progress", config)
        assert result == "progress=50"

    def test_number_greater_than(self):
        config = {"filterType": "number", "type": "greaterThan", "filter": 3600}
        result = _build_single_filter("duration", config)
        assert result == "duration>3600"

    def test_number_less_than_or_equal(self):
        config = {"filterType": "number", "type": "lessThanOrEqual", "filter": 100}
        result = _build_single_filter("progress", config)
        assert result == "progress<=100"

    def test_number_empty_returns_none(self):
        config = {"filterType": "number", "type": "equals", "filter": ""}
        result = _build_single_filter("progress", config)
        assert result is None

    def test_set_filter(self):
        config = {"filterType": "set", "values": ["RUNNING", "PENDING"]}
        result = _build_single_filter("status", config)
        assert result == "(status='RUNNING' OR status='PENDING')"

    def test_set_filter_single_value(self):
        config = {"filterType": "set", "values": ["FINISHED"]}
        result = _build_single_filter("status", config)
        assert result == "(status='FINISHED')"

    def test_set_filter_empty_values(self):
        config = {"filterType": "set", "values": []}
        result = _build_single_filter("status", config)
        assert result is None

    def test_date_equals(self):
        config = {"filterType": "date", "type": "equals", "dateFrom": "2025-03-10"}
        result = _build_single_filter("start_date", config)
        assert result == "start_date>='2025-03-10',start_date<='2025-03-10'"

    def test_date_in_range(self):
        config = {
            "filterType": "date",
            "type": "inRange",
            "dateFrom": "2025-01-01",
            "dateTo": "2025-03-31",
        }
        result = _build_single_filter("start_date", config)
        assert result == "start_date>='2025-01-01',start_date<='2025-03-31'"


class TestBuildFilterClause:
    """Test the full filter clause builder."""

    def test_simple_text_filter(self):
        filter_model = {
            "script_name": {"filterType": "text", "type": "contains", "filter": "emissions"}
        }
        clause, params = build_filter_clause(
            filter_model, allowed_columns={"script_name", "status"}
        )
        assert clause == "script_name like '%emissions%'"
        assert params == {}

    def test_disallowed_column_filtered_out(self):
        filter_model = {
            "secret_field": {"filterType": "text", "type": "contains", "filter": "test"}
        }
        clause, params = build_filter_clause(
            filter_model, allowed_columns={"script_name", "status"}
        )
        assert clause is None

    def test_multiple_filters(self):
        filter_model = {
            "script_name": {"filterType": "text", "type": "contains", "filter": "emissions"},
            "status": {"filterType": "text", "type": "equals", "filter": "RUNNING"},
        }
        clause, params = build_filter_clause(
            filter_model, allowed_columns={"script_name", "status"}
        )
        assert clause is not None
        # Both clauses should be present (order may vary due to dict iteration)
        assert "script_name like '%emissions%'" in clause
        assert "status='RUNNING'" in clause

    def test_compound_filter_with_conditions_array(self):
        """AG Grid v31+ compound filter format with conditions array."""
        filter_model = {
            "script_name": {
                "filterType": "text",
                "operator": "AND",
                "conditions": [
                    {"filterType": "text", "type": "contains", "filter": "emissions"},
                    {"filterType": "text", "type": "startsWith", "filter": "avoided"},
                ],
            }
        }
        clause, params = build_filter_clause(filter_model, allowed_columns={"script_name"})
        assert clause is not None
        assert "script_name like '%emissions%'" in clause
        assert "script_name like 'avoided%'" in clause

    def test_compound_filter_with_or_operator(self):
        """AG Grid compound OR filter."""
        filter_model = {
            "script_name": {
                "filterType": "text",
                "operator": "OR",
                "conditions": [
                    {"filterType": "text", "type": "contains", "filter": "emissions"},
                    {"filterType": "text", "type": "contains", "filter": "vegetation"},
                ],
            }
        }
        clause, params = build_filter_clause(filter_model, allowed_columns={"script_name"})
        assert clause is not None
        assert "OR" in clause
        assert "script_name like '%emissions%'" in clause
        assert "script_name like '%vegetation%'" in clause

    def test_compound_filter_with_condition1_condition2(self):
        """Older AG Grid compound filter format with condition1/condition2."""
        filter_model = {
            "script_name": {
                "filterType": "text",
                "operator": "AND",
                "condition1": {"filterType": "text", "type": "contains", "filter": "emissions"},
                "condition2": {"filterType": "text", "type": "startsWith", "filter": "avoided"},
            }
        }
        clause, params = build_filter_clause(filter_model, allowed_columns={"script_name"})
        assert clause is not None
        assert "script_name like '%emissions%'" in clause
        assert "script_name like 'avoided%'" in clause

    def test_compound_filter_with_one_empty_condition(self):
        """Compound model where second condition is empty (should produce clause from first only)."""
        filter_model = {
            "script_name": {
                "filterType": "text",
                "operator": "AND",
                "conditions": [
                    {"filterType": "text", "type": "contains", "filter": "emissions"},
                    {"filterType": "text", "type": "contains", "filter": ""},
                ],
            }
        }
        clause, params = build_filter_clause(filter_model, allowed_columns={"script_name"})
        assert clause == "script_name like '%emissions%'"

    def test_empty_filter_model(self):
        clause, params = build_filter_clause({})
        assert clause is None

    def test_none_filter_model(self):
        clause, params = build_filter_clause(None)
        assert clause is None


class TestBuildAggridRequestParams:
    """Test the full request parameter builder."""

    def test_basic_request_with_filter(self):
        request_data = {
            "startRow": 0,
            "endRow": 50,
            "sortModel": [{"colId": "end_date", "sort": "desc"}],
            "filterModel": {
                "script_name": {"filterType": "text", "type": "contains", "filter": "emissions"}
            },
        }
        params, state = build_aggrid_request_params(
            request_data,
            allowed_sort_columns={"end_date", "script_name"},
            allowed_filter_columns={"script_name", "status"},
        )
        assert params["filter"] == "script_name like '%emissions%'"
        assert params["sort"] == "end_date desc"
        assert params["page"] == 1
        assert params["per_page"] == 50

    def test_request_with_no_filter(self):
        request_data = {
            "startRow": 0,
            "endRow": 50,
            "sortModel": [],
            "filterModel": {},
        }
        params, state = build_aggrid_request_params(request_data)
        assert "filter" not in params

    def test_filter_model_overrides(self):
        request_data = {
            "startRow": 0,
            "endRow": 50,
            "sortModel": [],
            "filterModel": {
                "script_name": {"filterType": "text", "type": "contains", "filter": "emissions"}
            },
        }
        overrides = {"status": {"filterType": "set", "values": ["RUNNING"]}}
        params, state = build_aggrid_request_params(
            request_data,
            allowed_filter_columns={"script_name", "status"},
            filter_model_overrides=overrides,
        )
        assert "filter" in params
        assert "script_name like '%emissions%'" in params["filter"]
        assert "(status='RUNNING')" in params["filter"]
