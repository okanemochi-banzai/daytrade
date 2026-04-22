"""
キリバンシグナル + 米→日セクター連動 HTMLダッシュボード生成
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def format_jpy(n: float) -> str:
    return f"¥{n:,.0f}"


def render_sayatori_badge(direction: str) -> str:
    if direction == "long":
        return '<span class="badge badge-long">鞘取りロング</span>'
    if direction == "short":
        return '<span class="badge badge-short">鞘取りショート</span>'
    return '<span class="badge badge-neutral">様子見</span>'


def render_sector_card(sig: dict) -> str:
    """1セクターぶんのカードをHTMLで返す"""
    direction = sig["direction"]
    strength = sig["signal_strength"]
    avg = sig["us_avg_change_pct"]

    # 色分け
    if direction == "bullish":
        bar_class = "bar-bullish"
        dir_class = "dir-bullish"
        dir_text = "買い" if strength == "strong" else "やや買い"
        arrow = "▲"
    elif direction == "bearish":
        bar_class = "bar-bearish"
        dir_class = "dir-bearish"
        dir_text = "売り" if strength == "strong" else "やや売り"
        arrow = "▼"
    else:
        bar_class = "bar-neutral"
        dir_class = "dir-neutral"
        dir_text = "様子見"
        arrow = "━"

    # 連動強度のマーク
    corr_badges = {
        "high": '<span class="corr corr-high" title="PDFで繰り返し言及される強い連動">🔗🔗🔗</span>',
        "medium": '<span class="corr corr-med" title="条件次第で連動">🔗🔗</span>',
        "low": '<span class="corr corr-low" title="連動は弱め">🔗</span>',
    }
    corr_badge = corr_badges.get(sig["correlation_strength"], "")

    # バーの幅（±3%を100%として）
    bar_width = min(abs(avg) / 3.0 * 100, 100)
    # バーの方向オフセット
    bar_offset = 50 if direction == "bullish" else (50 - bar_width if direction == "bearish" else 50)
    bar_display_width = bar_width if direction != "neutral" else 0

    jp_stocks_text = "、".join(sig["jp_stocks"][:4])

    return f"""
    <div class="sector-card">
      <div class="sector-header">
        <div class="sector-title">
          {arrow} <b>{sig['sector_name']}</b> {corr_badge}
        </div>
        <div class="sector-avg {dir_class}">
          {avg:+.2f}%
        </div>
      </div>
      <div class="sector-bar-container">
        <div class="sector-bar-center"></div>
        <div class="sector-bar {bar_class}" style="width: {bar_display_width}%; left: {bar_offset}%;"></div>
      </div>
      <div class="sector-detail">
        <div class="sector-us-label">米: {sig['us_label']}</div>
        <div class="sector-jp-stocks">日: {jp_stocks_text}</div>
        <div class="sector-action">→ <b class="{dir_class}">{dir_text}目線</b></div>
      </div>
      <div class="sector-note">{sig['note']}</div>
    </div>
    """


def render_dashboard(signal: dict, market: dict, sector_signals: list[dict], output_path: Path) -> None:
    """HTMLダッシュボードを生成してファイルに書き出す。"""
    kiriban = signal["kiriban_bands"]
    sayatori = signal["sayatori_signal"]
    round_levels = signal["round_number_levels"]
    hivol = signal["high_volatility"]

    band_rows = ""
    for key in ["+1500", "+1000", "+500", "-500", "-1000", "-1500"]:
        price = kiriban["bands"][key]
        label_class = "band-upper" if key.startswith("+") else "band-lower"
        band_rows += f"""
        <tr class="{label_class}">
          <td>前日比 {key}</td>
          <td class="price">{format_jpy(price)}</td>
        </tr>"""

    sayatori_badge = render_sayatori_badge(sayatori["direction"])
    hivol_label = "🔥 ハイボラ" if hivol else "😴 通常ボラ"
    hivol_color = "#ef4444" if hivol else "#6b7280"

    us_nasdaq = market["us_markets"]["nasdaq_change_pct"]
    us_sox = market["us_markets"]["sox_change_pct"]

    # セクターカード一覧
    sector_cards_html = "".join(render_sector_card(s) for s in sector_signals)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daytrade Signal Board</title>
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
  header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }}
  h1 {{ margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.02em; }}
  .timestamp {{ color: var(--muted); font-size: 13px; }}
  section {{ margin-bottom: 28px; }}
  section > h2.section-title {{
    font-size: 16px;
    font-weight: 600;
    color: var(--accent);
    margin: 0 0 14px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
    letter-spacing: 0.02em;
  }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
  }}
  .card h2 {{ margin: 0 0 12px 0; font-size: 14px; font-weight: 500; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; }}
  .big-number {{ font-size: 32px; font-weight: 700; margin: 8px 0; font-variant-numeric: tabular-nums; }}
  .sub {{ color: var(--muted); font-size: 14px; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 13px; font-weight: 600; }}
  .badge-long {{ background: rgba(16, 185, 129, 0.15); color: var(--long); }}
  .badge-short {{ background: rgba(239, 68, 68, 0.15); color: var(--short); }}
  .badge-neutral {{ background: rgba(107, 114, 128, 0.15); color: var(--neutral); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 500; }}
  .price {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }}
  .band-upper td {{ color: var(--short); }}
  .band-lower td {{ color: var(--long); }}
  .prev-close-row td {{ color: var(--accent); font-weight: 700; border-top: 2px solid var(--accent); border-bottom: 2px solid var(--accent); }}
  .rationale {{
    background: var(--panel-2);
    border-left: 3px solid var(--accent);
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin-top: 12px;
    font-size: 14px;
  }}
  .footer-note {{
    margin-top: 32px;
    padding: 16px;
    background: var(--panel);
    border-radius: 8px;
    font-size: 12px;
    color: var(--muted);
    border: 1px solid var(--border);
  }}
  .us-market {{ display: flex; gap: 16px; }}
  .us-market .item {{ flex: 1; }}
  .pct-pos {{ color: var(--long); }}
  .pct-neg {{ color: var(--short); }}

  /* セクターカード */
  .sector-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 14px;
  }}
  .sector-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
  }}
  .sector-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 8px;
  }}
  .sector-title {{ font-size: 15px; }}
  .sector-avg {{ font-size: 18px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .dir-bullish {{ color: var(--long); }}
  .dir-bearish {{ color: var(--short); }}
  .dir-neutral {{ color: var(--neutral); }}
  .corr {{ font-size: 10px; margin-left: 4px; opacity: 0.7; }}
  .sector-bar-container {{
    position: relative;
    height: 6px;
    background: var(--panel-2);
    border-radius: 3px;
    margin: 8px 0 12px 0;
    overflow: hidden;
  }}
  .sector-bar-center {{
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--border);
  }}
  .sector-bar {{
    position: absolute;
    top: 0;
    bottom: 0;
    border-radius: 3px;
  }}
  .bar-bullish {{ background: var(--long); }}
  .bar-bearish {{ background: var(--short); }}
  .bar-neutral {{ background: var(--neutral); }}
  .sector-detail {{
    font-size: 12px;
    color: var(--muted);
    line-height: 1.7;
  }}
  .sector-detail .sector-us-label {{ color: var(--muted); }}
  .sector-detail .sector-jp-stocks {{ color: var(--text); }}
  .sector-detail .sector-action {{ margin-top: 4px; font-size: 13px; color: var(--text); }}
  .sector-note {{
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed var(--border);
    font-size: 11px;
    color: var(--muted);
    line-height: 1.5;
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>📊 Daytrade Signal Board</h1>
    <div style="text-align: right;">
      <div class="timestamp">Updated: {datetime.fromisoformat(market['timestamp']).strftime('%Y-%m-%d %H:%M JST')}</div>
      <a href="./backtest_report.html" style="color: #fbbf24; text-decoration: none; font-size: 13px;">🧪 バックテスト検証レポート →</a>
    </div>
  </header>

  <!-- 朝一鞘取りシグナル -->
  <section>
    <div class="card">
      <h2>朝一先物鞘取りシグナル</h2>
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
        <div>
          <div class="big-number">{sayatori_badge}</div>
          <div class="sub">
            日経先物: <b>{format_jpy(sayatori['futures_price'])}</b> /
            現物: <b>{format_jpy(sayatori['spot_price'])}</b>
          </div>
          <div class="sub" style="font-size: 16px; margin-top: 4px;">
            現対: <b style="color: {'var(--accent)' if hivol else 'var(--muted)'};">{sayatori['diff']:+,.0f}円</b>
            <span style="color: {hivol_color}; margin-left: 8px;">{hivol_label}</span>
          </div>
        </div>
      </div>
      <div class="rationale">{sayatori['rationale']}</div>
    </div>
  </section>

  <!-- 米→日セクター連動予測 -->
  <section>
    <h2 class="section-title">🔁 米→日セクター連動予測（前日米騰落率ベース）</h2>
    <div class="sector-grid">
      {sector_cards_html}
    </div>
    <div class="rationale" style="margin-top: 16px;">
      連動強度: 🔗🔗🔗 = 強い / 🔗🔗 = 中程度 / 🔗 = 弱め（PDFサロン記事での言及頻度に基づく経験則）。
      しきい値: ±1.5%以上で「強いシグナル」、±0.5〜1.5%で「弱いシグナル」、それ未満は「様子見」。
    </div>
  </section>

  <!-- キリバン値幅とキリバン節目 -->
  <section>
    <h2 class="section-title">📐 キリバン水準</h2>
    <div class="grid">
      <div class="card">
        <h2>キリバン値幅（前日終値 ± N円）</h2>
        <table>
          <tbody>
            {band_rows}
            <tr class="prev-close-row">
              <td>前日終値</td>
              <td class="price">{format_jpy(kiriban['prev_close'])}</td>
            </tr>
          </tbody>
        </table>
        <div class="rationale" style="margin-top: 16px;">
          {"機能しやすい相場（ハイボラ）" if hivol else "通常ボラ時は効きにくい。参考値として"}。
          ±500/1000/1500円が天底・レジサポとして意識される水準。
        </div>
      </div>

      <div class="card">
        <h2>株価キリバン節目（{round_levels['step']:,}円単位）</h2>
        <table>
          <tbody>
            <tr class="band-upper">
              <td>レジスタンス</td>
              <td class="price">{format_jpy(round_levels['resistance'])}</td>
            </tr>
            <tr class="prev-close-row">
              <td>現在値</td>
              <td class="price">{format_jpy(round_levels['current_price'])}</td>
            </tr>
            <tr class="band-lower">
              <td>サポート</td>
              <td class="price">{format_jpy(round_levels['support'])}</td>
            </tr>
          </tbody>
        </table>
        <div class="rationale" style="margin-top: 16px;">
          丸い数字（0円で終わる水準）は常にレジサポ候補。軟調相場ほど機能しやすい。
        </div>
      </div>
    </div>
  </section>

  <!-- 米国市場と1570 -->
  <section>
    <h2 class="section-title">🌐 市場データ</h2>
    <div class="grid">
      <div class="card">
        <h2>前日米国市場（指数）</h2>
        <div class="us-market">
          <div class="item">
            <div class="sub">ナスダック</div>
            <div class="big-number" style="font-size: 24px;">
              <span class="{'pct-pos' if us_nasdaq >= 0 else 'pct-neg'}">{us_nasdaq:+.2f}%</span>
            </div>
          </div>
          <div class="item">
            <div class="sub">SOX指数</div>
            <div class="big-number" style="font-size: 24px;">
              <span class="{'pct-pos' if us_sox >= 0 else 'pct-neg'}">{us_sox:+.2f}%</span>
            </div>
          </div>
        </div>
        <div class="rationale" style="margin-top: 16px;">
          米日連動/非連動の判断材料。米上げに対して先物が追随してないなら「米強日弱」警戒。
        </div>
      </div>

      <div class="card">
        <h2>1570 日経レバETF</h2>
        <table>
          <tbody>
            <tr>
              <td>前日終値</td>
              <td class="price">{format_jpy(market['etf_1570']['prev_close'])}</td>
            </tr>
          </tbody>
        </table>
        <div class="rationale" style="margin-top: 16px;">
          ハイボラ時は1570が遅れて寄り付くことがあり、1570の寄り値が日経の天底を決めることも多い。
        </div>
      </div>
    </div>
  </section>

  <div class="footer-note">
    <b>⚠️ ディスクレーマー</b>:
    これは個人研究用のシグナルボードです。投資判断は自己責任で。
    セクター連動はPDFサロン記事からの経験則抽出であり、統計的有意性は自分でバックテストして検証してください。
    全ての関連性は過去のパターンに過ぎず、将来の値動きを保証するものではありません。
  </div>
</div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {output_path}")
