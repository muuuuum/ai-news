#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack Bot: メンション自動返信 + 毎日ニュース投稿
ai-news リポジトリに配置し、リモートトリガーから実行する
"""

import subprocess
import json
import sys
import os
import datetime
import urllib.request
import urllib.parse

TOKEN = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SLACK_BOT_TOKEN", "")
BOT_ID = "U0AQBPK129J"
CHANNELS = {
    "ai_news": "C0AQ1P4M64T",
    "micro_news": "C0AQW2751TK",
}
SITES = {
    "ai_news": "https://muuuuum.github.io/ai-news/",
    "micro_news": "https://muuuuum.github.io/micro-news/",
}

def slack_api(method, data=None):
    """Slack API を呼び出す"""
    url = f"https://slack.com/api/{method}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
    if data:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    else:
        req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"API error ({method}): {e}")
        return {"ok": False, "error": str(e)}

def get_messages(channel_id, limit=10):
    """チャンネルのメッセージを取得"""
    result = slack_api(f"conversations.history?channel={channel_id}&limit={limit}")
    return result.get("messages", []) if result.get("ok") else []

def get_thread(channel_id, ts):
    """スレッド内のメッセージを取得"""
    result = slack_api(f"conversations.replies?channel={channel_id}&ts={ts}")
    return result.get("messages", []) if result.get("ok") else []

def post_message(channel_id, text, thread_ts=None):
    """メッセージを投稿"""
    data = {"channel": channel_id, "text": text, "mrkdwn": True}
    if thread_ts:
        data["thread_ts"] = thread_ts
    result = slack_api("chat.postMessage", data)
    return result.get("ok", False)

def find_unreplied_mentions(channel_name, channel_id):
    """未返信のメンションを検索（トップレベル＋スレッド内）"""
    unreplied = []
    messages = get_messages(channel_id, 15)

    for msg in messages:
        user = msg.get("user", "")
        text = msg.get("text", "")
        ts = msg.get("ts", "")
        reply_count = msg.get("reply_count", 0)

        # トップレベルの未返信メンション
        if user != BOT_ID and f"<@{BOT_ID}>" in text and reply_count == 0:
            unreplied.append({
                "channel": channel_name,
                "channel_id": channel_id,
                "ts": ts,
                "parent_ts": ts,
                "text": text,
                "type": "top",
            })

        # スレッド内もチェック
        if reply_count > 0:
            thread = get_thread(channel_id, ts)
            for i, t_msg in enumerate(thread):
                t_user = t_msg.get("user", "")
                t_text = t_msg.get("text", "")
                t_ts = t_msg.get("ts", "")

                if t_user != BOT_ID and f"<@{BOT_ID}>" in t_text:
                    # このメンションの後にボットの返信があるか確認
                    t_ts_float = float(t_ts)
                    bot_replied = any(
                        float(x.get("ts", "0")) > t_ts_float and x.get("user") == BOT_ID
                        for x in thread
                    )
                    if not bot_replied:
                        unreplied.append({
                            "channel": channel_name,
                            "channel_id": channel_id,
                            "ts": t_ts,
                            "parent_ts": ts,
                            "text": t_text,
                            "type": "thread",
                        })

    return unreplied

def generate_reply(channel_name, question):
    """質問に対する返答を生成"""
    clean_q = question.replace(f"<@{BOT_ID}>", "").strip()

    if not clean_q or clean_q in ["", " "]:
        # 空のメンション
        if channel_name == "ai_news":
            return "お呼びですか？ AI に関する質問があればお気軽にメンションしてください！\n\n最新ニュースはこちら👇\n🔗 " + SITES["ai_news"]
        else:
            return "お呼びですか？ マイクロビジネスに関する質問があればお気軽にメンションしてください！\n\n最新ニュースはこちら👇\n🔗 " + SITES["micro_news"]

    q_lower = clean_q.lower()

    # 要約系
    if "要約" in clean_q or "まとめ" in clean_q:
        if channel_name == "ai_news":
            return ("📌 *本日のAIニュース要約*\n\n"
                    "• *OpenAI* — GPT-5.4 Thinking発表、コンピュータ操作機能を初搭載。GDPVal 83.0%達成\n"
                    "• *Anthropic* — Claude Codeソースコード流出。512K行・44の未公開フラグが露出。ARR $2.5B\n"
                    "• *Salesforce* — Slack をAIエージェント基盤へ刷新、30機能追加。MCP対応\n"
                    "• *Google* — Gemini 3.1 Pro、GPQA Diamond 94.3%で全モデル首位\n"
                    "• *Stripe* — 自律エージェント「Minions」が週1,300件PRを自動生成\n\n"
                    "詳細👇\n🔗 " + SITES["ai_news"])
        else:
            return ("📌 *本日のマイクロビジネスニュース要約*\n\n"
                    "• *Shopify* — AIストア自動生成機能、5分でECサイト構築可能に\n"
                    "• *フリーランス* — 人口500万人突破、前年比18%増\n"
                    "• *Stripe* — マイクロビジネス向け手数料2.5%に引き下げ\n"
                    "• *副業解禁* — 大企業の78%が副業を許可、IT・コンサルが人気\n"
                    "• *e-Tax* — AI自動連携で確定申告の手間が大幅削減\n\n"
                    "詳細👇\n🔗 " + SITES["micro_news"])

    # 話して系
    if "話して" in clean_q or "教えて" in clean_q or "紹介" in clean_q:
        if channel_name == "ai_news":
            return ("最新のAIトピックをお伝えします！ 🤖\n\n"
                    "*注目トレンド:*\n"
                    "• *AIエージェント* が本格普及期に。Stripe, Salesforceが実戦投入\n"
                    "• *MCP（Model Context Protocol）* が9,700万インストール突破、業界標準に\n"
                    "• *コスト低下* — Sonnet 4.6でOpus級性能が1/5の価格で利用可能\n"
                    "• *コンピュータ操作AI* — GPT-5.4がRPA市場に参入\n\n"
                    "気になるトピックがあればメンションしてくださいね！\n🔗 " + SITES["ai_news"])
        else:
            return ("最新のマイクロビジネストレンドをお伝えします！ 💼\n\n"
                    "*注目トレンド:*\n"
                    "• *AIツールで一人起業* — Cursor + Claude Codeで月収100万円のマイクロSaaS事例が増加\n"
                    "• *EC参入の敷居が激減* — Shopify AI機能で5分でストア構築\n"
                    "• *フリーランス市場拡大* — 500万人突破、AI活用で生産性が向上\n"
                    "• *副業解禁の波* — 大企業78%が許可、兼業時代が到来\n\n"
                    "気になるトピックがあればメンションしてくださいね！\n🔗 " + SITES["micro_news"])

    # 副業系
    if "副業" in clean_q or "サイドビジネス" in clean_q or "アイデア" in clean_q:
        return ("副業のアイデアですね！最近のトレンドを紹介します 💡\n\n"
                "*1. AIツール活用のフリーランス*\n"
                "Claude/ChatGPTを使った業務効率化コンサル。月20-50万円も狙えます。\n\n"
                "*2. Notionテンプレート販売*\n"
                "人気テンプレートは月10万円以上の不労所得に。\n\n"
                "*3. マイクロSaaS開発*\n"
                "Cursor + Claude Codeで一人でもSaaS開発。ニッチ課題解決で月50-100万円。\n\n"
                "*4. EC・ドロップシッピング*\n"
                "Shopify AIで5分でストア構築。仕入れ不要で初期費用ほぼゼロ。\n\n"
                "🔗 " + SITES["micro_news"])

    # デフォルト返答
    site = SITES.get(channel_name, SITES["ai_news"])
    topic = "AI" if channel_name == "ai_news" else "マイクロビジネス"
    return (f"ご質問ありがとうございます！\n\n"
            f"「{clean_q}」について、最新の{topic}ニュースサイトで詳しく解説しています👇\n"
            f"🔗 {site}\n\n"
            f"さらに詳しく知りたい場合は、具体的な質問をメンションしてくださいね！")

def handle_mentions():
    """全チャンネルの未返信メンションに返答"""
    total_replied = 0
    for ch_name, ch_id in CHANNELS.items():
        unreplied = find_unreplied_mentions(ch_name, ch_id)
        for mention in unreplied:
            reply_text = generate_reply(ch_name, mention["text"])
            ok = post_message(mention["channel_id"], reply_text, mention["parent_ts"])
            status = "✅" if ok else "❌"
            print(f"{status} [{ch_name}] replied to: {mention['text'][:60]}")
            total_replied += 1 if ok else 0

    if total_replied == 0:
        print("No unreplied mentions found.")
    else:
        print(f"Replied to {total_replied} mention(s).")

def post_daily_news():
    """毎日のニュース投稿（日付+URLのみ）"""
    jst = datetime.timezone(datetime.timedelta(hours=9))
    today = datetime.datetime.now(jst).strftime("%Y年%m月%d日")

    ai_ok = post_message(
        CHANNELS["ai_news"],
        f"🤖 *AIニュース速報 - {today}*\n\n本日の最新AIニュースを更新しました。\n🔗 {SITES['ai_news']}"
    )
    print(f"ai_news daily post: {'✅' if ai_ok else '❌'}")

    micro_ok = post_message(
        CHANNELS["micro_news"],
        f"💼 *マイクロビジネス速報 - {today}*\n\n本日のマイクロビジネス最新ニュースを更新しました。\n🔗 {SITES['micro_news']}"
    )
    print(f"micro_news daily post: {'✅' if micro_ok else '❌'}")

def main():
    print(f"=== Slack Bot started at {datetime.datetime.utcnow().isoformat()}Z ===")

    # Step 1: 常にメンション返信を実行
    print("\n--- Step 1: Checking mentions ---")
    handle_mentions()

    # Step 2: UTC 0時台のみニュース投稿
    utc_hour = datetime.datetime.utcnow().hour
    if utc_hour == 0:
        print("\n--- Step 2: Daily news posting (UTC 0) ---")
        post_daily_news()
    else:
        print(f"\n--- Step 2: Skipped (UTC hour={utc_hour}, not 0) ---")

    print("\n=== Done ===")

if __name__ == "__main__":
    main()
