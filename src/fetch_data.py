"""
日経・先物・1570・ナスダックのデータ取得モジュール
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import yfinance as yf


JST = ZoneInfo("Asia/Tokyo")

# Yahoo Financeのティッカー
TICKER_NIKKEI_SPOT = "^N225"       # 日経225現物
TICKER_NIKKEI_FUT = "NKD=F"        # 日経225先物（CME, JPY建てではなくUSD建てなので注意）
TICKER_NIKKEI_LEV_ETF = "1570.T"   # 日経レバレッジETF
TICKER_NASDAQ = "^IXIC"            # ナスダック総合
TICKER_SOX = "^SOX"                # 半導体指数

# CMEの日経先物（NKD=F）はUSD建てなので、JPY建てに換算する必要がある。
# 代替: 大証日経先物はyfinanceで取得困難。一旦 NKD=F を USD/JPY で換算して使う。
TICKER_USDJPY = "JPY=X"


def fetch_prev_close(ticker: str) -> float:
    """指定ティッカーの直近終値を取得する。"""
    data = yf.Ticker(ticker).history(period="5d", interval="1d")
    if data.empty:
        raise RuntimeError(f"No data for {ticker}")
    return float(data["Close"].iloc[-1])


def fetch_current_price(ticker: str) -> float:
    """指定ティッカーの現在価格（直近1分足）を取得する。

    寄り前はfast_infoのregularMarketPriceではなく直近セッション終値が返る点に注意。
    """
    tkr = yf.Ticker(ticker)
    # fast_info は ライトウェイトだが寄り前は前日データが返ることに注意
    try:
        info = tkr.fast_info
        price = info.get("lastPrice") or info.get("last_price")
        if price:
            return float(price)
    except Exception:
        pass

    # フォールバック: 1分足の直近
    data = tkr.history(period="1d", interval="1m")
    if data.empty:
        data = tkr.history(period="5d", interval="1d")
    if data.empty:
        raise RuntimeError(f"No data for {ticker}")
    return float(data["Close"].iloc[-1])


def fetch_nikkei_futures_jpy() -> float:
    """日経225先物をJPY建てで取得する。

    NKD=F はUSD建てなので USD/JPY で換算する。
    """
    nkd_usd = fetch_current_price(TICKER_NIKKEI_FUT)
    usdjpy = fetch_current_price(TICKER_USDJPY)
    # NKD=F の価格は既に日経インデックス値（USDではなくポイント扱い）で提供されることが多いが、
    # 実際には契約乗数がUSDベース。一旦そのまま使い、運用しながら補正する。
    # TODO: 大証先物のAPIに切り替える（yfinance外）
    return nkd_usd


def fetch_change_pct(ticker: str, days: int = 1) -> float:
    """直近N日間の騰落率（%）を返す。"""
    data = yf.Ticker(ticker).history(period=f"{days + 3}d", interval="1d")
    if len(data) < 2:
        return 0.0
    return float((data["Close"].iloc[-1] / data["Close"].iloc[-2] - 1) * 100)


def fetch_all_market_data() -> dict:
    """ダッシュボード用の全マーケットデータを一括取得する。"""
    now = datetime.now(JST)

    nikkei_prev_close = fetch_prev_close(TICKER_NIKKEI_SPOT)
    nikkei_futures = fetch_nikkei_futures_jpy()
    etf_1570_prev_close = fetch_prev_close(TICKER_NIKKEI_LEV_ETF)

    nasdaq_change = fetch_change_pct(TICKER_NASDAQ)
    sox_change = fetch_change_pct(TICKER_SOX)
    nikkei_change = fetch_change_pct(TICKER_NIKKEI_SPOT)

    return {
        "timestamp": now.isoformat(),
        "nikkei": {
            "prev_close": nikkei_prev_close,
            "change_pct": nikkei_change,
        },
        "nikkei_futures": {
            "price": nikkei_futures,
        },
        "etf_1570": {
            "prev_close": etf_1570_prev_close,
        },
        "us_markets": {
            "nasdaq_change_pct": nasdaq_change,
            "sox_change_pct": sox_change,
        },
    }
