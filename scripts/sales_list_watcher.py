#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
営業リストBot 常駐モード
10秒ごとにSlackをチェックし、即座に返信する
"""

import time
import sys
import os
import datetime

# sales_list_bot の関数を再利用
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sales_list_bot as bot

POLL_INTERVAL = 10  # 秒


def main():
    token = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SLACK_BOT_TOKEN", "")
    channel_id = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("SALES_CHANNEL_ID", "C0AR48QHRGB")

    bot.TOKEN = token
    bot.CHANNEL_ID = channel_id
    bot.init_excel()

    jst = datetime.timezone(datetime.timedelta(hours=9))
    print(f"=== 営業リストBot 常駐モード開始 ===")
    print(f"チャンネル: {channel_id}")
    print(f"ポーリング間隔: {POLL_INTERVAL}秒")
    print(f"終了するには Ctrl+C\n")

    while True:
        try:
            unreplied = bot.find_unreplied_mentions(channel_id)
            if unreplied:
                now = datetime.datetime.now(jst).strftime("%H:%M:%S")
                print(f"[{now}] メンション {len(unreplied)}件 検出")
                for mention in unreplied:
                    reply_text = bot.process_mention(mention)
                    ok = bot.post_message(channel_id, reply_text, mention["parent_ts"])
                    status = "✅" if ok else "❌"
                    print(f"  {status} {mention['text'][:60]}")
        except Exception as e:
            print(f"⚠️ エラー: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
