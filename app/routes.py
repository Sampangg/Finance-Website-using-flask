from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, jsonify, abort
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import User, Transaction, Category, SystemConfig
from app.services import FinanceService
from functools import wraps

auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Redirect visitors to the login page."""
    return redirect(url_for('auth.login'))

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ================= AUTHENTICATION ROUTES =================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        # .lower() ensures "Admin@Email.com" becomes "admin@email.com"
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Explicitly set is_active=True just in case the database default fails
        user = User(username=username, email=email, password_hash=hashed_password, is_active=True)
        
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Login Unsuccessful. That email is not registered.', 'danger')
        elif not bcrypt.check_password_hash(user.password_hash, password):
            flash('Login Unsuccessful. Incorrect password.', 'danger')
        elif not user.is_active:
            flash('Login Unsuccessful. This account is deactivated.', 'warning')
        else:
            remember = True if request.form.get('remember') else False
            login_user(user, remember=remember)
            return redirect(url_for('main.dashboard'))
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Feature 4: Secure Logout."""
    logout_user()
    return redirect(url_for('main.index'))

# ================= CORE EXPENSE ROUTES =================

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Feature 12, 15, 18: Main Hub."""
    summary = FinanceService.get_dashboard_summary(current_user.id)
    weekly_total = FinanceService.get_weekly_summary(current_user.id)
    categories = Category.query.all()
    
    return render_template('dashboard.html', 
                           summary=summary, 
                           weekly_total=weekly_total,
                           categories=categories)

@main_bp.route('/transaction/add', methods=['POST'])
@login_required
def add_transaction():
    """Feature 9 & 10 & 21 (Validation via form/backend)."""
    amount = float(request.form.get('amount'))
    if amount < 0:
        flash('Amount cannot be negative.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    tx = Transaction(
        amount=amount,
        title=request.form.get('title'),
        category_id=request.form.get('category_id'),
        user_id=current_user.id
    )
    db.session.add(tx)
    db.session.commit()
    flash('Transaction added!', 'success')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/transaction/<int:id>/delete', methods=['POST'])
@login_required
def delete_transaction(id):
    """Feature 14: Delete Entry."""
    tx = Transaction.query.get_or_404(id)
    if tx.user_id == current_user.id:
        db.session.delete(tx)
        db.session.commit()
        flash('Transaction deleted.', 'info')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/export')
@login_required
def export_csv():
    """Feature 19: Export CSV."""
    csv_data = FinanceService.export_transactions_csv(current_user.id)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=transactions.csv"}
    )

@main_bp.route('/api/chart-data')
@login_required
def chart_data():
    """Feature 17 API endpoint for Chart.js."""
    return jsonify(FinanceService.get_chart_data(current_user.id))

# ================= ADMIN ROUTES =================

@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    """Feature 26, 27: Admin overview."""
    stats = FinanceService.get_global_stats()
    users = User.query.all()
    config = SystemConfig.query.first()
    return render_template('admin/dashboard.html', stats=stats, users=users, config=config)

@admin_bp.route('/toggle-maintenance', methods=['POST'])
@admin_required
def toggle_maintenance():
    """Feature 30: Maintenance Mode Toggle."""
    config = SystemConfig.query.first()
    if not config:
        config = SystemConfig(maintenance_mode=True)
        db.session.add(config)
    else:
        config.maintenance_mode = not config.maintenance_mode
    db.session.commit()
    flash(f"Maintenance mode is now {'ON' if config.maintenance_mode else 'OFF'}", "warning")
    return redirect(url_for('admin.admin_dashboard'))

@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Feature 7 & 24: Profile Management and Currency Selector."""
    if request.method == 'POST':
        # Update Currency
        if 'currency' in request.form:
            current_user.currency = request.form.get('currency')
            db.session.commit()
            flash(f"Currency updated to {current_user.currency}", "success")
        
        # Update Daily Budget
        if 'daily_budget' in request.form:
            current_user.daily_budget = float(request.form.get('daily_budget'))
            db.session.commit()
            flash("Daily budget updated!", "success")

    # Get categories created by this user or global ones
    user_categories = Category.query.filter((Category.is_global == True) | (Category.name != "")).all()
    return render_template('settings.html', categories=user_categories)

@main_bp.route('/category/add', methods=['POST'])
@login_required
def add_category():
    """Allow users to create their own spending categories."""
    name = request.form.get('name').strip()
    if name:
        # Check if category already exists
        existing = Category.query.filter_by(name=name).first()
        if not existing:
            new_cat = Category(name=name, is_global=False)
            db.session.add(new_cat)
            db.session.commit()
            flash(f"Category '{name}' added!", "success")
        else:
            flash("Category already exists.", "info")
    return redirect(url_for('main.settings'))

@main_bp.route('/update-budget-dashboard', methods=['POST'])
@login_required
def update_budget_dashboard():
    """Quickly update budget from the dashboard."""
    new_budget = request.form.get('daily_budget')
    if new_budget:
        current_user.daily_budget = float(new_budget)
        db.session.commit()
        flash(f"Daily budget updated to {current_user.currency}{new_budget}", "success")
    return redirect(url_for('main.dashboard'))