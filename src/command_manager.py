#!/usr/bin/env python3
"""
Command Manager - !completeコマンドのワークフロー管理

このモジュールは以下の責務を持つ：
1. チャンネル固有の処理ロジック
2. ワークフロー状態の管理
3. Git操作の実行
4. 次ステージへの遷移
"""

import asyncio
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import discord

from src.prompt_sender import get_prompt_sender

logger = logging.getLogger(__name__)


class CommandManager:
    """!completeコマンドのワークフローを管理するクラス"""
    
    def __init__(self, bot, settings):
        """
        初期化
        
        Args:
            bot: ClaudeCLIBotインスタンス
            settings: SettingsManagerインスタンス
        """
        self.bot = bot
        self.settings = settings
        self.prompt_sender = get_prompt_sender(flask_port=settings.get_port('flask'))
        
        # チャンネル別ハンドラーのマッピング
        self.workflow_channels = {
            "1-idea": self.handle_idea_complete,
            "2-requirements": self.handle_requirements_complete,
            "3-design": self.handle_design_complete,
            "4-tasks": self.handle_tasks_complete
        }
    
    async def process_complete_command(self, ctx) -> None:
        """
        !completeコマンドの処理を振り分け
        
        Args:
            ctx: Discordコマンドコンテキスト
        """
        # スレッド内での実行確認
        if not hasattr(ctx.channel, 'parent') or ctx.channel.parent is None:
            await ctx.send("❌ このコマンドはスレッド内でのみ使用可能です")
            return
        
        # チャンネル名からステージを判定
        channel_name = ctx.channel.parent.name
        stage = self.bot.context_manager.get_stage_from_channel(channel_name)
        
        if not stage or stage == "development":
            await ctx.send("❌ このチャンネルでは!completeコマンドを使用できません")
            return
        
        # 対応するハンドラーを実行
        handler = None
        for key, func in self.workflow_channels.items():
            if key in channel_name:
                handler = func
                break
        
        if handler:
            await handler(ctx)
        else:
            await ctx.send("❌ 処理可能なワークフローチャンネルが見つかりません")
    
    async def handle_idea_complete(self, ctx) -> None:
        """#1-ideaでの!complete処理"""
        thread_name = ctx.channel.name  # スレッド名 = idea-name
        
        # 進捗メッセージ
        loading_msg = await ctx.send("`...` 処理中...")
        
        try:
            # プロジェクトパスを取得
            project_path = self.bot.project_manager.get_project_path(thread_name)
            if not project_path.exists():
                await loading_msg.edit(content=f"❌ プロジェクト `{thread_name}` が見つかりません")
                return
            
            # projectsディレクトリのGitリポジトリ初期化（必要な場合）
            projects_root = self.bot.project_manager.projects_root
            if not (projects_root / ".git").exists():
                success, output = await self.bot.project_manager.init_git_repository(projects_root)
                if not success:
                    await loading_msg.edit(content=f"❌ Git初期化エラー:\n```\n{output}\n```")
                    return
                
                # 初回の場合、リモートリポジトリを設定
                await loading_msg.edit(content="`...` プロジェクトリポジトリを設定中...")
                await self._setup_projects_remote(projects_root, loading_msg)
            
            # Git操作の実行（projectsディレクトリで実行）
            git_commands = [
                ["git", "add", f"{thread_name}/*"],
                ["git", "commit", "-m", f"[{thread_name}] Complete idea phase"]
            ]
            
            # リモートが設定されている場合のみpush
            has_remote = await self._check_git_remote(projects_root)
            if has_remote:
                git_commands.append(["git", "push"])
            
            for cmd in git_commands:
                success, output = await self.bot.project_manager.execute_git_command(projects_root, cmd)
                if not success:
                    # pushエラーの場合は警告のみ（リモートがない可能性）
                    if cmd[1] == "push":
                        logger.warning(f"Git push failed (may not have remote): {output}")
                    # commitエラーで「nothing to commit」の場合は警告のみ
                    elif cmd[1] == "commit" and "nothing to commit" in output.lower():
                        logger.info("Nothing to commit, continuing...")
                        await loading_msg.edit(content="`...` コミットする変更がありません。次のステップに進みます...")
                        break  # commitがスキップされたらpushもスキップ
                    else:
                        error_detail = output if output else f"Command failed: {' '.join(cmd)}"
                        await loading_msg.edit(content=f"❌ Gitエラー:\n```\n{error_detail}\n```")
                        return
            
            # 次チャンネルへの投稿
            next_message = self.bot.context_manager.format_complete_message("idea", thread_name)
            next_channel = self.bot.channel_validator.get_required_channel(ctx.guild, "requirements")
            
            if not next_channel:
                await loading_msg.edit(content="❌ #2-requirementsチャンネルが見つかりません")
                return
            
            # メッセージ投稿とスレッド作成
            message = await next_channel.send(next_message)
            thread = await message.create_thread(name=thread_name)
            
            # セッション管理の更新
            await self._setup_next_stage_session(
                thread, thread_name, "requirements", project_path
            )
            
            # 成功メッセージ
            await loading_msg.edit(content=f"✅ idea フェーズが完了しました！\n次フェーズ: {next_channel.mention}")
            
        except Exception as e:
            logger.error(f"Error in handle_idea_complete: {e}", exc_info=True)
            await loading_msg.edit(content=f"❌ エラーが発生しました: {str(e)[:100]}")
    
    async def handle_requirements_complete(self, ctx) -> None:
        """#2-requirementsでの!complete処理"""
        thread_name = ctx.channel.name
        
        loading_msg = await ctx.send("`...` 処理中...")
        
        try:
            # プロジェクトパスを取得
            project_path = self.bot.project_manager.get_project_path(thread_name)
            projects_root = self.bot.project_manager.projects_root
            
            # projectsディレクトリのGitリポジトリ初期化（必要な場合）
            if not (projects_root / ".git").exists():
                success, output = await self.bot.project_manager.init_git_repository(projects_root)
                if not success:
                    await loading_msg.edit(content=f"❌ Git初期化エラー:\n```\n{output}\n```")
                    return
                
                # 初回の場合、リモートリポジトリを設定
                await loading_msg.edit(content="`...` プロジェクトリポジトリを設定中...")
                await self._setup_projects_remote(projects_root, loading_msg)
            
            # Git操作（projectsディレクトリで実行）
            git_commands = [
                ["git", "add", f"{thread_name}/*"],
                ["git", "commit", "-m", f"[{thread_name}] Complete requirements phase"]
            ]
            
            # リモートが設定されている場合のみpush
            has_remote = await self._check_git_remote(projects_root)
            if has_remote:
                git_commands.append(["git", "push"])
            
            for cmd in git_commands:
                success, output = await self.bot.project_manager.execute_git_command(projects_root, cmd)
                if not success:
                    # pushエラーの場合はスキップ（リモートがない可能性）
                    if cmd[1] == "push":
                        logger.warning(f"Git push skipped (may not have remote): {output}")
                    # commitエラーで「nothing to commit」の場合は続行
                    elif cmd[1] == "commit" and "nothing to commit" in output.lower():
                        logger.info("Nothing to commit, continuing...")
                        await loading_msg.edit(content="`...` コミットする変更がありません。次のステップに進みます...")
                        break  # commitがスキップされたらpushもスキップ
                    else:
                        error_detail = output if output else f"Command failed: {' '.join(cmd)}"
                        await loading_msg.edit(content=f"❌ Gitエラー:\n```\n{error_detail}\n```")
                        return
            
            # 次チャンネルへの投稿
            next_message = self.bot.context_manager.format_complete_message("requirements", thread_name)
            next_channel = self.bot.channel_validator.get_required_channel(ctx.guild, "design")
            
            if not next_channel:
                await loading_msg.edit(content="❌ #3-designチャンネルが見つかりません")
                return
            
            # メッセージ投稿とスレッド作成
            message = await next_channel.send(next_message)
            thread = await message.create_thread(name=thread_name)
            
            # セッション管理の更新
            await self._setup_next_stage_session(
                thread, thread_name, "design", project_path
            )
            
            await loading_msg.edit(content=f"✅ requirements フェーズが完了しました！\n次フェーズ: {next_channel.mention}")
            
        except Exception as e:
            logger.error(f"Error in handle_requirements_complete: {e}", exc_info=True)
            await loading_msg.edit(content=f"❌ エラーが発生しました: {str(e)[:100]}")
    
    async def handle_design_complete(self, ctx) -> None:
        """#3-designでの!complete処理"""
        thread_name = ctx.channel.name
        
        loading_msg = await ctx.send("`...` 処理中...")
        
        try:
            # プロジェクトパスを取得
            project_path = self.bot.project_manager.get_project_path(thread_name)
            projects_root = self.bot.project_manager.projects_root
            
            # projectsディレクトリのGitリポジトリ初期化（必要な場合）
            if not (projects_root / ".git").exists():
                success, output = await self.bot.project_manager.init_git_repository(projects_root)
                if not success:
                    await loading_msg.edit(content=f"❌ Git初期化エラー:\n```\n{output}\n```")
                    return
                
                # 初回の場合、リモートリポジトリを設定
                await loading_msg.edit(content="`...` プロジェクトリポジトリを設定中...")
                await self._setup_projects_remote(projects_root, loading_msg)
            
            # Git操作（projectsディレクトリで実行）
            git_commands = [
                ["git", "add", f"{thread_name}/*"],
                ["git", "commit", "-m", f"[{thread_name}] Complete design phase"]
            ]
            
            # リモートが設定されている場合のみpush
            has_remote = await self._check_git_remote(projects_root)
            if has_remote:
                git_commands.append(["git", "push"])
            
            for cmd in git_commands:
                success, output = await self.bot.project_manager.execute_git_command(projects_root, cmd)
                if not success:
                    # pushエラーの場合はスキップ（リモートがない可能性）
                    if cmd[1] == "push":
                        logger.warning(f"Git push skipped (may not have remote): {output}")
                    # commitエラーで「nothing to commit」の場合は続行
                    elif cmd[1] == "commit" and "nothing to commit" in output.lower():
                        logger.info("Nothing to commit, continuing...")
                        await loading_msg.edit(content="`...` コミットする変更がありません。次のステップに進みます...")
                        break  # commitがスキップされたらpushもスキップ
                    else:
                        error_detail = output if output else f"Command failed: {' '.join(cmd)}"
                        await loading_msg.edit(content=f"❌ Gitエラー:\n```\n{error_detail}\n```")
                        return
            
            # 次チャンネルへの投稿
            next_message = self.bot.context_manager.format_complete_message("design", thread_name)
            next_channel = self.bot.channel_validator.get_required_channel(ctx.guild, "tasks")
            
            if not next_channel:
                await loading_msg.edit(content="❌ #4-tasksチャンネルが見つかりません")
                return
            
            # メッセージ投稿とスレッド作成
            message = await next_channel.send(next_message)
            thread = await message.create_thread(name=thread_name)
            
            # セッション管理の更新
            await self._setup_next_stage_session(
                thread, thread_name, "tasks", project_path
            )
            
            await loading_msg.edit(content=f"✅ design フェーズが完了しました！\n次フェーズ: {next_channel.mention}")
            
        except Exception as e:
            logger.error(f"Error in handle_design_complete: {e}", exc_info=True)
            await loading_msg.edit(content=f"❌ エラーが発生しました: {str(e)[:100]}")
    
    async def handle_tasks_complete(self, ctx) -> None:
        """#4-tasksでの!complete処理（GitHub リポジトリ作成を含む）"""
        thread_name = ctx.channel.name
        
        loading_msg = await ctx.send("`...` 処理中...")
        
        try:
            # プロジェクトパスを取得
            project_path = self.bot.project_manager.get_project_path(thread_name)
            projects_root = self.bot.project_manager.projects_root
            
            # projectsディレクトリのGitリポジトリ初期化（必要な場合）
            if not (projects_root / ".git").exists():
                success, output = await self.bot.project_manager.init_git_repository(projects_root)
                if not success:
                    await loading_msg.edit(content=f"❌ Git初期化エラー:\n```\n{output}\n```")
                    return
                
                # 初回の場合、リモートリポジトリを設定
                await loading_msg.edit(content="`...` プロジェクトリポジトリを設定中...")
                await self._setup_projects_remote(projects_root, loading_msg)
            
            # Git操作（projectsディレクトリで実行）
            git_commands = [
                ["git", "add", f"{thread_name}/*"],
                ["git", "commit", "-m", f"[{thread_name}] Complete tasks phase"]
            ]
            
            # リモートが設定されている場合のみpush
            has_remote = await self._check_git_remote(projects_root)
            if has_remote:
                git_commands.append(["git", "push"])
            
            for cmd in git_commands:
                success, output = await self.bot.project_manager.execute_git_command(projects_root, cmd)
                if not success:
                    # pushエラーの場合はスキップ（リモートがない可能性）
                    if cmd[1] == "push":
                        logger.warning(f"Git push skipped (may not have remote): {output}")
                    # commitエラーで「nothing to commit」の場合は続行
                    elif cmd[1] == "commit" and "nothing to commit" in output.lower():
                        logger.info("Nothing to commit, continuing...")
                        await loading_msg.edit(content="`...` コミットする変更がありません。次のステップに進みます...")
                        break  # commitがスキップされたらpushもスキップ
                    else:
                        error_detail = output if output else f"Command failed: {' '.join(cmd)}"
                        await loading_msg.edit(content=f"❌ Gitエラー:\n```\n{error_detail}\n```")
                        return
            
            # 開発ディレクトリへのコピー
            try:
                dev_path = self.bot.project_manager.copy_to_development(thread_name)
            except FileExistsError:
                await loading_msg.edit(content=f"❌ 開発ディレクトリ `{thread_name}` は既に存在します")
                return
            
            # GitHubワークフローのコピー
            self.bot.project_manager.copy_github_workflows(thread_name)
            
            # 開発ディレクトリでGit初期化
            success, output = await self.bot.project_manager.init_git_repository(dev_path)
            if not success:
                await loading_msg.edit(content=f"❌ Git初期化エラー:\n```\n{output}\n```")
                return
            
            # GitHubリポジトリ作成（正しい構文で）
            create_repo_cmd = ["gh", "repo", "create", thread_name, "--public", "--source=.", "--remote=origin"]
            success, output = await self._run_command(create_repo_cmd, cwd=str(dev_path))
            
            # リポジトリ作成が成功した場合、リモートURLをHTTPSに変更
            # （SSHキーが設定されていない環境でも動作するように）
            if success:
                github_user = await self._get_github_user()
                https_url = f"https://github.com/{github_user}/{thread_name}.git"
                
                # リモートURLをHTTPSに設定
                set_url_cmd = ["git", "remote", "set-url", "origin", https_url]
                success_url, output_url = await self.bot.project_manager.execute_git_command(dev_path, set_url_cmd)
                
                if success_url:
                    logger.info(f"Remote URL set to HTTPS: {https_url}")
                else:
                    logger.warning(f"Failed to set HTTPS URL, keeping SSH: {output_url}")
            
            if not success:
                # リポジトリが既に存在する場合は、リモートを手動で追加
                if "already exists" in output.lower():
                    logger.info("Repository already exists, adding remote...")
                    github_user = await self._get_github_user()
                    # HTTPSを使用（SSHキーが設定されていない環境でも動作）
                    https_url = f"https://github.com/{github_user}/{thread_name}.git"
                    
                    # 既存のリモートを削除（存在する場合）
                    await self.bot.project_manager.execute_git_command(dev_path, ["git", "remote", "remove", "origin"])
                    
                    # 新しいリモートを追加（HTTPS）
                    add_remote_cmd = ["git", "remote", "add", "origin", https_url]
                    success, output = await self.bot.project_manager.execute_git_command(dev_path, add_remote_cmd)
                    
                    if not success:
                        logger.error(f"Failed to add remote: {output}")
                else:
                    await loading_msg.edit(content=f"❌ GitHubリポジトリ作成エラー:\n```\n{output}\n```\n`gh auth login`で認証を確認してください")
                    return
            
            # 現在のブランチ名を取得
            success, branch_name = await self.bot.project_manager.execute_git_command(
                dev_path, ["git", "branch", "--show-current"]
            )
            if not success:
                # ブランチが取得できない場合はデフォルトブランチを作成
                await self.bot.project_manager.execute_git_command(
                    dev_path, ["git", "checkout", "-b", "main"]
                )
                branch_name = "main"
            else:
                branch_name = branch_name.strip()
                if not branch_name:
                    # ブランチ名が空の場合（初期状態）
                    await self.bot.project_manager.execute_git_command(
                        dev_path, ["git", "checkout", "-b", "main"]
                    )
                    branch_name = "main"
            
            # 初期コミットとプッシュ
            dev_git_commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", "Initial commit"],
                ["git", "push", "-u", "origin", branch_name]
            ]
            
            commit_skipped = False
            for cmd in dev_git_commands:
                # コミットがスキップされた場合、pushもスキップ
                if commit_skipped and cmd[1] == "push":
                    logger.info("Skipping push since there was nothing to commit")
                    continue
                    
                success, output = await self.bot.project_manager.execute_git_command(dev_path, cmd)
                if not success:
                    # commitエラーで「nothing to commit」の場合は続行
                    if cmd[1] == "commit" and "nothing to commit" in output.lower():
                        logger.info("Nothing to commit in development directory, continuing...")
                        await loading_msg.edit(content="`...` コミットする変更がありません。")
                        commit_skipped = True
                        continue  # 次のコマンドへ
                    # pushエラーでリモートの問題の場合
                    elif cmd[1] == "push" and ("Could not read from remote repository" in output or 
                                                "fatal: 'origin' does not appear" in output or
                                                "Permission denied" in output or
                                                "fatal: unable to access" in output):
                        logger.warning(f"Push failed due to remote issues: {output}")
                        await loading_msg.edit(content=f"`...` リモートリポジトリへのプッシュをスキップします。\n（リポジトリは作成済み: https://github.com/{await self._get_github_user()}/{thread_name}）")
                        continue
                    else:
                        # エラーメッセージが空の場合はコマンドを表示
                        error_detail = output if output else f"Command failed: {' '.join(cmd)}"
                        await loading_msg.edit(content=f"❌ Gitエラー:\n```\n{error_detail}\n```")
                        return
            
            # GitHubのURLを取得
            github_url = f"https://github.com/{await self._get_github_user()}/{thread_name}"
            
            # 次チャンネルへの投稿
            next_message = self.bot.context_manager.format_complete_message("tasks", thread_name)
            next_channel = self.bot.channel_validator.get_required_channel(ctx.guild, "development")
            
            if not next_channel:
                await loading_msg.edit(content="❌ #5-developmentチャンネルが見つかりません")
                return
            
            # メッセージ投稿とスレッド作成
            message = await next_channel.send(next_message)
            thread = await message.create_thread(name=thread_name)
            
            # 開発用セッションの設定（作業ディレクトリは開発ディレクトリ）
            await self._setup_development_session(
                thread, thread_name, str(dev_path), github_url
            )
            
            await loading_msg.edit(
                content=f"✅ tasks フェーズが完了しました！\n"
                f"🚀 GitHubリポジトリ: {github_url}\n"
                f"次フェーズ: {next_channel.mention}"
            )
            
        except Exception as e:
            logger.error(f"Error in handle_tasks_complete: {e}", exc_info=True)
            await loading_msg.edit(content=f"❌ エラーが発生しました: {str(e)[:100]}")
    
    async def _setup_next_stage_session(self, thread: discord.Thread, idea_name: str, 
                                      stage: str, project_path: Path) -> None:
        """
        次ステージのセッションをセットアップ
        
        Args:
            thread: Discordスレッド
            idea_name: アイデア名
            stage: ステージ名
            project_path: プロジェクトパス
        """
        from src.session_manager import get_session_manager
        
        # セッション番号の割り当て
        thread_id = str(thread.id)
        session_manager = get_session_manager()
        session_num = session_manager.get_or_create_session(thread_id)
        
        # セッション情報の作成
        working_dir = str(self.bot.project_manager.achi_kun_root)
        session_manager.create_session_info(
            session_num, thread_id, idea_name, stage, working_dir
        )
        
        # ワークフロー状態の更新
        session_manager.update_project_stage(idea_name, stage)
        session_manager.add_thread_to_workflow(idea_name, f"{stage[0]}-{stage}", thread_id)
        
        # ドキュメントファイルの作成
        doc_file = project_path / f"{stage}.md"
        doc_file.touch()
        session_manager.add_project_document(idea_name, stage, doc_file)
        
        # Claude Codeセッションの開始（project-wslディレクトリで）
        await self.bot._start_claude_session(session_num, thread.name, working_dir)
        
        # Flask APIにセッション情報を登録
        await self.bot._register_session_to_flask(
            session_num=session_num,
            thread_id=thread_id,
            idea_name=idea_name,
            current_stage=stage,
            working_directory=working_dir,
            project_path=str(project_path)
        )
        
        # 少し待ってからプロンプトを送信
        await asyncio.sleep(3)
        
        # ステージに応じたプロンプトを生成
        if stage == "requirements":
            prompt = self.bot.context_manager.generate_requirements_prompt(idea_name)
        elif stage == "design":
            prompt = self.bot.context_manager.generate_design_prompt(idea_name)
        elif stage == "tasks":
            prompt = self.bot.context_manager.generate_tasks_prompt(idea_name)
        else:
            prompt = ""
        
        # Flask経由でプロンプトを送信
        if prompt:
            success, msg = await self.prompt_sender.send_prompt(
                session_num=session_num,
                prompt=prompt,
                thread_id=thread_id
            )
            
            if not success:
                logger.error(f"Failed to send prompt for {stage}: {msg}")
        
        # スレッドに初期メッセージを投稿
        await thread.send(
            f"📝 Claude Code セッション #{session_num} を開始しました。\n"
            f"📄 ファイル: `{doc_file}`\n\n"
            f"{stage}ドキュメントを作成中..."
        )
    
    async def _setup_development_session(self, thread: discord.Thread, idea_name: str,
                                       working_dir: str, github_url: str) -> None:
        """
        開発セッションをセットアップ
        
        Args:
            thread: Discordスレッド
            idea_name: アイデア名
            working_dir: 作業ディレクトリ（開発ディレクトリ）
            github_url: GitHubリポジトリURL
        """
        from src.session_manager import get_session_manager
        
        # セッション番号の割り当て
        thread_id = str(thread.id)
        session_manager = get_session_manager()
        session_num = session_manager.get_or_create_session(thread_id)
        
        # セッション情報の作成（作業ディレクトリは開発ディレクトリ）
        session_manager.create_session_info(
            session_num, thread_id, idea_name, "development", working_dir
        )
        
        # プロジェクト情報の更新
        project = session_manager.get_project_by_name(idea_name)
        if project:
            project.development_path = Path(working_dir)
            project.github_url = github_url
            project.current_stage = "development"
        
        # ワークフロー状態の更新
        session_manager.update_project_stage(idea_name, "development")
        session_manager.add_thread_to_workflow(idea_name, "5-development", thread_id)
        
        # Claude Codeセッションの開始（作業ディレクトリを指定）
        session_name = f"claude-session-{session_num}"
        claude_cmd = f"cd {working_dir} && claude {self.settings.get_claude_options()}".strip()
        cmd = ['tmux', 'new-session', '-d', '-s', session_name, 'bash', '-c', claude_cmd]
        
        try:
            subprocess.run(cmd, check=True)
            logger.info(f"Started development session {session_num} in {working_dir}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start development session: {e}")
        
        # Flask APIにセッション情報を登録
        await self.bot._register_session_to_flask(
            session_num=session_num,
            thread_id=thread_id,
            idea_name=idea_name,
            current_stage="development",
            working_directory=working_dir,
            project_path=working_dir
        )
        
        # 少し待ってから開発プロンプトを送信
        await asyncio.sleep(3)
        
        prompt = self.bot.context_manager.generate_development_prompt(idea_name)
        success, msg = await self.prompt_sender.send_prompt(
            session_num=session_num,
            prompt=prompt,
            thread_id=thread_id
        )
        
        if not success:
            logger.error(f"Failed to send development prompt: {msg}")
        
        # スレッドに初期メッセージを投稿
        await thread.send(
            f"🚀 開発フェーズを開始しました！\n"
            f"📝 Claude Code セッション #{session_num}\n"
            f"📁 作業ディレクトリ: `{working_dir}`\n"
            f"🔗 GitHub: {github_url}\n\n"
            f"tasks.mdに従って開発を進めてください。"
        )
    
    async def _run_command(self, command: List[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
        """
        非同期でコマンドを実行
        
        Args:
            command: 実行するコマンドのリスト
            cwd: 作業ディレクトリ
            
        Returns:
            (成功フラグ, 出力メッセージ)
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True, stdout.decode('utf-8').strip()
            else:
                return False, stderr.decode('utf-8').strip()
                
        except Exception as e:
            return False, str(e)
    
    async def _get_github_user(self) -> str:
        """GitHub ユーザー名を取得"""
        success, output = await self._run_command(["gh", "api", "user", "--jq", ".login"])
        if success:
            return output.strip()
        return "unknown"
    
    async def _check_git_remote(self, repo_path: Path) -> bool:
        """Gitリモートが設定されているか確認"""
        success, output = await self.bot.project_manager.execute_git_command(
            repo_path, ["git", "remote", "get-url", "origin"]
        )
        return success
    
    async def _setup_projects_remote(self, projects_root: Path, loading_msg) -> bool:
        """projectsディレクトリのリモートリポジトリを設定"""
        try:
            # GitHub CLIを使ってprojectsリポジトリを作成
            github_user = await self._get_github_user()
            if github_user == "unknown":
                logger.warning("Could not get GitHub user, skipping remote setup")
                return False
            
            # リポジトリを作成（プライベート）
            create_cmd = ["gh", "repo", "create", "claude-projects", 
                         "--private", "--source", ".", "--remote", "origin",
                         "--description", "Claude Code project documentation repository"]
            success, output = await self._run_command(create_cmd, cwd=str(projects_root))
            
            if not success:
                if "already exists" in output.lower():
                    # リポジトリが既存の場合、リモートを追加
                    remote_url = f"https://github.com/{github_user}/claude-projects.git"
                    add_remote_cmd = ["git", "remote", "add", "origin", remote_url]
                    success, output = await self.bot.project_manager.execute_git_command(
                        projects_root, add_remote_cmd
                    )
                    if not success and "already exists" not in output.lower():
                        logger.error(f"Failed to add remote: {output}")
                        return False
                else:
                    logger.error(f"Failed to create projects repository: {output}")
                    return False
            
            # 初期コミット
            await self.bot.project_manager.execute_git_command(
                projects_root, ["git", "add", "."]
            )
            await self.bot.project_manager.execute_git_command(
                projects_root, ["git", "commit", "-m", "Initial commit"]
            )
            
            # mainブランチを作成してプッシュ
            await self.bot.project_manager.execute_git_command(
                projects_root, ["git", "branch", "-M", "main"]
            )
            success, output = await self.bot.project_manager.execute_git_command(
                projects_root, ["git", "push", "-u", "origin", "main"]
            )
            
            if success:
                await loading_msg.edit(content="`...` プロジェクトリポジトリを作成しました: https://github.com/{}/claude-projects".format(github_user))
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting up projects remote: {e}")
            return False