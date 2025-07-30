# スレッド単位セッション実装戦略

## 概要

Discord のスレッドごとに独立した Claude Code セッションを作成する。通常のチャンネルメッセージは処理しない。

## 基本方針

- **スレッドメッセージのみ処理**
- **チャンネル単位のセッションは作成しない**
- **Claude Code の自動コンテクスト保持機能を活用**

## 実装内容

### 1. settings.py の変更

```python
# チャンネル管理をスレッド管理に置き換え
self.thread_sessions = {}  # thread_id -> session_number
# self.channel_sessions = {} を削除または非推奨化

def thread_to_session(self, thread_id: str) -> Optional[int]:
    """スレッドIDからセッション番号を取得"""
    return self.thread_sessions.get(thread_id)

def add_thread_session(self, thread_id: str) -> int:
    """新規スレッド用セッションを割り当て"""
    # 次の利用可能なセッション番号を取得
    existing_sessions = set(self.thread_sessions.values())
    session_num = 1
    while session_num in existing_sessions:
        session_num += 1
    
    self.thread_sessions[thread_id] = session_num
    self._save_settings()
    return session_num

def list_sessions(self) -> List[Tuple[int, str]]:
    """スレッドセッション一覧を返す"""
    return [(num, thread_id) for thread_id, num in self.thread_sessions.items()]
```

### 2. discord_bot.py の修正

```python
async def on_message(self, message):
    # Bot自身のメッセージは無視
    if message.author == self.user:
        return
    
    # スレッド以外は処理しない
    if message.channel.type != discord.ChannelType.public_thread:
        return
    
    # スレッドの処理
    thread_id = str(message.channel.id)
    session_num = self.settings.thread_to_session(thread_id)
    
    if session_num is None:
        # 新規スレッドの場合
        session_num = self.settings.add_thread_session(thread_id)
        # tmuxで新しいClaude Codeセッションを起動
        await self._start_claude_session(session_num, message.channel.name)
        print(f"🧵 New thread: {message.channel.name} -> Session {session_num}")
    
    # ローディングメッセージ送信
    loading_msg = await self._send_loading_feedback(message.channel)
    
    # 以降は既存の処理と同じ（メッセージ転送等）
```

### 3. セッション起動処理

```python
# discord_bot.py内に追加
async def _start_claude_session(self, session_num: int, thread_name: str):
    """新しいClaude Codeセッションを起動"""
    session_name = f"claude-session-{session_num}"
    cmd = [
        'tmux', 'new-session', '-d', '-s', session_name,
        'claude', 'code'
    ]
    
    try:
        subprocess.run(cmd, check=True)
        logger.info(f"Started Claude Code session {session_num} for thread: {thread_name}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start session: {e}")
```

## 実装ステップ

1. [ ] settings.py でチャンネル管理をスレッド管理に置き換え
2. [ ] discord_bot.py でスレッドのみを処理するよう変更
3. [ ] 新規スレッド時のClaude Codeセッション自動起動
4. [ ] 既存のコマンドをスレッド対応に修正
5. [ ] テスト実施

## 変更点のまとめ

### 削除される機能
- チャンネル単位のセッション管理
- チャンネルへの直接メッセージ

### 新しい動作
- スレッドメッセージのみ処理
- スレッドごとに独立したClaude Codeセッション
- 初回メッセージ時に自動セッション作成

## 注意点

- スレッドが多くなるとセッション数も増える
- 不要になったスレッドセッションの削除機能が将来必要