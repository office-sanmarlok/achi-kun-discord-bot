# !postコマンド機能

## 概要

この機能は、Discord Bot に以下の2つの機能を追加します：

1. **!プレフィックスフィルタリング**: `!`で始まるメッセージはClaude Codeに転送されません
2. **!postコマンド**: スレッド内で実行すると、そのスレッド名を設定されたチャンネルに送信します

## 使用方法

### !postコマンド

スレッド内で以下のコマンドを実行します：

```
!post
```

成功すると、設定されたチャンネルに「スレッド名: [スレッド名]」というメッセージが送信されます。

### エラーメッセージ

- `❌ このコマンドはスレッド内でのみ使用可能です` - チャンネルで実行した場合
- `❌ 送信先チャンネルが設定されていません` - 送信先が未設定の場合
- `❌ 送信先チャンネルが見つかりません` - チャンネルが削除されている場合
- `❌ 送信先チャンネルへのアクセス権限がありません` - Botに権限がない場合

## 設定方法

### 送信先チャンネルの設定

Pythonスクリプトまたは対話型シェルで以下を実行：

```python
from config.settings import SettingsManager

settings = SettingsManager()
settings.set_post_target_channel("チャンネルID")
```

### 設定の確認

```python
channel_id = settings.get_post_target_channel()
print(f"送信先チャンネルID: {channel_id}")
```

## 実装詳細

### メッセージフィルタリング

`discord_bot.py`の`should_forward_to_claude`メソッドで、以下の条件でメッセージをフィルタリング：

1. Bot自身のメッセージは転送しない
2. `!`で始まるメッセージは転送しない
3. それ以外は転送する

### 設定管理

`settings.json`ファイルに`post_target_channel`フィールドを追加：

```json
{
    "thread_sessions": {},
    "registered_channels": [],
    "ports": {"flask": 5001},
    "post_target_channel": "チャンネルID"
}
```

既存の設定ファイルとの互換性も保たれています。

## セキュリティ考慮事項

- Botは送信先チャンネルへの書き込み権限のみ必要
- チャンネルIDは設定ファイルに保存され、適切な権限で保護
- エラーメッセージに機密情報は含まれない