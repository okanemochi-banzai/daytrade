"""
手仕舞い警告判定モジュール

PDFから抽出した警告パターン:
  - 金曜の週足手仕舞い: 日経週足が陽線なら後場の手仕舞い売り警戒
                       日経週足が陰線ならショートカバー買い警戒
  - 月末の月足手仕舞い: 日経月足が陽線なら手仕舞い売り警戒（金曜より重い）
  - 3連休前: 祝日前営業日は手仕舞いが入りやすい
  - 月初: 「月初めという節目での下げ → 月全体に波及する恐れ」
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Literal


Severity = Literal["high", "medium", "low"]


@dataclass
class TradingWarning:
    """1つの警告"""
    type: str                     # "friday_closing" / "month_end" / "pre_holiday" / "month_start"
    severity: Severity
    label: str                    # 見出し
    message: str                  # 本文
    action: str                   # 推奨アクション

    def as_dict(self) -> dict:
        return asdict(self)


# ========== 日本の祝日判定 ==========

def _days_from_second_monday(d: date) -> int:
    """その月の第2月曜日からの日数（負値=まだ来ていない）"""
    first = date(d.year, d.month, 1)
    # 第2月曜 = 最初の月曜 + 7日
    first_monday_offset = (0 - first.weekday()) % 7
    second_monday = first + timedelta(days=first_monday_offset + 7)
    return (d - second_monday).days


def _days_from_third_monday(d: date) -> int:
    first = date(d.year, d.month, 1)
    first_monday_offset = (0 - first.weekday()) % 7
    third_monday = first + timedelta(days=first_monday_offset + 14)
    return (d - third_monday).days


def is_japanese_holiday(d: date) -> bool:
    """日本の主要祝日を判定（完璧ではないが実用十分）。

    振替休日・国民の休日は簡略化のため省略。
    正確性が必要なら jpholiday ライブラリを requirements に追加することも可能。
    """
    y, m, day = d.year, d.month, d.day

    # 固定祝日
    fixed_holidays = {
        (1, 1),    # 元日
        (2, 11),   # 建国記念の日
        (2, 23),   # 天皇誕生日
        (4, 29),   # 昭和の日
        (5, 3),    # 憲法記念日
        (5, 4),    # みどりの日
        (5, 5),    # こどもの日
        (8, 11),   # 山の日
        (11, 3),   # 文化の日
        (11, 23),  # 勤労感謝の日
    }
    if (m, day) in fixed_holidays:
        return True

    # ハッピーマンデー系
    if m == 1 and _days_from_second_monday(d) == 0:
        return True  # 成人の日
    if m == 7 and _days_from_third_monday(d) == 0:
        return True  # 海の日
    if m == 9 and _days_from_third_monday(d) == 0:
        return True  # 敬老の日
    if m == 10 and _days_from_second_monday(d) == 0:
        return True  # スポーツの日

    # 春分の日・秋分の日（近似: 3/20-21、9/22-23）
    if m == 3 and day in (20, 21):
        return True
    if m == 9 and day in (22, 23):
        return True

    return False


def is_trading_day(d: date) -> bool:
    """東証の営業日か（週末・祝日・年末年始以外）"""
    if d.weekday() >= 5:  # 土日
        return False
    if is_japanese_holiday(d):
        return False
    # 年末年始（12/31, 1/1-1/3）
    if d.month == 12 and d.day == 31:
        return False
    if d.month == 1 and d.day in (1, 2, 3):
        return False
    return True


def next_trading_day(d: date, max_lookahead: int = 10) -> date | None:
    """d の翌営業日"""
    candidate = d + timedelta(days=1)
    for _ in range(max_lookahead):
        if is_trading_day(candidate):
            return candidate
        candidate += timedelta(days=1)
    return None


def is_last_trading_day_of_month(d: date) -> bool:
    """その月の最終営業日か"""
    if not is_trading_day(d):
        return False
    nxt = next_trading_day(d)
    if nxt is None:
        return False
    return nxt.month != d.month


def is_pre_holiday(d: date) -> bool:
    """翌営業日まで2日以上間が空いているか（3連休前など）"""
    if not is_trading_day(d):
        return False
    nxt = next_trading_day(d)
    if nxt is None:
        return False
    return (nxt - d).days >= 3


# ========== 各警告ロジック ==========

def check_friday_warning(
    today: date,
    nikkei_week_is_positive: bool | None,
) -> TradingWarning | None:
    """金曜の週足手仕舞い警告。

    Args:
        today: 今日の日付
        nikkei_week_is_positive: 今週の日経が陽線か（月曜始値より現時点の終値が上か）
                                  None の場合は判定不能
    """
    if today.weekday() != 4:  # 4 = 金曜
        return None

    if nikkei_week_is_positive is None:
        return TradingWarning(
            type="friday_closing",
            severity="medium",
            label="📅 金曜の手仕舞い警戒",
            message="今日は金曜日。後場にロングカバーの手仕舞い動向が入りやすい傾向。",
            action="午後からの持ち越しポジは慎重に。前場上げ→後場下げのパターンにも注意。",
        )

    if nikkei_week_is_positive:
        return TradingWarning(
            type="friday_closing",
            severity="high",
            label="📅 金曜 × 週足陽線 = 手仕舞い売り警戒",
            message="今週の日経は陽線。金曜のロングカバーで後場は売りに振れやすい。",
            action="午前に買いポジを持ってる場合、前場のうちに一部利確を検討。"
                   "デイトレは「前場上げ→後場下げ」のアノマリーを意識。",
        )
    else:
        return TradingWarning(
            type="friday_closing",
            severity="medium",
            label="📅 金曜 × 週足陰線 = ショートカバー買い警戒",
            message="今週の日経は陰線。金曜のショートカバーで後場上げの可能性。",
            action="安易な売りポジ持ち越しに注意。後場の買い戻しに巻き込まれる懸念。",
        )


def check_month_end_warning(
    today: date,
    nikkei_month_is_positive: bool | None,
) -> TradingWarning | None:
    """月末最終営業日の月足手仕舞い警告。"""
    if not is_last_trading_day_of_month(today):
        return None

    if nikkei_month_is_positive is None:
        return TradingWarning(
            type="month_end",
            severity="high",
            label="🗓️ 月末最終営業日 = 月足手仕舞い警戒",
            message="今日は月の最終営業日。月足ベースの手仕舞い動向に警戒。",
            action="週足より強い動きになりやすい。翌月月初から新トレンドが出る可能性も。",
        )

    if nikkei_month_is_positive:
        return TradingWarning(
            type="month_end",
            severity="high",
            label="🗓️ 月末 × 月足陽線 = 大きな手仕舞い売り警戒",
            message="今月の日経は陽線。月末にロングカバーの売りが入りやすく、週足手仕舞いより強い。",
            action="月末近くの大引けにかけての下げを警戒。"
                   "長期玉でもボラが大きくなるので、逆指値を引き締めておく。",
        )
    else:
        return TradingWarning(
            type="month_end",
            severity="medium",
            label="🗓️ 月末 × 月足陰線 = ショートカバー買い警戒",
            message="今月の日経は陰線。月末にショートカバーの買いが入りやすい。",
            action="ショートポジの翌月持ち越しは注意。月末大引けからの買い戻しで巻き込まれる懸念。",
        )


def check_pre_holiday_warning(today: date) -> TradingWarning | None:
    """3連休前警告。"""
    if not is_pre_holiday(today):
        return None

    nxt = next_trading_day(today)
    assert nxt is not None
    gap_days = (nxt - today).days
    gap_label = "3連休前" if gap_days == 3 else f"{gap_days}日休暇前"

    return TradingWarning(
        type="pre_holiday",
        severity="medium",
        label=f"🏖️ {gap_label} = 持ち越しリスク増",
        message=f"次の営業日は{nxt.isoformat()}。休暇中は地政学リスクで窓開けしやすい。",
        action="ポジションを縮小する、ヘッジポジを入れる等の検討を。"
               "特にレバレッジ先物・CFDは想定外の窓開けに注意。",
    )


def check_month_start_warning(today: date) -> TradingWarning | None:
    """月初営業日警告（PDFの「月初めという節目での下げ → 月全体に波及する恐れ」）。"""
    if not is_trading_day(today):
        return None
    # 前営業日が前月なら、今日は月初営業日
    # 簡易判定: 過去7日の範囲で前月の最終営業日を探す
    for delta in range(1, 8):
        prev = today - timedelta(days=delta)
        if is_trading_day(prev):
            if prev.month != today.month:
                return TradingWarning(
                    type="month_start",
                    severity="low",
                    label="🆕 月初営業日 = 月間トレンド形成に注目",
                    message="月初の値動きが月全体のバイアスになりやすい（特に下げの場合）。",
                    action="今日の方向性は月間トレンドの示唆になりうる。過大な逆張りは控えめに。",
                )
            return None
    return None


# ========== 統合API ==========

def get_all_warnings(
    today: date,
    nikkei_week_is_positive: bool | None = None,
    nikkei_month_is_positive: bool | None = None,
) -> list[TradingWarning]:
    """今日該当する警告を全て返す（severity=high を先頭に）"""
    candidates = [
        check_friday_warning(today, nikkei_week_is_positive),
        check_month_end_warning(today, nikkei_month_is_positive),
        check_pre_holiday_warning(today),
        check_month_start_warning(today),
    ]
    warnings = [w for w in candidates if w is not None]

    severity_order = {"high": 0, "medium": 1, "low": 2}
    warnings.sort(key=lambda w: severity_order.get(w.severity, 9))
    return warnings
