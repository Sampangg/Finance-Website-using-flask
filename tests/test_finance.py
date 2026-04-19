import pytest
from app import create_app, db
from app.models import User, Transaction
from app.services import FinanceService

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def init_database(app):
    """Fixture to create a test user and transaction."""
    user = User(username="testuser", email="test@test.com", password_hash="hashed_pw", daily_budget=100.0)
    db.session.add(user)
    db.session.commit()
    
    tx = Transaction(amount=25.50, title="Lunch", user_id=user.id)
    db.session.add(tx)
    db.session.commit()
    return user

def test_user_creation(init_database):
    """Test User Model logic."""
    user = User.query.filter_by(username="testuser").first()
    assert user is not None
    assert user.email == "test@test.com"
    assert user.daily_budget == 100.0

def test_dashboard_summary_logic(init_database, app):
    """Test FinanceService OOP calculation logic for budgets."""
    user = init_database
    
    # Calculate using the service layer
    summary = FinanceService.get_dashboard_summary(user.id)
    
    assert summary['spent_today'] == 25.50
    assert summary['budget_remaining'] == 74.50
    assert summary['progress_percentage'] == 25.50

def test_negative_transaction_validation(client, init_database):
    """Test that negative amounts are rejected (via Route logic)."""
    user = init_database
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id) # Mock Flask-Login login

    response = client.post('/transaction/add', data={
        'amount': '-10',
        'title': 'Hacker attempt',
        'category_id': ''
    }, follow_redirects=True)
    
    assert b'Amount cannot be negative' in response.data