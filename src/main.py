"""
Daytrade Signal Board - メインエントリポイント

GitHub Actionsから呼ばれ、毎朝寄り前にシグナルを計算してHTMLダッシュボードを生成する。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from kiriban import build_daily_signal
from sector_mapping import build_all_sector_signals, get_all_us_tickers
from dashboard import render_dashboard


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
            "timestamp": "2026-04-23T08:40:00+09:00",
            "nikkei": {"prev_close": 38500.0, "change_pct": -0.5},
            "nikkei_futures": {"price": 37400.0},
            "etf_1570": {"prev_close": 26000.0},
            "us_markets": {"nasdaq_change_pct": -1.2, "sox_change_pct": -2.5},
            "us_sector_changes": {
                # 半導体: SOXに連動して下げ
                "AMAT": -2.8, "LRCX": -3.1, "KLAC": -2.5, "AMD": -3.5, "NVDA": -2.9,
                # ストレージ: 半導体と同じく下げ
                "SNDK": -2.2, "WDC": -1.9, "STX": -1.5,
                # 建機: 中立
                "CAT": 0.3, "DE": -0.1,
                # エネルギー: 原油上げ
                "XOM": 1.8, "CVX": 1.6, "COP": 2.1,
                # 軍需: 地政学リスクで上げ
                "LMT": 2.3, "RTX": 1.9, "BA": 0.8, "HON": 0.4, "NOC": 1.7,
                # 通信: やや上げ
                "VZ": 0.7, "T": 0.5, "TMUS": 0.2,
                # SaaS: 下げ主体
                "CRM": -1.4, "MSFT": -0.8, "ORCL": -2.1, "ADBE": -1.6, "INTU": -1.2, "NOW": -1.8,
                # 物流: 中立
                "UPS": -0.2, "FDX": 0.1,
                # 生活防衛
                "KO": 0.3, "PG": 0.1, "CL": -0.1, "MCD": 0.4,
            },
        }

    # キリバンシグナル
    signal = build_daily_signal(
        nikkei_prev_close=market["nikkei"]["prev_close"],
        nikkei_futures=market["nikkei_futures"]["price"],
    )

    # セクター連動シグナル
    sector_signals = build_all_sector_signals(market.get("us_sector_changes", {}))
    sector_signals_dict = [s.as_dict() for s in sector_signals]

    # JSON出力
    json_path = output_dir / "signal.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {"market": market, "signal": signal, "sectors": sector_signals_dict},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"✅ Signal JSON: {json_path}")

    # HTML出力
    html_path = output_dir / "index.html"
    render_dashboard(signal, market, sector_signals_dict, html_path)

    # サマリ
    sayatori = signal["sayatori_signal"]
    print("\n" + "=" * 60)
    print(f"📊 朝一鞘取りシグナル: {sayatori['direction'].upper()}")
    print(f"   現対: {sayatori['diff']:+,.0f}円")
    print(f"   {sayatori['rationale']}")
    print("=" * 60)
    print("🔁 セクター連動予測（強い順）:")
    for s in sector_signals_dict[:5]:
        if s["signal_strength"] != "neutral":
            print(f"   [{s['signal_strength']:>6}] {s['sector_name']:10s} {s['us_avg_change_pct']:+.2f}% → {s['direction']}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
