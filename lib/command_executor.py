#!/usr/bin/env python3
"""
統一コマンド実行モジュール

このモジュールは、プロジェクト全体で使用される
コマンド実行関数を一元化します。
"""

import asyncio
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Union

logger = logging.getLogger(__name__)


async def async_run(
    command: List[str],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[float] = None,
    capture_output: bool = True,
    verbose: bool = False
) -> Tuple[bool, str]:
    """
    非同期でコマンドを実行
    
    Args:
        command: 実行するコマンドのリスト
        cwd: 作業ディレクトリ（strまたはPath）
        timeout: タイムアウト秒数（None で無制限）
        capture_output: 出力をキャプチャするか
        verbose: 詳細ログを出力するか
        
    Returns:
        (成功フラグ, 出力メッセージ)
        
    Examples:
        >>> success, output = await async_run(["ls", "-la"])
        >>> success, output = await async_run(["git", "status"], cwd="/path/to/repo")
    """
    try:
        # cwdをstrに変換（Pathオブジェクトの場合）
        if cwd is not None and isinstance(cwd, Path):
            cwd = str(cwd)
        
        if verbose:
            logger.debug(f"Executing command: {' '.join(command)} in {cwd or 'current directory'}")
        
        # サブプロセスの作成
        if capture_output:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd
            )
        
        try:
            # タイムアウトを考慮した実行
            if capture_output:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            else:
                await asyncio.wait_for(
                    process.wait(), 
                    timeout=timeout
                )
                stdout, stderr = b"", b""
                
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return False, f"Command timed out after {timeout} seconds"
        
        # 結果の処理
        if process.returncode == 0:
            # 成功時
            if capture_output:
                output = stdout.decode('utf-8', errors='replace').strip()
                # 出力が空の場合はメッセージを返す
                return True, output if output else "Command completed successfully"
            else:
                return True, "Command completed successfully"
        else:
            # エラー時
            if capture_output:
                error_output = stderr.decode('utf-8', errors='replace').strip()
                # stderrが空の場合はstdoutも確認
                if not error_output:
                    error_output = stdout.decode('utf-8', errors='replace').strip()
                # それでも空の場合はエラーコードを返す
                if not error_output:
                    error_output = f"Command failed with exit code {process.returncode}"
                return False, error_output
            else:
                return False, f"Command failed with exit code {process.returncode}"
                
    except FileNotFoundError:
        error_msg = f"Command not found: {command[0]}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Command execution error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def sync_run(
    command: List[str],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[float] = None,
    capture_output: bool = True,
    shell: bool = False,
    verbose: bool = False
) -> Tuple[bool, str]:
    """
    同期的にコマンドを実行
    
    Args:
        command: 実行するコマンドのリスト
        cwd: 作業ディレクトリ（strまたはPath）
        timeout: タイムアウト秒数（None で無制限）
        capture_output: 出力をキャプチャするか
        shell: シェル経由で実行するか
        verbose: 詳細ログを出力するか
        
    Returns:
        (成功フラグ, 出力メッセージ)
        
    Examples:
        >>> success, output = sync_run(["ls", "-la"])
        >>> success, output = sync_run(["git", "status"], cwd="/path/to/repo")
    """
    try:
        # cwdをstrに変換（Pathオブジェクトの場合）
        if cwd is not None and isinstance(cwd, Path):
            cwd = str(cwd)
        
        if verbose:
            logger.debug(f"Executing command: {' '.join(command)} in {cwd or 'current directory'}")
        
        # コマンドの実行
        if shell:
            # シェル実行の場合はコマンドを文字列に結合
            cmd = ' '.join(command) if isinstance(command, list) else command
        else:
            cmd = command
        
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            shell=shell
        )
        
        # 結果の処理
        if result.returncode == 0:
            # 成功時
            if capture_output:
                output = result.stdout.strip()
                return True, output if output else "Command completed successfully"
            else:
                return True, "Command completed successfully"
        else:
            # エラー時
            if capture_output:
                error_output = result.stderr.strip()
                # stderrが空の場合はstdoutも確認
                if not error_output:
                    error_output = result.stdout.strip()
                # それでも空の場合はエラーコードを返す
                if not error_output:
                    error_output = f"Command failed with exit code {result.returncode}"
                return False, error_output
            else:
                return False, f"Command failed with exit code {result.returncode}"
                
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout} seconds"
    except FileNotFoundError:
        error_msg = f"Command not found: {command[0] if isinstance(command, list) else command.split()[0]}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Command execution error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def execute_git_command(
    path: Union[str, Path],
    git_args: List[str],
    verbose: bool = True
) -> Tuple[bool, str]:
    """
    Git専用のコマンド実行ヘルパー
    
    Args:
        path: Gitリポジトリのパス
        git_args: gitコマンドの引数（例: ["add", "."]）
        verbose: 詳細ログを出力するか
        
    Returns:
        (成功フラグ, 出力メッセージ)
        
    Examples:
        >>> success, output = await execute_git_command("/repo", ["status"])
        >>> success, output = await execute_git_command("/repo", ["commit", "-m", "message"])
    """
    # "git"を先頭に追加
    command = ["git"] + git_args
    
    if verbose:
        logger.info(f"Executing git command: {' '.join(command)} in {path}")
    
    success, output = await async_run(command, cwd=path, verbose=False)
    
    if verbose:
        if success:
            logger.info(f"Git command succeeded: {' '.join(git_args)}")
        else:
            logger.error(f"Git command failed: {' '.join(git_args)} - {output}")
    
    return success, output


# 互換性のためのエイリアス
async_execute = async_run
sync_execute = sync_run


if __name__ == "__main__":
    # テスト実行
    import asyncio
    
    async def test_async():
        print("Testing async_run...")
        success, output = await async_run(["echo", "Hello, World!"])
        print(f"Success: {success}, Output: {output}")
        
        success, output = await execute_git_command(".", ["status"])
        print(f"Git status - Success: {success}, Output: {output[:100]}...")
    
    def test_sync():
        print("Testing sync_run...")
        success, output = sync_run(["echo", "Hello, World!"])
        print(f"Success: {success}, Output: {output}")
    
    # テスト実行
    test_sync()
    asyncio.run(test_async())