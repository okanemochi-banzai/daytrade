"""
バックテストロジックのユニットテスト（合成データで検証）
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from backtest import (
    compute_daily_returns,
    aggregate_sector_returns,
    align_us_jp_returns,
    compute_correlation,
    compute_hit_rates,
    classify_verdict,
)


def test_compute_daily_returns():
    """日次騰落率の計算"""
    prices = pd.DataFrame(
        {"A": [100, 105, 110, 99]},
        index=pd.date_range("2026-01-01", periods=4),
    )
    returns = compute_daily_returns(prices)
    # 105/100-1 = +5%, 110/105-1 ≈ +4.76%, 99/110-1 = -10%
    assert abs(returns["A"].iloc[0] - 5.0) < 1e-6
    assert abs(returns["A"].iloc[1] - (110 / 105 - 1) * 100) < 1e-6
    assert abs(returns["A"].iloc[2] - (-10.0)) < 1e-6
    print("✅ test_compute_daily_returns")


def test_aggregate_sector_returns():
    """セクター平均の騰落率"""
    returns = pd.DataFrame(
        {"A": [1.0, 2.0, 3.0], "B": [3.0, 2.0, 1.0], "C": [5.0, 5.0, 5.0]}
    )
    avg = aggregate_sector_returns(returns, ["A", "B"])
    assert list(avg) == [2.0, 2.0, 2.0]
    print("✅ test_aggregate_sector_returns")


def test_aggregate_sector_returns_partial_missing():
    """一部ティッカーが無くても利用可能な分で平均"""
    returns = pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0]})
    avg = aggregate_sector_returns(returns, ["A", "B", "Z"])  # Zは存在しない
    assert list(avg) == [2.0, 3.0]
    print("✅ test_aggregate_sector_returns_partial_missing")


def test_align_us_jp_returns():
    """米T日 vs 日T+1日 のアライメント"""
    idx = pd.date_range("2026-01-01", periods=5)
    us = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=idx)
    jp = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0], index=idx)

    paired = align_us_jp_returns(us, jp)
    # T=1/1の米(1.0) と T+1=1/2の日(20.0) がペアリング
    assert paired.iloc[0]["us"] == 1.0
    assert paired.iloc[0]["jp"] == 20.0
    assert paired.iloc[1]["us"] == 2.0
    assert paired.iloc[1]["jp"] == 30.0
    # 最終日のjpはT+1がないので除外される
    assert len(paired) == 4
    print("✅ test_align_us_jp_returns")


def test_compute_correlation_perfect():
    """完全正相関"""
    df = pd.DataFrame({"us": [1, 2, 3, 4, 5], "jp": [2, 4, 6, 8, 10]})
    r, p, n = compute_correlation(df)
    assert abs(r - 1.0) < 1e-6
    assert p < 0.01
    assert n == 5
    print("✅ test_compute_correlation_perfect")


def test_compute_correlation_negative():
    """完全負相関"""
    df = pd.DataFrame({"us": [1, 2, 3, 4, 5], "jp": [10, 8, 6, 4, 2]})
    r, p, n = compute_correlation(df)
    assert abs(r - (-1.0)) < 1e-6
    print("✅ test_compute_correlation_negative")


def test_compute_correlation_small_n():
    """サンプル数が3未満ならNaN"""
    df = pd.DataFrame({"us": [1, 2], "jp": [3, 4]})
    r, p, n = compute_correlation(df)
    assert np.isnan(r)
    assert n == 2
    print("✅ test_compute_correlation_small_n")


def test_compute_hit_rates_up():
    """米+1%以上の日、翌日日本も+0%以上の確率"""
    # 米+1%以上は3日、そのうち日本+以上は2日 → 2/3
    df = pd.DataFrame(
        {
            "us": [1.5, 2.0, 0.5, 1.2, -0.5, -2.0, 3.0, 0.1],
            "jp": [0.5, -0.2, 0.3, 1.0, 0.8, -1.5, 0.1, 0.2],
        }
    )
    # 米+1%以上: rows 0,1,3,6 (us=1.5,2.0,1.2,3.0) = 4日
    # それらのjp: 0.5, -0.2, 1.0, 0.1 → +0%以上は3日
    hit_up, n_up, hit_down, n_down = compute_hit_rates(df)
    assert n_up == 4
    assert abs(hit_up - 0.75) < 1e-6
    # 米-1%以下: rows 5 (us=-2.0) = 1日
    # jpが-0%以下: -1.5 → 1日
    assert n_down == 1
    assert abs(hit_down - 1.0) < 1e-6
    print("✅ test_compute_hit_rates_up")


def test_compute_hit_rates_no_qualifying_days():
    """閾値超えの日がない場合は None"""
    df = pd.DataFrame({"us": [0.1, 0.2, 0.3], "jp": [0.1, 0.2, 0.3]})
    hit_up, n_up, hit_down, n_down = compute_hit_rates(df)
    assert hit_up is None
    assert hit_down is None
    assert n_up == 0
    assert n_down == 0
    print("✅ test_compute_hit_rates_no_qualifying_days")


def test_classify_verdict_high_confirmed():
    """high期待で強い正相関 → confirmed"""
    v, _ = classify_verdict(r=0.5, p=0.01, n=100, expected="high")
    assert v == "confirmed"
    print("✅ test_classify_verdict_high_confirmed")


def test_classify_verdict_high_weak():
    """high期待だが実測は中程度 → weak"""
    v, _ = classify_verdict(r=0.25, p=0.01, n=100, expected="high")
    assert v == "weak"
    print("✅ test_classify_verdict_high_weak")


def test_classify_verdict_negative_correlation():
    """負の相関ならいつでも contradicted"""
    v, _ = classify_verdict(r=-0.5, p=0.01, n=100, expected="high")
    assert v == "contradicted"
    print("✅ test_classify_verdict_negative_correlation")


def test_classify_verdict_insufficient_data():
    """サンプル数20未満 → insufficient_data"""
    v, _ = classify_verdict(r=0.5, p=0.01, n=10, expected="high")
    assert v == "insufficient_data"
    print("✅ test_classify_verdict_insufficient_data")


def test_classify_verdict_low_actually_high():
    """low期待だが実測は強い相関 → confirmed（想定より良い）"""
    v, _ = classify_verdict(r=0.35, p=0.01, n=100, expected="low")
    assert v == "confirmed"
    print("✅ test_classify_verdict_low_actually_high")


if __name__ == "__main__":
    test_compute_daily_returns()
    test_aggregate_sector_returns()
    test_aggregate_sector_returns_partial_missing()
    test_align_us_jp_returns()
    test_compute_correlation_perfect()
    test_compute_correlation_negative()
    test_compute_correlation_small_n()
    test_compute_hit_rates_up()
    test_compute_hit_rates_no_qualifying_days()
    test_classify_verdict_high_confirmed()
    test_classify_verdict_high_weak()
    test_classify_verdict_negative_correlation()
    test_classify_verdict_insufficient_data()
    test_classify_verdict_low_actually_high()
    print("\n🎉 All backtest tests passed!")
