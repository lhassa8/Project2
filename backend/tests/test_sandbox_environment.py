"""Tests for the SandboxEnvironment — stateful mock world."""

import pytest
from app.services.sandbox_environment import SandboxEnvironment, HttpStub


class TestFilesystem:
    def test_read_seeded_file(self):
        env = SandboxEnvironment({"filesystem": {"readme.md": "# Hello"}, "database": {}, "http_stubs": []})
        result, diffs = env.read_file("readme.md")
        assert result["content"] == "# Hello"
        assert diffs == []

    def test_read_missing_file(self):
        env = SandboxEnvironment()
        result, diffs = env.read_file("/missing.txt")
        assert "error" in result
        assert result["exists"] is False

    def test_write_creates_file(self):
        env = SandboxEnvironment()
        result, diffs = env.write_file("/new.txt", "content")
        assert result["success"] is True
        assert len(diffs) == 1
        assert diffs[0].change_type == "created"
        # Can read back
        r2, _ = env.read_file("/new.txt")
        assert r2["content"] == "content"

    def test_write_modifies_existing(self):
        env = SandboxEnvironment({"filesystem": {"/a.txt": "old"}, "database": {}, "http_stubs": []})
        _, diffs = env.write_file("/a.txt", "new")
        assert diffs[0].change_type == "modified"
        assert diffs[0].before == "old"
        assert diffs[0].after == "new"


class TestDatabase:
    @pytest.fixture()
    def env(self):
        return SandboxEnvironment({
            "filesystem": {},
            "database": {
                "users": [
                    {"id": 1, "name": "Alice", "role": "admin"},
                    {"id": 2, "name": "Bob", "role": "viewer"},
                ],
            },
            "http_stubs": [],
        })

    def test_select_all(self, env):
        result, diffs = env.query_database("SELECT * FROM users")
        assert result["row_count"] == 2
        assert diffs == []

    def test_select_with_where(self, env):
        result, _ = env.query_database("SELECT * FROM users WHERE id = 1")
        assert result["row_count"] == 1
        assert result["rows"][0]["name"] == "Alice"

    def test_select_with_limit(self, env):
        result, _ = env.query_database("SELECT * FROM users LIMIT 1")
        assert result["row_count"] == 1

    def test_insert(self, env):
        result, diffs = env.query_database("INSERT INTO users (name, role) VALUES ('Carol', 'editor')")
        assert result["affected_rows"] == 1
        assert result["generated_id"] == 3
        assert len(diffs) == 1
        assert diffs[0].change_type == "created"
        # Verify inserted
        r2, _ = env.query_database("SELECT * FROM users WHERE id = 3")
        assert r2["row_count"] == 1

    def test_update(self, env):
        result, diffs = env.query_database("UPDATE users SET role = 'editor' WHERE id = 2")
        assert result["affected_rows"] == 1
        assert diffs[0].change_type == "modified"

    def test_delete(self, env):
        result, diffs = env.query_database("DELETE FROM users WHERE id = 2")
        assert result["affected_rows"] == 1
        assert diffs[0].change_type == "deleted"
        # Verify deleted
        r2, _ = env.query_database("SELECT * FROM users")
        assert r2["row_count"] == 1

    def test_unknown_table_select(self, env):
        result, _ = env.query_database("SELECT * FROM nonexistent")
        assert result["row_count"] == 0


class TestEmail:
    def test_send_email(self):
        env = SandboxEnvironment()
        result, diffs = env.send_email("alice@x.com", "Subject", "Body")
        assert result["status"] == "sent"
        assert result["to"] == "alice@x.com"
        assert len(diffs) == 1
        assert diffs[0].system == "email"
        assert len(env.emails_sent) == 1


class TestHTTP:
    def test_stub_matched(self):
        env = SandboxEnvironment({
            "filesystem": {},
            "database": {},
            "http_stubs": [
                {"url_pattern": "api.example.com", "method": "GET", "status_code": 200, "response_body": {"data": "stubbed"}},
            ],
        })
        result, diffs = env.http_request("GET", "https://api.example.com/v1")
        assert result["body"]["data"] == "stubbed"

    def test_unmatched_falls_back(self):
        env = SandboxEnvironment()
        result, _ = env.http_request("GET", "https://unknown.com/api")
        assert result["status_code"] == 200  # default fallback

    def test_post_creates_diff(self):
        env = SandboxEnvironment()
        _, diffs = env.http_request("POST", "https://api.com/data", {"key": "val"})
        assert len(diffs) == 1
        assert diffs[0].system == "http"

    def test_get_no_diff(self):
        env = SandboxEnvironment()
        _, diffs = env.http_request("GET", "https://api.com/data")
        assert diffs == []


class TestHttpStub:
    def test_regex_match(self):
        stub = HttpStub(url_pattern=r"api\.example\.com/v\d+")
        assert stub.matches("GET", "https://api.example.com/v2/users") is True

    def test_method_filter(self):
        stub = HttpStub(url_pattern="api.com", method="POST")
        assert stub.matches("POST", "https://api.com") is True
        assert stub.matches("GET", "https://api.com") is False

    def test_invalid_regex_falls_back(self):
        stub = HttpStub(url_pattern="[invalid(regex")
        assert stub._is_regex is False
        assert stub.matches("GET", "http://[invalid(regex") is True

    def test_response_deepcopy(self):
        stub = HttpStub(url_pattern="x", response_body={"items": [1, 2]})
        r1 = stub.response()
        r1["body"]["items"].append(3)
        r2 = stub.response()
        assert len(r2["body"]["items"]) == 2  # Not mutated


class TestCheckpointRestore:
    def test_restore_reverts_writes(self):
        env = SandboxEnvironment({"filesystem": {"a.txt": "original"}, "database": {}, "http_stubs": []})
        cp = env.checkpoint()
        env.write_file("b.txt", "new file")
        env.write_file("a.txt", "modified")
        assert "b.txt" in env.filesystem
        env.restore(cp)
        assert "b.txt" not in env.filesystem
        assert env.filesystem["a.txt"] == "original"

    def test_restore_reverts_db_changes(self):
        env = SandboxEnvironment({
            "filesystem": {},
            "database": {"users": [{"id": 1, "name": "Alice"}]},
            "http_stubs": [],
        })
        cp = env.checkpoint()
        env.query_database("INSERT INTO users (name) VALUES ('Bob')")
        assert len(env.database["users"]) == 2
        env.restore(cp)
        assert len(env.database["users"]) == 1

    def test_restore_reverts_emails(self):
        env = SandboxEnvironment()
        cp = env.checkpoint()
        env.send_email("x@x.com", "hi", "body")
        assert len(env.emails_sent) == 1
        env.restore(cp)
        assert len(env.emails_sent) == 0


class TestSnapshot:
    def test_to_snapshot_captures_state(self):
        env = SandboxEnvironment({"filesystem": {"a.txt": "hello"}, "database": {}, "http_stubs": []})
        snap = env.to_snapshot()
        assert snap["filesystem"] == {"a.txt": "hello"}
        assert "database" in snap
        assert "emails_sent" in snap
        assert "http_log" in snap

    def test_snapshot_is_isolated(self):
        env = SandboxEnvironment({"filesystem": {"a.txt": "hello"}, "database": {}, "http_stubs": []})
        snap = env.to_snapshot()
        env.write_file("a.txt", "changed")
        assert snap["filesystem"]["a.txt"] == "hello"  # Not mutated
