"""
米→日セクター連動マッピング

PDFから抽出したセクター連動パターンに基づき、
前日米国市場の騰落率から翌朝の日本株セクター方向を予測する。

注意:
  これは「連動傾向がある」という過去の経験則であり、統計的有意性は未検証。
  実運用前に必ずバックテストで勝率を確認すること。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal


Direction = Literal["bullish", "bearish", "neutral"]


# セクター連動強度のしきい値（%）
STRONG_MOVE_THRESHOLD = 1.5   # ±1.5%以上 → 強いシグナル
WEAK_MOVE_THRESHOLD = 0.5     # ±0.5%以上 → 弱いシグナル
# それ未満 → ニュートラル


@dataclass(frozen=True)
class SectorPair:
    """米セクターと対応する日本株セクターのペア"""
    name: str                          # セクター名（日本語）
    us_tickers: tuple[str, ...]        # 米代表銘柄ティッカー
    us_label: str                      # 米側の表示名
    jp_stocks: tuple[str, ...]         # 日本側の対応銘柄名（表示用）
    jp_tickers: tuple[str, ...]        # 日本側ティッカー（.T付き、後日データ取得用）
    correlation_strength: Literal["high", "medium", "low"]  # 経験則上の連動の強さ
    note: str                          # メモ


# PDFから抽出したマッピング定義
SECTOR_PAIRS: list[SectorPair] = [
    SectorPair(
        name="半導体",
        us_tickers=("AMAT", "LRCX", "KLAC", "AMD", "NVDA"),
        us_label="SOX指数（半導体）",
        jp_stocks=("東京エレクトロン", "アドバンテスト", "ディスコ", "レーザーテック"),
        jp_tickers=("8035.T", "6857.T", "6146.T", "6920.T"),
        correlation_strength="high",
        note="SOX指数との連動が最も強いグループ（半導体カルテット）",
    ),
    SectorPair(
        name="ストレージ半導体",
        us_tickers=("SNDK", "WDC", "STX"),
        us_label="サンディスク等ストレージ",
        jp_stocks=("キオクシア",),
        jp_tickers=("285A.T",),
        correlation_strength="high",
        note="キオクシアはサンディスクの動きに強く連動。半導体カルテットとは別扱いが鉄則",
    ),
    SectorPair(
        name="建機",
        us_tickers=("CAT", "DE"),
        us_label="キャタピラー・ディアー",
        jp_stocks=("コマツ", "日立建機", "クボタ"),
        jp_tickers=("6301.T", "6305.T", "6326.T"),
        correlation_strength="high",
        note="CAT・DEの動きから翌朝のコマツ方向が読みやすい",
    ),
    SectorPair(
        name="エネルギー（原油）",
        us_tickers=("XOM", "CVX", "COP"),
        us_label="エクソン・シェブロン等",
        jp_stocks=("INPEX", "ENEOS", "出光興産", "コスモエネルギー"),
        jp_tickers=("1605.T", "5020.T", "5019.T", "5021.T"),
        correlation_strength="high",
        note="原油先物・XOM・CVXが上げればINPEX等は高確率で連動",
    ),
    SectorPair(
        name="軍需・防衛",
        us_tickers=("LMT", "RTX", "BA", "HON", "NOC"),
        us_label="ロッキード・RTX等",
        jp_stocks=("三菱重工業", "IHI", "川崎重工業"),
        jp_tickers=("7011.T", "7013.T", "7012.T"),
        correlation_strength="high",
        note="地政学リスク連動。戦争懸念時の強い順張りセクター",
    ),
    SectorPair(
        name="通信（配当ディフェンシブ）",
        us_tickers=("VZ", "T", "TMUS"),
        us_label="ベライゾン・AT&T",
        jp_stocks=("KDDI", "NTT", "ソフトバンク"),
        jp_tickers=("9433.T", "9432.T", "9434.T"),
        correlation_strength="medium",
        note="ディフェンシブ資金フロー時に連動。日本特有の材料（粉飾等）には非連動",
    ),
    SectorPair(
        name="SaaS・ソフトウェア",
        us_tickers=("CRM", "MSFT", "ORCL", "ADBE", "INTU", "NOW"),
        us_label="セールスフォース・MSFT等",
        jp_stocks=("富士通", "NEC", "NRI", "オービック", "マネーフォワード"),
        jp_tickers=("6702.T", "6701.T", "4307.T", "4684.T", "3994.T"),
        correlation_strength="medium",
        note="「アメリカ下げ戦犯・ソフトウェアSaaS系」として頻出。下げ時の連動が特に強い",
    ),
    SectorPair(
        name="電線（CAT連動系）",
        us_tickers=("CAT", "DE"),
        us_label="キャタピラー・ディアー",
        jp_stocks=("フジクラ", "住友電工", "古河電工"),
        jp_tickers=("5803.T", "5802.T", "5801.T"),
        correlation_strength="medium",
        note="インフラ投資テーマでCAT・DEと一緒に動く傾向。PDFでは「電線3種」としてコマツとセットで語られる",
    ),
    SectorPair(
        name="海運・物流",
        us_tickers=("UPS", "FDX"),
        us_label="UPS・FedEx",
        jp_stocks=("日本郵船", "商船三井", "川崎汽船"),
        jp_tickers=("9101.T", "9104.T", "9107.T"),
        correlation_strength="low",
        note="連動は弱め。海運は日本独自の材料（海峡・BDI）の影響が大きい",
    ),
    SectorPair(
        name="生活防衛（配当王）",
        us_tickers=("KO", "PG", "CL", "MCD"),
        us_label="コカコーラ・P&G等",
        jp_stocks=("花王", "味の素", "明治HD", "キッコーマン"),
        jp_tickers=("4452.T", "2802.T", "2269.T", "2801.T"),
        correlation_strength="low",
        note="連動は弱い。配当ディフェンシブ資金フロー時のみ同方向",
    ),
]


@dataclass
class SectorSignal:
    """1セクター分の連動シグナル"""
    sector_name: str
    us_label: str
    us_avg_change_pct: float       # 米代表銘柄の平均騰落率
    direction: Direction
    signal_strength: Literal["strong", "weak", "neutral"]
    jp_stocks: list[str]
    correlation_strength: str
    note: str
    rationale: str

    def as_dict(self) -> dict:
        return asdict(self)


def classify_direction(avg_change_pct: float) -> tuple[Direction, Literal["strong", "weak", "neutral"]]:
    """米セクター平均騰落率から日本株の方向とシグナル強度を判定"""
    abs_chg = abs(avg_change_pct)
    if abs_chg < WEAK_MOVE_THRESHOLD:
        return "neutral", "neutral"

    direction: Direction = "bullish" if avg_change_pct > 0 else "bearish"
    strength = "strong" if abs_chg >= STRONG_MOVE_THRESHOLD else "weak"
    return direction, strength


def build_sector_signal(pair: SectorPair, us_changes: dict[str, float]) -> SectorSignal:
    """1セクター分のシグナルを組み立てる。

    Args:
        pair: セクター定義
        us_changes: 米ティッカー → 騰落率(%) のマッピング
    """
    # 存在する米ティッカーのみで平均を取る
    available = [us_changes[t] for t in pair.us_tickers if t in us_changes]
    if not available:
        avg = 0.0
    else:
        avg = sum(available) / len(available)

    direction, strength = classify_direction(avg)

    # 文言生成
    jp_list = "・".join(pair.jp_stocks[:3])
    if direction == "bullish":
        action = "買い目線" if strength == "strong" else "やや買い寄り"
        rationale = (
            f"米{pair.us_label}が平均+{avg:.2f}%。{jp_list}等は{action}で想定。"
        )
    elif direction == "bearish":
        action = "売り目線" if strength == "strong" else "やや売り寄り"
        rationale = (
            f"米{pair.us_label}が平均{avg:.2f}%。{jp_list}等は{action}で想定。"
        )
    else:
        rationale = (
            f"米{pair.us_label}が平均{avg:+.2f}%。方向感なし、様子見。"
        )

    return SectorSignal(
        sector_name=pair.name,
        us_label=pair.us_label,
        us_avg_change_pct=avg,
        direction=direction,
        signal_strength=strength,
        jp_stocks=list(pair.jp_stocks),
        correlation_strength=pair.correlation_strength,
        note=pair.note,
        rationale=rationale,
    )


def build_all_sector_signals(us_changes: dict[str, float]) -> list[SectorSignal]:
    """全セクターのシグナルを一括生成。強度（強→弱→中立）順にソート。"""
    signals = [build_sector_signal(p, us_changes) for p in SECTOR_PAIRS]

    # ソート順: signal_strength(strong→weak→neutral) × 騰落率絶対値
    strength_order = {"strong": 0, "weak": 1, "neutral": 2}
    signals.sort(
        key=lambda s: (strength_order[s.signal_strength], -abs(s.us_avg_change_pct))
    )
    return signals


def get_all_us_tickers() -> list[str]:
    """全セクターで必要な米ティッカーの重複排除リスト。データ取得で使う。"""
    tickers: set[str] = set()
    for pair in SECTOR_PAIRS:
        tickers.update(pair.us_tickers)
    return sorted(tickers)
