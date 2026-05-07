#!/usr/bin/env python3
"""
YouTube AI News TTS音声生成スクリプト
edge-tts (Microsoft Edge TTS) を使用 — 無料・API キー不要

使い方:
  python3 generate_tts.py
"""

import asyncio
import edge_tts
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# === 音声設定 ===
# ja-JP-KeitaNeural: 男性、落ち着いたトーン
# ja-JP-NanamiNeural: 女性、フレンドリー
VOICE = "ja-JP-KeitaNeural"
RATE = "-5%"      # やや遅め（ニュース向き）
PITCH = "-2Hz"    # やや低め（落ち着いた印象）


async def generate_audio(text, filename, voice=VOICE, rate=RATE, pitch=PITCH):
    """テキストから音声ファイルを生成"""
    output_path = os.path.join(OUTPUT_DIR, filename)
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)
    print(f"生成完了: {output_path}")
    return output_path


async def main():
    # === HOOK セクション ===
    hook_text = (
        "Anthropicの Claude Code、ソースコード約51万2千行が流出しました。"
        "npmのパッケージングミスが原因で、約1900ファイルがそのまま公開状態に。"
        "中には44個の未公開フィーチャーフラグが含まれていて、"
        "Anthropicのロードマップが丸見えの状態でした。"
        "今日はこのニュースを詳しく解説するほか、"
        "OpenAI GPT-5.4のコンピュータ操作機能と、"
        "SalesforceのSlack AI全面刷新についてもお伝えします。"
    )

    # === OP セクション ===
    op_text = (
        "AI News Daily。世界のAI最新ニュースを毎日お届けします。"
        "2026年4月3日、今日のラインナップです。"
        "1つ目、Claude Code ソースコード51万行が流出。"
        "2つ目、OpenAI GPT-5.4 Thinking、コンピュータ操作を初搭載。"
        "3つ目、Salesforce、SlackをAIエージェント基盤に全面刷新。"
        "では、早速いきましょう。"
    )

    # === ニュース1 WHAT セクション ===
    news1_what = (
        "Anthropicが提供するコーディングツール「Claude Code」のソースコードが、"
        "npmパッケージの公開ミスにより流出しました。"
        "流出したのは約1900ファイル、51万2千行にのぼります。"
        "特に問題なのは、コード内に44個のフィーチャーフラグ、"
        "つまり未公開機能のオンオフスイッチが含まれていたことです。"
        "これにより、Anthropicが今後実装を予定している機能の一端が明らかになりました。"
    )

    # === まとめセクション ===
    wrap_text = (
        "今日のポイントをまとめます。"
        "1つ目、Anthropic Claude Codeのソースコード51万行が流出。"
        "44個の未公開機能が判明し、npmパッケージ管理の重要性が再認識されました。"
        "2つ目、OpenAIがGPT-5.4 Thinkingを発表。"
        "ネイティブのコンピュータ操作機能で、OSWorldのベンチマーク記録を更新しました。"
        "3つ目、SalesforceがSlackをAIエージェント基盤に刷新。"
        "30機能が追加され、MCP対応で外部システムとの連携が強化されました。"
        "つまり、今週のAI業界は、"
        "AIがコードを書き、PCを操作し、業務ツールで動く、"
        "というエージェント時代の到来を象徴するニュースが揃いました。"
    )

    # === CTA セクション ===
    cta_text = (
        "AI News Dailyでは、こうしたAIの最新動向を毎日お届けしています。"
        "気になった方はチャンネル登録をお願いします。"
        "コメント欄で「あなたが注目しているAIエージェントツール」を教えてください。"
        "概要欄に今日紹介したニュースのソースリンクをまとめています。"
        "それでは、また明日。"
    )

    # 各セクションを生成
    print("=== TTS音声生成開始 ===\n")

    print("[1/5] HOOK セクション...")
    await generate_audio(hook_text, "tts_01_hook.mp3")

    print("[2/5] OP セクション...")
    await generate_audio(op_text, "tts_02_op.mp3")

    print("[3/5] ニュース1 (WHAT) セクション...")
    await generate_audio(news1_what, "tts_03_news1_what.mp3")

    print("[4/5] まとめセクション...")
    await generate_audio(wrap_text, "tts_04_wrap.mp3")

    print("[5/5] CTA セクション...")
    await generate_audio(cta_text, "tts_05_cta.mp3")

    # フル版（全セクション結合テキスト）
    full_text = hook_text + op_text + news1_what + wrap_text + cta_text
    print("\n[FULL] フルバージョン...")
    await generate_audio(full_text, "tts_full_sample.mp3")

    print("\n=== 全音声生成完了! ===")
    print(f"出力先: {OUTPUT_DIR}/tts_*.mp3")


if __name__ == "__main__":
    asyncio.run(main())
