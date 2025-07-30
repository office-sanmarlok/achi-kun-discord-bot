# Discord.py スレッド機能調査結果

## 1. スレッド作成イベントの検出

### `on_thread_create`イベントの存在
- **存在する**: Discord.pyには`on_thread_create`イベントが実装されています
- **必要なIntents**: `Intents.guilds`を有効にする必要があります

```python
intents = discord.Intents.default()
intents.guilds = True  # これが必要

@bot.event
async def on_thread_create(thread):
    print(f'新しいスレッドが作成されました: {thread.name}')
```

### 自動検出の可否
- **可能**: 新規スレッド作成を自動的に検出できます
- **親チャンネルの権限があれば自動的に監視可能**: 親チャンネルへのアクセス権限があれば、その中で作成されるスレッドも自動的に検出されます

## 2. スレッドの親メッセージ取得

### Discord APIの仕様
- **重要な発見**: スレッドIDと親メッセージ（スターターメッセージ）のIDは**同じ**です
- この仕様により、親メッセージの取得が可能です

### 実装方法
```python
async def on_thread_create(thread):
    try:
        # スレッドIDを使って親チャンネルから親メッセージを取得
        parent_message = await thread.parent.fetch_message(thread.id)
        print(f'親メッセージ内容: {parent_message.content}')
        print(f'親メッセージ作成者: {parent_message.author}')
    except discord.NotFound:
        print('親メッセージが見つかりません')
    except discord.Forbidden:
        print('親メッセージへのアクセス権限がありません')
```

### 利用可能な情報
親メッセージから取得できる情報：
- `content`: メッセージ内容
- `author`: 作成者
- `created_at`: 作成日時
- `attachments`: 添付ファイル
- `embeds`: 埋め込みコンテンツ
- その他、通常のMessageオブジェクトの全属性

## 3. 権限の継承

### 基本的な権限継承
- **自動継承**: チャンネルに対する権限があれば、そのチャンネル内のスレッドも自動的に読み取れます
- **追加の権限設定は不要**: 親チャンネルの権限がそのまま適用されます

### 権限の詳細
1. **パブリックスレッド**:
   - 親チャンネルを見れるユーザーは全員アクセス可能
   - Botも親チャンネルの権限をそのまま継承

2. **プライベートスレッド**:
   - 明示的に追加されたユーザーのみアクセス可能
   - `Manage Threads`権限を持つユーザーはアクセス可能
   - Botも同様の制限を受ける

### 権限チェックの実装
```python
# スレッド内でのBot権限確認
perms = thread.permissions_for(thread.guild.me)
print(f'読み取り権限: {perms.read_messages}')
print(f'送信権限: {perms.send_messages}')
print(f'スレッド管理権限: {perms.manage_threads}')
```

## 推奨実装

現在のプロジェクトでスレッド対応を実装する場合：

1. **`discord_bot.py`への追加**:
   - `on_thread_create`イベントハンドラを追加
   - スレッド作成時に自動的に親メッセージを取得
   - スレッドコンテキストをFlask APIに送信

2. **メッセージ処理の拡張**:
   - スレッド内メッセージの場合、親メッセージ情報も含めて送信
   - セッション管理にスレッドコンテキストを追加

3. **権限管理**:
   - 既存のチャンネル権限チェックで十分
   - プライベートスレッドの場合は追加の確認が必要

## テストスクリプト

`test_thread_features.py`を作成しました。このスクリプトで以下の機能をテストできます：
- `on_thread_create`イベントの動作確認
- スレッドの親メッセージ取得
- スレッド権限の確認
- コマンドによるスレッド情報の取得