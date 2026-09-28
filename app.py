import os
from flask import Flask, render_template
from config import Config
from database.supabase import init_supabase

import mimetypes
mimetypes.add_type('image/webp', '.webpg')
mimetypes.add_type('image/webp', '.webp')

# Import Blueprints
from routes.home_routes import home_bp
from routes.product_routes import product_bp
from routes.category_routes import category_bp
from routes.brand_routes import brand_bp
from routes.enquiry_routes import enquiry_bp
from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.cart_routes import cart_bp
from routes.order_routes import order_bp
from routes.payment_routes import payment_bp

def create_app(config_class=Config):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        static_folder=os.path.join(root_dir, 'static'),
        template_folder=os.path.join(root_dir, 'templates'),
        static_url_path='/static'
    )
    app.config.from_object(config_class)

    # Initialize Supabase Client
    init_supabase(app)

    # Global Template Context Processor (inject company info and canonical_url in all templates)
    from utils.constants import COMPANY_INFO
    from utils.seo import get_canonical_url
    @app.context_processor
    def inject_global_context():
        return {
            'company': COMPANY_INFO,
            'canonical_url': get_canonical_url()
        }


    # Register Blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(brand_bp)
    app.register_blueprint(enquiry_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(payment_bp)

    # Global 404 Error Handler
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', content="<div class='container section text-center'><h1>404</h1><p>Page Not Found</p><a href='/' class='btn btn-primary'>Back to Home</a></div>"), 404

    # Global 500 Error Handler
    @app.errorhandler(500)
    def server_error(e):
        return render_template('base.html', content="<div class='container section text-center'><h1>500</h1><p>Server Error</p><a href='/' class='btn btn-primary'>Back to Home</a></div>"), 500

    return app

# Top-level Flask application instance exported for Vercel Serverless Functions
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', app.config.get('PORT', 5001)))
    print(f"🚀 Sathik Groups Flask Catalogue Platform starting on http://localhost:{port}")
    try:
        app.run(host='0.0.0.0', port=port, debug=True)
    except OSError as err:
        if "Address already in use" in str(err) or getattr(err, 'errno', None) in (48, 98):
            fallback_port = 5002 if port == 5001 else 5001
            print(f"⚠️ Port {port} is occupied. Starting on fallback port http://localhost:{fallback_port}")
            app.run(host='0.0.0.0', port=fallback_port, debug=True)
        else:
            raise err
