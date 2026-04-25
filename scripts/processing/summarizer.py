"""
要約生成モジュール
Gemini APIで各記事の日本語要約・見出しを生成する
"""

import json
import requests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY, GEMINI_MODEL


def summarize(articles: list) -> list:
    """
    上位記事に日本語要約を付与する。
    追加フィールド: title_ja, summary_ja, impact
    """
    if not articles:
        return articles

    if not GEMINI_API_KEY:
        print("[要約] GEMINI_API_KEY未設定 — スキップ")
        for art in articles:
            art["title_ja"] = art["title"]
            art["summary_ja"] = art["summary"][:200]
            art["impact"] = ""
            art["key_stats"] = []
            art["related_topics"] = []
            art["timeline_context"] = ""
        return articles

    print(f"[要約] {len(articles)}件の日本語要約を生成中...")

    # 5件ずつバッチ処理
    batch_size = 5
    for start in range(0, len(articles), batch_size):
        batch = articles[start:start + batch_size]
        _summarize_batch(batch)
        print(f"  {min(start + batch_size, len(articles))}/{len(articles)}件完了")

    summarized = sum(1 for a in articles if "title_ja" in a)
    print(f"[要約] 完了: {summarized}/{len(articles)}件")
    return articles


def _summarize_batch(batch: list):
    """5件まとめてGeminiで要約"""
    article_list = ""
    for i, a in enumerate(batch):
        article_list += f"\n---\n記事{i}:\nタイトル: {a['title']}\n概要: {a['summary'][:300]}\nソース: {a['sources'][0]['name']}\nカテゴリ: {a.get('category_label', '不明')}\n"

    prompt = f"""以下の{len(batch)}件のAIニュース記事を日本語で要約してください。

要件:
- title_ja: 日本語の見出し（30文字以内、具体的な数字や固有名詞を含める）
- summary_ja: 2-3文の日本語要約（重要な部分を<b>タグで強調）
- impact: 読者にとってなぜ重要かを1文で
- key_stats: 記事から抽出できる重要な数値を最大3つ。各要素は {{"value": "数値", "label": "説明"}} の形式。数値がなければ空配列。
- related_topics: この記事に関連するトレンドトピックを2-3個（例: "LLM競争", "AI規制"）
- timeline_context: このニュースを時系列で位置づける1文（例: "OpenAIのGPT-4o発表から2ヶ月後の動き"）

トーン: プロフェッショナルだが親しみやすい。事実ベースで、煽らない。
日本語の記事はそのまま要約。英語の記事は自然な日本語に翻訳して要約。

{article_list}

JSON配列で回答。各要素: {{"index": 番号, "title_ja": "...", "summary_ja": "...", "impact": "...", "key_stats": [...], "related_topics": [...], "timeline_context": "..."}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=60)
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        results = json.loads(text)

        for item in results:
            idx = item.get("index", -1)
            if 0 <= idx < len(batch):
                batch[idx]["title_ja"] = item.get("title_ja", batch[idx]["title"])
                batch[idx]["summary_ja"] = item.get("summary_ja", batch[idx]["summary"][:200])
                batch[idx]["impact"] = item.get("impact", "")
                batch[idx]["key_stats"] = item.get("key_stats", [])
                batch[idx]["related_topics"] = item.get("related_topics", [])
                batch[idx]["timeline_context"] = item.get("timeline_context", "")

    except Exception as e:
        print(f"  [WARN] Gemini要約失敗 - {e}")
        for art in batch:
            if "title_ja" not in art:
                art["title_ja"] = art["title"]
                art["summary_ja"] = art["summary"][:200]
                art["impact"] = ""
                art["key_stats"] = []
                art["related_topics"] = []
                art["timeline_context"] = ""
