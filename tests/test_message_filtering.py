#!/usr/bin/env python3
"""
メッセージフィルタリング機能のテスト
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMessageFiltering(unittest.TestCase):
    """メッセージフィルタリング機能のテストクラス"""
    
    @patch('discord.Intents')
    @patch('src.discord_bot.commands.Bot.__init__', return_value=None)
    def setUp(self, mock_bot_init, mock_intents):
        """テストの初期設定"""
        from src.discord_bot import ClaudeCLIBot
        from config.settings import SettingsManager
        
        self.settings = Mock(spec=SettingsManager)
        
        # ClaudeCLIBotのインスタンスを作成（__init__をモック化）
        self.bot = ClaudeCLIBot.__new__(ClaudeCLIBot)
        self.bot.settings = self.settings
        self.bot.attachment_manager = Mock()
        self.bot.message_processor = Mock()
        
        # Mock user
        self.bot.user = Mock()
        self.bot.user.id = 12345
        
    def test_should_forward_bot_message(self):
        """Bot自身のメッセージは転送されないことを確認"""
        message = Mock()
        message.author = self.bot.user
        message.content = "Hello from bot"
        
        result = self.bot.should_forward_to_claude(message)
        self.assertFalse(result)
        
    def test_should_not_forward_command_message(self):
        """!で始まるメッセージは転送されないことを確認"""
        message = Mock()
        message.author = Mock()
        message.author.id = 67890  # Different from bot
        message.content = "!status"
        
        result = self.bot.should_forward_to_claude(message)
        self.assertFalse(result)
        
    def test_should_forward_normal_message(self):
        """通常のメッセージは転送されることを確認"""
        message = Mock()
        message.author = Mock()
        message.author.id = 67890  # Different from bot
        message.content = "Hello, Claude!"
        
        result = self.bot.should_forward_to_claude(message)
        self.assertTrue(result)
        
    def test_should_forward_message_with_exclamation_not_at_start(self):
        """!が先頭以外にあるメッセージは転送されることを確認"""
        message = Mock()
        message.author = Mock()
        message.author.id = 67890
        message.content = "Hello! How are you?"
        
        result = self.bot.should_forward_to_claude(message)
        self.assertTrue(result)
        
    def test_edge_cases(self):
        """エッジケースのテスト"""
        test_cases = [
            ("", True),  # 空メッセージ
            ("!", False),  # !のみ
            ("!!", False),  # 複数の!
            (" !command", True),  # スペースで始まる
            ("@!command", True),  # @で始まる
        ]
        
        for content, expected in test_cases:
            with self.subTest(content=content):
                message = Mock()
                message.author = Mock()
                message.author.id = 67890
                message.content = content
                
                result = self.bot.should_forward_to_claude(message)
                self.assertEqual(result, expected, f"Failed for content: '{content}'")


class TestIntegration(unittest.TestCase):
    """統合テスト"""
    
    @patch('discord.Intents')
    def test_existing_commands_registered(self, mock_intents):
        """既存のコマンドが正しく登録されることを確認"""
        from src.discord_bot import ClaudeCLIBot, create_bot_commands
        from config.settings import SettingsManager
        
        # Mock settings
        settings = Mock(spec=SettingsManager)
        
        # Create bot instance
        mock_intents.default.return_value = Mock()
        bot = ClaudeCLIBot(settings)
        
        # Register commands
        create_bot_commands(bot, settings)
        
        # Check commands exist
        self.assertIsNotNone(bot.get_command('status'))
        self.assertIsNotNone(bot.get_command('sessions'))
        self.assertIsNotNone(bot.get_command('cc'))


if __name__ == '__main__':
    unittest.main()