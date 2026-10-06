from flask import Blueprint, render_template, request, abort
from models.product import ProductModel
from models.category import CategoryModel
from models.brand import BrandModel
from utils.constants import BUSINESSES, COMPANY_INFO
from utils.helpers import build_whatsapp_url, build_product_whatsapp_message

product_bp = Blueprint('product', __name__)

@product_bp.route('/products')
def product_list():
    business_filter = request.args.get('business', '').strip()
    category_filter = request.args.get('category', '').strip()
    subcategory_filter = request.args.get('subcategory', '').strip()
    brand_filter = request.args.get('brand', '').strip()
    search_query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    limit = 12

    filter_query = {}
    if business_filter:
        filter_query['business_slug'] = business_filter
    if category_filter:
        filter_query['category_slug'] = category_filter
    if subcategory_filter:
        filter_query['subcategory_slug'] = subcategory_filter
    if brand_filter:
        filter_query['brand_slug'] = brand_filter
    if search_query:
        filter_query['$or'] = [
            {'name': {'$regex': search_query, '$options': 'i'}},
            {'description': {'$regex': search_query, '$options': 'i'}},
            {'brand_name': {'$regex': search_query, '$options': 'i'}},
            {'sku': {'$regex': search_query, '$options': 'i'}}
        ]

    grouped_mode = False
    bath_kitchen_products = []
    plumbing_products = []
    hardware_products = []

    # Check if we should render in grouped mode (no active filters or search and page is 1)
    if not (business_filter or category_filter or subcategory_filter or brand_filter or search_query) and page == 1:
        grouped_mode = True
        bath_kitchen_products, _ = ProductModel.find_all(
            filter_query={'business_slug': 'bath-kitchen'},
            limit=4
        )
        plumbing_products, _ = ProductModel.find_all(
            filter_query={'business_slug': 'plumbing'},
            limit=4
        )
        hardware_products, _ = ProductModel.find_all(
            filter_query={'business_slug': 'hardware'},
            limit=4
        )

    products, total = ProductModel.find_all(
        filter_query=filter_query,
        page=page,
        limit=limit
    )

    categories = CategoryModel.find_all(business_slug=business_filter or None)
    
    # Fetch subcategories for active category/business
    from services.category_service import SubcategoryService
    if category_filter:
        subcategories = SubcategoryService.get_by_category(category_filter)
    elif business_filter:
        subcategories = SubcategoryService.get_by_business(business_filter)
    else:
        subcategories = SubcategoryService.get_all()

    brands = BrandModel.find_all(business_slug=business_filter or None)

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return render_template(
        'products.html',
        products=products,
        businesses=BUSINESSES,
        categories=categories,
        subcategories=subcategories,
        brands=brands,
        current_business=business_filter,
        current_category=category_filter,
        current_subcategory=subcategory_filter,
        current_brand=brand_filter,
        search_query=search_query,
        page=page,
        total_pages=total_pages,
        total_products=total,
        company=COMPANY_INFO,
        grouped_mode=grouped_mode,
        bath_kitchen_products=bath_kitchen_products,
        plumbing_products=plumbing_products,
        hardware_products=hardware_products
    )


@product_bp.route('/products/<subcategory_slug>/<product_slug>')
@product_bp.route('/products/<product_slug>')
@product_bp.route('/product/<product_slug>')
def product_detail(product_slug, subcategory_slug='uncategorized'):
    product = ProductModel.find_by_slug(subcategory_slug, product_slug)
    if not product:
        # Also try searching by product_slug if first argument was interpreted as product_slug
        product = ProductModel.find_by_id(product_slug) or ProductModel.find_by_slug('', product_slug)
    if not product:
        abort(404)

    # Related products: prioritize same subcategory, then category, then business
    related_products = []
    seen_ids = {str(product.get('slug') or product.get('_id') or product.get('id'))}

    # 1. Try same subcategory
    sub_prods, _ = ProductModel.find_all(
        filter_query={'subcategory_slug': subcategory_slug, 'slug': {'$ne': product_slug}},
        limit=4
    )
    for p in sub_prods:
        p_id = str(p.get('slug') or p.get('_id') or p.get('id'))
        if p_id not in seen_ids:
            related_products.append(p)
            seen_ids.add(p_id)

    # 2. Fill from same category
    if len(related_products) < 4 and product.get('category_slug'):
        cat_prods, _ = ProductModel.find_all(
            filter_query={'category_slug': product.get('category_slug'), 'slug': {'$ne': product_slug}},
            limit=8
        )
        for p in cat_prods:
            p_id = str(p.get('slug') or p.get('_id') or p.get('id'))
            if p_id not in seen_ids:
                related_products.append(p)
                seen_ids.add(p_id)
            if len(related_products) >= 4:
                break

    # 3. Fill from same business/store vertical
    if len(related_products) < 4 and product.get('business_slug'):
        biz_prods, _ = ProductModel.find_all(
            filter_query={'business_slug': product.get('business_slug'), 'slug': {'$ne': product_slug}},
            limit=8
        )
        for p in biz_prods:
            p_id = str(p.get('slug') or p.get('_id') or p.get('id'))
            if p_id not in seen_ids:
                related_products.append(p)
                seen_ids.add(p_id)
            if len(related_products) >= 4:
                break

    # WhatsApp pre-filled enquiry text
    wa_message = build_product_whatsapp_message(product.get('name', ''), product.get('sku', ''))
    wa_url = build_whatsapp_url(COMPANY_INFO['whatsapp'], wa_message)

    return render_template(
        'product.html',
        product=product,
        related_products=related_products,
        whatsapp_url=wa_url,
        company=COMPANY_INFO
    )
