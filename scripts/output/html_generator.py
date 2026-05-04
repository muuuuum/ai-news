#!/usr/bin/env python3
"""
HTML生成モジュール v2 — リッチコンテンツ生成

旧版index.htmlの構造（モーダル・JS・リッチSVG・テーブル・チャート）を保持し、
記事コンテンツのみを差し替える。

方式:
  1. index.htmlのCSS・HTML構造・フッターはそのまま維持
  2. 記事データからGeminiでリッチなモーダル本文・統計を生成
  3. ティッカー、日付、メインコンテンツ、サイドバー、JSの記事データを差し替え
"""

import json
import os
import re
import hashlib
from datetime import datetime, timezone, timedelta

import requests

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, PROJECT_ROOT, GEMINI_API_KEY, GEMINI_MODEL
from output.image_generator import generate_images_for_articles

INDEX_PATH = os.path.join(PROJECT_ROOT, "index.html")

# 画像辞書（{article_id: web_path}）— generate_html() 実行中にセットされる
_IMAGE_MAP: dict = {}

# カテゴリ設定
CAT_CONFIG = {
    "model_research": {"tag": "MODEL", "tc": "tag-model", "label": "モデル・研究",
                        "bar_color": "var(--purple)", "grad": ("#1e1b4b", "#312e81"), "emoji": "🧠"},
    "agent_ai":       {"tag": "AGENT", "tc": "tag-agent", "label": "エージェントAI",
                        "bar_color": "var(--green)", "grad": ("#14532d", "#166534"), "emoji": "🤖"},
    "business":       {"tag": "BUSINESS", "tc": "tag-biz", "label": "ビジネス",
                        "bar_color": "var(--blue)", "grad": ("#1e3a5f", "#1d4ed8"), "emoji": "📊"},
    "security":       {"tag": "SECURITY", "tc": "tag-sec", "label": "セキュリティ",
                        "bar_color": "var(--accent)", "grad": ("#7f1d1d", "#991b1b"), "emoji": "🔒"},
    "startup":        {"tag": "STARTUP", "tc": "tag-startup", "label": "スタートアップ",
                        "bar_color": "var(--teal)", "grad": ("#134e4a", "#0d9488"), "emoji": "🚀"},
    "research_paper": {"tag": "PAPER", "tc": "tag-paper", "label": "研究論文",
                        "bar_color": "var(--orange)", "grad": ("#78350f", "#d97706"), "emoji": "📄"},
}


def _esc(text: str) -> str:
    """HTMLエスケープ（<b>タグは保持）"""
    text = text.replace("<b>", "{{B}}").replace("</b>", "{{/B}}")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "\\'").replace('"', '\\"')
    text = text.replace("{{B}}", "<b>").replace("{{/B}}", "</b>")
    return text


def _js_esc(text: str) -> str:
    """JavaScript文字列用エスケープ"""
    return text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def _fmt_date(date_str: str) -> str:
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y.%m.%d")
    except Exception:
        return date_str


def _fmt_date_ja(date_str: str) -> str:
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.year}年{dt.month}月{dt.day}日"
    except Exception:
        return date_str


def _article_id(art: dict) -> str:
    """記事のユニークID（JSオブジェクトのキー用）"""
    slug = re.sub(r'[^a-zA-Z0-9]', '', art.get("title", ""))[:20].lower()
    h = hashlib.md5(art.get("title", "").encode()).hexdigest()[:6]
    return f"a{h}"


def _make_svg(art: dict, width: int, height: int) -> str:
    """カテゴリに応じたSVGサムネイル（フォールバック）"""
    cat = art.get("category", "model_research")
    cfg = CAT_CONFIG.get(cat, CAT_CONFIG["model_research"])
    g1, g2 = cfg["grad"]
    emoji = cfg["emoji"]
    gid = f"g{_article_id(art)}"

    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{g1}"/><stop offset="100%" stop-color="{g2}"/>'
        f'</linearGradient></defs>'
        f'<rect fill="url(#{gid})" width="{width}" height="{height}"/>'
        f'<text x="{width//2}" y="{height//2+10}" text-anchor="middle" font-size="{min(width,height)//3}" opacity=".15">{emoji}</text>'
        f'</svg>'
    )


def _make_visual(art: dict, width: int, height: int) -> str:
    """画像があれば<img>タグ、なければSVGフォールバックを返す。"""
    aid = _article_id(art)
    img_path = _IMAGE_MAP.get(aid)
    if img_path:
        title = art.get("title_ja", art.get("title", "")).replace('"', "&quot;")
        return (
            f'<img src="/{img_path}" alt="{title}" loading="lazy" '
            f'style="width:100%;height:100%;object-fit:cover;display:block;" />'
        )
    return _make_svg(art, width, height)


def _generate_rich_content(articles: list) -> dict:
    """Geminiで各記事のリッチなモーダルコンテンツを生成。記事IDでキャッシュして再生成しない。"""
    if not GEMINI_API_KEY or not articles:
        return {}

    cache_path = os.path.join(DATA_DIR, "rich_content_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    # 既にキャッシュにある記事はスキップ
    needs_generation = [a for a in articles if _article_id(a) not in cache]
    print(f"[HTML] リッチコンテンツ: キャッシュ {len(articles) - len(needs_generation)}件 / 新規生成 {len(needs_generation)}件")

    if needs_generation:
        batch_size = 5
        for start in range(0, len(needs_generation), batch_size):
            batch = needs_generation[start:start + batch_size]
            batch_results = _generate_rich_batch(batch)
            cache.update(batch_results)
            print(f"  {min(start + batch_size, len(needs_generation))}/{len(needs_generation)}件完了")

        # キャッシュ保存
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    # 今回の記事分だけ返す
    return {_article_id(a): cache[_article_id(a)] for a in articles if _article_id(a) in cache}


def _generate_rich_batch(batch: list) -> dict:
    """5件まとめてリッチコンテンツ生成"""
    article_list = ""
    for i, a in enumerate(batch):
        article_list += f"""
---
記事{i}: {a.get('title_ja', a['title'])}
カテゴリ: {a.get('category_label', '')}
要約: {a.get('summary_ja', a.get('summary', ''))[:300]}
ソース: {', '.join(s['name'] for s in a.get('sources', []))}
"""

    prompt = f"""以下の{len(batch)}件のAIニュース記事について、ニュースサイトの記事詳細ページ用のリッチコンテンツを生成してください。

{article_list}

各記事について以下を生成:
1. body: 記事の詳細な本文HTML。以下の構成で:
   - 導入パラグラフ（<p class="modal-text">タグ。重要部分を<strong>で強調）
   - 小見出し（<h3 class="modal-subhead">）
   - 詳細パラグラフまたはリスト（<ul class="modal-list"><li>）
   - 影響・まとめパラグラフ
   全体で300〜500文字程度の日本語。

2. stats: 3つの重要な数字。各数字は value（短い表示値）と label（説明）。

JSON配列で回答。各要素:
{{
  "index": 番号,
  "body": "HTML文字列",
  "stats": [{{"value": "数値", "label": "説明"}}, ...]
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
    }

    try:
        resp = requests.post(url, json=payload, timeout=60)
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        items = json.loads(text)

        result = {}
        for item in items:
            idx = item.get("index", -1)
            if 0 <= idx < len(batch):
                aid = _article_id(batch[idx])
                result[aid] = {
                    "body": item.get("body", ""),
                    "stats": item.get("stats", []),
                }
        return result
    except Exception as e:
        print(f"  [WARN] リッチコンテンツ生成失敗: {e}")
        return {}


def generate_html(date_str: str = None):
    """JSONデータからindex.htmlを更新する"""
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    if not date_str:
        date_str = now.strftime("%Y-%m-%d")

    # データ読み込み
    reports_path = os.path.join(DATA_DIR, "reports.json")
    with open(reports_path, "r", encoding="utf-8") as f:
        reports = json.load(f)

    day_report = reports.get("reports", {}).get(date_str)
    if not day_report:
        print(f"[HTML] {date_str} のデータが見つかりません")
        return

    articles = day_report["articles"]
    if not articles:
        print("[HTML] 記事が0件")
        return

    # 最大40件に絞る
    articles = articles[:40]

    # 既存HTMLを読み込み
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # サムネイル画像生成（Gemini Image） — コスト制御のため上位N件のみ
    # IMAGE_GENERATION_LIMIT 環境変数で枚数を調整可能（デフォルト9件 = Hero+Pickup）
    global _IMAGE_MAP
    _IMAGE_MAP = generate_images_for_articles(articles)

    # リッチコンテンツ生成（Gemini） — SKIP_RICH=1 でAPI費用節約のためスキップ可
    if os.environ.get("SKIP_RICH") == "1":
        print("[HTML] SKIP_RICH=1 — リッチコンテンツ生成をスキップ")
        rich = {}
    else:
        rich = _generate_rich_content(articles)

    # 日付
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    date_display = f"{dt.year}年{dt.month}月{dt.day}日（{weekdays[dt.weekday()]}）"

    # === 1. ヘッダー日付 + アーカイブセレクタ ===
    html = re.sub(r'<div class="header-date">[^<]*</div>',
                  f'<div class="header-date">{date_display}</div>', html)

    # アーカイブセレクタを検索ボックスの隣に挿入
    archive_html = _build_archive_selector(reports.get("reports", {}), date_str)
    # 既存のセレクタがあれば差し替え、なければ search-box の前に挿入
    if 'class="archive-select"' in html:
        html = re.sub(r'<select class="archive-select"[^>]*>.*?</select>',
                       archive_html, html, count=1, flags=re.DOTALL)
    else:
        html = re.sub(r'(<div class="search-box">)',
                       f'{archive_html}\\1', html, count=1)

    # === 1b. ナビゲーション（カテゴリリンク化） ===
    nav_items = (
        '<div class="nav-item active" onclick="scrollToSec(\'top\')">トップ</div>'
        '<div class="nav-item" onclick="scrollToSec(\'sec-key-numbers\')">注目数字</div>'
        '<div class="nav-item" onclick="scrollToSec(\'sec-trends\')">トレンド</div>'
        '<div class="nav-item" onclick="scrollToSec(\'sec-model_research\')">モデル・研究</div>'
        '<div class="nav-item" onclick="scrollToSec(\'sec-agent_ai\')">エージェントAI</div>'
        '<div class="nav-item" onclick="scrollToSec(\'sec-business\')">ビジネス</div>'
        '<div class="nav-item" onclick="scrollToSec(\'sec-startup\')">スタートアップ</div>'
        '<div class="nav-item" onclick="scrollToSec(\'sec-security\')">セキュリティ</div>'
        '<div class="nav-item" onclick="scrollToSec(\'sec-timeline\')">タイムライン</div>'
    )
    html = re.sub(
        r'<div class="nav-inner">.*?</div></div>',
        f'<div class="nav-inner">{nav_items}</div></div>',
        html, count=1, flags=re.DOTALL
    )

    # Add CSS for new elements
    new_css = """
.hero-visual img,.pickup-thumb img,.card-h-thumb img,.card-v-thumb img,.modal-hero img{width:100%;height:100%;object-fit:cover;display:block;}
.archive-select{appearance:none;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 28px 6px 12px;font-size:13px;color:var(--text2);font-weight:600;cursor:pointer;font-family:inherit;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='%236b7280'%3E%3Cpath d='M8 11L3 6h10z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center;background-size:14px;transition:border-color .15s;}
.archive-select:hover{border-color:var(--muted2);}
.card-text-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;}
.card-text{background:var(--white);border:1px solid var(--border-light);border-left:3px solid var(--border);border-radius:8px;padding:16px 18px;cursor:pointer;transition:all .15s;display:flex;flex-direction:column;gap:8px;}
.card-text:hover{border-left-color:var(--accent);box-shadow:0 2px 12px rgba(0,0,0,.06);transform:translateX(2px);}
.card-text-tag{display:inline-block;font-size:10px;font-weight:800;padding:2px 8px;border-radius:3px;align-self:flex-start;letter-spacing:.04em;}
.card-text-title{font-size:14.5px;font-weight:700;line-height:1.55;color:var(--text);margin:0;}
.card-text-desc{font-size:12.5px;color:var(--muted);line-height:1.65;margin:0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.card-text-meta{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--muted2);font-weight:500;margin-top:auto;padding-top:6px;}
.card-text-meta-dot{width:3px;height:3px;border-radius:50%;background:var(--muted3);}
@media(max-width:640px){.card-text-grid{grid-template-columns:1fr;}}
.tag-paper{background:var(--orange-light);color:var(--orange);}
.card-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;}
.card-v{background:var(--white);border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04);cursor:pointer;transition:transform .15s,box-shadow .15s;}
.card-v:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.08);}
.card-v-thumb{width:100%;height:140px;overflow:hidden;}
.card-v-thumb svg{width:100%;height:100%;}
.card-v-body{padding:14px 16px 8px;}
.card-v-tag{display:inline-block;font-size:10px;font-weight:800;padding:2px 8px;border-radius:4px;margin-bottom:6px;}
.card-v-title{font-size:14px;font-weight:800;line-height:1.5;margin-bottom:6px;}
.card-v-desc{font-size:12px;color:var(--muted);line-height:1.6;}
.card-v-footer{display:flex;justify-content:space-between;padding:8px 16px 14px;font-size:11px;color:var(--muted2);}
"""
    html = html.replace('</style>', new_css + '</style>')

    # === 2. ティッカー ===
    ticker = ""
    for a in articles[:4]:
        t = a.get("title_ja", a["title"]).replace('"', '&quot;').replace("'", "&#39;")
        ticker += f'  <span class="ticker-badge">BREAKING</span><span class="ticker-text">{t}</span>\n'
    ticker_html = ticker + ticker  # 2回繰り返し
    html = re.sub(
        r'(<div class="ticker"><div class="ticker-inner">)\s*.*?\s*(</div></div>)',
        rf'\1\n{ticker_html}\2', html, flags=re.DOTALL
    )

    # === 3. メインコンテンツ ===
    hero = articles[0]
    pickups = articles[1:9]

    # カテゴリ分類（各カテゴリ最大6件）
    by_cat = {}
    for a in articles[9:]:
        cat = a.get("category", "model_research")
        by_cat.setdefault(cat, [])
        if len(by_cat[cat]) < 6:
            by_cat[cat].append(a)

    main = ""
    main += _hero_section(hero, rich)
    main += _pickup_section(pickups)
    main += _key_numbers_section(articles)
    main += _trending_topics_section(articles)
    for cat_id, cat_arts in by_cat.items():
        main += _category_section(cat_id, cat_arts)
    main += _timeline_section(articles)
    main += _sources_section(articles)

    html = re.sub(r'<main>.*?</main>', f'<main>\n{main}\n</main>', html, flags=re.DOTALL)

    # === 4. サイドバー ===
    sidebar = _sidebar(articles, date_display)
    html = re.sub(r'<aside class="sidebar">.*?</aside>',
                  f'<aside class="sidebar">\n{sidebar}\n</aside>', html, flags=re.DOTALL)

    # === 5. JavaScript記事データ（全記事分） ===
    js_data = _build_js_data(articles, rich)
    # const A={...}; を丸ごと差し替え
    html = re.sub(r'const A=\{.*?\};', js_data, html, flags=re.DOTALL)

    # === 6. フッター更新日時 ===
    update_time = now.strftime("%Y-%m-%d %H:%M")
    html = re.sub(r'最終更新:.*?</div>', f'最終更新: {update_time} ・ 毎朝 9:00 自動更新</div>', html)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    # アーカイブHTMLを保存（過去日として残す）
    archive_dir = os.path.join(PROJECT_ROOT, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    archive_path = os.path.join(archive_dir, f"{date_str}.html")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[HTML] index.html 更新完了（{len(articles)}件、リッチコンテンツ{len(rich)}件、アーカイブ: {archive_path}）")


# === セクション生成関数 ===

def _build_archive_selector(reports: dict, current_date: str) -> str:
    """過去日アーカイブのドロップダウンを生成。最新の日付から最大30件表示。"""
    dates = sorted([d for d in reports.keys() if reports[d].get("articles")], reverse=True)
    dates = dates[:30]

    weekdays = ["月", "火", "水", "木", "金", "土", "日"]

    options = ['<option value="">📅 アーカイブ</option>']
    for d in dates:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            wd = weekdays[dt.weekday()]
            label = f"{dt.month}月{dt.day}日（{wd}）"
        except Exception:
            label = d

        if d == current_date:
            label = f"{label} ← 表示中"
            url = "/"
            selected = " selected"
        else:
            url = f"/archive/{d}.html"
            selected = ""

        options.append(f'<option value="{url}"{selected}>{label}</option>')

    options_html = "".join(options)
    return (
        f'<select class="archive-select" '
        f'onchange="if(this.value)window.location.href=this.value">'
        f'{options_html}</select>'
    )


def _hero_section(art: dict, rich: dict) -> str:
    cat = art.get("category", "model_research")
    cfg = CAT_CONFIG.get(cat, CAT_CONFIG["model_research"])
    aid = _article_id(art)
    title_ja = art.get("title_ja", art["title"])
    summary_ja = art.get("summary_ja", "")
    svg = _make_visual(art, 600, 340)
    sources_html = ""
    for s in art.get("sources", []):
        sources_html += f'<a class="src-link" href="{s["url"]}" target="_blank" onclick="event.stopPropagation()">{s["name"]}</a>'
    pub = _fmt_date(art.get("published", ""))

    # 統計
    stats_html = ""
    r = rich.get(aid, {})
    if r.get("stats"):
        for st in r["stats"][:3]:
            stats_html += f'<div class="hero-stat"><div class="hero-stat-val" style="color:{cfg["bar_color"]}">{st["value"]}</div><div class="hero-stat-label">{st["label"]}</div></div>'
        stats_html = f'<div class="hero-stats">{stats_html}</div>'

    return f'''
  <div class="sec">
    <div class="sec-header"><div class="sec-bar"></div><div class="sec-title">TOP STORY</div></div>
    <div class="hero" onclick="openArticle('{aid}')">
      <div class="hero-visual">{svg}</div>
      <div class="hero-content">
        <div class="hero-tag {cfg["tc"]}">{cfg["tag"]}</div>
        <div class="hero-title">{title_ja}</div>
        <div class="hero-desc">{summary_ja}</div>
        <div class="hero-meta">{sources_html}<span class="hero-meta-dot"></span><span>{pub}</span></div>
        {stats_html}
      </div>
    </div>
  </div>
'''


def _pickup_section(articles: list) -> str:
    cards = ""
    for a in articles:
        cat = a.get("category", "model_research")
        cfg = CAT_CONFIG.get(cat, CAT_CONFIG["model_research"])
        aid = _article_id(a)
        svg = _make_visual(a, 300, 120)
        src = a["sources"][0]["name"] if a.get("sources") else ""
        pub = _fmt_date(a.get("published", ""))
        cards += f'''
      <div class="pickup-card" onclick="openArticle('{aid}')">
        <div class="pickup-thumb">{svg}</div>
        <div class="pickup-body"><span class="pickup-tag {cfg["tc"]}">{cfg["tag"]}</span><div class="pickup-title">{a.get("title_ja", a["title"])}</div><div class="pickup-meta"><span>{src}</span><span>{pub}</span></div></div>
      </div>'''

    return f'''
  <div class="sec">
    <div class="sec-header"><div class="sec-bar"></div><div class="sec-title">PICKUP</div></div>
    <div class="pickup-grid">{cards}
    </div>
  </div>
'''


def _category_section(cat_id: str, articles: list) -> str:
    cfg = CAT_CONFIG.get(cat_id, CAT_CONFIG["model_research"])
    cards = ""
    for a in articles:
        aid = _article_id(a)
        src_name = a["sources"][0]["name"] if a.get("sources") else ""
        pub = _fmt_date(a.get("published", ""))
        summary = a.get("summary_ja", "")[:130]
        title_ja = a.get("title_ja", a["title"])

        cards += f'''
      <article class="card-text" onclick="openArticle('{aid}')">
        <div class="card-text-tag {cfg["tc"]}">{cfg["tag"]}</div>
        <h3 class="card-text-title">{title_ja}</h3>
        <p class="card-text-desc">{summary}</p>
        <div class="card-text-meta"><span>{src_name}</span><span class="card-text-meta-dot"></span><span>{pub}</span></div>
      </article>'''

    return f'''
  <div class="sec" id="sec-{cat_id}">
    <div class="sec-header"><div class="sec-bar" style="background:{cfg["bar_color"]}"></div><div class="sec-title">{cfg["label"]}</div><div class="sec-more">すべて見る →</div></div>
    <div class="card-text-grid">{cards}
    </div>
  </div>
'''


def _key_numbers_section(articles: list) -> str:
    """記事からkey_statsを抽出し、数字カードのグリッドとして表示"""
    numbers = []
    for a in articles:
        # key_stats フィールドから抽出
        for stat in a.get("key_stats", []):
            val = stat.get("value", "")
            label = stat.get("label", "")
            if val and label:
                numbers.append((val, label))
        # rich content の stats からも抽出
        for stat in a.get("stats", []):
            val = stat.get("value", stat.get("v", ""))
            label = stat.get("label", stat.get("l", ""))
            if val and label:
                numbers.append((val, label))
    # 重複除去し最大8件
    seen = set()
    unique_numbers = []
    for val, label in numbers:
        key = f"{val}_{label}"
        if key not in seen:
            seen.add(key)
            unique_numbers.append((val, label))
    unique_numbers = unique_numbers[:8]

    if not unique_numbers:
        return ""

    cards = ""
    for val, label in unique_numbers:
        cards += f'''
      <div style="background:var(--white);border-radius:8px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.04);text-align:center;">
        <div style="font-size:24px;font-weight:900;color:var(--blue);letter-spacing:-1px">{val}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:4px">{label}</div>
      </div>'''

    return f'''
  <div class="sec" id="sec-key-numbers">
    <div class="sec-header"><div class="sec-bar"></div><div class="sec-title">📈 注目の数字</div></div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
      {cards}
    </div>
  </div>
'''


def _timeline_section(articles: list) -> str:
    """記事を公開日順にタイムライン表示"""
    sorted_arts = sorted(articles, key=lambda a: a.get("published", ""), reverse=True)
    items = ""
    for a in sorted_arts[:12]:
        pub = _fmt_date(a.get("published", ""))
        title_ja = a.get("title_ja", a["title"])
        summary = a.get("summary_ja", "")[:80]
        items += f'''
      <div style="margin-bottom:20px;position:relative;">
        <div style="position:absolute;left:-29px;width:10px;height:10px;border-radius:50%;background:var(--accent);border:2px solid var(--white);"></div>
        <div style="font-size:11px;font-weight:700;color:var(--accent);margin-bottom:4px;">{pub}</div>
        <div style="font-size:13px;font-weight:700;">{title_ja}</div>
        <div style="font-size:12px;color:var(--muted);margin-top:2px;">{summary}</div>
      </div>'''

    return f'''
  <div class="sec" id="sec-timeline">
    <div class="sec-header"><div class="sec-bar" style="background:var(--accent)"></div><div class="sec-title">📅 タイムライン</div></div>
    <div style="position:relative;padding-left:24px;border-left:2px solid var(--border);">
      {items}
    </div>
  </div>
'''


def _trending_topics_section(articles: list) -> str:
    """記事のrelated_topicsを集計し、タグクラウドとして表示"""
    topic_counts = {}
    for a in articles:
        for topic in a.get("related_topics", []):
            topic = topic.strip()
            if topic:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
    # 頻度順にソート
    sorted_topics = sorted(topic_counts.items(), key=lambda x: -x[1])[:15]

    if not sorted_topics:
        return ""

    tags = ""
    for topic, count in sorted_topics:
        tags += f'''
      <span style="background:var(--purple-light,#f3e8ff);color:var(--purple,#7c3aed);padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;">{topic} ({count})</span>'''

    return f'''
  <div class="sec" id="sec-trends">
    <div class="sec-header"><div class="sec-bar" style="background:var(--purple)"></div><div class="sec-title">🔥 トレンドトピック</div></div>
    <div style="display:flex;flex-wrap:wrap;gap:8px;">
      {tags}
    </div>
  </div>
'''


def _sources_section(articles: list) -> str:
    sources = set()
    for a in articles:
        for s in a.get("sources", []):
            sources.add(s["name"])
    chips = "".join(f'<span class="source-chip">{s}</span>' for s in sorted(sources))
    return f'''
  <div class="sources">
    <div class="sources-title">📎 参考文献・情報ソース</div>
    <div class="sources-list">{chips}</div>
  </div>
'''


def _sidebar(articles: list, date_display: str) -> str:
    # ニュースレター
    nl = '''<div class="sb-newsletter"><div class="sb-nl-title">📬 AI News Daily</div><div class="sb-nl-desc">世界のAI最新ニュースを毎朝メールでお届け。無料で購読できます。</div><div class="sb-nl-form"><input class="sb-nl-input" type="email" placeholder="メールアドレス"><button class="sb-nl-btn">購読</button></div><div class="sb-nl-note">※ いつでも解除できます</div></div>'''

    # 注目数字
    stats = '<div class="sb-stat"><span class="sb-stat-name">記事数</span><span class="sb-stat-val" style="color:var(--blue)">{}</span></div>'.format(f"{len(articles)}件")

    cats = {}
    for a in articles:
        cat = a.get("category_label", "不明")
        cats[cat] = cats.get(cat, 0) + 1
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        stats += f'<div class="sb-stat"><span class="sb-stat-name">{cat}</span><span class="sb-stat-val">{cnt}件</span></div>'

    stats_box = f'<div class="sb-box"><div class="sb-title"><span>📊</span>本日の注目数字</div><div class="sb-stats">{stats}</div></div>'

    # ランキング
    rank_html = ""
    rank_classes = ["r1", "r2", "r3", "other", "other"]
    for i, a in enumerate(articles[:5]):
        t = a.get("title_ja", a["title"])[:40]
        src = a["sources"][0]["name"] if a.get("sources") else ""
        rc = rank_classes[i]
        rank_html += f'''<div class="rank-item" style="display:flex;gap:10px;align-items:flex-start;margin-bottom:10px"><div class="rank-num {rc}" style="font-size:18px;font-weight:900;min-width:24px">{i+1}</div><div><div class="rank-text" style="font-size:12.5px;font-weight:700;line-height:1.5">{t}</div><div style="font-size:10.5px;color:var(--muted2)">{src}</div></div></div>'''

    rank_box = f'<div class="sb-box"><div class="sb-title"><span>🏆</span>注目ランキング</div>{rank_html}</div>'

    # トレンドトピック（サイドバー版）
    topic_counts = {}
    for a in articles:
        for topic in a.get("related_topics", []):
            topic = topic.strip()
            if topic:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
    sorted_topics = sorted(topic_counts.items(), key=lambda x: -x[1])[:8]
    trend_tags = ""
    for topic, count in sorted_topics:
        trend_tags += f'<span style="display:inline-block;background:var(--purple-light,#f3e8ff);color:var(--purple,#7c3aed);padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;margin:2px;">{topic} ({count})</span>'
    trend_box = ""
    if trend_tags:
        trend_box = f'<div class="sb-box"><div class="sb-title"><span>🔥</span>トレンドトピック</div><div style="display:flex;flex-wrap:wrap;gap:4px;">{trend_tags}</div></div>'

    # イベント（timeline_contextから日付を抽出）
    events_html = ""
    event_items = []
    for a in articles:
        tc = a.get("timeline_context", "")
        if tc:
            title_ja = a.get("title_ja", a["title"])[:35]
            pub = _fmt_date(a.get("published", ""))
            event_items.append((pub, title_ja))
    event_items = event_items[:5]
    if event_items:
        ev_list = ""
        for pub, title in event_items:
            ev_list += f'<div style="display:flex;gap:8px;align-items:flex-start;margin-bottom:8px;"><div style="font-size:10px;font-weight:700;color:var(--accent);min-width:60px;">{pub}</div><div style="font-size:11.5px;font-weight:600;line-height:1.4;">{title}</div></div>'
        events_html = f'<div class="sb-box"><div class="sb-title"><span>📅</span>関連イベント</div>{ev_list}</div>'

    return f'{nl}\n{stats_box}\n{rank_box}\n{trend_box}\n{events_html}'


def _build_js_data(articles: list, rich: dict) -> str:
    """JavaScript の const A={...}; を生成"""
    entries = []
    for a in articles:
        aid = _article_id(a)
        cat = a.get("category", "model_research")
        cfg = CAT_CONFIG.get(cat, CAT_CONFIG["model_research"])
        title_ja = _js_esc(a.get("title_ja", a["title"]))
        img_path = _IMAGE_MAP.get(aid)
        if img_path:
            svg = (
                f'<img src="/{img_path}" alt="{_js_esc(a.get("title_ja", a["title"]))}" '
                f'style="width:100%;height:100%;object-fit:cover;display:block;" />'
            )
        else:
            svg = _make_svg(a, 780, 260)
        svg_js = _js_esc(svg)

        # ソース
        sources_js = ",".join(
            f"{{n:'{_js_esc(s['name'])}',u:'{_js_esc(s['url'])}'}}"
            for s in a.get("sources", [])
        )

        # 統計
        r = rich.get(aid, {})
        stats_js = ""
        if r.get("stats"):
            stats_items = ",".join(
                f"{{v:'{_js_esc(str(st.get('value', '')))}',l:'{_js_esc(st.get('label', ''))}',c:'{cfg['bar_color']}'}}"
                for st in r["stats"][:3]
            )
            stats_js = f"stats:[{stats_items}],"

        # 本文
        body = r.get("body", f'<p class="modal-text">{_js_esc(a.get("summary_ja", a.get("summary", "")))}</p>')
        body_js = _js_esc(body)

        date_ja = _fmt_date_ja(a.get("published", ""))

        entry = (
            f"  {aid}:{{tag:'{cfg['tag']}',tc:'{cfg['tc']}',"
            f"title:'{title_ja}',"
            f"sources:[{sources_js}],"
            f"date:'{date_ja}',"
            f"svg:'{svg_js}',"
            f"{stats_js}"
            f"body:`{body_js}`}}"
        )
        entries.append(entry)

    js = "const A={\n" + ",\n".join(entries) + "\n};"

    # ナビゲーションのスクロール関数を追加
    js += """
function scrollToSec(id){
  if(id==='top'){window.scrollTo({top:0,behavior:'smooth'});return;}
  var el=document.getElementById(id);
  if(el){el.scrollIntoView({behavior:'smooth',block:'start'});}
}"""

    return js


if __name__ == "__main__":
    generate_html()
