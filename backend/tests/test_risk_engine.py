"""Tests for the risk scoring engine."""

import pytest
from app.services.risk_engine import score_action, score_run, RiskReport


class TestScoreAction:
    def test_file_write_has_blast_radius(self):
        action = {"action_type": "tool_call", "content": {"tool": "write_file", "arguments": {"path": "/data.txt", "content": "hello"}}, "sequence": 1}
        signals = score_action(action)
        assert any(s.category == "blast_radius" for s in signals)

    def test_sensitive_file_read(self):
        action = {"action_type": "tool_call", "content": {"tool": "read_file", "arguments": {"path": ".env.production"}}, "sequence": 1}
        signals = score_action(action)
        assert any(s.category == "data_sensitivity" for s in signals)

    def test_email_with_pii(self):
        action = {"action_type": "tool_call", "content": {"tool": "send_email", "arguments": {"to": "alice@example.com", "body": "SSN: 123-45-6789", "subject": "test"}}, "sequence": 1}
        signals = score_action(action)
        assert any("SSN" in s.description for s in signals)

    def test_dangerous_sql(self):
        action = {"action_type": "tool_call", "content": {"tool": "query_database", "arguments": {"query": "DROP TABLE users"}}, "sequence": 1}
        signals = score_action(action)
        assert any(s.severity >= 90 for s in signals)

    def test_delete_http_request_irreversibility(self):
        action = {"action_type": "tool_call", "content": {"tool": "http_request", "arguments": {"method": "DELETE", "url": "https://api.com/users/1"}}, "sequence": 1}
        signals = score_action(action)
        assert any(s.category == "reversibility" for s in signals)

    def test_thought_with_escalation(self):
        action = {"action_type": "thought", "content": {"text": "I need to get admin access to override the permissions"}, "sequence": 1}
        signals = score_action(action)
        assert any(s.category == "privilege_escalation" for s in signals)

    def test_safe_read_has_no_high_signals(self):
        action = {"action_type": "tool_call", "content": {"tool": "read_file", "arguments": {"path": "/readme.md"}}, "sequence": 1}
        signals = score_action(action)
        assert all(s.severity < 50 for s in signals) if signals else True

    def test_multiple_email_recipients(self):
        action = {"action_type": "tool_call", "content": {"tool": "send_email", "arguments": {"to": "a@x.com,b@x.com", "body": "hi", "subject": "test"}}, "sequence": 1}
        signals = score_action(action)
        assert any("multiple recipients" in s.description.lower() for s in signals)


class TestScoreRun:
    def test_empty_run_is_low_risk(self):
        report = score_run([], [])
        assert report.risk_level == "low"
        assert report.overall_score == 0

    def test_high_mutation_count_raises_score(self):
        actions = [
            {"action_type": "tool_call", "content": {"tool": "write_file", "arguments": {"path": f"/file{i}.txt", "content": "x"}}, "sequence": i}
            for i in range(10)
        ]
        report = score_run(actions, [])
        assert report.overall_score > 0
        assert any("mutation" in s.description.lower() for s in report.signals)

    def test_multi_system_raises_blast_radius(self):
        diffs = [
            {"system": "filesystem", "resource_id": "/a.txt"},
            {"system": "database", "resource_id": "users/1"},
            {"system": "email", "resource_id": "bob@x.com"},
            {"system": "http", "resource_id": "https://api.com"},
        ]
        report = score_run([], diffs)
        assert any("system" in s.description.lower() for s in report.signals)

    def test_report_to_dict(self):
        report = score_run([], [])
        d = report.to_dict()
        assert "overall_score" in d
        assert "risk_level" in d
        assert "signals" in d
        assert "summary" in d
        assert "recommendations" in d

    def test_recommendations_for_sensitive_data(self):
        actions = [
            {"action_type": "tool_call", "content": {"tool": "read_file", "arguments": {"path": "credentials.json"}}, "sequence": 1},
        ]
        report = score_run(actions, [])
        assert any("data access" in r.lower() for r in report.recommendations)

    def test_critical_risk_level(self):
        actions = [
            {"action_type": "tool_call", "content": {"tool": "query_database", "arguments": {"query": "DROP TABLE users"}}, "sequence": 1},
        ]
        report = score_run(actions, [])
        assert report.risk_level in ("critical", "high")
        assert report.overall_score >= 60
