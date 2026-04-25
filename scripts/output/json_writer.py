"""
JSON出力モジュール
収集・処理済みの記事をdata/reports.jsonとアーカイブに書き出す
"""

import json
import os
from datetime import datetime, timezone, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, ARCHIVE_DIR, REPORTS_JSON


def write(articles: list, date_str: str = None):
    """
    記事リストをJSON形式で保存する。
    - data/reports.json: メインファイル（過去30日分保持）
    - data/archive/YYYY-MM-DD.json: 日次アーカイブ
    """
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)

    if not date_str:
        date_str = now.strftime("%Y-%m-%d")

    generated_at = now.isoformat()

    # 記事データを整形
    output_articles = []
    for i, art in enumerate(articles):
        output_articles.append({
            "id": f"{date_str}-{i+1:03d}",
            "title": art.get("title", ""),
            "title_ja": art.get("title_ja", art.get("title", "")),
            "summary_ja": art.get("summary_ja", art.get("summary", "")[:200]),
            "impact": art.get("impact", ""),
            "category": art.get("category", "model_research"),
            "category_label": art.get("category_label", "モデル・研究"),
            "tag_class": art.get("tag_class", "tag-model"),
            "sources": [
                {"name": s["name"], "url": s["url"]}
                for s in art.get("sources", [])
            ],
            "importance": art.get("importance", 5.0),
            "published": art.get("published").isoformat() if art.get("published") else date_str,
            "language": art.get("language", "en"),
            "key_stats": art.get("key_stats", []),
            "related_topics": art.get("related_topics", []),
            "timeline_context": art.get("timeline_context", ""),
        })

    day_report = {
        "generated_at": generated_at,
        "article_count": len(output_articles),
        "articles": output_articles,
    }

    # --- メインJSONに書き込み ---
    os.makedirs(DATA_DIR, exist_ok=True)

    reports = {"reports": {}, "weeklyReviews": {}, "syncedAt": generated_at}
    if os.path.exists(REPORTS_JSON):
        try:
            with open(REPORTS_JSON, "r", encoding="utf-8") as f:
                reports = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    reports["reports"][date_str] = day_report
    reports["syncedAt"] = generated_at

    # 30日以上前のレポートを削除
    cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    old_keys = [k for k in reports["reports"] if k < cutoff]
    for k in old_keys:
        del reports["reports"][k]

    with open(REPORTS_JSON, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

    print(f"[出力] reports.json 更新: {date_str} ({len(output_articles)}件)")

    # --- アーカイブに書き込み ---
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    archive_path = os.path.join(ARCHIVE_DIR, f"{date_str}.json")
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(day_report, f, ensure_ascii=False, indent=2)

    print(f"[出力] アーカイブ: {archive_path}")

    return day_report
