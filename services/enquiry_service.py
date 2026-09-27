import os
import json
import time
from datetime import datetime, timezone
from database.supabase import get_supabase
from services.github_storage import GithubStorageService

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE_PATH = os.path.join(ROOT_DIR, 'database', 'enquiries_data.json')

_LOCAL_ENQUIRIES = None
_LOCAL_ENQUIRIES_MTIME = 0

def format_record(record):
    """Ensure record has _id field and name/phone aliases for template compatibility."""
    if isinstance(record, dict):
        rec_id = str(record.get('id') or record.get('_id') or '')
        if rec_id:
            record['id'] = rec_id
            record['_id'] = rec_id
        if 'customer_name' in record and 'name' not in record:
            record['name'] = record['customer_name']
        elif 'name' in record and 'customer_name' not in record:
            record['customer_name'] = record['name']
        if 'mobile_number' in record and 'phone' not in record:
            record['phone'] = record['mobile_number']
        elif 'mobile' in record and 'phone' not in record:
            record['phone'] = record['mobile']
        elif 'phone' in record and 'mobile_number' not in record:
            record['mobile_number'] = record['phone']
        if 'address' in record and 'city' not in record:
            record['city'] = record['address']
        elif 'city' in record and 'address' not in record:
            record['address'] = record['city']
        if 'is_deleted' not in record:
            record['is_deleted'] = False
        if 'deleted_at' not in record:
            record['deleted_at'] = None
        if 'status' not in record or not record['status']:
            record['status'] = 'New'
        if 'items' not in record or not isinstance(record.get('items'), list):
            record['items'] = []
        record['cart_items'] = record['items']
    return record

def _load_local_enquiries(force_reload=False):
    global _LOCAL_ENQUIRIES, _LOCAL_ENQUIRIES_MTIME
    try:
        mtime = os.path.getmtime(DATA_FILE_PATH) if os.path.exists(DATA_FILE_PATH) else 0
    except OSError:
        mtime = 0

    if not force_reload and _LOCAL_ENQUIRIES is not None and mtime == _LOCAL_ENQUIRIES_MTIME:
        return _LOCAL_ENQUIRIES

    if os.path.exists(DATA_FILE_PATH):
        try:
            with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    _LOCAL_ENQUIRIES = [format_record(e) for e in data]
                    _LOCAL_ENQUIRIES_MTIME = mtime
                    return _LOCAL_ENQUIRIES
        except Exception as e:
            print(f"⚠️ Notice reading {DATA_FILE_PATH}: {e}")

    _LOCAL_ENQUIRIES = []
    _LOCAL_ENQUIRIES_MTIME = mtime
    return _LOCAL_ENQUIRIES

def _save_local_enquiries(commit_msg="update enquiries list"):
    global _LOCAL_ENQUIRIES, _LOCAL_ENQUIRIES_MTIME
    if _LOCAL_ENQUIRIES is None:
        return
    try:
        os.makedirs(os.path.dirname(DATA_FILE_PATH), exist_ok=True)
        with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(_LOCAL_ENQUIRIES, f, indent=2, ensure_ascii=False)
        _LOCAL_ENQUIRIES_MTIME = os.path.getmtime(DATA_FILE_PATH)
    except Exception as e:
        print(f"⚠️ Error saving enquiries to {DATA_FILE_PATH}: {e}")

    # Also persist to GitHub via GithubStorageService if configured
    try:
        if GithubStorageService.is_configured():
            GithubStorageService.save_json_file(
                'database/enquiries_data.json',
                _LOCAL_ENQUIRIES,
                f"feat(enquiries): {commit_msg} [{len(_LOCAL_ENQUIRIES)} items]"
            )
    except Exception as gh_e:
        print(f"⚠️ Notice syncing enquiries to GitHub: {gh_e}")


class EnquiryService:
    @staticmethod
    def create_enquiry(data):
        """
        Creates and persists a new customer enquiry or quote cart submission.
        """
        if not data:
            return False

        enquiries = _load_local_enquiries()
        now = datetime.now(timezone.utc).isoformat()
        enq_id = data.get('id') or f"enq_{int(time.time() * 1000)}"
        enq_ref = f"#ENQ-{1000 + len(enquiries) + 1}"

        customer_name = (data.get('customer_name') or data.get('name') or 'Customer').strip()
        phone = (data.get('mobile_number') or data.get('phone') or data.get('mobile') or '').strip()
        email = (data.get('email') or '').strip()
        city = (data.get('city') or data.get('address') or '').strip()
        product_name = (data.get('product_name') or '').strip()
        product_sku = (data.get('product_sku') or data.get('sku') or '').strip()
        message = (data.get('message') or '').strip()
        preferred_contact = (data.get('preferred_contact') or 'WhatsApp Message').strip()
        whatsapp_url = data.get('whatsapp_url', '')

        # Parse structured items if provided (from cart or multi-item quote)
        items = []
        raw_items = data.get('items')
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
                print(f"Notice parsing enquiry items_json: {e}")
        elif isinstance(raw_items, list):
            items = raw_items

        if not items and product_name and product_name != 'Multiple Products Quote List':
            items.append({
                'name': product_name,
                'sku': product_sku,
                'quantity': data.get('quantity') or 1,
                'brand': data.get('brand') or ''
            })

        record = {
            'id': enq_id,
            '_id': enq_id,
            'enquiry_ref': enq_ref,
            'reference_id': enq_ref,
            'customer_name': customer_name,
            'name': customer_name,
            'mobile_number': phone,
            'phone': phone,
            'mobile': phone,
            'email': email,
            'city': city,
            'address': city,
            'interested_in': data.get('interested_in') or '',
            'product_name': product_name,
            'product_sku': product_sku,
            'items': items,
            'cart_items': items,
            'preferred_contact': preferred_contact,
            'message': message,
            'page_url': data.get('page_url') or '',
            'status': data.get('status') or 'New',
            'admin_notes': data.get('admin_notes') or '',
            'whatsapp_url': whatsapp_url,
            'is_deleted': False,
            'deleted_at': None,
            'created_at': data.get('created_at') or now,
            'updated_at': now
        }

        # Try remote Supabase insert if available
        client = get_supabase()
        if client is not None:
            try:
                remote_payload = {
                    'customer_name': customer_name,
                    'mobile': phone,
                    'email': email or None,
                    'address': city or None,
                    'interested_in': data.get('interested_in') or None,
                    'product_name': product_name or None,
                    'preferred_contact': preferred_contact,
                    'message': message or None,
                    'page_url': data.get('page_url') or None,
                    'status': 'New',
                    'created_at': now
                }
                client.table('enquiries').insert(remote_payload).execute()
            except Exception as e:
                print(f"EnquiryService remote insert notice: {e}")

        enquiries.insert(0, record)
        _save_local_enquiries(f"add enquiry from {customer_name}")
        return format_record(record)

    @staticmethod
    def create(data):
        """Legacy compatibility wrapper."""
        return EnquiryService.create_enquiry(data)

    @staticmethod
    def get_all(status=None, view='active', search=None, page=1, limit=20):
        enquiries = _load_local_enquiries()

        # Filter by active vs recycle bin
        if view == 'recycle_bin':
            results = [e for e in enquiries if e.get('is_deleted') is True]
        else:
            results = [e for e in enquiries if e.get('is_deleted') is not True]

        # Filter by status
        if status and status.lower() != 'all':
            s_clean = status.lower().strip()
            results = [e for e in results if str(e.get('status', '')).lower() == s_clean]

        # Search filter
        if search:
            q_clean = search.lower().strip()
            results = [
                e for e in results
                if q_clean in str(e.get('customer_name', '')).lower()
                or q_clean in str(e.get('phone', '')).lower()
                or q_clean in str(e.get('city', '')).lower()
                or q_clean in str(e.get('enquiry_ref', '')).lower()
                or q_clean in str(e.get('product_name', '')).lower()
                or q_clean in str(e.get('message', '')).lower()
            ]

        total = len(results)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated = results[start_idx:end_idx]
        return paginated, total

    @staticmethod
    def get_by_id(enquiry_id):
        enquiries = _load_local_enquiries()
        str_id = str(enquiry_id)
        for e in enquiries:
            if str(e.get('id', '')) == str_id or str(e.get('_id', '')) == str_id or str(e.get('enquiry_ref', '')) == str_id:
                return e
        return None

    @staticmethod
    def update_status(enquiry_id, status, notes=None):
        enquiries = _load_local_enquiries()
        str_id = str(enquiry_id)
        now = datetime.now(timezone.utc).isoformat()

        client = get_supabase()
        if client is not None:
            try:
                update_data = {'status': status}
                if notes:
                    update_data['admin_notes'] = notes
                client.table('enquiries').update(update_data).eq('id', enquiry_id).execute()
            except Exception as e:
                print(f"EnquiryService remote update error: {e}")

        for i, e in enumerate(enquiries):
            if str(e.get('id', '')) == str_id or str(e.get('_id', '')) == str_id or str(e.get('enquiry_ref', '')) == str_id:
                enquiries[i]['status'] = status
                if notes is not None:
                    enquiries[i]['admin_notes'] = notes
                enquiries[i]['updated_at'] = now
                _save_local_enquiries(f"update status of enquiry {enquiry_id} to {status}")
                return True
        return False

    @staticmethod
    def soft_delete(enquiry_id):
        """Move enquiry to Recycle Bin."""
        enquiries = _load_local_enquiries()
        str_id = str(enquiry_id)
        now = datetime.now(timezone.utc).isoformat()

        for i, e in enumerate(enquiries):
            if str(e.get('id', '')) == str_id or str(e.get('_id', '')) == str_id or str(e.get('enquiry_ref', '')) == str_id:
                enquiries[i]['is_deleted'] = True
                enquiries[i]['deleted_at'] = now
                enquiries[i]['updated_at'] = now
                _save_local_enquiries(f"move enquiry {enquiry_id} to recycle bin")
                return True
        return False

    @staticmethod
    def restore(enquiry_id):
        """Restore enquiry from Recycle Bin back to Active."""
        enquiries = _load_local_enquiries()
        str_id = str(enquiry_id)
        now = datetime.now(timezone.utc).isoformat()

        for i, e in enumerate(enquiries):
            if str(e.get('id', '')) == str_id or str(e.get('_id', '')) == str_id or str(e.get('enquiry_ref', '')) == str_id:
                enquiries[i]['is_deleted'] = False
                enquiries[i]['deleted_at'] = None
                enquiries[i]['updated_at'] = now
                _save_local_enquiries(f"restore enquiry {enquiry_id}")
                return True
        return False

    @staticmethod
    def permanent_delete(enquiry_id):
        """Permanently delete an enquiry from system."""
        enquiries = _load_local_enquiries()
        str_id = str(enquiry_id)

        client = get_supabase()
        if client is not None:
            try:
                client.table('enquiries').delete().eq('id', enquiry_id).execute()
            except Exception as e:
                print(f"EnquiryService remote delete error: {e}")

        for i, e in enumerate(enquiries):
            if str(e.get('id', '')) == str_id or str(e.get('_id', '')) == str_id or str(e.get('enquiry_ref', '')) == str_id:
                enquiries.pop(i)
                _save_local_enquiries(f"permanently delete enquiry {enquiry_id}")
                return True
        return False

    @staticmethod
    def empty_recycle_bin():
        """Permanently delete all enquiries currently in the recycle bin."""
        global _LOCAL_ENQUIRIES
        enquiries = _load_local_enquiries()
        retained = [e for e in enquiries if e.get('is_deleted') is not True]
        deleted_count = len(enquiries) - len(retained)
        _LOCAL_ENQUIRIES = retained
        _save_local_enquiries(f"empty recycle bin [{deleted_count} items purged]")
        return deleted_count

    @staticmethod
    def get_recycle_bin_count():
        enquiries = _load_local_enquiries()
        return sum(1 for e in enquiries if e.get('is_deleted') is True)

    @staticmethod
    def get_stats():
        enquiries = _load_local_enquiries()
        active = [e for e in enquiries if e.get('is_deleted') is not True]
        recycle = [e for e in enquiries if e.get('is_deleted') is True]

        total = len(active)
        new_count = sum(1 for e in active if str(e.get('status', '')).lower() == 'new')
        read_count = sum(1 for e in active if str(e.get('status', '')).lower() == 'read')
        responded_count = sum(1 for e in active if str(e.get('status', '')).lower() == 'responded')
        closed_count = sum(1 for e in active if str(e.get('status', '')).lower() == 'closed')

        return {
            'total': total,
            'new': new_count,
            'read': read_count,
            'responded': responded_count,
            'closed': closed_count,
            'recycle_bin': len(recycle)
        }
