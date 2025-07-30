#!/usr/bin/env python3
"""
設定管理拡張機能のテスト
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import SettingsManager


class TestSettingsExtension(unittest.TestCase):
    """設定管理拡張機能のテストクラス"""
    
    def setUp(self):
        """テストの初期設定"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # SettingsManagerのパスをモック
        with patch.object(SettingsManager, '__init__', lambda x: None):
            self.settings = SettingsManager()
            self.settings.config_dir = self.temp_path
            self.settings.env_file = self.temp_path / '.env'
            self.settings.sessions_file = self.temp_path / 'sessions.json'
            self.settings.settings_file = self.temp_path / 'settings.json'
            self.settings.toolkit_root = Path(__file__).parent.parent
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir)
    
    def test_get_post_target_channel_when_not_set(self):
        """未設定時のget_post_target_channelテスト"""
        result = self.settings.get_post_target_channel()
        self.assertIsNone(result)
    
    def test_set_and_get_post_target_channel(self):
        """送信先チャンネルIDの設定と取得テスト"""
        test_channel_id = "123456789012345678"
        
        # 設定
        self.settings.set_post_target_channel(test_channel_id)
        
        # 取得
        result = self.settings.get_post_target_channel()
        self.assertEqual(result, test_channel_id)
        
        # ファイルに保存されているか確認
        with open(self.settings.settings_file, 'r') as f:
            saved_settings = json.load(f)
            self.assertEqual(saved_settings['post_target_channel'], test_channel_id)
    
    def test_update_existing_settings_file(self):
        """既存の設定ファイルを更新するテスト"""
        # 既存の設定ファイルを作成
        existing_settings = {
            'thread_sessions': {'111': 1, '222': 2},
            'registered_channels': ['333', '444'],
            'ports': {'flask': 5001}
        }
        
        self.settings.config_dir.mkdir(exist_ok=True)
        with open(self.settings.settings_file, 'w') as f:
            json.dump(existing_settings, f)
        
        # 新しい設定を追加
        test_channel_id = "555555555555555555"
        self.settings.set_post_target_channel(test_channel_id)
        
        # 既存の設定が保持されているか確認
        with open(self.settings.settings_file, 'r') as f:
            saved_settings = json.load(f)
            self.assertEqual(saved_settings['thread_sessions'], existing_settings['thread_sessions'])
            self.assertEqual(saved_settings['registered_channels'], existing_settings['registered_channels'])
            self.assertEqual(saved_settings['ports'], existing_settings['ports'])
            self.assertEqual(saved_settings['post_target_channel'], test_channel_id)
    
    def test_load_settings_backward_compatibility(self):
        """既存の設定ファイルとの互換性テスト"""
        # post_target_channelを含まない既存の設定ファイル
        old_settings = {
            'thread_sessions': {'111': 1},
            'registered_channels': ['333'],
            'ports': {'flask': 5001}
        }
        
        self.settings.config_dir.mkdir(exist_ok=True)
        with open(self.settings.settings_file, 'w') as f:
            json.dump(old_settings, f)
        
        # 設定を読み込み
        loaded_settings = self.settings._load_settings()
        
        # post_target_channelがNoneとして追加されているか確認
        self.assertIn('post_target_channel', loaded_settings)
        self.assertIsNone(loaded_settings['post_target_channel'])
        
        # 既存の設定が保持されているか確認
        self.assertEqual(loaded_settings['thread_sessions'], old_settings['thread_sessions'])
        self.assertEqual(loaded_settings['registered_channels'], old_settings['registered_channels'])
        self.assertEqual(loaded_settings['ports'], old_settings['ports'])
    
    def test_default_settings_include_post_target_channel(self):
        """デフォルト設定にpost_target_channelが含まれるテスト"""
        # 設定ファイルが存在しない状態で読み込み
        loaded_settings = self.settings._load_settings()
        
        # デフォルト設定の確認
        self.assertIn('post_target_channel', loaded_settings)
        self.assertIsNone(loaded_settings['post_target_channel'])
        self.assertEqual(loaded_settings['thread_sessions'], {})
        self.assertEqual(loaded_settings['registered_channels'], [])
        self.assertEqual(loaded_settings['ports'], {'flask': 5001})
    
    def test_ensure_config_dir_called(self):
        """設定保存時にensure_config_dirが呼ばれることを確認"""
        with patch.object(self.settings, 'ensure_config_dir') as mock_ensure:
            self.settings.set_post_target_channel("123")
            mock_ensure.assert_called_once()


if __name__ == '__main__':
    unittest.main()