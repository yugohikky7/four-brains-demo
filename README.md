# freee キャッシュフロー予測ダッシュボード

freee会計 / freee人事労務 のAPIから請求書・経費・給与データを取得し、向こう12ヶ月分のキャッシュフロー予測を生成するローカルWebアプリです。

- 売掛サイト・買掛サイトを考慮した入金・支払タイミングの自動展開
- 借入金の元利返済スケジュール
- 楽観／中立／悲観の3シナリオ比較
- 手動調整（仮払・税金支払・賞与・設備投資など）
- ブラウザで開くだけで最新の予測が見えるダッシュボード

freee Developersでの認証情報が無くても、付属の**Mockモード**で全機能をすぐに体験できます。

---

## 必要環境

- Python 3.10 以上
- ブラウザ（Chrome / Edge / Safari いずれか最新版）
- freee会計（法人プラン）と freee人事労務（同一アカウント推奨）
  - Mockモードのみであれば不要

---

## 1. インストール

```bash
cd freee_cashflow
python -m venv .venv
# Windowsの場合
.venv\Scripts\activate
# macOS / Linuxの場合
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 2. まずMockモードで起動して動作確認

freeeの認証情報を取得する前に、まずは動作確認を推奨いたします。

```bash
# Windowsの場合
copy .env.example .env
# macOS / Linuxの場合
cp .env.example .env

# サーバー起動
uvicorn app.main:app --reload --port 8765
```

ブラウザで <http://localhost:8765> を開くと、Mockデータで予測が表示されます。

---

## 3. freee Developersでのアプリ登録手順

実データを使う場合は、以下の手順でアプリ登録を行います。所要時間：約15-20分。

### 3-1. freee Developersに登録

1. <https://developer.freee.co.jp/> にアクセスし、画面右上の「アプリストアログイン」から、普段お使いのfreeeアカウントでログインします。
2. 初回の場合「freee for Developers」の利用規約に同意します。

### 3-2. アプリの新規作成

1. <https://app.secure.freee.co.jp/developers/applications> を開きます。
2. 「新規追加」をクリック。
3. 以下のように入力します。

   - **アプリ名**：任意（例：`社内キャッシュフロー予測`）
   - **概要**：任意（例：`社内のCF予測ツール`）
   - **アプリタイプ**：`プライベートアプリ` を選択（自社内利用のため）

4. 「作成」をクリック。

### 3-3. コールバックURLの設定

1. 作成したアプリ詳細画面 → 「基本設定」タブを開きます。
2. **コールバックURL** に以下を入力します：

   ```
   http://localhost:8765/oauth/callback
   ```

3. 「下書き保存」をクリックします。

### 3-4. 権限の設定

1. 同じく「アプリ詳細」画面で「権限設定」タブを開きます。
2. 以下のスコープを有効化します（**読み取り権限のみで充分**）：

   **freee会計**
   - 事業所：読み取り
   - 取引：読み取り
   - 請求書：読み取り
   - 経費精算：読み取り（任意）
   - 口座：読み取り
   - 取引先：読み取り
   - 勘定科目：読み取り

   **freee人事労務**
   - 事業所：読み取り
   - 従業員：読み取り
   - 給与明細：読み取り

3. 「下書き保存」をクリック。

### 3-5. Client ID / Client Secret を控える

1. 「基本設定」タブに戻ります。
2. **Client ID** と **Client Secret** をコピーします。

---

## 4. .env に認証情報を書く

`freee_cashflow/.env` をテキストエディタで開き、以下を設定します。

```env
# Mockモード（trueの場合はfreee APIを呼ばずダミーデータで動作）
MOCK_MODE=false

# freee Developersで取得したもの
FREEE_CLIENT_ID=ここにClient IDを貼り付け
FREEE_CLIENT_SECRET=ここにClient Secretを貼り付け
FREEE_REDIRECT_URI=http://localhost:8765/oauth/callback

# トークン暗号化用キー（uuidgenでも openssl rand -hex 32 でも可。一度設定したら変更しない）
APP_SECRET_KEY=ここに32文字以上のランダム文字列
```

`APP_SECRET_KEY` の生成例：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 5. freeeと連携してデータ取得

1. サーバーを再起動します。
2. ブラウザで <http://localhost:8765> を開きます。
3. 画面右上の「freeeと連携」ボタンをクリック。
4. freeeのログイン画面に遷移するのでログインし、対象事業所を選択して「許可する」をクリック。
5. 自動でダッシュボードに戻り、実データに基づくCF予測が表示されます。

トークンは `data/tokens.json` に暗号化されて保存されます。アクセストークン（6時間）はリフレッシュトークン（90日）で自動更新されます。

---

## 6. 主な機能の使い方

### キャッシュフロー予測表
- 月次×12ヶ月のCF予測が表形式で表示されます。
- 営業CF・投資CF・財務CFそれぞれの内訳が確認できます。

### 売掛・買掛サイトの設定
画面上部「設定」から、以下を入力できます。
- 売上回収サイト：何ヶ月後に入金するか（デフォルト：1ヶ月後）
- 仕入支払サイト：何ヶ月後に支払うか（デフォルト：2ヶ月後）

### 借入返済スケジュール
- 「借入金」タブから、借入残高・金利・返済方式（元利均等/元金均等）を入力。
- 月次の元金返済・利息支払が自動的にCFに反映されます。

### 手動調整
- 「手動調整」タブから、賞与・税金・設備投資など、APIに無い項目を月別に入力できます。
- 入力内容は `data/adjustments.json` に保存されます。

### シナリオ比較
- 画面上部「シナリオ」セレクタで切替。
- 楽観：売上+10%、原価-5%
- 中立：実績ベース
- 悲観：売上-15%、原価+5%
- 各シナリオの数値はカスタマイズ可能です。

---

## ファイル構成

```
freee_cashflow/
├── README.md             ← このファイル
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py           ← FastAPIエントリ
│   ├── config.py         ← 環境変数読み込み
│   ├── auth.py           ← OAuth2フロー・トークン管理
│   ├── freee_client.py   ← freee API クライアント
│   ├── forecast.py       ← CF予測エンジン
│   ├── scenarios.py      ← シナリオ計算
│   ├── loans.py          ← 借入返済スケジュール
│   ├── storage.py        ← JSON永続化
│   └── mock_data.py      ← Mockデータ
├── static/
│   ├── index.html        ← ダッシュボードUI
│   ├── style.css
│   └── app.js
└── data/                 ← 起動時に自動作成
    ├── tokens.json       ← 暗号化されたトークン
    ├── settings.json     ← サイト・シナリオ設定
    └── adjustments.json  ← 手動調整内容
```

---

## トラブルシューティング

### `port 8765 is already in use`
別のプロセスが同じポートを使っています。`--port 8800` など別のポートを指定するか、`.env` の `FREEE_REDIRECT_URI` も同様に書き換え、freee Developersのコールバック設定も更新してください。

### `Invalid grant` エラー
リフレッシュトークンが期限切れ（90日）または既に使用済みです。`data/tokens.json` を削除して、再度「freeeと連携」を行ってください。

### 給与データが取得できない
freee人事労務側で、APIアクセス権を持つ管理者ユーザーで連携を行ってください。一般従業員アカウントでは給与明細を取得できません。

### Mockモードに戻したい
`.env` の `MOCK_MODE=true` に変更してサーバーを再起動してください。

---

## セキュリティ上の注意

- このアプリは**ローカルでのみ動作**することを前提としています。`uvicorn` の `--host 0.0.0.0` 指定はお控えください。
- `data/tokens.json` はFernet（AES-128 CBC + HMAC-SHA256）で暗号化されますが、`APP_SECRET_KEY` を漏らさないようご注意ください。
- `.env` および `data/` は Git にコミットしないでください（同梱の `.gitignore` で除外済み）。

---

## ライセンス

社内利用を前提とした個別開発成果物です。
