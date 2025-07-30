# Claude-Discord Bridge 開発ログ

## 2025-07-30

### 修正された問題

#### 1. Flask AppのModuleNotFoundError
- **問題**: Flask Appが`config`モジュールを見つけられずに起動に失敗
- **原因**: `vai`コマンドが`src`ディレクトリから直接Pythonスクリプトを実行していたため、PYTHONPATHが正しく設定されていなかった
- **解決策**: `bin/vai`の70行目と84行目を修正し、プロジェクトルートから実行するように変更
  ```python
  # 修正前
  tmux.send_command("0.0", f"cd {src_dir} && python3 discord_bot.py")
  tmux.send_command("0.1", f"cd {src_dir} && python3 flask_app.py")
  
  # 修正後
  tmux.send_command("0.0", f"cd {toolkit_root} && python3 src/discord_bot.py")
  tmux.send_command("0.1", f"cd {toolkit_root} && python3 src/flask_app.py")
  ```

#### 2. Discord Botの特権インテントエラー
- **問題**: Discord Botが`PrivilegedIntentsRequired`エラーで起動に失敗
- **原因**: `message_content`インテントは特権インテントであり、Discord開発者ポータルで明示的に有効化する必要がある
- **解決策**: Discord開発者ポータル（https://discord.com/developers/applications/）でアプリケーションの"Bot"セクションから"MESSAGE CONTENT INTENT"を有効化

### 今後の開発メモ
- botの機能に対し変更を行った場合は、このdevlog.mdを更新していく