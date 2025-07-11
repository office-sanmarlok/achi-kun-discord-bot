#!/usr/bin/env python3
"""
Attachment Manager - Discord添付ファイル管理システム

このモジュールは以下の責任を持つ：
1. Discord添付ファイルの非同期ダウンロード
2. ファイル形式の検証とサイズ制限管理
3. 自動ファイル命名と重複回避
4. ストレージ管理と自動クリーンアップ
5. Claude Code連携用パス生成

拡張性のポイント：
- 新しいファイル形式のサポート追加
- ファイル変換・処理機能の実装
- 外部ストレージ連携（S3、GCS等）
- ウイルススキャン・セキュリティ機能
- メタデータ抽出・分析機能
"""

import os
import sys
import secrets
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

# パッケージルートの追加（相対インポート対応）
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import aiohttp
except ImportError:
    print("Error: aiohttp is not installed. Run: pip install aiohttp")
    sys.exit(1)

from config.settings import SettingsManager

# ログ設定
logger = logging.getLogger(__name__)

@dataclass
class FileMetadata:
    """
    ファイルメタデータ管理用データクラス
    
    拡張ポイント：
    - 追加メタデータフィールド
    - ファイル分析結果
    - 変換処理情報
    """
    original_name: str
    saved_name: str
    file_path: str
    size: int
    mime_type: Optional[str] = None
    download_url: str = ""
    timestamp: str = ""

class FileValidator:
    """
    ファイル検証処理
    
    将来の拡張：
    - MIME type詳細検証
    - ファイル内容スキャン
    - ウイルス検査連携
    - カスタム検証ルール
    """
    
    # サポートする画像形式（拡張可能）
    SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'}
    
    # ファイルサイズ制限（Discord制限に準拠、将来は設定可能）
    MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB
    
    @classmethod
    def is_supported_format(cls, filename: str) -> bool:
        """
        サポートされているファイル形式かチェック
        
        拡張ポイント：
        - 動的サポート形式管理
        - MIME type検証
        - カスタム形式定義
        """
        return Path(filename).suffix.lower() in cls.SUPPORTED_EXTENSIONS
    
    @classmethod
    def is_valid_size(cls, size: int) -> bool:
        """
        ファイルサイズが制限内かチェック
        
        拡張ポイント：
        - ユーザー別サイズ制限
        - 動的制限設定
        - 圧縮処理による制限回避
        """
        return size <= cls.MAX_FILE_SIZE
    
    @classmethod
    def validate_attachment(cls, attachment) -> Tuple[bool, Optional[str]]:
        """
        添付ファイルの総合検証
        
        Args:
            attachment: Discord attachment object
        
        Returns:
            Tuple[bool, Optional[str]]: (有効フラグ, エラーメッセージ)
        """
        # ファイル形式チェック
        if not cls.is_supported_format(attachment.filename):
            return False, f"Unsupported file format: {attachment.filename}"
        
        # ファイルサイズチェック
        if not cls.is_valid_size(attachment.size):
            return False, f"File too large ({attachment.size} bytes, max {cls.MAX_FILE_SIZE})"
        
        return True, None

class FileNamingStrategy:
    """
    ファイル命名戦略
    
    将来の拡張：
    - 命名規則のカスタマイズ
    - ユーザー別命名空間
    - コンテンツベース命名
    - 重複回避アルゴリズム
    """
    
    @staticmethod
    def generate_unique_filename(original_name: str) -> str:
        """
        一意なファイル名を生成
        
        拡張ポイント：
        - 命名パターンの設定化
        - ハッシュベース命名
        - 日付フォーマットカスタマイズ
        
        Args:
            original_name: 元のファイル名
        
        Returns:
            str: 生成された一意ファイル名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = secrets.token_hex(3)  # 6文字のランダム文字列
        extension = Path(original_name).suffix.lower()
        
        # 拡張子が無い場合のデフォルト処理
        if not extension:
            extension = '.bin'
        
        return f"IMG_{timestamp}_{random_suffix}{extension}"

class StorageManager:
    """
    ストレージ管理システム
    
    将来の拡張：
    - 外部ストレージ対応（S3、GCS等）
    - ストレージ階層化
    - 自動バックアップ
    - 容量制限管理
    """
    
    def __init__(self, config_dir: Path):
        """
        ストレージマネージャーの初期化
        
        Args:
            config_dir: 設定ディレクトリパス
        """
        self.config_dir = config_dir
        self.attachments_dir = config_dir / 'attachments'
        self.ensure_storage_directory()
    
    def ensure_storage_directory(self):
        """
        ストレージディレクトリの作成・確認
        
        拡張ポイント：
        - 権限設定の最適化
        - 複数ディレクトリ管理
        - 容量監視機能
        """
        try:
            self.attachments_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Storage directory ensured: {self.attachments_dir}")
        except Exception as e:
            logger.error(f"Failed to create storage directory: {e}")
            raise
    
    def get_storage_path(self, filename: str) -> Path:
        """
        ファイル保存パスを取得
        
        拡張ポイント：
        - ディレクトリ階層化（日付別等）
        - 負荷分散ディレクトリ選択
        - 重複ファイル処理
        """
        return self.attachments_dir / filename
    
    def cleanup_old_files(self, max_age_days: int = 1) -> int:
        """
        古いファイルのクリーンアップ
        
        拡張ポイント：
        - 詳細な削除ポリシー
        - アーカイブ機能
        - 削除前通知
        
        Args:
            max_age_days: 保持期間（日数）
        
        Returns:
            int: 削除されたファイル数
        """
        if not self.attachments_dir.exists():
            return 0
        
        try:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            deleted_count = 0
            
            for file_path in self.attachments_dir.glob('IMG_*'):
                try:
                    # ファイルの更新時刻を取得
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old attachment: {file_path.name}")
                        
                except OSError as e:
                    logger.warning(f"Failed to delete {file_path.name}: {e}")
                    continue
            
            if deleted_count > 0:
                logger.info(f"Cleanup completed: {deleted_count} files deleted")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        ストレージ使用状況の取得
        
        拡張ポイント：
        - 詳細統計情報
        - ファイル種別分析
        - 使用量予測
        """
        try:
            if not self.attachments_dir.exists():
                return {
                    'total_files': 0,
                    'total_size': 0,
                    'total_size_mb': 0.0,
                    'directory': str(self.attachments_dir)
                }
            
            files = list(self.attachments_dir.glob('IMG_*'))
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            return {
                'total_files': len(files),
                'total_size': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'directory': str(self.attachments_dir),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                'total_files': 0,
                'total_size': 0,
                'total_size_mb': 0.0,
                'directory': str(self.attachments_dir),
                'error': str(e)
            }

class AttachmentDownloader:
    """
    非同期ファイルダウンロード処理
    
    将来の拡張：
    - 並列ダウンロード数制御
    - 進捗表示機能
    - リトライ機構
    - 帯域制限機能
    """
    
    # 設定可能な定数（将来は設定ファイル化）
    DOWNLOAD_TIMEOUT_SECONDS = 30
    MAX_CONCURRENT_DOWNLOADS = 5
    
    def __init__(self, storage_manager: StorageManager):
        """
        ダウンローダーの初期化
        
        Args:
            storage_manager: ストレージマネージャーインスタンス
        """
        self.storage_manager = storage_manager
        self.file_validator = FileValidator()
        self.naming_strategy = FileNamingStrategy()
    
    async def download_attachment(self, attachment) -> Optional[FileMetadata]:
        """
        Discord添付ファイルの非同期ダウンロード
        
        拡張ポイント：
        - プログレスコールバック
        - 部分ダウンロード対応
        - ダウンロード優先度制御
        
        Args:
            attachment: Discord attachment object
        
        Returns:
            Optional[FileMetadata]: ダウンロード成功時のメタデータ
        """
        try:
            # ステップ1: ファイル検証
            is_valid, error_msg = self.file_validator.validate_attachment(attachment)
            if not is_valid:
                logger.warning(f"Invalid attachment {attachment.filename}: {error_msg}")
                return None
            
            # ステップ2: ファイル名生成
            saved_filename = self.naming_strategy.generate_unique_filename(attachment.filename)
            file_path = self.storage_manager.get_storage_path(saved_filename)
            
            # ステップ3: ダウンロード実行
            success = await self._perform_download(attachment.url, file_path)
            if not success:
                return None
            
            # ステップ4: メタデータ作成
            metadata = FileMetadata(
                original_name=attachment.filename,
                saved_name=saved_filename,
                file_path=str(file_path.absolute()),
                size=attachment.size,
                download_url=attachment.url,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"Downloaded attachment: {saved_filename} ({attachment.size} bytes)")
            return metadata
            
        except Exception as e:
            logger.error(f"Error downloading {attachment.filename}: {e}")
            return None
    
    async def _perform_download(self, url: str, file_path: Path) -> bool:
        """
        実際のダウンロード処理
        
        拡張ポイント：
        - チャンク単位ダウンロード
        - レジューム機能
        - 進捗通知
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.DOWNLOAD_TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # ファイル保存
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        
                        # 権限設定（読み取り専用）
                        os.chmod(file_path, 0o644)
                        
                        return True
                    else:
                        logger.error(f"HTTP {response.status} for URL: {url}")
                        return False
                        
        except asyncio.TimeoutError:
            logger.error(f"Download timeout for URL: {url}")
            return False
        except Exception as e:
            logger.error(f"Download error for URL {url}: {e}")
            return False

class AttachmentManager:
    """
    添付ファイル管理の統合クラス
    
    アーキテクチャ特徴：
    - 非同期処理による高い並列性
    - モジュラー設計による拡張性
    - 堅牢なエラーハンドリング
    - 自動リソース管理
    
    拡張可能要素：
    - ファイル変換処理
    - メタデータ抽出
    - 外部API連携
    - 統計・分析機能
    - バックアップ・同期機能
    """
    
    def __init__(self):
        """
        添付ファイルマネージャーの初期化
        """
        self.settings = SettingsManager()
        self.storage_manager = StorageManager(self.settings.config_dir)
        self.downloader = AttachmentDownloader(self.storage_manager)
    
    async def process_attachments(self, attachments) -> List[str]:
        """
        複数添付ファイルの並列処理
        
        拡張ポイント：
        - 処理優先度制御
        - リアルタイム進捗表示
        - 処理結果の詳細分析
        
        Args:
            attachments: Discord attachment objects のリスト
        
        Returns:
            List[str]: 成功したファイルパスのリスト
        """
        if not attachments:
            return []
        
        logger.info(f"Processing {len(attachments)} attachment(s)")
        
        # 並列ダウンロード実行
        tasks = [self.downloader.download_attachment(attachment) for attachment in attachments]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果の処理
        successful_paths = []
        failed_count = 0
        
        for result in results:
            if isinstance(result, FileMetadata):
                successful_paths.append(result.file_path)
            elif isinstance(result, Exception):
                logger.error(f"Attachment processing failed: {result}")
                failed_count += 1
            else:
                # None の場合（検証失敗等）
                failed_count += 1
        
        # 処理結果ログ
        logger.info(f"Attachment processing completed: {len(successful_paths)} success, {failed_count} failed")
        
        return successful_paths
    
    def cleanup_old_files(self, max_age_days: int = 1) -> int:
        """
        古いファイルのクリーンアップ（同期ラッパー）
        
        Args:
            max_age_days: 保持期間（日数）
        
        Returns:
            int: 削除されたファイル数
        """
        return self.storage_manager.cleanup_old_files(max_age_days)
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        ストレージ情報の取得（同期ラッパー）
        
        Returns:
            Dict[str, Any]: ストレージ使用状況
        """
        return self.storage_manager.get_storage_info()

# テスト・デバッグ用関数
async def test_attachment_manager():
    """
    AttachmentManagerの動作テスト
    
    拡張ポイント：
    - ユニットテスト実装
    - パフォーマンステスト
    - ストレステスト
    """
    manager = AttachmentManager()
    
    print(f"Storage directory: {manager.storage_manager.attachments_dir}")
    print(f"Storage info: {manager.get_storage_info()}")
    
    # クリーンアップテスト
    deleted = manager.cleanup_old_files()
    print(f"Cleanup: {deleted} files deleted")

if __name__ == "__main__":
    asyncio.run(test_attachment_manager())