from flask import Flask, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
import os

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
csrf = CSRFProtect()

def create_app(config_class='config.Config'):
    app = Flask(__name__)
    
    # Security and Session Config
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Database Logic: SQLite for local, PostgreSQL for Render
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///finance.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

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

   # --- Inject Default Categories ---
    with app.app_context():
        # 1. Force database tables to exist before we try to add anything!
        db.create_all() 
        
        from app.models import Category
        try:
            defaults = ['Food', 'Transportation', 'Entertainment', 'Vehicle Fuel', 'Utilities']
            for cat_name in defaults:
                if not Category.query.filter_by(name=cat_name).first():
                    db.session.add(Category(name=cat_name, is_global=True))
            db.session.commit()
        except Exception as e:
            # 2. Print the exact error so it's no longer a secret!
            print(f"DATABASE INJECTION ERROR: {e}") 

    return app