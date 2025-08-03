#!/usr/bin/env python3
"""
ロギング設定のユニットテスト
"""

import sys
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logging_config import (
    StructuredFormatter, OperationLogger, setup_logging,
    SessionLifecycleLogger, GitOperationLogger
)


class TestStructuredFormatter:
    """StructuredFormatterのテストクラス"""
    
    def test_basic_formatting(self):
        """基本的なログフォーマットテスト"""
        formatter = StructuredFormatter()
        
        # ログレコードの作成
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function"
        )
        
        # フォーマット実行
        formatted = formatter.format(record)
        log_obj = json.loads(formatted)
        
        # 検証
        assert log_obj["level"] == "INFO"
        assert log_obj["logger"] == "test.module"
        assert log_obj["message"] == "Test message"
        assert log_obj["function"] == "test_function"
        assert log_obj["line"] == 42
        assert "timestamp" in log_obj
    
    def test_context_formatting(self):
        """コンテキスト情報付きフォーマットテスト"""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test", args=(), exc_info=None
        )
        record.context = {"user_id": "123", "action": "create"}
        
        formatted = formatter.format(record)
        log_obj = json.loads(formatted)
        
        assert log_obj["context"]["user_id"] == "123"
        assert log_obj["context"]["action"] == "create"
    
    def test_exception_formatting(self):
        """例外情報のフォーマットテスト"""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="", lineno=0,
                msg="Error occurred", args=(), exc_info=sys.exc_info()
            )
        
        formatted = formatter.format(record)
        log_obj = json.loads(formatted)
        
        assert "exception" in log_obj
        assert "ValueError: Test error" in log_obj["exception"]


class TestOperationLogger:
    """OperationLoggerのテストクラス"""
    
    @pytest.fixture
    def mock_logger(self):
        """モックロガー"""
        return Mock(spec=logging.Logger)
    
    def test_timed_operation_success(self, mock_logger):
        """成功した操作のタイミング記録テスト"""
        op_logger = OperationLogger(mock_logger)
        
        with op_logger.timed_operation("test_op", {"key": "value"}):
            time.sleep(0.01)  # 10ms待機
        
        # 開始と完了の2回呼ばれる
        assert mock_logger.info.call_count == 2
        
        # 開始ログ
        start_call = mock_logger.info.call_args_list[0]
        assert "Starting test_op" in start_call[0][0]
        assert start_call[1]["extra"]["context"]["key"] == "value"
        
        # 完了ログ
        end_call = mock_logger.info.call_args_list[1]
        assert "Completed test_op" in end_call[0][0]
        assert "duration" in end_call[1]["extra"]
        assert end_call[1]["extra"]["duration"] >= 10  # 最低10ms
    
    def test_timed_operation_error(self, mock_logger):
        """失敗した操作のタイミング記録テスト"""
        op_logger = OperationLogger(mock_logger)
        
        with pytest.raises(ValueError):
            with op_logger.timed_operation("test_op"):
                raise ValueError("Test error")
        
        # エラーログが記録される
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Failed test_op" in error_call[0][0]
        assert error_call[1]["exc_info"] is True
    
    def test_log_operation_decorator(self, mock_logger):
        """操作ログデコレーターテスト"""
        op_logger = OperationLogger(mock_logger)
        
        @op_logger.log_operation
        def test_function(x, y):
            return x + y
        
        result = test_function(1, 2)
        
        assert result == 3
        assert mock_logger.info.call_count == 2  # 開始と完了


class TestSetupLogging:
    """setup_logging関数のテストクラス"""
    
    def test_setup_logging_basic(self):
        """基本的なロギング設定テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            loggers = setup_logging(
                log_dir=log_dir,
                log_level="INFO",
                enable_file_logging=True,
                enable_rotation=False
            )
            
            # ロガーが作成されているか確認
            assert "discord_bot" in loggers
            assert "session_manager" in loggers
            assert "project_manager" in loggers
            
            # ログファイルが作成されているか確認
            log_file = log_dir / "claude-discord-bridge.log"
            assert log_file.exists()
            
            # 操作ロガーが設定されているか確認
            assert hasattr(loggers["discord_bot"], "operation")
            assert isinstance(loggers["discord_bot"].operation, OperationLogger)
    
    def test_log_rotation(self):
        """ログローテーション設定テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            loggers = setup_logging(
                log_dir=log_dir,
                enable_rotation=True,
                max_bytes=1024,  # 1KB
                backup_count=3
            )
            
            # ハンドラーがRotatingFileHandlerであることを確認
            root_logger = logging.getLogger()
            file_handlers = [h for h in root_logger.handlers 
                           if isinstance(h, logging.handlers.RotatingFileHandler)]
            assert len(file_handlers) > 0


class TestSessionLifecycleLogger:
    """SessionLifecycleLoggerのテストクラス"""
    
    @pytest.fixture
    def session_logger(self):
        """テスト用セッションロガー"""
        mock_logger = Mock(spec=logging.Logger)
        return SessionLifecycleLogger(mock_logger)
    
    def test_log_session_lifecycle(self, session_logger):
        """セッションライフサイクルのログテスト"""
        # セッション開始
        session_logger.log_session_start(
            session_num=1,
            thread_id="thread123",
            idea_name="test-app",
            stage="idea",
            working_dir="/workspace"
        )
        
        assert 1 in session_logger.sessions
        session_logger.logger.info.assert_called()
        
        # コマンド送信
        session_logger.log_session_command(1, "Test command")
        assert session_logger.logger.info.call_count == 2
        
        # セッション終了
        session_logger.log_session_end(1, "normal")
        assert 1 not in session_logger.sessions
        assert session_logger.logger.info.call_count == 3


class TestGitOperationLogger:
    """GitOperationLoggerのテストクラス"""
    
    @pytest.fixture
    def git_logger(self):
        """テスト用Gitロガー"""
        mock_logger = Mock(spec=logging.Logger)
        return GitOperationLogger(mock_logger)
    
    def test_log_git_success(self, git_logger):
        """Git操作成功のログテスト"""
        git_logger.log_git_operation(
            operation="commit",
            project_path=Path("/projects/test-app"),
            command=["git", "commit", "-m", "Test"],
            success=True,
            output="[main abc123] Test"
        )
        
        git_logger.logger.info.assert_called_once()
        call_args = git_logger.logger.info.call_args
        assert "Git operation commit completed" in call_args[0][0]
        assert call_args[1]["extra"]["context"]["project"] == "test-app"
    
    def test_log_git_failure(self, git_logger):
        """Git操作失敗のログテスト"""
        git_logger.log_git_operation(
            operation="push",
            project_path=Path("/projects/test-app"),
            command=["git", "push"],
            success=False,
            output="fatal: The current branch has no upstream branch"
        )
        
        git_logger.logger.error.assert_called_once()
        call_args = git_logger.logger.error.call_args
        assert "Git operation push failed" in call_args[0][0]
        assert "fatal:" in call_args[1]["extra"]["context"]["output"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])