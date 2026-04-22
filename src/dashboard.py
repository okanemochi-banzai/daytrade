"""
警告バナー + 日経方針 + 為替コモディティ + セクター連動 + キリバン のHTMLダッシュボード
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def format_jpy(n: float) -> str:
    return f"¥{n:,.0f}"


# ----- 警告バナー -----

def render_warnings_banner(warnings: list[dict]) -> str:
    if not warnings:
        return ""

    items = ""
    for w in warnings:
        sev = w["severity"]
        if sev == "high":
            border_color = "var(--short)"
            bg_color = "rgba(239, 68, 68, 0.08)"
            badge_color = "var(--short)"
        elif sev == "medium":
            border_color = "var(--accent)"
            bg_color = "rgba(251, 191, 36, 0.08)"
            badge_color = "var(--accent)"
        else:
            border_color = "var(--muted)"
            bg_color = "rgba(107, 114, 128, 0.08)"
            badge_color = "var(--muted)"

        items += f"""
        <div class="warning-item" style="border-left-color: {border_color}; background: {bg_color};">
          <div class="warning-header">
            <span style="color: {badge_color}; font-weight: 600;">{w['label']}</span>
          </div>
          <div class="warning-message">{w['message']}</div>
          <div class="warning-action">→ {w['action']}</div>
        </div>
        """
    return f"""
    <section>
      <div class="warnings-wrap">
        {items}
      </div>
    </section>
    """


# ----- 日経方針カード -----

def render_direction_verdict(direction_signal: dict) -> str:
    verdict = direction_signal["verdict"]
    label = direction_signal["verdict_label"]
    confidence = direction_signal["confidence"]

    if verdict == "buy_bias":
        bg = "rgba(16, 185, 129, 0.15)"
        color = "var(--long)"
        icon = "📈"
    elif verdict == "sell_bias":
        bg = "rgba(239, 68, 68, 0.15)"
        color = "var(--short)"
        icon = "📉"
    else:
        bg = "rgba(107, 114, 128, 0.15)"
        color = "var(--neutral)"
        icon = "⏸️"

    conf_text = {"high": "確度:高", "medium": "確度:中", "low": "確度:低"}.get(confidence, "")

    return f"""
    <div style="background: {bg}; color: {color}; padding: 16px 20px; border-radius: 12px; display: inline-flex; align-items: center; gap: 12px;">
      <div style="font-size: 32px;">{icon}</div>
      <div>
        <div style="font-size: 24px; font-weight: 700;">{label}</div>
        <div style="font-size: 12px; opacity: 0.8; margin-top: 2px;">{conf_text}</div>
      </div>
    </div>
    """


def render_us_indices_row(indices: list[dict]) -> str:
    items = ""
    for idx in indices:
        pct = idx["change_pct"]
        if idx["direction"] == "bullish":
            color = "var(--long)"
        elif idx["direction"] == "bearish":
            color = "var(--short)"
        else:
            color = "var(--muted)"
        items += f"""
        <div class="us-idx-item">
          <div class="us-idx-name">{idx['name']}</div>
          <div class="us-idx-pct" style="color: {color};">{pct:+.2f}%</div>
        </div>
        """
    return items


# ----- 為替・コモディティカード -----

def render_market_context(ctx: dict) -> str:
    items_html = ""
    for item in ctx["items"]:
        direction = item["direction"]
        if direction == "up":
            color = "var(--long)"
            arrow = "▲"
        elif direction == "down":
            color = "var(--short)"
            arrow = "▼"
        else:
            color = "var(--muted)"
            arrow = "━"

        if item["name"] == "ドル円":
            price_str = f"{item['current']:.2f}"
        elif item["name"] == "ゴールド":
            price_str = f"${item['current']:,.1f}"
        else:
            price_str = f"${item['current']:,.2f}"

        items_html += f"""
        <div class="fx-item">
          <div class="fx-header">
            <span class="fx-name">{item['name']}</span>
            <span class="fx-symbol">{item['symbol']}</span>
          </div>
          <div class="fx-price-row">
            <span class="fx-price">{price_str}</span>
            <span class="fx-change" style="color: {color};">{arrow} {item['change_pct']:+.2f}%</span>
          </div>
          <div class="fx-interpretation">{item['interpretation']}</div>
        </div>
        """

    combined_html = ""
    if ctx.get("combined_note"):
        combined_html = f"""
        <div class="fx-combined">
          {ctx['combined_note']}
        </div>
        """

    return f"""
    <section>
      <h2 class="section-title">💱 参考: 為替・コモディティ</h2>
      <div class="fx-grid">
        {items_html}
      </div>
      {combined_html}
    </section>
    """


# ----- セクターカード -----

def render_sector_card(sig: dict) -> str:
    direction = sig["direction"]
    strength = sig["signal_strength"]
    avg = sig["us_avg_change_pct"]

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

    corr_badges = {
        "high": '<span class="corr" title="強連動">🔗🔗🔗</span>',
        "medium": '<span class="corr" title="中連動">🔗🔗</span>',
        "low": '<span class="corr" title="弱連動">🔗</span>',
    }
    corr_badge = corr_badges.get(sig["correlation_strength"], "")

    bar_width = min(abs(avg) / 3.0 * 100, 100)
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


def render_dashboard(
    warnings: list[dict],
    market_context: dict,
    direction_signal: dict,
    kiriban_signal: dict,
    market: dict,
    sector_signals: list[dict],
    output_path: Path,
) -> None:
    """HTMLダッシュボードを生成してファイルに書き出す。"""
    kiriban = kiriban_signal["kiriban_bands"]
    round_levels = kiriban_signal["round_number_levels"]
    hivol = kiriban_signal["high_volatility"]

    band_rows = ""
    for key in ["+1500", "+1000", "+500", "-500", "-1000", "-1500"]:
        price = kiriban["bands"][key]
        label_class = "band-upper" if key.startswith("+") else "band-lower"
        band_rows += f"""
        <tr class="{label_class}">
          <td>前日比 {key}</td>
          <td class="price">{format_jpy(price)}</td>
        </tr>"""

    sector_cards_html = "".join(render_sector_card(s) for s in sector_signals)

    direction_verdict_html = render_direction_verdict(direction_signal)
    us_indices_html = render_us_indices_row(direction_signal["us_indices"])
    reasons_html = "".join(f"<li>{r}</li>" for r in direction_signal["reasons"])

    warnings_html = render_warnings_banner(warnings)
    market_context_html = render_market_context(market_context)

    futures_diff = direction_signal["futures_diff"]
    futures_diff_color = (
        "var(--long)" if futures_diff >= 200
        else ("var(--short)" if futures_diff <= -200 else "var(--muted)")
    )

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
  header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; flex-wrap: wrap; gap: 8px; }}
  h1 {{ margin: 0; font-size: 20px; font-weight: 600; }}
  .header-right {{ text-align: right; }}
  .timestamp {{ color: var(--muted); font-size: 13px; }}
  .report-link {{ color: var(--accent); text-decoration: none; font-size: 13px; }}
  .report-link:hover {{ text-decoration: underline; }}

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

  /* 警告バナー */
  .warnings-wrap {{ display: flex; flex-direction: column; gap: 10px; }}
  .warning-item {{
    background: var(--panel);
    border-left: 4px solid var(--accent);
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
  }}
  .warning-header {{ font-size: 15px; margin-bottom: 4px; }}
  .warning-message {{ font-size: 13px; color: var(--text); margin: 4px 0; }}
  .warning-action {{ font-size: 12px; color: var(--muted); margin-top: 6px; }}

  /* 日経方針 */
  .direction-card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }}
  .direction-meta {{ margin-top: 16px; display: flex; gap: 20px; flex-wrap: wrap; }}
  .direction-meta-item {{ flex: 1; min-width: 200px; }}
  .direction-meta-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; }}
  .us-indices {{ display: flex; gap: 16px; margin-top: 6px; }}
  .us-idx-item {{ flex: 1; text-align: center; padding: 8px; background: var(--panel-2); border-radius: 6px; }}
  .us-idx-name {{ font-size: 11px; color: var(--muted); }}
  .us-idx-pct {{ font-size: 16px; font-weight: 700; font-variant-numeric: tabular-nums; margin-top: 2px; }}
  .futures-value {{ font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; margin-top: 6px; }}
  .sub {{ color: var(--muted); font-size: 14px; }}
  .reasons-list {{ margin-top: 16px; padding: 14px 16px; background: var(--panel-2); border-left: 3px solid var(--accent); border-radius: 0 8px 8px 0; }}
  .reasons-list ul {{ margin: 0; padding-left: 18px; font-size: 13px; }}
  .reasons-list li {{ margin: 4px 0; }}
  .time-nodes-note {{
    margin-top: 12px;
    padding: 10px 14px;
    background: var(--panel-2);
    border-radius: 8px;
    font-size: 12px;
    color: var(--muted);
    border: 1px dashed var(--border);
  }}
  .time-nodes-note b {{ color: var(--accent); }}

  /* 為替・コモディティ */
  .fx-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }}
  .fx-item {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
  }}
  .fx-header {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .fx-name {{ font-weight: 600; font-size: 14px; }}
  .fx-symbol {{ font-size: 11px; color: var(--muted); }}
  .fx-price-row {{ display: flex; justify-content: space-between; align-items: baseline; margin: 6px 0; }}
  .fx-price {{ font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .fx-change {{ font-size: 14px; font-weight: 600; font-variant-numeric: tabular-nums; }}
  .fx-interpretation {{ font-size: 12px; color: var(--muted); margin-top: 6px; border-top: 1px dashed var(--border); padding-top: 6px; }}
  .fx-combined {{
    margin-top: 12px;
    padding: 10px 14px;
    background: rgba(251, 191, 36, 0.1);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    font-size: 13px;
  }}

  /* キリバン */
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }}
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
    font-size: 13px;
  }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
  .card h2 {{ margin: 0 0 12px 0; font-size: 14px; font-weight: 500; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; }}
  .footer-note {{
    margin-top: 32px; padding: 16px; background: var(--panel);
    border-radius: 8px; font-size: 12px; color: var(--muted); border: 1px solid var(--border);
  }}

  /* セクターカード */
  .sector-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }}
  .sector-card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }}
  .sector-header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }}
  .sector-title {{ font-size: 15px; }}
  .sector-avg {{ font-size: 18px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .dir-bullish {{ color: var(--long); }}
  .dir-bearish {{ color: var(--short); }}
  .dir-neutral {{ color: var(--neutral); }}
  .corr {{ font-size: 10px; margin-left: 4px; opacity: 0.7; }}
  .sector-bar-container {{ position: relative; height: 6px; background: var(--panel-2); border-radius: 3px; margin: 8px 0 12px 0; overflow: hidden; }}
  .sector-bar-center {{ position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: var(--border); }}
  .sector-bar {{ position: absolute; top: 0; bottom: 0; border-radius: 3px; }}
  .bar-bullish {{ background: var(--long); }}
  .bar-bearish {{ background: var(--short); }}
  .bar-neutral {{ background: var(--neutral); }}
  .sector-detail {{ font-size: 12px; color: var(--muted); line-height: 1.7; }}
  .sector-detail .sector-jp-stocks {{ color: var(--text); }}
  .sector-detail .sector-action {{ margin-top: 4px; font-size: 13px; color: var(--text); }}
  .sector-note {{ margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border); font-size: 11px; color: var(--muted); line-height: 1.5; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>📊 Daytrade Signal Board</h1>
    <div class="header-right">
      <div class="timestamp">Updated: {datetime.fromisoformat(market['timestamp']).strftime('%Y-%m-%d %H:%M JST')}</div>
      <a href="./backtest_report.html" class="report-link">🧪 バックテスト検証レポート →</a>
    </div>
  </header>

  {warnings_html}

  <!-- 本日の日経デイトレ方針 -->
  <section>
    <div class="direction-card">
      <h2 style="margin: 0 0 14px 0; font-size: 14px; font-weight: 500; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em;">
        本日の日経デイトレ方針
      </h2>
      {direction_verdict_html}

      <div class="direction-meta">
        <div class="direction-meta-item">
          <div class="direction-meta-label">前日米国市場</div>
          <div class="us-indices">
            {us_indices_html}
          </div>
        </div>
        <div class="direction-meta-item">
          <div class="direction-meta-label">日経先物 現対</div>
          <div class="futures-value" style="color: {futures_diff_color};">{futures_diff:+,.0f}円</div>
          <div class="sub" style="font-size: 12px;">
            先物: {format_jpy(market['nikkei_futures']['price'])} / 現物終値: {format_jpy(market['nikkei']['prev_close'])}
          </div>
        </div>
      </div>

      <div class="reasons-list">
        <ul>{reasons_html}</ul>
      </div>

      <div class="time-nodes-note">
        💡 <b>時間節目</b>: 9:40・10:00（前場トレ転）／12:30（後場寄り）／14:00・14:30（後場トレ転）
        で方向転換・手仕舞いが発生しやすい。ただし相場に大変動あるほど時間節目も貫通する点に留意。
      </div>
    </div>
  </section>

  {market_context_html}

  <!-- 米→日セクター連動予測 -->
  <section>
    <h2 class="section-title">🔁 米→日セクター連動予測</h2>
    <div class="sector-grid">
      {sector_cards_html}
    </div>
    <div class="rationale" style="margin-top: 16px;">
      連動強度: 🔗🔗🔗 = 強 / 🔗🔗 = 中 / 🔗 = 弱。
      しきい値: ±1.5%以上=強シグナル / ±0.5〜1.5%=弱シグナル / それ未満=様子見。
    </div>
  </section>

  <!-- キリバン水準 -->
  <section>
    <h2 class="section-title">📐 キリバン水準（参考）</h2>
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
          丸い数字は常にレジサポ候補。「買い」の日は下降トレンドから節目タッチで買い、
          「売り」の日は上昇トレンドから節目タッチで売り。
        </div>
      </div>
    </div>
  </section>

  <div class="footer-note">
    <b>⚠️ ディスクレーマー</b>:
    これは個人研究用のシグナルボードです。投資判断は自己責任で。
    全ての判定はPDFサロン記事から抽出した経験則に基づく仮説であり、
    統計的有意性は自分でバックテストレポートで検証してください。
  </div>
</div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {output_path}")
