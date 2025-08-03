#!/usr/bin/env python3
"""
!postコマンドの統合テスト
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from pathlib import Path
import discord

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPostCommand(unittest.IsolatedAsyncioTestCase):
    """!postコマンドのテストクラス"""
    
    async def asyncSetUp(self):
        """非同期テストの初期設定"""
        from src.discord_bot import ClaudeCLIBot, create_bot_commands
        from config.settings import SettingsManager
        
        # Mock settings
        self.settings = Mock(spec=SettingsManager)
        
        # Mock discord intents
        with patch('discord.Intents.default') as mock_intents:
            mock_intents.return_value = Mock()
            self.bot = ClaudeCLIBot(self.settings)
        
        # Register commands
        create_bot_commands(self.bot, self.settings)
        
        # Get the post command
        self.post_command = self.bot.get_command('post')
        self.assertIsNotNone(self.post_command, "!post command should be registered")
    
    async def test_post_command_in_channel_error(self):
        """チャンネルで実行した場合のエラーテスト"""
        # Mock context
        ctx = Mock()
        ctx.channel = Mock()
        ctx.channel.parent = None  # Not a thread
        ctx.send = AsyncMock()
        
        # Execute command
        await self.post_command.callback(ctx)
        
        # Verify error message
        ctx.send.assert_called_once_with("❌ このコマンドはスレッド内でのみ使用可能です")
    
    async def test_post_command_no_target_channel_error(self):
        """送信先チャンネル未設定エラーテスト"""
        # Mock context
        ctx = Mock()
        ctx.channel = Mock()
        ctx.channel.parent = Mock()  # This is a thread
        ctx.send = AsyncMock()
        
        # Mock settings
        self.settings.get_post_target_channel.return_value = None
        
        # Execute command
        await self.post_command.callback(ctx)
        
        # Verify error message
        ctx.send.assert_called_once_with("❌ 送信先チャンネルが設定されていません")
    
    async def test_post_command_channel_not_found_error(self):
        """送信先チャンネルが見つからないエラーテスト"""
        # Mock context
        ctx = Mock()
        ctx.channel = Mock()
        ctx.channel.parent = Mock()  # This is a thread
        ctx.channel.name = "test-thread"
        ctx.send = AsyncMock()
        
        # Mock settings
        self.settings.get_post_target_channel.return_value = "123456789"
        
        # Mock bot.get_channel to return None
        self.bot.get_channel = Mock(return_value=None)
        
        # Execute command
        await self.post_command.callback(ctx)
        
        # Verify error message
        ctx.send.assert_called_once_with("❌ 送信先チャンネルが見つかりません")
    
    async def test_post_command_permission_error(self):
        """権限エラーテスト"""
        # Mock context
        ctx = Mock()
        ctx.channel = Mock()
        ctx.channel.parent = Mock()  # This is a thread
        ctx.channel.name = "test-thread"
        ctx.send = AsyncMock()
        
        # Mock settings
        self.settings.get_post_target_channel.return_value = "123456789"
        
        # Mock target channel
        target_channel = Mock()
        target_channel.name = "target-channel"
        target_channel.send = AsyncMock(side_effect=discord.Forbidden(Mock(), "Permission denied"))
        
        # Mock bot.get_channel
        self.bot.get_channel = Mock(return_value=target_channel)
        
        # Execute command
        await self.post_command.callback(ctx)
        
        # Verify error message
        ctx.send.assert_called_once_with("❌ 送信先チャンネルへのアクセス権限がありません")
    
    async def test_post_command_success(self):
        """正常動作テスト"""
        # Mock context
        ctx = Mock()
        ctx.channel = Mock()
        ctx.channel.parent = Mock()  # This is a thread
        ctx.channel.name = "test-thread"
        ctx.send = AsyncMock()
        
        # Mock settings
        self.settings.get_post_target_channel.return_value = "123456789"
        
        # Mock target channel
        target_channel = Mock()
        target_channel.name = "target-channel"
        target_channel.send = AsyncMock()
        
        # Mock bot.get_channel
        self.bot.get_channel = Mock(return_value=target_channel)
        
        # Execute command
        await self.post_command.callback(ctx)
        
        # Verify messages
        target_channel.send.assert_called_once_with("スレッド名: test-thread")
        ctx.send.assert_called_once_with("✅ スレッド名をtarget-channelに送信しました")
    
    async def test_post_command_invalid_channel_id(self):
        """無効なチャンネルIDエラーテスト"""
        # Mock context
        ctx = Mock()
        ctx.channel = Mock()
        ctx.channel.parent = Mock()  # This is a thread
        ctx.channel.name = "test-thread"
        ctx.send = AsyncMock()
        
        # Mock settings with invalid channel ID
        self.settings.get_post_target_channel.return_value = "invalid-id"
        
        # Mock bot.get_channel to raise ValueError
        self.bot.get_channel = Mock(side_effect=ValueError("Invalid channel ID"))
        
        # Execute command
        await self.post_command.callback(ctx)
        
        # Verify error message
        ctx.send.assert_called_once_with("❌ 無効なチャンネルIDが設定されています")
    
    async def test_post_command_generic_error(self):
        """一般的なエラーのテスト"""
        # Mock context
        ctx = Mock()
        ctx.channel = Mock()
        ctx.channel.parent = Mock()  # This is a thread
        ctx.channel.name = "test-thread"
        ctx.send = AsyncMock()
        
        # Mock settings
        self.settings.get_post_target_channel.return_value = "123456789"
        
        # Mock target channel
        target_channel = Mock()
        target_channel.name = "target-channel"
        target_channel.send = AsyncMock(side_effect=Exception("Network error"))
        
        # Mock bot.get_channel
        self.bot.get_channel = Mock(return_value=target_channel)
        
        # Execute command
        await self.post_command.callback(ctx)
        
        # Verify error message
        ctx.send.assert_called_once_with("❌ エラーが発生しました: Network error")


class TestPostCommandIntegration(unittest.TestCase):
    """!postコマンドの統合テスト"""
    
    @patch('discord.Intents')
    def test_post_command_registered(self, mock_intents):
        """!postコマンドが正しく登録されることを確認"""
        from src.discord_bot import ClaudeCLIBot, create_bot_commands
        from config.settings import SettingsManager
        
        # Mock settings
        settings = Mock(spec=SettingsManager)
        
        # Create bot instance
        mock_intents.default.return_value = Mock()
        bot = ClaudeCLIBot(settings)
        
        # Register commands
        create_bot_commands(bot, settings)
        
        # Check command exists
        self.assertIsNotNone(bot.get_command('post'))
        
        # Check other commands still exist
        self.assertIsNotNone(bot.get_command('status'))
        self.assertIsNotNone(bot.get_command('sessions'))
        self.assertIsNotNone(bot.get_command('cc'))


if __name__ == '__main__':
    unittest.main()