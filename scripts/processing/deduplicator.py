"""
重複排除モジュール
URL正規化 + タイトル類似度で重複を排除し、複数ソースをマージする
"""

import re
from difflib import SequenceMatcher
from urllib.parse import urlparse


def _normalize_url(url: str) -> str:
    """URLを正規化して比較可能にする"""
    parsed = urlparse(url)
    # www. を除去、パスの末尾スラッシュを除去
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")
    return f"{host}{path}".lower()


def _title_similarity(a: str, b: str) -> float:
    """2つのタイトルの類似度を計算（0-1）"""
    # 日本語・英語混在を考慮して、小文字化して比較
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def deduplicate(articles: list) -> list:
    """
    重複排除し、同じニュースを複数ソースでカバーしている場合はマージする。
    戻り値は dict のリスト:
      {
        "title": str,
        "url": str,
        "summary": str,
        "sources": [{"name": str, "url": str, "tier": int}],
        "published": datetime or None,
        "language": str,
        "best_tier": int,
        "source_count": int,
      }
    """
    # Phase 1: URL正規化で完全一致の重複を除去
    seen_urls = {}
    unique = []

    for art in articles:
        norm_url = _normalize_url(art.url)
        if norm_url in seen_urls:
            # 既存エントリにソースを追加
            idx = seen_urls[norm_url]
            unique[idx]["sources"].append({
                "name": art.source_name,
                "url": art.url,
                "tier": art.source_tier,
            })
        else:
            seen_urls[norm_url] = len(unique)
            unique.append({
                "title": art.title,
                "url": art.url,
                "summary": art.summary,
                "sources": [{"name": art.source_name, "url": art.url, "tier": art.source_tier}],
                "published": art.published,
                "language": art.language,
            })

    # Phase 2: タイトル類似度で同一ニュースをマージ
    merged = []
    used = set()

    for i, item_a in enumerate(unique):
        if i in used:
            continue

        cluster = [item_a]
        used.add(i)

        for j, item_b in enumerate(unique):
            if j in used or j <= i:
                continue
            if _title_similarity(item_a["title"], item_b["title"]) > 0.45:
                cluster.append(item_b)
                used.add(j)

        # クラスタ内で最もティアが高い（数値が小さい）記事をベースにする
        best = min(cluster, key=lambda x: min(s["tier"] for s in x["sources"]))
        all_sources = []
        seen_source_names = set()
        for item in cluster:
            for src in item["sources"]:
                if src["name"] not in seen_source_names:
                    all_sources.append(src)
                    seen_source_names.add(src["name"])

        best["sources"] = all_sources
        best["best_tier"] = min(s["tier"] for s in all_sources)
        best["source_count"] = len(all_sources)
        merged.append(best)

    print(f"[重複排除] {len(articles)}件 → {len(merged)}件（{len(articles) - len(merged)}件マージ）")
    return merged
