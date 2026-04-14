"""Tests for the PATSTAT sidecar API."""

import json
import sys
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_patstat_client():
    """Mock the PatstatClient so tests don't need BigQuery."""
    with patch("sidecar.client") as mock_client:
        yield mock_client


@pytest.fixture
def app_client(mock_patstat_client):
    """Create a test client with mocked PatstatClient."""
    from sidecar import app
    return TestClient(app)


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Use a temporary config directory."""
    import sidecar
    monkeypatch.setattr(sidecar, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(sidecar, "CONFIG_FILE", tmp_path / "config.json")
    return tmp_path


# --- Health endpoint ---

class TestHealth:
    def test_health_ok(self, app_client, mock_patstat_client):
        mock_patstat_client.sql_query.return_value = [{"ok": 1}]
        res = app_client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert "connected" in data["message"].lower() or "1 row" in data["message"]

    def test_health_failure(self, app_client, mock_patstat_client):
        mock_patstat_client.sql_query.side_effect = Exception("Connection refused")
        res = app_client.get("/api/health")
        assert res.status_code == 200  # endpoint always returns 200
        data = res.json()
        assert data["ok"] is False
        assert "Connection refused" in data["message"]


# --- Query endpoint ---

class TestQuery:
    def test_query_success(self, app_client, mock_patstat_client):
        mock_patstat_client.sql_query.return_value = [
            {"name": "BASF", "count": 100},
            {"name": "BAYER", "count": 80},
        ]
        res = app_client.post("/api/query", json={"sql": "SELECT 1"})
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["name"] == "BASF"

    def test_query_passes_sql_to_client(self, app_client, mock_patstat_client):
        mock_patstat_client.sql_query.return_value = []
        sql = "SELECT person_name FROM tls206_person LIMIT 5"
        app_client.post("/api/query", json={"sql": sql})
        mock_patstat_client.sql_query.assert_called_once_with(sql, use_legacy_sql=True)

    def test_query_bigquery_error(self, app_client, mock_patstat_client):
        mock_patstat_client.sql_query.side_effect = Exception("Syntax error at position 10")
        res = app_client.post("/api/query", json={"sql": "INVALID SQL"})
        assert res.status_code == 400
        assert "Syntax error" in res.json()["detail"]

    def test_query_empty_result(self, app_client, mock_patstat_client):
        mock_patstat_client.sql_query.return_value = []
        res = app_client.post("/api/query", json={"sql": "SELECT 1 WHERE FALSE"})
        assert res.status_code == 200
        assert res.json() == []


# --- Settings endpoints ---

class TestSettings:
    def test_get_settings_default(self, app_client, config_dir):
        res = app_client.get("/api/settings")
        assert res.status_code == 200
        data = res.json()
        assert data["has_api_key"] is False
        assert data["api_key_preview"] == ""
        assert "claude" in data["model"]

    def test_post_settings_saves_key(self, app_client, config_dir):
        res = app_client.post("/api/settings", json={"api_key": "sk-ant-test123456789abcdef"})
        assert res.status_code == 200
        assert res.json()["ok"] is True

        # Verify it persists
        config_file = config_dir / "config.json"
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        assert config["api_key"] == "sk-ant-test123456789abcdef"

    def test_get_settings_with_key(self, app_client, config_dir):
        # Save a key first
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"api_key": "sk-ant-api03-abcdefghij1234567890klmnopqrst"}))

        res = app_client.get("/api/settings")
        data = res.json()
        assert data["has_api_key"] is True
        assert data["api_key_preview"].startswith("sk-ant-a")
        assert data["api_key_preview"].endswith("qrst")

    def test_post_settings_saves_model(self, app_client, config_dir):
        app_client.post("/api/settings", json={"model": "claude-haiku-4-20250414"})

        config = json.loads((config_dir / "config.json").read_text())
        assert config["model"] == "claude-haiku-4-20250414"

    def test_post_settings_partial_update(self, app_client, config_dir):
        # First save a key
        app_client.post("/api/settings", json={"api_key": "sk-ant-original"})
        # Then update only model
        app_client.post("/api/settings", json={"model": "claude-haiku-4-20250414"})

        config = json.loads((config_dir / "config.json").read_text())
        assert config["api_key"] == "sk-ant-original"  # key unchanged
        assert config["model"] == "claude-haiku-4-20250414"


# --- NL-to-SQL endpoint ---

@pytest.fixture
def mock_anthropic():
    """Mock the anthropic module for NL-to-SQL tests."""
    mock_mod = MagicMock()
    mock_mod.AuthenticationError = type("AuthenticationError", (Exception,), {})
    with patch.dict(sys.modules, {"anthropic": mock_mod}):
        yield mock_mod


def _parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE response text into list of event dicts."""
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


class TestNlToSql:
    def test_no_api_key_returns_400(self, app_client, config_dir):
        res = app_client.post("/api/nl-to-sql", json={"question": "Show top applicants"})
        assert res.status_code == 400
        assert "API key" in res.json()["detail"]

    def test_with_api_key_returns_sse_with_result(self, app_client, config_dir, mock_anthropic):
        """SSE stream should contain a result event with the SQL."""
        (config_dir / "config.json").write_text(json.dumps({"api_key": "sk-ant-test"}))

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "SELECT person_name FROM tls206_person LIMIT 10"
        mock_response.content = [text_block]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        # Mock MCP so it doesn't try to connect to a real server
        async def mock_noop():
            pass
        with patch("sidecar._get_mcp_tools_and_caller", return_value=([], None, mock_noop)):
            res = app_client.post("/api/nl-to-sql", json={"question": "Show top applicants"})
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")

        events = _parse_sse_events(res.text)
        result_events = [e for e in events if e.get("event") == "result"]
        assert len(result_events) == 1
        assert "SELECT" in result_events[0]["data"]["text"]

    def test_invalid_key_returns_error_event(self, app_client, config_dir, mock_anthropic):
        """SSE stream should contain an error event for invalid key."""
        (config_dir / "config.json").write_text(json.dumps({"api_key": "sk-ant-bad"}))

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = mock_anthropic.AuthenticationError("Invalid")
        mock_anthropic.Anthropic.return_value = mock_client

        async def mock_noop():
            pass
        with patch("sidecar._get_mcp_tools_and_caller", return_value=([], None, mock_noop)):
            res = app_client.post("/api/nl-to-sql", json={"question": "test"})
        assert res.status_code == 200  # SSE always returns 200

        events = _parse_sse_events(res.text)
        error_events = [e for e in events if e.get("event") == "error"]
        assert len(error_events) == 1
        assert "key" in error_events[0]["data"]["message"].lower() or "invalid" in error_events[0]["data"]["message"].lower()

    def test_sse_stream_ends_with_done(self, app_client, config_dir, mock_anthropic):
        """SSE stream should always end with a done event."""
        (config_dir / "config.json").write_text(json.dumps({"api_key": "sk-ant-test"}))

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "SELECT 1"
        mock_response.content = [text_block]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        async def mock_noop():
            pass
        with patch("sidecar._get_mcp_tools_and_caller", return_value=([], None, mock_noop)):
            res = app_client.post("/api/nl-to-sql", json={"question": "test"})
        events = _parse_sse_events(res.text)
        assert events[-1]["event"] == "done"


# --- Patent detail endpoint ---

class TestPatentDetail:
    def test_returns_patent_details(self, app_client, mock_patstat_client):
        """GET /api/patent/{appln_id} returns basic info, applicants, and CPC codes."""
        mock_patstat_client.sql_query.side_effect = [
            # First call: basic info
            [{
                "appln_id": 42,
                "appln_auth": "EP",
                "appln_nr": "1234567",
                "appln_kind": "A",
                "appln_filing_date": "2020-03-15",
                "appln_filing_year": 2020,
                "docdb_family_id": 99999,
                "granted": 1,
                "title": "Method for energy storage",
                "title_lang": "en",
                "abstract": "A method for improved energy storage using solid-state electrolytes.",
            }],
            # Second call: applicants
            [
                {"person_name": "SIEMENS AG", "person_ctry_code": "DE"},
                {"person_name": "BASF SE", "person_ctry_code": "DE"},
            ],
            # Third call: CPC codes
            [
                {"cpc_class_symbol": "H01M10/0562"},
                {"cpc_class_symbol": "H02J7/00"},
            ],
        ]

        res = app_client.get("/api/patent/42")
        assert res.status_code == 200
        data = res.json()

        # Basic info
        assert data["appln_id"] == 42
        assert data["appln_auth"] == "EP"
        assert data["appln_nr"] == "1234567"
        assert data["docdb_family_id"] == 99999
        assert data["title"] == "Method for energy storage"

        # Applicants
        assert len(data["applicants"]) == 2
        assert data["applicants"][0]["person_name"] == "SIEMENS AG"
        assert data["applicants"][0]["person_ctry_code"] == "DE"

        # CPC codes
        assert len(data["cpc_codes"]) == 2
        assert data["cpc_codes"][0] == "H01M10/0562"

    def test_patent_not_found(self, app_client, mock_patstat_client):
        """Returns 404 when appln_id does not exist."""
        mock_patstat_client.sql_query.side_effect = [
            [],  # No basic info found
        ]

        res = app_client.get("/api/patent/99999999")
        assert res.status_code == 404

    def test_patent_with_no_applicants(self, app_client, mock_patstat_client):
        """Returns patent even if no applicants or CPC codes are linked."""
        mock_patstat_client.sql_query.side_effect = [
            [{"appln_id": 1, "appln_auth": "US", "appln_nr": "111", "appln_kind": "A",
              "appln_filing_date": "2021-01-01", "appln_filing_year": 2021,
              "docdb_family_id": 1, "granted": 0,
              "title": "Test patent", "title_lang": "en", "abstract": None}],
            [],  # no applicants
            [],  # no CPC codes
        ]

        res = app_client.get("/api/patent/1")
        assert res.status_code == 200
        data = res.json()
        assert data["applicants"] == []
        assert data["cpc_codes"] == []
        assert data["abstract"] is None

    def test_patent_queries_correct_sql(self, app_client, mock_patstat_client):
        """Verifies the SQL queries use the correct appln_id."""
        mock_patstat_client.sql_query.side_effect = [
            [{"appln_id": 123, "appln_auth": "DE", "appln_nr": "555", "appln_kind": "A",
              "appln_filing_date": "2022-06-01", "appln_filing_year": 2022,
              "docdb_family_id": 77, "granted": 0,
              "title": "Title", "title_lang": "en", "abstract": "Abstract"}],
            [],
            [],
        ]

        app_client.get("/api/patent/123")

        # All three queries should contain the appln_id
        assert mock_patstat_client.sql_query.call_count == 3
        for call in mock_patstat_client.sql_query.call_args_list:
            sql = call[0][0]
            assert "123" in sql

    def test_invalid_appln_id_returns_400(self, app_client, mock_patstat_client):
        """Non-integer appln_id should return 400."""
        res = app_client.get("/api/patent/not-a-number")
        assert res.status_code in (400, 422)  # FastAPI validation


# --- Co-occurrence endpoint ---

class TestCoOccurrence:
    def test_returns_matrix(self, app_client, mock_patstat_client):
        """POST /api/co-occurrence returns a list of {row, col, count} entries."""
        mock_patstat_client.sql_query.return_value = [
            {"section1": "A", "section2": "B", "family_count": 42},
            {"section1": "A", "section2": "C", "family_count": 10},
            {"section1": "B", "section2": "C", "family_count": 5},
        ]
        res = app_client.post("/api/co-occurrence", json={
            "where_clause": "pa.applt_seq_nr > 0 AND p.person_name = 'BASF SE'"
        })
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 3
        assert data[0]["section1"] == "A"
        assert data[0]["section2"] == "B"
        assert data[0]["family_count"] == 42

    def test_with_cpc_filter(self, app_client, mock_patstat_client):
        """Supports optional CPC prefix filter."""
        mock_patstat_client.sql_query.return_value = []
        res = app_client.post("/api/co-occurrence", json={
            "where_clause": "1=1",
            "cpc_prefix": "H01"
        })
        assert res.status_code == 200
        # Verify the SQL includes the CPC prefix in some form
        sql = mock_patstat_client.sql_query.call_args[0][0]
        assert "H01" in sql

    def test_empty_result(self, app_client, mock_patstat_client):
        """Returns empty list when no co-occurrences found."""
        mock_patstat_client.sql_query.return_value = []
        res = app_client.post("/api/co-occurrence", json={
            "where_clause": "1=0"
        })
        assert res.status_code == 200
        assert res.json() == []

    def test_requires_where_clause(self, app_client, mock_patstat_client):
        """where_clause is required."""
        res = app_client.post("/api/co-occurrence", json={})
        assert res.status_code == 422  # pydantic validation
