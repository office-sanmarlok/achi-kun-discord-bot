#!/usr/bin/env python3
"""
ChannelValidatorのユニットテスト
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, PropertyMock
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.channel_validator import ChannelValidator


class TestChannelValidator:
    """ChannelValidatorのテストクラス"""
    
    @pytest.fixture
    def validator(self):
        """テスト用ChannelValidatorインスタンス"""
        return ChannelValidator()
    
    @pytest.fixture
    def mock_guild(self):
        """モックのDiscordギルド"""
        guild = Mock()
        guild.me = Mock()
        
        # ロールのモックを適切に設定
        bot_role = Mock()
        bot_role.name = "BotRole"
        everyone_role = Mock()
        everyone_role.name = "@everyone"
        
        guild.me.roles = [bot_role, everyone_role]
        return guild
    
    @pytest.fixture
    def mock_channels(self):
        """モックのチャンネルリスト"""
        channels = []
        
        # 必要なチャンネルを作成
        for i, channel_name in enumerate(["1-idea", "2-requirements", "3-design", "4-tasks", "5-development"]):
            channel = Mock()
            channel.name = f"workflow-{channel_name}"
            channel.id = 100 + i
            
            # 権限設定
            permissions = Mock()
            permissions.send_messages = True
            permissions.create_public_threads = True
            permissions.send_messages_in_threads = True
            permissions.manage_threads = True
            permissions.read_message_history = True
            permissions.attach_files = True
            permissions.embed_links = True
            
            channel.permissions_for = Mock(return_value=permissions)
            channels.append(channel)
        
        return channels
    
    @pytest.mark.asyncio
    async def test_validate_all_channels_success(self, validator, mock_guild, mock_channels):
        """全チャンネル検証成功テスト"""
        mock_guild.text_channels = mock_channels
        
        errors = await validator.validate_all_channels(mock_guild)
        
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_all_channels_missing(self, validator, mock_guild):
        """チャンネル不足テスト"""
        # 一部のチャンネルのみ存在
        partial_channels = []
        for channel_name in ["1-idea", "3-design"]:
            channel = Mock()
            channel.name = channel_name
            channel.id = 100
            
            permissions = Mock()
            for perm in validator.REQUIRED_PERMISSIONS:
                setattr(permissions, perm, True)
            channel.permissions_for = Mock(return_value=permissions)
            
            partial_channels.append(channel)
        
        mock_guild.text_channels = partial_channels
        mock_guild.me = Mock()
        
        errors = await validator.validate_all_channels(mock_guild)
        
        # 3つのチャンネルが不足
        assert len(errors) >= 3
        assert any("2-requirements" in error for error in errors)
        assert any("4-tasks" in error for error in errors)
        assert any("5-development" in error for error in errors)
    
    @pytest.mark.asyncio
    async def test_validate_channel_permissions_success(self, validator):
        """権限検証成功テスト"""
        channel = Mock()
        channel.guild.me = Mock()
        
        # 全権限を有効に設定
        permissions = Mock()
        for perm in validator.REQUIRED_PERMISSIONS:
            setattr(permissions, perm, True)
        
        channel.permissions_for = Mock(return_value=permissions)
        
        errors = await validator.validate_channel_permissions(channel)
        
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_channel_permissions_missing(self, validator):
        """権限不足テスト"""
        channel = Mock()
        channel.name = "test-channel"
        channel.guild.me = Mock()
        
        # 一部の権限のみ有効
        permissions = Mock()
        permissions.send_messages = True
        permissions.create_public_threads = False
        permissions.send_messages_in_threads = False
        permissions.manage_threads = True
        permissions.read_message_history = True
        permissions.attach_files = False
        permissions.embed_links = True
        
        channel.permissions_for = Mock(return_value=permissions)
        
        errors = await validator.validate_channel_permissions(channel)
        
        assert len(errors) == 1
        assert "Missing permissions" in errors[0]
        assert "create_public_threads" in errors[0]
        assert "send_messages_in_threads" in errors[0]
        assert "attach_files" in errors[0]
    
    def test_get_channel_by_name_found(self, validator, mock_guild, mock_channels):
        """チャンネル名検索成功テスト"""
        mock_guild.text_channels = mock_channels
        
        channel = validator.get_channel_by_name(mock_guild, "2-requirements")
        
        assert channel is not None
        assert "2-requirements" in channel.name
    
    def test_get_channel_by_name_not_found(self, validator, mock_guild, mock_channels):
        """チャンネル名検索失敗テスト"""
        mock_guild.text_channels = mock_channels
        
        channel = validator.get_channel_by_name(mock_guild, "general")
        
        assert channel is None
    
    def test_get_required_channel(self, validator, mock_guild, mock_channels):
        """ステージ別チャンネル取得テスト"""
        mock_guild.text_channels = mock_channels
        
        # 各ステージでテスト
        assert validator.get_required_channel(mock_guild, "idea") is not None
        assert validator.get_required_channel(mock_guild, "requirements") is not None
        assert validator.get_required_channel(mock_guild, "design") is not None
        assert validator.get_required_channel(mock_guild, "tasks") is not None
        assert validator.get_required_channel(mock_guild, "development") is not None
        
        # 未知のステージ
        assert validator.get_required_channel(mock_guild, "unknown") is None
    
    def test_validate_thread_name_length(self, validator):
        """スレッド名長さ検証テスト"""
        # 正常な長さ
        assert validator.validate_thread_name_length("normal-thread-name") is None
        assert validator.validate_thread_name_length("a" * 100) is None
        
        # 長すぎる名前
        error = validator.validate_thread_name_length("a" * 101)
        assert error is not None
        assert "too long" in error
        assert "101" in error
    
    @pytest.mark.asyncio
    async def test_check_bot_setup_complete(self, validator, mock_guild, mock_channels):
        """ボットセットアップ完全チェックテスト"""
        mock_guild.text_channels = mock_channels
        
        result = await validator.check_bot_setup(mock_guild)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["channel_status"]) == 5
        assert all(status["found"] for status in result["channel_status"].values())
        assert "BotRole" in result["bot_roles"]
    
    @pytest.mark.asyncio
    async def test_check_bot_setup_incomplete(self, validator, mock_guild):
        """ボットセットアップ不完全チェックテスト"""
        # 空のチャンネルリスト
        mock_guild.text_channels = []
        
        # @everyoneロールのみ設定
        everyone_role = Mock()
        everyone_role.name = "@everyone"
        mock_guild.me.roles = [everyone_role]
        
        result = await validator.check_bot_setup(mock_guild)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert len(result["warnings"]) > 0
        assert "no custom roles" in result["warnings"][0]
    
    def test_format_setup_report(self, validator):
        """セットアップレポートフォーマットテスト"""
        setup_result = {
            "is_valid": False,
            "errors": ["Channel not found: #2-requirements"],
            "warnings": ["Bot has no custom roles"],
            "channel_status": {
                "1-idea": {"found": True, "id": 100, "name": "workflow-1-idea"},
                "2-requirements": {"found": False, "id": None, "name": None}
            },
            "bot_roles": ["BotRole"]
        }
        
        report = validator.format_setup_report(setup_result)
        
        assert "❌ SETUP REQUIRED" in report
        assert "Channel not found" in report
        assert "✅ #1-idea" in report
        assert "❌ #2-requirements NOT FOUND" in report
        assert "BotRole" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])