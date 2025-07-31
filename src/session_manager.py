#!/usr/bin/env python3
"""
Session Manager - メモリベースのセッション管理

このモジュールはスレッドIDとセッション番号のマッピングを
メモリ上で管理します。サーバー再起動時にはリセットされます。
"""

from typing import Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """メモリベースのセッション管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.thread_sessions: Dict[str, int] = {}  # thread_id -> session_num
        self.next_session_num = 1
        
    def get_or_create_session(self, thread_id: str) -> int:
        """
        スレッドIDに対応するセッション番号を取得または作成
        
        Args:
            thread_id: DiscordスレッドID
            
        Returns:
            セッション番号
        """
        if thread_id in self.thread_sessions:
            return self.thread_sessions[thread_id]
            
        # 新しいセッション番号を割り当て
        session_num = self.next_session_num
        self.thread_sessions[thread_id] = session_num
        self.next_session_num += 1
        
        logger.info(f"New session created: Thread {thread_id} -> Session {session_num}")
        return session_num
        
    def get_session(self, thread_id: str) -> Optional[int]:
        """
        スレッドIDに対応するセッション番号を取得
        
        Args:
            thread_id: DiscordスレッドID
            
        Returns:
            セッション番号、存在しない場合はNone
        """
        return self.thread_sessions.get(thread_id)
        
    def find_thread_by_session(self, session_num: int) -> Optional[str]:
        """
        セッション番号からスレッドIDを逆引き
        
        Args:
            session_num: セッション番号
            
        Returns:
            スレッドID、存在しない場合はNone
        """
        for thread_id, num in self.thread_sessions.items():
            if num == session_num:
                return thread_id
        return None
        
    def list_sessions(self) -> List[Tuple[int, str]]:
        """
        全セッションをリスト形式で返す
        
        Returns:
            [(session_num, thread_id), ...]のリスト
        """
        sessions = [(num, thread_id) for thread_id, num in self.thread_sessions.items()]
        return sorted(sessions, key=lambda x: x[0])
        
    def remove_session(self, thread_id: str) -> bool:
        """
        セッションを削除
        
        Args:
            thread_id: DiscordスレッドID
            
        Returns:
            削除成功時True
        """
        if thread_id in self.thread_sessions:
            session_num = self.thread_sessions[thread_id]
            del self.thread_sessions[thread_id]
            logger.info(f"Session removed: Thread {thread_id} (Session {session_num})")
            return True
        return False
        
    def clear_all(self):
        """全セッションをクリア"""
        self.thread_sessions.clear()
        self.next_session_num = 1
        logger.info("All sessions cleared")
        
    def get_stats(self) -> Dict[str, any]:
        """統計情報を取得"""
        return {
            'total_sessions': len(self.thread_sessions),
            'next_session_num': self.next_session_num,
            'sessions': dict(self.thread_sessions)
        }

# グローバルインスタンス（シングルトン）
_session_manager = None

def get_session_manager() -> SessionManager:
    """
    SessionManagerのシングルトンインスタンスを取得
    
    Returns:
        SessionManager インスタンス
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager