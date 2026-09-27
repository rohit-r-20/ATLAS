import os
from flask import Blueprint, render_template, redirect, url_for, send_from_directory, current_app, Response
from models.product import ProductModel
from models.brand import BrandModel
from models.project import ProjectModel
from utils.constants import BUSINESSES, COMPANY_INFO

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def index():
    featured_products = ProductModel.find_featured(limit=12)
    bath_products, _ = ProductModel.find_all(filter_query={'business_slug': 'bath-kitchen'}, limit=6)
    plumbing_products, _ = ProductModel.find_all(filter_query={'business_slug': 'plumbing'}, limit=6)
    hardware_products, _ = ProductModel.find_all(filter_query={'business_slug': 'hardware'}, limit=6)
    featured_brands = BrandModel.find_all(featured_only=True)

    # Dynamically detect awards from static/images/awards
    awards_dir = os.path.join(current_app.static_folder, 'images', 'awards')
    if not os.path.exists(awards_dir):
        awards_dir = os.path.join(current_app.static_folder, 'images', 'Awards')
    awards_list = []
    if os.path.exists(awards_dir):
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.svg'}
        awards_list = [
            f for f in sorted(os.listdir(awards_dir))
            if not f.startswith('.') and os.path.splitext(f)[1].lower() in valid_exts
        ]

    return render_template(
        'index.html',
        businesses=BUSINESSES,
        featured_products=featured_products,
        bath_products=bath_products,
        plumbing_products=plumbing_products,
        hardware_products=hardware_products,
        featured_brands=featured_brands,
        awards=awards_list,
        company=COMPANY_INFO
    )

@home_bp.route('/about')
def about():
    return redirect(url_for('home.index') + '#aboutUs')

@home_bp.route('/locations/red-hills/')
@home_bp.route('/locations/red-hills')
def red_hills():
    """Local SEO landing page — Red Hills, Chennai."""
    return render_template('red_hills.html', company=COMPANY_INFO)

@home_bp.route('/projects')
def projects():
    project_list = ProjectModel.find_all()
    return render_template('projects.html', projects=project_list, company=COMPANY_INFO)
@home_bp.route('/favicon.ico')
def favicon():
    static_folder = current_app.static_folder
    logo_dir = os.path.join(static_folder, 'images', 'logo')
    if os.path.exists(os.path.join(logo_dir, 'favicon.ico')):
        return send_from_directory(logo_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    return send_from_directory(static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@home_bp.route('/site.webmanifest')
def site_manifest():
    return send_from_directory(current_app.static_folder, 'site.webmanifest', mimetype='application/manifest+json')

@home_bp.route('/robots.txt')
def robots():
    static_folder = current_app.static_folder
    robots_path = os.path.join(static_folder, 'robots.txt')
    if os.path.exists(robots_path):
        return send_from_directory(static_folder, 'robots.txt', mimetype='text/plain')
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_robots = os.path.join(root_dir, 'robots.txt')
    if os.path.exists(root_robots):
        return send_from_directory(root_dir, 'robots.txt', mimetype='text/plain')
    fallback_content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /msasathik\n"
        "Disallow: /ashiksathik\n"
        "Disallow: /register\n"
        "Disallow: /logout\n"
        "Disallow: /cart/\n"
        "Disallow: /orders/\n"
        "Disallow: /payment/\n"
        "Disallow: /enquiry/submit\n"
        "Disallow: /categories\n"
        "Allow: /static/\n"
        "Sitemap: https://sathikgroups.com/sitemap.xml\n"
    )
    return Response(fallback_content, mimetype='text/plain')

@home_bp.route('/sitemap.xml')
def sitemap():
    static_folder = current_app.static_folder
    sitemap_path = os.path.join(static_folder, 'sitemap.xml')
    if os.path.exists(sitemap_path):
        return send_from_directory(static_folder, 'sitemap.xml', mimetype='application/xml')
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_sitemap = os.path.join(root_dir, 'sitemap.xml')
    if os.path.exists(root_sitemap):
        return send_from_directory(root_dir, 'sitemap.xml', mimetype='application/xml')
    try:
        from services.sitemap_service import generate_sitemap_xml
        return Response(generate_sitemap_xml(), mimetype='application/xml')
    except Exception as err:
        print(f"⚠️ Error generating dynamic sitemap: {err}")
        return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>', mimetype='application/xml')

