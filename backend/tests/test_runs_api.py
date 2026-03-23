"""Tests for the runs API — workspace isolation, approval flow, export, replay."""

import pytest


class TestGetRun:
    def test_get_existing_run(self, client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = client.get("/api/runs/run_test_001")
        assert resp.status_code == 200
        assert resp.json()["id"] == "run_test_001"

    def test_get_nonexistent_run(self, client):
        resp = client.get("/api/runs/nonexistent")
        assert resp.status_code == 404

    def test_workspace_isolation(self, other_workspace_client, run_store, sample_run_data):
        """A run from ws_test should not be visible to ws_other."""
        run_store.save(sample_run_data)
        # other_workspace_client is ws_other — should not see ws_test's run
        resp = other_workspace_client.get("/api/runs/run_test_001")
        assert resp.status_code == 404


class TestListRuns:
    def test_list_empty(self, client):
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json()["runs"] == []
        assert resp.json()["total"] == 0

    def test_list_scoped_to_workspace(self, client, other_workspace_client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        # Different workspace sees nothing
        resp = other_workspace_client.get("/api/runs")
        assert resp.json()["total"] == 0

    def test_filter_by_status(self, client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = client.get("/api/runs?status=complete")
        assert resp.json()["total"] == 1
        resp2 = client.get("/api/runs?status=running")
        assert resp2.json()["total"] == 0


class TestApproval:
    def test_approve_completed_run(self, client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = client.post("/api/runs/run_test_001/approve", json={
            "decision": "approved",
            "reviewer_notes": "Looks good",
        })
        assert resp.status_code == 200
        assert resp.json()["decision"] == "approved"
        assert resp.json()["signature"] != ""

    def test_reject_run(self, client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = client.post("/api/runs/run_test_001/approve", json={
            "decision": "rejected",
            "reviewer_notes": "Too risky",
        })
        assert resp.status_code == 200
        assert resp.json()["decision"] == "rejected"

    def test_cannot_approve_running_run(self, client, run_store, sample_run_data):
        sample_run_data["status"] = "running"
        run_store.save(sample_run_data)
        resp = client.post("/api/runs/run_test_001/approve", json={"decision": "approved"})
        assert resp.status_code == 400

    def test_viewer_cannot_approve(self, viewer_client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = viewer_client.post("/api/runs/run_test_001/approve", json={"decision": "approved"})
        assert resp.status_code == 403

    def test_cross_workspace_approve_blocked(self, other_workspace_client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = other_workspace_client.post("/api/runs/run_test_001/approve", json={"decision": "approved"})
        assert resp.status_code == 404

    def test_approval_signature_persisted(self, client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        client.post("/api/runs/run_test_001/approve", json={"decision": "approved"})
        run = run_store.get("run_test_001")
        assert run["approval"]["signature"] != ""
        # Verify the signature is valid
        from app.models import ApprovalRecord
        record = ApprovalRecord(**run["approval"])
        assert record.verify() is True


class TestExport:
    def test_export_run(self, client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = client.get("/api/runs/run_test_001/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["export_version"] == "2.0"
        assert data["run"]["id"] == "run_test_001"
        assert "risk_report" in data
        assert "environment_snapshots" in data

    def test_export_uses_stored_risk_report(self, client, run_store, sample_run_data):
        """Export should use the stored risk_report, not recompute."""
        sample_run_data["risk_report"] = {"overall_score": 99, "risk_level": "critical", "signals": [], "summary": "custom", "recommendations": []}
        run_store.save(sample_run_data)
        resp = client.get("/api/runs/run_test_001/export")
        assert resp.json()["risk_report"]["overall_score"] == 99

    def test_export_workspace_isolated(self, other_workspace_client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = other_workspace_client.get("/api/runs/run_test_001/export")
        assert resp.status_code == 404


class TestReplay:
    def test_replay_unapproved_live_blocked(self, client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = client.post("/api/runs/run_test_001/replay", json={"target": "live"})
        assert resp.status_code == 400
        assert "not approved" in resp.json()["detail"].lower() or "approved" in resp.json()["detail"].lower()

    def test_replay_approved_live_verifies_signature(self, client, run_store, sample_run_data):
        """Tampered approval should fail signature verification."""
        sample_run_data["approval"] = {
            "run_id": "run_test_001",
            "decision": "approved",
            "reviewer_notes": "",
            "approved_at": "2025-01-01T00:00:00+00:00",
            "signature": "tampered_signature",
        }
        run_store.save(sample_run_data)
        resp = client.post("/api/runs/run_test_001/replay", json={"target": "live"})
        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    def test_replay_cross_workspace_blocked(self, other_workspace_client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = other_workspace_client.post("/api/runs/run_test_001/replay", json={"target": "sandbox"})
        assert resp.status_code == 404


class TestCompare:
    def test_compare_cross_workspace_blocked(self, other_workspace_client, run_store, sample_run_data):
        run_store.save(sample_run_data)
        resp = other_workspace_client.post("/api/runs/compare", json={
            "run_id_a": "run_test_001",
            "run_id_b": "run_test_001",
        })
        assert resp.status_code == 404
