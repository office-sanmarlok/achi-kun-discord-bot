#!/usr/bin/env python3
"""
全機能の統合テスト
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntegration(unittest.TestCase):
    """統合テストクラス"""
    
    def test_message_filtering_logic(self):
        """メッセージフィルタリングロジックの確認"""
        from src.discord_bot import ClaudeCLIBot
        
        # Create a minimal bot instance
        with patch('discord.Intents.default') as mock_intents:
            mock_intents.return_value = Mock()
            with patch('src.discord_bot.commands.Bot.__init__', return_value=None):
                bot = ClaudeCLIBot.__new__(ClaudeCLIBot)
                bot.user = Mock()
                bot.user.id = 12345
                
                # Test cases
                test_cases = [
                    # (message_content, author_is_bot, expected_result)
                    ("Hello Claude", False, True),  # Normal message
                    ("!status", False, False),  # Command message
                    ("!post", False, False),  # New command
                    ("!cc thread-name", False, False),  # Existing command
                    ("Hello!", False, True),  # Exclamation not at start
                    ("", False, True),  # Empty message
                    ("Hello Claude", True, False),  # Bot's own message
                ]
                
                for content, is_bot, expected in test_cases:
                    with self.subTest(content=content, is_bot=is_bot):
                        message = Mock()
                        message.content = content
                        message.author = bot.user if is_bot else Mock(id=67890)
                        
                        result = bot.should_forward_to_claude(message)
                        self.assertEqual(result, expected, 
                                       f"Failed for content='{content}', is_bot={is_bot}")
    
    def test_settings_integration(self):
        """設定管理の統合テスト"""
        from config.settings import SettingsManager
        import tempfile
        import shutil
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create settings instance
            with patch.object(SettingsManager, '__init__', lambda x: None):
                settings = SettingsManager()
                settings.config_dir = Path(temp_dir)
                settings.settings_file = Path(temp_dir) / 'settings.json'
                settings.env_file = Path(temp_dir) / '.env'
                settings.sessions_file = Path(temp_dir) / 'sessions.json'
                
                # Test post target channel functionality
                self.assertIsNone(settings.get_post_target_channel())
                
                # Set channel
                test_channel_id = "987654321098765432"
                settings.set_post_target_channel(test_channel_id)
                
                # Verify it's saved
                self.assertEqual(settings.get_post_target_channel(), test_channel_id)
                
                # Test with existing settings
                settings.add_thread_session("111222333444555666")
                
                # Verify all settings are preserved
                loaded_settings = settings._load_settings()
                self.assertEqual(loaded_settings['post_target_channel'], test_channel_id)
                self.assertIn("111222333444555666", loaded_settings['thread_sessions'])
                
        finally:
            # Cleanup
            shutil.rmtree(temp_dir)
    
    def test_command_existence(self):
        """全コマンドの存在確認"""
        from src.discord_bot import ClaudeCLIBot, create_bot_commands
        from config.settings import SettingsManager
        
        with patch('discord.Intents.default') as mock_intents:
            mock_intents.return_value = Mock()
            
            settings = Mock(spec=SettingsManager)
            bot = ClaudeCLIBot(settings)
            create_bot_commands(bot, settings)
            
            # Check all commands exist
            expected_commands = ['status', 'sessions', 'cc', 'post']
            for cmd_name in expected_commands:
                with self.subTest(command=cmd_name):
                    command = bot.get_command(cmd_name)
                    self.assertIsNotNone(command, f"Command !{cmd_name} should exist")
    
    def test_performance_considerations(self):
        """パフォーマンス関連の確認"""
        from src.discord_bot import ClaudeCLIBot
        
        # Verify that message filtering is efficient
        with patch('discord.Intents.default') as mock_intents:
            mock_intents.return_value = Mock()
            with patch('src.discord_bot.commands.Bot.__init__', return_value=None):
                bot = ClaudeCLIBot.__new__(ClaudeCLIBot)
                bot.user = Mock()
                bot.user.id = 12345
                
                # The should_forward_to_claude method should be fast
                # It only does simple string checks
                message = Mock()
                message.author = Mock(id=67890)
                
                # Test with various message lengths
                for length in [10, 100, 1000, 10000]:
                    message.content = "a" * length
                    result = bot.should_forward_to_claude(message)
                    self.assertTrue(result)  # Should forward long messages
                    
                    message.content = "!" + "a" * (length - 1)
                    result = bot.should_forward_to_claude(message)
                    self.assertFalse(result)  # Should not forward commands


if __name__ == '__main__':
    unittest.main()