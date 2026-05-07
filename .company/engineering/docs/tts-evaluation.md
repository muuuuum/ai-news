---
created: "2026-04-15"
topic: "TTS音声合成ツール評価"
type: technical-doc
tags: [tts, voice, youtube, evaluation]
---

# YouTube AI News ナレーション用 TTS ツール評価

> 調査日: 2026-04-15
> 目的: YouTube AI News 動画のナレーション音声生成に最適な TTS ツールを選定
> 注意: Google Cloud TTS 以外の料金は2025年5月時点の知識ベース。最新は各公式サイトを確認のこと

---

## 総合比較表

| ツール | 日本語品質 | コスト | API/CLI | ニュース適合 | セットアップ | 総合 |
|--------|-----------|--------|---------|-------------|-------------|------|
| **Google Cloud TTS** | A | 実質無料~ | REST/SDK/CLI | A+ | 中程度 | **A+** |
| **VOICEVOX** | A | 無料 | REST API | B+ | 簡単 | **A** |
| **Style-Bert-VITS2** | A+ | 無料 | REST API | A | やや難 | **A** |
| **ElevenLabs** | A- | $5-22/月 | REST/SDK | A | 非常に簡単 | **A-** |
| **OpenAI TTS** | B+ | $15-30/100万字 | REST/SDK | B | 非常に簡単 | **B+** |

---

## 推奨: Google Cloud TTS（第1候補）

### 理由
- WaveNet で月400万文字無料 = 個人開発者には実質無料
- SSML で細かい制御が可能（ピッチ・速度・ポーズ）→ ニュース読み上げに最適
- Neural2 も月100万文字無料

### 推奨ボイス
- `ja-JP-Neural2-B`（男性、落ち着いたトーン）
- `ja-JP-Neural2-C`（女性）
- `ja-JP-Wavenet-B`（男性、WaveNet版）

### 料金（2026年4月確認済み）

| モデル | 無料枠/月 | 有料（100万文字あたり） |
|--------|-----------|----------------------|
| Standard | 400万文字 | $4 |
| WaveNet | 400万文字 | $4 |
| Neural2 | 100万文字 | $16 |
| Chirp 3: HD | 100万文字 | $30 |

ニュース1本2,000文字 → 月400万文字枠で **月2,000本** 生成可能（実質無制限）

### セットアップ手順

```bash
# 1. GCP プロジェクト作成 & TTS API 有効化
gcloud services enable texttospeech.googleapis.com

# 2. 認証
gcloud auth application-default login

# 3. Python SDK インストール
pip install google-cloud-texttospeech
```

### コード例（SSML付き）

```python
from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

ssml = """<speak>
<prosody rate="95%" pitch="-1st">
  本日のAIニュースです。<break time="500ms"/>
  Anthropicの Claude Code から、ソースコード約51万2千行が流出しました。
  <break time="300ms"/>
  流出したファイルには、<emphasis level="moderate">44個の未公開フィーチャーフラグ</emphasis>が含まれていました。
</prosody>
</speak>"""

response = client.synthesize_speech(
    input=texttospeech.SynthesisInput(ssml=ssml),
    voice=texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name="ja-JP-Neural2-B"
    ),
    audio_config=texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
        pitch=0.0,
    ),
)

with open("output.mp3", "wb") as f:
    f.write(response.audio_content)
print("音声ファイルを output.mp3 に保存しました")
```

---

## 併用候補: VOICEVOX（コストゼロ枠）

### 理由
- 完全無料、ランニングコストゼロ
- Docker で簡単にAPIサーバー構築
- キャラクタークレジット表記が必要（「VOICEVOX: 四国めたん」等）

### 推奨キャラクター
- **四国めたん ノーマル** (speaker=2): 落ち着いた女性声
- **ずんだもん ノーマル** (speaker=3): 知名度が高く親しみやすい

### セットアップ

```bash
# Docker で起動
docker pull voicevox/voicevox_engine
docker run --rm -d -p 50021:50021 voicevox/voicevox_engine

# テスト
curl -s -X POST "http://localhost:50021/audio_query?text=本日のAIニュースをお伝えします。&speaker=2" \
  | curl -s -X POST "http://localhost:50021/synthesis?speaker=2" \
    -H "Content-Type: application/json" -d @- --output output.wav
```

### 注意
- キャラクター声なので「アナウンサー風」にはならない
- 動画の説明欄にクレジット表記が必要

---

## その他ツール簡易メモ

### ElevenLabs
- 英語ナレーションも併用する場合に最適
- 無料枠: 月10,000文字（約10分）→ 少なすぎて本格運用には$5-22/月が必要
- 音声クローニング機能あり（自分の声でナレーション可能）

### OpenAI TTS
- 既に OpenAI API を使っているなら最も導入が簡単
- 日本語品質は上位に劣る、SSML非対応
- onyx ボイスがニュース向き

### Style-Bert-VITS2
- 日本語の自然さではOSS最高峰
- スタイル制御で「ニュースキャスター風」が可能
- GPU推奨、初期セットアップに手間がかかる
- 将来的に品質追求する場合の最終候補

---

## 推奨ワークフロー

```
[台本 (Markdown)]
    ↓ SSML自動変換スクリプト
[SSML テキスト]
    ↓ Google Cloud TTS API
[ナレーション音声 (MP3)]
    ↓ ffmpeg
[BGM ミックス済み音声]
    ↓ 動画編集パイプライン
[完成動画]
```

## 結論

| 状況 | 推奨ツール |
|------|-----------|
| **本格運用（推奨）** | Google Cloud TTS (WaveNet/Neural2) |
| コストゼロで始めたい | VOICEVOX |
| 最高の日本語品質を追求 | Style-Bert-VITS2 |
| 英語もやる・声カスタマイズ | ElevenLabs |

**最終推奨: Google Cloud TTS を第一候補、VOICEVOX を併用するハイブリッド構成**
