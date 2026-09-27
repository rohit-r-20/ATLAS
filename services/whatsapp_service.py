import os
import re
import threading
import urllib.parse
from datetime import datetime
import requests
from utils.constants import COMPANY_INFO

def sanitize_phone_number(phone_str, default_country_code="91"):
    """
    Sanitizes a phone number to international WhatsApp format without '+' or spaces.
    e.g. '+91 98406 37307' -> '919840637307'
         '9840637307' -> '919840637307'
    """
    if not phone_str:
        return ""
    digits = re.sub(r'\D', '', str(phone_str))
    if len(digits) == 10:
        return f"{default_country_code}{digits}"
    return digits

def get_target_whatsapp_number():
    """
    Retrieves target WhatsApp number from environment or company constants.
    Default: Sathik Traders official WhatsApp (+91 98406 37307).
    """
    env_target = os.getenv('WHATSAPP_TARGET_PHONE')
    if env_target:
        return sanitize_phone_number(env_target)
    
    company_wa = COMPANY_INFO.get('whatsapp') or COMPANY_INFO.get('mobile') or '919840637307'
    return sanitize_phone_number(company_wa)

def format_whatsapp_quote_message(enquiry_data):
    """
    Generates a structured, professional WhatsApp message text for quote requests.
    Uses WhatsApp markdown styling (*bold*, _italic_).
    """
    customer_name = (enquiry_data.get('customer_name') or enquiry_data.get('name') or 'Valued Customer').strip()
    mobile = (enquiry_data.get('mobile_number') or enquiry_data.get('mobile') or enquiry_data.get('phone') or 'N/A').strip()
    email = (enquiry_data.get('email') or '').strip()
    address = (enquiry_data.get('address') or enquiry_data.get('city') or '').strip()
    interested_in = (enquiry_data.get('interested_in') or enquiry_data.get('category') or '').strip()
    product_name = (enquiry_data.get('product_name') or '').strip()
    preferred_contact = (enquiry_data.get('preferred_contact') or 'WhatsApp Message').strip()
    user_message = (enquiry_data.get('message') or '').strip()
    
    timestamp = datetime.now().strftime("%d-%b-%Y %I:%M %p")
    
    lines = [
        "📦 *NEW QUOTE REQUEST - SATHIK *",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"👤 *Customer:* {customer_name}",
        f"📱 *Phone:* {mobile}",
    ]
    
    if email:
        lines.append(f"✉️ *Email:* {email}")
    if address:
        lines.append(f"📍 *Location:* {address}")
    if interested_in:
        lines.append(f"🏢 *Vertical / Category:* {interested_in}")
    if product_name:
        lines.append(f"🏷️ *Product / Items:* {product_name}")
    if preferred_contact:
        lines.append(f"💬 *Preferred Contact:* {preferred_contact}")
    
    if user_message:
        lines.append("📝 *Details / Requirements:*")
        lines.append(user_message)
        
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━",
        f"⏱️ *Time:* {timestamp}",
        "🌐 *Source:* Sathik Groups Web Platform (sathikgroups.com)"
    ])
    
    return "\n".join(lines)

def generate_whatsapp_deeplink(enquiry_data, target_phone=None):
    """
    Constructs a universal WhatsApp deep link compatible with both mobile app & WhatsApp Web.
    """
    phone = target_phone or get_target_whatsapp_number()
    message_text = format_whatsapp_quote_message(enquiry_data)
    encoded_text = urllib.parse.quote(message_text)
    return f"https://api.whatsapp.com/send?phone={phone}&text={encoded_text}"

def _send_callmebot_notification(target_phone, message_text, api_key):
    """
    Delivers automated message via CallMeBot free WhatsApp API gateway.
    """
    try:
        encoded_text = urllib.parse.quote(message_text)
        url = f"https://api.callmebot.com/whatsapp.php?phone={target_phone}&text={encoded_text}&apikey={api_key}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            print(f"✅ CallMeBot WhatsApp automated notification delivered to {target_phone}")
            return True
        else:
            print(f"⚠️ CallMeBot returned status {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"⚠️ CallMeBot notification exception: {e}")
        return False

def _send_webhook_notification(webhook_url, enquiry_data, formatted_message):
    """
    Delivers enquiry payload to external automation webhook (Zapier, Make, n8n, etc.).
    """
    try:
        payload = {
            "source": "Sathik Groups Web Platform",
            "timestamp": datetime.now().isoformat(),
            "formatted_whatsapp_message": formatted_message,
            "enquiry": enquiry_data
        }
        res = requests.post(webhook_url, json=payload, timeout=8)
        if res.status_code in (200, 201, 202):
            print(f"✅ WhatsApp automation webhook triggered: {webhook_url}")
            return True
        else:
            print(f"⚠️ Webhook returned status {res.status_code}")
            return False
    except Exception as e:
        print(f"⚠️ WhatsApp webhook notification exception: {e}")
        return False

def trigger_background_whatsapp_dispatch(enquiry_data, formatted_message):
    """
    Dispatches automated server-side notification in a non-blocking background daemon thread.
    """
    callmebot_key = os.getenv('CALLMEBOT_API_KEY')
    callmebot_phone = os.getenv('CALLMEBOT_PHONE') or get_target_whatsapp_number()
    webhook_url = os.getenv('WHATSAPP_WEBHOOK_URL')
    
    def worker():
        if callmebot_key and callmebot_phone:
            _send_callmebot_notification(callmebot_phone, formatted_message, callmebot_key)
        if webhook_url:
            _send_webhook_notification(webhook_url, enquiry_data, formatted_message)
            
    if (callmebot_key and callmebot_phone) or webhook_url:
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

def process_whatsapp_enquiry(enquiry_data):
    """
    Main entrypoint for processing WhatsApp integration upon quote/enquiry submission.
    Returns dictionary with generated deep-link URL and automated dispatch status.
    """
    target_phone = get_target_whatsapp_number()
    formatted_message = format_whatsapp_quote_message(enquiry_data)
    whatsapp_url = generate_whatsapp_deeplink(enquiry_data, target_phone=target_phone)
    
    # Check if automated server-side delivery is configured
    callmebot_key = os.getenv('CALLMEBOT_API_KEY')
    webhook_url = os.getenv('WHATSAPP_WEBHOOK_URL')
    has_server_gateway = bool((callmebot_key and target_phone) or webhook_url)
    
    if has_server_gateway:
        trigger_background_whatsapp_dispatch(enquiry_data, formatted_message)
        
    return {
        "whatsapp_url": whatsapp_url,
        "target_phone": target_phone,
        "server_gateway_active": has_server_gateway,
        "formatted_message": formatted_message
    }
