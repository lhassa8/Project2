"""Tests for core models — approval signatures, environment validation."""

import pytest
from app.models import ApprovalRecord, EnvironmentConfig


class TestApprovalRecord:
    def test_sign_and_verify(self):
        record = ApprovalRecord(run_id="run_123", decision="approved")
        record.sign()
        assert record.signature != ""
        assert record.verify() is True

    def test_verify_detects_tampered_decision(self):
        record = ApprovalRecord(run_id="run_123", decision="approved")
        record.sign()
        record.decision = "rejected"
        assert record.verify() is False

    def test_verify_detects_tampered_run_id(self):
        record = ApprovalRecord(run_id="run_123", decision="approved")
        record.sign()
        record.run_id = "run_evil"
        assert record.verify() is False

    def test_verify_empty_signature_fails(self):
        record = ApprovalRecord(run_id="run_123", decision="approved")
        assert record.verify() is False

    def test_verify_detects_tampered_timestamp(self):
        from datetime import datetime, timezone, timedelta
        record = ApprovalRecord(run_id="run_123", decision="approved")
        record.sign()
        record.approved_at = datetime.now(timezone.utc) + timedelta(hours=1)
        assert record.verify() is False

    def test_different_decisions_different_signatures(self):
        r1 = ApprovalRecord(run_id="run_123", decision="approved")
        r2 = ApprovalRecord(run_id="run_123", decision="rejected")
        # Force same timestamp
        r2.approved_at = r1.approved_at
        r1.sign()
        r2.sign()
        assert r1.signature != r2.signature


class TestEnvironmentConfig:
    def test_valid_config(self):
        config = EnvironmentConfig(
            filesystem={"a.txt": "hello"},
            database={"users": [{"id": 1}]},
            http_stubs=[],
        )
        assert len(config.filesystem) == 1

    def test_empty_config(self):
        config = EnvironmentConfig()
        assert config.filesystem == {}
        assert config.database == {}
        assert config.http_stubs == []

    def test_too_many_files(self):
        with pytest.raises(ValueError, match="exceeds 50 files"):
            EnvironmentConfig(filesystem={f"file{i}.txt": "x" for i in range(51)})

    def test_file_too_large(self):
        with pytest.raises(ValueError, match="exceeds 100000 bytes"):
            EnvironmentConfig(filesystem={"big.txt": "x" * 100_001})

    def test_too_many_tables(self):
        with pytest.raises(ValueError, match="exceeds 20 tables"):
            EnvironmentConfig(database={f"table{i}": [] for i in range(21)})

    def test_too_many_rows(self):
        with pytest.raises(ValueError, match="exceeds 500 rows"):
            EnvironmentConfig(database={"big": [{"id": i} for i in range(501)]})

    def test_too_many_stubs(self):
        with pytest.raises(ValueError, match="exceeds 50 stubs"):
            EnvironmentConfig(http_stubs=[{"url_pattern": f"url{i}"} for i in range(51)])

    def test_at_limits_ok(self):
        config = EnvironmentConfig(
            filesystem={f"f{i}": "x" for i in range(50)},
            database={f"t{i}": [{"id": j} for j in range(500)] for i in range(20)},
            http_stubs=[{"url_pattern": f"u{i}"} for i in range(50)],
        )
        assert len(config.filesystem) == 50
