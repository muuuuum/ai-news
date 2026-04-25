"""
カテゴリ分類モジュール
Gemini APIを使って各記事を5カテゴリに分類する
"""

import json
import requests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY, GEMINI_MODEL, CATEGORIES, AI_NEGATIVE_KEYWORDS


def filter_non_ai(articles: list) -> list:
    """
    AI非関連の記事をフィルタリングする。
    Geminiで二値判定し、キーワードフォールバックも使用する。
    """
    if not articles:
        return articles

    # まずキーワードフォールバックで明らかな非AI記事を除外
    keyword_filtered = []
    for art in articles:
        title = art.get("title", "")
        title_lower = title.lower()
        rejected = False
        for kw in AI_NEGATIVE_KEYWORDS:
            if kw.lower() in title_lower:
                rejected = True
                break
        if not rejected:
            keyword_filtered.append(art)

    removed_by_keyword = len(articles) - len(keyword_filtered)
    if removed_by_keyword:
        print(f"[AIフィルタ] キーワードで{removed_by_keyword}件除外")

    if not GEMINI_API_KEY:
        print("[AIフィルタ] GEMINI_API_KEY未設定 — キーワードフィルタのみ適用")
        return keyword_filtered

    print(f"[AIフィルタ] {len(keyword_filtered)}件をGeminiでAI関連判定中...")

    kept = []
    batch_size = 20
    for start in range(0, len(keyword_filtered), batch_size):
        batch = keyword_filtered[start:start + batch_size]
        results = _filter_batch(batch)
        kept.extend(results)

    print(f"[AIフィルタ] 完了: {len(kept)}/{len(keyword_filtered)}件がAI関連")
    return kept


def _filter_batch(batch: list) -> list:
    """Geminiで一括AI関連判定"""
    article_list = "\n".join(
        f"{i}. {a.get('title', '')}"
        for i, a in enumerate(batch)
    )

    prompt = f"""以下の{len(batch)}件の記事タイトルについて、それぞれAI（人工知能・機械学習・深層学習）に
本質的に関連する記事かどうかを判定してください。

除外すべき例:
- CEO人事・役員交代のニュース
- カンファレンスのスピーカー一覧やイベント告知
- スポーツや卓球など無関係な話題
- 一般的なテック記事でAIに実質的に触れていないもの
- 求人情報

記事一覧:
{article_list}

JSON配列で回答。各要素: {{"index": 番号, "is_ai": true/false}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        results = json.loads(text)

        kept = []
        for item in results:
            idx = item.get("index", -1)
            is_ai = item.get("is_ai", True)
            if 0 <= idx < len(batch) and is_ai:
                kept.append(batch[idx])
        return kept

    except Exception as e:
        print(f"  [WARN] GeminiAIフィルタ失敗 - {e}; バッチ全件を保持")
        return batch


def classify(articles: list) -> list:
    """
    記事リストにカテゴリを付与する。
    articles: deduplicator の出力（dict のリスト）
    戻り値: 各 dict に category, category_label, tag_class が追加される
    """
    if not articles:
        return articles

    if not GEMINI_API_KEY:
        print("[分類] GEMINI_API_KEY未設定 — キーワードベースで分類")
        return _classify_by_keywords(articles)

    print(f"[分類] {len(articles)}件をGeminiで分類中...")

    # バッチ: 最大20件ずつ
    batch_size = 20
    for start in range(0, len(articles), batch_size):
        batch = articles[start:start + batch_size]
        _classify_batch(batch, start)

    categorized = sum(1 for a in articles if "category" in a)
    print(f"[分類] 完了: {categorized}/{len(articles)}件分類済み")
    return articles


def _classify_batch(batch: list, offset: int):
    """Gemini APIで一括分類"""
    article_list = "\n".join(
        f"{i}. [{a['title']}] {a['summary'][:150]}"
        for i, a in enumerate(batch)
    )

    prompt = f"""以下の{len(batch)}件のAIニュース記事を、それぞれ1つのカテゴリに分類してください。

カテゴリ:
- model_research: 新しいAIモデル、ベンチマーク、研究論文、技術的ブレークスルー
- agent_ai: AIエージェント、自律システム、ツール使用、MCP、ワークフロー自動化
- business: 資金調達、売上、企業提携、買収、IPO、市場動向
- security: AIの安全性、セキュリティ事件、規制、ポリシー、コンプライアンス
- startup: 新興企業、プロダクトローンチ、シード/シリーズ資金調達

記事一覧:
{article_list}

JSON配列で回答してください。各要素は {{"index": 番号, "category": "カテゴリID"}} の形式。"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        results = json.loads(text)

        for item in results:
            idx = item.get("index", -1)
            cat = item.get("category", "")
            if 0 <= idx < len(batch) and cat in CATEGORIES:
                batch[idx]["category"] = cat
                batch[idx]["category_label"] = CATEGORIES[cat]["label"]
                batch[idx]["tag_class"] = CATEGORIES[cat]["tag_class"]

    except Exception as e:
        print(f"  [WARN] Gemini分類失敗 - {e}")

    # 分類されなかった記事はキーワードフォールバック
    for art in batch:
        if "category" not in art:
            _classify_single_by_keywords(art)


def _classify_by_keywords(articles: list) -> list:
    """キーワードベースのフォールバック分類"""
    for art in articles:
        _classify_single_by_keywords(art)
    return articles


def _classify_single_by_keywords(art: dict):
    """1記事をキーワードで分類"""
    text = f"{art['title']} {art['summary']}".lower()
    best_cat = "model_research"  # デフォルト
    best_score = 0

    for cat_id, cat_info in CATEGORIES.items():
        score = sum(1 for kw in cat_info["keywords"] if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_cat = cat_id

    art["category"] = best_cat
    art["category_label"] = CATEGORIES[best_cat]["label"]
    art["tag_class"] = CATEGORIES[best_cat]["tag_class"]
