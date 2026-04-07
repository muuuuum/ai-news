"""
ai_news / micro_news チャンネル用 Slack Webhook (Vercel Serverless)
メンションに対してGemini AIで即時回答する
"""

import os
import re
import json
import time
from http.server import BaseHTTPRequestHandler

import requests

# ── 設定 ──
SLACK_BOT_TOKEN = os.environ.get("NEWS_SLACK_BOT_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

CHANNELS = {
    "C0AQ1P4M64T": "ai_news",
    "C0AQW2751TK": "micro_news",
}

SITES = {
    "ai_news": "https://muuuuum.github.io/ai-news/",
    "micro_news": "https://muuuuum.github.io/micro-news/",
}

SYSTEM_PROMPTS = {
    "ai_news": (
        "あなたはAIニュース専門のアシスタントです。"
        "AI、機械学習、LLM、生成AI、テック業界の最新トレンドに詳しいです。"
        "質問には正確かつ簡潔に、日本語で回答してください。"
        "回答はSlackのメッセージとして読みやすいように、適度に箇条書きや太字（*太字*）を使ってください。"
        "最新ニュースサイト: https://muuuuum.github.io/ai-news/ も適宜案内してください。"
        "回答は500文字以内に収めてください。"
    ),
    "micro_news": (
        "あなたはマイクロビジネス・副業・フリーランス専門のアシスタントです。"
        "個人開発、スタートアップ、EC、副業、フリーランスの最新トレンドに詳しいです。"
        "質問には正確かつ簡潔に、日本語で回答してください。"
        "回答はSlackのメッセージとして読みやすいように、適度に箇条書きや太字（*太字*）を使ってください。"
        "最新ニュースサイト: https://muuuuum.github.io/micro-news/ も適宜案内してください。"
        "回答は500文字以内に収めてください。"
    ),
}


# ── Slack API ──

def slack_post(channel, text, thread_ts=None):
    data = {"channel": channel, "text": text, "mrkdwn": True}
    if thread_ts:
        data["thread_ts"] = thread_ts
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"},
        json=data,
    )
    return resp.json().get("ok", False)


# ── Gemini API ──

def ask_gemini(question, channel_name):
    """Gemini APIで回答を生成"""
    system_prompt = SYSTEM_PROMPTS.get(channel_name, SYSTEM_PROMPTS["ai_news"])

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": question}]}
        ],
        "generationConfig": {
            "maxOutputTokens": 1024,
            "temperature": 0.7,
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()

        if "error" in data:
            print(f"Gemini error: {data['error'].get('message', '')[:200]}")
            return None

        candidates = data.get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"]
        return None

    except Exception as e:
        print(f"Gemini request failed: {e}")
        return None


# ── イベント処理 ──

def process_event(event):
    """メンションに即座に応答"""
    text = event.get("text", "")
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts", event.get("ts"))

    channel_name = CHANNELS.get(channel, "ai_news")
    site_url = SITES.get(channel_name, SITES["ai_news"])

    # メンション部分を除去
    clean = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not clean:
        slack_post(channel, f"お呼びですか？ 何でも質問してくださいね！\n🔗 {site_url}", thread_ts)
        return

    # Gemini AIで回答生成
    answer = ask_gemini(clean, channel_name)

    if answer:
        slack_post(channel, answer, thread_ts)
    else:
        # フォールバック
        topic = "AI" if channel_name == "ai_news" else "マイクロビジネス"
        slack_post(
            channel,
            f"ご質問ありがとうございます！\n\n「{clean}」について、最新の{topic}ニュースサイトで詳しく解説しています👇\n🔗 {site_url}",
            thread_ts,
        )


# ── Vercel Serverless Handler ──

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        # Slack URL Verification
        if payload.get("type") == "url_verification":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"challenge": payload["challenge"]}).encode())
            return

        # リトライは無視
        retry_num = self.headers.get("X-Slack-Retry-Num")
        if retry_num:
            self.send_response(200)
            self.end_headers()
            return

        # 先に200を返す
        self.send_response(200)
        self.end_headers()

        # イベント処理
        if payload.get("type") == "event_callback":
            event = payload.get("event", {})
            if event.get("type") == "app_mention" and not event.get("bot_id"):
                channel = event.get("channel", "")
                if channel in CHANNELS:
                    try:
                        process_event(event)
                    except Exception as e:
                        print(f"Error: {e}")
