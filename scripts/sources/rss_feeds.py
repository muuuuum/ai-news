"""
RSSフィード収集モジュール
設定済みの全RSSフィードからAIニュースを取得する
"""

import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

import feedparser
import requests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RSS_FEEDS, AI_KEYWORDS, AI_NEGATIVE_KEYWORDS, MAX_ARTICLES_PER_SOURCE, FETCH_TIMEOUT, LOOKBACK_HOURS


@dataclass
class RawArticle:
    title: str
    url: str
    summary: str
    source_name: str
    source_tier: int
    published: Optional[datetime] = None
    language: str = "en"

    def __post_init__(self):
        # URL正規化: クエリパラメータの一部除去、末尾スラッシュ統一
        if self.url:
            self.url = self.url.split("?utm_")[0].rstrip("/")


def _matches_ai_keywords(text: str) -> bool:
    """テキストがAI関連キーワードを含むか"""
    text_lower = text.lower()
    for kw in AI_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


def _matches_negative_keywords(text: str) -> bool:
    """テキストがAI非関連キーワードを含むか"""
    text_lower = text.lower()
    for kw in AI_NEGATIVE_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


def _parse_published(entry) -> Optional[datetime]:
    """feedparserのエントリから公開日時をパースする"""
    for attr in ("published_parsed", "updated_parsed"):
        tp = getattr(entry, attr, None)
        if tp:
            try:
                return datetime(*tp[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
    # 文字列からのフォールバック
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(val).astimezone(timezone.utc)
            except Exception:
                continue
    return None


def fetch_feed(feed_config: dict) -> list[RawArticle]:
    """単一のRSSフィードを取得・パースする"""
    name = feed_config["name"]
    url = feed_config["url"]
    tier = feed_config["tier"]
    lang = feed_config["lang"]
    needs_ai_filter = feed_config["ai_filter"]

    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    articles = []

    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers={
            "User-Agent": "AI-News-Daily/1.0 (news aggregator)"
        })
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"  [WARN] {name}: フィード取得失敗 - {e}")
        return []

    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", getattr(entry, "description", "")).strip()

        if not title or not link:
            continue

        # 日付フィルタ
        pub = _parse_published(entry)
        if pub and pub < cutoff:
            continue

        # ネガティブキーワードフィルタ（全ソース共通）
        if _matches_negative_keywords(title):
            continue

        # AI関連キーワードフィルタ（一般テック媒体のみ）
        if needs_ai_filter:
            combined = f"{title} {summary}"
            if not _matches_ai_keywords(combined):
                continue

        articles.append(RawArticle(
            title=title,
            url=link,
            summary=summary[:500],  # 要約は500文字まで
            source_name=name,
            source_tier=tier,
            published=pub,
            language=lang,
        ))

    return articles


def fetch_all() -> list[RawArticle]:
    """全RSSフィードを収集する"""
    all_articles = []
    total = len(RSS_FEEDS)

    print(f"\n[RSS] {total}フィードから収集開始...")

    for i, feed_config in enumerate(RSS_FEEDS):
        name = feed_config["name"]
        articles = fetch_feed(feed_config)
        all_articles.extend(articles)
        print(f"  [{i+1}/{total}] {name}: {len(articles)}件")

    print(f"[RSS] 完了: 合計 {len(all_articles)}件\n")
    return all_articles
