import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'sathik-groups-secret-key-2024-change-in-production')
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Resend Email Configuration
    RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')
    RESEND_FROM = os.getenv('RESEND_FROM', 'onboarding@resend.dev')
    RESEND_TO = os.getenv('RESEND_TO', 'info@sathikgroups.com')
    
    # WhatsApp Automation Configuration
    WHATSAPP_TARGET_PHONE = os.getenv('WHATSAPP_TARGET_PHONE', '919840637307')
    CALLMEBOT_API_KEY = os.getenv('CALLMEBOT_API_KEY', '')
    CALLMEBOT_PHONE = os.getenv('CALLMEBOT_PHONE', '')
    WHATSAPP_WEBHOOK_URL = os.getenv('WHATSAPP_WEBHOOK_URL', '')
    
    PORT = int(os.getenv('PORT', 5001))
    
    # Upload Settings
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'webpg', 'svg', 'pdf', 'jfif', 'avif'}
    
    # Cloudinary Config (Optional)
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')
    
    # GitHub Storage Configuration (Persistent zero-database storage on Vercel)
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    GITHUB_REPO = os.getenv('GITHUB_REPO', 'rohit-r-20/Sathik')
    GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
    
    # Pagination Defaults
    PRODUCTS_PER_PAGE = 12
    ADMIN_ITEMS_PER_PAGE = 20
