"""
セクター連動マッピングの統計検証モジュール

PDFから抽出したセクターペアについて、過去データで以下を検証する:
  - ピアソン相関係数（米T日 vs 日T+1日）
  - 統計的有意性（p値）
  - 上昇/下落ヒット率（条件付き確率）

日付のアライメント:
  米国市場は日本時間の深夜に引ける → その翌朝の日本市場寄り付きに影響
  したがって「米T日終値 vs 日(T+1)日終値」の騰落率ペアを比較するのが自然。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

from sector_mapping import SECTOR_PAIRS, SectorPair


# 判定基準
STRONG_CORR_THRESHOLD = 0.4   # |r| >= 0.4 で「強い連動」
WEAK_CORR_THRESHOLD = 0.2     # |r| >= 0.2 で「弱いながら連動」
SIGNIFICANT_P = 0.05          # p値 < 0.05 で統計的有意

# ヒット率の基準
US_UP_THRESHOLD = 1.0          # 米+1%以上を「上げ」と定義
US_DOWN_THRESHOLD = -1.0       # 米-1%以下を「下げ」と定義
JP_UP_THRESHOLD = 0.0          # 日+0%以上を「連動上げ」
JP_DOWN_THRESHOLD = 0.0        # 日0%以下を「連動下げ」


Verdict = Literal["confirmed", "weak", "contradicted", "insufficient_data"]


@dataclass
class PairValidationResult:
    """1セクターペアの検証結果"""
    sector_name: str
    us_label: str
    us_tickers_used: list[str]
    jp_tickers_used: list[str]
    n_samples: int                      # 有効サンプル数
    pearson_r: float
    p_value: float
    hit_rate_up: float | None           # 米上げ日の翌日日本上げ率（米上げ日がない場合はNone）
    hit_rate_down: float | None         # 米下げ日の翌日日本下げ率
    n_us_up_days: int
    n_us_down_days: int
    expected_correlation: str            # PDFから:high/medium/low
    verdict: Verdict
    verdict_label: str                  # 日本語ラベル

    def as_dict(self) -> dict:
        return asdict(self)


def fetch_prices(tickers: list[str], period: str = "6mo") -> pd.DataFrame:
    """複数ティッカーの過去終値を取得する。

    Returns:
        DataFrame: index=日付, columns=ティッカー, values=終値
    """
    if not tickers:
        return pd.DataFrame()

    data = yf.download(
        tickers=" ".join(tickers),
        period=period,
        interval="1d",
        progress=False,
        group_by="ticker",
        auto_adjust=True,
        threads=True,
    )

    # 単一ティッカーと複数ティッカーで構造が違うので統一
    if len(tickers) == 1:
        closes = data[["Close"]].rename(columns={"Close": tickers[0]})
    else:
        closes_dict = {}
        for t in tickers:
            try:
                closes_dict[t] = data[t]["Close"]
            except KeyError:
                continue
        closes = pd.DataFrame(closes_dict)

    return closes.dropna(how="all")


def compute_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """日次騰落率(%)を計算する。"""
    return prices.pct_change().dropna(how="all") * 100


def aggregate_sector_returns(returns: pd.DataFrame, tickers: list[str]) -> pd.Series:
    """セクター内の銘柄で平均した日次騰落率を返す。

    欠損値は除外して利用可能な銘柄のみで平均。
    """
    available = [t for t in tickers if t in returns.columns]
    if not available:
        return pd.Series(dtype=float)
    return returns[available].mean(axis=1, skipna=True)


def align_us_jp_returns(us_returns: pd.Series, jp_returns: pd.Series) -> pd.DataFrame:
    """米T日と日T+1日の騰落率をペアリングする。

    実装:
      日本の騰落率を1日前にシフト（T+1日の値をT日付にずらす）して、
      米国のインデックスと内部結合する。
    """
    if us_returns.empty or jp_returns.empty:
        return pd.DataFrame(columns=["us", "jp"])

    # 日付をdate型に統一（yfinanceはTimezone付きDatetimeIndexのことがある）
    us = us_returns.copy()
    jp = jp_returns.copy()
    us.index = pd.to_datetime(us.index).tz_localize(None).normalize()
    jp.index = pd.to_datetime(jp.index).tz_localize(None).normalize()

    # 日本株を1日前にシフト: 日(T+1)日のリターンをT日付として扱う
    jp_shifted = jp.shift(-1)

    df = pd.DataFrame({"us": us, "jp": jp_shifted}).dropna()
    return df


def compute_correlation(paired: pd.DataFrame) -> tuple[float, float, int]:
    """ピアソン相関と p値 と サンプル数を返す。"""
    n = len(paired)
    if n < 3:
        return float("nan"), float("nan"), n
    r, p = stats.pearsonr(paired["us"].values, paired["jp"].values)
    return float(r), float(p), n


def compute_hit_rates(
    paired: pd.DataFrame,
) -> tuple[float | None, int, float | None, int]:
    """米の大きな動きの翌日、日本が同方向に動いた率を計算。

    Returns:
        (上昇ヒット率, 米上げ日数, 下落ヒット率, 米下げ日数)
    """
    us_up_mask = paired["us"] >= US_UP_THRESHOLD
    us_down_mask = paired["us"] <= US_DOWN_THRESHOLD

    n_up = int(us_up_mask.sum())
    n_down = int(us_down_mask.sum())

    hit_up = None
    if n_up > 0:
        jp_on_us_up = paired.loc[us_up_mask, "jp"]
        hit_up = float((jp_on_us_up >= JP_UP_THRESHOLD).sum() / n_up)

    hit_down = None
    if n_down > 0:
        jp_on_us_down = paired.loc[us_down_mask, "jp"]
        hit_down = float((jp_on_us_down <= JP_DOWN_THRESHOLD).sum() / n_down)

    return hit_up, n_up, hit_down, n_down


def classify_verdict(
    r: float,
    p: float,
    n: int,
    expected: str,
) -> tuple[Verdict, str]:
    """期待連動強度と実測から総合判定を返す。"""
    if n < 20 or np.isnan(r):
        return "insufficient_data", "データ不足"

    abs_r = abs(r)
    is_positive = r > 0
    is_significant = p < SIGNIFICANT_P

    # 期待しているのは「正の相関」。負の相関なら矛盾
    if not is_positive:
        return "contradicted", "⚠️ 期待と逆方向の相関"

    # 強度マッピング
    if expected == "high":
        if abs_r >= STRONG_CORR_THRESHOLD and is_significant:
            return "confirmed", "✅ 強連動を確認"
        elif abs_r >= WEAK_CORR_THRESHOLD:
            return "weak", "△ 期待より弱い連動"
        else:
            return "contradicted", "✗ 強連動が確認できず"
    elif expected == "medium":
        if abs_r >= WEAK_CORR_THRESHOLD and is_significant:
            return "confirmed", "✅ 中程度の連動を確認"
        elif abs_r >= 0.1:
            return "weak", "△ 弱連動"
        else:
            return "contradicted", "✗ 連動性なし"
    else:  # low
        if abs_r >= WEAK_CORR_THRESHOLD and is_significant:
            return "confirmed", "✅ 想定より強い連動"
        elif abs_r >= 0.1:
            return "weak", "△ 弱連動（想定通り）"
        else:
            return "contradicted", "✗ 連動性なし"


def validate_sector_pair(
    pair: SectorPair,
    period: str = "6mo",
    _price_cache: dict | None = None,
) -> PairValidationResult:
    """1セクターペアを検証する。

    Args:
        pair: セクターペア定義
        period: yfinance の期間指定 ("3mo", "6mo", "1y" 等)
        _price_cache: 銘柄価格データのキャッシュ（複数ペアで共有）
    """
    all_tickers = list(pair.us_tickers) + list(pair.jp_tickers)

    if _price_cache is not None and all(t in _price_cache for t in all_tickers):
        prices = pd.DataFrame({t: _price_cache[t] for t in all_tickers if t in _price_cache})
    else:
        prices = fetch_prices(all_tickers, period=period)

    returns = compute_daily_returns(prices)

    us_avg = aggregate_sector_returns(returns, list(pair.us_tickers))
    jp_avg = aggregate_sector_returns(returns, list(pair.jp_tickers))

    paired = align_us_jp_returns(us_avg, jp_avg)
    r, p, n = compute_correlation(paired)
    hit_up, n_up, hit_down, n_down = compute_hit_rates(paired) if n > 0 else (None, 0, None, 0)

    verdict, verdict_label = classify_verdict(r, p, n, pair.correlation_strength)

    us_used = [t for t in pair.us_tickers if t in returns.columns]
    jp_used = [t for t in pair.jp_tickers if t in returns.columns]

    return PairValidationResult(
        sector_name=pair.name,
        us_label=pair.us_label,
        us_tickers_used=us_used,
        jp_tickers_used=jp_used,
        n_samples=n,
        pearson_r=r if not np.isnan(r) else 0.0,
        p_value=p if not np.isnan(p) else 1.0,
        hit_rate_up=hit_up,
        hit_rate_down=hit_down,
        n_us_up_days=n_up,
        n_us_down_days=n_down,
        expected_correlation=pair.correlation_strength,
        verdict=verdict,
        verdict_label=verdict_label,
    )


def validate_all_sectors(period: str = "6mo") -> list[PairValidationResult]:
    """全セクターペアを検証。効率化のため全ティッカーを一括取得してキャッシュ。"""
    # 全ティッカーを収集
    all_tickers: set[str] = set()
    for pair in SECTOR_PAIRS:
        all_tickers.update(pair.us_tickers)
        all_tickers.update(pair.jp_tickers)

    print(f"Fetching {len(all_tickers)} tickers for {period}...")
    prices = fetch_prices(sorted(all_tickers), period=period)
    print(f"Got data for {len(prices.columns)} tickers, {len(prices)} days")

    # キャッシュ化
    cache = {t: prices[t] for t in prices.columns}

    results = []
    for pair in SECTOR_PAIRS:
        result = validate_sector_pair(pair, period=period, _price_cache=cache)
        results.append(result)
        print(f"  {result.sector_name:20s} r={result.pearson_r:+.3f} p={result.p_value:.3f} n={result.n_samples:3d} {result.verdict_label}")

    return results
