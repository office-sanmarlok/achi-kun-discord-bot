#!/usr/bin/env python3
"""
Project Manager - プロジェクトディレクトリとファイル管理

このモジュールは以下の責務を持つ：
1. プロジェクトディレクトリ構造の作成と管理
2. ドキュメントファイルの作成
3. プロジェクトファイルのコピー操作
4. Git操作のラッパー機能
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime
from lib.command_executor import execute_git_command as exec_git_cmd, async_run

logger = logging.getLogger(__name__)


class ProjectManager:
    """プロジェクトディレクトリとファイルを管理するクラス"""
    
    def __init__(self):
        """初期化"""
        # 環境変数からプロジェクトルートを取得（必須）
        project_root = os.environ.get('PROJECT_ROOT')
        
        if not project_root:
            raise EnvironmentError(
                "PROJECT_ROOT環境変数が設定されていません。"
                ".envファイルに PROJECT_ROOT=/home/seito_nakagane/project-wsl を設定してください。"
            )
        
        # 環境変数から設定
        self.project_wsl_root = Path(project_root)
        
        # ディレクトリの設定
        self.achi_kun_root = self.project_wsl_root  # 開発用ディレクトリ（project-wslそのもの）
        self.projects_dir = self.project_wsl_root / "projects"  # ドキュメント用ディレクトリ
        self.projects_root = self.projects_dir  # エイリアスを追加
        
        # GitHub workflowテンプレートのパス
        self.workflow_templates_dir = self.project_wsl_root / "github-workflow-templates" / ".github"
        
        logger.info(f"ProjectManager initialized - projects: {self.projects_dir}, achi-kun: {self.achi_kun_root}")
    
    
    def create_project_structure(self, idea_name: str) -> Path:
        """
        プロジェクト構造を作成
        
        Args:
            idea_name: プロジェクト名（小文字とハイフンのみ）
            
        Returns:
            作成されたプロジェクトディレクトリのPath
            
        Raises:
            FileExistsError: ディレクトリが既に存在する場合
        """
        # projectsディレクトリが存在しない場合は作成
        if not self.projects_dir.exists():
            self.projects_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created projects directory: {self.projects_dir}")
        
        # プロジェクトディレクトリのパス
        project_path = self.projects_dir / idea_name
        
        # 既に存在する場合はエラー
        if project_path.exists():
            raise FileExistsError(f"プロジェクトディレクトリが既に存在します: {project_path}")
        
        # ディレクトリ作成
        project_path.mkdir(parents=True)
        logger.info(f"Created project directory: {project_path}")
        
        return project_path
    
    def create_document(self, idea_name: str, doc_type: str, content: str = "") -> Path:
        """
        ドキュメントファイルを作成
        
        Args:
            idea_name: プロジェクト名
            doc_type: ドキュメントタイプ（idea, requirements, design, tasks）
            content: ファイルの初期内容
            
        Returns:
            作成されたファイルのPath
        """
        # ドキュメントファイル名の検証
        valid_doc_types = ["idea", "requirements", "design", "tasks"]
        if doc_type not in valid_doc_types:
            raise ValueError(f"無効なドキュメントタイプ: {doc_type}")
        
        # プロジェクトディレクトリ
        project_path = self.projects_dir / idea_name
        if not project_path.exists():
            raise FileNotFoundError(f"プロジェクトディレクトリが見つかりません: {project_path}")
        
        # ファイルパス
        file_path = project_path / f"{doc_type}.md"
        
        # ファイル作成
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created document: {file_path}")
        return file_path
    
    def copy_to_development(self, idea_name: str) -> Path:
        """
        プロジェクトを開発ディレクトリにコピー
        
        Args:
            idea_name: プロジェクト名
            
        Returns:
            コピー先のPath
            
        Raises:
            FileNotFoundError: ソースディレクトリが存在しない場合
            FileExistsError: 開発ディレクトリが既に存在する場合
        """
        # ソースとターゲットのパス
        source_path = self.projects_dir / idea_name
        target_path = self.achi_kun_root / idea_name
        
        # ソースの存在確認
        if not source_path.exists():
            raise FileNotFoundError(f"プロジェクトディレクトリが見つかりません: {source_path}")
        
        # ターゲットの存在確認
        if target_path.exists():
            raise FileExistsError(f"開発ディレクトリが既に存在します: {target_path}")
        
        # コピー実行
        shutil.copytree(source_path, target_path)
        logger.info(f"Copied project to development: {source_path} -> {target_path}")
        
        return target_path
    
    def copy_github_workflows(self, idea_name: str) -> None:
        """
        GitHub Actionsワークフローテンプレートをコピー
        
        Args:
            idea_name: プロジェクト名
            
        Raises:
            FileNotFoundError: テンプレートまたはターゲットが見つからない場合
        """
        # ソースとターゲットのパス
        source_workflows = self.workflow_templates_dir
        target_dir = self.achi_kun_root / idea_name
        target_workflows = target_dir / ".github"
        
        # テンプレートの存在確認
        if not source_workflows.exists():
            logger.warning(f"ワークフローテンプレートが見つかりません: {source_workflows}")
            logger.info("テンプレートなしで続行します")
            return
        
        # ターゲットディレクトリの存在確認
        if not target_dir.exists():
            raise FileNotFoundError(f"開発ディレクトリが見つかりません: {target_dir}")
        
        # 既存の.githubディレクトリがある場合は削除
        if target_workflows.exists():
            shutil.rmtree(target_workflows)
        
        # コピー実行
        shutil.copytree(source_workflows, target_workflows)
        logger.info(f"Copied GitHub workflow templates: {source_workflows} -> {target_workflows}")
    
    async def init_git_repository(self, path: Path) -> Tuple[bool, str]:
        """
        Gitリポジトリを初期化
        
        Args:
            path: リポジトリのパス
            
        Returns:
            (成功フラグ, 出力メッセージ)
        """
        try:
            # git initコマンドを実行
            result = await async_run(["git", "init"], cwd=str(path))
            
            if result[0]:
                logger.info(f"Initialized git repository: {path}")
            else:
                logger.error(f"Failed to initialize git repository: {result[1]}")
            
            return result
            
        except Exception as e:
            error_msg = f"Git初期化エラー: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def execute_git_command(self, path: Path, command: List[str]) -> Tuple[bool, str]:
        """
        任意のGitコマンドを実行
        
        Args:
            path: 実行ディレクトリ
            command: Gitコマンドのリスト（例: ["git", "add", "."]）
            
        Returns:
            (成功フラグ, 出力メッセージ)
        """
        # "git"コマンドが先頭にある場合は削除（exec_git_cmdが自動的に追加するため）
        if command and command[0] == "git":
            git_args = command[1:]
        else:
            git_args = command
        
        return await exec_git_cmd(path, git_args, verbose=True)
    
    def get_project_path(self, idea_name: str) -> Path:
        """プロジェクトディレクトリのパスを取得"""
        return self.projects_dir / idea_name
    
    def get_development_path(self, idea_name: str) -> Path:
        """開発ディレクトリのパスを取得"""
        return self.achi_kun_root / idea_name
    
    def project_exists(self, idea_name: str) -> bool:
        """プロジェクトが存在するかチェック"""
        return self.get_project_path(idea_name).exists()
    
    def development_exists(self, idea_name: str) -> bool:
        """開発ディレクトリが存在するかチェック"""
        return self.get_development_path(idea_name).exists()