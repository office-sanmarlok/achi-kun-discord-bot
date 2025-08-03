#!/usr/bin/env python3
"""
ErrorHandlerのユニットテスト
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.error_handler import ErrorHandler, ErrorCategory


class TestErrorHandler:
    """ErrorHandlerのテストクラス"""
    
    def test_format_error_basic(self):
        """基本的なエラーメッセージフォーマットテスト"""
        # 無効な入力エラー
        msg = ErrorHandler.format_error(
            ErrorCategory.INVALID_INPUT, 
            "idea_name"
        )
        assert msg == "❌ 無効なアイデア名です。小文字英字とハイフンのみ使用可能です（例: my-awesome-app）"
        
        # プロジェクトが見つからないエラー
        msg = ErrorHandler.format_error(
            ErrorCategory.PROJECT_NOT_FOUND,
            "default",
            project_name="test-app"
        )
        assert msg == "❌ プロジェクト `test-app` が見つかりません"
    
    def test_format_error_with_variables(self):
        """変数埋め込みのエラーメッセージテスト"""
        # Gitエラー
        msg = ErrorHandler.format_error(
            ErrorCategory.GIT_ERROR,
            "init",
            error="Permission denied"
        )
        assert "❌ Git初期化エラー:" in msg
        assert "Permission denied" in msg
        
        # チャンネルが見つからないエラー
        msg = ErrorHandler.format_error(
            ErrorCategory.CHANNEL_NOT_FOUND,
            "default",
            channel_name="2-requirements"
        )
        assert msg == "❌ #2-requirementsチャンネルが見つかりません"
    
    def test_format_error_fallback(self):
        """エラーメッセージフォールバックテスト"""
        # 存在しないエラータイプ（デフォルトメッセージが使われる）
        msg = ErrorHandler.format_error(
            ErrorCategory.PROJECT_NOT_FOUND,
            "nonexistent"
        )
        assert "❌ プロジェクト" in msg  # デフォルトメッセージ
        assert "<project_name>" in msg  # 不足している変数はプレースホルダーで埋められる
        
        # 例外処理
        with patch.object(ErrorHandler, 'ERROR_MESSAGES', {}):
            msg = ErrorHandler.format_error(ErrorCategory.SYSTEM_ERROR)
            assert msg == "❌ エラーが発生しました"
    
    def test_log_error(self):
        """エラーログ記録テスト"""
        with patch('src.error_handler.logger') as mock_logger:
            error = ValueError("Test error")
            context = {"user": "test_user", "command": "!idea"}
            
            ErrorHandler.log_error(
                ErrorCategory.INVALID_INPUT,
                error,
                context
            )
            
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0][0]
            assert "[invalid_input]" in call_args
            assert "Test error" in call_args
            assert "Context:" in call_args
            assert "test_user" in call_args
    
    def test_handle_discord_error(self):
        """Discord例外処理テスト"""
        # discord.pyモジュールのモック
        with patch.dict('sys.modules', {'discord': Mock()}):
            import sys
            discord_mock = sys.modules['discord']
            
            # Forbiddenエラー
            discord_mock.Forbidden = type('Forbidden', (Exception,), {})
            error = discord_mock.Forbidden()
            msg = ErrorHandler.handle_discord_error(error)
            assert "権限がありません" in msg
            
            # NotFoundエラー
            discord_mock.NotFound = type('NotFound', (Exception,), {})
            error = discord_mock.NotFound()
            msg = ErrorHandler.handle_discord_error(error)
            assert "チャンネルが見つかりません" in msg
            
            # HTTPExceptionエラー
            discord_mock.HTTPException = type('HTTPException', (Exception,), {})
            error = discord_mock.HTTPException("Rate limited")
            msg = ErrorHandler.handle_discord_error(error)
            assert "システムエラー" in msg
            
            # その他のエラー
            error = Exception("Unknown error")
            msg = ErrorHandler.handle_discord_error(error)
            assert "予期しないエラー" in msg
    
    def test_create_loading_message(self):
        """ローディングメッセージ生成テスト"""
        # 各アクションのメッセージ
        assert ErrorHandler.create_loading_message("git") == "`...` Git操作を実行中..."
        assert ErrorHandler.create_loading_message("github") == "`...` GitHubリポジトリを作成中..."
        assert ErrorHandler.create_loading_message("session") == "`...` Claude Codeセッションを開始中..."
        assert ErrorHandler.create_loading_message("thread") == "`...` スレッドを作成中..."
        
        # デフォルトメッセージ
        assert ErrorHandler.create_loading_message("unknown") == "`...` 処理中..."
        assert ErrorHandler.create_loading_message("default") == "`...` 処理中..."
    
    def test_create_success_message(self):
        """成功メッセージ生成テスト"""
        # ideaフェーズ完了
        msg = ErrorHandler.create_success_message(
            "idea",
            next_channel="#2-requirements"
        )
        assert "✅ ideaフェーズが完了しました！" in msg
        assert "#2-requirements" in msg
        
        # tasksフェーズ完了（GitHub URL含む）
        msg = ErrorHandler.create_success_message(
            "tasks",
            github_url="https://github.com/user/repo",
            next_channel="#5-development"
        )
        assert "✅ tasksフェーズが完了しました！" in msg
        assert "https://github.com/user/repo" in msg
        assert "#5-development" in msg
        
        # セッション開始
        msg = ErrorHandler.create_success_message(
            "session",
            session_num=1
        )
        assert "📝 Claude Code セッション #1 を開始しました" in msg
        
        # 変数エラーのハンドリング
        msg = ErrorHandler.create_success_message(
            "idea"  # next_channelが不足
        )
        assert "✅ ideaフェーズが完了しました！" in msg  # テンプレートをそのまま返す
    
    def test_error_category_enum(self):
        """ErrorCategoryエニュメレーションテスト"""
        # 値の確認
        assert ErrorCategory.INVALID_INPUT.value == "invalid_input"
        assert ErrorCategory.PROJECT_NOT_FOUND.value == "project_not_found"
        assert ErrorCategory.GIT_ERROR.value == "git_error"
        
        # すべてのカテゴリがERROR_MESSAGESに定義されているか確認
        for category in ErrorCategory:
            assert category in ErrorHandler.ERROR_MESSAGES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])