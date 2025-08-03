#!/usr/bin/env python3
"""
設定管理モジュール
Claude-Discord Bridgeの設定を管理する
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, List
import configparser

class SettingsManager:
    """設定の読み込み、保存、管理を行うクラス"""
    
    def __init__(self):
        # プロジェクトルートディレクトリを基準に設定
        self.toolkit_root = Path(__file__).parent.parent
        self.config_dir = self.toolkit_root  # プロジェクトルートに設定ファイルを配置
        self.env_file = self.config_dir / '.env'
        self.attachments_dir = self.config_dir / 'attachments'
        self.run_dir = self.config_dir / 'run'
        
        # 既存の設定を移行（初回のみ）
        self._migrate_from_home_dir()
        
    def _migrate_from_home_dir(self):
        """ホームディレクトリからプロジェクトディレクトリへ設定を移行"""
        old_dir = Path.home() / '.claude-discord-bridge'
        
        # .envファイルの移行
        if old_dir.exists() and not self.env_file.exists():
            old_env = old_dir / '.env'
            if old_env.exists():
                import shutil
                shutil.copy2(old_env, self.env_file)
                print(f"📦 Migrated .env: {old_env} → {self.env_file}")
        
        # attachmentsディレクトリの移行
        if old_dir.exists():
            old_attachments = old_dir / 'attachments'
            if old_attachments.exists() and old_attachments.is_dir():
                if not self.attachments_dir.exists():
                    import shutil
                    shutil.move(str(old_attachments), str(self.attachments_dir))
                    print(f"📦 Migrated attachments: {old_attachments} → {self.attachments_dir}")
    
    def ensure_config_dir(self):
        """設定ディレクトリを作成"""
        self.config_dir.mkdir(exist_ok=True)
        self.attachments_dir.mkdir(exist_ok=True)
        self.run_dir.mkdir(exist_ok=True)
        
    def load_env(self) -> Dict[str, str]:
        """環境変数を読み込み"""
        env_vars = {}
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        return env_vars
    
    def save_env(self, env_vars: Dict[str, str]):
        """環境変数を保存"""
        self.ensure_config_dir()
        with open(self.env_file, 'w') as f:
            f.write("# Claude-Discord Bridge Configuration\n")
            f.write("# This file contains sensitive information. Do not share!\n\n")
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        # Set permissions to 600 (owner read/write only)
        os.chmod(self.env_file, 0o600)
    
    
    def get_token(self) -> Optional[str]:
        """Discord bot tokenを取得"""
        env_vars = self.load_env()
        return env_vars.get('DISCORD_BOT_TOKEN')
    
    def set_token(self, token: str):
        """Discord bot tokenを設定"""
        env_vars = self.load_env()
        env_vars['DISCORD_BOT_TOKEN'] = token
        self.save_env(env_vars)
    
    
    
    
    
    def get_port(self, service: str = 'flask') -> int:
        """サービスのポート番号を取得"""
        # 環境変数から読み取る
        env_vars = self.load_env()
        port_map = {
            'flask': int(env_vars.get('FLASK_PORT', '5001'))  # macOS ControlCenter対策
        }
        return port_map.get(service, 5001)
    
    def get_claude_work_dir(self) -> str:
        """Claude Codeの作業ディレクトリを取得"""
        env_vars = self.load_env()
        return env_vars.get('CLAUDE_WORK_DIR', os.getcwd())
    
    def get_claude_options(self) -> str:
        """Claude Codeの起動オプションを取得"""
        env_vars = self.load_env()
        return env_vars.get('CLAUDE_OPTIONS', '')
    
    
    def is_configured(self) -> bool:
        """初期設定が完了しているかチェック"""
        # 基本的な設定ファイルの存在とトークンの有無をチェック
        return (self.env_file.exists() and 
                self.get_token() is not None and 
                self.get_token() != 'your_token_here')

if __name__ == "__main__":
    # Test settings manager
    manager = SettingsManager()
    print(f"Config directory: {manager.config_dir}")
    print(f"Is configured: {manager.is_configured()}")
    
    if manager.is_configured():
        print("Configuration is valid")