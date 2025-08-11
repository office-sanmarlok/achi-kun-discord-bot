#!/usr/bin/env python3
"""
Prompt Sender - Claude Codeへのプロンプト送信を統一管理

このモジュールは以下の機能を提供：
1. Flask API経由でのプロンプト送信
2. 初期コンテキストとプロンプトの組み合わせ送信
3. セッション情報の自動付与
4. エラーハンドリングとリトライ
"""

import logging
import requests
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)


class PromptSender:
    """Claude Codeへのプロンプト送信を統一管理するクラス"""
    
    def __init__(self, flask_port: int = 5001, timeout: int = 30):
        """
        初期化
        
        Args:
            flask_port: Flask APIのポート番号
            timeout: リクエストタイムアウト（秒）
        """
        self.flask_port = flask_port
        self.timeout = timeout
        self.base_url = f"http://localhost:{flask_port}"
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
    
    async def send_prompt(self, 
                         session_num: int,
                         prompt: str,
                         thread_id: str,
                         user_id: str = "system",
                         username: str = "System") -> Tuple[bool, str]:
        """
        プロンプトをClaude Codeセッションに送信
        
        Args:
            session_num: セッション番号
            prompt: 送信するプロンプト
            thread_id: DiscordスレッドID
            user_id: ユーザーID（デフォルト: "system"）
            username: ユーザー名（デフォルト: "System"）
            
        Returns:
            (成功フラグ, メッセージ)のタプル
        """
        try:
            payload = {
                'message': prompt,
                'channel_id': str(thread_id),
                'session': session_num,
                'user_id': str(user_id),
                'username': str(username)
            }
            
            response = requests.post(
                f"{self.base_url}/discord-message",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent prompt to session {session_num}")
                return True, "✅ プロンプトを送信しました"
            else:
                error_msg = f"Failed to send prompt: HTTP {response.status_code}"
                logger.error(error_msg)
                return False, f"❌ エラー: {error_msg}"
                
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Flask API"
            logger.error(error_msg)
            return False, "❌ エラー: Flask APIに接続できません"
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.timeout} seconds"
            logger.error(error_msg)
            return False, "❌ エラー: リクエストがタイムアウトしました"
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, f"❌ エラー: {str(e)[:100]}"
    
    
    
    def check_connection(self) -> bool:
        """
        Flask APIへの接続を確認
        
        Returns:
            接続可能な場合True
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False


# グローバルインスタンス（シングルトン）
_prompt_sender = None

def get_prompt_sender(flask_port: int = 5001) -> PromptSender:
    """
    PromptSenderのシングルトンインスタンスを取得
    
    Args:
        flask_port: Flask APIのポート番号
        
    Returns:
        PromptSender インスタンス
    """
    global _prompt_sender
    if _prompt_sender is None:
        _prompt_sender = PromptSender(flask_port=flask_port)
    return _prompt_sender