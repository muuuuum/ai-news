#!/usr/bin/env python3
"""
記事サムネイル画像生成モジュール

Gemini画像生成APIで各記事のサムネイル画像を生成し、
images/news/ に保存する。記事IDでキャッシュするため再生成しない。

設定:
  GEMINI_IMAGE_MODEL: 使用する画像生成モデル
    - "gemini-2.5-flash-image" (Nano Banana, $0.039/枚)
    - "imagen-4.0-fast-generate-001" (最安, $0.02/枚) ※ Imagen系は別エンドポイント
  IMAGE_GENERATION_LIMIT: 1回の更新で生成する画像の最大枚数（コスト制御用）
"""

import os
import sys
import base64
import hashlib
import re
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY, PROJECT_ROOT

GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
IMAGE_GENERATION_LIMIT = int(os.environ.get("IMAGE_GENERATION_LIMIT", "9"))

IMAGES_DIR = os.path.join(PROJECT_ROOT, "images", "news")
WEB_PATH_PREFIX = "images/news"

CAT_VISUAL_STYLE = {
    "model_research": "neural network visualization, brain circuits, glowing nodes, deep purple-indigo color scheme",
    "agent_ai": "robotic systems, autonomous workflow, connected nodes, emerald-teal color scheme",
    "business": "corporate finance, stock charts, modern skyscrapers, navy blue-gold color scheme",
    "security": "digital lock, shield, encrypted data streams, deep red-black color scheme",
    "startup": "rocket launch, growth trajectory, innovation spark, teal-orange color scheme",
    "research_paper": "academic papers, mathematical equations, lab equipment, warm amber color scheme",
}


def _article_id(art: dict) -> str:
    h = hashlib.md5(art.get("title", "").encode()).hexdigest()[:6]
    return f"a{h}"


def _ensure_dir():
    os.makedirs(IMAGES_DIR, exist_ok=True)


def _build_prompt(article: dict) -> str:
    title_en = article.get("title", "")
    summary = (article.get("summary_ja", "") or article.get("summary", ""))[:200]
    cat = article.get("category", "model_research")
    style = CAT_VISUAL_STYLE.get(cat, CAT_VISUAL_STYLE["model_research"])

    return f"""Generate a cinematic 16:9 editorial illustration for an AI news article.

Topic: {title_en}
Context: {summary}

Visual requirements:
- {style}
- Modern, clean, minimal tech illustration style suitable for a news website
- Abstract/conceptual representation of the topic — no text, no words, no letters in the image
- Dramatic lighting with depth and cinematic composition
- High contrast, professional editorial quality (Reuters / The Verge / Wired aesthetic)
- 16:9 aspect ratio, optimized as a thumbnail
- No people's faces, no logos, no copyrighted brand marks"""


def generate_image(article: dict) -> str:
    """記事の画像を生成。既存ならキャッシュを返す。失敗時は空文字。

    Returns:
        Web相対パス (例: "images/news/a1b2c3.png") または ""
    """
    if not GEMINI_API_KEY:
        return ""

    _ensure_dir()
    aid = _article_id(article)
    filename = f"{aid}.png"
    filepath = os.path.join(IMAGES_DIR, filename)
    web_path = f"{WEB_PATH_PREFIX}/{filename}"

    if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
        return web_path

    prompt = _build_prompt(article)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    try:
        resp = requests.post(url, json=payload, timeout=120)
        data = resp.json()
        if "candidates" not in data:
            err = data.get("error", {}).get("message", "unknown")
            print(f"  [画像] 失敗 {aid}: {err[:120]}")
            return ""

        for part in data["candidates"][0]["content"]["parts"]:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                img_data = base64.b64decode(inline["data"])
                with open(filepath, "wb") as f:
                    f.write(img_data)
                kb = len(img_data) // 1024
                print(f"  [画像] {aid} 生成完了 ({kb}KB)")
                return web_path

        print(f"  [画像] {aid} レスポンスに画像なし")
        return ""
    except Exception as e:
        print(f"  [画像] {aid} エラー: {e}")
        return ""


def generate_images_for_articles(articles: list, limit: int = None) -> dict:
    """先頭からlimit件まで画像生成。{article_id: web_path} を返す"""
    if limit is None:
        limit = IMAGE_GENERATION_LIMIT
    if not GEMINI_API_KEY:
        print("[画像] GEMINI_API_KEY未設定 — 画像生成スキップ")
        return {}

    _ensure_dir()
    print(f"[画像] 上位{min(limit, len(articles))}件を生成中（モデル: {GEMINI_IMAGE_MODEL}）...")
    results = {}
    targets = articles[:limit]
    for i, art in enumerate(targets, 1):
        aid = _article_id(art)
        path = generate_image(art)
        if path:
            results[aid] = path
        if i % 5 == 0:
            print(f"  進捗 {i}/{len(targets)}件")

    print(f"[画像] 完了: {len(results)}/{len(targets)}件成功")
    return results
