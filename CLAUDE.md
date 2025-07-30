# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## コマンドリファレンス

### 基本コマンド
- `vai` - 全サービス起動（Discord bot + Flask server + Claude Codeセッション群）
- `vai status` - 動作状態確認
- `vai doctor` - 環境診断（tmux、Python、依存関係チェック）  
- `vai view` - 全セッションをリアルタイム表示（tmux画面分割）
- `vexit` - 全サービス停止
- `vai add-session <チャンネルID>` - 新規チャンネル追加
- `vai list-session` - 登録チャンネル一覧
- `dp [session] "メッセージ"` - Discordにメッセージ送信

### 開発コマンド
- `pip install -r requirements.txt` - 依存関係インストール
- `python -m src.discord_bot` - Discord bot単体起動（デバッグ用）
- `python -m src.flask_app` - Flask server単体起動（デバッグ用）

## アーキテクチャ概要

### コンポーネント間の連携
```
Discord → discord_bot.py → flask_app.py → tmux_manager.py → Claude Codeセッション
                                                ↓
                                        attachment_manager.py（画像処理）
```

### 主要コンポーネント

1. **discord_bot.py** - Discord APIとの通信、メッセージ受信、画像ダウンロード
2. **flask_app.py** - HTTP APIサーバー、メッセージルーティング、セッション管理
3. **tmux_manager.py** - tmuxセッション制御、Claude Code起動、メッセージ送信
4. **attachment_manager.py** - 画像ファイル管理、一時ファイル処理
5. **settings.py** - 設定管理、チャンネルID管理、環境変数処理

### セッション管理の仕組み
- 各DiscordチャンネルIDに対して1つのClaude Codeセッション（tmux）を割り当て
- セッションIDは1から始まる連番で管理
- Flask APIがチャンネルIDとセッションIDのマッピングを保持

### メッセージフロー
1. Discord Bot: メッセージ受信 → Flask APIへPOST
2. Flask API: チャンネルID → セッションID変換
3. tmux_manager: 該当セッションへメッセージ送信（tmux send-keys）
4. 画像がある場合: 一時ディレクトリに保存してパス情報を付加

## Discord経由の通知に対応するルール

以下のような文言が含まれるメッセージを受け取った場合、「Discordからの通知」と判断してください：
1. 「Discordからの通知:」で始まるメッセージ
2. メッセージ末尾に `session=数字` が含まれる場合
3. スラッシュコマンド（例：`/project-analyze session=1`）

「Discordからの通知」がきた場合は以下のルールに従ってください：
### 基本的な応答ルール
1. **CLI応答は禁止。すべて`Bash`ツールを使って`dp`コマンドでメッセージを送信してください。**
2. `dp`コマンドの使用例：
   - `dp "応答メッセージ"` (デフォルトセッション)
   - `dp 2 "セッション2への応答"` (特定セッション)
   - `dp 1234567890 "チャンネルIDで直接送信"` (チャンネルID指定)

### Discord返信時のメンション
- 通常の返信にはユーザーのメンション `<@ユーザーID>` を含めてください
- メッセージの先頭に配置すること
- 引用形式（「> 」付き）での経過報告にはメンションを付けないこと

### 画像添付への対応
メッセージに `[添付画像のファイルパス: /path/to/image.png]` が含まれている場合：
1. `Read`ツールでその画像ファイルを読み込み
2. 画像の内容を分析して適切に応答
3. UI/UXレビュー、コードレビュー、ドキュメント処理などに活用

### 出力の例

**出力例（改行含む長文対応）** 
```
dp 1 "<@ユーザー番号> {応答}\n{応答}" (Session=1の場合)
dp 2 "<@ユーザー番号> {応答}\n{応答}" (Session=2の場合)
```