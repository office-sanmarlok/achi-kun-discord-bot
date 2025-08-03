#!/usr/bin/env python3
"""
Discord.pyのスレッド機能調査用テストスクリプト
"""

import discord
from discord.ext import commands
import asyncio
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intents設定
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # on_thread_createイベントに必要

class ThreadTestBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
    
    async def on_ready(self):
        logger.info(f'Bot起動完了: {self.user}')
        logger.info(f'Intents: {self.intents}')
    
    async def on_thread_create(self, thread):
        """新規スレッド作成時のイベント"""
        logger.info(f'=== スレッド作成検出 ===')
        logger.info(f'スレッド名: {thread.name}')
        logger.info(f'スレッドID: {thread.id}')
        logger.info(f'親チャンネルID: {thread.parent_id}')
        logger.info(f'スレッドタイプ: {thread.type}')
        logger.info(f'アーカイブ済み: {thread.archived}')
        logger.info(f'ロック済み: {thread.locked}')
        
        # スレッドの親メッセージ（スターターメッセージ）を取得
        try:
            # スレッドIDと親メッセージIDは同じ
            parent_message = await thread.parent.fetch_message(thread.id)
            logger.info(f'親メッセージ取得成功:')
            logger.info(f'  内容: {parent_message.content}')
            logger.info(f'  作成者: {parent_message.author}')
            logger.info(f'  作成日時: {parent_message.created_at}')
        except discord.NotFound:
            logger.warning(f'親メッセージが見つかりません（ID: {thread.id}）')
        except discord.Forbidden:
            logger.warning(f'親メッセージへのアクセス権限がありません')
        except Exception as e:
            logger.error(f'親メッセージ取得エラー: {e}')
        
        # スレッドに参加
        try:
            await thread.join()
            logger.info('スレッドに参加しました')
        except Exception as e:
            logger.error(f'スレッド参加エラー: {e}')
    
    async def on_message(self, message):
        """メッセージ受信時のイベント"""
        if message.author == self.user:
            return
        
        # スレッド内のメッセージかチェック
        if isinstance(message.channel, discord.Thread):
            logger.info(f'=== スレッド内メッセージ受信 ===')
            logger.info(f'スレッド名: {message.channel.name}')
            logger.info(f'メッセージ: {message.content}')
            logger.info(f'作成者: {message.author}')
            
            # 親チャンネルの情報
            parent = message.channel.parent
            logger.info(f'親チャンネル: {parent.name if parent else "不明"}')
            
            # スレッドの権限チェック
            perms = message.channel.permissions_for(message.guild.me)
            logger.info(f'Bot権限:')
            logger.info(f'  読み取り: {perms.read_messages}')
            logger.info(f'  送信: {perms.send_messages}')
            logger.info(f'  スレッド管理: {perms.manage_threads}')
        
        await self.process_commands(message)

async def test_thread_features():
    """スレッド機能のテスト実行"""
    bot = ThreadTestBot()
    
    @bot.command()
    async def thread_info(ctx, thread_id: int = None):
        """スレッド情報を取得するコマンド"""
        if thread_id:
            try:
                thread = bot.get_channel(thread_id)
                if isinstance(thread, discord.Thread):
                    embed = discord.Embed(
                        title=f"スレッド情報: {thread.name}",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="ID", value=thread.id, inline=True)
                    embed.add_field(name="親チャンネル", value=thread.parent.name, inline=True)
                    embed.add_field(name="メンバー数", value=thread.member_count, inline=True)
                    embed.add_field(name="アーカイブ済み", value=thread.archived, inline=True)
                    embed.add_field(name="ロック済み", value=thread.locked, inline=True)
                    
                    # 親メッセージの取得を試みる
                    try:
                        starter_msg = await thread.parent.fetch_message(thread.id)
                        embed.add_field(
                            name="スターターメッセージ",
                            value=f"{starter_msg.content[:100]}..." if len(starter_msg.content) > 100 else starter_msg.content,
                            inline=False
                        )
                        embed.add_field(name="作成者", value=starter_msg.author.mention, inline=True)
                    except:
                        embed.add_field(name="スターターメッセージ", value="取得できません", inline=False)
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("指定されたIDはスレッドではありません")
            except Exception as e:
                await ctx.send(f"エラー: {e}")
        else:
            await ctx.send("使用方法: !thread_info <スレッドID>")
    
    @bot.command()
    async def list_threads(ctx):
        """アクティブなスレッドをリスト表示"""
        threads = []
        for thread in ctx.guild.threads:
            threads.append(f"- {thread.name} (ID: {thread.id}, 親: {thread.parent.name})")
        
        if threads:
            embed = discord.Embed(
                title="アクティブなスレッド一覧",
                description="\\n".join(threads[:10]),  # 最大10個まで表示
                color=discord.Color.green()
            )
            if len(threads) > 10:
                embed.set_footer(text=f"他 {len(threads) - 10} 個のスレッド")
            await ctx.send(embed=embed)
        else:
            await ctx.send("アクティブなスレッドはありません")
    
    # テスト用のトークンを設定してください
    # await bot.start('YOUR_BOT_TOKEN')
    
    return bot

if __name__ == "__main__":
    # テスト実行
    print("Discord.py スレッド機能テストスクリプト")
    print("使用方法:")
    print("1. このファイルの最後にあるbot.start()のコメントを外してトークンを設定")
    print("2. python test_thread_features.py で実行")
    print("\nテスト内容:")
    print("- on_thread_createイベントの動作確認")
    print("- スレッドの親メッセージ取得")
    print("- スレッド権限の確認")
    print("- !thread_info <ID> コマンドでスレッド情報表示")
    print("- !list_threads コマンドでアクティブスレッド一覧表示")