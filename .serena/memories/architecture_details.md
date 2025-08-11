# アーキテクチャ詳細

## システム全体の動作フロー

### 1. 起動フロー
1. `vai` コマンド実行
2. tmuxセッション作成（bridge-monitor）
3. Discord Bot起動
4. Flask Webサーバー起動（ポート5000）
5. 各チャンネル用のClaude Codeセッション起動

### 2. メッセージ処理フロー
```
Discord → Discord Bot → Flask App → Claude Code Session → Flask App → Discord
```

1. **Discord からメッセージ受信**
   - `ClaudeCLIBot.on_message()` でメッセージを受信
   - チャンネルIDの検証（`ChannelValidator`）
   - 画像添付の処理（`AttachmentManager`）

2. **Claude Codeへの転送**
   - `PromptSender` を使用してFlask経由で送信
   - セッション番号とメッセージをPOST

3. **Claude Codeからの応答**
   - `dp` コマンド経由でFlask Appが受信
   - `discord_post.py` でDiscord APIを呼び出し
   - スレッドまたはチャンネルに送信

## 主要コンポーネント

### Discord Bot (`discord_bot.py`)
- **役割**: Discord イベントの処理、メッセージの受信・送信
- **主要クラス**: `ClaudeCLIBot`, `MessageProcessor`
- **機能**:
  - メッセージフィルタリング
  - スラッシュコマンド処理
  - 画像添付の保存・処理
  - セッション管理との連携

### Flask App (`flask_app.py`)
- **役割**: Discord BotとClaude Code間のブリッジ
- **主要クラス**: `FlaskBridgeApp`, `TmuxMessageForwarder`
- **エンドポイント**:
  - `/send_prompt` - Claude Codeへのメッセージ送信
  - `/discord_post` - Discordへのメッセージ投稿

### Session Manager (`session_manager.py`)
- **役割**: Claude Codeセッションのライフサイクル管理
- **主要クラス**: `SessionManager`, `SessionInfo`
- **機能**:
  - セッション作成・削除
  - プロジェクトパス管理
  - セッション状態の追跡

### Tmux Manager (`tmux_manager.py`)
- **役割**: tmuxセッションの操作
- **主要クラス**: `TmuxManager`
- **機能**:
  - tmuxセッション作成・削除
  - ウィンドウ・ペイン管理
  - コマンド送信

### Settings Manager (`config/settings.py`)
- **役割**: 設定の一元管理
- **保存場所**: `~/.claude-discord-bridge/`
- **管理項目**:
  - Discord Bot Token
  - チャンネルID
  - ポート設定
  - セッション設定

## データフロー

### 設定データ
```
~/.claude-discord-bridge/
├── settings.json     # 基本設定
├── sessions.json     # セッション情報
└── channels.json     # チャンネル設定
```

### 添付ファイル
```
~/attachments/discord/
└── [session_number]/
    └── [image_files]
```

### ログ
- 各コンポーネントで `logger` を使用
- デバッグ情報、エラー情報を記録

## セキュリティ考慮事項
- Discord Bot Tokenは環境変数または設定ファイルで管理
- .envファイルは.gitignoreに追加
- 添付ファイルは一時的に保存、処理後削除