import json
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app, abort
from models.product import ProductModel
from models.brand import BrandModel
from models.category import CategoryModel
from models.enquiry import EnquiryModel
from models.quotation import QuotationModel
from models.project import ProjectModel
from models.settings import SettingModel
from utils.constants import BUSINESSES
from utils.helpers import generate_slug
from services.image_service import save_uploaded_image

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def _extract_available_brands(data, form, default_sku):
    """Extract sub-products / brand variants from JSON string or form lists."""
    available_brands = []
    json_str = data.get('available_brands_json', '').strip()
    if json_str:
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                for idx, v in enumerate(parsed):
                    if isinstance(v, dict):
                        b_name = str(v.get('brand_name', '')).strip()
                        v_name = str(v.get('name', '')).strip()
                        v_sku = str(v.get('sku', '')).strip().upper()
                        v_img = str(v.get('image', '')).strip() or '/static/images/placeholder.jpg'
                        if b_name or v_name:
                            available_brands.append({
                                'brand_name': b_name or v_name,
                                'name': v_name or b_name,
                                'sku': v_sku or f"{default_sku}-{idx+1}",
                                'image': v_img
                            })
        except Exception as e:
            current_app.logger.warning(f"Error parsing available_brands_json: {e}")

    if not available_brands:
        b_names = form.getlist('variant_brand_name[]')
        v_names = form.getlist('variant_name[]')
        v_skus = form.getlist('variant_sku[]')
        v_images = form.getlist('variant_image[]')
        for i in range(len(b_names)):
            b_name = b_names[i].strip() if i < len(b_names) else ''
            v_name = v_names[i].strip() if i < len(v_names) else ''
            v_sku = v_skus[i].strip().upper() if i < len(v_skus) else ''
            v_img = v_images[i].strip() if i < len(v_images) else '/static/images/placeholder.jpg'
            if b_name or v_name:
                available_brands.append({
                    'brand_name': b_name or v_name,
                    'name': v_name or b_name,
                    'sku': v_sku or f"{default_sku}-{i+1}",
                    'image': v_img or '/static/images/placeholder.jpg'
                })
    return available_brands

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or session.get('role') not in ('admin', 'super_admin'):
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    stats = EnquiryModel.get_stats()
    quote_stats = QuotationModel.get_stats()
    products, product_count = ProductModel.find_all(limit=5)
    brands = BrandModel.find_all()
    enquiries, _ = EnquiryModel.find_all(limit=5)
    recent_quotes, _ = QuotationModel.find_all(limit=5)
    
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        quote_stats=quote_stats,
        product_count=product_count,
        brand_count=len(brands),
        recent_products=products,
        recent_enquiries=enquiries,
        recent_quotes=recent_quotes
    )

@admin_bp.route('/products')
@admin_required
def products():
    page = int(request.args.get('page', 1))
    business_filter = request.args.get('business', '').strip()
    view = request.args.get('view', 'active').strip()
    
    filter_query = {}
    if business_filter:
        filter_query['business_slug'] = business_filter

    limit = 50 if view == 'recycle_bin' else 20

    if view == 'recycle_bin':
        products_list, total = ProductModel.find_all(
            filter_query=filter_query if business_filter else None,
            only_deleted=True,
            limit=limit,
            page=page,
            active_only=False
        )
    else:
        products_list, total = ProductModel.find_all(
            filter_query=filter_query, 
            limit=limit, 
            page=page, 
            active_only=False,
            only_deleted=False
        )

    recycle_bin_count = ProductModel.get_recycle_bin_count()
    categories = CategoryModel.find_all()
    from services.category_service import SubcategoryService
    subcategories = SubcategoryService.get_all()
    brands = BrandModel.find_all()
    valid_businesses = [b for b in BUSINESSES if b['slug'] != 'catalogue']
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    from services.github_storage import GithubStorageService
    storage_connected = GithubStorageService.is_configured()

    return render_template(
        'admin/products.html',
        products=products_list,
        categories=categories,
        subcategories=subcategories,
        brands=brands,
        businesses=valid_businesses,
        current_business=business_filter,
        current_view=view,
        recycle_bin_count=recycle_bin_count,
        page=page,
        total_pages=total_pages,
        storage_connected=storage_connected
    )

@admin_bp.route('/products/create', methods=['GET', 'POST'])
@admin_required
def create_product():
    if request.method == 'GET':
        return redirect(url_for('admin.products'))

    try:
        data = request.form.to_dict()
        name = data.get('name', '').strip()
        sku = data.get('sku', '').strip()
        
        if not name or not sku:
            flash('Product Name and SKU are required.', 'danger')
            return redirect(url_for('admin.products'))

        # Handle image upload or direct image URL
        image_url = data.get('image_url', '').strip()
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            ok, res = save_uploaded_image(file, current_app.config['UPLOAD_FOLDER'], current_app.config['ALLOWED_EXTENSIONS'])
            if ok:
                image_url = res

        # Resolve taxonomy
        business_slug = data.get('business_slug', 'plumbing').strip()
        category_slug = data.get('category_slug', 'pipes').strip()
        subcategory_slug = data.get('subcategory_slug', 'hoses-tubes').strip()
        brand_slug = data.get('brand_slug', 'standard').strip()

        # Support on-the-fly new category creation
        new_cat_name = data.get('new_category_name', '').strip()
        if category_slug == '__new__' or new_cat_name:
            if new_cat_name:
                from services.category_service import CategoryService, SubcategoryService
                created_cat = CategoryService.create({
                    'name': new_cat_name,
                    'business_slug': business_slug,
                    'subcategory_name': data.get('new_subcategory_name', '').strip()
                })
                if created_cat and isinstance(created_cat, dict):
                    category_slug = created_cat.get('slug', category_slug)
                    subs = SubcategoryService.get_by_category(category_slug)
                    if subs:
                        subcategory_slug = subs[0].get('slug', subcategory_slug)

        # Support on-the-fly new subcategory creation
        new_sub_name = data.get('new_subcategory_name', '').strip()
        if subcategory_slug == '__new__' or (new_sub_name and category_slug != '__new__'):
            if new_sub_name:
                from services.category_service import SubcategoryService
                created_sub = SubcategoryService.create({
                    'name': new_sub_name,
                    'category_slug': category_slug,
                    'business_slug': business_slug
                })
                if created_sub and isinstance(created_sub, dict):
                    subcategory_slug = created_sub.get('slug', subcategory_slug)

        # Look up proper brand name
        brand_name = brand_slug.replace('-', ' ').title()
        for b in BrandModel.find_all():
            if b.get('slug') == brand_slug:
                brand_name = b.get('name', brand_name)
                break

        # Extract sub-products / brand variants
        available_brands = _extract_available_brands(data, request.form, sku.upper())
        available_brand_slugs = [generate_slug(b['brand_name']) for b in available_brands if b.get('brand_name')]
        if brand_slug == 'multiple' and available_brands:
            brand_name = " / ".join(dict.fromkeys([b['brand_name'] for b in available_brands if b.get('brand_name')]))

        product_data = {
            'name': name,
            'slug': generate_slug(name),
            'sku': sku.upper(),
            'description': data.get('description', ''),
            'short_description': data.get('short_description', ''),
            'features': [f.strip() for f in data.get('features', '').split('\n') if f.strip()],
            'images': [{'url': image_url or '/static/images/placeholder.jpg', 'is_primary': True}],
            'business_slug': business_slug,
            'category_slug': category_slug,
            'subcategory_slug': subcategory_slug,
            'brand_slug': brand_slug,
            'brand_name': brand_name,
            'available_brands': available_brands,
            'available_brand_slugs': available_brand_slugs,
            'is_active': True,
            'is_featured': 'is_featured' in request.form,
            'is_new': 'is_new' in request.form,
        }

        ProductModel.create(product_data)
        flash(f'Product "{name}" added successfully!', 'success')
        return redirect(url_for('admin.products', business=business_slug))
    except Exception as e:
        current_app.logger.error(f"Error creating product: {e}", exc_info=True)
        flash(f'Error saving product: {e}', 'danger')
        return redirect(url_for('admin.products'))

@admin_bp.route('/products/<product_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    if request.method == 'GET':
        return redirect(url_for('admin.products'))

    try:
        data = request.form.to_dict()
        name = data.get('name', '').strip()
        sku = data.get('sku', '').strip()
        
        if not name or not sku:
            flash('Product Name and SKU are required.', 'danger')
            return redirect(url_for('admin.products'))

        # Handle image upload or direct image URL
        image_url = data.get('image_url', '').strip()
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            ok, res = save_uploaded_image(file, current_app.config['UPLOAD_FOLDER'], current_app.config['ALLOWED_EXTENSIONS'])
            if ok:
                image_url = res

        if not image_url:
            existing = ProductModel.find_by_id(product_id, include_deleted=True)
            if existing and existing.get('images') and len(existing['images']) > 0:
                image_url = existing['images'][0].get('url', '')

        business_slug = data.get('business_slug', 'plumbing').strip()
        category_slug = data.get('category_slug', 'pipes').strip()
        subcategory_slug = data.get('subcategory_slug', 'hoses-tubes').strip()
        brand_slug = data.get('brand_slug', 'standard').strip()

        # Support on-the-fly new category creation in edit modal
        new_cat_name = data.get('new_category_name', '').strip()
        if category_slug == '__new__' or new_cat_name:
            if new_cat_name:
                from services.category_service import CategoryService, SubcategoryService
                created_cat = CategoryService.create({
                    'name': new_cat_name,
                    'business_slug': business_slug,
                    'subcategory_name': data.get('new_subcategory_name', '').strip()
                })
                if created_cat and isinstance(created_cat, dict):
                    category_slug = created_cat.get('slug', category_slug)
                    subs = SubcategoryService.get_by_category(category_slug)
                    if subs:
                        subcategory_slug = subs[0].get('slug', subcategory_slug)

        # Support on-the-fly new subcategory creation in edit modal
        new_sub_name = data.get('new_subcategory_name', '').strip()
        if subcategory_slug == '__new__' or (new_sub_name and category_slug != '__new__'):
            if new_sub_name:
                from services.category_service import SubcategoryService
                created_sub = SubcategoryService.create({
                    'name': new_sub_name,
                    'category_slug': category_slug,
                    'business_slug': business_slug
                })
                if created_sub and isinstance(created_sub, dict):
                    subcategory_slug = created_sub.get('slug', subcategory_slug)

        # Extract sub-products / brand variants
        available_brands = _extract_available_brands(data, request.form, sku.upper())
        available_brand_slugs = [generate_slug(b['brand_name']) for b in available_brands if b.get('brand_name')]

        # Look up proper brand name
        brand_name = brand_slug.replace('-', ' ').title()
        for b in BrandModel.find_all():
            if b.get('slug') == brand_slug:
                brand_name = b.get('name', brand_name)
                break

        if brand_slug == 'multiple' and available_brands:
            brand_name = " / ".join(dict.fromkeys([b['brand_name'] for b in available_brands if b.get('brand_name')]))

        product_data = {
            'name': name,
            'slug': generate_slug(name),
            'sku': sku.upper(),
            'description': data.get('description', ''),
            'short_description': data.get('short_description', ''),
            'features': [f.strip() for f in data.get('features', '').split('\n') if f.strip()],
            'images': [{'url': image_url or '/static/images/placeholder.jpg', 'is_primary': True}],
            'business_slug': business_slug,
            'category_slug': category_slug,
            'subcategory_slug': subcategory_slug,
            'brand_slug': brand_slug,
            'brand_name': brand_name,
            'available_brands': available_brands,
            'available_brand_slugs': available_brand_slugs,
            'is_active': 'is_active' in request.form,
            'is_featured': 'is_featured' in request.form,
            'is_new': 'is_new' in request.form,
        }

        success = ProductModel.update(product_id, product_data)
        if success:
            flash(f'Product "{name}" updated successfully!', 'success')
        else:
            flash('Failed to update product.', 'danger')
        return redirect(url_for('admin.products', business=business_slug))
    except Exception as e:
        current_app.logger.error(f"Error editing product: {e}", exc_info=True)
        flash(f'Error updating product: {e}', 'danger')
        return redirect(url_for('admin.products'))

@admin_bp.route('/products/<product_id>/delete', methods=['POST'])
@admin_required
def delete_product(product_id):
    existing = ProductModel.find_by_id(product_id, include_deleted=True)
    prod_name = existing.get('name', 'Product') if existing else 'Product'
    business_slug = existing.get('business_slug', '') if existing else ''
    
    success = ProductModel.delete(product_id)
    if success:
        flash(f'Product "{prod_name}" moved to Recycle Bin.', 'success')
    else:
        flash('Failed to delete product.', 'danger')
    return redirect(url_for('admin.products', business=business_slug))

@admin_bp.route('/products/<product_id>/restore', methods=['POST'])
@admin_required
def restore_product(product_id):
    existing = ProductModel.find_by_id(product_id, include_deleted=True)
    prod_name = existing.get('name', 'Product') if existing else 'Product'
    
    success = ProductModel.restore(product_id)
    if success:
        flash(f'Product "{prod_name}" restored successfully to active catalogue!', 'success')
    else:
        flash('Failed to restore product.', 'danger')
    return redirect(url_for('admin.products', view='recycle_bin'))

@admin_bp.route('/products/<product_id>/permanent-delete', methods=['POST'])
@admin_required
def permanent_delete_product(product_id):
    existing = ProductModel.find_by_id(product_id, include_deleted=True)
    prod_name = existing.get('name', 'Product') if existing else 'Product'
    
    success = ProductModel.permanent_delete(product_id)
    if success:
        flash(f'Product "{prod_name}" permanently deleted.', 'success')
    else:
        flash('Failed to permanently delete product.', 'danger')
    return redirect(url_for('admin.products', view='recycle_bin'))

@admin_bp.route('/products/empty-recycle-bin', methods=['POST'])
@admin_required
def empty_recycle_bin():
    count = ProductModel.empty_recycle_bin()
    flash(f'{count} product(s) permanently removed from Recycle Bin.', 'success')
    return redirect(url_for('admin.products', view='recycle_bin'))

@admin_bp.route('/products/reorder', methods=['POST'])
@admin_required
def reorder_products():
    try:
        data = request.get_json(force=True)
        order_list = data.get('order', [])
        if not order_list:
            return jsonify({'ok': False, 'error': 'No order data'}), 400
        ProductModel.reorder(order_list)
        return jsonify({'ok': True})
    except Exception as e:
        current_app.logger.error(f"Error reordering products: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500

@admin_bp.route('/brands')
@admin_required
def brands():
    search_query = request.args.get('q', '').strip()
    business_filter = request.args.get('business', '').strip()
    featured_filter = request.args.get('featured', '').strip()

    featured_only = (featured_filter == '1' or featured_filter.lower() == 'true')
    brands_list = BrandModel.find_all(
        featured_only=featured_only,
        business_slug=business_filter or None,
        search=search_query or None,
        is_active_only=False
    )
    all_brands = BrandModel.find_all(is_active_only=False)
    featured_count = sum(1 for b in all_brands if b.get('featured'))

    return render_template(
        'admin/brands.html',
        brands=brands_list,
        total_brands=len(all_brands),
        featured_count=featured_count,
        businesses=[b for b in BUSINESSES if b['slug'] != 'catalogue'],
        search_query=search_query,
        current_business=business_filter,
        current_featured=featured_filter
    )

@admin_bp.route('/brands/create', methods=['POST'])
@admin_required
def create_brand():
    try:
        data = request.form.to_dict()
        name = data.get('name', '').strip()
        if not name:
            flash('Brand Name is required.', 'danger')
            return redirect(url_for('admin.brands'))

        slug = data.get('slug', '').strip() or generate_slug(name)
        businesses = request.form.getlist('businesses[]') or request.form.getlist('businesses')
        if not businesses:
            businesses = [data.get('business_slug', 'hardware')]

        logo_url = data.get('logo_url', '').strip()
        if 'logo' in request.files and request.files['logo'].filename:
            file = request.files['logo']
            ok, res = save_uploaded_image(file, current_app.config['UPLOAD_FOLDER'], current_app.config['ALLOWED_EXTENSIONS'])
            if ok:
                logo_url = res

        brand_data = {
            'name': name,
            'slug': slug,
            'businesses': businesses,
            'country': data.get('country', 'India').strip() or 'India',
            'featured': 'featured' in request.form,
            'logo': logo_url or f"/static/images/brands/{slug}.png",
            'description': data.get('description', '').strip(),
            'website': data.get('website', '').strip(),
            'is_active': True
        }

        created_slug = BrandModel.create(brand_data)
        if created_slug:
            flash(f'Brand "{name}" created successfully!', 'success')
        else:
            flash(f'Failed to create brand "{name}".', 'danger')

        return redirect(url_for('admin.brands'))
    except Exception as e:
        current_app.logger.error(f"Error creating brand: {e}", exc_info=True)
        flash(f'Error creating brand: {e}', 'danger')
        return redirect(url_for('admin.brands'))

@admin_bp.route('/brands/<brand_id>/edit', methods=['POST'])
@admin_required
def edit_brand(brand_id):
    try:
        data = request.form.to_dict()
        name = data.get('name', '').strip()
        if not name:
            flash('Brand Name is required.', 'danger')
            return redirect(url_for('admin.brands'))

        slug = data.get('slug', '').strip() or generate_slug(name)
        businesses = request.form.getlist('businesses[]') or request.form.getlist('businesses')
        if not businesses:
            businesses = [data.get('business_slug', 'hardware')]

        logo_url = data.get('logo_url', '').strip()
        if 'logo' in request.files and request.files['logo'].filename:
            file = request.files['logo']
            ok, res = save_uploaded_image(file, current_app.config['UPLOAD_FOLDER'], current_app.config['ALLOWED_EXTENSIONS'])
            if ok:
                logo_url = res

        update_payload = {
            'name': name,
            'slug': slug,
            'businesses': businesses,
            'country': data.get('country', 'India').strip() or 'India',
            'featured': 'featured' in request.form,
            'description': data.get('description', '').strip(),
            'website': data.get('website', '').strip(),
            'is_active': 'is_active' in request.form
        }
        if logo_url:
            update_payload['logo'] = logo_url

        success = BrandModel.update(brand_id, update_payload)
        if success:
            flash(f'Brand "{name}" updated successfully!', 'success')
        else:
            flash(f'Failed to update brand.', 'danger')
        return redirect(url_for('admin.brands'))
    except Exception as e:
        current_app.logger.error(f"Error updating brand: {e}", exc_info=True)
        flash(f'Error updating brand: {e}', 'danger')
        return redirect(url_for('admin.brands'))

@admin_bp.route('/brands/<brand_id>/delete', methods=['POST'])
@admin_required
def delete_brand(brand_id):
    try:
        success = BrandModel.delete(brand_id)
        if success:
            flash('Brand removed successfully.', 'success')
        else:
            flash('Failed to delete brand.', 'danger')
        return redirect(url_for('admin.brands'))
    except Exception as e:
        current_app.logger.error(f"Error deleting brand: {e}", exc_info=True)
        flash(f'Error deleting brand: {e}', 'danger')
        return redirect(url_for('admin.brands'))

@admin_bp.route('/enquiries')
@admin_required
def enquiries():
    page = int(request.args.get('page', 1))
    status_filter = request.args.get('status', '')
    enquiry_list, total = EnquiryModel.find_all(status=status_filter or None, page=page, limit=20)
    stats = EnquiryModel.get_stats()
    return render_template('admin/enquiries.html', enquiries=enquiry_list, stats=stats, current_status=status_filter)

@admin_bp.route('/enquiries/<enquiry_id>/status', methods=['POST'])
@admin_required
def update_enquiry_status(enquiry_id):
    status = request.form.get('status', 'read')
    notes = request.form.get('notes', '')
    EnquiryModel.update_status(enquiry_id, status, notes)
    flash('Enquiry status updated.', 'success')
    return redirect(url_for('admin.enquiries'))

@admin_bp.route('/orders')
@admin_bp.route('/quotations')
@admin_required
def quotations():
    page = int(request.args.get('page', 1))
    status_filter = request.args.get('status', '').strip()
    search_query = request.args.get('q', '').strip()
    limit = 20

    quote_list, total = QuotationModel.find_all(
        status=status_filter or None,
        search=search_query or None,
        page=page,
        limit=limit
    )
    stats = QuotationModel.get_stats()
    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return render_template(
        'admin/quotations.html',
        quotations=quote_list,
        stats=stats,
        current_status=status_filter,
        search_query=search_query,
        page=page,
        total_pages=total_pages,
        total_quotes=total
    )

@admin_bp.route('/orders/<quote_id>/status', methods=['POST'])
@admin_bp.route('/quotations/<quote_id>/status', methods=['POST'])
@admin_required
def update_quotation_status(quote_id):
    if request.is_json:
        data = request.get_json() or {}
        status = data.get('status', 'New')
        notes = data.get('notes') or data.get('admin_notes')
    else:
        status = request.form.get('status', 'New')
        notes = request.form.get('notes', None)

    success = QuotationModel.update_status(quote_id, status, notes)
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': bool(success), 'status': status, 'notes': notes}), 200

    flash('Order status updated successfully.', 'success')
    return redirect(url_for('admin.quotations', status=request.args.get('current_status', '')))

@admin_bp.route('/orders/<quote_id>/edit', methods=['POST'])
@admin_bp.route('/quotations/<quote_id>/edit', methods=['POST'])
@admin_required
def edit_quotation(quote_id):
    try:
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()

        items = []
        raw_items = data.get('items')
        raw_items_json = data.get('items_json')
        if raw_items_json:
            try:
                items = json.loads(raw_items_json) if isinstance(raw_items_json, str) else raw_items_json
            except Exception:
                pass
        elif isinstance(raw_items, list):
            items = raw_items
        elif request.form.getlist('item_name[]'):
            names = request.form.getlist('item_name[]')
            skus = request.form.getlist('item_sku[]')
            qtys = request.form.getlist('item_qty[]')
            brands = request.form.getlist('item_brand[]')
            prices = request.form.getlist('item_price[]')
            for idx in range(len(names)):
                n = names[idx].strip()
                if n:
                    items.append({
                        'name': n,
                        'sku': skus[idx].strip().upper() if idx < len(skus) else '',
                        'quantity': qtys[idx].strip() if idx < len(qtys) else '1',
                        'brand': brands[idx].strip() if idx < len(brands) else '',
                        'price': prices[idx].strip() if idx < len(prices) else ''
                    })

        update_data = {
            'customer_name': data.get('customer_name', '').strip(),
            'mobile_number': data.get('mobile_number', '').strip(),
            'email': data.get('email', '').strip(),
            'city': data.get('city', '').strip(),
            'status': data.get('status', 'New'),
            'admin_notes': data.get('admin_notes', data.get('notes', '')).strip(),
            'message': data.get('message', '').strip(),
            'total_amount': data.get('total_amount', '').strip(),
        }
        if items:
            update_data['items'] = items

        success = QuotationModel.update(quote_id, update_data)

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': bool(success), 'data': update_data}), 200

        if success:
            flash('Order / Quotation updated successfully.', 'success')
        else:
            flash('Failed to update order.', 'danger')

        return redirect(url_for('admin.quotations', status=request.args.get('current_status', '')))
    except Exception as e:
        current_app.logger.error(f"Error editing quotation {quote_id}: {e}", exc_info=True)
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Error updating order: {e}', 'danger')
        return redirect(url_for('admin.quotations'))

@admin_bp.route('/orders/<quote_id>/delete', methods=['POST'])
@admin_bp.route('/quotations/<quote_id>/delete', methods=['POST'])
@admin_required
def delete_quotation(quote_id):
    success = QuotationModel.delete(quote_id)
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': bool(success)}), 200

    flash('Order / Quotation deleted successfully.', 'success')
    return redirect(url_for('admin.quotations'))

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        for key, value in request.form.items():
            SettingModel.set_value(key, value)
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('admin.settings'))

    all_settings = SettingModel.get_all()
    return render_template('admin/settings.html', settings=all_settings)

@admin_bp.route('/categories/create', methods=['POST'])
@admin_required
def create_category():
    try:
        data = request.get_json(silent=True) if request.is_json else request.form.to_dict()
        if not data:
            data = {}
        name = (data.get('name') or '').strip()
        business_slug = (data.get('business_slug') or 'hardware').strip()
        subcategory_name = (data.get('subcategory_name') or data.get('first_subcategory_name') or '').strip()

        if not name:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Category name is required'}), 400
            flash('Category name is required.', 'danger')
            return redirect(url_for('admin.products', business=business_slug))

        from services.category_service import CategoryService, SubcategoryService
        cat_record = CategoryService.create({
            'name': name,
            'business_slug': business_slug,
            'subcategory_name': subcategory_name
        })

        if not cat_record:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Failed to create category'}), 500
            flash('Failed to create category.', 'danger')
            return redirect(url_for('admin.products', business=business_slug))

        subcats = SubcategoryService.get_by_category(cat_record.get('slug'))

        if request.is_json:
            return jsonify({
                'ok': True,
                'success': True,
                'category': cat_record,
                'subcategories': subcats,
                'subcategory': subcats[0] if subcats else None,
                'message': f'Category "{name}" created successfully!'
            })

        flash(f'Category "{name}" added successfully!', 'success')
        return redirect(url_for('admin.products', business=business_slug))
    except Exception as e:
        current_app.logger.error(f"Error creating category: {e}", exc_info=True)
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f'Error creating category: {e}', 'danger')
        return redirect(url_for('admin.products'))

@admin_bp.route('/subcategories/create', methods=['POST'])
@admin_required
def create_subcategory():
    try:
        data = request.get_json(silent=True) if request.is_json else request.form.to_dict()
        if not data:
            data = {}
        name = (data.get('name') or '').strip()
        category_slug = (data.get('category_slug') or '').strip()
        business_slug = (data.get('business_slug') or '').strip()

        if not name or not category_slug:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Element name and Category are required'}), 400
            flash('Element name and Category are required.', 'danger')
            return redirect(url_for('admin.products'))

        from services.category_service import SubcategoryService
        sub_record = SubcategoryService.create({
            'name': name,
            'category_slug': category_slug,
            'business_slug': business_slug
        })

        if request.is_json:
            return jsonify({
                'ok': True,
                'success': True,
                'subcategory': sub_record,
                'message': f'Element "{name}" created successfully!'
            })

        flash(f'Element "{name}" added successfully!', 'success')
        return redirect(url_for('admin.products'))
    except Exception as e:
        current_app.logger.error(f"Error creating subcategory: {e}", exc_info=True)
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f'Error creating element: {e}', 'danger')
        return redirect(url_for('admin.products'))

