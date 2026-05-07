#!/usr/bin/env python3
"""
パラノイア式5段構造の動画台本を生成する

入力: ニュースJSON（reports.json）
出力: 各ニュースの台本JSON（hook/fact/depth/your_life/close）+ 推奨クリップ指定
"""

import json, os, sys, requests, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

API_KEY = os.environ.get("GEMINI_API_KEY", "")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT = os.path.join(PROJECT_ROOT, "output")


def generate_script(article: dict) -> dict:
    """1記事からパラノイア式5段台本を生成"""

    title = article.get("title_ja", article.get("title", ""))
    summary = article.get("summary_ja", article.get("summary", ""))[:300]
    impact = article.get("impact", "")
    real_world = article.get("real_world", "")
    hook_q = article.get("hook_question", "")

    prompt = f"""あなたはYouTubeのエンタメ系AIニュース番組の台本ライターです。
パラノイア式（@paranoia369）の手法で台本を書きます。

ニュース:
タイトル: {title}
要約: {summary}
影響: {impact}
現実への反映: {real_world}

パラノイア式5段構造で60秒の台本を書いてください:

1. hook (5秒/30文字以内): 衝撃の数字or問いかけで引きつける。「人間さん、」で始めても良い。
2. fact (10秒/60文字以内): 何が起きたか事実のみ。短く鋭く。
3. depth (15秒/100文字以内): なぜ重大か。表面→本質→未来の3段階で深掘り。
4. your_life (20秒/120文字以内): あなたの人生にどう影響するか。具体的に。「あなたの○○が変わる」レベルに。
5. close (10秒/50文字以内): 問いかけで締める。余韻を残す。

ルール:
- ドルは円換算メイン（$40B→約6兆円）
- 煽りではなく本質的な問い
- 抽象論NG、具体的な影響のみ
- 合計250〜350文字

また、各パートに最適なキャラクリップを指定:
- clip_talking: 通常解説
- clip_surprised: 衝撃リアクション
- clip_serious: 重要ポイント
- clip_pointing: 画面を指す
- clip_laugh: ユーモア
- clip_waving: エンディング

JSON:
{{
  "hook": {{"text": "...", "clip": "clip_surprised"}},
  "fact": {{"text": "...", "clip": "clip_talking"}},
  "depth": {{"text": "...", "clip": "clip_serious"}},
  "your_life": {{"text": "...", "clip": "clip_pointing"}},
  "close": {{"text": "...", "clip": "clip_waving"}}
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    for attempt in range(3):
        try:
            resp = requests.post(url, json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.5, "responseMimeType": "application/json"},
            }, timeout=30)
            data = resp.json()
            if "candidates" in data:
                return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
        except Exception:
            pass
        time.sleep(5)

    # フォールバック
    return {
        "hook": {"text": hook_q or title, "clip": "clip_surprised"},
        "fact": {"text": summary[:60], "clip": "clip_talking"},
        "depth": {"text": impact or "詳細は動画をご覧ください。", "clip": "clip_serious"},
        "your_life": {"text": real_world or "あなたの生活にも影響があります。", "clip": "clip_pointing"},
        "close": {"text": "この続きは明日。", "clip": "clip_waving"},
    }


def main():
    with open(os.path.join(DATA_DIR, "reports.json")) as f:
        reports = json.load(f)

    dates = sorted(reports["reports"].keys(), reverse=True)
    articles = reports["reports"][dates[0]]["articles"]

    print(f"日付: {dates[0]}")
    print(f"トップニュース: {articles[0].get('title_ja', articles[0]['title'])}\n")

    script = generate_script(articles[0])

    print("=== パラノイア式台本 ===\n")
    for part in ["hook", "fact", "depth", "your_life", "close"]:
        s = script[part]
        print(f"[{part}] ({s['clip']})")
        print(f"  {s['text']}\n")

    output_path = os.path.join(OUTPUT, "paranoia_script.json")
    with open(output_path, "w") as f:
        json.dump({"date": dates[0], "article": articles[0], "script": script}, f, ensure_ascii=False, indent=2)
    print(f"保存: {output_path}")


if __name__ == "__main__":
    main()
