#!/usr/bin/env python3
"""
AI News Daily — ニュース収集パイプライン メインオーケストレータ

3ステージで世界中のAIニュースを収集・処理・出力する:
  1. Collect: RSS + arXiv + Hacker News から生記事を取得
  2. Process: 重複排除 → カテゴリ分類 → 重要度ランキング → 日本語要約
  3. Output:  JSON出力（reports.json + アーカイブ）

使い方:
  python3 scripts/collect_news.py

環境変数:
  GEMINI_API_KEY: Gemini API キー（分類・ランキング・要約に使用）
"""

import sys
import os
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MAX_FINAL_ARTICLES
from sources.rss_feeds import fetch_all as fetch_rss
from sources.arxiv_fetcher import fetch as fetch_arxiv
from sources.hackernews import fetch as fetch_hn
from sources.reddit_fetcher import fetch as fetch_reddit
from processing.deduplicator import deduplicate
from processing.classifier import classify, filter_non_ai
from processing.ranker import rank
from processing.summarizer import summarize
from output.json_writer import write
from output.html_generator import generate_html


def main():
    start = time.time()

    print("=" * 60)
    print("  AI News Daily — ニュース収集パイプライン")
    print("=" * 60)

    # ──────────────────────────────────────────
    # Stage 1: Collect（収集）
    # ──────────────────────────────────────────
    print("\n📡 Stage 1: 収集")
    raw_articles = []

    raw_articles.extend(fetch_rss())
    raw_articles.extend(fetch_arxiv())
    raw_articles.extend(fetch_hn())
    raw_articles.extend(fetch_reddit())

    print(f"収集完了: 合計 {len(raw_articles)}件の生記事\n")

    if not raw_articles:
        print("記事が0件のため終了します。")
        return

    # ──────────────────────────────────────────
    # Stage 2: Process（処理）
    # ──────────────────────────────────────────
    print("🔧 Stage 2: 処理")

    # 重複排除
    deduplicated = deduplicate(raw_articles)

    # AI関連フィルタ
    filtered = filter_non_ai(deduplicated)

    # カテゴリ分類
    classified = classify(filtered)

    # 重要度ランキング
    ranked = rank(classified)

    # 上位N件を要約
    top_articles = ranked[:MAX_FINAL_ARTICLES]
    summarized = summarize(top_articles)

    # ──────────────────────────────────────────
    # Stage 3: Output（出力）
    # ──────────────────────────────────────────
    print("\n💾 Stage 3: 出力")
    report = write(summarized)

    # HTML更新
    print("\n🌐 Stage 4: HTML生成")
    generate_html()

    # ──────────────────────────────────────────
    # 完了レポート
    # ──────────────────────────────────────────
    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"  完了！")
    print(f"  処理時間: {elapsed:.1f}秒")
    print(f"  収集: {len(raw_articles)}件 → 重複排除: {len(deduplicated)}件 → AIフィルタ: {len(filtered)}件 → 最終: {len(summarized)}件")
    print(f"  カテゴリ分布:")
    cats = {}
    for a in summarized:
        cat = a.get("category_label", "不明")
        cats[cat] = cats.get(cat, 0) + 1
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}件")
    print("=" * 60)

    return summarized


if __name__ == "__main__":
    main()
