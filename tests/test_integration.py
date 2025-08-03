#!/usr/bin/env python3
"""
統合テスト - エンドツーエンドのワークフローテスト

このテストは以下を検証：
1. !ideaから!completeチェーンの完全なフロー
2. ファイル作成の各ステージ
3. Git操作とGitHubリポジトリ作成
4. エラーリカバリーテスト
"""

import sys
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest
import discord

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import SettingsManager
from src.discord_bot import ClaudeCLIBot, create_bot_commands
from src.session_manager import get_session_manager
from src.project_manager import ProjectManager
from src.claude_context_manager import ClaudeContextManager
from src.channel_validator import ChannelValidator
from src.command_manager import CommandManager


class TestIntegration:
    """統合テストクラス"""
    
    @pytest.fixture
    def mock_bot(self):
        """テスト用のBotインスタンス"""
        # 設定マネージャーのモック
        settings = Mock(spec=SettingsManager)
        settings.get_claude_options = Mock(return_value="--no-interaction")
        settings.get_token = Mock(return_value="test_token")
        
        # Botインスタンス作成
        bot = ClaudeCLIBot(settings)
        
        # コマンド登録
        create_bot_commands(bot, settings)
        
        yield bot
        
        # クリーンアップ
        session_manager = get_session_manager()
        session_manager.clear_all()
    
    @pytest.fixture
    def mock_guild(self):
        """モックGuildオブジェクト"""
        guild = Mock(spec=discord.Guild)
        guild.name = "Test Guild"
        guild.id = 123456
        
        # チャンネルの作成
        channels = []
        for i, name in enumerate(["1-idea", "2-requirements", "3-design", "4-tasks", "5-development"]):
            channel = Mock(spec=discord.TextChannel)
            channel.name = name
            channel.id = 1000 + i
            channel.send = AsyncMock()
            channel.mention = f"#{name}"
            channels.append(channel)
        
        guild.channels = channels
        guild.text_channels = channels
        
        # ロールの作成
        bot_role = Mock(spec=discord.Role)
        bot_role.name = "TestBot"
        
        guild.me = Mock()
        guild.me.roles = [bot_role]
        
        return guild
    
    @pytest.fixture
    def temp_workspace(self):
        """一時的な作業ディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_bot, mock_guild, temp_workspace):
        """!ideaから!completeチェーンの完全なフローテスト"""
        # プロジェクトディレクトリの設定
        mock_bot.project_manager.achi_kun_root = temp_workspace
        mock_bot.project_manager.projects_dir = temp_workspace / "projects"
        mock_bot.project_manager.projects_dir.mkdir(parents=True)
        
        # 1. !ideaコマンドのテスト
        # コンテキストのモック
        idea_ctx = Mock()
        idea_ctx.send = AsyncMock()
        idea_ctx.guild = mock_guild
        idea_ctx.channel = mock_guild.channels[0]  # #1-idea
        
        # 返信メッセージのモック
        parent_msg = Mock()
        parent_msg.content = "素晴らしいアプリケーションのアイデアです！"
        parent_msg.reference = None
        parent_msg.author = Mock(name="TestUser")
        parent_msg.created_at = Mock(strftime=Mock(return_value="2024-01-01 00:00:00"))
        parent_msg.channel = idea_ctx.channel
        idea_ctx.message = Mock()
        idea_ctx.message.reference = Mock(message_id=12345)
        idea_ctx.channel.fetch_message = AsyncMock(return_value=parent_msg)
        
        # スレッド作成のモック
        thread = Mock()
        thread.id = "thread-idea-123"
        thread.name = "test-app"
        thread.send = AsyncMock()
        thread.join = AsyncMock()
        parent_msg.create_thread = AsyncMock(return_value=thread)
        idea_ctx.channel.create_thread = AsyncMock(return_value=thread)
        
        # Claude Codeセッション開始のモック
        with patch.object(mock_bot, '_start_claude_session_with_context', new_callable=AsyncMock):
            with patch('subprocess.run'):
                await mock_bot.handle_idea_command(idea_ctx, "test-app")
        
        # 検証: プロジェクトディレクトリが作成されたか
        project_path = mock_bot.project_manager.get_project_path("test-app")
        assert project_path.exists()
        assert (project_path / "idea.md").exists()
        
        # 検証: セッションが登録されたか
        session_manager = get_session_manager()
        # thread.idはMockオブジェクトなので、str()で文字列に変換される
        thread_id = str(thread.id)
        assert session_manager.get_idea_name_by_thread(thread_id) == "test-app"
        
        # 2. !completeコマンド（idea → requirements）のテスト
        complete_ctx1 = Mock()
        complete_ctx1.send = AsyncMock()
        complete_ctx1.guild = mock_guild
        complete_ctx1.channel = thread
        complete_ctx1.channel.parent = mock_guild.channels[0]  # #1-idea
        
        # 次チャンネルのメッセージとスレッド作成
        req_message = Mock()
        req_thread = Mock()
        req_thread.id = "thread-req-123"
        req_thread.name = "test-app"
        req_thread.send = AsyncMock()
        req_message.create_thread = AsyncMock(return_value=req_thread)
        mock_guild.channels[1].send = AsyncMock(return_value=req_message)
        
        # Git操作のモック
        with patch.object(mock_bot.project_manager, 'init_git_repository', new_callable=AsyncMock) as mock_git_init:
            mock_git_init.return_value = (True, "Initialized")
            
            with patch.object(mock_bot.project_manager, 'execute_git_command', new_callable=AsyncMock) as mock_git_cmd:
                mock_git_cmd.return_value = (True, "Success")
                
                with patch.object(mock_bot, '_start_claude_session', new_callable=AsyncMock):
                    with patch('subprocess.run'):
                        await mock_bot.command_manager.process_complete_command(complete_ctx1)
        
        # 検証: requirements.mdが作成されたか
        assert (project_path / "requirements.md").exists()
        
        # 3. 全ステージを通した検証
        stages = [
            ("requirements", "design", mock_guild.channels[2]),
            ("design", "tasks", mock_guild.channels[3]),
            ("tasks", "development", mock_guild.channels[4])
        ]
        
        for current_stage, next_stage, next_channel in stages:
            # コンテキストの準備
            ctx = Mock()
            ctx.send = AsyncMock()
            ctx.guild = mock_guild
            ctx.channel = Mock()
            ctx.channel.name = "test-app"
            ctx.channel.parent = Mock()
            ctx.channel.parent.name = f"{stages.index((current_stage, next_stage, next_channel)) + 2}-{current_stage}"
            
            # メッセージとスレッドのモック
            msg = Mock()
            thread = Mock()
            thread.id = f"thread-{next_stage}-123"
            thread.name = "test-app"
            thread.send = AsyncMock()
            msg.create_thread = AsyncMock(return_value=thread)
            next_channel.send = AsyncMock(return_value=msg)
            
            # tasksステージの場合はGitHub操作も含める
            if current_stage == "tasks":
                # 開発ディレクトリのコピー
                with patch.object(mock_bot.project_manager, 'copy_to_development') as mock_copy:
                    dev_path = temp_workspace / "test-app"
                    dev_path.mkdir(parents=True)
                    mock_copy.return_value = dev_path
                    
                    # GitHub操作のモック
                    with patch.object(mock_bot.command_manager, '_run_command', new_callable=AsyncMock) as mock_run:
                        mock_run.return_value = (True, "Repository created")
                        
                        with patch.object(mock_bot.command_manager, '_get_github_user', new_callable=AsyncMock) as mock_user:
                            mock_user.return_value = "testuser"
                            
                            with patch.object(mock_bot.project_manager, 'execute_git_command', new_callable=AsyncMock) as mock_git:
                                mock_git.return_value = (True, "Success")
                                
                                with patch('subprocess.run'):
                                    await mock_bot.command_manager.process_complete_command(ctx)
            else:
                # 通常のステージ
                with patch.object(mock_bot.project_manager, 'execute_git_command', new_callable=AsyncMock) as mock_git:
                    mock_git.return_value = (True, "Success")
                    
                    with patch.object(mock_bot, '_start_claude_session', new_callable=AsyncMock):
                        with patch('subprocess.run'):
                            await mock_bot.command_manager.process_complete_command(ctx)
            
            # 検証: ドキュメントファイルが作成されたか
            if current_stage != "tasks":
                assert (project_path / f"{next_stage}.md").exists()
    
    @pytest.mark.asyncio
    async def test_error_recovery_existing_project(self, mock_bot, temp_workspace):
        """既存プロジェクトのエラーリカバリーテスト"""
        # 既存プロジェクトの作成
        mock_bot.project_manager.achi_kun_root = temp_workspace
        mock_bot.project_manager.projects_dir = temp_workspace / "projects"
        mock_bot.project_manager.projects_dir.mkdir(parents=True)
        
        existing_project = mock_bot.project_manager.projects_dir / "existing-app"
        existing_project.mkdir()
        
        # コンテキストのモック
        ctx = Mock()
        ctx.send = AsyncMock()
        ctx.message = Mock()
        ctx.message.reference = Mock(message_id=12345)
        
        # スレッドのモック
        thread = Mock()
        thread.send = AsyncMock()
        thread.join = AsyncMock()
        thread.id = "test-thread-123"
        
        # 親メッセージのモック
        parent_msg = Mock()
        parent_msg.content = "Test idea"
        parent_msg.create_thread = AsyncMock(return_value=thread)
        
        ctx.channel = Mock()
        ctx.channel.fetch_message = AsyncMock(return_value=parent_msg)
        
        # !ideaコマンド実行
        await mock_bot.handle_idea_command(ctx, "existing-app")
        
        # 検証: エラーメッセージがスレッドに送信されたか
        thread.send.assert_called()
        error_msg = thread.send.call_args[0][0]
        assert "既に存在します" in error_msg
    
    @pytest.mark.asyncio
    async def test_error_recovery_git_failure(self, mock_bot, mock_guild, temp_workspace):
        """Git操作失敗のエラーリカバリーテスト"""
        # プロジェクトの準備
        mock_bot.project_manager.achi_kun_root = temp_workspace
        mock_bot.project_manager.projects_dir = temp_workspace / "projects"
        mock_bot.project_manager.projects_dir.mkdir(parents=True)
        
        project_path = mock_bot.project_manager.get_project_path("git-fail-app")
        project_path.mkdir(parents=True)
        
        # コンテキストのモック
        ctx = Mock()
        ctx.send = AsyncMock()
        ctx.guild = mock_guild
        ctx.channel = Mock()
        ctx.channel.name = "git-fail-app"
        ctx.channel.parent = mock_guild.channels[0]
        
        # Git初期化失敗のモック
        with patch.object(mock_bot.project_manager, 'init_git_repository', new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (False, "Permission denied")
            
            await mock_bot.command_manager.process_complete_command(ctx)
        
        # 検証: エラーメッセージが送信されたか
        loading_msg = ctx.send.return_value
        loading_msg.edit.assert_called()
        error_msg = loading_msg.edit.call_args[1]["content"]
        assert "Git初期化エラー" in error_msg
        assert "Permission denied" in error_msg
    
    @pytest.mark.asyncio
    async def test_channel_validation(self, mock_bot):
        """チャンネル検証のテスト"""
        # 不完全なギルドのモック（チャンネルが不足）
        incomplete_guild = Mock(spec=discord.Guild)
        incomplete_guild.name = "Incomplete Guild"
        
        # チャンネルのモックを正しく作成
        channel1 = Mock(spec=discord.TextChannel)
        channel1.name = "1-idea"
        channel2 = Mock(spec=discord.TextChannel)
        channel2.name = "2-requirements"
        
        incomplete_guild.channels = [channel1, channel2]
        incomplete_guild.text_channels = incomplete_guild.channels
        
        bot_role = Mock()
        bot_role.name = "TestBot"
        incomplete_guild.me = Mock()
        incomplete_guild.me.roles = [bot_role]
        
        # チャンネル検証
        result = await mock_bot.channel_validator.check_bot_setup(incomplete_guild)
        
        # 検証: 不足チャンネルが検出されたか
        assert not result["is_valid"]
        assert len(result["errors"]) > 0
        
        # チャンネルステータスを確認
        channel_status = result["channel_status"]
        assert not channel_status["3-design"]["found"]
        assert not channel_status["4-tasks"]["found"]
        assert not channel_status["5-development"]["found"]
        assert channel_status["1-idea"]["found"]
        assert channel_status["2-requirements"]["found"]
    
    @pytest.mark.asyncio
    async def test_invalid_command_inputs(self, mock_bot):
        """無効なコマンド入力のテスト"""
        # 1. !ideaコマンドでアイデア名なし
        ctx = Mock()
        ctx.send = AsyncMock()
        
        # コマンドハンドラーを直接呼び出し
        idea_cmd = None
        for cmd in mock_bot.commands:
            if cmd.name == "idea":
                idea_cmd = cmd
                break
        
        if idea_cmd:
            await idea_cmd.callback(ctx, None)
            ctx.send.assert_called_with("❌ アイデア名を指定してください。使用方法: `!idea <idea-name>`")
        
        # 2. !completeコマンドをスレッド外で実行
        ctx2 = Mock()
        ctx2.send = AsyncMock()
        ctx2.channel = Mock()
        ctx2.channel.parent = None  # スレッドではない
        
        await mock_bot.command_manager.process_complete_command(ctx2)
        ctx2.send.assert_called_with("❌ このコマンドはスレッド内でのみ使用可能です")
    
    @pytest.mark.asyncio
    async def test_concurrent_projects(self, mock_bot, mock_guild, temp_workspace):
        """複数プロジェクトの同時処理テスト"""
        mock_bot.project_manager.achi_kun_root = temp_workspace
        mock_bot.project_manager.projects_dir = temp_workspace / "projects"
        mock_bot.project_manager.projects_dir.mkdir(parents=True)
        
        projects = ["project-a", "project-b", "project-c"]
        contexts = []
        
        for i, project_name in enumerate(projects):
            ctx = Mock()
            ctx.send = AsyncMock()
            ctx.guild = mock_guild
            ctx.channel = mock_guild.channels[0]
            ctx.message = Mock()
            ctx.message.reference = Mock(resolved=Mock(content=f"Idea for {project_name}"))
            
            thread = Mock()
            thread.id = f"thread-{project_name}"
            thread.name = project_name
            thread.send = AsyncMock()
            ctx.channel.create_thread = AsyncMock(return_value=thread)
            
            contexts.append((ctx, project_name))
        
        # 並行してプロジェクト作成
        with patch.object(mock_bot, '_start_claude_session', new_callable=AsyncMock):
            with patch('subprocess.run'):
                tasks = [mock_bot.handle_idea_command(ctx, name) for ctx, name in contexts]
                await asyncio.gather(*tasks)
        
        # 検証: すべてのプロジェクトが作成されたか
        for project_name in projects:
            project_path = mock_bot.project_manager.get_project_path(project_name)
            assert project_path.exists()
            assert (project_path / "idea.md").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])