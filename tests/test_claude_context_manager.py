#!/usr/bin/env python3
"""
ClaudeContextManagerのユニットテスト
"""

import sys
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.claude_context_manager import ClaudeContextManager


class TestClaudeContextManager:
    """ClaudeContextManagerのテストクラス"""
    
    @pytest.fixture
    def context_manager(self, tmp_path):
        """テスト用ClaudeContextManagerインスタンス"""
        # テスト用のSDD.mdを作成
        sdd_path = tmp_path / "test_sdd.md"
        sdd_path.write_text("# Test SDD Document")
        
        return ClaudeContextManager(sdd_path=sdd_path)
    
    def test_generate_initial_context_basic(self, context_manager):
        """基本的な初期コンテキスト生成テスト"""
        session_num = 1
        thread_info = {
            "channel_name": "#1-idea",
            "thread_name": "test-project",
            "thread_id": "123456789"
        }
        
        context = context_manager.generate_initial_context(session_num, thread_info)
        
        # 検証
        assert "=== Discord スレッド情報 ===" in context
        assert "チャンネル名: #1-idea" in context
        assert "スレッド名: test-project" in context
        assert "スレッドID: 123456789" in context
        assert "セッション番号: 1" in context
        assert "dp 1 \"メッセージ\"" in context
        assert "親メッセージ" not in context  # 親メッセージなし
    
    def test_generate_initial_context_with_parent(self, context_manager):
        """親メッセージ付き初期コンテキスト生成テスト"""
        session_num = 2
        thread_info = {
            "channel_name": "#2-requirements",
            "thread_name": "awesome-app",
            "thread_id": "987654321"
        }
        parent_message = {
            "author": "TestUser",
            "timestamp": "2024-01-01 12:00:00",
            "content": "This is a test message\nwith multiple lines"
        }
        
        context = context_manager.generate_initial_context(
            session_num, thread_info, parent_message
        )
        
        # 検証
        assert "=== 親メッセージ ===" in context
        assert "作成者: TestUser" in context
        assert "時刻: 2024-01-01 12:00:00" in context
        assert "This is a test message\nwith multiple lines" in context
        assert "===================" in context
    
    def test_generate_idea_prompt(self, context_manager):
        """idea.md生成プロンプトテスト"""
        idea_name = "test-app"
        parent_content = "I want to create a todo list application"
        
        prompt = context_manager.generate_idea_prompt(idea_name, parent_content)
        
        # 検証
        assert f"./projects/{idea_name}/idea.md" in prompt
        assert "企画提案書" in prompt
        assert parent_content in prompt
        assert "プロジェクトの概要" in prompt
        assert "解決したい課題" in prompt
        assert "提案する解決策" in prompt
    
    def test_generate_requirements_prompt(self, context_manager):
        """requirements.md生成プロンプトテスト"""
        idea_name = "test-app"
        
        prompt = context_manager.generate_requirements_prompt(idea_name)
        
        # 検証
        assert f"./projects/{idea_name}/idea.md" in prompt
        assert f"./projects/{idea_name}/requirements.md" in prompt
        assert str(context_manager.sdd_path) in prompt
        assert "Requirement Gathering" in prompt
        assert "User Story" in prompt
        assert "Acceptance Criteria" in prompt
        assert "EARS形式" in prompt
        assert "WHEN [event] THEN [system] SHALL [response]" in prompt
    
    def test_generate_design_prompt(self, context_manager):
        """design.md生成プロンプトテスト"""
        idea_name = "test-app"
        
        prompt = context_manager.generate_design_prompt(idea_name)
        
        # 検証
        assert f"./projects/{idea_name}/requirements.md" in prompt
        assert f"./projects/{idea_name}/design.md" in prompt
        assert str(context_manager.sdd_path) in prompt
        assert "Create Feature Design Document" in prompt
        assert "Architecture" in prompt
        assert "Components and Interfaces" in prompt
        assert "Data Models" in prompt
        assert "Error Handling" in prompt
        assert "Testing Strategy" in prompt
        assert "Mermaid" in prompt
    
    def test_generate_tasks_prompt(self, context_manager):
        """tasks.md生成プロンプトテスト"""
        idea_name = "test-app"
        
        prompt = context_manager.generate_tasks_prompt(idea_name)
        
        # 検証
        assert f"./projects/{idea_name}/design.md" in prompt
        assert f"./projects/{idea_name}/tasks.md" in prompt
        assert str(context_manager.sdd_path) in prompt
        assert "Create Task List" in prompt
        assert "テスト駆動開発" in prompt
        assert "番号付きチェックボックスリスト" in prompt
        assert "_Requirements: X.X_" in prompt
        assert "コーディングタスクのみ" in prompt
        assert "デプロイメント" in prompt  # 除外項目
    
    def test_generate_development_prompt(self, context_manager):
        """開発開始プロンプトテスト"""
        idea_name = "test-app"
        
        prompt = context_manager.generate_development_prompt(idea_name)
        
        # 検証
        assert f"./projects/{idea_name}/tasks.md" in prompt
        assert "v0の開発を開始" in prompt
        assert "チェックボックスを埋めて" in prompt
        assert "テスト駆動開発" in prompt
        assert "最初のタスクから開始" in prompt
    
    def test_format_complete_message(self, context_manager):
        """!complete時の次チャンネルメッセージテスト"""
        idea_name = "test-app"
        
        # 各ステージでテスト
        assert context_manager.format_complete_message("idea", idea_name) == f"要件定義: {idea_name}"
        assert context_manager.format_complete_message("requirements", idea_name) == f"設計: {idea_name}"
        assert context_manager.format_complete_message("design", idea_name) == f"タスクリスト作成: {idea_name}"
        assert context_manager.format_complete_message("tasks", idea_name) == f"開発: {idea_name}"
        
        # 未知のステージ
        assert context_manager.format_complete_message("unknown", idea_name) == f"次フェーズ: {idea_name}"
    
    def test_get_stage_from_channel(self, context_manager):
        """チャンネル名からステージ判定テスト"""
        # 正確なチャンネル名
        assert context_manager.get_stage_from_channel("1-idea") == "idea"
        assert context_manager.get_stage_from_channel("2-requirements") == "requirements"
        assert context_manager.get_stage_from_channel("3-design") == "design"
        assert context_manager.get_stage_from_channel("4-tasks") == "tasks"
        assert context_manager.get_stage_from_channel("5-development") == "development"
        
        # プレフィックス付きチャンネル名
        assert context_manager.get_stage_from_channel("#1-idea") == "idea"
        assert context_manager.get_stage_from_channel("test-2-requirements") == "requirements"
        
        # 未知のチャンネル
        assert context_manager.get_stage_from_channel("general") is None
        assert context_manager.get_stage_from_channel("random-channel") is None
    
    def test_default_sdd_path(self):
        """デフォルトSDD.mdパステスト"""
        manager = ClaudeContextManager()
        
        # デフォルトパスが正しく設定されているか
        assert manager.sdd_path.name == "SDD.md"
        assert "docs" in str(manager.sdd_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])