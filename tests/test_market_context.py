"""
market_context のユニットテスト
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from market_context import (
    _classify,
    interpret_usdjpy,
    interpret_gold,
    interpret_oil,
    build_market_context,
)


def test_classify():
    assert _classify(2.0) == "up"
    assert _classify(-2.0) == "down"
    assert _classify(0.1) == "flat"
    assert _classify(-0.1) == "flat"
    assert _classify(0.3) == "up"
    assert _classify(-0.3) == "down"
    print("✅ test_classify")


def test_interpret_usdjpy_yen_weak():
    msg = interpret_usdjpy(1.2)
    assert "円安" in msg
    assert "追い風" in msg
    print("✅ test_interpret_usdjpy_yen_weak")


def test_interpret_usdjpy_yen_strong():
    msg = interpret_usdjpy(-1.5)
    assert "円高" in msg
    assert "銀行" in msg or "金利" in msg
    print("✅ test_interpret_usdjpy_yen_strong")


def test_interpret_usdjpy_flat():
    msg = interpret_usdjpy(0.05)
    assert msg == "変動なし"
    print("✅ test_interpret_usdjpy_flat")


def test_interpret_gold_up():
    msg = interpret_gold(1.5)
    assert "インフレ" in msg or "リスクオフ" in msg
    print("✅ test_interpret_gold_up")


def test_interpret_oil_sharp_up():
    msg = interpret_oil(2.5)
    assert "急騰" in msg or "リスクオフ" in msg
    print("✅ test_interpret_oil_sharp_up")


def test_build_market_context_normal():
    ctx = build_market_context(
        usdjpy_price=150.2,
        usdjpy_change_pct=0.3,
        gold_price=2650,
        gold_change_pct=0.1,
        oil_price=72.5,
        oil_change_pct=-0.5,
    )
    assert len(ctx.items) == 3
    assert ctx.items[0].name == "ドル円"
    assert ctx.items[1].name == "ゴールド"
    assert ctx.items[2].name == "WTI原油"
    assert ctx.combined_note is None   # 特に警戒シグナルなし
    print("✅ test_build_market_context_normal")


def test_build_market_context_hyperinflation():
    """ゴールド & 原油両方大きく上げ → ハイパーインフレ警戒"""
    ctx = build_market_context(
        usdjpy_price=160,
        usdjpy_change_pct=0.2,
        gold_price=2800,
        gold_change_pct=2.0,
        oil_price=90,
        oil_change_pct=3.5,
    )
    assert ctx.combined_note is not None
    assert "ハイパーインフレ" in ctx.combined_note
    print("✅ test_build_market_context_hyperinflation")


def test_build_market_context_risk_off():
    """ゴールド↑ + 円高 → リスクオフ警戒"""
    ctx = build_market_context(
        usdjpy_price=145,
        usdjpy_change_pct=-1.2,
        gold_price=2700,
        gold_change_pct=1.5,
        oil_price=70,
        oil_change_pct=-0.3,
    )
    assert ctx.combined_note is not None
    assert "リスクオフ" in ctx.combined_note
    print("✅ test_build_market_context_risk_off")


def test_build_market_context_risk_on():
    """ゴールド↓ + 原油↓ → リスクオン"""
    ctx = build_market_context(
        usdjpy_price=150,
        usdjpy_change_pct=0.3,
        gold_price=2500,
        gold_change_pct=-1.5,
        oil_price=65,
        oil_change_pct=-2.0,
    )
    assert ctx.combined_note is not None
    assert "リスクオン" in ctx.combined_note
    print("✅ test_build_market_context_risk_on")


if __name__ == "__main__":
    test_classify()
    test_interpret_usdjpy_yen_weak()
    test_interpret_usdjpy_yen_strong()
    test_interpret_usdjpy_flat()
    test_interpret_gold_up()
    test_interpret_oil_sharp_up()
    test_build_market_context_normal()
    test_build_market_context_hyperinflation()
    test_build_market_context_risk_off()
    test_build_market_context_risk_on()
    print("\n🎉 All market_context tests passed!")
