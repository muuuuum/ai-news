#!/usr/bin/env python3
"""
動画用アセット一括生成

1. Veoで記事映像を動画クリップとして生成
2. TTS音声を生成（Brian Multilingual + pydub結合）
3. 結果をoutput/に保存
"""

import requests, json, time, base64, os, sys, asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

API_KEY = os.environ.get("GEMINI_API_KEY", "")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT = os.path.join(PROJECT_ROOT, "output")
VIDEOS_DIR = os.path.join(OUTPUT, "videos")
AUDIO_DIR = os.path.join(OUTPUT, "audio")

os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)


def generate_veo_video(prompt: str, filename: str) -> bool:
    """Veo 3.0 fast で動画を生成"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/veo-3.0-fast-generate-001:predictLongRunning?key={API_KEY}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1, "aspectRatio": "16:9", "durationSeconds": 8}
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        if "error" in data:
            print(f"    エラー: {data['error']['message'][:100]}")
            return False

        op_name = data["name"]
        print(f"    生成開始: {op_name}")

        for i in range(90):
            time.sleep(5)
            check = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/{op_name}?key={API_KEY}", timeout=15
            ).json()

            if check.get("done"):
                videos = check.get("response", {}).get("generateVideoResponse", {}).get("generatedSamples", [])
                if videos:
                    uri = videos[0].get("video", {}).get("uri", "")
                    if uri:
                        vid_resp = requests.get(uri, headers={"x-goog-api-key": API_KEY}, timeout=120)
                        if vid_resp.status_code == 200 and len(vid_resp.content) > 1000:
                            path = os.path.join(VIDEOS_DIR, filename)
                            with open(path, "wb") as f:
                                f.write(vid_resp.content)
                            print(f"    ✓ {filename} ({len(vid_resp.content)//1024}KB)")
                            return True
                print(f"    動画データ取得失敗")
                return False

            print(f"    待機中... ({i*5}秒)", end="\r")

        print(f"    タイムアウト")
        return False

    except Exception as e:
        print(f"    エラー: {e}")
        return False


async def generate_tts(text: str, filename: str):
    """Brian Multilingual でTTS音声を生成"""
    import edge_tts
    from pydub import AudioSegment

    VOICE = "en-US-BrianMultilingualNeural"
    PRONUNCIATION = {
        "Google": "グーグル", "Anthropic": "アンソロピック",
        "AI": "エーアイ", "Mythos": "ミソス",
        "Veo": "ヴェオ", "DeepSeek": "ディープシーク",
    }

    processed = text
    for eng, jpn in sorted(PRONUNCIATION.items(), key=lambda x: -len(x[0])):
        processed = processed.replace(eng, jpn)

    path = os.path.join(AUDIO_DIR, filename)
    communicate = edge_tts.Communicate(processed, voice=VOICE, rate="-5%", pitch="+0Hz")
    await communicate.save(path)
    print(f"    ✓ {filename}")


def main():
    print("=" * 60)
    print("  動画アセット一括生成")
    print("=" * 60)

    # ===== 1. 記事映像（Veo） =====
    print("\n🎬 記事映像をVeoで生成中...")

    news_videos = [
        ("news_clip_01.mp4", """Professional news broadcast animation about Google investing 6 trillion yen in Anthropic AI company.
Show: Flowing data streams, partnership handshake, golden coins, tech company logos merging.
Style: Clean modern motion graphics, light background, blue and gold tones.
Smooth professional animation. News quality. No text."""),
    ]

    for filename, prompt in news_videos:
        print(f"\n  {filename}:")
        generate_veo_video(prompt, filename)

    # ===== 2. 音声（TTS） =====
    print("\n🎤 音声生成中...")

    scripts = {
        "opening.mp3": "未来からおはよう、ミライです。2089年から来ました。信じなくていいよ。",
        "headline.mp3": "今日のニュース。グーグルが、アンソロピックに、約6兆円を投資します。",
        "explain_1.mp3": "グーグルはエーアイスタートアップのアンソロピックに対し、現金と計算資源を合わせて、最大約6兆円を投資する計画です。",
        "explain_2.mp3": "アンソロピックがサイバーセキュリティ特化型モデル、ミソスを限定公開した直後の動きで、エーアイ企業間の計算能力確保競争が激化しています。",
        "impact.mp3": "ボクの時代だと、これは始まりの一歩って呼ばれてる。覚えておいて。",
        "ending.mp3": "明日も、未来は来るよ。またね、人間さん。チャンネル、置いていかないで。",
    }

    for filename, text in scripts.items():
        print(f"  {filename}:")
        asyncio.run(generate_tts(text, filename))
        time.sleep(1)

    print("\n" + "=" * 60)
    print("  完了!")
    print("=" * 60)


if __name__ == "__main__":
    main()
