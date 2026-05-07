#!/usr/bin/env python3
"""
YouTube AI News TTS音声生成 v2 — エンタメ×ニュース版

戦略: edge-ttsはSSMLの break/複数prosody を受け付けないため、
文ごとに個別の prosody 設定で生成し、pydub で間（無音）を挟みながら結合する。
これにより文単位の緩急・間・キャラクター表現を実現。

使い方:
  python3 generate_tts_v2.py
"""

import asyncio
import edge_tts
import os
import tempfile
from pydub import AudioSegment

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# === 英語固有名詞 → 日本語読み辞書 ===
PRONUNCIATION_DICT = {
    "Claude Code": "クロードコード",
    "Claude": "クロード",
    "OpenAI": "オープンエーアイ",
    "GPT-5.4": "ジーピーティー ゴーテンヨン",
    "GPT": "ジーピーティー",
    "Anthropic": "アンソロピック",
    "LLM": "エルエルエム",
    "API": "エーピーアイ",
    "NVIDIA": "エヌビディア",
    "Google": "グーグル",
    "Gemini": "ジェミニ",
    "AI": "エーアイ",
    "MCP": "エムシーピー",
    "Slack": "スラック",
    "Salesforce": "セールスフォース",
    "npm": "エヌピーエム",
    "Stripe": "ストライプ",
    "OSWorld": "オーエスワールド",
}


def replace_pronunciations(text: str) -> str:
    """固有名詞を日本語読みに変換"""
    result = text
    for eng, jpn in sorted(PRONUNCIATION_DICT.items(), key=lambda x: -len(x[0])):
        result = result.replace(eng, jpn)
    return result


async def generate_segment(text: str, voice: str, rate: str, pitch: str, volume: str = "+0%") -> AudioSegment:
    """1文を指定パラメータで生成し AudioSegment として返す"""
    processed = replace_pronunciations(text)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    try:
        communicate = edge_tts.Communicate(processed, voice=voice, rate=rate, pitch=pitch, volume=volume)
        await communicate.save(tmp_path)
        return AudioSegment.from_mp3(tmp_path)
    finally:
        os.unlink(tmp_path)


def silence(ms: int) -> AudioSegment:
    """指定ミリ秒の無音を生成"""
    return AudioSegment.silent(duration=ms)


# ──────────────────────────────────────────
# セグメント定義
#
# 各文に role を設定:
#   "impact"  → 遅く、低く、大きく。事実をドンと置く
#   "hype"    → 速く、高く。テンション上げ、ワクワク感
#   "buildup" → やや速く、高め。次の impact への助走
#   "punch"   → かなり遅く、大きく。最大の強調
#   "chill"   → 普通〜やや遅。落ち着いたトーン
# ──────────────────────────────────────────

ROLES = {
    "impact":  {"rate": "-18%", "pitch": "-4Hz", "volume": "+8%"},
    "hype":    {"rate": "+12%", "pitch": "+8Hz", "volume": "+5%"},
    "buildup": {"rate": "+5%",  "pitch": "+5Hz", "volume": "+3%"},
    "punch":   {"rate": "-25%", "pitch": "-2Hz", "volume": "+12%"},
    "chill":   {"rate": "-5%",  "pitch": "+1Hz", "volume": "+0%"},
}


def build_script():
    """
    台本: (テキスト, 役割, 直後の無音ms)

    緩急の流れ:
      impact → 長い間 → buildup → punch → 長い間（話題転換）
      を繰り返して波を作る
    """
    return [
        # --- 冒頭ドカン ---
        ("OpenAIが、新モデル、",                           "buildup", 200),
        ("GPT-5.4を発表しました。",                        "impact",  1200),

        # --- 特徴: 助走→溜め→ドン ---
        ("最大の特徴は、",                                  "hype",    500),
        ("AIがコンピュータを、直接操作できる機能です。",      "punch",   1000),

        # --- ベンチマーク ---
        ("ベンチマークでは従来モデルを大きく上回り、",        "buildup", 250),
        ("OSWorldで、歴代最高スコアを記録しています。",      "impact",  1500),

        # --- 話題転換 ---
        ("一方、",                                          "hype",    200),
        ("Anthropicも負けていません。",                      "impact",  800),

        # --- Claude Code ---
        ("Claude Codeのアップデートにより、コーディング性能が、", "buildup", 200),
        ("大幅に向上。",                                    "punch",   700),

        # --- 未来描写: ワクワク→決め ---
        ("エージェントが自律的にコードを書き、テストし、",    "hype",    200),
        ("デプロイまで完了する世界が、",                      "buildup", 400),
        ("近づいています。",                                "punch",   1500),

        # --- Salesforce ---
        ("さらに、SalesforceがSlackを全面刷新。",           "hype",    600),
        ("AIエージェント基盤として、",                       "buildup", 300),
        ("30の新機能を追加しました。",                       "impact",  1500),

        # --- 締め ---
        ("つまり今週のAI業界は、",                           "hype",    600),
        ("AIが実際に仕事をこなす時代の、",                   "buildup", 400),
        ("幕開けを告げるニュースが揃いました。",              "punch",   0),
    ]


async def build_audio(voice: str, script: list, label: str) -> AudioSegment:
    """スクリプトから音声を組み立てる"""
    combined = AudioSegment.empty()
    total = len(script)

    for i, (text, role, pause_ms) in enumerate(script):
        params = ROLES[role]
        print(f"    [{i+1}/{total}] {role:8s} | {text[:20]}...")
        seg = await generate_segment(text, voice, **params)
        combined += seg
        if pause_ms > 0:
            combined += silence(pause_ms)

    return combined


async def main():
    script = build_script()
    full_text = "".join(t for t, _, _ in script)

    print("=== TTS音声生成 v2（エンタメ×ニュース版）===\n")
    print(f"テキスト（{len(full_text)}文字）\n")

    # ──────────────────────────────────────────
    # A: Nanami（女性・明るい）
    # ──────────────────────────────────────────
    print("[1/3] A: Nanami（女性）")
    audio_a = await build_audio("ja-JP-NanamiNeural", script, "A")
    path_a = os.path.join(OUTPUT_DIR, "sample_A_nanami.mp3")
    audio_a.export(path_a, format="mp3", bitrate="128k")
    print(f"  → {path_a} ({len(audio_a)/1000:.1f}秒)\n")

    # ──────────────────────────────────────────
    # B: Keita（男性）全体ピッチ+6Hz
    # ──────────────────────────────────────────
    print("[2/3] B: Keita High（高め男性）")
    script_high = []
    for text, role, pause_ms in script:
        params = ROLES[role].copy()
        # ピッチをさらに+6Hz上乗せ
        base_pitch = int(params["pitch"].replace("Hz", "").replace("+", ""))
        params_mod_pitch = f"+{base_pitch + 6}Hz" if base_pitch + 6 >= 0 else f"{base_pitch + 6}Hz"
        script_high.append((text, role, pause_ms))
    # Keita用にROLESを一時的に調整
    original_roles = {}
    for role_name, role_params in ROLES.items():
        original_roles[role_name] = role_params.copy()
        base = int(role_params["pitch"].replace("Hz", "").replace("+", ""))
        new = base + 6
        ROLES[role_name]["pitch"] = f"+{new}Hz" if new >= 0 else f"{new}Hz"

    audio_b = await build_audio("ja-JP-KeitaNeural", script, "B")
    path_b = os.path.join(OUTPUT_DIR, "sample_B_keita_high.mp3")
    audio_b.export(path_b, format="mp3", bitrate="128k")
    print(f"  → {path_b} ({len(audio_b)/1000:.1f}秒)\n")

    # ROLESを復元
    for role_name in ROLES:
        ROLES[role_name] = original_roles[role_name]

    # ──────────────────────────────────────────
    # C: Nanami Low（落ち着いた女性）全体ピッチ-4Hz
    # ──────────────────────────────────────────
    print("[3/3] C: Nanami Low（落ち着いた女性）")
    for role_name, role_params in ROLES.items():
        original_roles[role_name] = role_params.copy()
        base = int(role_params["pitch"].replace("Hz", "").replace("+", ""))
        new = base - 4
        ROLES[role_name]["pitch"] = f"+{new}Hz" if new >= 0 else f"{new}Hz"

    audio_c = await build_audio("ja-JP-NanamiNeural", script, "C")
    path_c = os.path.join(OUTPUT_DIR, "sample_C_nanami_low.mp3")
    audio_c.export(path_c, format="mp3", bitrate="128k")
    print(f"  → {path_c} ({len(audio_c)/1000:.1f}秒)\n")

    # ROLESを復元
    for role_name in ROLES:
        ROLES[role_name] = original_roles[role_name]

    print("=== 全3パターン生成完了 ===\n")
    print("  sample_A_nanami.mp3      — 女性（明るい・エンタメ寄り）")
    print("  sample_B_keita_high.mp3  — 男性（声高め）")
    print("  sample_C_nanami_low.mp3  — 女性（落ち着き）")
    print("\nどの声が印象に残るか教えてください！")


if __name__ == "__main__":
    asyncio.run(main())
