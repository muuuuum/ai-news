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

CAT_SCENE_HINT = {
    "model_research": "a research lab, computer screens with data, scientists at work, data center hardware, or a university campus setting",
    "agent_ai": "a modern office workspace, automated production line, logistics warehouse, or human-computer interaction in a real environment",
    "business": "corporate headquarters, conference rooms, trading floor, executive meetings, financial district streetscape, or product launch",
    "security": "government buildings, courtrooms, server rooms with dim lighting, cybersecurity operations center, or police/regulatory press conference",
    "startup": "modern co-working space, founder portraits in offices, product demos, venture capital meetings, or tech campus exterior",
    "research_paper": "academic conference hall, university library, whiteboards with equations, scientists presenting research, or peer review setting",
}


def _article_id(art: dict) -> str:
    h = hashlib.md5(art.get("title", "").encode()).hexdigest()[:6]
    return f"a{h}"


def _ensure_dir():
    os.makedirs(IMAGES_DIR, exist_ok=True)


def _build_prompt(article: dict) -> str:
    title_en = article.get("title", "")
    title_ja = article.get("title_ja", "")
    summary = (article.get("summary", "") or article.get("summary_ja", ""))[:300]
    cat = article.get("category", "model_research")
    scene_hint = CAT_SCENE_HINT.get(cat, CAT_SCENE_HINT["model_research"])

    return f"""You are a photo editor for a major international news website (Reuters, AP, The New York Times, The Verge).
Select a single editorial photograph that best illustrates the news article below — as if you were choosing a hero image to run with the story.

Article headline: {title_en}
{f'Japanese headline: {title_ja}' if title_ja else ''}
Summary: {summary}

Image requirements:
- Photorealistic editorial / documentary photograph style — NOT an illustration, NOT 3D render, NOT abstract digital art.
- Depict the actual subject of the news concretely and literally. Possible scenes: {scene_hint}.
- Natural lighting (daylight, office lighting, or ambient interior lighting). Shallow depth of field is fine.
- Composition like a Reuters / AP wire photo: real-world setting, real objects, believable scene.
- Avoid all sci-fi clichés: no glowing neural networks, no holograms, no neon circuits, no floating data, no robotic hands reaching out, no abstract blue/purple gradient backgrounds, no "AI brain" imagery.
- People can appear but use generic / unrecognizable faces (no real public figures). Body language and setting should match a news context.
- 16:9 wide aspect ratio.
- No text, no words, no letters, no logos, no brand marks, no watermarks anywhere in the image.
- Quality: high resolution, sharp, professional photojournalism quality."""


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
