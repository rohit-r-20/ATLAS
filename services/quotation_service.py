import os
import json
import time
from datetime import datetime, timezone
from database.supabase import get_supabase

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'quotations_data.json')

_LOCAL_QUOTATIONS = None

def format_record(record):
    """Ensure record has _id and id fields for template backward compatibility."""
    if isinstance(record, dict):
        rec_id = str(record.get('id') or record.get('_id') or '')
        if rec_id:
            record['id'] = rec_id
            record['_id'] = rec_id
        if 'name' not in record and 'customer_name' in record:
            record['name'] = record['customer_name']
        if 'phone' not in record and 'mobile_number' in record:
            record['phone'] = record['mobile_number']
        elif 'mobile_number' not in record and 'phone' in record:
            record['mobile_number'] = record['phone']
        if 'city' not in record and 'address' in record:
            record['city'] = record['address']
        if 'reference_id' not in record and 'quote_ref' in record:
            record['reference_id'] = record['quote_ref']
        elif 'quote_ref' not in record and 'reference_id' in record:
            record['quote_ref'] = record['reference_id']
        if 'notes' in record and record['notes']:
            record['admin_notes'] = record['notes']
        elif 'admin_notes' in record and record['admin_notes']:
            record['notes'] = record['admin_notes']
        if 'status' not in record or not record['status']:
            record['status'] = 'New'
        if 'items' not in record or not isinstance(record['items'], list):
            record['items'] = []
        record['quote_items'] = record['items']
        record['item_list'] = record['items']
    return record

_LOCAL_QUOTATIONS_MTIME = 0

def _load_local_quotations(force_reload=False):
    global _LOCAL_QUOTATIONS, _LOCAL_QUOTATIONS_MTIME
    try:
        mtime = os.path.getmtime(DATA_FILE_PATH) if os.path.exists(DATA_FILE_PATH) else 0
    except OSError:
        mtime = 0

    if not force_reload and _LOCAL_QUOTATIONS is not None and mtime == _LOCAL_QUOTATIONS_MTIME:
        return _LOCAL_QUOTATIONS

    if os.path.exists(DATA_FILE_PATH):
        try:
            with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    _LOCAL_QUOTATIONS = [format_record(q) for q in data]
                    _LOCAL_QUOTATIONS_MTIME = mtime
                    return _LOCAL_QUOTATIONS
        except Exception as e:
            print(f"⚠️ Notice reading {DATA_FILE_PATH}: {e}")

    _LOCAL_QUOTATIONS = []
    _LOCAL_QUOTATIONS_MTIME = mtime
    return _LOCAL_QUOTATIONS

def _save_local_quotations():
    global _LOCAL_QUOTATIONS
    if _LOCAL_QUOTATIONS is None:
        return
    try:
        os.makedirs(os.path.dirname(DATA_FILE_PATH), exist_ok=True)
        with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(_LOCAL_QUOTATIONS, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error saving quotations to {DATA_FILE_PATH}: {e}")


class QuotationService:
    @staticmethod
    def create_quotation(data):
        """
        Creates and persists a new quotation entry.
        Supports single product quotes, multi-item quote cart lists, and quick enquiries.
        """
        if not data:
            return None

        quotes = _load_local_quotations()
        now = datetime.now(timezone.utc).isoformat()
        quote_id = data.get('id') or f"qt_{int(time.time() * 1000)}"
        quote_num = f"#QT-{1000 + len(quotes) + 1}"

        customer_name = (data.get('customer_name') or data.get('name') or 'Customer').strip()
        phone = (data.get('mobile_number') or data.get('phone') or data.get('mobile') or '').strip()
        email = (data.get('email') or '').strip()
        city = (data.get('city') or data.get('address') or '').strip()
        product_name = (data.get('product_name') or '').strip()
        product_sku = (data.get('product_sku') or data.get('sku') or '').strip()
        quantity = (data.get('quantity') or data.get('qty') or '').strip()
        message = (data.get('message') or '').strip()
        quote_type = (data.get('type') or data.get('quote_type') or 'quote').strip()
        whatsapp_url = data.get('whatsapp_url', '')

        # Parse structured items
        items = []
        raw_items_json = data.get('items_json')
        if raw_items_json:
            try:
                parsed_items = json.loads(raw_items_json) if isinstance(raw_items_json, str) else raw_items_json
                if isinstance(parsed_items, list):
                    for it in parsed_items:
                        if isinstance(it, dict):
                            items.append({
                                'name': it.get('name', 'Product'),
                                'sku': it.get('sku', ''),
                                'quantity': it.get('quantity', 1),
                                'image': it.get('image', ''),
                                'brand': it.get('brand', '')
                            })
            except Exception as e:
                print(f"Notice parsing items_json: {e}")

        # If no items from json, try parsing from single product fields or message text
        if not items:
            if product_name and product_name != 'Multiple Products Quote List':
                items.append({
                    'name': product_name,
                    'sku': product_sku,
                    'quantity': quantity or '1',
                    'image': data.get('product_image', ''),
                    'brand': data.get('brand', '')
                })
            elif '[Quote Request List]' in message:
                try:
                    list_part = message.split('[Quote Request List]')[1].split('[User Message]')[0]
                    for line in list_part.strip().split('\n'):
                        line = line.strip()
                        if line:
                            # e.g. "1. Jaquar Tap (SKU: JQ-101)"
                            items.append({
                                'name': line,
                                'sku': '',
                                'quantity': '1',
                                'image': '',
                                'brand': ''
                            })
                except Exception:
                    pass

        record = {
            'id': quote_id,
            '_id': quote_id,
            'quote_ref': quote_num,
            'reference_id': quote_num,
            'customer_name': customer_name,
            'name': customer_name,
            'mobile_number': phone,
            'phone': phone,
            'email': email,
            'city': city,
            'address': city,
            'quote_type': quote_type,
            'product_name': product_name or (items[0]['name'] if items else 'Building Materials'),
            'product_sku': product_sku,
            'quantity': quantity,
            'items': items,
            'item_count': len(items) if items else 1,
            'message': message,
            'whatsapp_url': whatsapp_url,
            'preferred_contact': data.get('preferred_contact', 'WhatsApp Message'),
            'status': 'New',
            'notes': '',
            'admin_notes': '',
            'created_at': now
        }

        # Attempt remote Supabase insert if online
        client = get_supabase()
        if client is not None:
            try:
                client.table('quotations').insert({
                    'quote_ref': record['quote_ref'],
                    'customer_name': record['customer_name'],
                    'phone': record['phone'],
                    'email': record['email'],
                    'city': record['city'],
                    'product_name': record['product_name'],
                    'product_sku': record['product_sku'],
                    'items_count': record['item_count'],
                    'message': record['message'],
                    'whatsapp_url': record['whatsapp_url'],
                    'status': record['status'],
                    'created_at': record['created_at']
                }).execute()
            except Exception as e:
                print(f"QuotationService remote insert notice: {e}")

        # Insert at top of list
        quotes.insert(0, record)
        _save_local_quotations()
        return format_record(record)

    @staticmethod
    def get_all(status=None, search=None, page=1, limit=20):
        quotes = _load_local_quotations()
        client = get_supabase()

        if client is not None:
            try:
                query = client.table('quotations').select('*', count='exact')
                if status and status.lower() != 'all':
                    query = query.ilike('status', status)
                if search:
                    s = f"%{search}%"
                    query = query.or_(f"customer_name.ilike.{s},phone.ilike.{s},city.ilike.{s},product_name.ilike.{s}")
                query = query.order('created_at', desc=True)
                start_idx = (page - 1) * limit
                end_idx = start_idx + limit - 1
                res = query.range(start_idx, end_idx).execute()
                if res.data and len(res.data) > 0:
                    remote_quotes = [format_record(r) for r in res.data]
                    total = res.count if res.count is not None else len(remote_quotes)
                    return remote_quotes, total
            except Exception as e:
                print(f"QuotationService.get_all remote error: {e}")

        # Local filtering logic
        results = quotes.copy()

        if status and status.lower() != 'all':
            s_clean = status.lower()
            results = [q for q in results if str(q.get('status', '')).lower() == s_clean]

        if search:
            q_clean = search.lower().strip()
            results = [
                q for q in results
                if q_clean in str(q.get('customer_name', '')).lower()
                or q_clean in str(q.get('phone', '')).lower()
                or q_clean in str(q.get('city', '')).lower()
                or q_clean in str(q.get('quote_ref', '')).lower()
                or q_clean in str(q.get('product_name', '')).lower()
                or q_clean in str(q.get('message', '')).lower()
            ]

        total = len(results)
        start = (page - 1) * limit
        end = start + limit
        paginated = results[start:end]
        return [format_record(r) for r in paginated], total

    @staticmethod
    def get_by_id(quote_id):
        quotes = _load_local_quotations()
        str_id = str(quote_id)
        for q in quotes:
            if str(q.get('id', '')) == str_id or str(q.get('_id', '')) == str_id or str(q.get('quote_ref', '')) == str_id:
                return format_record(q)
        return None

    @staticmethod
    def update_quotation(quote_id, update_data):
        if not quote_id or not update_data:
            return False

        quotes = _load_local_quotations()
        str_id = str(quote_id)
        now = datetime.now(timezone.utc).isoformat()

        client = get_supabase()
        if client is not None:
            try:
                remote_payload = update_data.copy()
                remote_payload['updated_at'] = now
                client.table('quotations').update(remote_payload).eq('id', quote_id).execute()
            except Exception as e:
                print(f"QuotationService remote update error: {e}")

        for i, q in enumerate(quotes):
            if str(q.get('id', '')) == str_id or str(q.get('_id', '')) == str_id or str(q.get('quote_ref', '')) == str_id or str(q.get('reference_id', '')) == str_id:
                if 'customer_name' in update_data:
                    quotes[i]['customer_name'] = update_data['customer_name']
                    quotes[i]['name'] = update_data['customer_name']
                if 'mobile_number' in update_data:
                    quotes[i]['mobile_number'] = update_data['mobile_number']
                    quotes[i]['phone'] = update_data['mobile_number']
                if 'email' in update_data:
                    quotes[i]['email'] = update_data['email']
                if 'city' in update_data:
                    quotes[i]['city'] = update_data['city']
                    quotes[i]['address'] = update_data['city']
                if 'status' in update_data:
                    quotes[i]['status'] = update_data['status']
                if 'notes' in update_data or 'admin_notes' in update_data:
                    notes_val = update_data.get('admin_notes', update_data.get('notes', ''))
                    quotes[i]['notes'] = notes_val
                    quotes[i]['admin_notes'] = notes_val
                if 'message' in update_data:
                    quotes[i]['message'] = update_data['message']
                if 'items' in update_data and isinstance(update_data['items'], list):
                    quotes[i]['items'] = update_data['items']
                    quotes[i]['quote_items'] = update_data['items']
                    quotes[i]['item_list'] = update_data['items']
                if 'total_amount' in update_data:
                    quotes[i]['total_amount'] = update_data['total_amount']
                if 'product_name' in update_data:
                    quotes[i]['product_name'] = update_data['product_name']
                if 'product_sku' in update_data:
                    quotes[i]['product_sku'] = update_data['product_sku']
                if 'quantity' in update_data:
                    quotes[i]['quantity'] = update_data['quantity']

                quotes[i]['updated_at'] = now
                format_record(quotes[i])
                _save_local_quotations()
                return True
        return False

    @staticmethod
    def update_status(quote_id, status, notes=None):
        quotes = _load_local_quotations()
        str_id = str(quote_id)

        client = get_supabase()
        if client is not None:
            try:
                update_payload = {'status': status}
                if notes is not None:
                    update_payload['notes'] = notes
                client.table('quotations').update(update_payload).eq('id', quote_id).execute()
            except Exception as e:
                print(f"QuotationService remote update error: {e}")

        for i, q in enumerate(quotes):
            if str(q.get('id', '')) == str_id or str(q.get('_id', '')) == str_id or str(q.get('quote_ref', '')) == str_id or str(q.get('reference_id', '')) == str_id:
                quotes[i]['status'] = status
                if notes is not None:
                    quotes[i]['notes'] = notes
                    quotes[i]['admin_notes'] = notes
                _save_local_quotations()
                return True
        return False

    @staticmethod
    def delete(quote_id):
        quotes = _load_local_quotations()
        str_id = str(quote_id)

        client = get_supabase()
        if client is not None:
            try:
                client.table('quotations').delete().eq('id', quote_id).execute()
            except Exception as e:
                print(f"QuotationService remote delete error: {e}")

        for i, q in enumerate(quotes):
            if str(q.get('id', '')) == str_id or str(q.get('_id', '')) == str_id or str(q.get('quote_ref', '')) == str_id:
                quotes.pop(i)
                _save_local_quotations()
                return True
        return False

    @staticmethod
    def get_stats():
        quotes = _load_local_quotations()
        total = len(quotes)
        new_count = sum(1 for q in quotes if str(q.get('status', '')).lower() == 'new')
        contacted_count = sum(1 for q in quotes if str(q.get('status', '')).lower() == 'contacted')
        quoted_count = sum(1 for q in quotes if str(q.get('status', '')).lower() == 'quoted')
        closed_count = sum(1 for q in quotes if str(q.get('status', '')).lower() == 'closed')

        return {
            'total': total,
            'new': new_count,
            'contacted': contacted_count,
            'quoted': quoted_count,
            'closed': closed_count
        }
