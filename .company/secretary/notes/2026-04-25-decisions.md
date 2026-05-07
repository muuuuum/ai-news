---
date: "2026-04-25"
type: decisions
---

# 意思決定ログ - 2026-04-25

## TTS音声の方向性確定
- **決定**: YouTube AI News の音声は `en-US-BrianMultilingualNeural`（多言語男性ボイス）を採用
- **背景**: 4ボイスを聴き比べた結果、Brian Multi が最も印象に残る声質と評価
- **経緯**:
  - v1: edge-tts プレーンテキスト → 棒読み
  - v2: SSMLが実はエスケープされて効いていなかった問題を発見・修正
  - v2改: 文ごとに個別生成＋pydub結合方式に切替。Keita High（男性声高め）を選択
  - v3: 会話調台本 + 多言語ボイス比較 + ffmpeg warmth加工。Brian Multi に確定
- **今後のTTS改善方針**:
  - 台本は会話調（「来ました。」「で、これ何がすごいかっていうと」等）
  - 緩急ロール（BANG/HYPE/RUSH/BUILD/SOFT/NORM）で文単位にプロソディ制御
  - ffmpegで14kHzローパス + 2.5kHz存在感EQ + コンプ + ラウドネス正規化
  - キャラクター・プロフィール設定は今後別途行う
