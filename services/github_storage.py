import os
import json
import time
import base64
import requests
from flask import current_app

DATA_FILE_REL_PATH = 'database/products_data.json'

class GithubStorageService:
    _cached_products = None
    _cache_timestamp = 0
    CACHE_TTL_SECONDS = 30

    @classmethod
    def _get_config(cls):
        token = os.getenv('GITHUB_TOKEN', '')
        repo = os.getenv('GITHUB_REPO', 'rohit-r-20/Sathik')
        branch = os.getenv('GITHUB_BRANCH', 'main')

        if not token and current_app:
            token = current_app.config.get('GITHUB_TOKEN', '')
            repo = current_app.config.get('GITHUB_REPO', repo)
            branch = current_app.config.get('GITHUB_BRANCH', branch)

        return token.strip(), repo.strip(), branch.strip()

    @classmethod
    def is_configured(cls):
        token, _, _ = cls._get_config()
        return bool(token and len(token) > 8)

    @classmethod
    def clear_cache(cls):
        cls._cached_products = None
        cls._cache_timestamp = 0

    @classmethod
    def get_products(cls):
        """
        Fetches products from in-memory cache, GitHub repository, or local JSON fallback.
        """
        now = time.time()
        if cls._cached_products is not None and (now - cls._cache_timestamp) < cls.CACHE_TTL_SECONDS:
            return cls._cached_products

        token, repo, branch = cls._get_config()

        # 1. Try GitHub API if configured
        if cls.is_configured():
            try:
                url = f"https://api.github.com/repos/{repo}/contents/{DATA_FILE_REL_PATH}?ref={branch}"
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Sathik-Vercel-App'
                }
                resp = requests.get(url, headers=headers, timeout=6)
                if resp.status_code == 200:
                    data_json = resp.json()
                    content_b64 = data_json.get('content', '')
                    raw_bytes = base64.b64decode(content_b64)
                    products = json.loads(raw_bytes.decode('utf-8'))
                    if isinstance(products, list):
                        cls._cached_products = products
                        cls._cache_timestamp = now
                        return products
                else:
                    print(f"⚠️ GitHub API returned status {resp.status_code} reading products: {resp.text[:120]}")
            except Exception as e:
                print(f"⚠️ GitHub storage read error: {e}")

            # 2. Try raw fallback
            try:
                raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{DATA_FILE_REL_PATH}?t={int(now)}"
                headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'Sathik-Vercel-App'}
                raw_resp = requests.get(raw_url, headers=headers, timeout=5)
                if raw_resp.status_code == 200:
                    products = raw_resp.json()
                    if isinstance(products, list):
                        cls._cached_products = products
                        cls._cache_timestamp = now
                        return products
            except Exception as e:
                print(f"⚠️ GitHub raw content read error: {e}")

        # 3. Local fallback (disk)
        local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'products_data.json')
        if os.path.exists(local_path):
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    products = json.load(f)
                    if isinstance(products, list):
                        cls._cached_products = products
                        cls._cache_timestamp = now
                        return products
            except Exception as e:
                print(f"⚠️ Local disk read error: {e}")

        return []

    @classmethod
    def save_products(cls, products_list):
        """
        Saves products to GitHub repository via GitHub REST API commit,
        and updates in-memory cache immediately.
        """
        cls._cached_products = products_list
        cls._cache_timestamp = time.time()

        # Save to local disk if running locally or writable
        local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'products_data.json')
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump(products_list, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Ephemeral Vercel filesystem notice
            print(f"ℹ️ Local disk save notice (ephemeral): {e}")

        token, repo, branch = cls._get_config()
        if not cls.is_configured():
            print("⚠️ Notice: GITHUB_TOKEN not configured. Products saved locally only.")
            return True, "Saved locally"

        try:
            url = f"https://api.github.com/repos/{repo}/contents/{DATA_FILE_REL_PATH}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Sathik-Vercel-App'
            }

            # Fetch current file SHA
            sha = None
            get_resp = requests.get(f"{url}?ref={branch}", headers=headers, timeout=6)
            if get_resp.status_code == 200:
                sha = get_resp.json().get('sha')

            content_str = json.dumps(products_list, indent=2, ensure_ascii=False)
            content_b64 = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')

            payload = {
                "message": f"feat(catalogue): update product list via admin [{len(products_list)} items]",
                "content": content_b64,
                "branch": branch
            }
            if sha:
                payload["sha"] = sha

            put_resp = requests.put(url, headers=headers, json=payload, timeout=10)
            if put_resp.status_code in (200, 201):
                print(f"✅ Products committed successfully to GitHub repo {repo} ({branch})")
                return True, "Committed to GitHub"
            else:
                err_msg = f"GitHub commit failed ({put_resp.status_code}): {put_resp.text[:160]}"
                print(f"❌ {err_msg}")
                return False, err_msg
        except Exception as e:
            err_msg = f"GitHub save exception: {e}"
            print(f"❌ {err_msg}")
            return False, err_msg

    @classmethod
    def save_json_file(cls, rel_path, data, commit_message):
        """
        Saves any JSON data to local disk and commits to GitHub if configured.
        """
        local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel_path)
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"ℹ️ Local disk save notice for {rel_path}: {e}")

        token, repo, branch = cls._get_config()
        if not cls.is_configured():
            return True, "Saved locally"

        try:
            url = f"https://api.github.com/repos/{repo}/contents/{rel_path}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Sathik-Vercel-App'
            }

            sha = None
            get_resp = requests.get(f"{url}?ref={branch}", headers=headers, timeout=6)
            if get_resp.status_code == 200:
                sha = get_resp.json().get('sha')

            content_str = json.dumps(data, indent=2, ensure_ascii=False)
            content_b64 = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')

            payload = {
                "message": commit_message,
                "content": content_b64,
                "branch": branch
            }
            if sha:
                payload["sha"] = sha

            put_resp = requests.put(url, headers=headers, json=payload, timeout=10)
            if put_resp.status_code in (200, 201):
                print(f"✅ {rel_path} committed to GitHub repo {repo} ({branch})")
                return True, "Committed to GitHub"
            else:
                return False, f"GitHub commit failed ({put_resp.status_code})"
        except Exception as e:
            return False, str(e)

    @classmethod
    def upload_image(cls, file_bytes, filename):
        """
        Commits an uploaded image to static/uploads/ in the GitHub repository,
        returning a globally accessible permanent URL.
        """
        token, repo, branch = cls._get_config()

        # If GitHub not configured, save locally if writable
        if not cls.is_configured():
            try:
                local_upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads')
                os.makedirs(local_upload_dir, exist_ok=True)
                local_path = os.path.join(local_upload_dir, filename)
                with open(local_path, 'wb') as f:
                    f.write(file_bytes)
            except Exception as e:
                print(f"ℹ️ Local write bypassed on read-only serverless: {e}")
            return True, f"/static/uploads/{filename}"

        try:
            rel_path = f"static/uploads/{filename}"
            url = f"https://api.github.com/repos/{repo}/contents/{rel_path}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Sathik-Vercel-App'
            }

            sha = None
            get_resp = requests.get(f"{url}?ref={branch}", headers=headers, timeout=6)
            if get_resp.status_code == 200:
                sha = get_resp.json().get('sha')

            content_b64 = base64.b64encode(file_bytes).decode('utf-8')
            payload = {
                "message": f"feat(upload): add product image {filename}",
                "content": content_b64,
                "branch": branch
            }
            if sha:
                payload["sha"] = sha

            put_resp = requests.put(url, headers=headers, json=payload, timeout=10)
            if put_resp.status_code in (200, 201):
                # Permanent raw URL accessible immediately worldwide
                raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{rel_path}"
                print(f"✅ Image {filename} committed to GitHub: {raw_url}")
                return True, raw_url
            else:
                print(f"⚠️ GitHub image upload status {put_resp.status_code}: {put_resp.text[:120]}")
                # Fallback to local URL path
                return True, f"/static/uploads/{filename}"
        except Exception as e:
            print(f"⚠️ Image commit exception: {e}")
            return True, f"/static/uploads/{filename}"
