#!/usr/bin/env python3
"""
拡張されたSessionManagerのユニットテスト
"""

import sys
from pathlib import Path
from datetime import datetime
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.session_manager import (
    SessionManager, SessionInfo, ProjectInfo, WorkflowState, get_session_manager
)


class TestSessionManagerExtended:
    """拡張されたSessionManagerのテストクラス"""
    
    @pytest.fixture
    def session_manager(self):
        """テスト用の新しいSessionManagerインスタンス"""
        # 既存のグローバルインスタンスをリセット
        import src.session_manager
        src.session_manager._session_manager = None
        return get_session_manager()
    
    def test_data_models_creation(self):
        """データモデルの作成テスト"""
        # SessionInfo
        session_info = SessionInfo(
            session_num=1,
            thread_id="123456",
            idea_name="test-app",
            created_at=datetime.now(),
            current_stage="idea",
            tmux_session_name="claude-session-1",
            working_directory="/test/dir"
        )
        assert session_info.session_num == 1
        assert session_info.idea_name == "test-app"
        
        # ProjectInfo
        project_info = ProjectInfo(
            idea_name="test-app",
            created_at=datetime.now(),
            current_stage="idea",
            project_path=Path("/projects/test-app")
        )
        assert project_info.idea_name == "test-app"
        assert project_info.documents == {}
        
        # WorkflowState
        workflow_state = WorkflowState(
            idea_name="test-app",
            current_channel="1-idea",
            next_channel="2-requirements"
        )
        assert workflow_state.completed_stages == []
        assert workflow_state.thread_ids == {}
    
    def test_create_session_info(self, session_manager):
        """セッション情報作成テスト"""
        session_info = session_manager.create_session_info(
            session_num=1,
            thread_id="thread123",
            idea_name="my-project",
            current_stage="idea",
            working_directory="/workspace"
        )
        
        # 作成確認
        assert session_info.session_num == 1
        assert session_info.thread_id == "thread123"
        assert session_info.tmux_session_name == "claude-session-1"
        
        # 保存確認
        assert session_manager.session_info[1] == session_info
        assert session_manager.thread_to_idea["thread123"] == "my-project"
    
    def test_create_project_info(self, session_manager):
        """プロジェクト情報作成テスト"""
        project_path = Path("/projects/awesome-app")
        project_info = session_manager.create_project_info(
            idea_name="awesome-app",
            project_path=project_path
        )
        
        # 作成確認
        assert project_info.idea_name == "awesome-app"
        assert project_info.current_stage == "idea"
        assert project_info.project_path == project_path
        
        # 保存確認
        assert session_manager.project_info["awesome-app"] == project_info
    
    def test_create_workflow_state(self, session_manager):
        """ワークフロー状態作成テスト"""
        # 各ステージでテスト
        test_cases = [
            ("1-idea", "2-requirements"),
            ("2-requirements", "3-design"),
            ("3-design", "4-tasks"),
            ("4-tasks", "5-development"),
            ("5-development", None)
        ]
        
        for current, expected_next in test_cases:
            workflow_state = session_manager.create_workflow_state(
                idea_name=f"test-{current}",
                current_channel=f"channel-{current}"
            )
            
            assert workflow_state.idea_name == f"test-{current}"
            assert workflow_state.current_channel == f"channel-{current}"
            assert workflow_state.next_channel == expected_next
    
    def test_update_project_stage(self, session_manager):
        """プロジェクトステージ更新テスト"""
        # プロジェクトとワークフローを作成
        session_manager.create_project_info("update-test", Path("/test"))
        session_manager.create_workflow_state("update-test", "1-idea")
        
        # ステージ更新
        success = session_manager.update_project_stage("update-test", "requirements")
        
        assert success is True
        assert session_manager.project_info["update-test"].current_stage == "requirements"
        assert "requirements" in session_manager.workflow_states["update-test"].completed_stages
        
        # 存在しないプロジェクト
        success = session_manager.update_project_stage("non-existent", "design")
        assert success is False
    
    def test_add_project_document(self, session_manager):
        """プロジェクトドキュメント追加テスト"""
        # プロジェクト作成
        session_manager.create_project_info("doc-test", Path("/test"))
        
        # ドキュメント追加
        doc_path = Path("/test/idea.md")
        success = session_manager.add_project_document("doc-test", "idea", doc_path)
        
        assert success is True
        assert session_manager.project_info["doc-test"].documents["idea"] == doc_path
        
        # 複数ドキュメント
        session_manager.add_project_document("doc-test", "requirements", Path("/test/req.md"))
        session_manager.add_project_document("doc-test", "design", Path("/test/design.md"))
        
        docs = session_manager.project_info["doc-test"].documents
        assert len(docs) == 3
        assert "requirements" in docs
        assert "design" in docs
    
    def test_get_idea_name_by_thread(self, session_manager):
        """スレッドIDからアイデア名取得テスト"""
        # セッション情報作成
        session_manager.create_session_info(
            1, "thread999", "lookup-test", "idea", "/workspace"
        )
        
        # 取得テスト
        idea_name = session_manager.get_idea_name_by_thread("thread999")
        assert idea_name == "lookup-test"
        
        # 存在しないスレッド
        assert session_manager.get_idea_name_by_thread("unknown") is None
    
    def test_get_project_by_name(self, session_manager):
        """アイデア名からプロジェクト取得テスト"""
        # プロジェクト作成
        project_path = Path("/projects/get-test")
        session_manager.create_project_info("get-test", project_path)
        
        # 取得テスト
        project = session_manager.get_project_by_name("get-test")
        assert project is not None
        assert project.idea_name == "get-test"
        assert project.project_path == project_path
        
        # 存在しないプロジェクト
        assert session_manager.get_project_by_name("unknown") is None
    
    def test_get_workflow_state(self, session_manager):
        """ワークフロー状態取得テスト"""
        # ワークフロー作成
        session_manager.create_workflow_state("workflow-test", "3-design")
        
        # 取得テスト
        workflow = session_manager.get_workflow_state("workflow-test")
        assert workflow is not None
        assert workflow.current_channel == "3-design"
        assert workflow.next_channel == "4-tasks"
        
        # 存在しないワークフロー
        assert session_manager.get_workflow_state("unknown") is None
    
    def test_add_thread_to_workflow(self, session_manager):
        """ワークフローへのスレッド追加テスト"""
        # ワークフロー作成
        session_manager.create_workflow_state("thread-test", "1-idea")
        
        # スレッド追加
        success = session_manager.add_thread_to_workflow(
            "thread-test", "1-idea", "thread111"
        )
        
        assert success is True
        workflow = session_manager.get_workflow_state("thread-test")
        assert workflow.thread_ids["1-idea"] == "thread111"
        assert session_manager.thread_to_idea["thread111"] == "thread-test"
        
        # 複数チャンネルにスレッド追加
        session_manager.add_thread_to_workflow(
            "thread-test", "2-requirements", "thread222"
        )
        assert len(workflow.thread_ids) == 2
        
        # 存在しないワークフロー
        success = session_manager.add_thread_to_workflow(
            "unknown", "1-idea", "thread999"
        )
        assert success is False
    
    def test_get_stats_extended(self, session_manager):
        """拡張統計情報取得テスト"""
        # 複数のデータを作成
        session_manager.create_project_info("proj1", Path("/p1"))
        session_manager.create_project_info("proj2", Path("/p2"))
        session_manager.create_workflow_state("proj1", "1-idea")
        session_manager.get_or_create_session("thread1")
        session_manager.get_or_create_session("thread2")
        
        stats = session_manager.get_stats()
        
        assert stats["total_sessions"] == 2
        assert stats["total_projects"] == 2
        assert stats["active_workflows"] == 1
    
    def test_integration_workflow(self, session_manager):
        """統合ワークフローテスト"""
        idea_name = "integration-test"
        
        # 1. !ideaコマンドシミュレーション
        thread_id = "thread-integration"
        session_num = session_manager.get_or_create_session(thread_id)
        
        session_manager.create_session_info(
            session_num, thread_id, idea_name, "idea", "/workspace"
        )
        
        project_path = Path(f"/projects/{idea_name}")
        session_manager.create_project_info(idea_name, project_path)
        session_manager.create_workflow_state(idea_name, "1-idea")
        session_manager.add_thread_to_workflow(idea_name, "1-idea", thread_id)
        
        # 2. ドキュメント追加
        session_manager.add_project_document(
            idea_name, "idea", project_path / "idea.md"
        )
        
        # 3. !completeコマンドシミュレーション
        session_manager.update_project_stage(idea_name, "requirements")
        
        # 検証
        project = session_manager.get_project_by_name(idea_name)
        workflow = session_manager.get_workflow_state(idea_name)
        
        assert project.current_stage == "requirements"
        assert "idea" in project.documents
        assert workflow.next_channel == "2-requirements"
        assert len(workflow.completed_stages) == 1
        assert session_manager.get_idea_name_by_thread(thread_id) == idea_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])