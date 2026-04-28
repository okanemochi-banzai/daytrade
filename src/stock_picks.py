"""
「初心者手出し無用」日の個別銘柄候補ピックアップ

指数全体の方向性は読めないが、セクター単位では強い連動が出ている場合に
そのセクターの該当銘柄を「注目銘柄」として提示する。

安全条件:
  1. 指数判定が hands_off の日のみ表示
  2. セクターが strong シグナル (±1.5%以上)
  3. バックテストで confirmed のセクターのみ
  4. 「推奨」ではなく「注目」「該当」の表現
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal


Direction = Literal["bullish", "bearish"]


@dataclass
class StockPick:
    """注目銘柄の候補1件"""
    sector_name: str
    direction: Direction
    direction_label: str           # "買い候補" / "売り（空売り）候補"
    rationale: str                  # 「米半導体が-2.96%、検証済み連動強」など
    stocks: list[str]               # 銘柄名リスト
    tickers: list[str]              # 銘柄コードリスト（表示用）

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class StockPicksResult:
    available: bool                 # 表示すべきかどうか
    reason: str                     # 表示しない場合の理由
    picks: list[StockPick]          # 注目銘柄候補（空の可能性あり）

    def as_dict(self) -> dict:
        return {
            "available": self.available,
            "reason": self.reason,
            "picks": [p.as_dict() for p in self.picks],
        }


def build_stock_picks(
    direction_verdict: str,
    sector_signals: list[dict],
) -> StockPicksResult:
    """指数判定が hands_off の日に、強シグナル × 検証済みセクターから銘柄候補を抽出。

    Args:
        direction_verdict: "buy_bias" / "sell_bias" / "hands_off"
        sector_signals: 各セクターのシグナル辞書のリスト
                       各要素は signal_strength, direction, validation_verdict 等を持つ
    """
    # hands_off 以外なら表示しない（指数判定が出ているので、そちらに従えばよい）
    if direction_verdict != "hands_off":
        return StockPicksResult(
            available=False,
            reason="指数判定が出ているため、本機能は表示しません",
            picks=[],
        )

    picks: list[StockPick] = []

    for s in sector_signals:
        # 条件1: strongシグナルのみ（弱シグナルや中立は除外）
        if s.get("signal_strength") != "strong":
            continue

        # 条件2: バックテストで confirmed のみ（未検証 or 弱連動 or 連動なしは除外）
        if s.get("validation_verdict") != "confirmed":
            continue

        # 条件3: bullish/bearish のみ
        direction = s.get("direction")
        if direction not in ("bullish", "bearish"):
            continue

        avg_pct = s.get("us_avg_change_pct", 0.0)
        sector_name = s.get("sector_name", "")
        us_label = s.get("us_label", "")
        stocks = s.get("jp_stocks", [])
        tickers = s.get("jp_tickers", [])

        if direction == "bullish":
            direction_label = "買い候補"
            rationale = (
                f"米{us_label}が平均+{avg_pct:.2f}%。バックテストで連動が確認されたセクター。"
                f"指数全体は方向性不明でも、このセクターは買い目線で考えやすい。"
            )
        else:
            direction_label = "売り（空売り）候補"
            rationale = (
                f"米{us_label}が平均{avg_pct:.2f}%。バックテストで連動が確認されたセクター。"
                f"指数全体は方向性不明でも、このセクターは売り目線で考えやすい。"
            )

        picks.append(
            StockPick(
                sector_name=sector_name,
                direction=direction,
                direction_label=direction_label,
                rationale=rationale,
                stocks=list(stocks)[:4],     # 上位4銘柄まで
                tickers=list(tickers)[:4],
            )
        )

    if not picks:
        return StockPicksResult(
            available=True,
            reason="該当セクターなし。今日は指数もセクターも方向感がないので休む日。",
            picks=[],
        )

    return StockPicksResult(
        available=True,
        reason=f"{len(picks)}セクターで強い連動シグナル",
        picks=picks,
    )
