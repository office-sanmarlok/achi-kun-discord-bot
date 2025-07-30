#!/usr/bin/env python3
"""
Thread Context Manager - Discord スレッドのコンテクスト保持機能

このモジュールは以下の責任を持つ：
1. スレッドメッセージの履歴管理
2. スレッドごとのコンテクスト保持
3. コンテクストのフォーマットと構築
4. メモリ管理と古いコンテクストの自動削除

拡張性のポイント：
- 永続化機能の追加（ファイル/DB保存）
- コンテクストサイズの動的調整
- スレッド分析機能
- コンテクスト要約機能
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque, defaultdict
import logging

logger = logging.getLogger(__name__)

class ThreadContext:
    """
    単一スレッドのコンテクスト情報を管理
    """
    
    def __init__(self, thread_id: str, parent_channel_id: str, max_messages: int = 20):
        """
        Args:
            thread_id: DiscordスレッドID
            parent_channel_id: 親チャンネルID
            max_messages: 保持する最大メッセージ数
        """
        self.thread_id = thread_id
        self.parent_channel_id = parent_channel_id
        self.messages = deque(maxlen=max_messages)
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
    def add_message(self, author: str, content: str, timestamp: datetime, message_id: Optional[str] = None):
        """
        メッセージをコンテクストに追加
        
        Args:
            author: メッセージ送信者
            content: メッセージ内容
            timestamp: メッセージのタイムスタンプ
            message_id: Discord メッセージID（オプション）
        """
        self.messages.append({
            'author': author,
            'content': content,
            'timestamp': timestamp,
            'message_id': message_id
        })
        self.last_activity = datetime.now()
        
    def get_context_string(self, include_current: bool = False) -> str:
        """
        コンテクストを文字列として取得
        
        Args:
            include_current: 現在のメッセージを含めるか
        
        Returns:
            フォーマットされたコンテクスト文字列
        """
        if not self.messages:
            return ""
            
        context_parts = ["=== スレッドコンテクスト ==="]
        
        # 最新のメッセージを除外する場合
        messages_to_include = list(self.messages)[:-1] if include_current and len(self.messages) > 1 else list(self.messages)
        
        for msg in messages_to_include:
            timestamp_str = msg['timestamp'].strftime("%H:%M:%S")
            context_parts.append(f"[{timestamp_str}] {msg['author']}: {msg['content']}")
            
        context_parts.append("=== コンテクスト終了 ===\n")
        
        return "\n".join(context_parts)
        
    def is_expired(self, expiry_hours: int = 24) -> bool:
        """
        コンテクストが期限切れかチェック
        
        Args:
            expiry_hours: 有効期限（時間）
        
        Returns:
            期限切れの場合True
        """
        expiry_time = self.last_activity + timedelta(hours=expiry_hours)
        return datetime.now() > expiry_time

class ThreadContextManager:
    """
    全スレッドのコンテクストを管理するマネージャー
    """
    
    def __init__(self, max_messages_per_thread: int = 20, expiry_hours: int = 24):
        """
        Args:
            max_messages_per_thread: スレッドごとの最大メッセージ数
            expiry_hours: コンテクストの有効期限（時間）
        """
        self.contexts: Dict[str, ThreadContext] = {}
        self.max_messages_per_thread = max_messages_per_thread
        self.expiry_hours = expiry_hours
        self._cleanup_task = None
        
    def start_cleanup_task(self):
        """非同期クリーンアップタスクを開始"""
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
    async def _periodic_cleanup(self):
        """定期的に期限切れコンテクストを削除"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1時間ごと
                self.cleanup_expired_contexts()
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                
    def cleanup_expired_contexts(self):
        """期限切れコンテクストを削除"""
        expired_threads = []
        for thread_id, context in self.contexts.items():
            if context.is_expired(self.expiry_hours):
                expired_threads.append(thread_id)
                
        for thread_id in expired_threads:
            del self.contexts[thread_id]
            logger.info(f"Expired thread context removed: {thread_id}")
            
        if expired_threads:
            logger.info(f"Cleaned up {len(expired_threads)} expired thread contexts")
            
    def add_message(self, thread_id: str, parent_channel_id: str, author: str, 
                   content: str, timestamp: datetime, message_id: Optional[str] = None):
        """
        スレッドにメッセージを追加
        
        Args:
            thread_id: スレッドID
            parent_channel_id: 親チャンネルID
            author: メッセージ送信者
            content: メッセージ内容
            timestamp: タイムスタンプ
            message_id: メッセージID
        """
        if thread_id not in self.contexts:
            self.contexts[thread_id] = ThreadContext(
                thread_id, 
                parent_channel_id,
                self.max_messages_per_thread
            )
            
        self.contexts[thread_id].add_message(author, content, timestamp, message_id)
        
    def get_thread_context(self, thread_id: str, include_current: bool = False) -> Optional[str]:
        """
        スレッドのコンテクストを取得
        
        Args:
            thread_id: スレッドID
            include_current: 現在のメッセージを含めるか
            
        Returns:
            コンテクスト文字列、存在しない場合None
        """
        if thread_id not in self.contexts:
            return None
            
        return self.contexts[thread_id].get_context_string(include_current)
        
    def get_or_create_context(self, thread_id: str, parent_channel_id: str) -> ThreadContext:
        """
        スレッドコンテクストを取得または作成
        
        Args:
            thread_id: スレッドID
            parent_channel_id: 親チャンネルID
            
        Returns:
            ThreadContext インスタンス
        """
        if thread_id not in self.contexts:
            self.contexts[thread_id] = ThreadContext(
                thread_id,
                parent_channel_id,
                self.max_messages_per_thread
            )
        return self.contexts[thread_id]
        
    def clear_thread_context(self, thread_id: str):
        """特定スレッドのコンテクストをクリア"""
        if thread_id in self.contexts:
            del self.contexts[thread_id]
            logger.info(f"Thread context cleared: {thread_id}")
            
    def get_stats(self) -> Dict[str, any]:
        """統計情報を取得"""
        total_threads = len(self.contexts)
        total_messages = sum(len(ctx.messages) for ctx in self.contexts.values())
        
        return {
            'total_threads': total_threads,
            'total_messages': total_messages,
            'contexts': {
                thread_id: {
                    'message_count': len(ctx.messages),
                    'last_activity': ctx.last_activity.isoformat(),
                    'created_at': ctx.created_at.isoformat()
                }
                for thread_id, ctx in self.contexts.items()
            }
        }

# グローバルインスタンス（シングルトン）
_thread_context_manager = None

def get_thread_context_manager() -> ThreadContextManager:
    """
    ThreadContextManagerのシングルトンインスタンスを取得
    
    Returns:
        ThreadContextManager インスタンス
    """
    global _thread_context_manager
    if _thread_context_manager is None:
        _thread_context_manager = ThreadContextManager()
    return _thread_context_manager