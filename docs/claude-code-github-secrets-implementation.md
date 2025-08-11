# Claude Code GitHub Secrets 実装可能性調査

## 調査結果サマリー

### 現状
1. **GitHub Workflow Templates**: ../github-workflow-templatesは、tasksチャンネルでの!completeコマンド実行時に../{idea-name}をレポジトリ化する際に用いられるレポジトリのひな型であり、github actionsでclaude codeを用いるためのyamlファイルを含むものです。このyamlファイルがgithub actions上で実行されるためにはgithubレポジトリでclaude code oauth tokenの設定が必要です。
2. **GitHub連携**: `gh`コマンドを使用してリポジトリ作成とpushを実行
3. **Claude Code認証**: 定額プラン（max）ユーザーはOAuthトークンを使用

### 実装可能性: **可能**

## 実装方法

### 1. Claude Code OAuthトークンの取得

#### 重要な違い
- **API Key（sk-ant-api...）**: 従量課金プラン用
- **OAuth Token（sk-ant-oat01-...）**: 定額プラン用（maxプラン）

#### 推奨方法: credentials.jsonから取得
```bash
# ~/.claude/.credentials.jsonから既存のOAuthトークンを読み取る
# このファイルはClaude Codeへのログイン時に自動生成される
```

credentials.jsonの構造：
```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",  // これがGitHub Secretsに設定するトークン
    "refreshToken": "sk-ant-ort01-...", // リフレッシュ用（将来的な自動更新で使用）
    "expiresAt": 1785970807140,        // Unix timestamp（有効期限）
    "scopes": ["user:inference"],
    "subscriptionType": "max"           // 定額プラン
  }
}
```

#### 代替方法: claude setup-token（手動）
```bash
# ブラウザベースの対話的認証が必要
claude setup-token
# 注意: 自動化には向かない
```

### 2. GitHub Secretsへの設定

```bash
# リポジトリレベルでsecretを設定
gh secret set CLAUDE_CODE_OAUTH_TOKEN -b "$OAUTH_TOKEN" -R "owner/repo-name"

# または標準入力から
echo "$OAUTH_TOKEN" | gh secret set CLAUDE_CODE_OAUTH_TOKEN -R "owner/repo-name"
```

### 3. 実装案

`command_manager.py`の`_setup_development_environment`メソッドに以下を追加：

```python
import json
from datetime import datetime

async def _setup_github_secrets(self, repo_name: str, dev_path: Path) -> bool:
    """GitHub SecretsにClaude Code OAuthトークンを設定"""
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
        cmd = ["gh", "secret", "set", "CLAUDE_CODE_OAUTH_TOKEN", 
               "-b", access_token, "-R", f"{await self._get_github_user()}/{repo_name}"]
        
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
```

### 4. GitHub Workflow Template例

```yaml
name: Claude Code Analysis
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Claude Code
      run: |
        npm install -g @anthropic-ai/claude-code
        
    - name: Run Claude Code Analysis
      env:
        CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
      run: |
        # OAuthトークンを使用してClaude Codeを実行
        claude code analyze --token "$CLAUDE_CODE_OAUTH_TOKEN" --format github
```

## セキュリティ考慮事項

1. **OAuthトークンの保護**: 
   - ~/.claude/.credentials.jsonはパーミッション600で保護されている
   - トークンをログに出力しない
   - GitHub Secretsで暗号化保存

2. **権限の最小化**:
   - user:inferenceスコープのみ使用
   - リポジトリ単位でsecret管理

3. **有効期限管理**:
   - トークン設定前に有効期限をチェック
   - 期限切れの場合は警告を表示
   - 将来的にはrefreshTokenで自動更新を検討

4. **監査ログ**:
   - GitHub Secretsの設定・更新をログに記録
   - トークンの値自体はログに出力しない

## 実装手順

1. `_setup_github_secrets`メソッドの実装
2. `_setup_development_environment`内でGitHub push後にsecrets設定を呼び出し
3. エラーハンドリングとログ出力の実装
4. テストとドキュメント更新

## 注意事項

- このトークンは定額プラン（maxプラン）専用です
- 従量課金プランユーザーは`ANTHROPIC_API_KEY`を使用する必要があります
- `claude setup-token`コマンドはブラウザ認証が必要なため自動化には不向きです
- credentials.jsonのパスはプラットフォームによって異なる可能性があります