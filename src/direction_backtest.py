"""
日経デイトレ方針判定ロジックのバックテスト

検証内容:
  過去の市場データを使って各日の判定を再構成し、
  判定別に日経の実際の値動きを集計する。

  判定の再構成:
    T-1日の米3指数騰落率（前営業日ベース）
    T-1日のNKD=F終値 − T-1日の^N225終値 = 翌朝の先物現対 相当
    これらを market_direction.build_market_direction() に渡して判定

  実際の結果:
    T日の日経寄り付き → 引け（日中騰落率、OCO不成デイトレの収益源）
    T日の前日終値 → 引け（日次騰落率）
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal

import numpy as np
import pandas as pd
import yfinance as yf

from market_direction import build_market_direction


@dataclass
class DirectionOutcomeStats:
    """1つの判定カテゴリの結果統計"""
    verdict: str                     # buy_bias / sell_bias / hands_off
    verdict_label: str
    n: int
    mean_intraday_pct: float         # 日中騰落率の平均
    median_intraday_pct: float
    std_intraday_pct: float
    mean_daily_pct: float            # 日次騰落率の平均
    median_daily_pct: float
    std_daily_pct: float
    directional_win_rate: float      # 判定方向に動いた日の割合（日中騰落率ベース）
    n_aligned: int                   # 方向一致日数
    avg_when_aligned: float          # 方向一致日の平均騰落率
    avg_when_not_aligned: float      # 方向不一致日の平均騰落率

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class DirectionBacktestResult:
    """バックテスト全体の結果"""
    period: str
    total_days: int
    start_date: str
    end_date: str
    stats_by_verdict: list[DirectionOutcomeStats]
    # 日毎のシグナルと結果（デバッグ・詳細分析用）
    daily_records: list[dict]

    def as_dict(self) -> dict:
        return {
            "period": self.period,
            "total_days": self.total_days,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "stats_by_verdict": [s.as_dict() for s in self.stats_by_verdict],
            "daily_records": self.daily_records,
        }


def fetch_historical_data(period: str = "1y") -> pd.DataFrame:
    """バックテストに必要な全ティッカーの日次OHLCを取得する。

    Returns:
        DataFrame with MultiIndex columns: (ticker, field)
          ticker: ^IXIC, ^DJI, ^SOX, ^N225, NKD=F
          field: Close, Open
    """
    tickers = ["^IXIC", "^DJI", "^SOX", "^N225", "NKD=F"]
    data = yf.download(
        tickers=" ".join(tickers),
        period=period,
        interval="1d",
        progress=False,
        group_by="ticker",
        auto_adjust=True,
        threads=True,
    )
    return data


def reconstruct_daily_signals(data: pd.DataFrame) -> pd.DataFrame:
    """各日の判定を再構成する。

    アライメント:
      T日の判定には、T-1日に確定した米指数とNKD=F終値を使う
      （実運用の朝 8:40 JST 時点で見られる情報と同等）

    Returns:
        DataFrame: index=T日（日本市場の日付）, columns=判定結果と入力値
    """
    # 必要な系列を抽出
    ixic = data["^IXIC"]["Close"].dropna()
    dji = data["^DJI"]["Close"].dropna()
    sox = data["^SOX"]["Close"].dropna()
    n225_close = data["^N225"]["Close"].dropna()
    n225_open = data["^N225"]["Open"].dropna()
    nkd = data["NKD=F"]["Close"].dropna()

    # 日次騰落率(%)を計算
    ixic_pct = ixic.pct_change() * 100
    dji_pct = dji.pct_change() * 100
    sox_pct = sox.pct_change() * 100

    # タイムゾーンを統一して日付に正規化
    def norm(s: pd.Series) -> pd.Series:
        s = s.copy()
        s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
        return s

    ixic_pct = norm(ixic_pct)
    dji_pct = norm(dji_pct)
    sox_pct = norm(sox_pct)
    n225_close = norm(n225_close)
    n225_open = norm(n225_open)
    nkd = norm(nkd)

    # 日本市場の日付リストを基準に、T日の判定を作る
    # 必要な入力: T-1営業日の米指数騰落率、T-1営業日のNKD=F終値、T-1営業日の^N225終値
    records = []
    nikkei_dates = sorted(n225_close.index)
    for i in range(1, len(nikkei_dates)):
        t = nikkei_dates[i]
        t_prev = nikkei_dates[i - 1]

        # 米指数は T-1 の日付、またはそれより手前の直近データ を使う
        # （週末などで日本休市の場合もあるため .asof() で最近接を取る）
        try:
            us_ixic_pct = ixic_pct.asof(t_prev)
            us_dji_pct = dji_pct.asof(t_prev)
            us_sox_pct = sox_pct.asof(t_prev)
            # NKD=F のT-1日終値を寄り前先物価格として使用
            futures_price = nkd.asof(t_prev)
            spot_price = n225_close.loc[t_prev]  # T-1の日経現物終値
        except (KeyError, IndexError):
            continue

        if pd.isna(us_ixic_pct) or pd.isna(us_dji_pct) or pd.isna(us_sox_pct):
            continue
        if pd.isna(futures_price) or pd.isna(spot_price):
            continue

        futures_diff = float(futures_price) - float(spot_price)

        signal = build_market_direction(
            nasdaq_change_pct=float(us_ixic_pct),
            dow_change_pct=float(us_dji_pct),
            sox_change_pct=float(us_sox_pct),
            futures_diff=futures_diff,
        )

        # 実際のT日の日経の値動き
        t_close = n225_close.get(t)
        t_open = n225_open.get(t)
        prev_close = n225_close.loc[t_prev]

        if pd.isna(t_close) or pd.isna(t_open):
            continue

        intraday_pct = float((t_close / t_open - 1) * 100)
        daily_pct = float((t_close / prev_close - 1) * 100)

        records.append(
            {
                "date": t.isoformat()[:10],
                "verdict": signal.verdict,
                "verdict_label": signal.verdict_label,
                "confidence": signal.confidence,
                "nasdaq_pct": float(us_ixic_pct),
                "dow_pct": float(us_dji_pct),
                "sox_pct": float(us_sox_pct),
                "futures_diff": futures_diff,
                "nikkei_open": float(t_open),
                "nikkei_close": float(t_close),
                "nikkei_prev_close": float(prev_close),
                "intraday_pct": intraday_pct,
                "daily_pct": daily_pct,
            }
        )

    return pd.DataFrame(records)


def compute_outcome_stats(
    daily_df: pd.DataFrame,
    verdict: Literal["buy_bias", "sell_bias", "hands_off"],
    verdict_label: str,
) -> DirectionOutcomeStats:
    """1つの判定カテゴリの統計を計算"""
    subset = daily_df[daily_df["verdict"] == verdict]
    n = len(subset)

    if n == 0:
        return DirectionOutcomeStats(
            verdict=verdict,
            verdict_label=verdict_label,
            n=0,
            mean_intraday_pct=0.0,
            median_intraday_pct=0.0,
            std_intraday_pct=0.0,
            mean_daily_pct=0.0,
            median_daily_pct=0.0,
            std_daily_pct=0.0,
            directional_win_rate=0.0,
            n_aligned=0,
            avg_when_aligned=0.0,
            avg_when_not_aligned=0.0,
        )

    intraday = subset["intraday_pct"].values
    daily = subset["daily_pct"].values

    # 方向一致の判定（intraday_pctベース）
    if verdict == "buy_bias":
        aligned_mask = intraday > 0  # 買い判定 & 日中上げ
    elif verdict == "sell_bias":
        aligned_mask = intraday < 0  # 売り判定 & 日中下げ
    else:
        # hands_off は方向を断定しないので、「ほぼフラットで推移した日」を方向一致扱い
        aligned_mask = np.abs(intraday) < 0.3

    n_aligned = int(aligned_mask.sum())
    win_rate = n_aligned / n if n > 0 else 0.0

    aligned_vals = intraday[aligned_mask]
    not_aligned_vals = intraday[~aligned_mask]

    return DirectionOutcomeStats(
        verdict=verdict,
        verdict_label=verdict_label,
        n=n,
        mean_intraday_pct=float(np.mean(intraday)),
        median_intraday_pct=float(np.median(intraday)),
        std_intraday_pct=float(np.std(intraday, ddof=1)) if n > 1 else 0.0,
        mean_daily_pct=float(np.mean(daily)),
        median_daily_pct=float(np.median(daily)),
        std_daily_pct=float(np.std(daily, ddof=1)) if n > 1 else 0.0,
        directional_win_rate=win_rate,
        n_aligned=n_aligned,
        avg_when_aligned=float(np.mean(aligned_vals)) if len(aligned_vals) > 0 else 0.0,
        avg_when_not_aligned=float(np.mean(not_aligned_vals)) if len(not_aligned_vals) > 0 else 0.0,
    )


def validate_direction_logic(period: str = "1y") -> DirectionBacktestResult:
    """メインのバックテスト実行関数"""
    print(f"Fetching historical data for {period}...")
    data = fetch_historical_data(period)

    print("Reconstructing daily signals...")
    daily_df = reconstruct_daily_signals(data)

    if daily_df.empty:
        return DirectionBacktestResult(
            period=period,
            total_days=0,
            start_date="",
            end_date="",
            stats_by_verdict=[],
            daily_records=[],
        )

    print(f"Analyzing {len(daily_df)} trading days...")

    stats = [
        compute_outcome_stats(daily_df, "buy_bias", "買いポジ主体"),
        compute_outcome_stats(daily_df, "sell_bias", "売りポジ主体"),
        compute_outcome_stats(daily_df, "hands_off", "初心者手出し無用"),
    ]

    # ログ出力
    for s in stats:
        if s.n > 0:
            print(
                f"  {s.verdict_label:20s} n={s.n:3d}  "
                f"日中平均={s.mean_intraday_pct:+.2f}%  "
                f"日中勝率={s.directional_win_rate*100:.1f}%  "
                f"日次平均={s.mean_daily_pct:+.2f}%"
            )

    return DirectionBacktestResult(
        period=period,
        total_days=len(daily_df),
        start_date=daily_df["date"].min(),
        end_date=daily_df["date"].max(),
        stats_by_verdict=stats,
        daily_records=daily_df.to_dict(orient="records"),
    )
