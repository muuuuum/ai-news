---
created: "2026-04-15"
topic: "無料動画制作ツール調査"
type: note
tags: [youtube, video, tools, free, production]
---

# 無料ツールでのサムネイル・動画制作クオリティ調査

> 調査日: 2026-04-15

---

## サムネイル制作（無料）

| ツール | 適合度 | 用途 |
|--------|--------|------|
| **Figma Free** | A+ | 量産ワークフロー（コンポーネント + バリアント） |
| **Canva Free** | A | 単発で速く作る場合 |
| **Python Pillow** | A | プログラマティック量産（既存スクリプト） |
| Photopea | A- | PSD互換が必要な場合 |

AI画像生成で素材作成:
- **Ideogram**: テキスト描画が最も正確（サムネ素材に最適）
- **Bing Image Creator (DALL-E 3)**: 無制限、背景・イメージ画像に

---

## 動画編集（無料）

| ツール | 適合度 | 特徴 |
|--------|--------|------|
| **FFmpeg** | A | 80%カバー。スライドショー+字幕+BGMミックス |
| **Remotion** | A+ | React + TSでリッチ動画。コンポーネント再利用。個人無料 |
| **DaVinci Resolve** | A+ | 業界標準級。手動編集なら最強 |
| CapCut | A | 自動字幕、テンプレ豊富。ByteDance製 |
| Motion Canvas | A- | アニメーション特化 |

### FFmpegでできること
- スライドショー（Ken Burnsズーム付き）
- TTS音声 + BGMミックス（音量バランス調整）
- SRT字幕の焼き付け（フォント・色・縁取り指定）
- フェード/クロスフェードトランジション

---

## BGM・SE（無料・商用可）

| サービス | 特徴 |
|---------|------|
| **YouTube Audio Library** | 最も安全。著作権問題ゼロ |
| **DOVA-SYNDROME** | 日本語、テクノロジー系BGM豊富 |
| **効果音ラボ** | 日本語SE定番。帰属不要 |
| Pixabay Music | 数万曲、帰属不要 |
| **魔王魂** | 定番フリーBGM |

---

## 推奨構成: Tier 1（完全無料、今すぐ開始）

| 工程 | ツール | コスト |
|------|--------|--------|
| TTS | edge-tts | 無料 |
| サムネイル | Python Pillow | 無料 |
| 動画合成 | FFmpeg | 無料 |
| 字幕 | 台本→SRT直接生成 | 無料 |
| BGM/SE | YouTube Audio Library + DOVA-SYNDROME | 無料 |
| **月額合計** | | **~$1-2（台本生成APIのみ）** |

## 推奨構成: Tier 2（無料、品質アップ）

| 工程 | ツール | コスト |
|------|--------|--------|
| TTS | Google Cloud TTS (Neural2) | 無料枠内 |
| サムネイル | Figma Free + Ideogram | 無料 |
| 動画合成 | Remotion | 無料（個人利用） |
| 字幕 | faster-whisper → SRT | 無料 |
| CI/CD | GitHub Actions | 無料（月2000分） |

---

## 実装ロードマップ

- **Phase 1（今週）**: FFmpeg + edge-tts + Pillow で MVP 1本制作
- **Phase 2（来週〜）**: pipeline.py で全工程統合
- **Phase 3（1ヶ月後）**: Remotion リッチ動画テンプレート
- **Phase 4（3ヶ月後）**: GitHub Actions で完全自動化

## 最低限有料にすべきポイント

**初期段階では全部無料で戦える。** 登録者1000人超えたらサムネイル品質（Canva Pro）を検討。
