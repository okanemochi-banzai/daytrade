"""
セクター連動ロジックのユニットテスト
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sector_mapping import (
    classify_direction,
    build_sector_signal,
    build_all_sector_signals,
    get_all_us_tickers,
    SECTOR_PAIRS,
)


def test_classify_direction_strong_bullish():
    d, s = classify_direction(2.0)
    assert d == "bullish"
    assert s == "strong"
    print("✅ test_classify_direction_strong_bullish")


def test_classify_direction_strong_bearish():
    d, s = classify_direction(-2.5)
    assert d == "bearish"
    assert s == "strong"
    print("✅ test_classify_direction_strong_bearish")


def test_classify_direction_weak():
    d, s = classify_direction(0.8)
    assert d == "bullish"
    assert s == "weak"
    print("✅ test_classify_direction_weak")


def test_classify_direction_neutral():
    d, s = classify_direction(0.3)
    assert d == "neutral"
    assert s == "neutral"
    d2, s2 = classify_direction(-0.2)
    assert d2 == "neutral"
    assert s2 == "neutral"
    print("✅ test_classify_direction_neutral")


def test_build_sector_signal_semiconductor_bearish():
    """半導体が全面下げのシナリオ（-3%前後）"""
    semi_pair = next(p for p in SECTOR_PAIRS if p.name == "半導体")
    us_changes = {"AMAT": -3.0, "LRCX": -2.8, "KLAC": -3.2, "AMD": -3.5, "NVDA": -2.5}
    sig = build_sector_signal(semi_pair, us_changes)
    assert sig.direction == "bearish"
    assert sig.signal_strength == "strong"
    assert sig.us_avg_change_pct < -2.5
    assert "東京エレクトロン" in sig.jp_stocks
    print("✅ test_build_sector_signal_semiconductor_bearish")


def test_build_sector_signal_energy_bullish():
    """エネルギーが上げるシナリオ"""
    energy_pair = next(p for p in SECTOR_PAIRS if p.name == "エネルギー（原油）")
    us_changes = {"XOM": 2.0, "CVX": 1.8, "COP": 2.5}
    sig = build_sector_signal(energy_pair, us_changes)
    assert sig.direction == "bullish"
    assert sig.signal_strength == "strong"
    assert "INPEX" in sig.jp_stocks
    print("✅ test_build_sector_signal_energy_bullish")


def test_build_sector_signal_missing_ticker_data():
    """一部ティッカーのデータが欠けても、取れる分だけで計算する"""
    semi_pair = next(p for p in SECTOR_PAIRS if p.name == "半導体")
    us_changes = {"AMD": -2.0, "NVDA": -3.0}  # 3銘柄分は欠損
    sig = build_sector_signal(semi_pair, us_changes)
    assert sig.us_avg_change_pct == -2.5
    assert sig.direction == "bearish"
    print("✅ test_build_sector_signal_missing_ticker_data")


def test_build_sector_signal_no_data():
    """全ティッカーのデータが欠損した場合は0%扱い→ニュートラル"""
    semi_pair = next(p for p in SECTOR_PAIRS if p.name == "半導体")
    sig = build_sector_signal(semi_pair, us_changes={})
    assert sig.us_avg_change_pct == 0.0
    assert sig.direction == "neutral"
    print("✅ test_build_sector_signal_no_data")


def test_build_all_sector_signals_sorted():
    """強い順（strong → weak → neutral、絶対値降順）に並ぶ"""
    us_changes = {
        # 半導体: 強い下げ
        "AMAT": -3.0, "LRCX": -3.0, "KLAC": -3.0, "AMD": -3.0, "NVDA": -3.0,
        # エネルギー: 強い上げ（-3%より絶対値は小さい）
        "XOM": 2.0, "CVX": 2.0, "COP": 2.0,
        # 軍需: 弱い上げ
        "LMT": 0.8, "RTX": 0.8, "BA": 0.8, "HON": 0.8, "NOC": 0.8,
    }
    sigs = build_all_sector_signals(us_changes)
    # 半導体が先頭、次にエネルギー（どちらもstrong、絶対値大きい順）
    assert sigs[0].sector_name == "半導体"
    assert sigs[1].sector_name == "エネルギー（原油）"
    # 軍需はweakなのでstrongの後
    semi_idx = next(i for i, s in enumerate(sigs) if s.sector_name == "半導体")
    armament_idx = next(i for i, s in enumerate(sigs) if s.sector_name == "軍需・防衛")
    assert semi_idx < armament_idx
    print("✅ test_build_all_sector_signals_sorted")


def test_get_all_us_tickers_unique():
    """重複なくティッカーが取れる"""
    tickers = get_all_us_tickers()
    assert len(tickers) == len(set(tickers))
    # 半導体の代表銘柄が含まれている
    assert "NVDA" in tickers
    assert "XOM" in tickers
    assert "LMT" in tickers
    print("✅ test_get_all_us_tickers_unique")


if __name__ == "__main__":
    test_classify_direction_strong_bullish()
    test_classify_direction_strong_bearish()
    test_classify_direction_weak()
    test_classify_direction_neutral()
    test_build_sector_signal_semiconductor_bearish()
    test_build_sector_signal_energy_bullish()
    test_build_sector_signal_missing_ticker_data()
    test_build_sector_signal_no_data()
    test_build_all_sector_signals_sorted()
    test_get_all_us_tickers_unique()
    print("\n🎉 All sector tests passed!")
