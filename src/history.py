"""
日次判定の履歴管理モジュール

毎日の判定を docs/history.json に追記し、ダッシュボードで直近5営業日の
判定を表示できるようにする。

履歴の構造:
  [
    {
      "date": "2026-04-23",
      "verdict": "buy_bias",
      "verdict_label": "買いポジ主体",
      "confidence": "high",
      "futures_diff": -1100.0,
      "nasdaq_pct": -1.2,
      "dow_pct": -0.8,
      "sox_pct": -2.5,
      "warnings": ["📅 金曜 × 週足陽線 = 手仕舞い売り警戒"]
    },
    ...
  ]
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


JST = ZoneInfo("Asia/Tokyo")
MAX_HISTORY_ENTRIES = 60  # 約3ヶ月分まで保持


def load_history(history_path: Path) -> list[dict]:
    """履歴ファイルを読み込む。なければ空リスト。"""
    if not history_path.exists():
        return []
    try:
        with history_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️ Failed to load history: {e}")
    return []


def append_today_signal(
    history_path: Path,
    direction_signal: dict,
    market: dict,
    warnings: list[dict],
) -> list[dict]:
    """今日の判定を履歴に追記する。

    同じ日付のエントリがあれば上書き（同日中に複数回ワークフロー実行された場合の対策）。
    """
    today_str = datetime.now(JST).strftime("%Y-%m-%d")

    new_entry = {
        "date": today_str,
        "verdict": direction_signal["verdict"],
        "verdict_label": direction_signal["verdict_label"],
        "confidence": direction_signal["confidence"],
        "futures_diff": direction_signal["futures_diff"],
        "nasdaq_pct": market["us_markets"].get("nasdaq_change_pct", 0.0),
        "dow_pct": market["us_markets"].get("dow_change_pct", 0.0),
        "sox_pct": market["us_markets"].get("sox_change_pct", 0.0),
        "warnings": [w["label"] for w in warnings] if warnings else [],
    }

    history = load_history(history_path)

    # 既存の同日エントリを除外
    history = [h for h in history if h.get("date") != today_str]
    history.append(new_entry)

    # 日付昇順でソートして直近MAX_HISTORY_ENTRIES件のみ保持
    history.sort(key=lambda h: h.get("date", ""))
    history = history[-MAX_HISTORY_ENTRIES:]

    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return history


def get_recent_entries(history: list[dict], n: int = 5) -> list[dict]:
    """直近n件の履歴を新しい順で返す。"""
    sorted_h = sorted(history, key=lambda h: h.get("date", ""), reverse=True)
    return sorted_h[:n]
