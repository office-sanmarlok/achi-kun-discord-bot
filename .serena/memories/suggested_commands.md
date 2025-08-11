# 推奨コマンド一覧

## 基本的な起動・管理コマンド
- `vai` - Claude-Discord Bridge全機能を起動（Discord bot + Flask + セッション群）
- `vai status` - 動作状態確認
- `vai doctor` - 環境診断実行
- `vai view` - 全セッションをリアルタイム表示（tmux）
- `vexit` - 全機能停止

## セッション管理
- `vai add-session <チャンネルID>` - 新しいチャンネルID追加
- `vai list-session` - チャンネルID一覧表示

## Discord通信
- `dp [session] "メッセージ"` - Discordスレッドにメッセージ送信
  - 例: `dp 1 "Hello from Claude Code"`
  - 複数行: ダブルクォート内で実際の改行を使用

## テスト実行
- `python -m unittest discover tests/` - 全テスト実行
- `python tests/test_[モジュール名].py` - 個別テスト実行

## 日本語ファイル作成（UTF-8）
- `echo "内容" | write-utf8 --stdin /path/to/file.md` - 日本語を含むファイル作成
- ヒアドキュメント使用:
  ```bash
  write-utf8 --stdin /path/to/file.md << 'EOF'
  日本語を含む
  複数行の内容
  EOF
  ```

## Git操作
- `git status` - 変更状態確認
- `git diff` - 変更内容確認
- `git add .` - 変更をステージング
- `git commit -m "メッセージ"` - コミット

## システムユーティリティ（Linux）
- `ls` - ファイル一覧
- `cd` - ディレクトリ移動
- `grep` - テキスト検索
- `find` - ファイル検索
- `ps aux | grep [プロセス名]` - プロセス確認
- `tmux ls` - tmuxセッション一覧
- `tmux attach -t [セッション名]` - tmuxセッションにアタッチ