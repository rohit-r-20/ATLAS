import os
import json
import re
from datetime import datetime
from database.supabase import get_supabase
from utils.constants import BRANDS_LIST

BRANDS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'brands_data.json')

_LOCAL_BRANDS = None

def generate_slug(text):
    if not text:
        return ''
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', str(text)).strip().lower()
    return re.sub(r'[\s-]+', '-', slug)

def format_record(record):
    """Ensure record has _id and id fields for template backward compatibility."""
    if isinstance(record, dict):
        rec_id = str(record.get('id') or record.get('_id') or record.get('slug') or '')
        if rec_id:
            record['id'] = rec_id
            record['_id'] = rec_id
        if 'is_active' not in record:
            record['is_active'] = True
        if 'businesses' not in record or not isinstance(record.get('businesses'), list):
            record['businesses'] = []
        if 'country' not in record or not record.get('country'):
            record['country'] = 'India'
        if 'featured' not in record:
            record['featured'] = False
        if 'logo' not in record:
            record['logo'] = f"/static/images/brands/{record.get('slug', '')}.png"
    return record

_LOCAL_BRANDS_MTIME = 0

def _load_local_brands(force_reload=False):
    global _LOCAL_BRANDS, _LOCAL_BRANDS_MTIME
    try:
        mtime = os.path.getmtime(BRANDS_FILE_PATH) if os.path.exists(BRANDS_FILE_PATH) else 0
    except OSError:
        mtime = 0

    if not force_reload and _LOCAL_BRANDS is not None and mtime == _LOCAL_BRANDS_MTIME:
        return _LOCAL_BRANDS

    if os.path.exists(BRANDS_FILE_PATH):
        try:
            with open(BRANDS_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    _LOCAL_BRANDS = [format_record(b) for b in data]
                    _LOCAL_BRANDS_MTIME = mtime
                    return _LOCAL_BRANDS
        except Exception as e:
            print(f"⚠️ Notice reading {BRANDS_FILE_PATH}: {e}")

    # Fallback to BRANDS_LIST from constants
    _LOCAL_BRANDS = []
    for idx, b in enumerate(BRANDS_LIST):
        item = b.copy()
        item['id'] = item.get('slug')
        item['_id'] = item.get('slug')
        item['is_active'] = True
        item['order'] = idx + 1
        item['logo'] = f"/static/images/brands/{item['slug']}.png"
        _LOCAL_BRANDS.append(format_record(item))
    _save_local_brands()
    return _LOCAL_BRANDS

def _save_local_brands():
    global _LOCAL_BRANDS
    if _LOCAL_BRANDS is None:
        return
    try:
        os.makedirs(os.path.dirname(BRANDS_FILE_PATH), exist_ok=True)
        with open(BRANDS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(_LOCAL_BRANDS, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error saving brands to {BRANDS_FILE_PATH}: {e}")


class BrandService:
    @staticmethod
    def get_all(featured_only=False, business_slug=None, search=None, is_active_only=True):
        client = get_supabase()
        if client is not None:
            try:
                query = client.table('brands').select('*')
                if is_active_only:
                    query = query.eq('is_active', True)
                if featured_only:
                    query = query.eq('featured', True)
                if business_slug:
                    query = query.contains('businesses', [business_slug])

                res = query.order('name', desc=False).execute()
                if res.data and len(res.data) > 0:
                    data = [format_record(b) for b in res.data]
                    if search:
                        s_lower = search.lower().strip()
                        data = [b for b in data if s_lower in b.get('name', '').lower() or s_lower in b.get('slug', '').lower()]
                    return data
            except Exception as e:
                print(f"BrandService.get_all remote error: {e}")

        brands = _load_local_brands()
        results = brands.copy()
        if is_active_only:
            results = [b for b in results if b.get('is_active', True)]
        if featured_only:
            results = [b for b in results if b.get('featured')]
        if business_slug:
            results = [b for b in results if business_slug in b.get('businesses', [])]
        if search:
            s_lower = search.lower().strip()
            results = [b for b in results if s_lower in b.get('name', '').lower() or s_lower in b.get('slug', '').lower() or s_lower in b.get('country', '').lower()]

        # Sort alphabetically by name
        results.sort(key=lambda x: x.get('name', '').lower())
        return [format_record(b) for b in results]

    @staticmethod
    def get_by_slug(slug):
        if not slug:
            return None
        slug_clean = slug.strip().lower()

        client = get_supabase()
        if client is not None:
            try:
                res = client.table('brands').select('*').eq('slug', slug_clean).limit(1).execute()
                if res.data:
                    return format_record(res.data[0])
            except Exception as e:
                print(f"BrandService.get_by_slug error: {e}")

        brands = _load_local_brands()
        for b in brands:
            if b.get('slug', '').lower() == slug_clean:
                return format_record(b.copy())
        return None

    @staticmethod
    def get_by_id(brand_id):
        if not brand_id:
            return None
        str_id = str(brand_id).strip()

        client = get_supabase()
        if client is not None:
            try:
                res = client.table('brands').select('*').eq('id', str_id).limit(1).execute()
                if res.data:
                    return format_record(res.data[0])
            except Exception as e:
                print(f"BrandService.get_by_id error: {e}")

        brands = _load_local_brands()
        for b in brands:
            if str(b.get('id', '')) == str_id or str(b.get('_id', '')) == str_id or b.get('slug', '').lower() == str_id.lower():
                return format_record(b.copy())
        return None

    @staticmethod
    def create(data):
        if not data or not data.get('name'):
            return None

        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip() or generate_slug(name)
        now = datetime.utcnow().isoformat()

        brand_record = {
            'id': slug,
            '_id': slug,
            'name': name,
            'slug': slug,
            'businesses': data.get('businesses', ['hardware']),
            'featured': bool(data.get('featured', False)),
            'country': data.get('country', 'India').strip() or 'India',
            'logo': data.get('logo', f"/static/images/brands/{slug}.png"),
            'description': data.get('description', '').strip(),
            'website': data.get('website', '').strip(),
            'is_active': bool(data.get('is_active', True)),
            'created_at': now,
            'updated_at': now
        }

        # Check for existing
        brands = _load_local_brands()
        for i, existing in enumerate(brands):
            if existing.get('slug') == slug:
                # Update existing rather than duplicate
                brands[i].update(brand_record)
                _save_local_brands()
                return slug

        brands.append(format_record(brand_record))
        _save_local_brands()

        client = get_supabase()
        if client is not None:
            try:
                client.table('brands').insert(brand_record).execute()
            except Exception as e:
                print(f"BrandService.create remote error: {e}")

        return slug

    @staticmethod
    def update(brand_id_or_slug, data):
        if not brand_id_or_slug or not data:
            return False

        str_id = str(brand_id_or_slug).strip()
        now = datetime.utcnow().isoformat()
        brands = _load_local_brands()

        client = get_supabase()
        if client is not None:
            try:
                update_payload = data.copy()
                update_payload['updated_at'] = now
                client.table('brands').update(update_payload).or_(f"id.eq.{str_id},slug.eq.{str_id}").execute()
            except Exception as e:
                print(f"BrandService.update remote error: {e}")

        for i, b in enumerate(brands):
            if str(b.get('id', '')) == str_id or str(b.get('_id', '')) == str_id or b.get('slug', '').lower() == str_id.lower():
                brands[i].update(data)
                brands[i]['updated_at'] = now
                if 'name' in data and not data.get('slug') and not brands[i].get('slug'):
                    brands[i]['slug'] = generate_slug(data['name'])
                format_record(brands[i])
                _save_local_brands()
                return True

        return False

    @staticmethod
    def delete(brand_id_or_slug):
        if not brand_id_or_slug:
            return False

        str_id = str(brand_id_or_slug).strip()
        brands = _load_local_brands()

        client = get_supabase()
        if client is not None:
            try:
                client.table('brands').delete().or_(f"id.eq.{str_id},slug.eq.{str_id}").execute()
            except Exception as e:
                print(f"BrandService.delete remote error: {e}")

        for i, b in enumerate(brands):
            if str(b.get('id', '')) == str_id or str(b.get('_id', '')) == str_id or b.get('slug', '').lower() == str_id.lower():
                brands.pop(i)
                _save_local_brands()
                return True

        return False
