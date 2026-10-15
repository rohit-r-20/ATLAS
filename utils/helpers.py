import re
import urllib.parse
from datetime import datetime

def generate_slug(text):
    """
    Converts a title or name into a URL-friendly slug.
    Example: "CPVC Pipes 1/2 inch" -> "cpvc-pipes-1-2-inch"
    """
    if not text:
        return ''
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text

def build_whatsapp_url(phone, message):
    """
    Generates a WhatsApp click-to-chat link.
    """
    sanitized_phone = re.sub(r'\D', '', phone)
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{sanitized_phone}?text={encoded_message}"

def build_product_whatsapp_message(product_name, sku):
    """
    Formats WhatsApp product quote request text.
    """
    return f"Hi, I'm interested in the following product from Sathik Groups:\n\n*Product:* {product_name}\n*SKU:* {sku}\n\nPlease share availability and quote."

def format_date(dt):
    """
    Formats a datetime object to a readable string.
    """
    if isinstance(dt, datetime):
        return dt.strftime('%b %d, %Y %I:%M %p')
    return str(dt) if dt else ''

def parse_id(id_str):
    """
    Safely stringifies an ID.
    """
    return str(id_str) if id_str else None

_NAV_STORES_CACHE = None
_NAV_STORES_CACHE_TIME = 0

def get_specialized_stores_nav():
    """
    Returns the 3 specialized stores with their active products for the navbar multi-level dropdown.
    Cached for 30 seconds to guarantee instant sub-millisecond page rendering.
    """
    global _NAV_STORES_CACHE, _NAV_STORES_CACHE_TIME
    import time
    now = time.time()
    if _NAV_STORES_CACHE is not None and (now - _NAV_STORES_CACHE_TIME < 30):
        return _NAV_STORES_CACHE

    try:
        from services.product_service import _load_local_products
        all_prods = _load_local_products() or []
    except Exception:
        all_prods = []

    store_configs = [
        {
            'slug': 'hardware',
            'name': 'Paints, Hardwares & Door Fittings',
            'brand_name': 'Sathik Hardwares',
            'sub': 'Door Locks, Asian Paints & Fitting Accessories',
            'icon': '🔨',
            'badge': 'Store 01',
            'color': '#EA580C',
            'accent_rgb': '234, 88, 12'
        },
        {
            'slug': 'plumbing',
            'name': 'Pumps & Plumbing Solutions',
            'brand_name': 'Sathik Traders',
            'sub': 'CRI Pumps, Pipes, Valves & Power Tools',
            'icon': '🔧',
            'badge': 'Store 02',
            'color': '#0284C7',
            'accent_rgb': '2, 132, 199'
        },
        {
            'slug': 'bath-kitchen',
            'name': 'Bathware & Sanitaryware',
            'brand_name': 'Sathik Enterprises',
            'sub': 'Luxury Sanitaryware, Faucets & Sinks',
            'icon': '🛁',
            'badge': 'Store 03',
            'color': '#0D9488',
            'accent_rgb': '13, 148, 136'
        }
    ]

    stores = []
    for s in store_configs:
        prods = [
            p for p in all_prods
            if p.get('business_slug') == s['slug']
            and p.get('is_active', True)
            and not p.get('is_deleted', False)
        ]
        stores.append({
            **s,
            'products': prods,
            'count': len(prods)
        })

    _NAV_STORES_CACHE = stores
    _NAV_STORES_CACHE_TIME = now
    return stores

