#!/bin/bash

# プロジェクト移行スクリプト
# 間違った場所にあるプロジェクトを正しい場所に移動

echo "==================================="
echo "プロジェクト移行スクリプト"
echo "==================================="
echo ""

PROJECT_WSL="/home/seito_nakagane/project-wsl"
WRONG_DIR="$PROJECT_WSL/achi-kun"

# 間違ったディレクトリが存在するか確認
if [ ! -d "$WRONG_DIR" ]; then
    echo "✅ 移行の必要はありません。$WRONG_DIR が存在しません。"
    exit 0
fi

echo "📁 間違った場所にあるプロジェクト："
ls -la "$WRONG_DIR"
echo ""

# 各プロジェクトを移動
for project in "$WRONG_DIR"/*; do
    if [ -d "$project" ]; then
        project_name=$(basename "$project")
        target_path="$PROJECT_WSL/$project_name"
        
        echo "🔄 $project_name を移動中..."
        
        # ターゲットが既に存在する場合の確認
        if [ -d "$target_path" ]; then
            echo "  ⚠️  $target_path は既に存在します"
            echo "  スキップするか、手動で確認してください"
            continue
        fi
        
        # プロジェクトを移動
        mv "$project" "$target_path"
        
        if [ $? -eq 0 ]; then
            echo "  ✅ $project_name を正しい場所に移動しました"
            echo "     新しいパス: $target_path"
        else
            echo "  ❌ $project_name の移動に失敗しました"
        fi
        echo ""
    fi
done

# 空になったachi-kunディレクトリを削除
if [ -z "$(ls -A "$WRONG_DIR")" ]; then
    echo "🗑️  空になった $WRONG_DIR を削除します..."
    rmdir "$WRONG_DIR"
    if [ $? -eq 0 ]; then
        echo "✅ ディレクトリを削除しました"
    else
        echo "❌ ディレクトリの削除に失敗しました"
    fi
else
    echo "⚠️  $WRONG_DIR はまだ空ではありません："
    ls -la "$WRONG_DIR"
fi

echo ""
echo "==================================="
echo "移行完了"
echo "==================================="
echo ""
echo "現在のproject-wslディレクトリ構造："
ls -la "$PROJECT_WSL" | grep "^d" | grep -v "^\."