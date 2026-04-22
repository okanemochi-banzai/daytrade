"""
ゴールド/ドル円/原油 の補助情報モジュール

PDFから抽出した解釈パターン:
  ドル円↑（円安）→ 日本株（特に輸出）追い風
  ドル円↓（円高）→ 輸出弱、銀行株強（金利上昇期待）
  ゴールド↑     → インフレ/リスクオフ懸念
  原油↑        → エネルギー株強（INPEX等）、他はリスクオフ
  ゴールド+原油 両方↑ → ハイパーインフレ警戒

判定には使わず「参考情報」として表示する。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal


Direction = Literal["up", "down", "flat"]


# しきい値（%）
STRONG_MOVE = 1.0     # ±1%以上で明確な方向性
WEAK_MOVE = 0.3       # ±0.3%未満はフラット扱い


@dataclass
class ContextItem:
    name: str
    symbol: str                          # "USD/JPY" 等の表示用
    current: float                        # 現在値
    change_pct: float                     # 前日比(%)
    direction: Direction
    interpretation: str                   # 解釈（1行）

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class MarketContext:
    items: list[ContextItem]
    combined_note: str | None             # 複合シグナル（ハイパーインフレ警戒等）

    def as_dict(self) -> dict:
        return {
            "items": [i.as_dict() for i in self.items],
            "combined_note": self.combined_note,
        }


def _classify(change_pct: float) -> Direction:
    if change_pct >= WEAK_MOVE:
        return "up"
    if change_pct <= -WEAK_MOVE:
        return "down"
    return "flat"


def interpret_usdjpy(change_pct: float) -> str:
    d = _classify(change_pct)
    if d == "up":
        if change_pct >= STRONG_MOVE:
            return "円安進行 → 輸出株追い風、日本株全体にプラス寄与"
        return "円安傾向 → 輸出株にやや追い風"
    if d == "down":
        if change_pct <= -STRONG_MOVE:
            return "円高進行 → 輸出株に逆風、銀行株には追い風（金利上昇期待）"
        return "円高傾向 → 輸出株にやや逆風"
    return "変動なし"


def interpret_gold(change_pct: float) -> str:
    d = _classify(change_pct)
    if d == "up":
        if change_pct >= STRONG_MOVE:
            return "ゴールド上昇 → インフレ懸念 or リスクオフ。住友金属鉱山等の金鉱株に追い風"
        return "ゴールド小幅上昇"
    if d == "down":
        if change_pct <= -STRONG_MOVE:
            return "ゴールド下落 → リスクオン転換の可能性"
        return "ゴールド小幅下落"
    return "変動なし"


def interpret_oil(change_pct: float) -> str:
    d = _classify(change_pct)
    if d == "up":
        if change_pct >= STRONG_MOVE * 2:  # 原油はボラ大きいので2倍にスケール
            return "原油急騰 → リスクオフ懸念。エネルギー株（INPEX・ENEOS等）に追い風、他はリスクオフ警戒"
        if change_pct >= STRONG_MOVE:
            return "原油上昇 → エネルギー株に追い風"
        return "原油小幅上昇"
    if d == "down":
        if change_pct <= -STRONG_MOVE * 2:
            return "原油急落 → リスクオン転換の可能性、エネルギー株は逆風"
        if change_pct <= -STRONG_MOVE:
            return "原油下落 → エネルギー株に逆風"
        return "原油小幅下落"
    return "変動なし"


def _check_combined_signals(
    usdjpy_change: float,
    gold_change: float,
    oil_change: float,
) -> str | None:
    """複合的なマクロシグナルを検出"""
    strong_gold_up = gold_change >= STRONG_MOVE
    strong_oil_up = oil_change >= STRONG_MOVE

    # PDF: 「貴金属に次いで原油まであがったらハイパーインフレを疑うべし」
    if strong_gold_up and strong_oil_up:
        return "⚠️ ゴールド & 原油の同時上昇 → ハイパーインフレ/重度リスクオフの兆候。株全体に警戒。"

    # リスクオフの典型: ゴールド↑ + ドル円↓
    if gold_change >= STRONG_MOVE and usdjpy_change <= -STRONG_MOVE:
        return "⚠️ ゴールド↑ × 円高 → 典型的なリスクオフ。輸出株は警戒。"

    # リスクオン転換
    if gold_change <= -STRONG_MOVE and oil_change <= -STRONG_MOVE:
        return "✅ ゴールド & 原油の同時下落 → リスクオン転換の可能性。"

    return None


def build_market_context(
    usdjpy_price: float,
    usdjpy_change_pct: float,
    gold_price: float,
    gold_change_pct: float,
    oil_price: float,
    oil_change_pct: float,
) -> MarketContext:
    """為替・コモディティの補助情報を組み立てる"""
    items = [
        ContextItem(
            name="ドル円",
            symbol="USD/JPY",
            current=usdjpy_price,
            change_pct=usdjpy_change_pct,
            direction=_classify(usdjpy_change_pct),
            interpretation=interpret_usdjpy(usdjpy_change_pct),
        ),
        ContextItem(
            name="ゴールド",
            symbol="XAU/USD",
            current=gold_price,
            change_pct=gold_change_pct,
            direction=_classify(gold_change_pct),
            interpretation=interpret_gold(gold_change_pct),
        ),
        ContextItem(
            name="WTI原油",
            symbol="CL",
            current=oil_price,
            change_pct=oil_change_pct,
            direction=_classify(oil_change_pct),
            interpretation=interpret_oil(oil_change_pct),
        ),
    ]

    combined_note = _check_combined_signals(usdjpy_change_pct, gold_change_pct, oil_change_pct)

    return MarketContext(items=items, combined_note=combined_note)
