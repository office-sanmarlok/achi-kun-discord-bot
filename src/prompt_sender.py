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
    
    async def send_initial_context_and_prompt(self,
                                            session_num: int,
                                            thread_id: str,
                                            thread_name: str,
                                            initial_context: Dict[str, Any],
                                            prompt: str) -> Tuple[bool, str]:
        """
        初期コンテキストとプロンプトを組み合わせて送信
        
        Args:
            session_num: セッション番号
            thread_id: DiscordスレッドID
            thread_name: スレッド名
            initial_context: 初期コンテキスト情報
            prompt: 実行したいプロンプト
            
        Returns:
            (成功フラグ, メッセージ)のタプル
        """
        # 初期コンテキストを構築
        context_lines = [
            "=== Discord スレッド情報 ===",
            f"チャンネル名: {initial_context.get('channel_name', 'Unknown')}",
            f"スレッド名: {thread_name}",
            f"スレッドID: {thread_id}",
            f"セッション番号: {session_num}",
            "",
            "【重要】このセッションはDiscordのスレッド専用です。",
            f"メッセージ送信は: dp {session_num} \"メッセージ\"",
            ""
        ]
        
        # 親メッセージがある場合は追加
        if 'parent_message' in initial_context:
            parent = initial_context['parent_message']
            context_lines.extend([
                "=== 親メッセージ ===",
                f"作成者: {parent.get('author', 'Unknown')}",
                f"時刻: {parent.get('created_at', 'Unknown')}",
                f"内容:",
                parent.get('content', ''),
                "==================="
            ])
        
        # プロンプトと結合
        full_message = "\n".join(context_lines) + "\n\n" + prompt
        
        # 送信
        return await self.send_prompt(
            session_num=session_num,
            prompt=full_message,
            thread_id=thread_id
        )
    
    def build_initial_context(self,
                            session_num: int,
                            thread_id: str,
                            thread_name: str,
                            initial_context: Dict[str, Any],
                            template_name: str = "cc.md",
                            use_base_template: bool = True) -> str:
        """
        初期コンテキストメッセージを構築（送信はしない）
        
        Args:
            session_num: セッション番号
            thread_id: DiscordスレッドID
            thread_name: スレッド名
            initial_context: 初期コンテキスト情報
            template_name: 使用するテンプレートファイル名
            
        Returns:
            構築されたコンテキストメッセージ
        """
        # テンプレートファイルを読み込みを試みる
        template_content = None
        
        if use_base_template:
            # context_base.mdを読み込む
            base_path = self.prompts_dir / "context_base.md"
            if base_path.exists():
                try:
                    with open(base_path, 'r', encoding='utf-8') as f:
                        base_content = f.read()
                        template_content = base_content
                except Exception as e:
                    logger.warning(f"Failed to load base template: {e}")
            
            # コマンドテンプレートを読み込む
            template_path = self.prompts_dir / template_name
            if template_path.exists():
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        command_content = f.read()
                        if template_content:
                            template_content = template_content + "\n\n" + command_content
                        else:
                            template_content = command_content
                except Exception as e:
                    logger.warning(f"Failed to load command template: {e}")
        else:
            # コマンドテンプレートのみ読み込む
            template_path = self.prompts_dir / template_name
            if template_path.exists():
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                except Exception as e:
                    logger.warning(f"Failed to load template: {e}")
        
        if template_content:
                    
                # 変数を準備
                parent = initial_context.get('parent_message', {})
                variables = {
                    'channel_name': initial_context.get('channel_name', 'Unknown'),
                    'thread_name': thread_name,
                    'thread_id': thread_id,
                    'session_num': session_num,
                    'author': parent.get('author', 'Unknown'),
                    'created_at': parent.get('created_at', 'Unknown'),
                    'parent_content': parent.get('content', '')
                }
                
                # テンプレート変数を置換
                template = Template(template_content)
                return template.safe_substitute(variables)
        
        # テンプレートが存在しない場合はデフォルトを使用
        context_lines = [
            "=== Discord スレッド情報 ===",
            f"チャンネル名: {initial_context.get('channel_name', 'Unknown')}",
            f"スレッド名: {thread_name}",
            f"スレッドID: {thread_id}",
            f"セッション番号: {session_num}",
            "",
            "【重要】このセッションはDiscordのスレッド専用です。",
            f"メッセージ送信は: dp {session_num} \"メッセージ\"",
            ""
        ]
        
        # 親メッセージがある場合は追加
        if 'parent_message' in initial_context:
            parent = initial_context['parent_message']
            context_lines.extend([
                "=== 親メッセージ ===",
                f"作成者: {parent.get('author', 'Unknown')}",
                f"時刻: {parent.get('created_at', 'Unknown')}",
                f"内容:",
                parent.get('content', ''),
                "==================="
            ])
        
        return "\n".join(context_lines)
    
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