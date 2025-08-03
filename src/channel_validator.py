#!/usr/bin/env python3
"""
Channel Validator - Discordチャンネルと権限の検証

このモジュールは以下の責務を持つ：
1. 必要なDiscordチャンネルの存在確認
2. ボットの権限検証
3. ワークフロー設定の検証
"""

import logging
from typing import List, Optional, Dict, Set
import discord

logger = logging.getLogger(__name__)


class ChannelValidator:
    """Discordチャンネルと権限を検証するクラス"""
    
    # 必要なチャンネル名のリスト
    REQUIRED_CHANNELS = ["1-idea", "2-requirements", "3-design", "4-tasks", "5-development"]
    
    # 必要な権限のセット
    REQUIRED_PERMISSIONS = {
        "send_messages",
        "create_public_threads",
        "send_messages_in_threads",
        "manage_threads",
        "read_message_history",
        "attach_files",  # 画像送信用
        "embed_links"    # リッチメッセージ用
    }
    
    def __init__(self):
        """初期化"""
        logger.info("ChannelValidator initialized")
    
    async def validate_all_channels(self, guild: discord.Guild) -> List[str]:
        """
        全必須チャンネルの検証
        
        Args:
            guild: DiscordギルドオブジェクトChannelValidator
        
        Returns:
            エラーメッセージのリスト（問題がない場合は空リスト）
        """
        errors = []
        found_channels = set()
        
        # ギルド内の全テキストチャンネルをチェック
        for channel in guild.text_channels:
            # チャンネル名に必要なキーワードが含まれているかチェック
            for required_channel in self.REQUIRED_CHANNELS:
                if required_channel in channel.name:
                    found_channels.add(required_channel)
                    logger.info(f"Found required channel: {channel.name} (#{channel.id})")
                    break
        
        # 見つからなかったチャンネルを特定
        missing_channels = set(self.REQUIRED_CHANNELS) - found_channels
        for missing in missing_channels:
            error_msg = f"Required channel not found: #{missing}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        # 各チャンネルの権限もチェック
        for channel in guild.text_channels:
            for required_channel in self.REQUIRED_CHANNELS:
                if required_channel in channel.name:
                    permission_errors = await self.validate_channel_permissions(channel)
                    if permission_errors:
                        for perm_error in permission_errors:
                            errors.append(f"#{channel.name}: {perm_error}")
                    break
        
        return errors
    
    async def validate_channel_permissions(self, channel: discord.TextChannel) -> List[str]:
        """
        チャンネル権限の検証
        
        Args:
            channel: Discordテキストチャンネル
            
        Returns:
            不足している権限のリスト（問題がない場合は空リスト）
        """
        errors = []
        
        # ボットのメンバーオブジェクトを取得
        bot_member = channel.guild.me
        if not bot_member:
            errors.append("Bot member not found in guild")
            return errors
        
        # チャンネルでのボットの権限を取得
        permissions = channel.permissions_for(bot_member)
        
        # 必要な権限をチェック
        missing_permissions = []
        for perm_name in self.REQUIRED_PERMISSIONS:
            if not getattr(permissions, perm_name, False):
                missing_permissions.append(perm_name)
        
        if missing_permissions:
            errors.append(f"Missing permissions: {', '.join(missing_permissions)}")
            logger.warning(f"Channel {channel.name} missing permissions: {missing_permissions}")
        
        return errors
    
    def get_channel_by_name(self, guild: discord.Guild, name: str) -> Optional[discord.TextChannel]:
        """
        チャンネル名からチャンネルオブジェクトを取得
        
        Args:
            guild: Discordギルド
            name: 検索するチャンネル名（部分一致）
            
        Returns:
            見つかったチャンネル、見つからない場合はNone
        """
        for channel in guild.text_channels:
            if name in channel.name:
                logger.info(f"Found channel: {channel.name} for search term: {name}")
                return channel
        
        logger.warning(f"Channel not found for search term: {name}")
        return None
    
    def get_required_channel(self, guild: discord.Guild, stage: str) -> Optional[discord.TextChannel]:
        """
        ステージ名から必要なチャンネルを取得
        
        Args:
            guild: Discordギルド
            stage: ステージ名（idea, requirements, design, tasks, development）
            
        Returns:
            対応するチャンネル、見つからない場合はNone
        """
        channel_map = {
            "idea": "1-idea",
            "requirements": "2-requirements",
            "design": "3-design",
            "tasks": "4-tasks",
            "development": "5-development"
        }
        
        channel_name = channel_map.get(stage)
        if not channel_name:
            logger.error(f"Unknown stage: {stage}")
            return None
        
        return self.get_channel_by_name(guild, channel_name)
    
    def validate_thread_name_length(self, thread_name: str) -> Optional[str]:
        """
        スレッド名の長さを検証
        
        Args:
            thread_name: 検証するスレッド名
            
        Returns:
            エラーメッセージ、問題がない場合はNone
        """
        # Discordのスレッド名制限は100文字
        MAX_THREAD_NAME_LENGTH = 100
        
        if len(thread_name) > MAX_THREAD_NAME_LENGTH:
            return f"Thread name too long: {len(thread_name)} characters (max: {MAX_THREAD_NAME_LENGTH})"
        
        return None
    
    async def check_bot_setup(self, guild: discord.Guild) -> Dict[str, any]:
        """
        ボットのセットアップ状態を包括的にチェック
        
        Args:
            guild: Discordギルド
            
        Returns:
            チェック結果の辞書
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "channel_status": {},
            "permission_status": {}
        }
        
        # チャンネル検証
        channel_errors = await self.validate_all_channels(guild)
        if channel_errors:
            result["is_valid"] = False
            result["errors"].extend(channel_errors)
        
        # 各チャンネルの詳細ステータス
        for required_channel in self.REQUIRED_CHANNELS:
            channel = self.get_channel_by_name(guild, required_channel)
            if channel:
                result["channel_status"][required_channel] = {
                    "found": True,
                    "id": channel.id,
                    "name": channel.name
                }
                
                # 権限チェック
                perms = channel.permissions_for(guild.me)
                result["permission_status"][required_channel] = {
                    perm: getattr(perms, perm, False)
                    for perm in self.REQUIRED_PERMISSIONS
                }
            else:
                result["channel_status"][required_channel] = {
                    "found": False,
                    "id": None,
                    "name": None
                }
        
        # ボットのロール確認
        bot_roles = [role.name for role in guild.me.roles if role.name != "@everyone"]
        if not bot_roles:
            result["warnings"].append("Bot has no custom roles assigned")
        
        result["bot_roles"] = bot_roles
        
        return result
    
    def format_setup_report(self, setup_result: Dict[str, any]) -> str:
        """
        セットアップチェック結果を人間が読みやすい形式にフォーマット
        
        Args:
            setup_result: check_bot_setupの結果
            
        Returns:
            フォーマットされたレポート文字列
        """
        lines = ["=== Discord Bot Setup Report ===\n"]
        
        # 全体のステータス
        status = "✅ READY" if setup_result["is_valid"] else "❌ SETUP REQUIRED"
        lines.append(f"Status: {status}\n")
        
        # エラー
        if setup_result["errors"]:
            lines.append("Errors:")
            for error in setup_result["errors"]:
                lines.append(f"  ❌ {error}")
            lines.append("")
        
        # 警告
        if setup_result["warnings"]:
            lines.append("Warnings:")
            for warning in setup_result["warnings"]:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")
        
        # チャンネルステータス
        lines.append("Channel Status:")
        for channel_name, status in setup_result["channel_status"].items():
            if status["found"]:
                lines.append(f"  ✅ #{channel_name} (ID: {status['id']})")
            else:
                lines.append(f"  ❌ #{channel_name} NOT FOUND")
        lines.append("")
        
        # ボットロール
        lines.append("Bot Roles:")
        for role in setup_result.get("bot_roles", []):
            lines.append(f"  - {role}")
        
        return "\n".join(lines)