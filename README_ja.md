# Claude-Discord Bridge

Claude CodeとDiscordをシームレスに連携する、複数セッション、スラッシュコマンド対応、複数枚の画像送信対応のポータブルブリッジツールです。

## 主な特徴
- **スケーラブルなマルチセッション**: Discord botを1つ作成するだけで、チャンネルを追加するたびにClaude Codeセッションが自動増設されます。
- **画像添付サポート**: 画像分析ワークフローの完全サポート
- **スラッシュコマンドサポート**: コマンドもDiscord経由で実行可能
- **完全自動セットアップ**: 1コマンドでの環境検出とワンクリック導入
- **ポータブル設計**: 絶対パスやシステム固有設定に依存しない

## 操作イメージ
1. Discord Botを作成。権限を与えてBotトークンを発行
2. install.shを起動して、インストール開始。
3. インストール時に、BotトークンとChannel IDを3つまで設定できます。
   （vai add-session {channel id}であとでさらに追加可能です）
4. Claude.mdにDiscordへの返信ルールを記載。
5. 「vai」で起動。
6. 「vai view」でtmuxで複数のセッションをリアルタイムに直接操作・監視
7. Discordからチャット → Claude Codeから応答がきます。

## システム要件
- macOS または Linux
- Python 3.8以上
- tmux
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications)で作成)

## インストール / アンインストール
```bash
git clone https://github.com/yamkz/claude-discord-bridge.git
cd claude-discord-bridge
./install.sh
```

```bash
cd claude-discord-bridge
./uninstall.sh
```

## クイックスタート
**1. CLAUDE.mdに追記**
作業場所のCLAUDE.mdファイルに以下の設定を追加してください:
[CLAUDE.md設定例](./CLAUDE.md)

**1. ブリッジ開始、セッション状況の確認**
```bash
vai
vai view
```

**2. Discordでテスト**

**3. 停止**
```bash
vexit
```

## コマンド一覧
### 基本コマンド
- `vai` - 全機能開始（Discord bot + ルーティング + Claude Codeセッション群）
- `vai status` - 動作状態確認
- `vai doctor` - 環境診断実行
- `vai view` - 全セッションをリアルタイム表示
  (現在最大6画面表示までしか実装してません)
- `vexit` - 全機能停止
- `vai add-session <チャンネルID>`- チャンネルID追加
- `vai list-session`- チャンネルID一覧
- `dp [session] "メッセージ"` - Discordにメッセージ送信

## ライセンス
MIT License - 詳細はLICENSEファイルを参照
