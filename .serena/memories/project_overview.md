# Claude-Discord Bridge プロジェクト概要

## プロジェクトの目的
Claude CodeとDiscordをシームレスに連携する、複数セッション対応のポータブルブリッジツール。Discord botを1つ作成するだけで、チャンネルを追加するたびにClaude Codeセッションが自動増設される。

## 主な機能
- マルチセッション管理（チャンネルごとにClaude Codeセッション）
- 画像添付サポート（複数枚対応）
- スラッシュコマンドサポート
- tmuxを使用したセッション管理
- 完全自動セットアップ

## 技術スタック
- **言語**: Python 3.8+
- **主要ライブラリ**: 
  - discord.py >= 2.0.0 (Discord Bot)
  - Flask >= 2.0.0 (Webサーバー/ルーティング)
  - psutil >= 5.8.0 (プロセス管理)
  - python-dotenv >= 0.19.0 (環境変数管理)
- **外部ツール**: tmux (セッション管理)

## プロジェクト構造
```
achi-kun-discord-bot/
├── src/
│   ├── discord_bot.py        # Discord Botメインクラス
│   ├── flask_app.py           # Flask アプリケーション
│   ├── session_manager.py     # セッション管理
│   ├── tmux_manager.py        # tmux制御
│   ├── command_manager.py     # コマンド処理
│   ├── attachment_manager.py  # 画像添付処理
│   ├── channel_validator.py   # チャンネル検証
│   ├── prompt_sender.py       # プロンプト送信
│   ├── project_manager.py     # プロジェクト管理
│   ├── claude_context_manager.py # Claude コンテキスト管理
│   ├── discord_post.py        # Discord メッセージ送信
│   └── environment.py         # 環境検出
├── config/
│   ├── settings.py            # 設定管理
├── tests/                     # テストファイル群
├── bin/                       # 実行可能スクリプト
│   ├── vai                    # メイン起動コマンド
│   ├── dp                     # Discord投稿コマンド
│   ├── vexit                  # 停止コマンド
│   └── write-utf8             # UTF-8ファイル作成ツール
└── lib/                       # ユーティリティライブラリ
```