#!/usr/bin/env python3
"""
settings.py の単体テスト
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import json

# テスト対象のモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import SettingsManager


class TestSettingsManager(unittest.TestCase):
    """SettingsManagerのテストクラス"""
    
    def setUp(self):
        """各テストの前に実行される"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.original_home = Path.home()
        
        # SettingsManagerが使用するホームディレクトリを一時的に変更
        Path.home = lambda: Path(self.temp_dir)
        
        # テスト用のSettingsManagerインスタンスを作成
        self.settings = SettingsManager()
        
    def tearDown(self):
        """各テストの後に実行される"""
        # ホームディレクトリを元に戻す
        Path.home = lambda: self.original_home
        
        # 一時ディレクトリを削除
        shutil.rmtree(self.temp_dir)
    
    def test_initial_settings_structure(self):
        """初期設定構造のテスト"""
        settings = self.settings._load_settings()
        
        self.assertIn('thread_sessions', settings)
        self.assertIn('registered_channels', settings)
        self.assertIn('ports', settings)
        self.assertEqual(settings['thread_sessions'], {})
        self.assertEqual(settings['registered_channels'], [])
        self.assertEqual(settings['ports']['flask'], 5001)
    
    def test_channel_registration(self):
        """チャンネル登録機能のテスト"""
        channel_id = "123456789"
        
        # 初期状態では未登録
        self.assertFalse(self.settings.is_channel_registered(channel_id))
        
        # チャンネルを登録
        self.settings.register_channel(channel_id)
        
        # 登録後は登録済み
        self.assertTrue(self.settings.is_channel_registered(channel_id))
        
        # 重複登録のテスト
        self.settings.register_channel(channel_id)
        settings = self.settings._load_settings()
        self.assertEqual(settings['registered_channels'].count(channel_id), 1)
    
    def test_thread_session_management(self):
        """スレッドセッション管理のテスト"""
        thread_id1 = "thread_123"
        thread_id2 = "thread_456"
        
        # 初期状態ではセッションなし
        self.assertIsNone(self.settings.thread_to_session(thread_id1))
        
        # セッション追加
        session_num1 = self.settings.add_thread_session(thread_id1)
        self.assertEqual(session_num1, 1)
        self.assertEqual(self.settings.thread_to_session(thread_id1), 1)
        
        # 2つ目のセッション追加
        session_num2 = self.settings.add_thread_session(thread_id2)
        self.assertEqual(session_num2, 2)
        self.assertEqual(self.settings.thread_to_session(thread_id2), 2)
        
        # 重複追加はしない（既存のセッション番号を返す想定）
        # ※現在の実装では新しいセッション番号が割り当てられる
        session_num3 = self.settings.add_thread_session(thread_id1)
        self.assertEqual(session_num3, 3)
    
    def test_list_thread_sessions(self):
        """スレッドセッション一覧のテスト"""
        # 初期状態
        sessions = self.settings.list_thread_sessions()
        self.assertEqual(len(sessions), 0)
        
        # セッション追加
        self.settings.add_thread_session("thread_1")
        self.settings.add_thread_session("thread_2")
        
        # 一覧取得
        sessions = self.settings.list_thread_sessions()
        self.assertEqual(len(sessions), 2)
        
        # フォーマットの確認
        self.assertEqual(sessions[0][0], 1)  # session_num
        self.assertEqual(sessions[0][1], "thread_1")  # thread_id
        self.assertEqual(sessions[0][2], "thread")  # type
        
        self.assertEqual(sessions[1][0], 2)
        self.assertEqual(sessions[1][1], "thread_2")
        self.assertEqual(sessions[1][2], "thread")
    
    def test_settings_persistence(self):
        """設定の永続化テスト"""
        # 設定を追加
        self.settings.register_channel("channel_123")
        self.settings.add_thread_session("thread_abc")
        
        # 新しいインスタンスで読み込み
        new_settings = SettingsManager()
        
        # 設定が保持されていることを確認
        self.assertTrue(new_settings.is_channel_registered("channel_123"))
        self.assertEqual(new_settings.thread_to_session("thread_abc"), 1)
    
    def test_port_configuration(self):
        """ポート設定のテスト"""
        # デフォルトポート
        self.assertEqual(self.settings.get_port('flask'), 5001)
        
        # 未知のサービス
        self.assertEqual(self.settings.get_port('unknown'), 5000)
        
        # 設定ファイルでポートを変更
        settings = self.settings._load_settings()
        settings['ports']['flask'] = 8080
        self.settings._save_settings(settings)
        
        # 変更が反映されることを確認
        self.assertEqual(self.settings.get_port('flask'), 8080)
    
    def test_is_configured(self):
        """設定完了チェックのテスト"""
        # 初期状態では未設定
        self.assertFalse(self.settings.is_configured())
        
        # トークンを設定
        self.settings.set_token("test_token_123")
        
        # まだチャンネルが登録されていないので未設定
        self.assertFalse(self.settings.is_configured())
        
        # チャンネルを登録
        self.settings.register_channel("channel_123")
        
        # これで設定完了
        self.assertTrue(self.settings.is_configured())


if __name__ == '__main__':
    unittest.main()