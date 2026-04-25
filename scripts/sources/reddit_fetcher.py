"""
Reddit 収集モジュール
AI関連サブレディットからホットな投稿を取得する
"""

import time
from datetime import datetime, timezone, timedelta
import requests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FETCH_TIMEOUT, LOOKBACK_HOURS, REDDIT_SUBREDDITS
from sources.rss_feeds import RawArticle


REDDIT_BASE = "https://www.reddit.com/r"
USER_AGENT = "AI-News-Daily/1.0 (news aggregator; contact: ai-news-daily)"


def fetch() -> list[RawArticle]:
    """Reddit の AI関連サブレディットからホットな投稿を取得"""
    print("[Reddit] Reddit 収集開始...")
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    for i, sub_config in enumerate(REDDIT_SUBREDDITS):
        subreddit = sub_config["subreddit"]
        name = sub_config["name"]
        min_score = sub_config["min_score"]

        if i > 0:
            time.sleep(2)  # レート制限回避

        url = f"{REDDIT_BASE}/{subreddit}/hot.json?limit=50"
        try:
            resp = requests.get(url, timeout=FETCH_TIMEOUT, headers={
                "User-Agent": USER_AGENT,
            })
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [WARN] {name}: 取得失敗 - {e}")
            continue

        posts = data.get("data", {}).get("children", [])
        sub_count = 0

        for post in posts:
            post_data = post.get("data", {})

            title = post_data.get("title", "").strip()
            score = post_data.get("score", 0)
            created_utc = post_data.get("created_utc", 0)
            is_self = post_data.get("is_self", False)

            # 実際のリンクURL（セルフ投稿の場合はRedditコメントURL）
            if is_self or not post_data.get("url"):
                link = f"https://www.reddit.com{post_data.get('permalink', '')}"
            else:
                link = post_data.get("url", "")

            if not title or not link:
                continue

            # 日付フィルタ
            pub = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None
            if pub and pub < cutoff:
                continue

            # スコアフィルタ
            if score < min_score:
                continue

            selftext = post_data.get("selftext", "")[:300]
            summary = f"{name} (score: {score}) {selftext}".strip()

            articles.append(RawArticle(
                title=title,
                url=link,
                summary=summary[:500],
                source_name=name,
                source_tier=5,
                published=pub,
                language="en",
            ))
            sub_count += 1

        print(f"  [{name}] {sub_count}件取得")

    print(f"[Reddit] 完了: 合計 {len(articles)}件")
    return articles
