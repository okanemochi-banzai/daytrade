"""
バックテスト結果のHTML/JSONレポート生成
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backtest import PairValidationResult


JST = ZoneInfo("Asia/Tokyo")


def _verdict_class(verdict: str) -> str:
    return {
        "confirmed": "verdict-confirmed",
        "weak": "verdict-weak",
        "contradicted": "verdict-contradicted",
        "insufficient_data": "verdict-neutral",
    }.get(verdict, "verdict-neutral")


def _format_hit_rate(rate: float | None, n_days: int) -> str:
    if rate is None or n_days == 0:
        return '<span class="muted">—</span>'
    pct = rate * 100
    color = "var(--long)" if pct >= 60 else ("var(--short)" if pct < 40 else "var(--text)")
    return f'<span style="color: {color};">{pct:.1f}%</span><span class="muted"> (n={n_days})</span>'


def _format_r(r: float) -> str:
    if r >= 0.4:
        color = "var(--long)"
    elif r >= 0.2:
        color = "var(--accent)"
    elif r > 0:
        color = "var(--muted)"
    else:
        color = "var(--short)"
    return f'<b style="color: {color};">{r:+.3f}</b>'


def _format_p(p: float) -> str:
    if p < 0.001:
        return '<b style="color: var(--long);">&lt; 0.001</b>'
    if p < 0.05:
        return f'<b style="color: var(--long);">{p:.3f}</b>'
    if p < 0.1:
        return f'<span style="color: var(--accent);">{p:.3f}</span>'
    return f'<span class="muted">{p:.3f}</span>'


def render_report(
    results: list[PairValidationResult],
    period: str,
    output_html: Path,
    output_json: Path,
) -> None:
    """結果をHTMLとJSONで出力"""
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    # 統計サマリ
    n_total = len(results)
    n_confirmed = sum(1 for r in results if r.verdict == "confirmed")
    n_weak = sum(1 for r in results if r.verdict == "weak")
    n_contradicted = sum(1 for r in results if r.verdict == "contradicted")
    n_insufficient = sum(1 for r in results if r.verdict == "insufficient_data")

    # テーブル行
    rows_html = ""
    for r in results:
        tickers_us = ", ".join(r.us_tickers_used) if r.us_tickers_used else "—"
        tickers_jp = ", ".join(r.jp_tickers_used) if r.jp_tickers_used else "—"

        rows_html += f"""
          <tr>
            <td>
              <div class="sector-name"><b>{r.sector_name}</b></div>
              <div class="muted tiny">期待: {r.expected_correlation}</div>
            </td>
            <td class="num">{_format_r(r.pearson_r)}</td>
            <td class="num">{_format_p(r.p_value)}</td>
            <td class="num">{r.n_samples}</td>
            <td class="num">{_format_hit_rate(r.hit_rate_up, r.n_us_up_days)}</td>
            <td class="num">{_format_hit_rate(r.hit_rate_down, r.n_us_down_days)}</td>
            <td><span class="verdict {_verdict_class(r.verdict)}">{r.verdict_label}</span></td>
            <td class="tiny muted">
              米: {tickers_us}<br>
              日: {tickers_jp}
            </td>
          </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Backtest Report - Daytrade Signal Board</title>
<style>
  :root {{
    --bg: #0b1220;
    --panel: #151f33;
    --panel-2: #1d2842;
    --text: #e6edf3;
    --muted: #8ca0b3;
    --accent: #fbbf24;
    --long: #10b981;
    --short: #ef4444;
    --neutral: #6b7280;
    --border: #2a3654;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, "Segoe UI", "Hiragino Sans", "Yu Gothic", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
  }}
  .container {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
  header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; flex-wrap: wrap; gap: 8px; }}
  h1 {{ margin: 0; font-size: 20px; font-weight: 600; }}
  .back-link {{ color: var(--accent); text-decoration: none; font-size: 14px; }}
  .back-link:hover {{ text-decoration: underline; }}
  .timestamp {{ color: var(--muted); font-size: 13px; }}
  .period {{ color: var(--accent); font-size: 13px; font-weight: 600; }}

  .summary {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }}
  .summary-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    text-align: center;
  }}
  .summary-card .num {{ font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .summary-card .label {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
  .summary-confirmed .num {{ color: var(--long); }}
  .summary-weak .num {{ color: var(--accent); }}
  .summary-contradicted .num {{ color: var(--short); }}
  .summary-insufficient .num {{ color: var(--neutral); }}

  table.results {{
    width: 100%;
    border-collapse: collapse;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    font-size: 13px;
  }}
  table.results th {{
    background: var(--panel-2);
    color: var(--muted);
    font-weight: 500;
    text-align: left;
    padding: 12px 10px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }}
  table.results td {{
    padding: 12px 10px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }}
  table.results tr:last-child td {{ border-bottom: none; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .muted {{ color: var(--muted); }}
  .tiny {{ font-size: 11px; }}
  .sector-name {{ font-size: 14px; }}

  .verdict {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }}
  .verdict-confirmed {{ background: rgba(16, 185, 129, 0.15); color: var(--long); }}
  .verdict-weak {{ background: rgba(251, 191, 36, 0.15); color: var(--accent); }}
  .verdict-contradicted {{ background: rgba(239, 68, 68, 0.15); color: var(--short); }}
  .verdict-neutral {{ background: rgba(107, 114, 128, 0.15); color: var(--neutral); }}

  .explainer {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    margin: 24px 0;
    font-size: 13px;
  }}
  .explainer h3 {{ margin: 0 0 8px 0; font-size: 14px; color: var(--accent); }}
  .explainer ul {{ margin: 4px 0; padding-left: 20px; }}
  .explainer li {{ margin: 4px 0; }}
  .explainer code {{ background: var(--panel-2); padding: 1px 6px; border-radius: 3px; font-size: 12px; }}

  .footer-note {{
    margin-top: 32px;
    padding: 16px;
    background: var(--panel);
    border-radius: 8px;
    font-size: 12px;
    color: var(--muted);
    border: 1px solid var(--border);
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1>🧪 バックテスト検証レポート</h1>
      <a href="./index.html" class="back-link">← メインダッシュボードに戻る</a>
    </div>
    <div style="text-align: right;">
      <div class="period">検証期間: 過去 {period}</div>
      <div class="timestamp">Updated: {now}</div>
    </div>
  </header>

  <!-- サマリ -->
  <div class="summary">
    <div class="summary-card summary-confirmed">
      <div class="num">{n_confirmed}</div>
      <div class="label">✅ 連動確認</div>
    </div>
    <div class="summary-card summary-weak">
      <div class="num">{n_weak}</div>
      <div class="label">△ 弱連動</div>
    </div>
    <div class="summary-card summary-contradicted">
      <div class="num">{n_contradicted}</div>
      <div class="label">✗ 連動せず</div>
    </div>
    <div class="summary-card summary-insufficient">
      <div class="num">{n_insufficient}</div>
      <div class="label">— データ不足</div>
    </div>
    <div class="summary-card">
      <div class="num">{n_total}</div>
      <div class="label">合計セクター</div>
    </div>
  </div>

  <!-- 結果テーブル -->
  <table class="results">
    <thead>
      <tr>
        <th>セクター</th>
        <th class="num">相関 r</th>
        <th class="num">p値</th>
        <th class="num">n</th>
        <th class="num">米↑→日↑</th>
        <th class="num">米↓→日↓</th>
        <th>判定</th>
        <th>使用銘柄</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>

  <!-- 読み方 -->
  <div class="explainer">
    <h3>📖 指標の読み方</h3>
    <ul>
      <li><b>相関 r</b>: 米セクター平均騰落率(T日) と 日本セクター平均騰落率(T+1日) のピアソン相関係数。
        <code>r ≥ 0.4</code> で強い連動、<code>0.2 ≤ r &lt; 0.4</code> で中程度、それ未満は弱い。</li>
      <li><b>p値</b>: 「本当は無相関なのに偶然この相関係数が出た確率」。<code>&lt; 0.05</code> で統計的に有意。</li>
      <li><b>n</b>: 有効サンプル数（日数）。<code>n &lt; 20</code> だと判定不能。</li>
      <li><b>米↑→日↑ ヒット率</b>: 米セクターが<b>+1%以上上げた日</b>、翌日の日本セクターが<b>+0%以上</b>だった確率。</li>
      <li><b>米↓→日↓ ヒット率</b>: 米セクターが<b>-1%以上下げた日</b>、翌日の日本セクターが<b>-0%以下</b>だった確率。</li>
      <li><b>判定</b>: PDFの経験則（期待連動強度: high/medium/low）と実測の整合性。</li>
    </ul>
  </div>

  <!-- 使い方 -->
  <div class="explainer">
    <h3>🎯 このレポートの使い方</h3>
    <ul>
      <li><b>confirmed</b> のセクター → メインダッシュボードのシグナルを信頼度高く使える。</li>
      <li><b>weak</b> のセクター → 参考程度に。他の根拠と組み合わせて判断。</li>
      <li><b>contradicted</b> のセクター → シグナルを疑う、もしくはマッピングから外す候補。</li>
      <li><b>insufficient_data</b> → サンプル不足、バックテスト期間を伸ばすか、銘柄構成を見直す。</li>
    </ul>
  </div>

  <div class="footer-note">
    <b>⚠️ 注意点</b><br>
    ・バックテスト期間は市場環境に大きく依存します（下げ相場・上げ相場で相関が変わる）。定期的に再検証してください。<br>
    ・相関が高くても、将来も同じとは限りません。特に個別銘柄材料（決算、不正、M&A）発生時は連動が崩れます。<br>
    ・サンプル数が少ないセクターでは、たまたま高い相関が出ていることがあります。p値も必ず確認してください。<br>
    ・ヒット率は「方向一致率」を見るもので、実際のトレード収益性とは別物です。
  </div>
</div>
</body>
</html>"""

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")

    # JSON出力
    json_data = {
        "generated_at": now,
        "period": period,
        "summary": {
            "total": n_total,
            "confirmed": n_confirmed,
            "weak": n_weak,
            "contradicted": n_contradicted,
            "insufficient_data": n_insufficient,
        },
        "results": [r.as_dict() for r in results],
    }
    output_json.write_text(
        json.dumps(json_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"📄 HTML report: {output_html}")
    print(f"📊 JSON report: {output_json}")


def run_backtest_and_report(period: str = "6mo") -> None:
    """バックテストを実行してレポートを出力するエントリポイント"""
    from backtest import validate_all_sectors

    output_dir = Path(__file__).resolve().parent.parent / "docs"
    output_dir.mkdir(exist_ok=True)

    print(f"🔍 Running backtest for period: {period}")
    results = validate_all_sectors(period=period)

    print()
    render_report(
        results=results,
        period=period,
        output_html=output_dir / "backtest_report.html",
        output_json=output_dir / "backtest_report.json",
    )


if __name__ == "__main__":
    import sys

    period = sys.argv[1] if len(sys.argv) > 1 else "6mo"
    run_backtest_and_report(period=period)
