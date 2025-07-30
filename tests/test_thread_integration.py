#!/usr/bin/env python3
"""
スレッド機能の統合テスト
Discord.pyのモックを使用してエンドツーエンドの動作を検証
"""

import unittest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import sys
from pathlib import Path
from datetime import datetime

# テスト対象のモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import SettingsManager
from src.discord_bot import ClaudeCLIBot


class TestThreadIntegration(unittest.TestCase):
    """スレッド機能の統合テストクラス"""
    
    def setUp(self):
        """各テストの前に実行される"""
        # 設定マネージャーのモック
        self.settings = Mock(spec=SettingsManager)
        self.settings.is_channel_registered = Mock(return_value=True)
        self.settings.add_thread_session = Mock(return_value=1)
        self.settings.thread_to_session = Mock(return_value=None)
        self.settings._load_settings = Mock(return_value={
            'thread_sessions': {},
            'registered_channels': ['123456789012345678'],
            'ports': {'flask': 5001}
        })
        
        # Discord.pyのモック
        self.mock_discord = MagicMock()
        
        # Botインスタンスの作成（実際のIntentsは必要）
        # ただし、実際の接続は行わない
        import discord
        intents = discord.Intents.default()
        intents.guilds = True
        intents.message_content = True
        
        # HTTPClientのモックを作成
        with patch('discord.ext.commands.Bot.__init__', return_value=None):
            self.bot = ClaudeCLIBot.__new__(ClaudeCLIBot)
            self.bot.settings = self.settings
            self.bot.attachment_manager = Mock()
            self.bot.message_processor = Mock()
            self.bot.intents = intents
            self.bot.user = Mock()
            self.bot.cleanup_task = Mock()
            self.bot.cleanup_task.is_running = Mock(return_value=False)
            
    @patch('subprocess.run')
    async def test_thread_creation_flow(self, mock_subprocess):
        """スレッド作成フローのテスト"""
        # モックスレッドオブジェクト
        mock_thread = AsyncMock()
        mock_thread.id = 987654321098765432
        mock_thread.name = "Test Thread"
        mock_thread.parent_id = 123456789012345678
        mock_thread.join = AsyncMock()
        
        # 親メッセージのモック
        mock_parent_message = Mock()
        mock_parent_message.content = "This is the parent message"
        mock_parent_message.author.name = "TestUser"
        mock_parent_message.created_at = datetime.now()
        
        mock_thread.parent.fetch_message = AsyncMock(return_value=mock_parent_message)
        
        # on_thread_createメソッドを呼び出し
        await self.bot.on_thread_create(mock_thread)
        
        # 検証
        # 1. 登録済みチャンネルの確認が行われたか
        self.settings.is_channel_registered.assert_called_once_with('123456789012345678')
        
        # 2. スレッドに参加したか
        mock_thread.join.assert_called_once()
        
        # 3. セッションが作成されたか
        self.settings.add_thread_session.assert_called_once_with('987654321098765432')
        
        # 4. tmuxセッションが起動されたか
        mock_subprocess.assert_called()
        tmux_calls = [call for call in mock_subprocess.call_args_list 
                     if call[0][0][0] == 'tmux']
        self.assertTrue(len(tmux_calls) >= 2)  # new-session と send-keys
        
    @patch('subprocess.run')
    async def test_thread_creation_unregistered_channel(self, mock_subprocess):
        """未登録チャンネルでのスレッド作成テスト"""
        # 未登録チャンネル
        self.settings.is_channel_registered = Mock(return_value=False)
        
        # モックスレッドオブジェクト
        mock_thread = AsyncMock()
        mock_thread.id = 987654321098765432
        mock_thread.name = "Test Thread"
        mock_thread.parent_id = 999999999999999999  # 未登録チャンネル
        mock_thread.join = AsyncMock()
        
        # on_thread_createメソッドを呼び出し
        await self.bot.on_thread_create(mock_thread)
        
        # 検証
        # 1. 登録確認は行われたか
        self.settings.is_channel_registered.assert_called_once()
        
        # 2. スレッドに参加していないか
        mock_thread.join.assert_not_called()
        
        # 3. セッションが作成されていないか
        self.settings.add_thread_session.assert_not_called()
        
        # 4. tmuxセッションが起動されていないか
        mock_subprocess.assert_not_called()
        
    async def test_thread_message_processing(self):
        """スレッドメッセージ処理のテスト"""
        # モックメッセージ
        mock_message = AsyncMock()
        mock_message.author = Mock()
        mock_message.author.id = 123456789
        mock_message.author.name = "TestUser"
        mock_message.channel.type = MagicMock()
        mock_message.channel.type.name = "public_thread"
        mock_message.channel.id = 987654321098765432
        mock_message.channel.parent_id = 123456789012345678
        mock_message.channel.name = "Test Thread"
        mock_message.channel.join = AsyncMock()
        mock_message.content = "Test message in thread"
        mock_message.attachments = []
        
        # Discord.ChannelTypeのモック
        with patch('discord.ChannelType') as mock_channel_type:
            mock_channel_type.public_thread = mock_message.channel.type
            
            # Bot自身でないことを確認
            self.bot.user = Mock()
            self.bot.user.id = 999999999
            
            # 既存スレッドで初回メッセージ
            self.settings.thread_to_session = Mock(return_value=None)
            
            # _send_loading_feedbackのモック
            self.bot._send_loading_feedback = AsyncMock(return_value=Mock())
            
            # _process_message_pipelineのモック
            self.bot._process_message_pipeline = AsyncMock(return_value="Success")
            
            # _update_feedbackのモック
            self.bot._update_feedback = AsyncMock()
            
            # _start_claude_sessionのモック
            self.bot._start_claude_session = AsyncMock()
            
            # process_commandsのモック
            self.bot.process_commands = AsyncMock()
            
            # on_messageメソッドを呼び出し
            await self.bot.on_message(mock_message)
            
            # 検証
            # 1. セッション確認が行われたか
            self.settings.thread_to_session.assert_called_with('987654321098765432')
            
            # 2. 新規セッションが作成されたか
            self.settings.add_thread_session.assert_called_with('987654321098765432')
            
            # 3. スレッドに参加したか
            mock_message.channel.join.assert_called_once()
            
            # 4. Claude Codeセッションが起動されたか
            self.bot._start_claude_session.assert_called_once()
            
    async def test_regular_channel_message_ignored(self):
        """通常チャンネルメッセージが無視されることをテスト"""
        # モックメッセージ（通常チャンネル）
        mock_message = AsyncMock()
        mock_message.author = Mock()
        mock_message.author.id = 123456789
        mock_message.channel.type = MagicMock()
        mock_message.channel.type.name = "text"  # 通常のテキストチャンネル
        
        # Discord.ChannelTypeのモック
        with patch('discord.ChannelType') as mock_channel_type:
            mock_channel_type.public_thread = MagicMock()
            mock_channel_type.public_thread.name = "public_thread"
            
            # Bot自身でないことを確認
            self.bot.user = Mock()
            self.bot.user.id = 999999999
            
            # process_commandsのモック
            self.bot.process_commands = AsyncMock()
            
            # _send_loading_feedbackのモック（呼ばれないはず）
            self.bot._send_loading_feedback = AsyncMock()
            
            # on_messageメソッドを呼び出し
            await self.bot.on_message(mock_message)
            
            # 検証
            # 通常チャンネルのメッセージは処理されないことを確認
            self.bot._send_loading_feedback.assert_not_called()


def run_async_test(coro):
    """非同期テストを実行するヘルパー関数"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


class TestThreadIntegrationAsync(TestThreadIntegration):
    """非同期テストを同期的に実行するラッパークラス"""
    
    def test_thread_creation_flow(self):
        run_async_test(super().test_thread_creation_flow())
        
    def test_thread_creation_unregistered_channel(self):
        run_async_test(super().test_thread_creation_unregistered_channel())
        
    def test_thread_message_processing(self):
        run_async_test(super().test_thread_message_processing())
        
    def test_regular_channel_message_ignored(self):
        run_async_test(super().test_regular_channel_message_ignored())


if __name__ == '__main__':
    unittest.main()