"""
Daytrade Signal Board - メインエントリポイント
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from kiriban import build_daily_signal
from market_direction import build_market_direction
from sector_mapping import build_all_sector_signals, get_all_us_tickers
from warnings_module import get_all_warnings
from market_context import build_market_context
from dashboard import render_dashboard


JST = ZoneInfo("Asia/Tokyo")


def main() -> int:
    output_dir = Path(__file__).resolve().parent.parent / "docs"
    output_dir.mkdir(exist_ok=True)

    us_tickers = get_all_us_tickers()

    try:
        from fetch_data import fetch_all_market_data
        market = fetch_all_market_data(us_sector_tickers=us_tickers)
    except Exception as e:
        print(f"⚠️ Failed to fetch live data: {e}")
        print("Falling back to stub data for development.")
        market = {
            "timestamp": "2026-04-24T08:40:00+09:00",  # 金曜にしてテスト
            "nikkei": {
                "prev_close": 38500.0,
                "change_pct": -0.5,
                "week_is_positive": True,
                "month_is_positive": True,
            },
            "nikkei_futures": {"price": 37400.0},
            "etf_1570": {"prev_close": 26000.0},
            "us_markets": {
                "nasdaq_change_pct": -1.2,
                "dow_change_pct": -0.8,
                "sox_change_pct": -2.5,
            },
            "fx_commodities": {
                "usdjpy_price": 150.2,
                "usdjpy_change_pct": -0.8,
                "gold_price": 2650.0,
                "gold_change_pct": 1.2,
                "oil_price": 72.5,
                "oil_change_pct": -0.3,
            },
            "us_sector_changes": {
                "AMAT": -2.8, "LRCX": -3.1, "KLAC": -2.5, "AMD": -3.5, "NVDA": -2.9,
                "SNDK": -2.2, "WDC": -1.9, "STX": -1.5,
                "CAT": 0.3, "DE": -0.1,
                "XOM": 1.8, "CVX": 1.6, "COP": 2.1,
                "LMT": 2.3, "RTX": 1.9, "BA": 0.8, "HON": 0.4, "NOC": 1.7,
                "VZ": 0.7, "T": 0.5, "TMUS": 0.2,
                "CRM": -1.4, "MSFT": -0.8, "ORCL": -2.1, "ADBE": -1.6, "INTU": -1.2, "NOW": -1.8,
                "UPS": -0.2, "FDX": 0.1,
                "KO": 0.3, "PG": 0.1, "CL": -0.1, "MCD": 0.4,
            },
        }

    today = datetime.fromisoformat(market["timestamp"]).date()

    # 警告バナー
    warnings = get_all_warnings(
        today=today,
        nikkei_week_is_positive=market["nikkei"].get("week_is_positive"),
        nikkei_month_is_positive=market["nikkei"].get("month_is_positive"),
    )

    # 為替・コモディティ情報
    fx = market.get("fx_commodities", {})
    market_ctx = build_market_context(
        usdjpy_price=fx.get("usdjpy_price", 150.0),
        usdjpy_change_pct=fx.get("usdjpy_change_pct", 0.0),
        gold_price=fx.get("gold_price", 2600.0),
        gold_change_pct=fx.get("gold_change_pct", 0.0),
        oil_price=fx.get("oil_price", 70.0),
        oil_change_pct=fx.get("oil_change_pct", 0.0),
    )

    # 日経デイトレ方針
    futures_diff = market["nikkei_futures"]["price"] - market["nikkei"]["prev_close"]
    direction_signal = build_market_direction(
        nasdaq_change_pct=market["us_markets"]["nasdaq_change_pct"],
        dow_change_pct=market["us_markets"]["dow_change_pct"],
        sox_change_pct=market["us_markets"]["sox_change_pct"],
        futures_diff=futures_diff,
    )

    # キリバン
    kiriban_signal = build_daily_signal(
        nikkei_prev_close=market["nikkei"]["prev_close"],
        nikkei_futures=market["nikkei_futures"]["price"],
    )

    # セクター
    sector_signals = build_all_sector_signals(market.get("us_sector_changes", {}))
    sector_signals_dict = [s.as_dict() for s in sector_signals]

    # JSON出力
    json_path = output_dir / "signal.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "market": market,
                "warnings": [w.as_dict() for w in warnings],
                "market_context": market_ctx.as_dict(),
                "direction": direction_signal.as_dict(),
                "kiriban": kiriban_signal,
                "sectors": sector_signals_dict,
            },
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    print(f"✅ Signal JSON: {json_path}")

    # HTML出力
    html_path = output_dir / "index.html"
    render_dashboard(
        warnings=[w.as_dict() for w in warnings],
        market_context=market_ctx.as_dict(),
        direction_signal=direction_signal.as_dict(),
        kiriban_signal=kiriban_signal,
        market=market,
        sector_signals=sector_signals_dict,
        output_path=html_path,
    )

    # サマリ
    print("\n" + "=" * 60)
    if warnings:
        print("⚠️  警告:")
        for w in warnings:
            print(f"   [{w.severity:>6}] {w.label}")
    print(f"📊 本日の日経デイトレ方針: {direction_signal.verdict_label} (確度: {direction_signal.confidence})")
    print(f"📐 現対: {futures_diff:+,.0f}円")
    if market_ctx.combined_note:
        print(f"💱 マクロ警戒: {market_ctx.combined_note}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
