"""
Unit tests for the scheduler Lambda handler.

Patches urllib.request.urlopen so no real HTTP calls are made.
"""

import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Provide required env var before importing the module
os.environ.setdefault("APP_RUNNER_URL", "https://researcher.example.com")

# Re-import to pick up env var
if "lambda_function" in sys.modules:
    del sys.modules["lambda_function"]

# Add parent dir so the import resolves
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from lambda_function import _build_payload, handler  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_context(request_id: str = "test-req-id"):
    ctx = types.SimpleNamespace()
    ctx.aws_request_id = request_id
    return ctx


def _make_response(status: int, body: dict):
    """Return a mock urllib response."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(body).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# _build_payload
# ---------------------------------------------------------------------------

class TestBuildPayload(unittest.TestCase):
    def test_defaults(self):
        payload = _build_payload()
        self.assertIn("mode", payload)
        self.assertIn("window", payload)
        self.assertIn("ingest", payload)

    def test_auto_mode_no_tickers(self):
        payload = _build_payload()
        self.assertNotIn("tickers", payload)
        self.assertNotIn("sector", payload)


# ---------------------------------------------------------------------------
# handler — success path
# ---------------------------------------------------------------------------

class TestHandlerSuccess(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_200_returns_ok(self, mock_urlopen):
        mock_urlopen.return_value = _make_response(200, {
            "run_id": "abc123",
            "mode": "auto",
            "parse_ok": True,
            "duration_ms": 12000,
            "brief": {"items": [], "top_signal": None},
        })
        result = handler({}, _fake_context())
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("message", body)

    @patch("urllib.request.urlopen")
    def test_event_overrides_mode(self, mock_urlopen):
        mock_urlopen.return_value = _make_response(200, {
            "run_id": "xyz", "mode": "ticker", "parse_ok": True,
            "duration_ms": 5000, "brief": {"items": []},
        })
        result = handler({"mode": "ticker", "tickers": ["NVDA"]}, _fake_context())
        self.assertEqual(result["statusCode"], 200)
        # Confirm the POST was called with the ticker payload
        call_args = mock_urlopen.call_args[0][0]
        sent_payload = json.loads(call_args.data.decode())
        self.assertEqual(sent_payload["mode"], "ticker")
        self.assertIn("NVDA", sent_payload["tickers"])


# ---------------------------------------------------------------------------
# handler — error paths
# ---------------------------------------------------------------------------

class TestHandlerErrors(unittest.TestCase):
    def test_missing_url_returns_500(self):
        import lambda_function as lf
        original = lf.APP_RUNNER_URL
        lf.APP_RUNNER_URL = ""
        try:
            result = handler({}, _fake_context())
            self.assertEqual(result["statusCode"], 500)
        finally:
            lf.APP_RUNNER_URL = original

    @patch("urllib.request.urlopen")
    def test_non_200_propagated(self, mock_urlopen):
        import urllib.error
        exc = urllib.error.HTTPError(
            url="https://x", code=504, msg="Timeout",
            hdrs=None, fp=MagicMock(read=lambda: b'{"detail":"timeout"}'),
        )
        mock_urlopen.side_effect = exc
        result = handler({}, _fake_context())
        self.assertEqual(result["statusCode"], 504)


if __name__ == "__main__":
    unittest.main()
