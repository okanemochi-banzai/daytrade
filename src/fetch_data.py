"""
日経・先物・1570・米セクター代表銘柄のデータ取得モジュール
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf


JST = ZoneInfo("Asia/Tokyo")

TICKER_NIKKEI_SPOT = "^N225"
TICKER_NIKKEI_FUT = "NKD=F"
TICKER_NIKKEI_LEV_ETF = "1570.T"
TICKER_NASDAQ = "^IXIC"
TICKER_DOW = "^DJI"
TICKER_SOX = "^SOX"
TICKER_USDJPY = "JPY=X"
TICKER_GOLD = "GC=F"        # ゴールド先物
TICKER_OIL_WTI = "CL=F"     # WTI原油先物


def fetch_prev_close(ticker: str) -> float:
    data = yf.Ticker(ticker).history(period="5d", interval="1d")
    if data.empty:
        raise RuntimeError(f"No data for {ticker}")
    return float(data["Close"].iloc[-1])


def fetch_current_price(ticker: str) -> float:
    tkr = yf.Ticker(ticker)
    try:
        info = tkr.fast_info
        price = info.get("lastPrice") or info.get("last_price")
        if price:
            return float(price)
    except Exception:
        pass

    data = tkr.history(period="1d", interval="1m")
    if data.empty:
        data = tkr.history(period="5d", interval="1d")
    if data.empty:
        raise RuntimeError(f"No data for {ticker}")
    return float(data["Close"].iloc[-1])


def fetch_nikkei_futures_jpy() -> float:
    """日経225先物をJPY建てで取得する（NKD=FはCME日経先物、ポイント表示）。"""
    return fetch_current_price(TICKER_NIKKEI_FUT)


def fetch_change_pct(ticker: str, days: int = 1) -> float:
    data = yf.Ticker(ticker).history(period=f"{days + 3}d", interval="1d")
    if len(data) < 2:
        return 0.0
    return float((data["Close"].iloc[-1] / data["Close"].iloc[-2] - 1) * 100)


def fetch_multi_change_pct(tickers: list[str]) -> dict[str, float]:
    """複数ティッカーの騰落率を一括取得する。

    yf.download で一括取得すると効率的だが、多数ティッカーではAPI制限にかかるため
    個別取得にフォールバックできるよう設計。
    """
    if not tickers:
        return {}

    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period="5d",
            interval="1d",
            progress=False,
            group_by="ticker",
            auto_adjust=True,
        )
    except Exception as e:
        print(f"⚠️ Bulk download failed: {e}. Falling back to individual fetches.")
        return {t: _safe_change_pct(t) for t in tickers}

    result: dict[str, float] = {}
    for t in tickers:
        try:
            if len(tickers) == 1:
                closes = data["Close"]
            else:
                closes = data[t]["Close"]
            closes = closes.dropna()
            if len(closes) < 2:
                continue
            pct = float((closes.iloc[-1] / closes.iloc[-2] - 1) * 100)
            result[t] = pct
        except (KeyError, IndexError):
            continue
    return result


def _safe_change_pct(ticker: str) -> float:
    try:
        return fetch_change_pct(ticker)
    except Exception:
        return 0.0


def _week_and_month_direction() -> tuple[bool | None, bool | None]:
    """今週と今月の日経が陽線かを判定する。

    Returns:
        (週足陽線か, 月足陽線か) または (None, None) if データ取得失敗
    """
    try:
        data = yf.Ticker(TICKER_NIKKEI_SPOT).history(period="3mo", interval="1d")
        if data.empty:
            return None, None
        # タイムゾーン除去
        data.index = data.index.tz_localize(None) if data.index.tz is not None else data.index

        from datetime import datetime
        now = datetime.now(JST).replace(tzinfo=None)

        # 今週の月曜日の日付を計算
        days_since_monday = now.weekday()
        week_start = now - __import__("datetime").timedelta(days=days_since_monday)
        week_start_ts = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        week_data = data[data.index >= week_start_ts]
        if len(week_data) < 1:
            week_positive = None
        else:
            week_open = float(week_data["Open"].iloc[0])
            week_close = float(week_data["Close"].iloc[-1])
            week_positive = week_close > week_open

        # 今月
        month_start_ts = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_data = data[data.index >= month_start_ts]
        if len(month_data) < 1:
            month_positive = None
        else:
            month_open = float(month_data["Open"].iloc[0])
            month_close = float(month_data["Close"].iloc[-1])
            month_positive = month_close > month_open

        return week_positive, month_positive
    except Exception as e:
        print(f"⚠️ Failed to compute week/month direction: {e}")
        return None, None


def fetch_all_market_data(us_sector_tickers: list[str] | None = None) -> dict:
    """ダッシュボード用の全マーケットデータを一括取得する。"""
    now = datetime.now(JST)

    nikkei_prev_close = fetch_prev_close(TICKER_NIKKEI_SPOT)
    nikkei_futures = fetch_nikkei_futures_jpy()
    etf_1570_prev_close = fetch_prev_close(TICKER_NIKKEI_LEV_ETF)

    nasdaq_change = fetch_change_pct(TICKER_NASDAQ)
    dow_change = fetch_change_pct(TICKER_DOW)
    sox_change = fetch_change_pct(TICKER_SOX)
    nikkei_change = fetch_change_pct(TICKER_NIKKEI_SPOT)

    # 為替・コモディティ
    usdjpy_price = fetch_current_price(TICKER_USDJPY)
    usdjpy_change = fetch_change_pct(TICKER_USDJPY)
    gold_price = fetch_current_price(TICKER_GOLD)
    gold_change = fetch_change_pct(TICKER_GOLD)
    oil_price = fetch_current_price(TICKER_OIL_WTI)
    oil_change = fetch_change_pct(TICKER_OIL_WTI)

    # 日経の週足・月足方向
    week_positive, month_positive = _week_and_month_direction()

    us_sector_changes: dict[str, float] = {}
    if us_sector_tickers:
        us_sector_changes = fetch_multi_change_pct(us_sector_tickers)

    return {
        "timestamp": now.isoformat(),
        "nikkei": {
            "prev_close": nikkei_prev_close,
            "change_pct": nikkei_change,
            "week_is_positive": week_positive,
            "month_is_positive": month_positive,
        },
        "nikkei_futures": {
            "price": nikkei_futures,
        },
        "etf_1570": {
            "prev_close": etf_1570_prev_close,
        },
        "us_markets": {
            "nasdaq_change_pct": nasdaq_change,
            "dow_change_pct": dow_change,
            "sox_change_pct": sox_change,
        },
        "fx_commodities": {
            "usdjpy_price": usdjpy_price,
            "usdjpy_change_pct": usdjpy_change,
            "gold_price": gold_price,
            "gold_change_pct": gold_change,
            "oil_price": oil_price,
            "oil_change_pct": oil_change,
        },
        "us_sector_changes": us_sector_changes,
    }
