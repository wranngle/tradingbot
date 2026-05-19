"""Tests for the drawdown-breach alarm webhook (`alarm.py`).

The plan §7.2 contract: when drawdown exceeds a tier threshold, a POST
fires with `"breach": true` and the drawdown value in the payload. We
also pin the dual no-op surfaces (no breach → no POST; --dry-run → no
POST) because a leaky alarm is worse than a silent one.
"""

from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import alarm  # noqa: E402


# ---- evaluate() -----------------------------------------------------


def test_evaluate_below_lowest_tier_does_not_breach():
    result = alarm.evaluate({"current_drawdown_pct": 1.0})
    assert result.breach is False
    assert result.tier is None
    assert result.threshold_pct is None


def test_evaluate_at_threshold_breaches_that_tier():
    result = alarm.evaluate({"current_drawdown_pct": 10.0})
    assert result.breach is True
    assert result.tier == "warn"
    assert result.threshold_pct == 10.0


def test_evaluate_returns_highest_breached_tier():
    result = alarm.evaluate({"current_drawdown_pct": 25.5})
    assert result.breach is True
    assert result.tier == "critical"
    assert result.threshold_pct == 20.0


def test_evaluate_rejects_negative_drawdown():
    with pytest.raises(ValueError, match="non-negative"):
        alarm.evaluate({"current_drawdown_pct": -3.0})


def test_evaluate_rejects_missing_field():
    with pytest.raises(ValueError, match="current_drawdown_pct"):
        alarm.evaluate({})


# ---- fire() ---------------------------------------------------------


def test_fire_breach_posts_with_breach_true_and_drawdown():
    poster = MagicMock(return_value=200)
    snapshot = {
        "current_drawdown_pct": 22.5,
        "strategy": "core",
        "regime": "crisis",
        "asof": "2026-05-14",
    }
    evaluation, posted = alarm.fire(
        snapshot, "https://hooks.example/abc", poster=poster
    )

    assert posted is True
    assert evaluation.breach is True
    poster.assert_called_once()
    url, payload = poster.call_args.args[0], poster.call_args.args[1]
    assert url == "https://hooks.example/abc"
    assert payload["breach"] is True
    assert payload["drawdown_pct"] == 22.5
    assert payload["tier"] == "critical"
    assert payload["strategy"] == "core"
    assert payload["regime"] == "crisis"
    assert "core drawdown 22.50% breached" in payload["text"]


def test_fire_no_breach_skips_post_by_default():
    poster = MagicMock()
    snapshot = {"current_drawdown_pct": 2.0}
    evaluation, posted = alarm.fire(
        snapshot, "https://hooks.example/abc", poster=poster
    )
    assert posted is False
    assert evaluation.breach is False
    poster.assert_not_called()


def test_fire_only_on_breach_false_posts_even_when_clean():
    poster = MagicMock()
    snapshot = {"current_drawdown_pct": 2.0}
    _, posted = alarm.fire(
        snapshot,
        "https://hooks.example/abc",
        poster=poster,
        only_on_breach=False,
    )
    assert posted is True
    poster.assert_called_once()
    payload = poster.call_args.args[1]
    assert payload["breach"] is False


# ---- _post() (the urllib seam mocked as `requests.post` analogue) ---


def test_post_serializes_json_and_uses_urlopen():
    """The mocking-target equivalent of `requests.post` in stdlib.

    Plan wording was 'mocks requests.post'; this project is stdlib-only
    so the equivalent seam is `urllib.request.urlopen`. We patch that
    and assert: POST verb, JSON content-type, body contains breach:true
    plus the drawdown value — that is the plan's contract.
    """
    captured: dict[str, object] = {}

    class _FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse()

    with patch.object(alarm.urllib.request, "urlopen", side_effect=fake_urlopen):
        status = alarm._post(
            "https://hooks.example/xyz",
            {"breach": True, "drawdown_pct": 27.0, "text": "boom"},
        )

    assert status == 200
    assert captured["url"] == "https://hooks.example/xyz"
    assert captured["method"] == "POST"
    assert captured["headers"].get("Content-type") == "application/json"
    assert captured["body"]["breach"] is True
    assert captured["body"]["drawdown_pct"] == 27.0


# ---- CLI end-to-end -------------------------------------------------


def _write_snapshot(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_cli_breach_posts_payload(tmp_path, capsys, monkeypatch):
    snapshot_path = _write_snapshot(
        tmp_path,
        {"current_drawdown_pct": 24.0, "strategy": "experimental"},
    )
    posted: list[tuple[str, dict]] = []

    def fake_post(url, payload, timeout=5.0):
        posted.append((url, payload))
        return 200

    monkeypatch.setattr(alarm, "_post", fake_post)

    code = alarm.main(
        [
            "--input",
            str(snapshot_path),
            "--url",
            "https://hooks.example/abc",
        ]
    )
    out = capsys.readouterr().out

    assert code == 0
    assert len(posted) == 1
    url, payload = posted[0]
    assert url == "https://hooks.example/abc"
    assert payload["breach"] is True
    assert payload["drawdown_pct"] == 24.0
    assert json.loads(out)["posted"] is True


def test_cli_no_breach_does_not_post(tmp_path, capsys, monkeypatch):
    snapshot_path = _write_snapshot(tmp_path, {"current_drawdown_pct": 3.0})

    def fail_post(*_args, **_kwargs):
        pytest.fail("network POST should not fire on no-breach")

    monkeypatch.setattr(alarm, "_post", fail_post)
    code = alarm.main(
        ["--input", str(snapshot_path), "--url", "https://hooks.example/abc"]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert json.loads(out) == {"breach": False, "posted": False}


def test_cli_dry_run_emits_payload_and_does_not_post(
    tmp_path, capsys, monkeypatch
):
    snapshot_path = _write_snapshot(tmp_path, {"current_drawdown_pct": 50.0})
    monkeypatch.setattr(
        alarm,
        "_post",
        lambda *_a, **_k: pytest.fail("dry-run must not POST"),
    )

    code = alarm.main(
        ["--input", str(snapshot_path), "--url", "https://x", "--dry-run"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["breach"] is True
    assert payload["drawdown_pct"] == 50.0
    assert payload["tier"] == "critical"


def test_cli_missing_url_when_breach_returns_2(tmp_path, capsys, monkeypatch):
    snapshot_path = _write_snapshot(tmp_path, {"current_drawdown_pct": 30.0})
    monkeypatch.delenv("ALARM_WEBHOOK_URL", raising=False)
    code = alarm.main(["--input", str(snapshot_path)])
    err = capsys.readouterr().err
    assert code == 2
    assert "ALARM_WEBHOOK_URL" in err or "--url" in err


def test_cli_env_var_supplies_url(tmp_path, capsys, monkeypatch):
    snapshot_path = _write_snapshot(tmp_path, {"current_drawdown_pct": 30.0})
    posted: list[str] = []
    monkeypatch.setenv("ALARM_WEBHOOK_URL", "https://hooks.example/from-env")
    monkeypatch.setattr(
        alarm, "_post", lambda url, _p, **_k: posted.append(url) or 200
    )
    code = alarm.main(["--input", str(snapshot_path)])
    assert code == 0
    assert posted == ["https://hooks.example/from-env"]


def test_cli_network_failure_returns_1(tmp_path, capsys, monkeypatch):
    snapshot_path = _write_snapshot(tmp_path, {"current_drawdown_pct": 30.0})

    def boom(*_a, **_k):
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(alarm, "_post", boom)
    code = alarm.main(
        ["--input", str(snapshot_path), "--url", "https://hooks.example/x"]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "webhook POST failed" in err
