---
created: "2026-04-15"
topic: "TTS日本語ナレーション品質向上ガイド"
type: technical-doc
tags: [tts, ssml, japanese, quality, ffmpeg]
---

# TTS日本語ナレーション品質向上ガイド

> edge-tts (ja-JP-KeitaNeural) を使用中の前提で、自然さを段階的に改善する方法。

---

## 1. SSML テクニック（即効性あり）

### ポーズ制御
```xml
<break time="1200ms"/>  <!-- ニュース見出し→本文の間 -->
<break time="600ms"/>   <!-- 箇条書き的列挙の間 -->
<break time="300ms"/>   <!-- 重要キーワードの前の「溜め」 -->
```

### mstts:silence（edge-tts固有、最も費用対効果が高い）
```xml
<mstts:silence type="Sentenceboundary" value="400ms"/>
<!-- 全文の文境界で一律400msのポーズ → 落ち着いた印象 -->
```

### 英語固有名詞の読み方制御
```xml
<sub alias="クロード">Claude</sub>
<sub alias="オープンエーアイ">OpenAI</sub>
<sub alias="アンソロピック">Anthropic</sub>
```

### Python前処理辞書（推奨）
```python
PRONUNCIATION_DICT = {
    "Claude": "クロード", "OpenAI": "オープンエーアイ",
    "GPT-4": "ジーピーティーフォー", "Anthropic": "アンソロピック",
    "LLM": "エルエルエム", "API": "エーピーアイ",
    "NVIDIA": "エヌビディア", "$1.5B": "15億ドル",
}
```

### プロソディ制御（ニュースキャスター風）
```xml
<prosody pitch="-3%" rate="0.93" volume="+5%">
    本日のAIニュースをお伝えします。
</prosody>
```

---

## 2. 台本の書き方ルール（TTS向き）

### 1文の最適な長さ
- **20〜35文字**: 最も自然（短い事実文）
- **35〜50文字**: 説明文（読点1つ）
- **50〜70文字**: 許容範囲（読点2つ以内）
- **70文字以上**: 分割必須

### 読点ルール
- 主語の後、長い修飾語の後、接続詞の後、数値の前
- 1文に読点1〜2個が最適。3個以上は分割サイン

### 避けるべき
- 括弧の多用（`<sub>` に前処理する）
- 記号（→, ※, /）→ 日本語に置換
- 体言止めの連続
- 70文字以上の文

---

## 3. ffmpeg ポストプロセスチェーン

```bash
ffmpeg -i tts_output.mp3 \
  -af "
    highpass=f=80,
    lowpass=f=16000,
    agate=threshold=0.01:ratio=2:attack=10:release=100,
    acompressor=threshold=-20dB:ratio=4:attack=5:release=50:makeup=2dB,
    equalizer=f=200:t=q:w=1.5:g=-2,
    equalizer=f=3000:t=q:w=1.0:g=3,
    equalizer=f=8000:t=q:w=1.0:g=1,
    alimiter=limit=0.95:attack=5:release=50,
    loudnorm=I=-14:TP=-1.5:LRA=11
  " \
  -ar 48000 -ac 1 output_processed.mp3
```

| 処理 | 効果 |
|------|------|
| ハイパス 80Hz | 低域ノイズ除去 |
| ローパス 16kHz | TTSアーティファクト除去 |
| ノイズゲート | 無音部分のヒスノイズ除去 |
| コンプレッサー -20dB 4:1 | 音量均一化 |
| EQ 3kHz +3dB | 明瞭度・プレゼンス向上 |
| ラウドネス正規化 -14 LUFS | YouTube推奨値 |

### BGMミックス（サイドチェインダッキング）
```bash
ffmpeg -i narration.mp3 -i bgm.mp3 \
  -filter_complex "
    [1:a]volume=-16dB[bgm_vol];
    [bgm_vol][0:a]sidechaincompress=
      threshold=0.02:ratio=6:attack=200:release=1000[bgm_ducked];
    [0:a][bgm_ducked]amix=inputs=2:duration=first[out]
  " -map "[out]" final_with_bgm.mp3
```

---

## 4. 改善ロードマップ

### Phase 1（即座、コスト0）
1. テキスト前処理辞書の作成
2. SSML化（break + prosody + mstts:silence）
3. ffmpegポストプロセスチェーン導入

### Phase 2（1-2週間）
1. Google Cloud TTS Neural2 との品質比較
2. BGMミックス自動化
3. サイドチェインコンプレッション導入

### Phase 3（長期）
1. Style-Bert-VITS2 でオリジナル声学習
2. A/Bテストによる視聴者反応測定
