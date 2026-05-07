---
created: "2026-04-03"
type: system-manual
version: "2.0"
status: approved
depends_on: "creative/manuals/ai-news-design-manual.md"
---

# AI News Daily システムマニュアル

> **前提**: 本マニュアルはデザイナー部門の「ai-news-design-manual.md」に基づき、
> 技術的な実装仕様をまとめたものです。デザイン変更が入った場合、本マニュアルも連動して更新します。

---

## 1. プロジェクト概要

### 1.1 サイト情報

| 項目 | 値 |
|------|-----|
| サイト名 | AI News Daily |
| 目的 | 世界のAI最新ニュースを日本語で毎日配信 |
| 参考メディア | Reuters, AP通信, AFP通信, ledge.ai |
| 現在のアーキテクチャ | 静的HTML単一ファイル（index.html） |
| ホスティング | 未定（GitHub Pages / Vercel / Cloudflare Pages 候補） |
| ドメイン | 未取得 |

### 1.2 技術スタック（現在）

| レイヤー | 技術 | 備考 |
|---------|------|------|
| マークアップ | HTML5 | セマンティックタグ使用 |
| スタイル | CSS3（インライン `<style>`） | CSS変数・Grid・Flexbox |
| フォント | Google Fonts（Noto Sans JP + Inter） | preconnect 設定済み |
| JavaScript | なし | 現時点では静的コンテンツのみ |
| バージョン管理 | Git | mainブランチで運用 |

### 1.3 ファイル構成

```
ai-news/
├── index.html          ← メインファイル（HTML + CSS 全て内包）
├── .company/           ← 組織管理（Git管理外推奨）
└── .git/
```

---

## 2. HTML構造仕様

### 2.1 ドキュメント設定

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI News Daily — 世界のAIニュース</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>/* CSS全体をここに記述 */</style>
</head>
```

**チェックポイント**:
- `lang="ja"` でアクセシビリティ・SEO対応
- `viewport` メタタグでレスポンシブ対応
- Google Fonts は `preconnect` で先読みしパフォーマンス向上

### 2.2 ページセクション構造

```html
<body>
  <!-- 1. 速報ティッカーバー -->
  <div class="ticker-wrap">...</div>

  <!-- 2. ヘッダー -->
  <header>
    <div class="header-inner">...</div>
  </header>

  <!-- 3. ナビゲーション -->
  <nav>
    <div class="nav-inner">...</div>
  </nav>

  <!-- 4. メインコンテンツエリア -->
  <div class="page">
    <div class="layout">

      <!-- 4a. メインカラム -->
      <main>
        <!-- セクション群 -->
      </main>

      <!-- 4b. サイドバー -->
      <aside class="sidebar">
        <!-- サイドバーセクション群 -->
      </aside>

    </div>
  </div>

  <!-- 5. フッター -->
  <footer>...</footer>
</body>
```

### 2.3 セマンティックHTML使用ルール

| HTML要素 | 用途 | 備考 |
|---------|------|------|
| `<header>` | サイトヘッダー | 1ページ1回 |
| `<nav>` | ナビゲーション | 1ページ1回 |
| `<main>` | メインコンテンツ | 1ページ1回 |
| `<aside>` | サイドバー | 補足情報 |
| `<footer>` | フッター | 1ページ1回 |
| `<div>` | 汎用コンテナ | セマンティック要素が適さない場合 |
| `<table>` | データテーブル | `<thead>` `<tbody>` 必須 |
| `<p>` | 段落テキスト | 本文はp要素で囲む |
| `<b>` | 強調テキスト | デザイン上の太字に使用 |

---

## 3. CSS実装仕様

### 3.1 CSS変数（デザインマニュアル §2.1 準拠）

CSS変数は `:root` に定義し、全コンポーネントで共有する。
ハードコードされた色値は禁止。必ず `var(--xxx)` を使用すること。

**例外**: グラデーション内の色値、`rgba()` 値、インラインスタイルの図解要素

### 3.2 リセットCSS

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
```

最小限のリセットを採用。normalize.css は不使用（単一ページのため軽量化優先）。

### 3.3 コンポーネント別CSSクラス命名規則

| 接頭辞 | 用途 | 例 |
|--------|------|-----|
| `.ticker-` | 速報ティッカー | `.ticker-wrap`, `.ticker-inner`, `.ticker-label`, `.ticker-text` |
| `.header-` | ヘッダー | `.header-inner`, `.header-date`, `.header-tagline` |
| `.logo-` | ロゴ | `.logo`, `.logo-mark`, `.logo-name` |
| `.nav-` | ナビゲーション | `.nav-inner`, `.nav-item` |
| `.sec-head-` | セクションヘッダー | `.sec-head`, `.sec-head-bar`, `.sec-head-title` |
| `.hero-` | ヒーロー記事 | `.hero-article`, `.hero-thumb`, `.hero-body` |
| `.key-num-` | キーナンバーズ | `.key-numbers`, `.key-num-item`, `.key-num-val` |
| `.data-table-` | データテーブル | `.data-table-wrap`, `.data-table`, `.data-table-title` |
| `.bar-` | バーチャート（テーブル内） | `.bar-cell`, `.bar-bg`, `.bar-fill`, `.bar-val` |
| `.chart-` | 棒グラフ | `.chart-wrap`, `.chart-bars`, `.chart-bar`, `.chart-bar-val` |
| `.card-` | ニュースカード | `.card`, `.card-grid`, `.card-thumb`, `.card-body`, `.card-tag` |
| `.tag-` | カテゴリタグ | `.tag-model`, `.tag-biz`, `.tag-agent`, `.tag-sec`, `.tag-research` |
| `.inline-img-` | インライン図解 | `.inline-img`, `.inline-img-inner`, `.inline-img-caption` |
| `.sidebar-` | サイドバー | `.sidebar`, `.sidebar-section`, `.sidebar-title` |
| `.rank-` | ランキング | `.rank-item`, `.rank-num`, `.rank-text` |
| `.stat-` | 統計リスト | `.stat-list`, `.stat-row`, `.stat-name`, `.stat-val` |
| `.source-` | ソース | `.sources-box`, `.source-chip` |
| `.footer-` | フッター | `.footer-logo`, `.footer-text` |

### 3.4 レスポンシブ実装

**メディアクエリの記述順序**: モバイルファーストではなく、デスクトップファーストで記述（現在の実装に合わせる）。

```css
/* デスクトップ（デフォルト） */
.layout { display: grid; grid-template-columns: 1fr 300px; gap: 28px; }

/* タブレット */
@media (max-width: 860px) {
  .layout { grid-template-columns: 1fr; }
  .card-grid { grid-template-columns: 1fr; }
  .chart-bars { height: 80px; }
}

/* モバイル */
@media (max-width: 540px) {
  .page { padding: 16px 14px 40px; }
  .hero-thumb { height: 200px; }
  .hero-thumb-title { font-size: 20px; }
  .key-numbers { grid-template-columns: 1fr 1fr; }
}
```

### 3.5 アニメーション仕様

| アニメーション名 | 用途 | 仕様 |
|-----------------|------|------|
| `ticker` | 速報スクロール | `translateX(0)` → `translateX(-50%)`, 35s linear infinite |

**transition 一覧**:

| 要素 | プロパティ | 時間 |
|------|-----------|------|
| `.card` | `box-shadow, transform` | 0.2s |
| `.nav-item` | `all` | 0.15s |
| `.bar-fill` | `width` | 0.3s |

---

## 4. コンテンツ更新手順

### 4.1 日次ニュース更新フロー

```
1. 情報収集
   ├─ Reuters, AP, AFP 等の通信社
   ├─ TechCrunch, VentureBeat, The Verge
   ├─ 各社公式ブログ (Anthropic, OpenAI, Google DeepMind)
   └─ 日本語メディア (ITmedia, Impress, ledge.ai)

2. コンテンツ作成
   ├─ トップニュース1件（ヒーロー記事）
   ├─ カテゴリ別ニュース2〜4件（カード）
   ├─ データ可視化（テーブル/チャート）
   └─ サイドバー更新（数字・ランキング・イベント）

3. HTML更新
   ├─ ヘッダーの日付を更新
   ├─ 速報ティッカーの内容を更新
   ├─ 各セクションのコンテンツを差し替え
   └─ フッターの最終更新日時を更新
```

### 4.2 コンテンツ追加テンプレート

#### ニュースカード追加

```html
<div class="card">
  <div class="card-thumb" style="background:linear-gradient(135deg, [色1], [色2]);">
    <div class="card-thumb-icon">[絵文字]</div>
    <div class="card-thumb-label">[企業名]</div>
  </div>
  <div class="card-body">
    <div class="card-tag [tag-xxx]">[カテゴリ名]</div>
    <div class="card-title">[見出し]</div>
    <div class="card-desc">[説明文。<b>強調部分</b>を含む。]</div>
  </div>
  <div class="card-footer">
    <span class="card-source">[出典]</span>
    <span>[YYYY.MM.DD]</span>
  </div>
</div>
```

#### サイドバー統計追加

```html
<div class="stat-row">
  <span class="stat-name">[指標名]</span>
  <span class="stat-val">[値]</span>
</div>
```

#### サイドバーランキング追加

```html
<div class="rank-item">
  <div class="rank-num [r1|r2|r3|other]">[順位]</div>
  <div>
    <div class="rank-text">[タイトル]</div>
    <div class="rank-source">[出典 / カテゴリ]</div>
  </div>
</div>
```

#### セクション追加

```html
<div class="sec-head" style="margin-top:32px;">
  <div class="sec-head-bar"></div>
  <div class="sec-head-title">[絵文字] [セクション名]</div>
</div>
```

### 4.3 サムネイル背景パターン一覧

| 企業/カテゴリ | グラデーション |
|-------------|--------------|
| Anthropic | `linear-gradient(135deg, #1e1b4b, #312e81)` |
| OpenAI | `linear-gradient(135deg, #0c4a6e, #075985)` |
| Google | `linear-gradient(135deg, #14532d, #166534)` |
| Salesforce / ビジネス | `linear-gradient(135deg, #1e3a5f, #1d4ed8)` |
| セキュリティ | `linear-gradient(135deg, #7f1d1d, #991b1b)` |
| Meta | `linear-gradient(135deg, #1e3a5f, #2563eb)` |
| Mistral | `linear-gradient(135deg, #374151, #1f2937)` |
| スタートアップ | `linear-gradient(135deg, #713f12, #92400e)` |

---

## 5. パフォーマンス最適化

### 5.1 現在の最適化状況

| 項目 | 状態 | 備考 |
|------|------|------|
| 外部JS | なし | 静的HTMLのみ |
| 外部CSS | Google Fonts のみ | インラインCSS |
| 画像 | なし | CSSグラデーション + Emoji |
| フォント | preconnect 済み | Noto Sans JP + Inter |
| アニメーション | CSS のみ | JS不使用 |

### 5.2 パフォーマンスベストプラクティス

1. **Google Fonts**: `preconnect` + `display=swap` で FOUT を最小化
2. **インラインCSS**: HTTP リクエスト削減（単一ページのため有効）
3. **画像不使用**: CSSグラデーション + Emoji でゼロ画像読み込み
4. **最小限のアニメーション**: `transform` と `opacity` のみで GPU アクセラレーション活用
5. **CSS変数**: 一貫性維持 + メンテナンス性向上

### 5.3 将来のパフォーマンス改善候補

| 施策 | 優先度 | 効果 |
|------|--------|------|
| Google Fonts のサブセット化 | 中 | 日本語フォントの読み込み時間短縮 |
| Critical CSS インライン化 | 低 | 既にインラインのため不要 |
| Service Worker 導入 | 低 | オフライン対応・キャッシュ戦略 |
| HTML ミニファイ | 低 | ファイルサイズ削減 |

---

## 6. SEO・アクセシビリティ

### 6.1 現在のSEO対応

| 項目 | 状態 | 備考 |
|------|------|------|
| `<title>` | 設定済み | "AI News Daily — 世界のAIニュース" |
| `<meta charset>` | 設定済み | UTF-8 |
| `<meta viewport>` | 設定済み | レスポンシブ対応 |
| `lang` 属性 | 設定済み | `ja` |
| セマンティックHTML | 部分対応 | header, nav, main, aside, footer 使用 |

### 6.2 追加すべきSEOタグ（将来）

```html
<meta name="description" content="世界のAI最新ニュースを毎朝日本語でお届け。Reuters, AP通信レベルの信頼性で、AIモデル・エージェント・ビジネスの最新動向を解説。">
<meta name="keywords" content="AI, 人工知能, ニュース, ChatGPT, Claude, Gemini, OpenAI, Anthropic">
<meta property="og:title" content="AI News Daily — 世界のAIニュース">
<meta property="og:description" content="世界のAI最新ニュースを毎朝日本語でお届け">
<meta property="og:type" content="website">
<meta property="og:image" content="[OGP画像URL]">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
```

### 6.3 アクセシビリティ改善候補

| 項目 | 優先度 | 対応 |
|------|--------|------|
| `aria-label` 追加 | 高 | ナビ・セクションに追加 |
| キーボードナビゲーション | 中 | `tabindex`, `:focus` スタイル |
| カラーコントラスト | 確認済み | WCAG AA準拠 |
| スクリーンリーダー | 中 | 適切な見出し階層 |

---

## 7. 開発ワークフロー

### 7.1 ブランチ戦略

```
main ─── 本番（現在のデフォルトブランチ）
  └── feature/xxx ─── 機能開発
  └── fix/xxx ─── バグ修正
```

### 7.2 コミットメッセージ規約

```
[種別]: 簡潔な説明（日本語OK）

種別:
- Add: 新機能追加
- Update: 既存機能の改善
- Fix: バグ修正
- Redesign: デザイン変更
- Refactor: リファクタリング
- Docs: ドキュメント更新
```

### 7.3 デプロイフロー（将来）

```
1. feature ブランチで開発
2. ローカルでブラウザ確認（file:// で開くだけ）
3. main にマージ
4. 自動デプロイ（GitHub Pages / Vercel）
```

---

## 8. 将来のシステムアーキテクチャ計画

### Phase 1: 静的サイト（現在）
- 単一 HTML ファイル
- 手動コンテンツ更新
- Git でバージョン管理

### Phase 2: 静的サイト生成（SSG）
- ニュースデータを JSON/YAML に分離
- テンプレートエンジンで HTML 生成
- ビルドスクリプトで自動生成
- 候補: 11ty, Astro, Next.js (static export)

### Phase 3: 自動化
- AIエージェントによるニュース収集
- 自動コンテンツ生成パイプライン
- スケジュール実行（毎朝 9:00）
- GitHub Actions でCI/CD

### Phase 4: フル動的サイト
- バックエンド API（ニュース管理）
- データベース（記事・カテゴリ・ソース管理）
- 管理画面（CMS）
- ユーザー機能（メルマガ購読、ブックマーク）

---

## 9. トラブルシューティング

### 9.1 よくある問題

| 問題 | 原因 | 対処 |
|------|------|------|
| フォントが表示されない | Google Fonts CDN 障害 | フォールバック `-apple-system, sans-serif` が適用される |
| ティッカーが止まる | CSS animation の競合 | `animation` プロパティの重複確認 |
| 2カラムが崩れる | コンテンツ幅超過 | `overflow-x: auto` で水平スクロール対応 |
| テーブルがはみ出す | モバイルでの幅不足 | `.data-table-wrap` の `overflow-x: auto` で対応済み |
| グラデーションが表示されない | ブラウザ互換性 | 主要ブラウザ（Chrome/Safari/Firefox/Edge）で対応済み |

### 9.2 ブラウザ対応

| ブラウザ | サポート | 備考 |
|---------|---------|------|
| Chrome 90+ | 完全対応 | 推奨ブラウザ |
| Safari 15+ | 完全対応 | `-webkit-font-smoothing` 対応 |
| Firefox 90+ | 完全対応 | |
| Edge 90+ | 完全対応 | Chromium ベース |
| IE 11 | 非対応 | CSS変数・Grid非対応のため |

---

## 10. コード品質チェックリスト

新しいコードを追加する際に確認:

### HTML
- [ ] セマンティックHTMLを使用しているか
- [ ] インデント（スペース2個）は統一されているか
- [ ] 不要な `<div>` ネストがないか
- [ ] `lang` 属性が正しいか

### CSS
- [ ] CSS変数（`var(--xxx)`）を使用しているか
- [ ] クラス命名は既存の接頭辞規則に従っているか
- [ ] レスポンシブ対応（860px / 540px）を考慮しているか
- [ ] `transition` が必要な要素に設定されているか
- [ ] `overflow: hidden` が必要な要素に設定されているか

### パフォーマンス
- [ ] 不必要な外部リソースを追加していないか
- [ ] アニメーションは `transform` / `opacity` ベースか
- [ ] 画像を追加する場合、適切なサイズ・フォーマットか

### アクセシビリティ
- [ ] カラーコントラスト比は十分か（WCAG AA: 4.5:1 以上）
- [ ] フォントサイズは 10px 以上か
- [ ] クリック/タップ領域は十分か（44px × 44px 推奨）
