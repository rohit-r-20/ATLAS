from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from services.enquiry_service import EnquiryService
from services.email_service import send_enquiry_email
from services.whatsapp_service import process_whatsapp_enquiry
from utils.constants import COMPANY_INFO

enquiry_bp = Blueprint('enquiry', __name__)

@enquiry_bp.route('/contact')
def contact():
    return redirect(url_for('home.index') + '#contactUs')

@enquiry_bp.route('/enquiry/submit', methods=['POST'])
def submit_enquiry():
    data = request.form.to_dict() if request.form else (request.get_json() or {})

    # Extract customer input fields with support for both form field naming conventions
    customer_name = (data.get('customer_name') or data.get('name') or '').strip()
    mobile_number = (data.get('mobile_number') or data.get('phone') or '').strip()
    email = (data.get('email') or '').strip()
    address = (data.get('address') or data.get('city') or '').strip()
    interested_in = (data.get('interested_in') or data.get('category') or data.get('business_slug') or '').strip()
    product_name = (data.get('product_name') or '').strip()
    preferred_contact = (data.get('preferred_contact') or 'WhatsApp Message').strip()
    message = (data.get('message') or '').strip()
    page_url = (request.referrer or data.get('page_url') or '').strip()

    # Validation: Customer Name & Mobile Number are required
    if not customer_name or not mobile_number:
        return jsonify({
            "success": False,
            "message": "Unable to save enquiry."
        }), 400

    # Pre-generate WhatsApp message & deep-link
    whatsapp_info = {}
    try:
        whatsapp_info = process_whatsapp_enquiry(data)
    except Exception as wa_err:
        print(f"⚠️ WhatsApp processing notice: {wa_err}")

    whatsapp_url = whatsapp_info.get("whatsapp_url") or data.get("whatsapp_url") or ""

    items_json = data.get('items_json') or ''
    product_sku = (data.get('product_sku') or data.get('sku') or '').strip()
    quantity = data.get('quantity') or data.get('qty') or ''
    submission_type = data.get('type') or ('quote_list' if items_json else 'quote')

    enquiry_data = {
        'customer_name': customer_name,
        'mobile_number': mobile_number,
        'email': email,
        'address': address,
        'city': address,
        'interested_in': interested_in,
        'product_name': product_name,
        'product_sku': product_sku,
        'quantity': quantity,
        'preferred_contact': preferred_contact,
        'message': message,
        'page_url': page_url,
        'items_json': items_json,
        'type': submission_type,
        'whatsapp_url': whatsapp_url,
        'status': 'New'
    }

    try:
        enquiry_record = EnquiryService.create_enquiry(enquiry_data)
        if enquiry_record:
            # Send Resend email notification (non-blocking if it fails)
            try:
                send_enquiry_email(enquiry_data)
            except Exception as mail_err:
                print(f"⚠️ Email notification trigger notice: {mail_err}")

            # Also record quotation so it appears in the Admin Quotation section
            try:
                from models.quotation import QuotationModel
                quote_payload = {
                    'customer_name': customer_name,
                    'mobile_number': mobile_number,
                    'email': email,
                    'city': address,
                    'address': address,
                    'interested_in': interested_in,
                    'product_name': product_name,
                    'product_sku': product_sku,
                    'quantity': quantity,
                    'preferred_contact': preferred_contact,
                    'message': message,
                    'type': submission_type,
                    'items_json': items_json,
                    'whatsapp_url': whatsapp_url
                }
                quote_record = QuotationModel.create(quote_payload)
            except Exception as quote_err:
                print(f"⚠️ Quotation recording notice: {quote_err}")
                quote_record = None

            return jsonify({
                "success": True,
                "message": "Thank you! Your quote request has been received.",
                "whatsapp_url": whatsapp_url,
                "target_phone": whatsapp_info.get("target_phone"),
                "enquiry_id": enquiry_record.get("id") if isinstance(enquiry_record, dict) else None,
                "enquiry_reference": enquiry_record.get("reference_id") if isinstance(enquiry_record, dict) else None,
                "quotation_id": quote_record.get("id") if quote_record else None,
                "quotation_reference": quote_record.get("reference_id") if quote_record else None
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Unable to save enquiry."
            }), 500
    except Exception as e:
        print(f"Error handling enquiry submit route: {e}")
        return jsonify({
            "success": False,
            "message": "Unable to save enquiry."
        }), 500

@enquiry_bp.route('/quotations/record-click', methods=['POST'])
def record_quotation_click():
    try:
        data = request.get_json(silent=True) if request.is_json else request.form.to_dict()
        if not data:
            data = {}
        from models.quotation import QuotationModel
        quote_payload = {
            'customer_name': data.get('name') or data.get('customer_name') or 'Direct WhatsApp Visitor',
            'mobile_number': data.get('phone') or data.get('mobile_number') or '',
            'city': data.get('city') or '',
            'product_name': data.get('product_name') or 'Product Enquiry',
            'product_sku': data.get('sku') or data.get('product_sku') or '',
            'message': data.get('message') or 'Clicked Direct WhatsApp Enquiry button on product page',
            'type': 'direct_whatsapp',
            'whatsapp_url': data.get('whatsapp_url') or ''
        }
        record = QuotationModel.create(quote_payload)

        # Also create a copy in enquiries section so admin sees it in both places
        enquiry_record = None
        try:
            enquiry_payload = {
                'customer_name': quote_payload['customer_name'],
                'mobile_number': quote_payload['mobile_number'],
                'city': quote_payload['city'],
                'product_name': quote_payload['product_name'],
                'product_sku': quote_payload['product_sku'],
                'message': quote_payload['message'],
                'preferred_contact': 'WhatsApp Message',
                'type': 'direct_whatsapp',
                'whatsapp_url': quote_payload['whatsapp_url'],
                'status': 'New'
            }
            enquiry_record = EnquiryService.create_enquiry(enquiry_payload)
        except Exception as enq_err:
            print(f"⚠️ Enquiry click sync notice: {enq_err}")

        return jsonify({
            'ok': True,
            'success': True,
            'quotation_id': record['id'] if record else None,
            'quotation_reference': record['reference_id'] if record else None,
            'enquiry_id': enquiry_record.get('id') if isinstance(enquiry_record, dict) else None
        }), 200
    except Exception as e:
        return jsonify({'ok': False, 'success': False, 'error': str(e)}), 500
