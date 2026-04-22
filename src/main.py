"""
Daytrade Signal Board - メインエントリポイント

GitHub Actionsから呼ばれ、毎朝寄り前にシグナルを計算してHTMLダッシュボードを生成する。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from kiriban import build_daily_signal
from dashboard import render_dashboard


def main() -> int:
    output_dir = Path(__file__).resolve().parent.parent / "docs"
    output_dir.mkdir(exist_ok=True)

    try:
        from fetch_data import fetch_all_market_data
        market = fetch_all_market_data()
    except Exception as e:
        print(f"⚠️ Failed to fetch live data: {e}")
        print("Falling back to stub data for development.")
        market = {
            "timestamp": "2026-04-23T08:40:00+09:00",
            "nikkei": {"prev_close": 38500.0, "change_pct": -0.5},
            "nikkei_futures": {"price": 37400.0},
            "etf_1570": {"prev_close": 26000.0},
            "us_markets": {"nasdaq_change_pct": -1.2, "sox_change_pct": -2.5},
        }

    signal = build_daily_signal(
        nikkei_prev_close=market["nikkei"]["prev_close"],
        nikkei_futures=market["nikkei_futures"]["price"],
    )

    # JSON出力（他ツール連携用）
    json_path = output_dir / "signal.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"market": market, "signal": signal}, f, ensure_ascii=False, indent=2)
    print(f"✅ Signal JSON: {json_path}")

    # HTML出力
    html_path = output_dir / "index.html"
    render_dashboard(signal, market, html_path)

    # サマリを標準出力に
    sayatori = signal["sayatori_signal"]
    print("\n" + "=" * 60)
    print(f"📊 朝一鞘取りシグナル: {sayatori['direction'].upper()}")
    print(f"   現対: {sayatori['diff']:+,.0f}円")
    print(f"   {sayatori['rationale']}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
