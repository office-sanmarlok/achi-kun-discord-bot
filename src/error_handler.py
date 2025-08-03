#!/usr/bin/env python3
"""
Error Handler - 統一的なエラー処理とユーザーフィードバック

このモジュールは以下の責務を持つ：
1. エラーの分類と処理
2. ユーザーへのフィードバックメッセージ生成
3. エラーログの記録
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """エラーカテゴリの定義"""
    INVALID_INPUT = "invalid_input"
    PROJECT_NOT_FOUND = "project_not_found"
    PROJECT_EXISTS = "project_exists"
    GIT_ERROR = "git_error"
    CHANNEL_NOT_FOUND = "channel_not_found"
    PERMISSION_ERROR = "permission_error"
    SESSION_ERROR = "session_error"
    GITHUB_ERROR = "github_error"
    SYSTEM_ERROR = "system_error"


class ErrorHandler:
    """統一的なエラー処理を提供するクラス"""
    
    # エラーメッセージテンプレート
    ERROR_MESSAGES = {
        ErrorCategory.INVALID_INPUT: {
            "idea_name": "❌ 無効なアイデア名です。小文字英字とハイフンのみ使用可能です（例: my-awesome-app）",
            "no_parent": "❌ このコマンドはメッセージへの返信として実行してください",
            "thread_only": "❌ このコマンドはスレッド内でのみ使用可能です",
            "channel_only": "❌ このチャンネルでは{command}コマンドを使用できません"
        },
        ErrorCategory.PROJECT_NOT_FOUND: {
            "default": "❌ プロジェクト `{project_name}` が見つかりません",
            "path": "❌ プロジェクトパス `{path}` が存在しません"
        },
        ErrorCategory.PROJECT_EXISTS: {
            "default": "❌ プロジェクト `{project_name}` は既に存在します",
            "dev_dir": "❌ 開発ディレクトリ `{project_name}` は既に存在します"
        },
        ErrorCategory.GIT_ERROR: {
            "init": "❌ Git初期化エラー:\n```\n{error}\n```",
            "commit": "❌ Gitコミットエラー:\n```\n{error}\n```",
            "push": "❌ Gitプッシュエラー:\n```\n{error}\n```\n`git remote -v`でリモート設定を確認してください",
            "general": "❌ Gitエラー:\n```\n{error}\n```"
        },
        ErrorCategory.CHANNEL_NOT_FOUND: {
            "default": "❌ #{channel_name}チャンネルが見つかりません",
            "next": "❌ 次のステージのチャンネルが見つかりません"
        },
        ErrorCategory.PERMISSION_ERROR: {
            "send": "❌ #{channel_name}チャンネルへのメッセージ送信権限がありません",
            "thread": "❌ スレッド作成権限がありません",
            "read": "❌ チャンネルの読み取り権限がありません"
        },
        ErrorCategory.SESSION_ERROR: {
            "start": "❌ Claude Codeセッションの開始に失敗しました:\n```\n{error}\n```",
            "tmux": "❌ tmuxセッションエラー:\n```\n{error}\n```",
            "exists": "❌ セッション番号 {session_num} は既に使用中です"
        },
        ErrorCategory.GITHUB_ERROR: {
            "create": "❌ GitHubリポジトリ作成エラー:\n```\n{error}\n```\n`gh auth login`で認証を確認してください",
            "auth": "❌ GitHub認証エラー。`gh auth login`を実行してください",
            "api": "❌ GitHub APIエラー:\n```\n{error}\n```"
        },
        ErrorCategory.SYSTEM_ERROR: {
            "default": "❌ システムエラーが発生しました:\n```\n{error}\n```",
            "unexpected": "❌ 予期しないエラーが発生しました。詳細はログを確認してください"
        }
    }
    
    @classmethod
    def format_error(cls, category: ErrorCategory, error_type: str = "default", 
                    **kwargs) -> str:
        """
        エラーメッセージをフォーマット
        
        Args:
            category: エラーカテゴリ
            error_type: エラータイプ（デフォルト: "default"）
            **kwargs: メッセージに埋め込む変数
            
        Returns:
            フォーマットされたエラーメッセージ
        """
        try:
            messages = cls.ERROR_MESSAGES.get(category, {})
            template = messages.get(error_type, messages.get("default", "❌ エラーが発生しました"))
            
            # テンプレートに必要な変数を抽出してデフォルト値を設定
            import re
            placeholders = re.findall(r'\{(\w+)\}', template)
            for placeholder in placeholders:
                if placeholder not in kwargs:
                    kwargs[placeholder] = f"<{placeholder}>"
            
            return template.format(**kwargs)
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return "❌ エラーが発生しました"
    
    @classmethod
    def log_error(cls, category: ErrorCategory, error: Exception, 
                  context: Optional[Dict[str, Any]] = None) -> None:
        """
        エラーをログに記録
        
        Args:
            category: エラーカテゴリ
            error: 発生した例外
            context: 追加のコンテキスト情報
        """
        log_message = f"[{category.value}] {str(error)}"
        if context:
            log_message += f" | Context: {context}"
        
        logger.error(log_message, exc_info=True)
    
    @classmethod
    def handle_discord_error(cls, error: Exception) -> str:
        """
        Discord関連のエラーを処理
        
        Args:
            error: Discord例外
            
        Returns:
            ユーザー向けエラーメッセージ
        """
        import discord
        
        if isinstance(error, discord.Forbidden):
            return cls.format_error(ErrorCategory.PERMISSION_ERROR, "send")
        elif isinstance(error, discord.NotFound):
            return cls.format_error(ErrorCategory.CHANNEL_NOT_FOUND)
        elif isinstance(error, discord.HTTPException):
            return cls.format_error(ErrorCategory.SYSTEM_ERROR, "default", error=str(error))
        else:
            return cls.format_error(ErrorCategory.SYSTEM_ERROR, "unexpected")
    
    @classmethod
    def create_loading_message(cls, action: str) -> str:
        """
        ローディングメッセージを生成
        
        Args:
            action: 実行中のアクション
            
        Returns:
            ローディングメッセージ
        """
        messages = {
            "default": "`...` 処理中...",
            "git": "`...` Git操作を実行中...",
            "github": "`...` GitHubリポジトリを作成中...",
            "session": "`...` Claude Codeセッションを開始中...",
            "thread": "`...` スレッドを作成中..."
        }
        return messages.get(action, messages["default"])
    
    @classmethod
    def create_success_message(cls, action: str, **kwargs) -> str:
        """
        成功メッセージを生成
        
        Args:
            action: 完了したアクション
            **kwargs: メッセージに埋め込む変数
            
        Returns:
            成功メッセージ
        """
        messages = {
            "idea": "✅ ideaフェーズが完了しました！\n次フェーズ: {next_channel}",
            "requirements": "✅ requirementsフェーズが完了しました！\n次フェーズ: {next_channel}",
            "design": "✅ designフェーズが完了しました！\n次フェーズ: {next_channel}",
            "tasks": "✅ tasksフェーズが完了しました！\n🚀 GitHubリポジトリ: {github_url}\n次フェーズ: {next_channel}",
            "session": "📝 Claude Code セッション #{session_num} を開始しました",
            "thread": "🧵 スレッド `{thread_name}` を作成しました"
        }
        
        template = messages.get(action, "✅ 完了しました")
        try:
            return template.format(**kwargs)
        except:
            return template