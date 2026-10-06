import os
import json
import re
import time
from datetime import datetime
from database.supabase import get_supabase
from utils.constants import MOCK_CATEGORIES, MOCK_SUBCATEGORIES

CATEGORIES_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'categories_data.json')
SUBCATEGORIES_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'subcategories_data.json')

_LOCAL_CATEGORIES = None
_LOCAL_SUBCATEGORIES = None

def generate_slug(text):
    if not text:
        return ''
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', str(text)).strip().lower()
    return re.sub(r'[\s-]+', '-', slug)

def format_record(record):
    """Ensure record has _id field for template backward compatibility."""
    if isinstance(record, dict):
        rec_id = str(record.get('id') or record.get('_id') or '')
        if rec_id:
            record['id'] = rec_id
            record['_id'] = rec_id
        elif 'slug' in record:
            record['id'] = record['slug']
            record['_id'] = record['slug']
        if 'is_active' not in record:
            record['is_active'] = True
    return record

def _load_local_categories():
    global _LOCAL_CATEGORIES
    if _LOCAL_CATEGORIES is not None:
        return _LOCAL_CATEGORIES

    # Try GitHub storage first
    try:
        from services.github_storage import GithubStorageService
        gh_cats = GithubStorageService.get_categories()
        if gh_cats and isinstance(gh_cats, list) and len(gh_cats) > 0:
            _LOCAL_CATEGORIES = [format_record(c) for c in gh_cats]
            return _LOCAL_CATEGORIES
    except Exception as e:
        print(f"⚠️ Notice reading GitHub storage categories: {e}")

    if os.path.exists(CATEGORIES_FILE_PATH):
        try:
            with open(CATEGORIES_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    _LOCAL_CATEGORIES = [format_record(c) for c in data]
                    return _LOCAL_CATEGORIES
        except Exception as e:
            print(f"⚠️ Notice reading {CATEGORIES_FILE_PATH}: {e}")

    # Initialize from MOCK_CATEGORIES
    _LOCAL_CATEGORIES = [format_record(c.copy()) for c in MOCK_CATEGORIES]
    _save_local_categories()
    return _LOCAL_CATEGORIES

def _save_local_categories():
    global _LOCAL_CATEGORIES
    if _LOCAL_CATEGORIES is None:
        return
    try:
        with open(CATEGORIES_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(_LOCAL_CATEGORIES, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error saving categories to {CATEGORIES_FILE_PATH}: {e}")

    try:
        from services.github_storage import GithubStorageService
        GithubStorageService.save_categories(_LOCAL_CATEGORIES)
    except Exception as e:
        print(f"⚠️ Notice saving categories to GitHub storage: {e}")

def _load_local_subcategories():
    global _LOCAL_SUBCATEGORIES
    if _LOCAL_SUBCATEGORIES is not None:
        return _LOCAL_SUBCATEGORIES

    # Try GitHub storage first
    try:
        from services.github_storage import GithubStorageService
        gh_subs = GithubStorageService.get_subcategories()
        if gh_subs and isinstance(gh_subs, list) and len(gh_subs) > 0:
            _LOCAL_SUBCATEGORIES = [format_record(s) for s in gh_subs]
            return _LOCAL_SUBCATEGORIES
    except Exception as e:
        print(f"⚠️ Notice reading GitHub storage subcategories: {e}")

    if os.path.exists(SUBCATEGORIES_FILE_PATH):
        try:
            with open(SUBCATEGORIES_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    _LOCAL_SUBCATEGORIES = [format_record(s) for s in data]
                    return _LOCAL_SUBCATEGORIES
        except Exception as e:
            print(f"⚠️ Notice reading {SUBCATEGORIES_FILE_PATH}: {e}")

    # Initialize from MOCK_SUBCATEGORIES
    _LOCAL_SUBCATEGORIES = [format_record(s.copy()) for s in MOCK_SUBCATEGORIES]
    _save_local_subcategories()
    return _LOCAL_SUBCATEGORIES

def _save_local_subcategories():
    global _LOCAL_SUBCATEGORIES
    if _LOCAL_SUBCATEGORIES is None:
        return
    try:
        with open(SUBCATEGORIES_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(_LOCAL_SUBCATEGORIES, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error saving subcategories to {SUBCATEGORIES_FILE_PATH}: {e}")

    try:
        from services.github_storage import GithubStorageService
        GithubStorageService.save_subcategories(_LOCAL_SUBCATEGORIES)
    except Exception as e:
        print(f"⚠️ Notice saving subcategories to GitHub storage: {e}")

class CategoryService:
    @staticmethod
    def get_all(business_slug=None):
        cats = _load_local_categories()
        client = get_supabase()

        if client is not None:
            try:
                query = client.table('categories').select('*').eq('is_active', True)
                if business_slug:
                    query = query.eq('business_slug', business_slug)
                res = query.order('order', desc=False).execute()
                if res.data and len(res.data) > 0:
                    remote_slugs = {c['slug'] for c in res.data if 'slug' in c}
                    merged = [format_record(c) for c in res.data]
                    for lc in cats:
                        if lc.get('slug') not in remote_slugs:
                            if not business_slug or lc.get('business_slug') == business_slug:
                                merged.append(format_record(lc))
                    return merged
            except Exception as e:
                print(f"CategoryService.get_all remote error: {e}")

        results = [c for c in cats if c.get('is_active', True)]
        if business_slug:
            results = [c for c in results if c.get('business_slug') == business_slug]
        return [format_record(c) for c in results]

    @staticmethod
    def get_by_slug(slug):
        client = get_supabase()
        if client is not None:
            try:
                res = client.table('categories').select('*').eq('slug', slug).eq('is_active', True).limit(1).execute()
                if res.data:
                    return format_record(res.data[0])
            except Exception as e:
                print(f"CategoryService.get_by_slug remote error: {e}")

        cats = _load_local_categories()
        for c in cats:
            if c.get('slug') == slug:
                return format_record(c)
        return format_record(cats[0]) if cats else None

    @staticmethod
    def create(data):
        if not data or not data.get('name'):
            return None

        name = str(data['name']).strip()
        biz_slug = data.get('business_slug', 'hardware')
        base_slug = data.get('slug') or generate_slug(name)

        cats = _load_local_categories()
        existing = next((c for c in cats if c.get('slug') == base_slug and c.get('business_slug') == biz_slug), None)
        if existing:
            existing['is_active'] = True
            _save_local_categories()
            return format_record(existing)

        # Ensure slug uniqueness if collision with another store
        slug = base_slug
        if any(c.get('slug') == slug for c in cats):
            slug = f"{slug}-{biz_slug}"

        cat_id = data.get('id') or f"cat_{int(time.time() * 1000)}"
        cat_record = {
            'id': cat_id,
            '_id': cat_id,
            'name': name,
            'slug': slug,
            'business_slug': biz_slug,
            'description': data.get('description', ''),
            'icon': data.get('icon', '📦'),
            'order': len(cats) + 1,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }

        cats.append(cat_record)
        _save_local_categories()

        # Automatically create a default subcategory/element for this category
        subcat_name = data.get('subcategory_name') or data.get('first_subcategory_name') or f"General {name}"
        subcat_slug = generate_slug(subcat_name)
        SubcategoryService.create({
            'name': subcat_name,
            'slug': subcat_slug,
            'category_slug': slug,
            'business_slug': biz_slug,
            'icon': '📦'
        })

        # Also insert into Supabase if connected
        client = get_supabase()
        if client is not None:
            try:
                client.table('categories').insert({
                    'name': name,
                    'slug': slug,
                    'business_slug': biz_slug,
                    'description': cat_record['description'],
                    'icon': cat_record['icon'],
                    'is_active': True,
                    'order': cat_record['order'],
                    'created_at': cat_record['created_at']
                }).execute()
            except Exception as e:
                print(f"CategoryService.create remote error: {e}")

        return format_record(cat_record)

    @staticmethod
    def delete(category_slug):
        cats = _load_local_categories()
        str_slug = str(category_slug).strip()
        cat = next((c for c in cats if c.get('slug') == str_slug or c.get('id') == str_slug or c.get('_id') == str_slug), None)
        if not cat:
            return {'success': False, 'message': f'Category "{str_slug}" not found'}

        cat_slug = cat.get('slug')
        cat_name = cat.get('name', 'Category')

        # 1. Move all products in this category to staging area (uncategorized state)
        from services.product_service import ProductService
        moved_count = ProductService.move_category_products_to_staging(cat_slug)

        # 2. Remove all subcategories for this category
        subs = _load_local_subcategories()
        remaining_subs = [s for s in subs if s.get('category_slug') != cat_slug and s.get('category_id') != cat_slug]
        global _LOCAL_SUBCATEGORIES
        _LOCAL_SUBCATEGORIES = remaining_subs
        _save_local_subcategories()

        # 3. Remove category from categories list
        global _LOCAL_CATEGORIES
        _LOCAL_CATEGORIES = [c for c in cats if c.get('slug') != cat_slug and c.get('id') != cat_slug and c.get('_id') != cat_slug]
        _save_local_categories()

        # 4. Clean up in Supabase if online
        client = get_supabase()
        if client is not None:
            try:
                client.table('categories').delete().eq('slug', cat_slug).execute()
                client.table('subcategories').delete().eq('category_slug', cat_slug).execute()
            except Exception as e:
                print(f"CategoryService.delete remote error: {e}")

        return {
            'success': True,
            'ok': True,
            'category': cat,
            'moved_count': moved_count,
            'message': f'Category "{cat_name}" deleted. {moved_count} product(s) moved to Staging Area.'
        }

    @classmethod
    def create_category(cls, name, business_slug='hardware', first_subcategory_name=None):
        cat = cls.create({
            'name': name,
            'business_slug': business_slug,
            'subcategory_name': first_subcategory_name
        })
        subs = SubcategoryService.get_by_category(cat.get('slug')) if cat else []
        sub = subs[0] if subs else None
        return cat, sub


class SubcategoryService:
    @staticmethod
    def get_by_category(category_id_or_slug):
        client = get_supabase()
        str_id = str(category_id_or_slug)
        if client is not None:
            try:
                res = client.table('subcategories').select('*')\
                    .or_(f"category_id.eq.{str_id},category_slug.eq.{str_id}")\
                    .eq('is_active', True)\
                    .order('order', desc=False).execute()
                if res.data and len(res.data) > 0:
                    return [format_record(s) for s in res.data]
            except Exception as e:
                print(f"SubcategoryService.get_by_category remote error: {e}")

        subs = _load_local_subcategories()
        return [format_record(s) for s in subs if s.get('category_slug') == str_id or s.get('category_id') == str_id]

    @staticmethod
    def get_by_business(business_slug):
        client = get_supabase()
        if client is not None:
            try:
                res = client.table('subcategories').select('*').eq('business_slug', business_slug).eq('is_active', True).order('order', desc=False).execute()
                if res.data and len(res.data) > 0:
                    return [format_record(s) for s in res.data]
            except Exception as e:
                print(f"SubcategoryService.get_by_business remote error: {e}")

        subs = _load_local_subcategories()
        return [format_record(s) for s in subs if s.get('business_slug') == business_slug]

    @staticmethod
    def get_by_slug(slug):
        client = get_supabase()
        if client is not None:
            try:
                res = client.table('subcategories').select('*').eq('slug', slug).eq('is_active', True).limit(1).execute()
                if res.data:
                    return format_record(res.data[0])
            except Exception as e:
                print(f"SubcategoryService.get_by_slug remote error: {e}")

        subs = _load_local_subcategories()
        for s in subs:
            if s.get('slug') == slug:
                return format_record(s)
        return None

    @staticmethod
    def get_all():
        client = get_supabase()
        if client is not None:
            try:
                res = client.table('subcategories').select('*').eq('is_active', True).order('order', desc=False).execute()
                if res.data and len(res.data) > 0:
                    return [format_record(s) for s in res.data]
            except Exception as e:
                print(f"SubcategoryService.get_all remote error: {e}")

        subs = _load_local_subcategories()
        return [format_record(s) for s in subs if s.get('is_active', True)]

    @staticmethod
    def create(data):
        if not data or not data.get('name'):
            return None

        name = str(data['name']).strip()
        slug = data.get('slug') or generate_slug(name)
        subs = _load_local_subcategories()

        existing = next((s for s in subs if s.get('slug') == slug), None)
        if existing:
            return format_record(existing)

        sub_id = data.get('id') or f"subcat_{int(time.time() * 1000)}"
        sub_record = {
            'id': sub_id,
            '_id': sub_id,
            'name': name,
            'slug': slug,
            'category_slug': data.get('category_slug', ''),
            'business_slug': data.get('business_slug', ''),
            'icon': data.get('icon', '📦'),
            'order': len(subs) + 1,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        subs.append(sub_record)
        _save_local_subcategories()

        client = get_supabase()
        if client is not None:
            try:
                client.table('subcategories').insert({
                    'name': name,
                    'slug': slug,
                    'category_slug': sub_record['category_slug'],
                    'business_slug': sub_record['business_slug'],
                    'icon': sub_record['icon'],
                    'order': sub_record['order'],
                    'is_active': True,
                    'created_at': sub_record['created_at']
                }).execute()
            except Exception as e:
                print(f"SubcategoryService.create remote error: {e}")

        return format_record(sub_record)

    @staticmethod
    def delete(subcategory_slug):
        subs = _load_local_subcategories()
        str_slug = str(subcategory_slug).strip()
        sub = next((s for s in subs if s.get('slug') == str_slug or s.get('id') == str_slug), None)
        if not sub:
            return {'success': False, 'message': 'Element not found'}
        global _LOCAL_SUBCATEGORIES
        _LOCAL_SUBCATEGORIES = [s for s in subs if s.get('slug') != str_slug and s.get('id') != str_slug]
        _save_local_subcategories()

        client = get_supabase()
        if client is not None:
            try:
                client.table('subcategories').delete().eq('slug', str_slug).execute()
            except Exception as e:
                pass
        return {'success': True, 'ok': True, 'subcategory': sub}
