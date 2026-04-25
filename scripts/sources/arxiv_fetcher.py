"""
arXiv 収集モジュール
cs.AI, cs.CL, cs.LG の最新論文を取得する
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import requests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FETCH_TIMEOUT, LOOKBACK_HOURS
from sources.rss_feeds import RawArticle


ARXIV_API = "http://export.arxiv.org/api/query"
CATEGORIES = "cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG"
# 主要ラボの著者名（部分一致）で優先度を上げる
PRIORITY_AFFILIATIONS = [
    "google", "deepmind", "openai", "anthropic", "meta", "microsoft",
    "nvidia", "apple", "amazon", "alibaba", "tsinghua", "stanford", "mit", "berkeley",
]


def fetch() -> list[RawArticle]:
    """arXiv APIから最新AI論文を取得"""
    print("[arXiv] 論文収集開始...")
    articles = []

    params = {
        "search_query": CATEGORIES,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": 100,
    }

    try:
        resp = requests.get(ARXIV_API, params=params, timeout=FETCH_TIMEOUT * 4)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [WARN] arXiv: 取得失敗 - {e}")
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.content)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS * 2)  # 論文は少し広めに

    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        title = title_el.text.strip().replace("\n", " ") if title_el is not None else ""

        link_el = entry.find("atom:id", ns)
        url = link_el.text.strip() if link_el is not None else ""

        summary_el = entry.find("atom:summary", ns)
        summary = summary_el.text.strip().replace("\n", " ")[:500] if summary_el is not None else ""

        pub_el = entry.find("atom:published", ns)
        pub = None
        if pub_el is not None:
            try:
                pub = datetime.fromisoformat(pub_el.text.strip().replace("Z", "+00:00"))
            except ValueError:
                pass

        if pub and pub < cutoff:
            continue

        # 著者を取得
        authors = []
        for author_el in entry.findall("atom:author", ns):
            name_el = author_el.find("atom:name", ns)
            if name_el is not None:
                authors.append(name_el.text.strip())

        author_str = ", ".join(authors[:5])
        if len(authors) > 5:
            author_str += f" et al. ({len(authors)}人)"

        articles.append(RawArticle(
            title=title,
            url=url,
            summary=f"[{author_str}] {summary}",
            source_name="arXiv",
            source_tier=3,
            published=pub,
            language="en",
        ))

    print(f"  [arXiv] {len(articles)}件取得")
    return articles
