from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    """User Model representing account information and preferences."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # Feature 6: Password Hashing
    
    # Feature 8 & 24: Monthly Budget and NPR Default
    monthly_budget = db.Column(db.Float, default=15000.0) 
    currency = db.Column(db.String(5), default='Rs.')
    
    # Feature 26 & 29: Admin Controls
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    transactions = db.relationship('Transaction', backref='author', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    is_global = db.Column(db.Boolean, default=False) 
    
    # This links categories to transactions
    transactions = db.relationship('Transaction', backref='category', lazy=True)

class Transaction(db.Model):
    """Core Expense Log Model."""
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False) # Handled by WTF for non-negative
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Feature 11
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    
    category = db.relationship('Category')

class SystemConfig(db.Model):
    """Global system configuration (e.g., Maintenance mode)."""
    id = db.Column(db.Integer, primary_key=True)
    maintenance_mode = db.Column(db.Boolean, default=False)