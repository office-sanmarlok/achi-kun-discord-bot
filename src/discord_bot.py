#!/usr/bin/env python3
"""
Discord Bot実装 - Claude-Discord Bridgeのコア機能

このモジュールは以下の責任を持つ：
1. Discordメッセージの受信・処理
2. 画像添付ファイルの管理
3. Claude Codeへのメッセージ転送
4. ユーザーフィードバックの管理
5. 定期的なメンテナンス処理

拡張性のポイント：
- メッセージフォーマット戦略の追加
- 新しい添付ファイル形式のサポート
- カスタムコマンドの追加
- 通知方法の拡張
- セッション管理の強化
"""

import os
import sys
import json
import asyncio
import logging
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any

# パッケージルートの追加（相対インポート対応）
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import discord
    from discord.ext import commands, tasks
except ImportError:
    print("Error: discord.py is not installed. Run: pip install discord.py")
    sys.exit(1)

from config.settings import SettingsManager
from attachment_manager import AttachmentManager

# ログ設定（本番環境では外部設定ファイルから読み込み可能）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MessageProcessor:
    """
    メッセージ処理の戦略パターン実装
    
    将来の拡張：
    - 異なるメッセージ形式への対応
    - コンテンツフィルタリング
    - メッセージ変換処理
    """
    
    @staticmethod
    def format_message_with_attachments(content: str, attachment_paths: List[str], session_num: int) -> str:
        """
        メッセージと添付ファイルパスを適切にフォーマット
        
        拡張ポイント：
        - 添付ファイル形式の多様化（動画、音声、ドキュメント等）
        - メッセージテンプレートのカスタマイズ
        - 多言語対応
        
        Args:
            content: 元のメッセージ内容
            attachment_paths: 添付ファイルのパスリスト
            session_num: セッション番号
        
        Returns:
            str: フォーマットされたメッセージ
        """
        # 添付ファイルパス文字列の生成
        attachment_str = ""
        if attachment_paths:
            attachment_parts = [f"[添付画像のファイルパス: {path}]" for path in attachment_paths]
            attachment_str = " " + " ".join(attachment_parts)
        
        # メッセージタイプによる分岐処理
        if content.startswith('/'):
            # スラッシュコマンド形式（直接Claude Codeコマンド実行）
            return f"{content}{attachment_str} session={session_num}"
        else:
            # 通常メッセージ形式（Claude Codeへの通知）
            return f"Discordからの通知: {content}{attachment_str} session={session_num}"

class ClaudeCLIBot(commands.Bot):
    """
    Claude CLI統合Discord Bot
    
    アーキテクチャ特徴：
    - 非同期処理による高いレスポンス性
    - モジュラー設計による拡張性
    - 堅牢なエラーハンドリング
    - 自動リソース管理
    
    拡張可能要素：
    - カスタムコマンドの追加
    - 権限管理システム
    - ユーザーセッション管理
    - 統計・分析機能
    - Webhook統合
    """
    
    # 設定可能な定数（将来は設定ファイル化）
    CLEANUP_INTERVAL_HOURS = 6
    REQUEST_TIMEOUT_SECONDS = 5
    LOADING_MESSAGE = "`...`"
    SUCCESS_MESSAGE = "> メッセージを送信完了しました"
    
    def __init__(self, settings_manager: SettingsManager):
        """
        Botインスタンスの初期化
        
        Args:
            settings_manager: 設定管理インスタンス
        """
        self.settings = settings_manager
        self.attachment_manager = AttachmentManager()
        self.message_processor = MessageProcessor()
        
        # Discord Bot設定
        intents = discord.Intents.default()
        intents.message_content = True  # メッセージ内容へのアクセス権限
        
        super().__init__(command_prefix='!', intents=intents)
        
    async def on_ready(self):
        """
        Bot準備完了時の初期化処理
        
        拡張ポイント：
        - データベース接続初期化
        - 外部API接続確認
        - 統計情報の初期化
        - 定期処理タスクの開始
        """
        logger.info(f'{self.user} has connected to Discord!')
        print(f'✅ Discord bot is ready as {self.user}')
        
        # 初回システムクリーンアップ
        await self._perform_initial_cleanup()
        
        # 定期メンテナンス処理の開始
        await self._start_maintenance_tasks()
        
    async def _perform_initial_cleanup(self):
        """
        Bot起動時の初回クリーンアップ処理
        
        拡張ポイント：
        - 古いセッションデータの削除
        - ログファイルのローテーション
        - キャッシュの初期化
        """
        cleanup_count = self.attachment_manager.cleanup_old_files()
        if cleanup_count > 0:
            print(f'🧹 Cleaned up {cleanup_count} old attachment files')
            
    async def _start_maintenance_tasks(self):
        """
        定期メンテナンスタスクの開始
        
        拡張ポイント：
        - データベースメンテナンス
        - 統計情報の集計
        - 外部API状態確認
        """
        if not self.cleanup_task.is_running():
            self.cleanup_task.start()
            print(f'⏰ Attachment cleanup task started (runs every {self.CLEANUP_INTERVAL_HOURS} hours)')
        
    async def on_message(self, message):
        """
        メッセージ受信時のメイン処理ハンドラー
        
        処理フロー：
        1. メッセージの事前検証
        2. セッション確認
        3. 即座のユーザーフィードバック
        4. 添付ファイル処理
        5. メッセージフォーマット
        6. Claude Codeへの転送
        7. 結果フィードバック
        
        拡張ポイント：
        - メッセージ前処理フィルター
        - 権限チェック
        - レート制限
        - ログ記録
        - 統計収集
        """
        # 基本的な検証
        if not await self._validate_message(message):
            return
        
        # セッション確認
        session_num = self.settings.channel_to_session(str(message.channel.id))
        if session_num is None:
            return
        
        # ユーザーフィードバック（即座のローディング表示）
        loading_msg = await self._send_loading_feedback(message.channel)
        if not loading_msg:
            return
        
        try:
            # メッセージ処理パイプライン
            result_text = await self._process_message_pipeline(message, session_num)
            
        except Exception as e:
            result_text = f"❌ 処理エラー: {str(e)[:100]}"
            logger.error(f"Message processing error: {e}", exc_info=True)
        
        # 最終結果の表示
        await self._update_feedback(loading_msg, result_text)
        
    async def _validate_message(self, message) -> bool:
        """
        メッセージの基本検証
        
        拡張ポイント：
        - スパム検出
        - 権限確認
        - ブラックリストチェック
        """
        # Bot自身のメッセージは無視
        if message.author == self.user:
            return False
        
        # Discord標準コマンドの処理
        await self.process_commands(message)
        
        return True
        
    async def _send_loading_feedback(self, channel) -> Optional[discord.Message]:
        """
        ローディングフィードバックの送信
        
        拡張ポイント：
        - カスタムローディングメッセージ
        - アニメーション表示
        - プログレスバー
        """
        try:
            return await channel.send(self.LOADING_MESSAGE)
        except Exception as e:
            logger.error(f'フィードバック送信エラー: {e}')
            return None
            
    async def _process_message_pipeline(self, message, session_num: int) -> str:
        """
        メッセージ処理パイプライン
        
        拡張ポイント：
        - 処理ステップの追加
        - 非同期処理の並列化
        - キャッシュ機能
        """
        # ステップ1: 添付ファイル処理
        attachment_paths = await self._process_attachments(message, session_num)
        
        # ステップ2: メッセージフォーマット
        formatted_message = self.message_processor.format_message_with_attachments(
            message.content, attachment_paths, session_num
        )
        
        # ステップ3: Claude Codeへの転送
        return await self._forward_to_claude(formatted_message, message, session_num)
        
    async def _process_attachments(self, message, session_num: int) -> List[str]:
        """
        添付ファイルの処理
        
        拡張ポイント：
        - 新しいファイル形式のサポート
        - ファイル変換処理
        - ウイルススキャン
        """
        attachment_paths = []
        if message.attachments:
            try:
                attachment_paths = await self.attachment_manager.process_attachments(message.attachments)
                if attachment_paths:
                    print(f'📎 Processed {len(attachment_paths)} attachment(s) for session {session_num}')
            except Exception as e:
                logger.error(f'Attachment processing error: {e}')
        
        return attachment_paths
        
    async def _forward_to_claude(self, formatted_message: str, original_message, session_num: int) -> str:
        """
        Claude Codeへのメッセージ転送
        
        拡張ポイント：
        - 複数転送先のサポート
        - 転送失敗時のリトライ
        - 負荷分散
        """
        try:
            payload = {
                'message': formatted_message,
                'channel_id': str(original_message.channel.id),
                'session': session_num,
                'user_id': str(original_message.author.id),
                'username': str(original_message.author)
            }
            
            flask_port = self.settings.get_port('flask')
            response = requests.post(
                f'http://localhost:{flask_port}/discord-message',
                json=payload,
                timeout=self.REQUEST_TIMEOUT_SECONDS
            )
            
            return self._format_response_status(response.status_code)
            
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Flask app. Is it running?")
            return "❌ エラー: Flask appに接続できません"
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            return f"❌ エラー: {str(e)[:100]}"
            
    def _format_response_status(self, status_code: int) -> str:
        """
        レスポンスステータスのフォーマット
        
        拡張ポイント：
        - 詳細ステータスメッセージ
        - 多言語対応
        - カスタムメッセージ
        """
        if status_code == 200:
            return self.SUCCESS_MESSAGE
        else:
            return f"⚠️ ステータス: {status_code}"
            
    async def _update_feedback(self, loading_msg: discord.Message, result_text: str):
        """
        フィードバックメッセージの更新
        
        拡張ポイント：
        - リッチメッセージ表示
        - 進捗状況の表示
        - インタラクティブ要素
        """
        try:
            await loading_msg.edit(content=result_text)
        except Exception as e:
            logger.error(f'メッセージ更新失敗: {e}')
    
    @tasks.loop(hours=CLEANUP_INTERVAL_HOURS)
    async def cleanup_task(self):
        """
        定期クリーンアップタスク
        
        拡張ポイント：
        - データベースクリーンアップ
        - ログファイル管理
        - 統計情報の集計
        - システムヘルスチェック
        """
        try:
            cleanup_count = self.attachment_manager.cleanup_old_files()
            if cleanup_count > 0:
                logger.info(f'Automatic cleanup: {cleanup_count} files deleted')
        except Exception as e:
            logger.error(f'Error in cleanup task: {e}')
    
    @cleanup_task.before_loop
    async def before_cleanup_task(self):
        """クリーンアップタスク開始前の準備処理"""
        await self.wait_until_ready()

def create_bot_commands(bot: ClaudeCLIBot, settings: SettingsManager):
    """
    Botコマンドの登録
    
    拡張ポイント：
    - 新しいコマンドの追加
    - 権限ベースのコマンド
    - 動的コマンド登録
    """
    
    @bot.command(name='status')
    async def status_command(ctx):
        """Bot状態確認コマンド"""
        sessions = settings.list_sessions()
        embed = discord.Embed(
            title="Claude CLI Bot Status",
            description="✅ Bot is running",
            color=discord.Color.green()
        )
        
        session_list = "\n".join([f"Session {num}: <#{ch_id}>" for num, ch_id in sessions])
        embed.add_field(name="Active Sessions", value=session_list or "No sessions configured", inline=False)
        
        await ctx.send(embed=embed)
    
    @bot.command(name='sessions')
    async def sessions_command(ctx):
        """設定済みセッション一覧表示コマンド"""
        sessions = settings.list_sessions()
        if not sessions:
            await ctx.send("No sessions configured.")
            return
        
        lines = ["**Configured Sessions:**"]
        for num, channel_id in sessions:
            lines.append(f"Session {num}: <#{channel_id}>")
        
        await ctx.send("\n".join(lines))

def run_bot():
    """
    Discord Botのメイン実行関数
    
    拡張ポイント：
    - 複数Bot管理
    - シャーディング対応
    - 高可用性設定
    """
    settings = SettingsManager()
    
    # トークン確認
    token = settings.get_token()
    if not token or token == 'your_token_here':
        print("❌ Discord bot token not configured!")
        print("Run './install.sh' to set up the token.")
        sys.exit(1)
    
    # Botインスタンス作成
    bot = ClaudeCLIBot(settings)
    
    # コマンド登録
    create_bot_commands(bot, settings)
    
    # Bot実行
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Failed to login. Check your Discord bot token.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        logger.error(f"Bot execution error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_bot()