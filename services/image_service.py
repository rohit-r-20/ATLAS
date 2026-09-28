import os
import io
import base64
from werkzeug.utils import secure_filename
from PIL import Image

def optimize_image_to_data_url(file_bytes, max_dim=800, quality=82):
    """
    Optimizes and compresses an image into a compact Base64 WebP/JPEG/SVG data URL.
    Embeds directly into product data so images load instantly anywhere without 404s.
    """
    try:
        # Check if file is SVG vector
        header_sample = file_bytes[:300].lower()
        if b'<svg' in header_sample or b'<?xml' in header_sample:
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            return f"data:image/svg+xml;base64,{b64}"

        img = Image.open(io.BytesIO(file_bytes))
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGBA')
            fmt = 'WEBP'
            mime = 'image/webp'
        else:
            img = img.convert('RGB')
            fmt = 'WEBP'
            mime = 'image/webp'

        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format=fmt, quality=quality, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"⚠️ Image base64 optimization notice: {e}")
        b64 = base64.b64encode(file_bytes).decode('utf-8')
        # Check if svg fallback
        if b'<svg' in file_bytes[:300].lower():
            return f"data:image/svg+xml;base64,{b64}"
        return f"data:image/jpeg;base64,{b64}"

def save_uploaded_image(file_obj, upload_folder, allowed_extensions):
    """
    Saves or optimizes an uploaded image file safely.
    Supports .webpg, .webp, .png, .jpg, .svg, etc.
    Returns (success, url_or_error)
    """
    if not file_obj or file_obj.filename == '':
        return False, 'No file selected'

    filename = secure_filename(file_obj.filename)
    raw_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    # Normalize webpg -> webp
    norm_ext = 'webp' if raw_ext == 'webpg' else raw_ext

    # Allow if either raw_ext or norm_ext is permitted
    if raw_ext not in allowed_extensions and norm_ext not in allowed_extensions:
        return False, f'File extension .{raw_ext} is not allowed'

    # Read raw bytes directly from upload stream
    file_bytes = file_obj.read()
    if not file_bytes:
        return False, 'Uploaded file is empty'

    # Safely attempt saving locally if writable (for local dev and git commits)
    local_saved_url = None
    try:
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        local_saved_url = f"/static/uploads/{filename}"
    except Exception as e:
        print(f"ℹ️ Local disk write bypassed on read-only serverless: {e}")

    # 1. Upload to GitHub repository if GITHUB_TOKEN is configured
    try:
        from services.github_storage import GithubStorageService
        if GithubStorageService.is_configured():
            ok, url_or_err = GithubStorageService.upload_image(file_bytes, filename)
            if ok and (url_or_err.startswith('http://') or url_or_err.startswith('https://')):
                return True, url_or_err
    except Exception as e:
        print(f"⚠️ GitHub image upload notice: {e}")

    # If local disk write succeeded and file is accessible via static, use it
    if local_saved_url:
        return True, local_saved_url

    # 2. Resilient Cloud Fallback: Convert to self-contained optimized WebP/SVG Data URI
    data_url = optimize_image_to_data_url(file_bytes)
    return True, data_url

def save_brand_logo(file_obj, slug, allowed_extensions=None):
    """
    Specialized handler to save brand logos directly to static/images/brands/{slug}.{ext}.
    Supports .webpg, .webp, .png, .jpg, .svg, and preserves transparency for logos.
    Returns (success, url_or_error)
    """
    if not file_obj or not file_obj.filename:
        return False, 'No file selected'

    raw_filename = secure_filename(file_obj.filename)
    raw_ext = raw_filename.rsplit('.', 1)[-1].lower() if '.' in raw_filename else ''

    # Normalize extensions
    if raw_ext in ('webpg', 'webp'):
        clean_ext = 'webp'
    elif raw_ext in ('jpeg', 'jpg', 'jfif'):
        clean_ext = 'jpg'
    elif raw_ext in ('svg', 'svgz'):
        clean_ext = 'svg'
    elif raw_ext in ('png', 'gif', 'avif'):
        clean_ext = raw_ext
    else:
        clean_ext = raw_ext

    # Check allowed extensions if provided
    if allowed_extensions:
        if raw_ext not in allowed_extensions and clean_ext not in allowed_extensions:
            return False, f'File extension .{raw_ext} is not supported. Use WEBP, WEBPG, PNG, JPG, or SVG.'

    file_bytes = file_obj.read()
    if not file_bytes:
        return False, 'Uploaded file is empty'

    # Process image bytes
    processed_bytes = file_bytes
    if clean_ext != 'svg':
        try:
            img = Image.open(io.BytesIO(file_bytes))
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            # Preserve transparency for logos
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')

            # Resize to max 600x600 for sharp, lightweight brand logos
            img.thumbnail((600, 600), Image.Resampling.LANCZOS)
            buf = io.BytesIO()

            if clean_ext == 'webp':
                img.save(buf, format='WEBP', quality=92, method=6)
            elif clean_ext == 'png':
                img.save(buf, format='PNG', optimize=True)
            elif clean_ext == 'jpg':
                img.save(buf, format='JPEG', quality=90, optimize=True)
            else:
                img.save(buf, format='WEBP', quality=92)
                clean_ext = 'webp'

            processed_bytes = buf.getvalue()
        except Exception as e:
            print(f"⚠️ PIL brand logo optimization warning: {e}")
            processed_bytes = file_bytes

    # Destination directories
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    brands_dir = os.path.join(base_dir, 'static', 'images', 'brands')
    uploads_dir = os.path.join(base_dir, 'static', 'uploads')
    
    target_filename = f"{slug}.{clean_ext}"
    local_saved = False

    try:
        os.makedirs(brands_dir, exist_ok=True)
        brand_file_path = os.path.join(brands_dir, target_filename)
        with open(brand_file_path, 'wb') as f:
            f.write(processed_bytes)
        local_saved = True

        # If clean_ext is webp, also write .webpg file so direct .webpg requests resolve
        if clean_ext == 'webp':
            try:
                with open(os.path.join(brands_dir, f"{slug}.webpg"), 'wb') as f:
                    f.write(processed_bytes)
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️ Could not write to static/images/brands: {e}")

    # Also save a copy to uploads folder
    try:
        os.makedirs(uploads_dir, exist_ok=True)
        with open(os.path.join(uploads_dir, f"brand_{target_filename}"), 'wb') as f:
            f.write(processed_bytes)
        if clean_ext == 'webp':
            with open(os.path.join(uploads_dir, f"brand_{slug}.webpg"), 'wb') as f:
                f.write(processed_bytes)
    except Exception:
        pass

    # Optional GitHub storage upload for serverless persistence
    try:
        from services.github_storage import GithubStorageService
        if GithubStorageService.is_configured():
            ok, url_or_err = GithubStorageService.upload_image(processed_bytes, f"static/images/brands/{target_filename}")
            if ok and (url_or_err.startswith('http://') or url_or_err.startswith('https://')):
                return True, url_or_err
    except Exception as e:
        print(f"⚠️ GitHub storage upload note: {e}")

    # Return local static path if file was written to disk
    if local_saved:
        return True, f"/static/images/brands/{target_filename}"

    # Serverless fallback: Data URI
    if clean_ext == 'svg':
        mime = 'image/svg+xml'
    elif clean_ext == 'webp':
        mime = 'image/webp'
    elif clean_ext == 'png':
        mime = 'image/png'
    else:
        mime = 'image/jpeg'

    b64 = base64.b64encode(processed_bytes).decode('utf-8')
    return True, f"data:{mime};base64,{b64}"
