"""
重要度ランキングモジュール
ヒューリスティック + Gemini AI で記事の重要度スコアを算出する
"""

import json
import requests
from datetime import datetime, timezone, timedelta

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY, GEMINI_MODEL, TIER_WEIGHTS


def rank(articles: list) -> list:
    """
    記事リストに importance スコア（1-10）を付与し、降順ソートして返す。
    """
    if not articles:
        return articles

    print(f"[ランキング] {len(articles)}件のスコアリング...")

    # Phase 1: ヒューリスティックスコア（0-5点）
    for art in articles:
        art["_heuristic"] = _heuristic_score(art)

    # Phase 2: AIスコア（1-10点）
    if GEMINI_API_KEY:
        _ai_rank(articles)
    else:
        for art in articles:
            art["_ai_score"] = 5.0  # API無しはニュートラル

    # 合成スコア: ヒューリスティック40% + AI60%
    for art in articles:
        h = art.pop("_heuristic", 0)
        a = art.pop("_ai_score", 5.0)
        # ヒューリスティック(0-5)を1-10にスケール + AI(1-10)
        art["importance"] = round(h * 0.8 + a * 0.6, 1)  # max: 4 + 6 = 10

    articles.sort(key=lambda x: x["importance"], reverse=True)

    top3 = articles[:3]
    print(f"[ランキング] 完了。トップ3:")
    for i, a in enumerate(top3):
        print(f"  {i+1}. [{a['importance']}] {a['title'][:60]}")

    return articles


def _heuristic_score(art: dict) -> float:
    """ヒューリスティックスコア（0-5点）"""
    score = 0.0

    # ソースティア
    tier = art.get("best_tier", 5)
    score += TIER_WEIGHTS.get(tier, 0.5)

    # 複数ソースカバレッジ
    src_count = art.get("source_count", 1)
    if src_count >= 3:
        score += 2.0
    elif src_count >= 2:
        score += 1.0

    # 新鮮度
    pub = art.get("published")
    if pub:
        now = datetime.now(timezone.utc)
        hours_ago = (now - pub).total_seconds() / 3600
        if hours_ago < 6:
            score += 1.0
        elif hours_ago < 12:
            score += 0.5

    return min(score, 5.0)


def _ai_rank(articles: list):
    """Gemini AIで重要度を判定"""
    article_list = "\n".join(
        f"{i}. [{a.get('category_label', '不明')}] {a['title']}"
        for i, a in enumerate(articles)
    )

    prompt = f"""以下の{len(articles)}件のAIニュースの重要度を1-10のスコアで評価してください。

評価基準:
- 10: 業界を変えるレベルの発表（新しいフロンティアモデル、大型買収、重大な規制）
- 7-9: 重要なニュース（主要企業の新機能、大きな資金調達、重要な研究成果）
- 4-6: 注目すべきニュース（アップデート、提携、新サービス）
- 1-3: 軽微なニュース（小規模な更新、ニッチな話題）

記事一覧:
{article_list}

JSON配列で回答。各要素: {{"index": 番号, "score": スコア}}"""

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
            score = item.get("score", 5)
            if 0 <= idx < len(articles):
                articles[idx]["_ai_score"] = float(score)

    except Exception as e:
        print(f"  [WARN] Geminiランキング失敗 - {e}")
        for art in articles:
            if "_ai_score" not in art:
                art["_ai_score"] = 5.0
