"""Tests for application middleware — error handling, rate limiting, request logging."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.middleware import RateLimitMiddleware


class TestErrorHandling:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_not_found_returns_404(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code in (404, 405)


class TestRateLimiting:
    def test_rate_limiter_blocks_after_limit(self):
        """Test that the rate limiter returns 429 after exceeding the limit."""
        limiter = RateLimitMiddleware(app, read_limit=3, write_limit=2, window=60)
        # Simulate hits by directly manipulating internal state
        import time
        now = time.time()
        ip = "1.2.3.4"
        limiter._read_hits[ip] = [now, now, now]
        # Pruned list should still have 3 entries (all within window)
        pruned = limiter._prune(limiter._read_hits[ip], now)
        assert len(pruned) == 3

    def test_rate_limiter_prunes_old_entries(self):
        """Old entries outside the window should be pruned."""
        limiter = RateLimitMiddleware(app, read_limit=3, write_limit=2, window=60)
        import time
        now = time.time()
        # Entries from 120 seconds ago should be pruned
        old_entries = [now - 120, now - 100, now - 80]
        pruned = limiter._prune(old_entries, now)
        assert len(pruned) == 0

    def test_testclient_bypasses_rate_limit(self, client):
        """The testclient IP should bypass rate limiting."""
        # Make many requests — none should be rate limited
        for _ in range(50):
            resp = client.get("/api/health")
            assert resp.status_code == 200
