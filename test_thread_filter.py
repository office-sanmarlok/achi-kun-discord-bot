#!/usr/bin/env python3
"""
コマンド経由スレッドフィルタリングのテストスクリプト
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.session_manager import get_session_manager

def test_session_manager():
    """SessionManagerのテスト"""
    print("=== SessionManager テスト開始 ===")
    
    manager = get_session_manager()
    
    # コマンド経由スレッドのマーキングテスト
    test_thread_id = "123456789"
    
    print(f"1. スレッド {test_thread_id} がコマンド経由かチェック...")
    assert not manager.is_command_thread(test_thread_id), "初期状態では False のはず"
    print("   ✅ 初期状態: False")
    
    print(f"2. スレッド {test_thread_id} をコマンド経由としてマーク...")
    manager.mark_as_command_thread(test_thread_id)
    print("   ✅ マーク完了")
    
    print(f"3. スレッド {test_thread_id} がコマンド経由かチェック...")
    assert manager.is_command_thread(test_thread_id), "マーク後は True のはず"
    print("   ✅ マーク後: True")
    
    # 別のスレッドIDのテスト
    other_thread_id = "987654321"
    print(f"4. 別のスレッド {other_thread_id} がコマンド経由かチェック...")
    assert not manager.is_command_thread(other_thread_id), "マークしていないスレッドは False のはず"
    print("   ✅ 未マークスレッド: False")
    
    print("\n✅ すべてのテストが成功しました！")
    print("\n=== 実装の動作説明 ===")
    print("1. !idea または !cc コマンドでスレッドを作成")
    print("   → スレッドIDが command_created_threads に追加される")
    print("2. 手動でスレッドを作成してメッセージを送信")
    print("   → is_command_thread() が False を返すため無視される")
    print("3. !idea や !cc で作成したスレッドにメッセージを送信")
    print("   → is_command_thread() が True を返すため処理される")

if __name__ == "__main__":
    test_session_manager()