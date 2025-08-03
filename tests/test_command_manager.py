#!/usr/bin/env python3
"""
CommandManagerのユニットテスト
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
import discord

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.command_manager import CommandManager


class TestCommandManager:
    """CommandManagerのテストクラス"""
    
    @pytest.fixture
    def mock_bot(self):
        """モックBotオブジェクト"""
        bot = Mock()
        
        # ProjectManager mock
        bot.project_manager = Mock()
        bot.project_manager.get_project_path = Mock(return_value=Path("/projects/test-app"))
        bot.project_manager.achi_kun_root = Path("/achi-kun")
        bot.project_manager.init_git_repository = AsyncMock(return_value=(True, "Initialized"))
        bot.project_manager.execute_git_command = AsyncMock(return_value=(True, "Success"))
        bot.project_manager.copy_to_development = Mock(return_value=Path("/achi-kun/test-app"))
        bot.project_manager.copy_github_workflows = Mock()
        
        # ContextManager mock
        bot.context_manager = Mock()
        bot.context_manager.get_stage_from_channel = Mock(return_value="idea")
        bot.context_manager.format_complete_message = Mock(return_value="Test message")
        bot.context_manager.generate_requirements_prompt = Mock(return_value="Requirements prompt")
        bot.context_manager.generate_design_prompt = Mock(return_value="Design prompt")
        bot.context_manager.generate_tasks_prompt = Mock(return_value="Tasks prompt")
        bot.context_manager.generate_development_prompt = Mock(return_value="Development prompt")
        
        # ChannelValidator mock
        bot.channel_validator = Mock()
        bot.channel_validator.get_required_channel = Mock()
        
        # Claude session start mock
        bot._start_claude_session = AsyncMock()
        
        return bot
    
    @pytest.fixture
    def mock_settings(self):
        """モックSettingsオブジェクト"""
        settings = Mock()
        settings.get_claude_options = Mock(return_value="--no-interaction")
        return settings
    
    @pytest.fixture
    def command_manager(self, mock_bot, mock_settings):
        """テスト用CommandManager"""
        return CommandManager(mock_bot, mock_settings)
    
    @pytest.fixture
    def mock_ctx(self):
        """モックDiscordコンテキスト"""
        ctx = Mock()
        ctx.send = AsyncMock()
        
        # チャンネル設定（スレッド内）
        ctx.channel = Mock()
        ctx.channel.name = "test-app"
        ctx.channel.parent = Mock()
        ctx.channel.parent.name = "1-idea"
        
        # Guild設定
        ctx.guild = Mock()
        
        return ctx
    
    @pytest.mark.asyncio
    async def test_process_complete_command_not_in_thread(self, command_manager):
        """スレッド外での!completeコマンドテスト"""
        ctx = Mock()
        ctx.send = AsyncMock()
        ctx.channel = Mock()
        ctx.channel.parent = None  # スレッドではない
        
        await command_manager.process_complete_command(ctx)
        
        ctx.send.assert_called_once_with("❌ このコマンドはスレッド内でのみ使用可能です")
    
    @pytest.mark.asyncio
    async def test_process_complete_command_development_channel(self, command_manager, mock_ctx):
        """開発チャンネルでの!completeコマンドテスト"""
        mock_ctx.channel.parent.name = "5-development"
        command_manager.bot.context_manager.get_stage_from_channel.return_value = "development"
        
        await command_manager.process_complete_command(mock_ctx)
        
        mock_ctx.send.assert_called_once_with("❌ このチャンネルでは!completeコマンドを使用できません")
    
    @pytest.mark.asyncio
    async def test_process_complete_command_valid_channel(self, command_manager, mock_ctx):
        """有効なチャンネルでの!completeコマンドテスト"""
        # workflow_channelsに登録されているハンドラーを直接モック
        mock_handler = AsyncMock()
        
        # workflow_channelsの"1-idea"エントリを上書き
        command_manager.workflow_channels["1-idea"] = mock_handler
        
        await command_manager.process_complete_command(mock_ctx)
        
        mock_handler.assert_called_once_with(mock_ctx)
    
    @pytest.mark.asyncio
    async def test_handle_idea_complete_success(self, command_manager, mock_ctx):
        """#1-ideaでの!complete成功テスト"""
        # プロジェクトパス設定
        project_path = Mock(spec=Path)
        project_path.__str__ = Mock(return_value="/projects/test-app")
        project_path.exists = Mock(return_value=True)
        project_path.__truediv__ = Mock(side_effect=lambda x: Mock(exists=Mock(return_value=False)) if x == ".git" else Mock())
        command_manager.bot.project_manager.get_project_path.return_value = project_path
        
        # 次チャンネル設定
        next_channel = Mock()
        next_channel.send = AsyncMock()
        next_channel.mention = "#2-requirements"
        command_manager.bot.channel_validator.get_required_channel.return_value = next_channel
        
        # メッセージとスレッド作成
        message = Mock()
        thread = Mock()
        thread.id = "thread123"
        thread.send = AsyncMock()
        message.create_thread = AsyncMock(return_value=thread)
        next_channel.send.return_value = message
        
        # セッション設定モック
        with patch.object(command_manager, '_setup_next_stage_session', new_callable=AsyncMock):
            await command_manager.handle_idea_complete(mock_ctx)
        
        # 検証
        assert mock_ctx.send.call_count == 1  # loading message
        loading_msg = mock_ctx.send.return_value
        loading_msg.edit.assert_called_with(
            content="✅ idea フェーズが完了しました！\n次フェーズ: #2-requirements"
        )
        
        # Git初期化の確認
        command_manager.bot.project_manager.init_git_repository.assert_called_once()
        
        # Git操作の確認
        assert command_manager.bot.project_manager.execute_git_command.call_count == 3
    
    @pytest.mark.asyncio
    async def test_handle_idea_complete_project_not_found(self, command_manager, mock_ctx):
        """プロジェクトが見つからない場合のテスト"""
        project_path = Mock(spec=Path)
        project_path.exists = Mock(return_value=False)
        command_manager.bot.project_manager.get_project_path.return_value = project_path
        
        await command_manager.handle_idea_complete(mock_ctx)
        
        loading_msg = mock_ctx.send.return_value
        loading_msg.edit.assert_called_with(content="❌ プロジェクト `test-app` が見つかりません")
    
    @pytest.mark.asyncio
    async def test_handle_tasks_complete_with_github(self, command_manager, mock_ctx):
        """#4-tasksでの!complete（GitHub作成含む）テスト"""
        mock_ctx.channel.parent.name = "4-tasks"
        
        # プロジェクトパス設定
        project_path = Path("/projects/test-app")
        dev_path = Path("/achi-kun/test-app")
        command_manager.bot.project_manager.get_project_path.return_value = project_path
        command_manager.bot.project_manager.copy_to_development.return_value = dev_path
        
        # GitHubコマンドモック
        with patch.object(command_manager, '_run_command', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (True, "Repository created")
            
            with patch.object(command_manager, '_get_github_user', new_callable=AsyncMock) as mock_user:
                mock_user.return_value = "testuser"
                
                # 次チャンネル設定
                next_channel = Mock()
                next_channel.send = AsyncMock()
                next_channel.mention = "#5-development"
                command_manager.bot.channel_validator.get_required_channel.return_value = next_channel
                
                # メッセージとスレッド作成
                message = Mock()
                thread = Mock()
                thread.id = "thread456"
                thread.send = AsyncMock()
                message.create_thread = AsyncMock(return_value=thread)
                next_channel.send.return_value = message
                
                # セッション設定モック
                with patch.object(command_manager, '_setup_development_session', new_callable=AsyncMock):
                    await command_manager.handle_tasks_complete(mock_ctx)
                
                # GitHub作成コマンドの確認
                mock_run.assert_called_with(
                    ["gh", "repo", "create", "test-app", "--public", "-y"],
                    cwd=str(dev_path)
                )
                
                # 成功メッセージの確認
                loading_msg = mock_ctx.send.return_value
                loading_msg.edit.assert_called_with(
                    content="✅ tasks フェーズが完了しました！\n"
                            "🚀 GitHubリポジトリ: https://github.com/testuser/test-app\n"
                            "次フェーズ: #5-development"
                )
    
    @pytest.mark.asyncio
    async def test_run_command_success(self, command_manager):
        """コマンド実行成功テスト"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # プロセスモック
            process = Mock()
            process.returncode = 0
            process.communicate = AsyncMock(return_value=(b"Success output", b""))
            mock_subprocess.return_value = process
            
            success, output = await command_manager._run_command(["echo", "test"])
            
            assert success is True
            assert output == "Success output"
    
    @pytest.mark.asyncio
    async def test_run_command_failure(self, command_manager):
        """コマンド実行失敗テスト"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # プロセスモック
            process = Mock()
            process.returncode = 1
            process.communicate = AsyncMock(return_value=(b"", b"Error output"))
            mock_subprocess.return_value = process
            
            success, output = await command_manager._run_command(["false"])
            
            assert success is False
            assert output == "Error output"
    
    @pytest.mark.asyncio
    async def test_setup_next_stage_session(self, command_manager):
        """次ステージセッション設定テスト"""
        thread = Mock()
        thread.id = "thread789"
        thread.name = "test-app"
        thread.send = AsyncMock()
        
        project_path = Path("/projects/test-app")
        
        # session_managerモック
        with patch('src.session_manager.get_session_manager') as mock_get_sm:
            session_manager = Mock()
            session_manager.get_or_create_session = Mock(return_value=1)
            session_manager.create_session_info = Mock()
            session_manager.update_project_stage = Mock()
            session_manager.add_thread_to_workflow = Mock()
            session_manager.add_project_document = Mock()
            mock_get_sm.return_value = session_manager
            
            # subprocessモック
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)
                
                # Pathオブジェクトのモック
                mock_doc_file = Mock()
                mock_doc_file.touch = Mock()
                
                with patch.object(Path, '__truediv__', return_value=mock_doc_file):
                    await command_manager._setup_next_stage_session(
                        thread, "test-app", "requirements", project_path
                    )
                
                # セッション作成の確認
                session_manager.get_or_create_session.assert_called_once_with("thread789")
                session_manager.create_session_info.assert_called_once()
                
                # ワークフロー更新の確認
                session_manager.update_project_stage.assert_called_with("test-app", "requirements")
                session_manager.add_thread_to_workflow.assert_called_with(
                    "test-app", "r-requirements", "thread789"
                )
                
                # ドキュメント作成の確認
                session_manager.add_project_document.assert_called_with(
                    "test-app", "requirements", mock_doc_file
                )
                
                # Claude Code開始の確認
                command_manager.bot._start_claude_session.assert_called_once_with(1, "test-app")
                
                # プロンプト送信の確認
                mock_run.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])