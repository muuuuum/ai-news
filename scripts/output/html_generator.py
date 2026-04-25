#!/usr/bin/env python3
"""
HTML生成モジュール
収集済みJSONデータからindex.htmlを更新する

既存のindex.htmlのCSS・構造をベースに、
ニュースコンテンツ部分のみを最新データで置き換える。
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, PROJECT_ROOT

TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "index.html")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "index.html")

# カテゴリ → グラデーション
CATEGORY_GRADIENTS = {
    "model_research": ("tag-model", "#1e1b4b", "#312e81", "🧠"),
    "agent_ai":       ("tag-agent", "#14532d", "#166534", "🤖"),
    "business":       ("tag-biz",   "#1e3a5f", "#1d4ed8", "📊"),
    "security":       ("tag-sec",   "#7f1d1d", "#991b1b", "🔒"),
    "startup":        ("tag-startup", "#134e4a", "#0d9488", "🚀"),
}


def _escape_html(text: str) -> str:
    """HTMLエスケープ（<b>タグは許可）"""
    # まず<b>と</b>を退避
    text = text.replace("<b>", "{{B}}").replace("</b>", "{{/B}}")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("{{B}}", "<b>").replace("{{/B}}", "</b>")
    return text


def _format_date(date_str: str) -> str:
    """日付文字列を YYYY.MM.DD 形式に"""
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y.%m.%d")
    except Exception:
        return date_str


def generate_html(date_str: str = None):
    """JSONデータからindex.htmlを生成する"""
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    if not date_str:
        date_str = now.strftime("%Y-%m-%d")

    # JSONデータ読み込み
    reports_path = os.path.join(DATA_DIR, "reports.json")
    with open(reports_path, "r", encoding="utf-8") as f:
        reports = json.load(f)

    day_report = reports.get("reports", {}).get(date_str)
    if not day_report:
        print(f"[HTML] {date_str} のデータが見つかりません")
        return

    articles = day_report["articles"]
    if not articles:
        print("[HTML] 記事が0件のためスキップ")
        return

    # 既存のindex.htmlを読み込み
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # 日付フォーマット
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    date_display = f"{dt.year}年{dt.month}月{dt.day}日（{weekdays[dt.weekday()]}）"

    # --- ヘッダー日付を更新 ---
    html = re.sub(
        r'<div class="header-date">[^<]*</div>',
        f'<div class="header-date">{date_display}</div>',
        html
    )

    # --- ティッカーを更新 ---
    ticker_items = ""
    for art in articles[:4]:
        title_ja = _escape_html(art.get("title_ja", art["title"]))
        ticker_items += f'  <span class="ticker-badge">BREAKING</span><span class="ticker-text">{title_ja}</span>\n'
    # 2回繰り返す（スクロールアニメーション用）
    ticker_html = ticker_items + ticker_items

    html = re.sub(
        r'(<div class="ticker"><div class="ticker-inner">)\s*.*?\s*(</div></div>)',
        rf'\1\n{ticker_html}\2',
        html,
        flags=re.DOTALL
    )

    # --- メインコンテンツを生成 ---
    hero = articles[0]  # トップニュース
    pickups = articles[1:5]  # ピックアップ4件
    rest = articles[5:]  # 残り

    # カテゴリ別に分類
    by_category = {}
    for art in rest:
        cat = art.get("category", "model_research")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(art)

    main_html = _build_hero(hero)
    main_html += _build_pickups(pickups)

    for cat_id, cat_articles in by_category.items():
        main_html += _build_category_section(cat_id, cat_articles)

    main_html += _build_sources(articles)

    # --- サイドバーを生成 ---
    sidebar_html = _build_sidebar(articles, date_display)

    # --- メインコンテンツ領域を置換 ---
    # <main>...</main> を丸ごと置換
    html = re.sub(
        r'<main>.*?</main>',
        f'<main>\n{main_html}\n</main>',
        html,
        flags=re.DOTALL
    )

    # <aside class="sidebar">...</aside> を丸ごと置換
    html = re.sub(
        r'<aside class="sidebar">.*?</aside>',
        f'<aside class="sidebar">\n{sidebar_html}\n</aside>',
        html,
        flags=re.DOTALL
    )

    # --- フッター更新日時 ---
    update_time = now.strftime("%Y年%m月%d日 %H:%M JST")
    html = re.sub(
        r'最終更新:.*?</span>',
        f'最終更新: {update_time}</span>',
        html
    )

    # 書き出し
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[HTML] index.html 更新完了 ({len(articles)}件)")


def _build_hero(art: dict) -> str:
    tag_class = art.get("tag_class", "tag-model")
    cat_label = art.get("category_label", "MODEL")
    title_ja = _escape_html(art.get("title_ja", art["title"]))
    summary_ja = _escape_html(art.get("summary_ja", ""))
    cat = art.get("category", "model_research")
    grad = CATEGORY_GRADIENTS.get(cat, CATEGORY_GRADIENTS["model_research"])
    g1, g2 = grad[1], grad[2]
    emoji = grad[3]

    sources_html = ""
    for src in art.get("sources", []):
        name = _escape_html(src["name"])
        url = src["url"]
        sources_html += f'<a class="src-link" href="{url}" target="_blank" onclick="event.stopPropagation()">{name}</a>\n'

    pub = _format_date(art.get("published", ""))

    return f'''
  <div class="sec">
    <div class="sec-header"><div class="sec-bar"></div><div class="sec-title">TOP STORY</div></div>
    <div class="hero">
      <div class="hero-visual">
        <svg viewBox="0 0 600 340" xmlns="http://www.w3.org/2000/svg">
          <defs><linearGradient id="g1" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{g1}"/><stop offset="100%" stop-color="{g2}"/></linearGradient></defs>
          <rect fill="url(#g1)" width="600" height="340"/>
          <text x="300" y="170" text-anchor="middle" font-size="60" opacity=".15">{emoji}</text>
        </svg>
      </div>
      <div class="hero-content">
        <div class="hero-tag {tag_class}">{cat_label.upper()}</div>
        <div class="hero-title">{title_ja}</div>
        <div class="hero-desc">{summary_ja}</div>
        <div class="hero-meta">
          {sources_html}
          <span class="hero-meta-dot"></span><span>{pub}</span>
        </div>
      </div>
    </div>
  </div>
'''


def _build_pickups(articles: list) -> str:
    if not articles:
        return ""

    cards = ""
    for i, art in enumerate(articles):
        tag_class = art.get("tag_class", "tag-model")
        cat_label = art.get("category_label", "MODEL")
        title_ja = _escape_html(art.get("title_ja", art["title"]))
        cat = art.get("category", "model_research")
        grad = CATEGORY_GRADIENTS.get(cat, CATEGORY_GRADIENTS["model_research"])
        g1, g2, emoji = grad[1], grad[2], grad[3]
        src_name = art["sources"][0]["name"] if art.get("sources") else ""
        pub = _format_date(art.get("published", ""))

        cards += f'''
      <div class="pickup-card">
        <div class="pickup-thumb"><svg viewBox="0 0 300 120"><defs><linearGradient id="p{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{g1}"/><stop offset="100%" stop-color="{g2}"/></linearGradient></defs><rect fill="url(#p{i})" width="300" height="120"/><text x="150" y="68" text-anchor="middle" font-size="36" opacity=".2">{emoji}</text></svg></div>
        <div class="pickup-body"><span class="pickup-tag {tag_class}">{cat_label.upper()}</span><div class="pickup-title">{title_ja}</div><div class="pickup-meta"><span>{_escape_html(src_name)}</span><span>{pub}</span></div></div>
      </div>'''

    return f'''
  <div class="sec">
    <div class="sec-header"><div class="sec-bar"></div><div class="sec-title">PICKUP</div></div>
    <div class="pickup-grid">{cards}
    </div>
  </div>
'''


def _build_category_section(cat_id: str, articles: list) -> str:
    grad = CATEGORY_GRADIENTS.get(cat_id, CATEGORY_GRADIENTS["model_research"])
    tag_class, g1, g2, emoji = grad
    cat_label = articles[0].get("category_label", "")
    bar_colors = {
        "model_research": "var(--purple)", "agent_ai": "var(--green)",
        "business": "var(--blue)", "security": "var(--accent)", "startup": "var(--teal)",
    }
    bar_color = bar_colors.get(cat_id, "var(--accent)")

    cards = ""
    for art in articles:
        title_ja = _escape_html(art.get("title_ja", art["title"]))
        summary_ja = _escape_html(art.get("summary_ja", ""))
        src_name = art["sources"][0]["name"] if art.get("sources") else ""
        pub = _format_date(art.get("published", ""))

        cards += f'''
    <div class="card-h">
      <div class="card-h-thumb"><svg viewBox="0 0 220 140"><defs><linearGradient id="ch{hash(title_ja) % 10000}" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{g1}"/><stop offset="100%" stop-color="{g2}"/></linearGradient></defs><rect fill="url(#ch{hash(title_ja) % 10000})" width="220" height="140"/><text x="110" y="78" text-anchor="middle" font-size="36" opacity=".15">{emoji}</text></svg></div>
      <div class="card-h-body">
        <div class="card-h-tag {tag_class}">{cat_label.upper()}</div>
        <div class="card-h-title">{title_ja}</div>
        <div class="card-h-desc">{summary_ja[:120]}</div>
        <div class="card-h-meta"><span>{_escape_html(src_name)}</span><span class="card-h-meta-dot"></span><span>{pub}</span></div>
      </div>
    </div>'''

    return f'''
  <div class="sec">
    <div class="sec-header"><div class="sec-bar" style="background:{bar_color}"></div><div class="sec-title">{emoji} {cat_label}</div></div>
    <div class="card-list">{cards}
    </div>
  </div>
'''


def _build_sources(articles: list) -> str:
    sources = set()
    for art in articles:
        for src in art.get("sources", []):
            sources.add(src["name"])

    chips = "".join(f'<span class="source-chip">{_escape_html(s)}</span>' for s in sorted(sources))

    return f'''
  <div class="sources">
    <div class="sources-title">📎 本日の情報源</div>
    <div class="sources-list">{chips}</div>
  </div>
'''


def _build_sidebar(articles: list, date_display: str) -> str:
    # カテゴリ別件数
    cats = {}
    for art in articles:
        cat = art.get("category_label", "不明")
        cats[cat] = cats.get(cat, 0) + 1

    stats_html = ""
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        stats_html += f'<div class="sb-stat"><span class="sb-stat-name">{cat}</span><span class="sb-stat-val">{count}件</span></div>\n'

    # トップ5ランキング
    rank_html = ""
    for i, art in enumerate(articles[:5]):
        title_ja = _escape_html(art.get("title_ja", art["title"]))[:40]
        src = art["sources"][0]["name"] if art.get("sources") else ""
        rank_class = ["r1", "r2", "r3", "other", "other"][i]
        rank_html += f'''<div class="rank-item"><div class="rank-num {rank_class}">{i+1}</div><div><div class="rank-text">{title_ja}</div><div style="font-size:10.5px;color:var(--muted2)">{_escape_html(src)}</div></div></div>\n'''

    return f'''
    <div class="sb-box">
      <div class="sb-title">📊 本日の数字</div>
      <div class="sb-stats">
        <div class="sb-stat"><span class="sb-stat-name">記事数</span><span class="sb-stat-val">{len(articles)}件</span></div>
        <div class="sb-stat"><span class="sb-stat-name">情報源数</span><span class="sb-stat-val">{len(set(s["name"] for a in articles for s in a.get("sources", [])))}サイト</span></div>
        {stats_html}
      </div>
    </div>
    <div class="sb-box">
      <div class="sb-title">🏆 注目ランキング</div>
      {rank_html}
    </div>
'''


if __name__ == "__main__":
    generate_html()
