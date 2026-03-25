"""Tests for SQL extraction helpers."""

import pytest


class TestExtractSql:
    def test_pure_sql(self):
        from sidecar import _extract_sql
        assert _extract_sql("SELECT 1") == "SELECT 1"

    def test_markdown_fences(self):
        from sidecar import _extract_sql
        text = "```sql\nSELECT * FROM tls201_appln LIMIT 10\n```"
        assert _extract_sql(text) == "SELECT * FROM tls201_appln LIMIT 10"

    def test_markdown_fences_no_lang(self):
        from sidecar import _extract_sql
        text = "```\nSELECT 1\n```"
        assert _extract_sql(text) == "SELECT 1"

    def test_sql_with_trailing_explanation(self):
        from sidecar import _extract_sql
        text = "SELECT COUNT(*) FROM tls201_appln\nThis query counts all applications."
        result = _extract_sql(text)
        assert "SELECT" in result
        assert "This query" not in result

    def test_strips_trailing_semicolons(self):
        from sidecar import _extract_sql
        assert _extract_sql("SELECT 1;") == "SELECT 1"

    def test_multiline_sql(self):
        from sidecar import _extract_sql
        text = """SELECT
    p.person_name,
    COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls206_person p
JOIN tls207_pers_appln pa ON p.person_id = pa.person_id
JOIN tls201_appln a ON pa.appln_id = a.appln_id
WHERE pa.applt_seq_nr > 0
GROUP BY p.person_name
ORDER BY families DESC
LIMIT 20"""
        result = _extract_sql(text)
        assert result.startswith("SELECT")
        assert "LIMIT 20" in result

    def test_mixed_text_with_fenced_sql(self):
        from sidecar import _extract_sql
        text = """Here is the query:

```sql
SELECT person_name FROM tls206_person LIMIT 5
```

This will return the top 5 persons."""
        result = _extract_sql(text)
        assert result == "SELECT person_name FROM tls206_person LIMIT 5"


class TestExtractLastSqlFromMessages:
    def test_finds_last_execute_query(self):
        from sidecar import _extract_last_sql_from_messages
        messages = [
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "1", "name": "execute_query",
                 "input": {"query": "SELECT 1"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "1", "content": "ok"},
            ]},
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "2", "name": "execute_query",
                 "input": {"query": "SELECT person_name FROM tls206_person LIMIT 10"}},
            ]},
        ]
        result = _extract_last_sql_from_messages(messages)
        assert result == "SELECT person_name FROM tls206_person LIMIT 10"

    def test_returns_none_when_no_execute_query(self):
        from sidecar import _extract_last_sql_from_messages
        messages = [
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "1", "name": "list_tables", "input": {}},
            ]},
        ]
        assert _extract_last_sql_from_messages(messages) is None

    def test_skips_non_select_queries(self):
        from sidecar import _extract_last_sql_from_messages
        messages = [
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "1", "name": "execute_query",
                 "input": {"query": "SHOW TABLES"}},
            ]},
        ]
        assert _extract_last_sql_from_messages(messages) is None

    def test_empty_messages(self):
        from sidecar import _extract_last_sql_from_messages
        assert _extract_last_sql_from_messages([]) is None
