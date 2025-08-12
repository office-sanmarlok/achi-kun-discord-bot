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
import subprocess
import logging
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()
import requests
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import aiohttp

# パッケージルートの追加（相対インポート対応）
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import discord
    from discord.ext import commands, tasks
except ImportError:
    print("Error: discord.py is not installed. Run: pip install discord.py")
    sys.exit(1)

from config.settings import SettingsManager
from src.attachment_manager import AttachmentManager
from src.session_manager import get_session_manager
from src.project_manager import ProjectManager
from src.processing_animator import get_animator
from src.claude_context_manager import ClaudeContextManager
from src.channel_validator import ChannelValidator
from src.command_manager import CommandManager
from src.prompt_sender import get_prompt_sender

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
        
        # メッセージにファイルパスを追加して返す
        return f"{content}{attachment_str}"

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
    
    def __init__(self, settings_manager: SettingsManager):
        """
        Botインスタンスの初期化
        
        Args:
            settings_manager: 設定管理インスタンス
        """
        self.settings = settings_manager
        self.attachment_manager = AttachmentManager()
        self.message_processor = MessageProcessor()
        self.animator = get_animator()  # アニメーターの初期化
        
        # 新しいマネージャーの追加
        self.project_manager = ProjectManager()
        self.context_manager = ClaudeContextManager()
        self.channel_validator = ChannelValidator()
        self.command_manager = CommandManager(self, settings_manager)
        self.prompt_sender = get_prompt_sender(flask_port=self.settings.get_port('flask'))
        
        # Discord Bot設定
        intents = discord.Intents.default()
        intents.message_content = True  # メッセージ内容へのアクセス権限
        intents.guilds = True  # ギルドイベント（on_thread_create等）へのアクセス権限
        
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
        
        # チャンネル検証
        for guild in self.guilds:
            setup_result = await self.channel_validator.check_bot_setup(guild)
            if not setup_result["is_valid"]:
                report = self.channel_validator.format_setup_report(setup_result)
                print(report)
                logger.warning(f"Bot setup incomplete in guild {guild.name}")
            else:
                print(f"✅ All channels verified in guild: {guild.name}")
        
        # プロジェクトディレクトリの作成
        if not self.project_manager.projects_dir.exists():
            self.project_manager.projects_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created projects directory: {self.project_manager.projects_dir}")
        
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
        メッセージ受信時のメイン処理ハンドラー（スレッドメッセージのみ処理）
        
        処理フロー：
        1. メッセージの事前検証
        2. スレッドチェック
        3. セッション確認・作成
        4. 即座のユーザーフィードバック
        5. 添付ファイル処理
        6. メッセージフォーマット
        7. Claude Codeへの転送
        8. 結果フィードバック
        
        拡張ポイント：
        - メッセージ前処理フィルター
        - 権限チェック
        - レート制限
        - ログ記録
        - 統計収集
        """
        # Bot自身のメッセージの場合、アニメーションを停止する可能性がある
        if message.author == self.user:
            # スレッド内のBot自身のメッセージの場合、アニメーションを停止
            if message.channel.type == discord.ChannelType.public_thread:
                if self.animator.is_animating(message.channel.id):
                    await self.animator.stop_animation(
                        message.channel.id,
                        "応答を受信しました",
                        success=True
                    )
            return
        
        # Discord標準コマンドの処理（!で始まるコマンドを処理）
        await self.process_commands(message)
        
        # Claude Codeに転送すべきかチェック
        if not self.should_forward_to_claude(message):
            return
        
        # スレッド以外は処理しない
        if message.channel.type != discord.ChannelType.public_thread:
            return
        
        # セッション確認
        thread_id = str(message.channel.id)
        session_manager = get_session_manager()
        
        # 既存セッションがあるか確認
        existing_session = session_manager.get_session(thread_id)
        session_num = session_manager.get_or_create_session(thread_id)
        
        # 新規セッションの場合、Claude Codeセッションを開始
        if existing_session is None:  # 今作成された場合
            await message.channel.join()  # スレッドに参加
            await self._start_claude_session(session_num, message.channel.name)
            logger.info(f"Created session {session_num} for existing thread {thread_id}")
        
        try:
            # メッセージ処理パイプライン
            result_text = await self._process_message_pipeline(message, session_num)
            
            # エラーがあった場合のみ表示
            if result_text:
                await message.channel.send(result_text)
                
        except Exception as e:
            error_text = f"❌ 処理エラー: {str(e)[:100]}"
            logger.error(f"Message processing error: {e}", exc_info=True)
            await message.channel.send(error_text)
        
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
        

            
    async def _process_message_pipeline(self, message, session_num: int) -> str:
        """
        メッセージ処理パイプライン
        
        拡張ポイント：
        - 処理ステップの追加
        - 非同期処理の並列化
        - キャッシュ機能
        """
        # アニメーション開始
        animation_message = None
        try:
            # 処理開始時にアニメーションを表示
            animation_message = await self.animator.start_animation(
                message.channel,
                f"メッセージを処理中 (セッション #{session_num})"
            )
            
            # ステップ1: 添付ファイル処理
            attachment_paths = await self._process_attachments(message, session_num)
            
            # ステップ2: メッセージフォーマット
            formatted_message = self.message_processor.format_message_with_attachments(
                message.content, attachment_paths, session_num
            )
            
            # ステップ3: Claude Codeへの転送
            result = await self._forward_to_claude(formatted_message, message, session_num)
            
            # アニメーションは継続（Claude Codeの応答を待つ）
            # 注: アニメーションの停止はClaude Codeからの応答時、またはタイムアウト時に行う
            
            return result
            
        except Exception as e:
            # エラー時もアニメーションを停止
            if animation_message:
                await self.animator.stop_animation(
                    message.channel.id,
                    f"エラー: {str(e)[:50]}",
                    success=False
                )
            raise
        
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
            return None  # 成功時は何も表示しない
        else:
            return f"⚠️ ステータス: {status_code}"
            

    
    def should_forward_to_claude(self, message: discord.Message) -> bool:
        """
        メッセージをClaude Codeに転送すべきか判定
        
        Args:
            message: Discordメッセージオブジェクト
        
        Returns:
            bool: 転送する場合True、しない場合False
        """
        # Bot自身のメッセージは転送しない
        if message.author == self.user:
            return False
        
        # !で始まるメッセージは転送しない（コマンドとして処理）
        if message.content.startswith('!'):
            logger.info(f"Skipping Claude Code forwarding for command message: {message.content[:50]}")
            return False
        
        # それ以外のメッセージは転送する
        return True
    
    async def _start_claude_session(self, session_num: int, thread_name: str, work_dir: str = None):
        """Claude Codeセッションを起動
        
        Args:
            session_num: セッション番号
            thread_name: スレッド名
            work_dir: 作業ディレクトリ（指定しない場合はデフォルト）
        """
        session_name = f"claude-session-{session_num}"
        # 作業ディレクトリの決定（指定がない場合はデフォルト）
        if work_dir is None:
            work_dir = self.settings.get_claude_work_dir()
        claude_options = self.settings.get_claude_options()
        
        # claudeコマンドを構築（ロケール設定を追加）
        claude_cmd = f"export LANG=C.UTF-8 && export LC_ALL=C.UTF-8 && cd {work_dir} && claude {claude_options}".strip()
        cmd = ['tmux', 'new-session', '-d', '-s', session_name, 'bash', '-c', claude_cmd]
        
        try:
            subprocess.run(cmd, check=True)
            logger.info(f"Started Claude Code session {session_num} for thread: {thread_name}")
            print(f"🚀 Started Claude Code session {session_num}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start Claude Code session: {e}")
            print(f"❌ Failed to start Claude Code session {session_num}")
    
    async def _register_session_to_flask(self, session_num: int, thread_id: str, 
                                        idea_name: str, current_stage: str,
                                        working_directory: str, project_path: str = None,
                                        create_project: bool = False):
        """Flask APIにセッション情報を登録"""
        flask_port = self.settings.get_port('flask')
        url = f"http://localhost:{flask_port}/session/register"
        
        payload = {
            'session_num': session_num,
            'thread_id': thread_id,
            'idea_name': idea_name,
            'current_stage': current_stage,
            'working_directory': working_directory
        }
        
        if project_path:
            payload['project_path'] = project_path
        if create_project:
            payload['create_project'] = True
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        logger.info(f"Successfully registered session {session_num} to Flask API")
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to register session to Flask API: {response.status} - {error_text}")
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to Flask API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error registering session: {e}")
    
    
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
    
    async def handle_idea_command(self, ctx, idea_name: str):
        """
        !ideaコマンドの処理
        
        Args:
            ctx: コマンドコンテキスト
            idea_name: アイデア名
        """
        # バリデーション
        if not re.match(r'^[a-z]+(-[a-z]+)*$', idea_name):
            await ctx.send("❌ アイデア名は小文字アルファベットとハイフンのみ使用できます。例: `my-awesome-app`")
            return
        
        if len(idea_name) > 50:
            await ctx.send("❌ アイデア名は50文字以内にしてください。")
            return
        
        # 返信元メッセージの確認
        if not ctx.message.reference:
            await ctx.send("❌ アイデアを含むメッセージに返信する形で実行してください。")
            return
        
        try:
            # 返信元メッセージを取得
            parent_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            
            # スレッド作成
            thread = await parent_message.create_thread(name=idea_name)
            await thread.join()
            
            # セッション管理
            thread_id = str(thread.id)
            session_manager = get_session_manager()
            session_num = session_manager.get_or_create_session(thread_id)
            
            # プロジェクト構造の作成
            try:
                project_path = self.project_manager.create_project_structure(idea_name)
            except FileExistsError:
                await thread.send(f"❌ プロジェクト `{idea_name}` は既に存在します。")
                return
            
            # idea.mdファイルの作成
            idea_content = f"# {idea_name}\n\n## 親メッセージ\n\n{parent_message.content}\n"
            idea_file_path = self.project_manager.create_document(idea_name, "idea", idea_content)
            
            # セッション情報の作成
            working_dir = str(self.project_manager.achi_kun_root)
            session_manager.create_session_info(
                session_num, thread_id, idea_name, "idea", working_dir
            )
            
            # プロジェクト情報の作成
            session_manager.create_project_info(idea_name, project_path)
            
            # Flask APIにセッション情報を登録
            await self._register_session_to_flask(
                session_num=session_num,
                thread_id=thread_id,
                idea_name=idea_name,
                current_stage="idea",
                working_directory=working_dir,
                project_path=str(project_path),
                create_project=True
            )
            session_manager.create_workflow_state(idea_name, ctx.channel.name)
            session_manager.add_thread_to_workflow(idea_name, ctx.channel.name, thread_id)
            
            # Claude Codeセッションを開始
            await self._start_claude_session(session_num, thread.name, working_dir)
            
            # Claude Codeの起動完了を待ってからプロンプトを送信
            await asyncio.sleep(8)  # 3秒から8秒に延長
            
            # プロンプトを生成（thread_infoとsession_numを渡す）
            thread_info = {
                'channel_name': parent_message.channel.name,
                'thread_name': thread.name,
                'thread_id': str(thread.id),
                'author': parent_message.author.name,
                'created_at': parent_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'parent_content': parent_message.content
            }
            
            prompt = self.context_manager.generate_idea_prompt(
                idea_name, 
                parent_message.content,
                thread_info=thread_info,
                session_num=session_num
            )
            
            # Flask経由でプロンプトを送信（プロンプトには既にコンテキストが含まれている）
            success, msg = await self.prompt_sender.send_prompt(
                session_num=session_num,
                prompt=prompt,
                thread_id=str(thread.id)
            )
            
            if not success:
                logger.error(f"Failed to send initial prompt: {msg}")
                await thread.send(f"⚠️ プロンプト送信に失敗しました: {msg}")
            
            # ドキュメントをプロジェクトに追加
            session_manager.add_project_document(idea_name, "idea", idea_file_path)
            
            # 初期メッセージを投稿（online-explorerリンク付き）
            # プロジェクトパスをURLエンコード用に変換
            import urllib.parse
            relative_project_path = str(project_path).replace('/home/ubuntu/', '')
            encoded_path = urllib.parse.quote(relative_project_path)
            explorer_link = f"http://3.15.213.192:3456/?path={encoded_path}"
            
            initial_message = (
                f"🎯 プロジェクト `{idea_name}` を作成しました！\n"
                f"📝 Claude Code セッション #{session_num} を開始しました。\n"
                f"📄 ファイル: `{idea_file_path}`\n"
                f"🔗 作業ディレクトリ: {explorer_link}\n\n"
                f"アイデアの詳細を記載中です..."
            )
            await thread.send(initial_message)
            
            # 元のコマンドメッセージを削除
            try:
                await ctx.message.delete()
            except:
                pass
            
            logger.info(f"!idea command executed: {idea_name} (Thread: {thread_id})")
            
        except discord.NotFound:
            await ctx.send("❌ 返信先のメッセージが見つかりません。")
        except discord.Forbidden:
            await ctx.send("❌ スレッドを作成する権限がありません。")
        except Exception as e:
            logger.error(f"Error in !idea command: {e}", exc_info=True)
            await ctx.send(f"❌ エラーが発生しました: {str(e)[:100]}")

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
    
    @bot.command(name='cc')
    async def cc_command(ctx, thread_name: str = None):
        """メッセージをスレッド化してClaude Codeセッションを開始
        
        使用方法: !cc <thread-name>
        thread-name: 小文字アルファベットとハイフンのみ使用可能
        """
        
        # スレッド名の必須チェック
        if not thread_name:
            await ctx.send("❌ スレッド名を指定してください。使用方法: `!cc <thread-name>`")
            return
        
        # スレッド名のバリデーション（小文字アルファベットとハイフンのみ）
        if not re.match(r'^[a-z]+(-[a-z]+)*$', thread_name):
            await ctx.send("❌ スレッド名は小文字アルファベットとハイフンのみ使用できます。例: `hello-world`")
            return
        
        # スレッド名の長さチェック
        if len(thread_name) > 50:
            await ctx.send("❌ スレッド名は50文字以内にしてください。")
            return
        
        # 返信先メッセージの確認
        if not ctx.message.reference:
            await ctx.send("❌ スレッド化したいメッセージに返信する形で `!cc <thread-name>` を実行してください。")
            return
        
        try:
            # 返信先メッセージを取得
            parent_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            
            # 既にスレッドの場合はエラー
            if parent_message.channel.type == discord.ChannelType.public_thread:
                await ctx.send("❌ 既にスレッド内のメッセージです。")
                return
            
            # スレッド名は引数として既に受け取っているため、そのまま使用
            
            # スレッドを作成
            thread = await parent_message.create_thread(
                name=thread_name
            )
            
            # Botがスレッドに参加
            await thread.join()
            
            # セッション番号を割り当て
            thread_id = str(thread.id)
            session_manager = get_session_manager()
            session_num = session_manager.get_or_create_session(thread_id)
            
            # Claude Codeセッションを開始
            await bot._start_claude_session(session_num, thread.name)
            
            # Flask APIにセッション情報を登録
            await bot._register_session_to_flask(
                session_num=session_num,
                thread_id=thread_id,
                idea_name=thread_name,  # !ccの場合はthread_nameをidea_nameとして使用
                current_stage="general",  # !ccは汎用的なセッションなので"general"とする
                working_directory=bot.settings.get_claude_work_dir()
            )
            
            # Claude Codeの起動完了を待ってから初期コンテキストを送信
            await asyncio.sleep(8)  # 3秒から8秒に延長
            
            # テンプレートローダーを使ってコンテキストとプロンプトを生成
            from src.claude_context_manager import PromptTemplateLoader
            template_loader = PromptTemplateLoader()
            
            # cc.mdとcontext_base.mdを結合
            template_content = template_loader.load_and_combine_templates("cc.md")
            
            if template_content:
                # 変数を準備
                variables = {
                    'channel_name': parent_message.channel.name,
                    'thread_name': thread.name,
                    'thread_id': str(thread.id),
                    'session_num': session_num,
                    'author': parent_message.author.name,
                    'created_at': parent_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'parent_content': parent_message.content
                }
                
                # テンプレート変数を置換
                prompt = template_loader.render_template(template_content, variables)
            else:
                # フォールバック（テンプレートが見つからない場合）
                prompt = f"""=== Discord スレッド情報 ===
チャンネル名: {parent_message.channel.name}
スレッド名: {thread.name}
スレッドID: {thread.id}
セッション番号: {session_num}

【重要】このセッションはDiscordのスレッド専用です。
メッセージ送信は: dp {session_num} "メッセージ"

=== 親メッセージ ===
作成者: {parent_message.author.name}
時刻: {parent_message.created_at.strftime('%Y-%m-%d %H:%M:%S')}
内容:
{parent_message.content}
===================

このスレッドでメッセージを送信すると、Claude Codeに転送されます。"""
            
            success, msg = await bot.prompt_sender.send_prompt(
                session_num=session_num,
                prompt=prompt,
                thread_id=str(thread.id)
            )
            
            if not success:
                logger.error(f"Failed to send initial context: {msg}")
            
            # スレッド内に最初の返信を投稿
            initial_message = (
                f"🧵 スレッドを作成しました！\n"
                f"📝 Claude Code セッション #{session_num} を開始しました。\n\n"
                f"このスレッドでメッセージを送信すると、Claude Codeに転送されます。"
            )
            await thread.send(initial_message)
            
            # 元のチャンネルでの確認メッセージは削除（スレッド内で完結させる）
            try:
                await ctx.message.delete()
            except:
                pass  # 削除権限がない場合は無視
            
            logger.info(f"Thread created via !cc command: {thread_name} (ID: {thread.id})")
            
        except discord.NotFound:
            await ctx.send("❌ 返信先のメッセージが見つかりません。")
        except discord.Forbidden:
            await ctx.send("❌ スレッドを作成する権限がありません。")
        except Exception as e:
            logger.error(f"Error in /thread command: {e}", exc_info=True)
            await ctx.send(f"❌ エラーが発生しました: {str(e)[:100]}")
    
    @bot.command(name='idea')
    async def idea_command(ctx, idea_name: str = None):
        """アイデアからプロジェクトを開始するコマンド
        
        使用方法: !idea <idea-name>
        ※ アイデアを含むメッセージに返信する形で実行
        """
        if not idea_name:
            await ctx.send("❌ アイデア名を指定してください。使用方法: `!idea <idea-name>`")
            return
        
        await bot.handle_idea_command(ctx, idea_name)
    
    @bot.command(name='complete')
    async def complete_command(ctx):
        """現在のフェーズを完了して次のフェーズへ進むコマンド
        
        使用方法: !complete
        ※ #1-idea, #2-requirements, #3-design, #4-tasksのスレッド内で実行
        """
        await bot.command_manager.process_complete_command(ctx)
    
    @bot.command(name='stop')
    async def stop_command(ctx, target: str = None):
        """tmuxセッションを終了するコマンド
        
        使用方法:
        - !stop             : 現在のスレッドのセッションを終了
        - !stop <番号>      : 指定したセッション番号を終了
        - !stop all         : 全てのセッションを終了（管理者のみ）
        """
        from src.tmux_manager import TmuxManager
        from src.session_manager import get_session_manager
        
        tmux_manager = TmuxManager()
        session_manager = get_session_manager()
        
        # スレッド内での実行チェック
        if target is None and ctx.channel.type != discord.ChannelType.public_thread:
            await ctx.send("❌ このチャンネルでは`!stop`を使用できません。スレッド内で実行するか、セッション番号を指定してください。")
            return
        
        loading_msg = await ctx.send("`...` セッション終了処理中...")
        
        try:
            if target is None:
                # 現在のスレッドのセッションを終了
                thread_id = str(ctx.channel.id)
                session_num = session_manager.get_session(thread_id)
                
                if session_num is None:
                    await loading_msg.edit(content="❌ このスレッドにはアクティブなセッションがありません")
                    return
                
                # tmuxセッションを終了
                if tmux_manager.kill_claude_session(session_num):
                    # SessionManagerからも削除
                    session_manager.remove_session(thread_id)
                    await loading_msg.edit(content=f"✅ セッション {session_num} を終了しました")
                else:
                    await loading_msg.edit(content=f"⚠️ セッション {session_num} の終了に失敗しました")
                    
            elif target.lower() == "all":
                # 管理者権限チェック（必要に応じて）
                # if not ctx.author.guild_permissions.administrator:
                #     await loading_msg.edit(content="❌ 全セッション終了には管理者権限が必要です")
                #     return
                
                # 全セッションを終了
                if tmux_manager.kill_all_claude_sessions():
                    # SessionManagerもクリア
                    session_manager.clear_all_sessions()
                    await loading_msg.edit(content="✅ 全てのClaude Codeセッションを終了しました")
                else:
                    await loading_msg.edit(content="⚠️ セッションの終了中にエラーが発生しました")
                    
            else:
                # セッション番号を指定して終了
                try:
                    session_num = int(target)
                except ValueError:
                    await loading_msg.edit(content="❌ 無効なセッション番号です。数字を指定してください。")
                    return
                
                # セッションの存在確認
                if not tmux_manager.is_claude_session_exists(session_num):
                    await loading_msg.edit(content=f"❌ セッション {session_num} は存在しません")
                    return
                
                # tmuxセッションを終了
                if tmux_manager.kill_claude_session(session_num):
                    # SessionManagerから対応するthread_idを探して削除
                    thread_id = session_manager.get_thread_by_session(session_num)
                    if thread_id:
                        session_manager.remove_session(thread_id)
                    await loading_msg.edit(content=f"✅ セッション {session_num} を終了しました")
                else:
                    await loading_msg.edit(content=f"⚠️ セッション {session_num} の終了に失敗しました")
                    
        except Exception as e:
            logger.error(f"Error in stop command: {e}")
            await loading_msg.edit(content=f"❌ エラーが発生しました: {str(e)[:100]}")

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