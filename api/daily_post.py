"""
毎日のニュース投稿 (Vercel Cron Job)
JST 9時に ai_news / micro_news チャンネルへ投稿する
"""

import os
import json
import datetime
from http.server import BaseHTTPRequestHandler

import requests

SLACK_BOT_TOKEN = os.environ.get("NEWS_SLACK_BOT_TOKEN", "")
CRON_SECRET = os.environ.get("CRON_SECRET", "")

CHANNELS = {
    "ai_news": "C0AQ1P4M64T",
    "micro_news": "C0AQW2751TK",
}

SITES = {
    "ai_news": "https://muuuuum.github.io/ai-news/",
    "micro_news": "https://muuuuum.github.io/micro-news/",
}


def slack_post(channel, text):
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"},
        json={"channel": channel, "text": text, "mrkdwn": True},
    )
    return resp.json().get("ok", False)


def post_daily_news():
    jst = datetime.timezone(datetime.timedelta(hours=9))
    today = datetime.datetime.now(jst).strftime("%Y年%m月%d日")

    ai_ok = slack_post(
        CHANNELS["ai_news"],
        f"🤖 *AIニュース速報 - {today}*\n\n本日の最新AIニュースを更新しました。\n🔗 {SITES['ai_news']}"
    )

    micro_ok = slack_post(
        CHANNELS["micro_news"],
        f"💼 *マイクロビジネス速報 - {today}*\n\n本日のマイクロビジネス最新ニュースを更新しました。\n🔗 {SITES['micro_news']}"
    )

    return ai_ok, micro_ok


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Vercel Cron からの呼び出し検証
        auth = self.headers.get("Authorization", "")
        if CRON_SECRET and auth != f"Bearer {CRON_SECRET}":
            self.send_response(401)
            self.end_headers()
            return

        ai_ok, micro_ok = post_daily_news()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "ai_news": ai_ok,
            "micro_news": micro_ok,
        }).encode())
