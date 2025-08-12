#!/usr/bin/env python3
"""
処理中アニメーション表示モジュール
Discord上でClaude Codeが処理中であることを視覚的に表示
"""

import asyncio
import discord
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)


class ProcessingAnimator:
    """
    Discord上で処理中を示すアニメーションを管理するクラス
    """
    
    # スピナーアニメーションのフレーム
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    # ステータスメッセージのバリエーション
    STATUS_MESSAGES = [
        "Claude Codeが考えています",
        "コードを分析中",
        "応答を準備中",
        "処理を実行中"
    ]
    
    # アニメーション更新間隔（秒）
    UPDATE_INTERVAL = 1.0
    
    def __init__(self):
        """
        アニメーター初期化
        """
        self.active_animations = {}  # channel_id: (message, task)
        self.frame_counters = {}  # channel_id: frame_index
        
    async def start_animation(self, channel: discord.TextChannel, 
                             initial_message: str = None) -> discord.Message:
        """
        アニメーションを開始
        
        Args:
            channel: 表示するDiscordチャンネル
            initial_message: 初期表示メッセージ（オプション）
            
        Returns:
            送信されたアニメーションメッセージ
        """
        channel_id = channel.id
        
        # 既存のアニメーションがあれば停止
        await self.stop_animation(channel_id)
        
        # 初期メッセージ作成
        embed = self._create_animation_embed(0, initial_message)
        message = await channel.send(embed=embed)
        
        # アニメーションタスクを開始
        self.frame_counters[channel_id] = 0
        animation_task = asyncio.create_task(
            self._animation_loop(channel_id, message, initial_message)
        )
        
        self.active_animations[channel_id] = (message, animation_task)
        
        logger.info(f"Started animation in channel {channel_id}")
        return message
        
    async def stop_animation(self, channel_id: int, 
                           final_message: str = None,
                           success: bool = True) -> None:
        """
        アニメーションを停止
        
        Args:
            channel_id: チャンネルID
            final_message: 最終表示メッセージ（オプション）
            success: 成功/失敗の状態
        """
        if channel_id not in self.active_animations:
            return
            
        message, task = self.active_animations[channel_id]
        
        # タスクをキャンセル
        if not task.done():
            task.cancel()
            
        try:
            # 最終メッセージに更新または削除
            if final_message:
                embed = self._create_final_embed(final_message, success)
                await message.edit(embed=embed)
                # 3秒後に自動削除
                await asyncio.sleep(3)
                
            await message.delete()
            
        except discord.errors.NotFound:
            # メッセージが既に削除されている場合
            pass
        except Exception as e:
            logger.error(f"Error stopping animation: {e}")
            
        # クリーンアップ
        self.active_animations.pop(channel_id, None)
        self.frame_counters.pop(channel_id, None)
        
        logger.info(f"Stopped animation in channel {channel_id}")
        
    async def _animation_loop(self, channel_id: int, 
                            message: discord.Message,
                            context_message: str = None) -> None:
        """
        アニメーションループ処理
        
        Args:
            channel_id: チャンネルID
            message: 更新するメッセージ
            context_message: コンテキストメッセージ
        """
        try:
            while True:
                await asyncio.sleep(self.UPDATE_INTERVAL)
                
                # フレームインデックスを更新
                self.frame_counters[channel_id] = (
                    self.frame_counters[channel_id] + 1
                ) % len(self.SPINNER_FRAMES)
                
                frame_index = self.frame_counters[channel_id]
                
                # Embedを更新
                embed = self._create_animation_embed(frame_index, context_message)
                await message.edit(embed=embed)
                
        except asyncio.CancelledError:
            # 正常なキャンセル
            pass
        except discord.errors.NotFound:
            # メッセージが削除された
            pass
        except Exception as e:
            logger.error(f"Animation loop error: {e}")
            
    def _create_animation_embed(self, frame_index: int, 
                               context_message: str = None) -> discord.Embed:
        """
        アニメーション用Embedを作成
        
        Args:
            frame_index: 現在のフレームインデックス
            context_message: コンテキストメッセージ
            
        Returns:
            Discord Embed
        """
        spinner = self.SPINNER_FRAMES[frame_index % len(self.SPINNER_FRAMES)]
        status_index = (frame_index // len(self.SPINNER_FRAMES)) % len(self.STATUS_MESSAGES)
        status = self.STATUS_MESSAGES[status_index]
        
        # タイトルにスピナーとステータスを組み合わせ
        title = f"{spinner} {status}..."
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue(),
            description=context_message if context_message else "しばらくお待ちください"
        )
        
        # 経過時間を表示（オプション）
        if frame_index > 0:
            elapsed = frame_index * self.UPDATE_INTERVAL
            embed.set_footer(text=f"経過時間: {elapsed:.0f}秒")
        
        return embed
        
    def _create_final_embed(self, message: str, success: bool) -> discord.Embed:
        """
        最終状態用Embedを作成
        
        Args:
            message: 表示メッセージ
            success: 成功フラグ
            
        Returns:
            Discord Embed
        """
        if success:
            title = "✅ 処理完了"
            color = discord.Color.green()
        else:
            title = "❌ エラー"
            color = discord.Color.red()
            
        embed = discord.Embed(
            title=title,
            description=message,
            color=color
        )
        
        return embed
        
    def is_animating(self, channel_id: int) -> bool:
        """
        指定チャンネルでアニメーション中か確認
        
        Args:
            channel_id: チャンネルID
            
        Returns:
            アニメーション中ならTrue
        """
        return channel_id in self.active_animations
        
    async def cleanup_all(self) -> None:
        """
        全てのアニメーションを停止してクリーンアップ
        """
        channel_ids = list(self.active_animations.keys())
        for channel_id in channel_ids:
            await self.stop_animation(channel_id)
            
        logger.info("Cleaned up all animations")


# シングルトンインスタンス
_animator_instance = None


def get_animator() -> ProcessingAnimator:
    """
    アニメーターのシングルトンインスタンスを取得
    
    Returns:
        ProcessingAnimator インスタンス
    """
    global _animator_instance
    if _animator_instance is None:
        _animator_instance = ProcessingAnimator()
    return _animator_instance