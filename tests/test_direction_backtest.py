"""
direction_backtest のユニットテスト（合成データで検証）
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from direction_backtest import (
    compute_outcome_stats,
)


def _make_df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


def test_compute_outcome_stats_buy_bias_perfect():
    """買いポジ主体と判定された全日で日経が上げたケース → 勝率100%"""
    records = [
        {"verdict": "buy_bias", "intraday_pct": 0.5, "daily_pct": 0.7},
        {"verdict": "buy_bias", "intraday_pct": 1.2, "daily_pct": 1.5},
        {"verdict": "buy_bias", "intraday_pct": 0.8, "daily_pct": 1.0},
    ]
    stats = compute_outcome_stats(_make_df(records), "buy_bias", "買いポジ主体")
    assert stats.n == 3
    assert stats.n_aligned == 3
    assert stats.directional_win_rate == 1.0
    assert abs(stats.mean_intraday_pct - 0.833) < 0.01
    print("✅ test_compute_outcome_stats_buy_bias_perfect")


def test_compute_outcome_stats_buy_bias_partial():
    """買いポジ主体の日、半分上げ半分下げ → 勝率50%"""
    records = [
        {"verdict": "buy_bias", "intraday_pct": 1.0, "daily_pct": 1.2},
        {"verdict": "buy_bias", "intraday_pct": -0.5, "daily_pct": -0.3},
        {"verdict": "buy_bias", "intraday_pct": 0.8, "daily_pct": 1.0},
        {"verdict": "buy_bias", "intraday_pct": -1.2, "daily_pct": -1.5},
    ]
    stats = compute_outcome_stats(_make_df(records), "buy_bias", "買いポジ主体")
    assert stats.n == 4
    assert stats.n_aligned == 2
    assert stats.directional_win_rate == 0.5
    print("✅ test_compute_outcome_stats_buy_bias_partial")


def test_compute_outcome_stats_sell_bias_aligned_when_negative():
    """売りポジ主体は日中下げ = 方向一致"""
    records = [
        {"verdict": "sell_bias", "intraday_pct": -1.0, "daily_pct": -1.2},
        {"verdict": "sell_bias", "intraday_pct": -0.5, "daily_pct": -0.3},
        {"verdict": "sell_bias", "intraday_pct": 0.8, "daily_pct": 1.0},  # 下げ判定だが上げた
    ]
    stats = compute_outcome_stats(_make_df(records), "sell_bias", "売りポジ主体")
    assert stats.n == 3
    assert stats.n_aligned == 2   # 下げた日が2
    assert abs(stats.directional_win_rate - 2 / 3) < 0.001
    print("✅ test_compute_outcome_stats_sell_bias_aligned_when_negative")


def test_compute_outcome_stats_hands_off_aligned_when_flat():
    """初心者手出し無用は絶対値<0.3%で方向一致（レンジ相場）"""
    records = [
        {"verdict": "hands_off", "intraday_pct": 0.1, "daily_pct": 0.0},
        {"verdict": "hands_off", "intraday_pct": -0.2, "daily_pct": -0.1},
        {"verdict": "hands_off", "intraday_pct": 1.5, "daily_pct": 1.8},     # 大きく動いた
        {"verdict": "hands_off", "intraday_pct": -1.0, "daily_pct": -1.2},   # 大きく動いた
    ]
    stats = compute_outcome_stats(_make_df(records), "hands_off", "初心者手出し無用")
    assert stats.n == 4
    assert stats.n_aligned == 2   # フラット2日、動いた2日
    assert stats.directional_win_rate == 0.5
    print("✅ test_compute_outcome_stats_hands_off_aligned_when_flat")


def test_compute_outcome_stats_empty():
    """該当日0のケース"""
    records = [
        {"verdict": "hands_off", "intraday_pct": 0.1, "daily_pct": 0.0},
    ]
    stats = compute_outcome_stats(_make_df(records), "buy_bias", "買いポジ主体")
    assert stats.n == 0
    assert stats.directional_win_rate == 0.0
    print("✅ test_compute_outcome_stats_empty")


def test_compute_outcome_stats_avg_by_alignment():
    """方向一致日と不一致日で平均が分けて集計される"""
    records = [
        {"verdict": "buy_bias", "intraday_pct": 1.0, "daily_pct": 1.0},   # 一致
        {"verdict": "buy_bias", "intraday_pct": 2.0, "daily_pct": 2.0},   # 一致
        {"verdict": "buy_bias", "intraday_pct": -1.0, "daily_pct": -1.0}, # 不一致
    ]
    stats = compute_outcome_stats(_make_df(records), "buy_bias", "買いポジ主体")
    assert abs(stats.avg_when_aligned - 1.5) < 0.01  # (1.0 + 2.0) / 2
    assert abs(stats.avg_when_not_aligned - (-1.0)) < 0.01
    print("✅ test_compute_outcome_stats_avg_by_alignment")


if __name__ == "__main__":
    test_compute_outcome_stats_buy_bias_perfect()
    test_compute_outcome_stats_buy_bias_partial()
    test_compute_outcome_stats_sell_bias_aligned_when_negative()
    test_compute_outcome_stats_hands_off_aligned_when_flat()
    test_compute_outcome_stats_empty()
    test_compute_outcome_stats_avg_by_alignment()
    print("\n🎉 All direction_backtest tests passed!")
