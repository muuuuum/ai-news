"""
Hacker News 収集モジュール
上位ストーリーからAI関連ニュースを抽出する
"""

from datetime import datetime, timezone, timedelta
import requests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FETCH_TIMEOUT, LOOKBACK_HOURS, AI_KEYWORDS
from sources.rss_feeds import RawArticle


HN_API = "https://hacker-news.firebaseio.com/v0"
MIN_SCORE = 30


def _matches_ai(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in AI_KEYWORDS)


def fetch() -> list[RawArticle]:
    """Hacker Newsの上位ストーリーからAI関連を抽出"""
    print("[HN] Hacker News 収集開始...")
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    try:
        resp = requests.get(f"{HN_API}/topstories.json", timeout=FETCH_TIMEOUT)
        story_ids = resp.json()[:60]
    except Exception as e:
        print(f"  [WARN] HN: ストーリーID取得失敗 - {e}")
        return []

    for sid in story_ids:
        try:
            item = requests.get(f"{HN_API}/item/{sid}.json", timeout=FETCH_TIMEOUT).json()
        except Exception:
            continue

        if not item or item.get("type") != "story":
            continue

        title = item.get("title", "")
        url = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
        score = item.get("score", 0)
        created = item.get("time", 0)

        pub = datetime.fromtimestamp(created, tz=timezone.utc) if created else None
        if pub and pub < cutoff:
            continue
        if score < MIN_SCORE:
            continue
        if not _matches_ai(title):
            continue

        articles.append(RawArticle(
            title=title,
            url=url,
            summary=f"Hacker News (score: {score}, comments: {item.get('descendants', 0)})",
            source_name="Hacker News",
            source_tier=5,
            published=pub,
            language="en",
        ))

        if len(articles) >= 10:
            break

    print(f"  [HN] {len(articles)}件取得")
    return articles
