#!/usr/bin/env python3
"""
YouTube動画用アセット一括生成

ニュースJSONデータから:
1. 各ニュースのイラスト画像をGemini APIで生成
2. 動画用データJSON（Remotionが読み込む）を出力
"""

import json
import os
import sys
import time
import base64
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import GEMINI_API_KEY, DATA_DIR

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
VIDEO_DATA_PATH = os.path.join(OUTPUT_DIR, "video_data.json")

GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"


def generate_news_image(article: dict, index: int) -> str:
    """ニュース記事のイラスト画像を生成"""
    title = article.get("title_ja", article.get("title", ""))
    title_en = article.get("title", "")
    category = article.get("category_label", "")
    summary = article.get("summary_ja", "")[:200]

    # カテゴリ別のビジュアルスタイル
    cat_styles = {
        "ビジネス": "corporate finance style, dollar signs, stock charts, building silhouettes, blue-gold color scheme",
        "モデル・研究": "neural network visualization, brain circuits, glowing nodes, purple-blue color scheme",
        "エージェントAI": "robotic arms, autonomous workflow, connected systems, green-teal color scheme",
        "セキュリティ": "digital lock, shield, warning signs, red-dark color scheme",
        "スタートアップ": "rocket launch, growth chart, innovation, teal-orange color scheme",
        "研究論文": "academic papers, mathematical formulas, lab equipment, warm orange color scheme",
    }
    style = cat_styles.get(category, "futuristic tech illustration, blue-purple color scheme")

    prompt = f"""Generate a cinematic 16:9 illustration for an AI news video segment.

Topic: {title_en}
Summary: {summary}

Visual requirements:
- {style}
- Dark background (suitable for video overlay with white text)
- Modern, clean, minimal tech illustration style
- No text or words in the image
- Abstract/conceptual representation of the topic
- Dramatic lighting, depth, cinematic composition
- High contrast, suitable for YouTube thumbnails
- Professional quality, like Fireship or Two Minute Papers channel art"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    try:
        resp = requests.post(url, json=payload, timeout=120)
        data = resp.json()

        if "candidates" in data:
            for part in data["candidates"][0]["content"]["parts"]:
                if "inlineData" in part:
                    img_data = base64.b64decode(part["inlineData"]["data"])
                    filename = f"news_{index:02d}.png"
                    filepath = os.path.join(IMAGES_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(img_data)
                    print(f"  [{index+1}] {title[:30]}... → {filename} ({len(img_data)//1024}KB)")
                    return filename
        else:
            err = data.get("error", {}).get("message", "Unknown error")
            print(f"  [{index+1}] 画像生成失敗: {err[:100]}")
    except Exception as e:
        print(f"  [{index+1}] 画像生成エラー: {e}")

    return ""


def build_video_data(articles: list, date_str: str) -> dict:
    """Remotion用の動画データJSONを構築"""

    # 5分動画の構成:
    # Opening (5s) + Hook (15s) + [News × 5 (各45s)] + Summary (30s) + Closing (15s) = ~310s ≈ 5min
    video_data = {
        "date": date_str,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "segments": [],
    }

    # Opening
    video_data["segments"].append({
        "type": "opening",
        "duration": 5,
        "title": "AI News Daily",
        "subtitle": f"{date_str} のAIニュースをお届けします",
    })

    # Hook — 今日一番のニュースのハイライト
    top = articles[0]
    video_data["segments"].append({
        "type": "hook",
        "duration": 15,
        "title": top.get("title_ja", top["title"]),
        "image": top.get("_image_file", ""),
        "key_stat": top.get("key_stats", [{}])[0] if top.get("key_stats") else {},
    })

    # News segments (5本)
    for i, art in enumerate(articles[:5]):
        stats = art.get("key_stats", [])
        video_data["segments"].append({
            "type": "news",
            "duration": 45,
            "index": i + 1,
            "title": art.get("title_ja", art["title"]),
            "title_en": art.get("title", ""),
            "category": art.get("category", ""),
            "category_label": art.get("category_label", ""),
            "summary": art.get("summary_ja", ""),
            "source": art.get("sources", [{}])[0].get("name", ""),
            "image": art.get("_image_file", ""),
            "key_stats": stats[:3],
            "impact": art.get("impact", ""),
        })

    # Summary
    video_data["segments"].append({
        "type": "summary",
        "duration": 30,
        "articles": [
            {"title": a.get("title_ja", a["title"]), "category_label": a.get("category_label", "")}
            for a in articles[:5]
        ],
    })

    # Closing
    video_data["segments"].append({
        "type": "closing",
        "duration": 15,
    })

    return video_data


def main():
    print("=" * 60)
    print("  動画アセット生成")
    print("=" * 60)

    # 最新ニュースデータ読み込み
    reports_path = os.path.join(DATA_DIR, "reports.json")
    with open(reports_path) as f:
        reports = json.load(f)

    # 最新の日付を取得
    dates = sorted(reports.get("reports", {}).keys(), reverse=True)
    if not dates:
        print("ニュースデータがありません")
        return

    date_str = dates[0]
    articles = reports["reports"][date_str]["articles"]
    top_articles = articles[:5]

    print(f"\n日付: {date_str}")
    print(f"ニュース: {len(top_articles)}本\n")

    # 画像生成
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print("📷 画像生成中...")

    for i, art in enumerate(top_articles):
        img_file = generate_news_image(art, i)
        art["_image_file"] = img_file
        time.sleep(3)  # レート制限対策

    # 動画データJSON生成
    video_data = build_video_data(top_articles, date_str)

    with open(VIDEO_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(video_data, f, ensure_ascii=False, indent=2)

    print(f"\n📁 動画データ: {VIDEO_DATA_PATH}")
    print(f"📁 画像フォルダ: {IMAGES_DIR}")

    # セグメント一覧
    total_duration = sum(s["duration"] for s in video_data["segments"])
    print(f"\n動画構成（合計 {total_duration}秒 = {total_duration/60:.1f}分）:")
    for seg in video_data["segments"]:
        t = seg["type"]
        d = seg["duration"]
        title = seg.get("title", seg.get("index", ""))
        print(f"  [{d:3d}s] {t:10s} | {title}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
