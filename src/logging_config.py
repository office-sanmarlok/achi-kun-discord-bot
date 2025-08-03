#!/usr/bin/env python3
"""
ロギング設定 - 構造化ログとモニタリング

このモジュールは以下の責務を持つ：
1. 構造化ログの設定
2. ログローテーションの設定
3. 操作タイミングの記録
4. パフォーマンスモニタリング
"""

import logging
import logging.handlers
import json
import time
import functools
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター（JSON形式）"""
    
    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをJSON形式にフォーマット"""
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 追加のコンテキスト情報
        if hasattr(record, 'context'):
            log_obj['context'] = record.context
            
        # エラーの場合はスタックトレースを含める
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
            
        # 実行時間情報
        if hasattr(record, 'duration'):
            log_obj['duration_ms'] = record.duration
            
        return json.dumps(log_obj, ensure_ascii=False)


class OperationLogger:
    """操作ログとタイミング記録のヘルパークラス"""
    
    def __init__(self, logger: logging.Logger):
        """
        初期化
        
        Args:
            logger: 使用するロガー
        """
        self.logger = logger
    
    @contextmanager
    def timed_operation(self, operation_name: str, context: Optional[Dict[str, Any]] = None):
        """
        操作の実行時間を計測してログに記録
        
        Args:
            operation_name: 操作名
            context: 追加のコンテキスト情報
            
        使用例:
            with operation_logger.timed_operation("git_commit", {"repo": "test-app"}):
                # Git操作を実行
        """
        start_time = time.time()
        
        # 開始ログ
        self.logger.info(
            f"Starting {operation_name}",
            extra={"context": context or {}}
        )
        
        try:
            yield
            
            # 成功ログ（実行時間付き）
            duration = (time.time() - start_time) * 1000  # ミリ秒
            self.logger.info(
                f"Completed {operation_name}",
                extra={
                    "context": context or {},
                    "duration": duration
                }
            )
            
        except Exception as e:
            # エラーログ（実行時間付き）
            duration = (time.time() - start_time) * 1000
            self.logger.error(
                f"Failed {operation_name}: {str(e)}",
                extra={
                    "context": context or {},
                    "duration": duration
                },
                exc_info=True
            )
            raise
    
    def log_operation(self, func: Callable) -> Callable:
        """
        関数の実行をログに記録するデコレーター
        
        使用例:
            @operation_logger.log_operation
            def create_project(name: str):
                # プロジェクト作成処理
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            context = {"args": str(args), "kwargs": str(kwargs)}
            
            with self.timed_operation(operation_name, context):
                return func(*args, **kwargs)
        
        return wrapper


def setup_logging(log_dir: Optional[Path] = None, 
                 log_level: str = "INFO",
                 enable_file_logging: bool = True,
                 enable_rotation: bool = True,
                 max_bytes: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5) -> Dict[str, logging.Logger]:
    """
    アプリケーション全体のロギングを設定
    
    Args:
        log_dir: ログファイルの保存ディレクトリ
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR）
        enable_file_logging: ファイルへのログ出力を有効化
        enable_rotation: ログローテーションを有効化
        max_bytes: ローテーションサイズ（バイト）
        backup_count: 保持するバックアップファイル数
        
    Returns:
        設定されたロガーの辞書
    """
    # ログディレクトリの設定
    if log_dir is None:
        log_dir = Path.home() / ".claude-discord-bridge" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 既存のハンドラーをクリア
    root_logger.handlers.clear()
    
    # コンソールハンドラー（人間が読める形式）
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラー（構造化ログ）
    if enable_file_logging:
        if enable_rotation:
            # ローテーション付きファイルハンドラー
            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / "claude-discord-bridge.log",
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
        else:
            # 通常のファイルハンドラー
            file_handler = logging.FileHandler(
                log_dir / "claude-discord-bridge.log",
                encoding='utf-8'
            )
        
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    # 各モジュール用のロガーを作成
    loggers = {
        "discord_bot": logging.getLogger("src.discord_bot"),
        "session_manager": logging.getLogger("src.session_manager"),
        "project_manager": logging.getLogger("src.project_manager"),
        "command_manager": logging.getLogger("src.command_manager"),
        "claude_context": logging.getLogger("src.claude_context_manager"),
        "channel_validator": logging.getLogger("src.channel_validator"),
        "attachment_manager": logging.getLogger("src.attachment_manager"),
        "error_handler": logging.getLogger("src.error_handler")
    }
    
    # 操作ロガーの作成
    for name, logger in loggers.items():
        logger.operation = OperationLogger(logger)
    
    return loggers


class SessionLifecycleLogger:
    """Claude Codeセッションのライフサイクルをログに記録"""
    
    def __init__(self, logger: logging.Logger):
        """
        初期化
        
        Args:
            logger: 使用するロガー
        """
        self.logger = logger
        self.sessions: Dict[int, Dict[str, Any]] = {}
    
    def log_session_start(self, session_num: int, thread_id: str, 
                         idea_name: str, stage: str, working_dir: str):
        """セッション開始をログに記録"""
        session_info = {
            "thread_id": thread_id,
            "idea_name": idea_name,
            "stage": stage,
            "working_dir": working_dir,
            "start_time": datetime.utcnow().isoformat()
        }
        
        self.sessions[session_num] = session_info
        
        self.logger.info(
            f"Claude Code session {session_num} started",
            extra={"context": session_info}
        )
    
    def log_session_command(self, session_num: int, command: str):
        """セッションへのコマンド送信をログに記録"""
        if session_num in self.sessions:
            self.logger.info(
                f"Command sent to session {session_num}",
                extra={
                    "context": {
                        "session_num": session_num,
                        "command": command[:100],  # 最初の100文字のみ
                        "idea_name": self.sessions[session_num]["idea_name"]
                    }
                }
            )
    
    def log_session_end(self, session_num: int, reason: str = "normal"):
        """セッション終了をログに記録"""
        if session_num in self.sessions:
            session_info = self.sessions[session_num]
            start_time = datetime.fromisoformat(session_info["start_time"])
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                f"Claude Code session {session_num} ended",
                extra={
                    "context": {
                        "session_num": session_num,
                        "idea_name": session_info["idea_name"],
                        "stage": session_info["stage"],
                        "duration_seconds": duration,
                        "reason": reason
                    }
                }
            )
            
            del self.sessions[session_num]


class GitOperationLogger:
    """Git操作の詳細ログ記録"""
    
    def __init__(self, logger: logging.Logger):
        """
        初期化
        
        Args:
            logger: 使用するロガー
        """
        self.logger = logger
    
    def log_git_operation(self, operation: str, project_path: Path, 
                         command: list, success: bool, output: str):
        """Git操作をログに記録"""
        context = {
            "operation": operation,
            "project": project_path.name,
            "command": " ".join(command),
            "success": success,
            "output_length": len(output)
        }
        
        if success:
            self.logger.info(
                f"Git operation {operation} completed",
                extra={"context": context}
            )
        else:
            context["output"] = output[:500]  # エラー時は出力の一部を含める
            self.logger.error(
                f"Git operation {operation} failed",
                extra={"context": context}
            )


# グローバル設定
_loggers: Optional[Dict[str, logging.Logger]] = None

def get_loggers() -> Dict[str, logging.Logger]:
    """設定済みのロガーを取得（シングルトン）"""
    global _loggers
    if _loggers is None:
        _loggers = setup_logging()
    return _loggers