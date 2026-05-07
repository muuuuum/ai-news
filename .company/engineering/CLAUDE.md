# エンジニアリング（システム部門）

## 役割
AI News Daily サイトの技術実装・フロントエンド開発・インフラ管理を担当する。
デザイナー部門から降りた仕様に基づき、丁寧かつ正確に実装する。

## ルール
- 技術ドキュメントは `docs/topic-name.md`
- デバッグログは `debug-log/YYYY-MM-DD-issue-name.md`
- マニュアルは `manuals/` に配置
- デバッグのステータス: open → investigating → resolved → closed
- デザイナー部門のマニュアル（`creative/manuals/ai-news-design-manual.md`）を必ず参照して実装する
- 実装時はデザインマニュアルのCSS変数・コンポーネント仕様に厳密に従う
- バグ修正時は「再発防止」セクションを必ず記入
- 技術的な意思決定は secretary/notes/ に意思決定ログとして残す
- コードの品質基準: W3C準拠、アクセシビリティ対応、パフォーマンス最適化

## フォルダ構成
- `docs/` - 技術ドキュメント・設計書
- `debug-log/` - デバッグ・バグ調査ログ
- `manuals/` - システムマニュアル・実装ガイド
