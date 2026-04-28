"""
stock_picks のユニットテスト
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stock_picks import build_stock_picks


def _make_sector(
    name="半導体",
    direction="bearish",
    strength="strong",
    validation="confirmed",
    avg_pct=-2.5,
    stocks=("東京エレクトロン", "アドバンテスト"),
    tickers=("8035.T", "6857.T"),
):
    return {
        "sector_name": name,
        "direction": direction,
        "signal_strength": strength,
        "validation_verdict": validation,
        "us_avg_change_pct": avg_pct,
        "us_label": "SOX指数",
        "jp_stocks": list(stocks),
        "jp_tickers": list(tickers),
    }


def test_buy_bias_returns_unavailable():
    """指数判定が出ている日は本機能は表示しない"""
    result = build_stock_picks("buy_bias", [_make_sector()])
    assert result.available is False
    assert len(result.picks) == 0
    print("✅ test_buy_bias_returns_unavailable")


def test_sell_bias_returns_unavailable():
    result = build_stock_picks("sell_bias", [_make_sector()])
    assert result.available is False
    print("✅ test_sell_bias_returns_unavailable")


def test_hands_off_with_confirmed_strong_sector():
    """hands_off + strong + confirmed → ピックアップ"""
    sectors = [_make_sector()]
    result = build_stock_picks("hands_off", sectors)
    assert result.available is True
    assert len(result.picks) == 1
    p = result.picks[0]
    assert p.sector_name == "半導体"
    assert p.direction == "bearish"
    assert p.direction_label == "売り（空売り）候補"
    print("✅ test_hands_off_with_confirmed_strong_sector")


def test_hands_off_filters_weak_sector():
    """弱シグナルのセクターは除外"""
    sectors = [_make_sector(strength="weak")]
    result = build_stock_picks("hands_off", sectors)
    assert result.available is True
    assert len(result.picks) == 0
    print("✅ test_hands_off_filters_weak_sector")


def test_hands_off_filters_unverified_sector():
    """バックテスト未検証 / 弱連動 / 連動なし のセクターは除外"""
    sectors = [
        _make_sector(name="A", validation=None),
        _make_sector(name="B", validation="weak"),
        _make_sector(name="C", validation="contradicted"),
        _make_sector(name="D", validation="insufficient_data"),
    ]
    result = build_stock_picks("hands_off", sectors)
    assert result.available is True
    assert len(result.picks) == 0
    print("✅ test_hands_off_filters_unverified_sector")


def test_hands_off_no_neutral_direction():
    """中立方向のセクターは除外"""
    sectors = [_make_sector(direction="neutral", avg_pct=0.1)]
    result = build_stock_picks("hands_off", sectors)
    assert len(result.picks) == 0
    print("✅ test_hands_off_no_neutral_direction")


def test_hands_off_bullish_picks():
    """買いセクターは「買い候補」表示"""
    sectors = [_make_sector(direction="bullish", avg_pct=2.5)]
    result = build_stock_picks("hands_off", sectors)
    assert result.picks[0].direction_label == "買い候補"
    assert "買い目線" in result.picks[0].rationale
    print("✅ test_hands_off_bullish_picks")


def test_hands_off_multiple_sectors():
    """複数セクターが該当する場合は全部ピック"""
    sectors = [
        _make_sector(name="半導体", direction="bearish"),
        _make_sector(name="エネルギー", direction="bullish", avg_pct=2.0),
        _make_sector(name="軍需", strength="weak"),       # 弱→除外
        _make_sector(name="海運", validation="contradicted"),  # 連動なし→除外
    ]
    result = build_stock_picks("hands_off", sectors)
    assert len(result.picks) == 2
    names = [p.sector_name for p in result.picks]
    assert "半導体" in names
    assert "エネルギー" in names
    print("✅ test_hands_off_multiple_sectors")


def test_hands_off_no_qualifying_sectors():
    """hands_off だが該当セクターなし → available=True、picks=[]、休む日メッセージ"""
    sectors = [_make_sector(strength="weak")]
    result = build_stock_picks("hands_off", sectors)
    assert result.available is True
    assert len(result.picks) == 0
    assert "休む日" in result.reason
    print("✅ test_hands_off_no_qualifying_sectors")


def test_picks_limit_4_stocks():
    """5銘柄以上のセクターでも4銘柄までに制限"""
    sectors = [_make_sector(
        stocks=("A", "B", "C", "D", "E", "F"),
        tickers=("1.T", "2.T", "3.T", "4.T", "5.T", "6.T"),
    )]
    result = build_stock_picks("hands_off", sectors)
    assert len(result.picks[0].stocks) == 4
    assert len(result.picks[0].tickers) == 4
    print("✅ test_picks_limit_4_stocks")


if __name__ == "__main__":
    test_buy_bias_returns_unavailable()
    test_sell_bias_returns_unavailable()
    test_hands_off_with_confirmed_strong_sector()
    test_hands_off_filters_weak_sector()
    test_hands_off_filters_unverified_sector()
    test_hands_off_no_neutral_direction()
    test_hands_off_bullish_picks()
    test_hands_off_multiple_sectors()
    test_hands_off_no_qualifying_sectors()
    test_picks_limit_4_stocks()
    print("\n🎉 All stock_picks tests passed!")
