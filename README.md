# セッションハイジャックツール

指定したWEBサーバーに対してセッションハイジャックを実行し、SECRET_KEYを辞書攻撃で見つけるPythonツールです。

## 注意事項

⚠️ **このツールは教育目的および許可された環境でのみ使用してください。**
- 許可されていないサーバーに対する攻撃は違法です
- 自分のサーバーやCTF（Capture The Flag）などの許可された環境でのみ使用してください

## インストール

```bash
pip install -r requirements.txt
```

## 主な機能

### 1. SECRET_KEYの辞書攻撃
- デフォルトのSECRET_KEY候補リストを使用した自動攻撃
- 実際のHTTPリクエストでSECRET_KEYを検証
- 各候補を順次試行し、正しいSECRET_KEYを特定

### 2. セッションデータの偽造
- `_user_id`, `_fresh`, `_id`を含む標準的なFlask-Loginセッションデータ構造の生成
- 指定したユーザーIDでのセッション偽造
- Flaskの`SecureCookieSessionInterface`を使用した署名付きセッションクッキーの生成

### 3. プロフィールページへのアクセス
- 偽造したセッションクッキーを使用して`/profile`エンドポイントにアクセス
- 認証バイパスの成功/失敗を判定
- 成功した場合、HTMLをファイルに保存

### 4. 複数ユーザーIDのサポート
- 単一のユーザーIDまたは範囲（例: `1-5`）を指定可能
- 各ユーザーIDに対して個別にセッションハイジャックを実行
- 各ユーザーIDごとにHTMLファイルを保存

## 使用方法

### 基本的な使用方法

```bash
python 001session_hijack.py -u http://localhost:5000
```

### 特定のユーザーIDを指定

```bash
python 001session_hijack.py -u http://localhost:5000 -i 2
```

### ユーザーIDの範囲を指定

```bash
python 001session_hijack.py -u http://localhost:5000 -i 1-5
```

## オプション

- `-u, --url`: ターゲットURL（必須）
- `-i`: 攻撃対象のユーザーID（オプション、デフォルト: 1）。範囲指定可（例: 1-5）

## 動作原理

1. **コマンドライン引数の解析**: `argparse`を使用してターゲットURLとユーザーIDを取得
2. **ユーザーIDの範囲解析**: `-i`オプションで指定された範囲（例: `1-5`）をパースしてリストに変換
3. **SECRET_KEYの辞書攻撃**: デフォルトのSECRET_KEY候補リストを順次試行し、実際のHTTPリクエストで検証
4. **セッションデータの偽造**: `_user_id`, `_fresh`, `_id`を含む偽造セッションデータを生成
5. **Flaskセッションクッキーの生成**: `SecureCookieSessionInterface`を使用して署名付きのセッションクッキーを生成
6. **プロフィールページへのアクセス**: 偽造したセッションクッキーを使用して`/profile`エンドポイントにアクセス
7. **結果の判定**: レスポンスのステータスコードと内容を確認し、認証バイパスの成功/失敗を判定
8. **HTMLの保存**: 成功した場合、プロフィールページのHTMLを`profile_page_user_{id}.html`として保存

## コード解説

### 主要な関数

#### `parse_user_ids(user_id_str)`
ユーザーID文字列をパースしてリストを返す。`1-5`のような範囲指定の場合は、`['1', '2', '3', '4', '5']`のようなリストに変換。

#### `create_serializer(secret_key)`
Flaskアプリケーションを作成してセッションシリアライザーを取得。`SECRET_KEY`を使用してセッションクッキーの署名・検証に使用されるシリアライザーを返す。

#### `create_session_data(user_id)`
偽造するセッションデータを作成。Flaskの標準的なセッションデータ構造に合わせて、`_user_id`、`_fresh`、`_id`を含む辞書を返す。

#### `discover_secret_key(secret_keys, target_url, test_user_id)`
SECRET_KEYを総当たりで特定。各SECRET_KEY候補に対して実際のHTTPリクエストを送信して検証し、成功したSECRET_KEYを返す。

#### `test_secret_key(secret_key, target_url, test_user_id)`
SECRET_KEYをテストして有効性を確認。生成したセッションクッキーで実際にリクエストを送信し、成功判定を行う。

#### `hijack_user_session(user_id, serializer, target_url)`
指定されたユーザーIDでセッションハイジャックを実行。偽造したセッションクッキーを使用してプロフィールページにアクセスし、成功した場合はHTMLを保存。

#### `is_attack_successful(response)`
レスポンスから攻撃成功を判定。ステータスコード200でログインページでない場合、または302で`/login`以外へのリダイレクトの場合、成功と判定。

#### `make_request_with_cookie(cookie, target_url)`
セッションクッキーでリクエストを送信。偽造したセッションクッキーを設定して`/profile`エンドポイントにアクセス。

## 対応フレームワーク

- Flask（`SecureCookieSessionInterface`を使用）

## デフォルトのSECRET_KEY候補

コード内で定義されているデフォルトのSECRET_KEY候補リスト：

```python
SECRET_KEYS = [
    "secret",
    "secret-key",
    "testkey",
    "ecre-key",
    "your-secret-key-change-in-production",
    "secret-keys",
]
```

これらの候補を順次試行し、実際のHTTPリクエストで検証します。

## セッションハイジャックの技術的詳細

### 全体フロー

```
SECRET_KEY発見
    ↓
Flaskアプリケーションの設定
    ↓
セッションシリアライザーの取得
    ↓
偽造セッションデータの作成
    ↓
セッションクッキーの生成（署名付き）
    ↓
HTTPリクエストの送信（クッキー付き）
    ↓
サーバー側での検証と認証バイパス
    ↓
保護されたリソースへのアクセス成功
```

### セッションクッキーの生成プロセス

1. **セッションデータの作成**: `{"_user_id": user_id, "_fresh": True, "_id": user_id}`形式の辞書を作成
2. **JSONエンコード**: セッションデータをJSON形式に変換
3. **Base64エンコード**: JSON文字列をBase64エンコード
4. **HMAC署名の生成**: `SECRET_KEY`を使用してHMAC-SHA1署名を生成
5. **結合**: `{base64_data}.{timestamp}.{signature}`の形式で結合

生成されるクッキーの形式:
```
eyJfdXNlcl9pZCI6IjEiLCJfZnJlc2giOnRydWUsIl9pZCI6IjEifQ.aS66_g.kPRYHYEhk4vpdOw-XJdsiPsZY34
│─────────── Base64エンコードされたセッションデータ ───────────││timestamp││─── HMAC署名 ───│
```

### サーバー側での検証プロセス

1. **クッキーの受信**: HTTPリクエストから`session`クッキーを取得
2. **署名の検証**: サーバーの`SECRET_KEY`を使用してHMAC署名を再計算し、クッキーに含まれる署名と比較
3. **セッションデータの復号**: 署名が有効な場合、Base64デコードとJSONデコードを実行してセッションデータを取得
4. **認証チェック**: `_user_id`が存在する場合、そのユーザーとして認証済みとみなす

### SECRET_KEYが固定値の場合の危険性

SECRET_KEYが固定値（推測可能または漏洩）の場合、任意のユーザーIDを指定してセッションクッキーを偽造し、そのユーザーになりすましてログインできます。

**なぜこれが可能なのか**:
- Flaskのセッションクッキーは、SECRET_KEYを使用したHMAC署名によって改ざんを防いでいます
- サーバーは、クッキーに含まれる署名が正しいかどうかだけを検証します
- クッキー内の`_user_id`が実際にログインしたユーザーのIDかどうかは検証しません
- 署名の有効性は、SECRET_KEYが秘密であることに依存しています

**攻撃の流れ**:
1. **SECRET_KEYの取得**: 辞書攻撃や情報漏洩により、サーバーのSECRET_KEYを特定
2. **セッションデータの偽造**: 任意のユーザーIDを指定したセッションデータを作成
3. **署名付きクッキーの生成**: 取得したSECRET_KEYを使用して署名を生成
4. **なりすましの実行**: 偽造したクッキーをHTTPリクエストに含めて送信し、保護されたリソースにアクセス

**防御策**:
- 強力でランダムな`SECRET_KEY`を使用（推測不可能な長いランダム文字列）
- 環境変数やシークレット管理サービスを使用してSECRET_KEYを保護
- セッションクッキーに追加の検証（IPアドレス、User-Agent、セッションタイムスタンプなど）を実装
- セッションIDをランダムで予測不可能な値にする（ユーザーIDをそのまま使用しない）
- セッションタイムアウトを適切に設定
- セッションストア（Redis、データベース）を使用し、サーバー側でセッションの有効性を管理
- 定期的にSECRET_KEYをローテーション（ただし、既存セッションが無効化されることに注意）

## ライセンス

教育目的のみ。使用は自己責任でお願いします。
