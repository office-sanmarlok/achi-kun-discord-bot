# Implementation Plan

## フェーズ1: メッセージフィルタリング機能の実装

- [x] 1. メッセージフィルタリング関数の実装
  - `discord_bot.py`の`ClaudeCLIBot`クラスに`should_forward_to_claude`メソッドを追加
  - `!`で始まるメッセージをfalseで返すロジックを実装
  - Bot自身のメッセージも引き続きfalseで返す
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. on_messageハンドラの修正
  - `should_forward_to_claude`メソッドを使用してフィルタリングを追加
  - `!`で始まるメッセージの場合、`process_commands`のみ実行してCCへの転送をスキップ
  - 通常メッセージは既存の処理フローを維持
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3. フィルタリング機能のテスト実装
  - `!`で始まるメッセージがCCに転送されないことを確認するテスト
  - 通常メッセージが正常に転送されることを確認するテスト
  - 既存の`!status`、`!sessions`、`!cc`コマンドが正常に動作することを確認
  - _Requirements: 1.4, 1.5_

## フェーズ2: 設定管理の拡張

- [x] 4. SettingsManagerクラスの拡張
  - `get_post_target_channel`メソッドを実装（settings.jsonから読み取り）
  - `set_post_target_channel`メソッドを実装（settings.jsonに保存）
  - デフォルト値の処理とエラーハンドリングを実装
  - _Requirements: 3.1, 3.2_

- [x] 5. 設定ファイル構造の更新
  - `_load_settings`メソッドのデフォルト値に`post_target_channel`を追加
  - 既存の設定ファイルとの互換性を保つ処理を実装
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 6. 設定管理のテスト実装
  - 送信先チャンネルIDの読み書きテスト
  - 無効な値の検証テスト
  - 設定ファイルの永続化テスト
  - _Requirements: 3.4_

## フェーズ3: !postコマンドの実装

- [x] 7. postコマンドハンドラの基本実装
  - `create_bot_commands`関数に`post_command`を追加
  - スレッド内実行の検証ロジックを実装
  - エラーメッセージの定義と送信
  - _Requirements: 2.1, 2.2_

- [x] 8. 送信先チャンネル設定の確認機能
  - 設定から送信先チャンネルIDを取得
  - 未設定時のエラーメッセージ送信を実装
  - _Requirements: 2.3_

- [x] 9. Discord APIを使用したメッセージ送信機能
  - `discord_post.py`の`post_to_discord`関数を再利用
  - スレッド名を取得して送信メッセージをフォーマット
  - 成功時の確認メッセージをスレッド内に投稿
  - _Requirements: 2.4, 2.6_

- [x] 10. エラーハンドリングの実装
  - Discord APIエラー（権限不足、チャンネル未発見）の処理
  - 適切なエラーメッセージの返信
  - エラーログの記録
  - _Requirements: 2.5, 2.7_

- [x] 11. postコマンドの統合テスト
  - スレッド内での正常動作テスト
  - 各種エラーケースのテスト
  - エンドツーエンドの動作確認
  - _Requirements: 2.1-2.7_

## フェーズ4: 最終統合とテスト

- [x] 12. 全機能の統合テスト実装
  - `!`プレフィックスフィルタリングと既存コマンドの共存確認
  - `!post`コマンドの完全な動作確認
  - パフォーマンステストの実装
  - _Requirements: 1.1-3.4_

- [x] 13. ドキュメントとログの整備
  - 新機能に関するログ出力の追加
  - エラーメッセージの最終調整
  - コード内コメントの追加
  - _Requirements: 全般_