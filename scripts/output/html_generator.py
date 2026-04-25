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

INDEX_PATH = os.path.join(PROJECT_ROOT, "index.html")

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
    """カテゴリに応じたSVGサムネイルを生成"""
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


def _generate_rich_content(articles: list) -> dict:
    """Geminiで各記事のリッチなモーダルコンテンツを生成"""
    if not GEMINI_API_KEY or not articles:
        return {}

    print("[HTML] Geminiでリッチコンテンツ生成中...")

    results = {}
    batch_size = 5

    for start in range(0, len(articles), batch_size):
        batch = articles[start:start + batch_size]
        batch_results = _generate_rich_batch(batch)
        results.update(batch_results)
        print(f"  {min(start + batch_size, len(articles))}/{len(articles)}件完了")

    return results


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

    # 最大15件に絞る（ページが長くなりすぎない）
    articles = articles[:15]

    # 既存HTMLを読み込み
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # リッチコンテンツ生成（Gemini）
    rich = _generate_rich_content(articles[:10])

    # 日付
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    date_display = f"{dt.year}年{dt.month}月{dt.day}日（{weekdays[dt.weekday()]}）"

    # === 1. ヘッダー日付 ===
    html = re.sub(r'<div class="header-date">[^<]*</div>',
                  f'<div class="header-date">{date_display}</div>', html)

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
    pickups = articles[1:5]

    # カテゴリ分類（各カテゴリ最大3件）
    by_cat = {}
    for a in articles[5:]:
        cat = a.get("category", "model_research")
        by_cat.setdefault(cat, [])
        if len(by_cat[cat]) < 3:
            by_cat[cat].append(a)

    main = ""
    main += _hero_section(hero, rich)
    main += _pickup_section(pickups)
    for cat_id, cat_arts in by_cat.items():
        main += _category_section(cat_id, cat_arts)
    main += _sources_section(articles)

    html = re.sub(r'<main>.*?</main>', f'<main>\n{main}\n</main>', html, flags=re.DOTALL)

    # === 4. サイドバー ===
    sidebar = _sidebar(articles, date_display)
    html = re.sub(r'<aside class="sidebar">.*?</aside>',
                  f'<aside class="sidebar">\n{sidebar}\n</aside>', html, flags=re.DOTALL)

    # === 5. JavaScript記事データ ===
    js_data = _build_js_data(articles[:10], rich)
    # const A={...}; を丸ごと差し替え
    html = re.sub(r'const A=\{.*?\};', js_data, html, flags=re.DOTALL)

    # === 6. フッター更新日時 ===
    update_time = now.strftime("%Y-%m-%d %H:%M")
    html = re.sub(r'最終更新:.*?</div>', f'最終更新: {update_time} ・ 毎朝 9:00 自動更新</div>', html)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[HTML] index.html 更新完了（{len(articles)}件、リッチコンテンツ{len(rich)}件）")


# === セクション生成関数 ===

def _hero_section(art: dict, rich: dict) -> str:
    cat = art.get("category", "model_research")
    cfg = CAT_CONFIG.get(cat, CAT_CONFIG["model_research"])
    aid = _article_id(art)
    title_ja = art.get("title_ja", art["title"])
    summary_ja = art.get("summary_ja", "")
    svg = _make_svg(art, 600, 340)
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
        svg = _make_svg(a, 300, 120)
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
        svg = _make_svg(a, 220, 140)
        src = a["sources"][0]["name"] if a.get("sources") else ""
        pub = _fmt_date(a.get("published", ""))
        summary = a.get("summary_ja", "")[:120]
        src_links = ""
        for s in a.get("sources", []):
            src_links += f'<a class="src-link" href="{s["url"]}" target="_blank" onclick="event.stopPropagation()">{s["name"]}</a>'

        cards += f'''
      <div class="card-h" onclick="openArticle('{aid}')">
        <div class="card-h-thumb">{svg}</div>
        <div class="card-h-body">
          <span class="card-h-tag {cfg["tc"]}">{cfg["tag"]}</span>
          <div class="card-h-title">{a.get("title_ja", a["title"])}</div>
          <div class="card-h-desc">{summary}</div>
          <div class="card-h-meta">{src_links}<span class="card-h-meta-dot"></span><span>{pub}</span></div>
        </div>
      </div>'''

    return f'''
  <div class="sec">
    <div class="sec-header"><div class="sec-bar" style="background:{cfg["bar_color"]}"></div><div class="sec-title">{cfg["label"]}</div><div class="sec-more">すべて見る →</div></div>
    <div class="card-list">{cards}
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

    return f'{nl}\n{stats_box}\n{rank_box}'


def _build_js_data(articles: list, rich: dict) -> str:
    """JavaScript の const A={...}; を生成"""
    entries = []
    for a in articles:
        aid = _article_id(a)
        cat = a.get("category", "model_research")
        cfg = CAT_CONFIG.get(cat, CAT_CONFIG["model_research"])
        title_ja = _js_esc(a.get("title_ja", a["title"]))
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

    return "const A={\n" + ",\n".join(entries) + "\n};"


if __name__ == "__main__":
    generate_html()
