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
import json
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
import discord

from src.prompt_sender import get_prompt_sender
from lib.command_executor import async_run

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
    
    def _generate_online_explorer_link(self, project_path: str, is_file: bool = False) -> str:
        """
        Online Explorerのリンクを生成
        
        Args:
            project_path: プロジェクトのフルパス（例: /home/ubuntu/projects/my-project）
            is_file: ファイルへの直接リンクかどうか
        
        Returns:
            Online ExplorerのURL
        """
        # /home/ubuntu/からの相対パスを取得
        base_path = '/home/ubuntu/'
        if project_path.startswith(base_path):
            relative_path = project_path[len(base_path):]
        else:
            # すでに相対パスの場合
            relative_path = project_path.lstrip('/')
        
        # URLエンコード（/を%2Fに変換）
        encoded_path = urllib.parse.quote(relative_path, safe='')
        
        return f"http://3.15.213.192:3456/?path={encoded_path}"
    
    async def handle_idea_complete(self, ctx) -> None:
        """#1-ideaでの!complete処理"""
        thread_name = ctx.channel.name
        loading_msg = await ctx.send("`...` 処理中...")
        
        try:
            # プロジェクトパスを取得
            project_path = self.bot.project_manager.get_project_path(thread_name)
            if not project_path.exists():
                await loading_msg.edit(content=f"❌ プロジェクト `{thread_name}` が見つかりません")
                return
            
            projects_root = self.bot.project_manager.projects_root
            
            # Git操作の実行（共通メソッド呼び出し）
            if not await self._execute_git_workflow(
                projects_root, thread_name, "idea", loading_msg
            ):
                return
            
            # 次ステージへの遷移（共通メソッド呼び出し）
            await self._transition_to_next_stage(
                ctx, thread_name, "idea", "requirements", 
                project_path, loading_msg
            )
            
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
            
            # Git操作の実行（共通メソッド呼び出し）
            if not await self._execute_git_workflow(
                projects_root, thread_name, "requirements", loading_msg
            ):
                return
            
            # 次ステージへの遷移（共通メソッド呼び出し）
            await self._transition_to_next_stage(
                ctx, thread_name, "requirements", "design", 
                project_path, loading_msg
            )
            
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
            
            # Git操作の実行（共通メソッド呼び出し）
            if not await self._execute_git_workflow(
                projects_root, thread_name, "design", loading_msg
            ):
                return
            
            # 次ステージへの遷移（共通メソッド呼び出し）
            await self._transition_to_next_stage(
                ctx, thread_name, "design", "tasks", 
                project_path, loading_msg
            )
            
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
            
            # 1. 通常のGit操作（共通メソッド呼び出し）
            if not await self._execute_git_workflow(
                projects_root, thread_name, "tasks", loading_msg
            ):
                return
            
            # 2. 開発環境セットアップ（tasks特有の処理）
            dev_path, github_url = await self._setup_development_environment(
                thread_name, loading_msg
            )
            if not dev_path:
                return  # エラーメッセージは既に表示済み
            
            # 3. 次ステージへの遷移（開発用の特別なセッション設定）
            next_message = self.bot.context_manager.format_complete_message("tasks", thread_name)
            next_channel = self.bot.channel_validator.get_required_channel(ctx.guild, "development")
            
            if not next_channel:
                await loading_msg.edit(content="❌ #5-developmentチャンネルが見つかりません")
                return
            
            message = await next_channel.send(next_message)
            thread = await message.create_thread(name=thread_name)
            
            # 開発用セッションの設定（作業ディレクトリは開発ディレクトリ）
            await self._setup_development_session(
                thread, thread_name, str(dev_path), github_url
            )
            
            # 現在のセッションを終了
            await self._terminate_current_session(ctx)
            
            # Online Explorerリンクを生成（開発ディレクトリ用）
            explorer_link = self._generate_online_explorer_link(str(dev_path))
            
            await loading_msg.edit(
                content=(
                    f"✅ **tasks** フェーズが完了しました！\n"
                    f"📂 プロジェクト: `{thread_name}`\n"
                    f"📍 開発パス: `{dev_path}`\n"
                    f"🚀 GitHubリポジトリ: {github_url}\n"
                    f"🌐 ブラウザで確認: [Online Explorerで開く]({explorer_link})\n"
                    f"➡️ 次フェーズ: {next_channel.mention}"
                )
            )
            
        except Exception as e:
            logger.error(f"Error in handle_tasks_complete: {e}", exc_info=True)
            await loading_msg.edit(content=f"❌ エラーが発生しました: {str(e)[:100]}")
    
    async def _execute_git_workflow(
        self,
        projects_root: Path,
        thread_name: str,
        phase_name: str,
        loading_msg: discord.Message
    ) -> bool:
        """
        Git操作の共通ワークフロー実行
        
        Args:
            projects_root: プロジェクトのルートディレクトリ
            thread_name: スレッド名（プロジェクト名）
            phase_name: フェーズ名（idea, requirements, design, tasks）
            loading_msg: 進捗表示用メッセージ
        
        Returns:
            bool: 成功した場合True、失敗した場合False
        
        Raises:
            なし（エラーはFalseを返すことで処理）
        """
        # Gitリポジトリの存在確認
        if not (projects_root / ".git").exists():
            success, output = await self.bot.project_manager.init_git_repository(projects_root)
            if not success:
                await loading_msg.edit(content=f"❌ Git初期化エラー:\n```\n{output}\n```")
                return False
            
            # 初回の場合、リモートリポジトリを設定
            await loading_msg.edit(content="`...` プロジェクトリポジトリを設定中...")
            await self._setup_projects_remote(projects_root, loading_msg)
        
        # Git操作コマンドの定義
        git_commands = [
            ["git", "add", "."],  # projects全体をステージング
            ["git", "commit", "-m", f"[{thread_name}] Complete {phase_name} phase"]
        ]
        
        # リモート確認とpush追加
        has_remote = await self._check_git_remote(projects_root)
        if has_remote:
            git_commands.append(["git", "push"])
        
        # コマンド実行
        for cmd in git_commands:
            success, output = await self.bot.project_manager.execute_git_command(projects_root, cmd)
            if not success:
                # pushエラーの場合は警告のみ
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
                    return False
        
        return True
    
    async def _transition_to_next_stage(
        self,
        ctx,
        thread_name: str,
        current_stage: str,
        next_stage: str,
        project_path: Path,
        loading_msg: discord.Message
    ) -> bool:
        """
        次のステージへの遷移処理
        
        Args:
            ctx: コマンドコンテキスト
            thread_name: スレッド名
            current_stage: 現在のステージ
            next_stage: 次のステージ
            project_path: プロジェクトパス
            loading_msg: 進捗表示用メッセージ
        
        Returns:
            bool: 成功した場合True、失敗した場合False
        """
        # メッセージフォーマット
        next_message = self.bot.context_manager.format_complete_message(current_stage, thread_name)
        
        # 次チャンネル取得
        next_channel = self.bot.channel_validator.get_required_channel(ctx.guild, next_stage)
        if not next_channel:
            stage_number = {
                "requirements": "2",
                "design": "3", 
                "tasks": "4",
                "development": "5"
            }.get(next_stage, "?")
            await loading_msg.edit(content=f"❌ #{stage_number}-{next_stage}チャンネルが見つかりません")
            return False
        
        # メッセージ投稿とスレッド作成
        message = await next_channel.send(next_message)
        thread = await message.create_thread(name=thread_name)
        
        # セッション管理の更新
        await self._setup_next_stage_session(
            thread, thread_name, next_stage, project_path
        )
        
        # 現在のセッションを終了
        await self._terminate_current_session(ctx)
        
        # Online Explorerリンクを生成
        explorer_link = self._generate_online_explorer_link(str(project_path))
        
        # 成功メッセージ（Online Explorerリンクを含む）
        await loading_msg.edit(
            content=(
                f"✅ **{current_stage}** フェーズが完了しました！\n"
                f"📂 プロジェクト: `{thread_name}`\n"
                f"📍 パス: `{project_path}`\n"
                f"🌐 ブラウザで確認: [Online Explorerで開く]({explorer_link})\n"
                f"➡️ 次フェーズ: {next_channel.mention}"
            )
        )
        
        return True
    
    async def _setup_development_environment(
        self,
        thread_name: str,
        loading_msg: discord.Message
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        開発環境のセットアップ（tasksフェーズ専用）
        
        Args:
            thread_name: スレッド名（プロジェクト名）
            loading_msg: 進捗表示用メッセージ
        
        Returns:
            Tuple[Optional[Path], Optional[str]]: (開発パス, GitHub URL) or (None, None) if error
        """
        try:
            # 開発ディレクトリへのコピー
            try:
                dev_path = self.bot.project_manager.copy_to_development(thread_name)
            except FileExistsError:
                await loading_msg.edit(content=f"❌ 開発ディレクトリ `{thread_name}` は既に存在します")
                return None, None
            
            # GitHubワークフローのコピー
            self.bot.project_manager.copy_github_workflows(thread_name)
            
            # 開発ディレクトリでGit初期化
            success, output = await self.bot.project_manager.init_git_repository(dev_path)
            if not success:
                await loading_msg.edit(content=f"❌ Git初期化エラー:\n```\n{output}\n```")
                return None, None
            
            # Serena MCPをプロジェクトに追加
            serena_cmd = [
                "claude", "mcp", "add", "serena",
                "--scope", "project",
                "--", "uvx", "--from", "git+https://github.com/oraios/serena",
                "serena", "start-mcp-server",
                "--context", "ide-assistant",
                "--project", str(dev_path)
            ]
            success, output = await async_run(serena_cmd, cwd=str(dev_path))
            if success:
                logger.info(f"Serena MCP configured for project: {dev_path}")
            else:
                logger.warning(f"Failed to configure Serena MCP: {output}")
            
            # GitHubリポジトリ作成
            create_repo_cmd = ["gh", "repo", "create", thread_name, "--public", "--source=.", "--remote=origin"]
            success, output = await async_run(create_repo_cmd, cwd=str(dev_path))
            
            # GitHub ユーザー名取得
            github_user = await self._get_github_user()
            https_url = f"https://github.com/{github_user}/{thread_name}.git"
            
            if success:
                # リモートURLをHTTPSに設定
                set_url_cmd = ["git", "remote", "set-url", "origin", https_url]
                success_url, output_url = await self.bot.project_manager.execute_git_command(dev_path, set_url_cmd)
                
                if success_url:
                    logger.info(f"Remote URL set to HTTPS: {https_url}")
                else:
                    logger.warning(f"Failed to set HTTPS URL, keeping SSH: {output_url}")
            
            elif "already exists" in output.lower():
                # 既存リポジトリの場合、リモートを手動で追加
                logger.info("Repository already exists, adding remote...")
                
                # 既存のリモートを削除（存在する場合）
                await self.bot.project_manager.execute_git_command(dev_path, ["git", "remote", "remove", "origin"])
                
                # 新しいリモートを追加（HTTPS）
                add_remote_cmd = ["git", "remote", "add", "origin", https_url]
                success, output = await self.bot.project_manager.execute_git_command(dev_path, add_remote_cmd)
                
                if not success:
                    logger.error(f"Failed to add remote: {output}")
                    await loading_msg.edit(content=f"❌ リモート追加エラー:\n```\n{output}\n```")
                    return None, None
            else:
                await loading_msg.edit(
                    content=f"❌ GitHubリポジトリ作成エラー:\n```\n{output}\n```\n`gh auth login`で認証を確認してください"
                )
                return None, None
            
            # GitHub Secretsの設定
            await loading_msg.edit(content="`...` GitHub Secretsを設定中...")
            secrets_success = await self._setup_github_secrets(thread_name, dev_path)
            if not secrets_success:
                logger.warning("Failed to set GitHub secrets, but continuing with repository setup")
            
            # 現在のブランチ名を取得
            success, branch_name = await self.bot.project_manager.execute_git_command(
                dev_path, ["git", "branch", "--show-current"]
            )
            
            if not success or not branch_name.strip():
                # ブランチが取得できない場合はデフォルトブランチを作成
                await self.bot.project_manager.execute_git_command(
                    dev_path, ["git", "checkout", "-b", "main"]
                )
                branch_name = "main"
            else:
                branch_name = branch_name.strip()
            
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
                        continue
                    # pushエラーでリモートの問題の場合
                    elif cmd[1] == "push" and any(err in output for err in [
                        "Could not read from remote repository",
                        "fatal: 'origin' does not appear",
                        "Permission denied",
                        "fatal: unable to access"
                    ]):
                        logger.warning(f"Push failed due to remote issues: {output}")
                        await loading_msg.edit(
                            content=f"`...` リモートリポジトリへのプッシュをスキップします。\n"
                            f"（リポジトリは作成済み: {https_url}）"
                        )
                        continue
                    else:
                        # その他のエラー
                        error_detail = output if output else f"Command failed: {' '.join(cmd)}"
                        await loading_msg.edit(content=f"❌ Gitエラー:\n```\n{error_detail}\n```")
                        # pushエラーの場合は続行、それ以外は失敗
                        if cmd[1] != "push":
                            return None, None
            
            github_url = f"https://github.com/{github_user}/{thread_name}"
            return dev_path, github_url
        
        except Exception as e:
            logger.error(f"Error in _setup_development_environment: {e}", exc_info=True)
            await loading_msg.edit(content=f"❌ 開発環境セットアップエラー: {str(e)[:100]}")
            return None, None
    
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
        
        # Claude Codeセッションの開始
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
        
        # Claude Codeの起動完了を待ってからプロンプトを送信
        await asyncio.sleep(8)  # 3秒から8秒に延長
        
        # スレッド情報を準備
        thread_info = {
            'channel_name': thread.parent.name if thread.parent else 'Unknown',
            'thread_name': thread.name,
            'thread_id': thread_id
        }
        
        # ステージに応じたプロンプトを生成（thread_infoとsession_numを渡す）
        if stage == "requirements":
            prompt = self.bot.context_manager.generate_requirements_prompt(
                idea_name, thread_info=thread_info, session_num=session_num
            )
        elif stage == "design":
            prompt = self.bot.context_manager.generate_design_prompt(
                idea_name, thread_info=thread_info, session_num=session_num
            )
        elif stage == "tasks":
            prompt = self.bot.context_manager.generate_tasks_prompt(
                idea_name, thread_info=thread_info, session_num=session_num
            )
        else:
            prompt = ""
        
        # Flask経由でプロンプトを送信（プロンプトには既にコンテキストが含まれている）
        if prompt:
            success, msg = await self.prompt_sender.send_prompt(
                session_num=session_num,
                prompt=prompt,
                thread_id=thread_id
            )
            
            if not success:
                logger.error(f"Failed to send prompt for {stage}: {msg}")
        
        # Online Explorerリンクを生成
        explorer_link = self._generate_online_explorer_link(str(project_path))
        
        # スレッドに初期メッセージを投稿（Online Explorerリンクを含む）
        await thread.send(
            f"📝 Claude Code セッション #{session_num} を開始しました。\n"
            f"📄 ファイル: `{doc_file}`\n"
            f"🌐 ブラウザで確認: [Online Explorerで開く]({explorer_link})\n\n"
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
        
        # Claude Codeセッションの開始（.mcp.jsonがあれば自動的に使用）
        session_name = f"claude-session-{session_num}"
        
        # .mcp.jsonが存在する場合は--mcp-configオプションを追加
        mcp_json_path = Path(working_dir) / ".mcp.json"
        mcp_option = f"--mcp-config {mcp_json_path}" if mcp_json_path.exists() else ""
        claude_options = self.settings.get_claude_options()
        
        if mcp_json_path.exists():
            logger.info(f"Using MCP configuration: {mcp_json_path}")
        
        claude_cmd = f"export LANG=C.UTF-8 && export LC_ALL=C.UTF-8 && cd {working_dir} && claude {mcp_option} {claude_options}".strip()
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
        
        # スレッド情報を準備
        thread_info = {
            'channel_name': thread.parent.name if thread.parent else 'Unknown',
            'thread_name': thread.name,
            'thread_id': thread_id
        }
        
        # 開発プロンプトを生成（thread_infoとsession_numを渡す）
        prompt = self.bot.context_manager.generate_development_prompt(
            idea_name, thread_info=thread_info, session_num=session_num
        )
        
        # Flask経由でプロンプトを送信（プロンプトには既にコンテキストが含まれている）
        success, msg = await self.prompt_sender.send_prompt(
            session_num=session_num,
            prompt=prompt,
            thread_id=thread_id
        )
        
        if not success:
            logger.error(f"Failed to send development prompt: {msg}")
        
        # Online Explorerリンクを生成
        explorer_link = self._generate_online_explorer_link(working_dir)
        
        # スレッドに初期メッセージを投稿（Online Explorerリンクを含む）
        await thread.send(
            f"🚀 開発フェーズを開始しました！\n"
            f"📝 Claude Code セッション #{session_num}\n"
            f"📁 作業ディレクトリ: `{working_dir}`\n"
            f"🔗 GitHub: {github_url}\n"
            f"🌐 ブラウザエディタ: [Online Explorerで開く]({explorer_link})\n\n"
            f"tasks.mdに従って開発を進めてください。"
        )
    
    async def _get_github_user(self) -> str:
        """GitHub ユーザー名を取得"""
        success, output = await async_run(["gh", "api", "user", "--jq", ".login"])
        if success:
            return output.strip()
        return "unknown"

    async def _setup_github_secrets(self, repo_name: str, dev_path: Path) -> bool:
        """
        GitHub SecretsにClaude Code OAuthトークンを設定
        
        Args:
            repo_name: リポジトリ名
            dev_path: 開発ディレクトリパス
            
        Returns:
            bool: 成功した場合True、失敗した場合False
        """
        try:
            # 1. credentials.jsonからOAuthトークンを取得
            credentials_path = Path.home() / ".claude" / ".credentials.json"
            if not credentials_path.exists():
                logger.warning("Claude credentials file not found. Please login with 'claude login'")
                return False
            
            with open(credentials_path, 'r') as f:
                credentials = json.load(f)
            
            oauth_data = credentials.get('claudeAiOauth', {})
            access_token = oauth_data.get('accessToken')
            expires_at = oauth_data.get('expiresAt', 0)
            
            if not access_token:
                logger.warning("OAuth access token not found in credentials")
                return False
            
            # 2. トークンの有効期限をチェック
            if expires_at:
                expiry_date = datetime.fromtimestamp(expires_at / 1000)
                if datetime.now() > expiry_date:
                    logger.warning(f"OAuth token expired at {expiry_date}. Please re-login with 'claude login'")
                    return False
                logger.info(f"OAuth token valid until {expiry_date}")
            
            # 3. gh secretコマンドで設定
            github_user = await self._get_github_user()
            cmd = ["gh", "secret", "set", "CLAUDE_CODE_OAUTH_TOKEN", 
                   "-b", access_token, "-R", f"{github_user}/{repo_name}"]
            
            success, output = await async_run(cmd, cwd=str(dev_path))
            
            if success:
                logger.info(f"GitHub Secret CLAUDE_CODE_OAUTH_TOKEN set for {repo_name}")
                return True
            else:
                logger.error(f"Failed to set GitHub Secret: {output}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting GitHub secrets: {e}")
            return False
    
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
            success, output = await async_run(create_cmd, cwd=str(projects_root))
            
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
    
    async def _terminate_current_session(self, ctx) -> None:
        """
        現在のスレッドのtmuxセッションを終了
        
        Args:
            ctx: コマンドコンテキスト
        """
        try:
            from src.tmux_manager import TmuxManager
            from src.session_manager import get_session_manager
            
            tmux_manager = TmuxManager()
            session_manager = get_session_manager()
            
            # 現在のスレッドIDからセッション番号を取得
            thread_id = str(ctx.channel.id)
            session_num = session_manager.get_session(thread_id)
            
            if session_num is not None:
                # tmuxセッションを終了
                if tmux_manager.kill_claude_session(session_num):
                    # SessionManagerからも削除
                    session_manager.remove_session(thread_id)
                    logger.info(f"Terminated session {session_num} for thread {thread_id}")
                else:
                    logger.warning(f"Failed to terminate tmux session {session_num}")
            else:
                logger.debug(f"No active session found for thread {thread_id}")
                
        except Exception as e:
            logger.error(f"Error terminating session: {e}")
            # エラーが発生してもワークフローは継続