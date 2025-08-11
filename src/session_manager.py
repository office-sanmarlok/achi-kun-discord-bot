#!/usr/bin/env python3
"""
Session Manager - メモリベースのセッション管理

このモジュールはスレッドIDとセッション番号のマッピングを
メモリ上で管理します。サーバー再起動時にはリセットされます。
"""

from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """セッション情報を保持するデータクラス"""
    session_num: int
    thread_id: str
    idea_name: str
    created_at: datetime
    current_stage: str  # "idea", "requirements", "design", "tasks", "development"
    tmux_session_name: str
    working_directory: str


@dataclass
class ProjectInfo:
    """プロジェクト情報を保持するデータクラス"""
    idea_name: str
    created_at: datetime
    current_stage: str
    project_path: Path
    development_path: Optional[Path] = None
    github_url: Optional[str] = None
    documents: Dict[str, Path] = field(default_factory=dict)  # {"idea": Path, "requirements": Path, ...}


@dataclass
class WorkflowState:
    """ワークフロー状態を保持するデータクラス"""
    idea_name: str
    current_channel: str
    next_channel: Optional[str]
    completed_stages: List[str] = field(default_factory=list)
    git_commits: Dict[str, str] = field(default_factory=dict)  # {stage: commit_hash}
    thread_ids: Dict[str, str] = field(default_factory=dict)   # {channel: thread_id}

class SessionManager:
    """メモリベースのセッション管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.thread_sessions: Dict[str, int] = {}  # thread_id -> session_num
        self.next_session_num = 1
        
        # 拡張: プロジェクト追跡用の新しい属性
        self.session_info: Dict[int, SessionInfo] = {}  # session_num -> SessionInfo
        self.project_info: Dict[str, ProjectInfo] = {}  # idea_name -> ProjectInfo
        self.workflow_states: Dict[str, WorkflowState] = {}  # idea_name -> WorkflowState
        self.thread_to_idea: Dict[str, str] = {}  # thread_id -> idea_name
        
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
        # 新しいsession_infoから検索
        if session_num in self.session_info:
            return self.session_info[session_num].thread_id
            
        # 旧形式のthread_sessionsからも検索（後方互換性）
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
        # 新しいsession_infoから取得
        sessions = []
        for session_num, info in self.session_info.items():
            sessions.append((session_num, info.thread_id))
            
        # 旧形式のthread_sessionsからも取得（重複を避ける）
        existing_sessions = {s[0] for s in sessions}
        for thread_id, num in self.thread_sessions.items():
            if num not in existing_sessions:
                sessions.append((num, thread_id))
                
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
    
    def clear_all_sessions(self):
        """全セッションをクリア（clear_allのエイリアス）"""
        self.clear_all()
    
    def get_thread_by_session(self, session_num: int) -> Optional[str]:
        """
        セッション番号からスレッドIDを取得（find_thread_by_sessionのエイリアス）
        
        Args:
            session_num: セッション番号
            
        Returns:
            スレッドID、存在しない場合はNone
        """
        return self.find_thread_by_session(session_num)
        
    def get_stats(self) -> Dict[str, any]:
        """統計情報を取得"""
        return {
            'total_sessions': len(self.thread_sessions),
            'next_session_num': self.next_session_num,
            'sessions': dict(self.thread_sessions),
            'total_projects': len(self.project_info),
            'active_workflows': len(self.workflow_states)
        }
    
    # 拡張: プロジェクト追跡メソッド
    def create_session_info(self, session_num: int, thread_id: str, idea_name: str, 
                          current_stage: str, working_directory: str) -> SessionInfo:
        """
        セッション情報を作成して保存
        
        Args:
            session_num: セッション番号
            thread_id: DiscordスレッドID
            idea_name: アイデア名
            current_stage: 現在のステージ
            working_directory: 作業ディレクトリ
            
        Returns:
            作成されたSessionInfo
        """
        session_info = SessionInfo(
            session_num=session_num,
            thread_id=thread_id,
            idea_name=idea_name,
            created_at=datetime.now(),
            current_stage=current_stage,
            tmux_session_name=f"claude-session-{session_num}",
            working_directory=working_directory
        )
        
        self.session_info[session_num] = session_info
        self.thread_to_idea[thread_id] = idea_name
        logger.info(f"Created session info: {session_info}")
        
        return session_info
    
    def create_project_info(self, idea_name: str, project_path: Path) -> ProjectInfo:
        """
        プロジェクト情報を作成して保存
        
        Args:
            idea_name: アイデア名
            project_path: プロジェクトパス
            
        Returns:
            作成されたProjectInfo
        """
        project_info = ProjectInfo(
            idea_name=idea_name,
            created_at=datetime.now(),
            current_stage="idea",
            project_path=project_path
        )
        
        self.project_info[idea_name] = project_info
        logger.info(f"Created project info: {project_info}")
        
        return project_info
    
    def create_workflow_state(self, idea_name: str, current_channel: str) -> WorkflowState:
        """
        ワークフロー状態を作成して保存
        
        Args:
            idea_name: アイデア名
            current_channel: 現在のチャンネル
            
        Returns:
            作成されたWorkflowState
        """
        # 次のチャンネルを決定
        channel_flow = {
            "1-idea": "2-requirements",
            "2-requirements": "3-design",
            "3-design": "4-tasks",
            "4-tasks": "5-development",
            "5-development": None
        }
        
        next_channel = None
        for key, next_ch in channel_flow.items():
            if key in current_channel:
                next_channel = next_ch
                break
        
        workflow_state = WorkflowState(
            idea_name=idea_name,
            current_channel=current_channel,
            next_channel=next_channel
        )
        
        self.workflow_states[idea_name] = workflow_state
        logger.info(f"Created workflow state: {workflow_state}")
        
        return workflow_state
    
    def update_project_stage(self, idea_name: str, new_stage: str) -> bool:
        """
        プロジェクトのステージを更新
        
        Args:
            idea_name: アイデア名
            new_stage: 新しいステージ
            
        Returns:
            更新成功時True
        """
        if idea_name in self.project_info:
            self.project_info[idea_name].current_stage = new_stage
            
            # ワークフロー状態も更新
            if idea_name in self.workflow_states:
                self.workflow_states[idea_name].completed_stages.append(new_stage)
            
            logger.info(f"Updated project stage: {idea_name} -> {new_stage}")
            return True
        
        return False
    
    def add_project_document(self, idea_name: str, doc_type: str, doc_path: Path) -> bool:
        """
        プロジェクトにドキュメントを追加
        
        Args:
            idea_name: アイデア名
            doc_type: ドキュメントタイプ（idea, requirements, design, tasks）
            doc_path: ドキュメントパス
            
        Returns:
            追加成功時True
        """
        if idea_name in self.project_info:
            self.project_info[idea_name].documents[doc_type] = doc_path
            logger.info(f"Added document to project {idea_name}: {doc_type} -> {doc_path}")
            return True
        
        return False
    
    def get_idea_name_by_thread(self, thread_id: str) -> Optional[str]:
        """
        スレッドIDからアイデア名を取得
        
        Args:
            thread_id: DiscordスレッドID
            
        Returns:
            アイデア名、存在しない場合はNone
        """
        return self.thread_to_idea.get(thread_id)
    
    def get_project_by_name(self, idea_name: str) -> Optional[ProjectInfo]:
        """
        アイデア名からプロジェクト情報を取得
        
        Args:
            idea_name: アイデア名
            
        Returns:
            プロジェクト情報、存在しない場合はNone
        """
        return self.project_info.get(idea_name)
    
    def get_workflow_state(self, idea_name: str) -> Optional[WorkflowState]:
        """
        アイデア名からワークフロー状態を取得
        
        Args:
            idea_name: アイデア名
            
        Returns:
            ワークフロー状態、存在しない場合はNone
        """
        return self.workflow_states.get(idea_name)
    
    def add_thread_to_workflow(self, idea_name: str, channel: str, thread_id: str) -> bool:
        """
        ワークフロー状態にスレッドIDを追加
        
        Args:
            idea_name: アイデア名
            channel: チャンネル名
            thread_id: スレッドID
            
        Returns:
            追加成功時True
        """
        if idea_name in self.workflow_states:
            self.workflow_states[idea_name].thread_ids[channel] = thread_id
            self.thread_to_idea[thread_id] = idea_name
            logger.info(f"Added thread to workflow: {idea_name}, {channel} -> {thread_id}")
            return True
        
        return False

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