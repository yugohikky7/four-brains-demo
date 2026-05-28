# Render.com デプロイ手順

このダッシュボードを Render.com に無料でデプロイする手順です。
所要時間: 約20分。

## 必要なもの
- GitHub アカウント (無料)
- Render.com アカウント (無料、GitHub でログイン可)

## 手順

### 1. GitHub にリポジトリを作成

1. https://github.com/new で新しいリポジトリを作成
   - リポジトリ名: `four-brains-demo` (お好きな名前で)
   - Public または Private を選択 (どちらでも可)
   - 「Create repository」をクリック

2. ローカルでこのフォルダ (`freee_cashflow/`) を Git で初期化して GitHub にプッシュ:
   ```cmd
   cd C:\Users\yugoh\Documents\Claude\Projects\会計及び労務\freee_cashflow
   git init
   git add .
   git commit -m "Initial demo deploy"
   git branch -M main
   git remote add origin https://github.com/<あなたのユーザー名>/four-brains-demo.git
   git push -u origin main
   ```

### 2. Render.com にサインアップ

1. https://render.com/ にアクセス
2. 右上「Get Started」→ 「GitHub でサインアップ」
3. GitHub の認可で Render に「リポジトリへのアクセス」を許可

### 3. Web Service を作成 (render.yaml で自動)

1. Render dashboard で右上「**+ New**」→ **Blueprint**
2. 先ほど作成した GitHub リポジトリを選択
3. 自動的に `render.yaml` が読み込まれ「`four-brains-demo`」サービスが作成されます
4. 「Apply」をクリック → ビルド開始 (5〜10分)

### 4. デプロイ完了後

- 自動で `https://four-brains-demo.onrender.com` (または末尾にランダム文字) のURLが発行されます
- URL は Render dashboard の対象サービスページ上部に表示されます
- そのURLを他社にシェアしてください

### 5. オプション: カスタムドメイン (有料、月7ドル〜)

- Render の Settings → Custom Domain で `demo.your-domain.com` 等に変更可能

## 注意事項

- **無料プラン**: 15分間アクセスがないとサーバが「スリープ」します。
  - スリープから復帰すると初回アクセスに 30〜60秒 程度かかります
  - 有料プラン($7/月) にすると常時起動
- **Mock モード固定**: `MOCK_MODE=true` で起動するため、実 freee には繋がりません
  - 「freee連携」ボタンは表示されますが、認可画面は demo-client-id で freee 側エラーになります
  - デモ目的のため、ボタンの存在を見せるだけで OK

## 更新方法

GitHub にプッシュすると Render が自動再デプロイ:
```cmd
git add .
git commit -m "Update demo"
git push
```

## URL を非公開にしたい場合

Render の Settings → Security → Basic Authentication で ID/PW 設定可能
