from flask import Flask, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta  # <--- 1. ADD THIS IMPORT

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
csrf = CSRFProtect()

def create_app(config_class='config.Config'):
    """Application Factory Pattern"""
    app = Flask(__name__)
    
    # Existing Configs
    app.config['SECRET_KEY'] = 'dev-secret-key-replace-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- 2. ADD THESE SECURITY LINES HERE ---
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # ----------------------------------------

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Global Maintenance Mode Check
    @app.before_request
    def check_maintenance():
        from app.models import SystemConfig
        if request.path.startswith('/static') or request.path.startswith('/admin'):
            return
        
        try:
            config = SystemConfig.query.first()
            if config and config.maintenance_mode:
                return render_template('errors/maintenance.html'), 503
        except Exception:
            pass

    # Custom Error Pages
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Register Blueprints
    from app.routes import main_bp, auth_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app