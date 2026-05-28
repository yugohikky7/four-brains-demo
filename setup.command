#!/bin/bash
# ============================================================
# freee キャッシュフロー予測ダッシュボード セットアップ (macOS)
# ダブルクリックで実行 (初回のみ)
# ============================================================

cd "$(dirname "$0")"

echo ""
echo "============================================================"
echo "  freee キャッシュフロー予測ダッシュボード セットアップ"
echo "============================================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[エラー] Python 3 が見つかりません。"
    echo "https://www.python.org/downloads/ からインストールしてください。"
    read -p "Enterキーで終了"
    exit 1
fi

echo "[1/3] 仮想環境を作成しています..."
if [ ! -d .venv ]; then
    python3 -m venv .venv || { echo "[エラー] 仮想環境作成失敗"; exit 1; }
fi
echo "      完了。"
echo ""

echo "[2/3] 依存ライブラリをインストールしています..."
echo "      初回は1〜2分かかります..."
source .venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt || { echo "[エラー] ライブラリ導入失敗"; exit 1; }
echo "      完了。"
echo ""

echo "[3/3] .env を確認しています..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "      .env.example をコピーしました。"
else
    echo "      既に .env が存在します（スキップ）。"
fi
echo ""

echo "============================================================"
echo "  セットアップ完了！"
echo "============================================================"
echo ""
echo "次のステップ:"
echo "  1. start.command をダブルクリックしてアプリを起動"
echo "  2. ブラウザで http://localhost:8765 を開く"
echo "  3. まずMockモードで動作確認してください"
echo ""
read -p "Enterキーで終了"
