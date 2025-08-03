#!/usr/bin/env python3
"""
ProjectManagerのユニットテスト
"""

import os
import sys
import shutil
import tempfile
import asyncio
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.project_manager import ProjectManager


class TestProjectManager:
    """ProjectManagerのテストクラス"""
    
    @pytest.fixture
    def temp_dir(self):
        """テスト用一時ディレクトリ"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    def project_manager(self, temp_dir, monkeypatch):
        """テスト用ProjectManagerインスタンス"""
        # ProjectManagerのパスをモック
        pm = ProjectManager()
        pm.achi_kun_root = Path(temp_dir)
        pm.bot_dir = Path(temp_dir) / "achi-kun-discord-bot"
        pm.projects_dir = Path(temp_dir) / "projects"
        
        # bot_dirを作成（.github用）
        pm.bot_dir.mkdir(parents=True)
        
        return pm
    
    def test_create_project_structure_success(self, project_manager):
        """プロジェクト構造の作成成功テスト"""
        idea_name = "test-project"
        
        # プロジェクト作成
        project_path = project_manager.create_project_structure(idea_name)
        
        # 検証
        assert project_path.exists()
        assert project_path == project_manager.projects_dir / idea_name
        assert project_manager.projects_dir.exists()
    
    def test_create_project_structure_already_exists(self, project_manager):
        """既存プロジェクトでのエラーテスト"""
        idea_name = "existing-project"
        
        # 最初の作成
        project_manager.create_project_structure(idea_name)
        
        # 2回目はエラーになるはず
        with pytest.raises(FileExistsError) as exc_info:
            project_manager.create_project_structure(idea_name)
        
        assert "既に存在します" in str(exc_info.value)
    
    def test_create_document_success(self, project_manager):
        """ドキュメント作成成功テスト"""
        idea_name = "doc-test"
        content = "# Test Document\n\nThis is a test."
        
        # プロジェクト作成
        project_manager.create_project_structure(idea_name)
        
        # 各ドキュメントタイプでテスト
        for doc_type in ["idea", "requirements", "design", "tasks"]:
            file_path = project_manager.create_document(idea_name, doc_type, content)
            
            # 検証
            assert file_path.exists()
            assert file_path.name == f"{doc_type}.md"
            with open(file_path, 'r', encoding='utf-8') as f:
                assert f.read() == content
    
    def test_create_document_invalid_type(self, project_manager):
        """無効なドキュメントタイプのテスト"""
        idea_name = "invalid-doc"
        project_manager.create_project_structure(idea_name)
        
        with pytest.raises(ValueError) as exc_info:
            project_manager.create_document(idea_name, "invalid", "content")
        
        assert "無効なドキュメントタイプ" in str(exc_info.value)
    
    def test_create_document_no_project(self, project_manager):
        """プロジェクトが存在しない場合のテスト"""
        with pytest.raises(FileNotFoundError) as exc_info:
            project_manager.create_document("non-existent", "idea", "content")
        
        assert "プロジェクトディレクトリが見つかりません" in str(exc_info.value)
    
    def test_copy_to_development_success(self, project_manager):
        """開発ディレクトリへのコピー成功テスト"""
        idea_name = "copy-test"
        
        # プロジェクト作成とファイル追加
        project_manager.create_project_structure(idea_name)
        project_manager.create_document(idea_name, "idea", "# Idea")
        project_manager.create_document(idea_name, "requirements", "# Requirements")
        
        # コピー実行
        dev_path = project_manager.copy_to_development(idea_name)
        
        # 検証
        assert dev_path.exists()
        assert dev_path == project_manager.achi_kun_root / idea_name
        assert (dev_path / "idea.md").exists()
        assert (dev_path / "requirements.md").exists()
    
    def test_copy_to_development_already_exists(self, project_manager):
        """開発ディレクトリが既に存在する場合のテスト"""
        idea_name = "existing-dev"
        
        # プロジェクト作成
        project_manager.create_project_structure(idea_name)
        
        # 開発ディレクトリを先に作成
        dev_path = project_manager.achi_kun_root / idea_name
        dev_path.mkdir(parents=True)
        
        # コピーはエラーになるはず
        with pytest.raises(FileExistsError) as exc_info:
            project_manager.copy_to_development(idea_name)
        
        assert "開発ディレクトリが既に存在します" in str(exc_info.value)
    
    def test_copy_github_workflows_success(self, project_manager):
        """GitHubワークフローのコピー成功テスト"""
        idea_name = "workflow-test"
        
        # ソースワークフローを作成
        source_workflows = project_manager.bot_dir / ".github" / "workflows"
        source_workflows.mkdir(parents=True)
        (source_workflows / "test.yml").write_text("name: Test")
        (source_workflows / "deploy.yml").write_text("name: Deploy")
        
        # 開発ディレクトリを作成
        dev_path = project_manager.achi_kun_root / idea_name
        dev_path.mkdir(parents=True)
        
        # コピー実行
        project_manager.copy_github_workflows(idea_name)
        
        # 検証
        target_workflows = dev_path / ".github" / "workflows"
        assert target_workflows.exists()
        assert (target_workflows / "test.yml").exists()
        assert (target_workflows / "deploy.yml").exists()
    
    @pytest.mark.asyncio
    async def test_init_git_repository_success(self, project_manager):
        """Gitリポジトリ初期化成功テスト"""
        # テスト用ディレクトリ作成
        test_dir = project_manager.achi_kun_root / "git-test"
        test_dir.mkdir(parents=True)
        
        # Git初期化
        success, message = await project_manager.init_git_repository(test_dir)
        
        # 検証
        assert success
        assert (test_dir / ".git").exists()
    
    @pytest.mark.asyncio
    async def test_execute_git_command_success(self, project_manager):
        """Gitコマンド実行成功テスト"""
        # テスト用リポジトリ作成
        test_dir = project_manager.achi_kun_root / "git-cmd-test"
        test_dir.mkdir(parents=True)
        await project_manager.init_git_repository(test_dir)
        
        # テストファイル作成
        test_file = test_dir / "test.txt"
        test_file.write_text("test content")
        
        # git add実行
        success, message = await project_manager.execute_git_command(
            test_dir, ["git", "add", "."]
        )
        
        # 検証
        assert success
    
    def test_get_project_path(self, project_manager):
        """プロジェクトパス取得テスト"""
        idea_name = "path-test"
        expected = project_manager.projects_dir / idea_name
        
        assert project_manager.get_project_path(idea_name) == expected
    
    def test_get_development_path(self, project_manager):
        """開発パス取得テスト"""
        idea_name = "dev-path-test"
        expected = project_manager.achi_kun_root / idea_name
        
        assert project_manager.get_development_path(idea_name) == expected
    
    def test_project_exists(self, project_manager):
        """プロジェクト存在チェックテスト"""
        idea_name = "exists-test"
        
        # 存在しない場合
        assert not project_manager.project_exists(idea_name)
        
        # 作成後
        project_manager.create_project_structure(idea_name)
        assert project_manager.project_exists(idea_name)
    
    def test_development_exists(self, project_manager):
        """開発ディレクトリ存在チェックテスト"""
        idea_name = "dev-exists-test"
        
        # 存在しない場合
        assert not project_manager.development_exists(idea_name)
        
        # 作成後
        dev_path = project_manager.achi_kun_root / idea_name
        dev_path.mkdir(parents=True)
        assert project_manager.development_exists(idea_name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])