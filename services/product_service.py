import os
import json
from datetime import datetime
from database.supabase import get_supabase
from utils.constants import MOCK_PRODUCTS

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'products_data.json')

_LOCAL_PRODUCTS = None

def format_record(record):
    """Ensure record has both id and _id fields for template backward compatibility."""
    if isinstance(record, dict):
        rec_id = str(record.get('id') or record.get('_id') or '')
        if rec_id:
            record['id'] = rec_id
            record['_id'] = rec_id
        if 'images' in record and isinstance(record['images'], list):
            for img in record['images']:
                if isinstance(img, dict) and not img.get('url'):
                    img['url'] = '/static/images/placeholder.jpg'
        elif not record.get('images'):
            record['images'] = [{'url': '/static/images/placeholder.jpg', 'is_primary': True}]
    return record

def _load_local_products():
    """Load products from GitHub storage (cached or live), local JSON file, or MOCK_PRODUCTS."""
    global _LOCAL_PRODUCTS

    try:
        from services.github_storage import GithubStorageService
        gh_prods = GithubStorageService.get_products()
        if gh_prods and isinstance(gh_prods, list) and len(gh_prods) > 0:
            _LOCAL_PRODUCTS = [format_record(p) for p in gh_prods]
            return _LOCAL_PRODUCTS
    except Exception as e:
        print(f"⚠️ Notice reading GitHub storage: {e}")

    if _LOCAL_PRODUCTS is not None:
        return _LOCAL_PRODUCTS

    if os.path.exists(DATA_FILE_PATH):
        try:
            with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    _LOCAL_PRODUCTS = [format_record(p) for p in data]
                    return _LOCAL_PRODUCTS
        except Exception as e:
            print(f"⚠️ Notice reading {DATA_FILE_PATH}: {e}")

    # Initialize from MOCK_PRODUCTS
    _LOCAL_PRODUCTS = [format_record(p.copy()) for p in MOCK_PRODUCTS]
    _save_local_products()
    return _LOCAL_PRODUCTS

def _save_local_products():
    """Save current products to GitHub repository and local JSON file."""
    global _LOCAL_PRODUCTS
    if _LOCAL_PRODUCTS is None:
        return

    try:
        from services.github_storage import GithubStorageService
        GithubStorageService.save_products(_LOCAL_PRODUCTS)
    except Exception as e:
        print(f"⚠️ Notice saving to GitHub storage: {e}")

class ProductService:
    @staticmethod
    def get_all(filter_query=None, sort_field='created_at', sort_order='desc', page=1, limit=12, active_only=True, only_deleted=False, only_staging=False):
        products = _load_local_products()
        client = get_supabase()

        if client is not None:
            try:
                query = client.table('products').select('*', count='exact')
                if only_deleted:
                    query = query.eq('is_deleted', True)
                elif only_staging:
                    query = query.or_('is_deleted.is.null,is_deleted.eq.false')
                    query = query.or_('is_staging.eq.true,category_slug.eq.,category_slug.is.null,category_slug.eq.staging,category_slug.eq.uncategorized')
                else:
                    query = query.or_('is_deleted.is.null,is_deleted.eq.false')
                    if active_only:
                        query = query.eq('is_active', True)

                if filter_query:
                    if filter_query.get('business_slug'):
                        query = query.eq('business_slug', filter_query['business_slug'])
                    if filter_query.get('category_slug'):
                        query = query.eq('category_slug', filter_query['category_slug'])
                    if filter_query.get('brand_slug'):
                        query = query.eq('brand_slug', filter_query['brand_slug'])
                    if filter_query.get('subcategory_slug'):
                        query = query.eq('subcategory_slug', filter_query['subcategory_slug'])
                    if filter_query.get('slug'):
                        if isinstance(filter_query['slug'], dict) and '$ne' in filter_query['slug']:
                            query = query.neq('slug', filter_query['slug']['$ne'])
                        elif isinstance(filter_query['slug'], str):
                            query = query.eq('slug', filter_query['slug'])
                    
                    if filter_query.get('$or'):
                        search_term = None
                        for cond in filter_query['$or']:
                            if 'name' in cond and isinstance(cond['name'], dict):
                                search_term = cond['name'].get('$regex', '')
                        if search_term:
                            query = query.or_(f"name.ilike.%{search_term}%,description.ilike.%{search_term}%,sku.ilike.%{search_term}%,brand_name.ilike.%{search_term}%")

                desc_order = (sort_order in ('desc', -1, 'DESC'))
                query = query.order(sort_field, desc=desc_order)

                start_idx = (page - 1) * limit
                end_idx = start_idx + limit - 1
                query = query.range(start_idx, end_idx)

                res = query.execute()
                remote_products = [format_record(p) for p in (res.data or [])]
                total = res.count if res.count is not None else len(remote_products)
                if remote_products:
                    return remote_products, total
            except Exception as e:
                # Supabase unavailable; seamlessly fall back to local persistent products
                pass

        # Local filtering logic
        results = products.copy()

        if only_deleted:
            results = [p for p in results if p.get('is_deleted') is True]
        elif only_staging:
            results = [
                p for p in results 
                if not p.get('is_deleted', False) and (
                    p.get('is_staging') is True or 
                    not p.get('category_slug') or 
                    p.get('category_slug') in ('', 'staging', 'uncategorized')
                )
            ]
        else:
            results = [p for p in results if not p.get('is_deleted', False)]
            if active_only:
                results = [p for p in results if p.get('is_active', True) is True]

        if filter_query:
            if 'business_slug' in filter_query and filter_query['business_slug']:
                results = [p for p in results if p.get('business_slug') == filter_query['business_slug']]

            if 'category_slug' in filter_query and filter_query['category_slug']:
                results = [p for p in results if p.get('category_slug') == filter_query['category_slug']]

            if 'subcategory_slug' in filter_query and filter_query['subcategory_slug']:
                results = [p for p in results if p.get('subcategory_slug') == filter_query['subcategory_slug']]

            if 'brand_slug' in filter_query and filter_query['brand_slug']:
                b_slug = filter_query['brand_slug']
                results = [p for p in results if p.get('brand_slug') == b_slug or b_slug in p.get('available_brand_slugs', [])]

            if 'slug' in filter_query and filter_query['slug']:
                if isinstance(filter_query['slug'], dict) and '$ne' in filter_query['slug']:
                    results = [p for p in results if p.get('slug') != filter_query['slug']['$ne']]
                elif isinstance(filter_query['slug'], str):
                    results = [p for p in results if p.get('slug') == filter_query['slug']]

            if '$or' in filter_query:
                q = ''
                for item in filter_query['$or']:
                    if 'name' in item and isinstance(item['name'], dict):
                        q = item['name'].get('$regex', '')
                    elif 'name' in item and isinstance(item['name'], str):
                        q = item['name']
                if q:
                    q_lower = q.lower()
                    results = [
                        p for p in results 
                        if q_lower in p.get('name', '').lower() 
                        or q_lower in p.get('sku', '').lower()
                        or q_lower in p.get('brand_name', '').lower()
                        or q_lower in p.get('description', '').lower()
                    ]

        total = len(results)

        # Apply sorting — sort_order field takes priority (ascending = position 1 first)
        reverse_sort = (sort_order in ('desc', -1, 'DESC'))
        results.sort(
            key=lambda x: (
                x.get('sort_order') if x.get('sort_order') is not None else 9999,
                str(x.get('created_at') or '2000-01-01')
            ),
            reverse=False
        )
        if sort_field == 'name':
            results.sort(key=lambda x: str(x.get('name', '')).lower(), reverse=reverse_sort)

        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated = results[start_idx:end_idx]

        return [format_record(r) for r in paginated], total

    @staticmethod
    def get_by_slug(subcategory_slug, product_slug):
        products = _load_local_products()
        client = get_supabase()

        if client is not None:
            try:
                res = client.table('products').select('*')\
                    .eq('slug', product_slug)\
                    .eq('is_active', True)\
                    .or_('is_deleted.is.null,is_deleted.eq.false')\
                    .limit(1).execute()
                if res.data:
                    return format_record(res.data[0])
            except Exception:
                pass

        for p in products:
            if p.get('slug') == product_slug and p.get('is_active', True) and not p.get('is_deleted', False):
                return format_record(p)
        return None

    @staticmethod
    def get_by_id(product_id, include_deleted=False):
        products = _load_local_products()
        client = get_supabase()

        if client is not None:
            try:
                query = client.table('products').select('*').eq('id', product_id)
                if not include_deleted:
                    query = query.or_('is_deleted.is.null,is_deleted.eq.false')
                res = query.limit(1).execute()
                if res.data:
                    return format_record(res.data[0])
            except Exception:
                pass

        str_id = str(product_id)
        for p in products:
            p_id = str(p.get('id') or '')
            p__id = str(p.get('_id') or '')
            p_slug = str(p.get('slug') or '')
            if p_id == str_id or p__id == str_id or p_slug == str_id:
                if include_deleted or not p.get('is_deleted', False):
                    return format_record(p)
        return None

    @staticmethod
    def get_featured(limit=8):
        products = _load_local_products()
        client = get_supabase()

        if client is not None:
            try:
                res = client.table('products').select('*')\
                    .eq('is_featured', True)\
                    .eq('is_active', True)\
                    .or_('is_deleted.is.null,is_deleted.eq.false')\
                    .order('created_at', desc=True)\
                    .limit(limit).execute()
                if res.data:
                    return [format_record(p) for p in res.data]
            except Exception:
                pass

        featured = [p for p in products if p.get('is_active', True) and p.get('is_featured', False) and not p.get('is_deleted', False)]
        return [format_record(p) for p in featured[:limit]]

    @staticmethod
    def create(data):
        products = _load_local_products()
        now = datetime.utcnow().isoformat()
        
        prod_id = str(data.get('id') or f"p_{data.get('slug', 'prod')}_{int(datetime.utcnow().timestamp())}")
        data['id'] = prod_id
        data['_id'] = prod_id
        data['created_at'] = data.get('created_at') or now
        data['updated_at'] = now
        data['is_active'] = data.get('is_active', True)
        data['is_featured'] = data.get('is_featured', False)
        data['is_new'] = data.get('is_new', True)
        # New products get sort_order = 0 (top of list); existing products shift down
        data['sort_order'] = 0

        formatted = format_record(data)

        # Attempt remote Supabase insert if online
        client = get_supabase()
        if client is not None:
            try:
                remote_data = formatted.copy()
                client.table('products').insert(remote_data).execute()
            except Exception as e:
                print(f"ProductService remote insert note: {e}")

        # Insert at front of local list so it appears newest first
        products.insert(0, formatted)
        _save_local_products()
        return formatted['id']

    @staticmethod
    def update(product_id, data):
        products = _load_local_products()
        str_id = str(product_id)
        now = datetime.utcnow().isoformat()
        data['updated_at'] = now

        # Attempt remote Supabase update if online
        client = get_supabase()
        if client is not None:
            try:
                client.table('products').update(data).eq('id', product_id).execute()
            except Exception as e:
                print(f"ProductService remote update note: {e}")

        for i, p in enumerate(products):
            p_id = str(p.get('id') or '')
            p__id = str(p.get('_id') or '')
            p_slug = str(p.get('slug') or '')
            if p_id == str_id or p__id == str_id or p_slug == str_id:
                # Merge updates
                products[i].update(data)
                format_record(products[i])
                _save_local_products()
                return True
        return False

    @staticmethod
    def delete(product_id):
        """Soft delete: move to recycle bin."""
        products = _load_local_products()
        str_id = str(product_id)
        now = datetime.utcnow().isoformat()

        client = get_supabase()
        if client is not None:
            try:
                client.table('products').update({
                    'is_deleted': True,
                    'deleted_at': now,
                    'is_active': False,
                    'updated_at': now
                }).eq('id', product_id).execute()
            except Exception as e:
                print(f"ProductService remote delete note: {e}")

        for i, p in enumerate(products):
            p_id = str(p.get('id') or '')
            p__id = str(p.get('_id') or '')
            p_slug = str(p.get('slug') or '')
            if p_id == str_id or p__id == str_id or p_slug == str_id:
                products[i]['is_deleted'] = True
                products[i]['deleted_at'] = now
                products[i]['is_active'] = False
                products[i]['updated_at'] = now
                _save_local_products()
                return True
        return False

    @staticmethod
    def restore(product_id):
        """Restore soft-deleted product from recycle bin."""
        products = _load_local_products()
        str_id = str(product_id)
        now = datetime.utcnow().isoformat()

        client = get_supabase()
        if client is not None:
            try:
                client.table('products').update({
                    'is_deleted': False,
                    'deleted_at': None,
                    'is_active': True,
                    'updated_at': now
                }).eq('id', product_id).execute()
            except Exception as e:
                print(f"ProductService remote restore note: {e}")

        for i, p in enumerate(products):
            p_id = str(p.get('id') or '')
            p__id = str(p.get('_id') or '')
            p_slug = str(p.get('slug') or '')
            if p_id == str_id or p__id == str_id or p_slug == str_id:
                products[i]['is_deleted'] = False
                products[i]['deleted_at'] = None
                products[i]['is_active'] = True
                products[i]['updated_at'] = now
                _save_local_products()
                return True
        return False

    @staticmethod
    def permanent_delete(product_id):
        """Permanently remove product from storage."""
        products = _load_local_products()
        str_id = str(product_id)

        client = get_supabase()
        if client is not None:
            try:
                client.table('products').delete().eq('id', product_id).execute()
            except Exception as e:
                print(f"ProductService remote permanent delete note: {e}")

        for i, p in enumerate(products):
            p_id = str(p.get('id') or '')
            p__id = str(p.get('_id') or '')
            p_slug = str(p.get('slug') or '')
            if p_id == str_id or p__id == str_id or p_slug == str_id:
                products.pop(i)
                _save_local_products()
                return True
        return False

    @staticmethod
    def empty_recycle_bin():
        """Permanently delete all products currently in recycle bin."""
        global _LOCAL_PRODUCTS
        products = _load_local_products()

        client = get_supabase()
        if client is not None:
            try:
                client.table('products').delete().eq('is_deleted', True).execute()
            except Exception as e:
                print(f"ProductService remote empty_recycle_bin note: {e}")

        count_deleted = len([p for p in products if p.get('is_deleted') is True])
        _LOCAL_PRODUCTS = [p for p in products if not p.get('is_deleted', False)]
        _save_local_products()
        return count_deleted

    @staticmethod
    def get_recycle_bin_count():
        """Return total count of products in recycle bin."""
        products = _load_local_products()
        return len([p for p in products if p.get('is_deleted') is True])

    @staticmethod
    def get_staging_count():
        """Return total count of products in the staging area (uncategorized)."""
        products = _load_local_products()
        return len([
            p for p in products 
            if not p.get('is_deleted', False) and (
                p.get('is_staging') is True or 
                not p.get('category_slug') or 
                p.get('category_slug') in ('', 'staging', 'uncategorized')
            )
        ])

    @staticmethod
    def move_category_products_to_staging(category_slug):
        """
        When a category is deleted, all products in that category are moved to a staging area
        (uncategorized state). They remain active in the catalogue normally, but do not belong
        to any specific category.
        """
        products = _load_local_products()
        str_slug = str(category_slug).strip()
        now = datetime.utcnow().isoformat()
        moved_count = 0

        client = get_supabase()

        for p in products:
            if p.get('category_slug') == str_slug or p.get('category_id') == str_slug:
                p['category_slug'] = ''
                p['category_id'] = ''
                p['category_name'] = 'Uncategorized'
                p['subcategory_slug'] = 'uncategorized'
                p['subcategory_id'] = ''
                p['subcategory_name'] = ''
                p['is_staging'] = True
                p['updated_at'] = now
                moved_count += 1

                if client is not None:
                    try:
                        p_id = str(p.get('id') or p.get('_id'))
                        client.table('products').update({
                            'category_slug': '',
                            'category_id': '',
                            'category_name': 'Uncategorized',
                            'subcategory_slug': 'uncategorized',
                            'subcategory_id': '',
                            'subcategory_name': '',
                            'is_staging': True,
                            'updated_at': now
                        }).eq('id', p_id).execute()
                    except Exception as e:
                        print(f"ProductService remote staging update note: {e}")

        if moved_count > 0:
            _save_local_products()

        return moved_count

    @staticmethod
    def reorder(order_list):
        """Bulk-update sort_order. order_list = [{'id': ..., 'sort_order': int}, ...]"""
        products = _load_local_products()
        now = datetime.utcnow().isoformat()
        order_map = {str(item['id']): int(item['sort_order']) for item in order_list}

        client = get_supabase()
        for p in products:
            p_id = str(p.get('id') or p.get('_id') or '')
            if p_id in order_map:
                p['sort_order'] = order_map[p_id]
                p['updated_at'] = now
                if client is not None:
                    try:
                        client.table('products').update({'sort_order': order_map[p_id]}).eq('id', p_id).execute()
                    except Exception:
                        pass

        _save_local_products()
        return True
