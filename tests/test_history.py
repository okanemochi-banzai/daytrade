"""
history モジュールのユニットテスト
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from history import load_history, append_today_signal, get_recent_entries


def _make_signal(verdict="buy_bias", label="買いポジ主体", conf="high", diff=300.0):
    return {
        "verdict": verdict,
        "verdict_label": label,
        "confidence": conf,
        "futures_diff": diff,
    }


def _make_market(nasdaq=1.0, dow=0.5, sox=2.0):
    return {
        "us_markets": {
            "nasdaq_change_pct": nasdaq,
            "dow_change_pct": dow,
            "sox_change_pct": sox,
        }
    }


def test_load_history_missing_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "missing.json"
        history = load_history(path)
        assert history == []
    print("✅ test_load_history_missing_file")


def test_append_creates_new_history():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "history.json"
        result = append_today_signal(
            path,
            _make_signal(),
            _make_market(),
            warnings=[],
        )
        assert len(result) == 1
        assert result[0]["verdict"] == "buy_bias"
        # ファイルに書き込まれている
        loaded = load_history(path)
        assert len(loaded) == 1
    print("✅ test_append_creates_new_history")


def test_append_overwrites_same_day():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "history.json"
        # 1回目
        append_today_signal(path, _make_signal(verdict="buy_bias"), _make_market(), [])
        # 2回目（同日に再実行）
        append_today_signal(path, _make_signal(verdict="sell_bias"), _make_market(), [])
        loaded = load_history(path)
        assert len(loaded) == 1
        assert loaded[0]["verdict"] == "sell_bias"
    print("✅ test_append_overwrites_same_day")


def test_get_recent_entries_sorted_desc():
    history = [
        {"date": "2026-04-20", "verdict": "buy_bias"},
        {"date": "2026-04-22", "verdict": "sell_bias"},
        {"date": "2026-04-21", "verdict": "hands_off"},
    ]
    recent = get_recent_entries(history, n=2)
    assert recent[0]["date"] == "2026-04-22"
    assert recent[1]["date"] == "2026-04-21"
    print("✅ test_get_recent_entries_sorted_desc")


def test_history_keeps_warnings():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "history.json"
        warnings = [{"label": "📅 金曜手仕舞い"}, {"label": "🏖️ 3連休前"}]
        result = append_today_signal(path, _make_signal(), _make_market(), warnings)
        assert "📅 金曜手仕舞い" in result[-1]["warnings"]
    print("✅ test_history_keeps_warnings")


def test_history_corrupt_file_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "history.json"
        path.write_text("not valid json", encoding="utf-8")
        history = load_history(path)
        assert history == []
    print("✅ test_history_corrupt_file_returns_empty")


if __name__ == "__main__":
    test_load_history_missing_file()
    test_append_creates_new_history()
    test_append_overwrites_same_day()
    test_get_recent_entries_sorted_desc()
    test_history_keeps_warnings()
    test_history_corrupt_file_returns_empty()
    print("\n🎉 All history tests passed!")
