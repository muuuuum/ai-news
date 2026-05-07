#!/usr/bin/env python3
"""
YouTube AI News TTS v3 — AI感を消す

戦略:
  1. 台本を会話調に（「伝えたい人が話す」テンション）
  2. 文を細かく分割、緩急の波を大きく
  3. 多言語ボイスも含めて比較
  4. ffmpegで音声をウォームに加工（EQ・コンプ・ラウドネス）
"""

import asyncio
import edge_tts
import os
import subprocess
import tempfile
from pydub import AudioSegment

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

PRONUNCIATION_DICT = {
    "Claude Code": "クロードコード",
    "Claude": "クロード",
    "OpenAI": "オープンエーアイ",
    "GPT-5.4": "ジーピーティー ゴーテンヨン",
    "GPT": "ジーピーティー",
    "Anthropic": "アンソロピック",
    "AI": "エーアイ",
    "MCP": "エムシーピー",
    "Slack": "スラック",
    "Salesforce": "セールスフォース",
    "OSWorld": "オー��スワールド",
}


def replace_pronunciations(text: str) -> str:
    result = text
    for eng, jpn in sorted(PRONUNCIATION_DICT.items(), key=lambda x: -len(x[0])):
        result = result.replace(eng, jpn)
    return result


async def gen_seg(text: str, voice: str, rate: str, pitch: str, volume: str = "+0%") -> AudioSegment:
    processed = replace_pronunciations(text)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    try:
        c = edge_tts.Communicate(processed, voice=voice, rate=rate, pitch=pitch, volume=volume)
        await c.save(tmp)
        return AudioSegment.from_mp3(tmp)
    finally:
        os.unlink(tmp)


def silence(ms: int) -> AudioSegment:
    return AudioSegment.silent(duration=ms)


# ──────────────────────────────────────────
# ロール: さらに極端に振る
# ──────────────────────────────────────────
ROLES = {
    # ドカン: めちゃくちゃ遅く、低く、デカく。一番大事なところ
    "BANG":    {"rate": "-28%", "pitch": "-5Hz", "volume": "+12%"},
    # 速い盛り上げ: テンション高、速い
    "HYPE":    {"rate": "+15%", "pitch": "+10Hz", "volume": "+5%"},
    # 助走: やや速く高め
    "BUILD":   {"rate": "+8%",  "pitch": "+6Hz",  "volume": "+3%"},
    # 普通: ニュートラル
    "NORM":    {"rate": "-3%",  "pitch": "+1Hz",  "volume": "+0%"},
    # ささやき的: 小さく遅く。次の BANG との落差を作る
    "SOFT":    {"rate": "-10%", "pitch": "-2Hz",  "volume": "-5%"},
    # 超速: 情報を一気に流す
    "RUSH":    {"rate": "+20%", "pitch": "+8Hz",  "volume": "+3%"},
}


def build_script():
    """
    会話調の台本。ニ��ースキャスターではなく
    「友達にニュースを教えるテンション」で書く。
    """
    return [
        # --- 冒頭: 低く入ってドカン ---
        ("来ました。",                                       "SOFT",  300),
        ("OpenAIが、",                                       "BUILD", 200),
        ("GPT-5.4、発表です。",                              "BANG",  1200),

        # --- 特徴: 速く振って→溜めて→ドン ---
        ("で、これ何がすごいかっていうと、",                    "HYPE",  400),
        ("AIが、",                                           "SOFT",  300),
        ("パソコンを直接操作できるんですよ。",                  "BANG",  1000),

        # --- ベンチマーク: 速く→決め ---
        ("ベンチマークもぶっちぎりで、",                       "RUSH",  200),
        ("OSWorld、歴代最高スコア。",                         "BANG",  1500),

        # --- 話題転換: テンション維持 ---
        ("でね、",                                           "HYPE",  150),
        ("Anthropicも負けてないんですよ。",                    "BUILD", 700),

        # --- Claude Code ---
        ("Claude Codeがアップデートされて、",                  "RUSH",  150),
        ("コーディング性能、大幅に向上。",                     "NORM",  600),

        # --- 未来: ワクワク→ゆっくり決め ---
        ("もうね、",                                         "HYPE",  200),
        ("エージェントが勝手にコード書いて、テストして、",       "RUSH",  150),
        ("デプロイまで終わらせる。",                           "BUILD", 400),
        ("そういう世界が来てます。",                           "BANG",  1500),

        # --- Salesforce ---
        ("さらに。",                                         "HYPE",  300),
        ("SalesforceがSlack全面刷新。",                      "BUILD", 200),
        ("30個、新機能追加です。",                             "BANG",  1500),

        # --- 締め ---
        ("つまり今週は、",                                    "HYPE",  500),
        ("AIが本当に仕事をする時代が来た、",                   "BUILD", 300),
        ("そう言えるニュースが揃いました。",                    "BANG",  0),
    ]


def apply_warmth(input_path: str, output_path: str):
    """
    ffmpegで音声を「生っぽく」加工:
    - ハイパス80Hz: 低域ノイズ除去
    - ローパス14kHz: TTS特有の高域アーティファクト除去（キンキン消し）
    - コンプレッサー: 音量を均一にして聴きやすく
    - EQ 2.5kHz +4dB: 声のプレゼンス（存在感）を���調
    - EQ 200Hz -3dB: こもり除去
    - EQ 6kHz +2dB: 子音のクリスプさ
    - ラウドネス正規化 -14 LUFS: YouTube推奨値
    """
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", ",".join([
            "highpass=f=80",
            "lowpass=f=14000",
            "acompressor=threshold=-18dB:ratio=3:attack=10:release=80:makeup=3dB",
            "equalizer=f=200:t=q:w=1.5:g=-3",
            "equalizer=f=2500:t=q:w=1.2:g=4",
            "equalizer=f=6000:t=q:w=1.0:g=2",
            "alimiter=limit=0.95:attack=5:release=50",
            "loudnorm=I=-14:TP=-1.5:LRA=11",
        ]),
        "-ar", "48000", "-ac", "1",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)


async def build_audio(voice: str, script: list) -> AudioSegment:
    combined = AudioSegment.empty()
    total = len(script)
    for i, (text, role, pause_ms) in enumerate(script):
        params = ROLES[role]
        print(f"    [{i+1:2d}/{total}] {role:5s} | {text}")
        seg = await gen_seg(text, voice, **params)
        combined += seg
        if pause_ms > 0:
            combined += silence(pause_ms)
    return combined


async def main():
    script = build_script()

    print("=== TTS v3 — AI感を消す ===\n")

    voices = [
        ("ja-JP-KeitaNeural",                 "+6Hz",  "keita_high",     "Keita High（前回B）"),
        ("en-US-AndrewMultilingualNeural",     "+0Hz",  "andrew_multi",   "Andrew Multi（多言語男性）"),
        ("en-US-BrianMultilingualNeural",      "+0Hz",  "brian_multi",    "Brian Multi（多言語男性）"),
        ("ko-KR-HyunsuMultilingualNeural",     "+0Hz",  "hyunsu_multi",   "Hyunsu Multi（多言語男���）"),
    ]

    for voice_name, pitch_offset, file_label, display_name in voices:
        print(f"\n[{display_name}]")

        # ピッチオフセットをROLESに反映
        original = {}
        if pitch_offset != "+0Hz":
            offset = int(pitch_offset.replace("Hz", "").replace("+", ""))
            for role_name, params in ROLES.items():
                original[role_name] = params["pitch"]
                base = int(params["pitch"].replace("Hz", "").replace("+", ""))
                new = base + offset
                ROLES[role_name]["pitch"] = f"+{new}Hz" if new >= 0 else f"{new}Hz"

        audio = await build_audio(voice_name, script)

        # 元に戻す
        if original:
            for role_name, pitch_val in original.items():
                ROLES[role_name]["pitch"] = pitch_val

        # Raw版を保存
        raw_path = os.path.join(OUTPUT_DIR, f"v3_{file_label}_raw.mp3")
        audio.export(raw_path, format="mp3", bitrate="192k")
        print(f"  → raw: {raw_path} ({len(audio)/1000:.1f}秒)")

        # ffmpeg で温かみを加える
        warm_path = os.path.join(OUTPUT_DIR, f"v3_{file_label}_warm.mp3")
        apply_warmth(raw_path, warm_path)
        print(f"  → warm: {warm_path}")

    print("\n=== 全生成完了 ===\n")
    print("聴き比べポイント:")
    print("  1. _raw vs _warm → ffmpeg加工の効果")
    print("  2. keita vs andrew vs brian vs hyunsu → 声質の違い")
    print("  3. 会話調の台本 → AI感が減ったか")


if __name__ == "__main__":
    asyncio.run(main())
