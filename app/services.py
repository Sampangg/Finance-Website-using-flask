from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import Transaction, User, Category
from app import db
import csv
import io

class FinanceService:
    """
    Service Layer (OOP Principle) to handle all business logic.
    Keeps routing files thin and makes logic highly testable.
    """

    @staticmethod
    def get_dashboard_summary(user_id):
        """Feature 12: Get 10 recent transactions and budget progress."""
        recent_tx = Transaction.query.filter_by(user_id=user_id)\
                        .order_by(Transaction.date.desc()).limit(10).all()
        
        # Feature 18: Budget Progress Bar Math
        today = datetime.utcnow().date()
        today_start = datetime(today.year, today.month, today.day)
        tomorrow_start = today_start + timedelta(days=1) # NEW: Stop counting at midnight tonight!
        
        spent_today = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id, 
                    Transaction.date >= today_start,
                    Transaction.date < tomorrow_start)\
            .scalar() or 0.0

        user = User.query.get(user_id)
        budget_remaining = user.monthly_budget - spent_today
        progress_percentage = min(100, (spent_today / user.monthly_budget * 100)) if user.monthly_budget > 0 else 0

        return {
            'recent_transactions': recent_tx,
            'spent_today': spent_today,
            'budget_remaining': budget_remaining,
            'progress_percentage': progress_percentage
        }

    @staticmethod
    def get_weekly_summary(user_id):
        """Feature 15: Calculate spending for the current week."""
        today = datetime.utcnow()
        start_of_week = today - timedelta(days=today.weekday())
        
        total = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id, Transaction.date >= start_of_week)\
            .scalar() or 0.0
        return total

    @staticmethod
    def get_chart_data(user_id):
        """Feature 17: Generate data for Chart.js Pie Chart."""
        data = db.session.query(Category.name, func.sum(Transaction.amount))\
            .join(Transaction, Transaction.category_id == Category.id)\
            .filter(Transaction.user_id == user_id)\
            .group_by(Category.name).all()
        
        return {
            "labels": [row[0] for row in data],
            "values": [row[1] for row in data]
        }
    
    @staticmethod
    def get_weekly_chart_data(user_id):
        """Calculate total spending for each day of the current week (Mon-Sun)."""
        today = datetime.utcnow().date()
        start_of_week = today - timedelta(days=today.weekday()) # Gets Monday
        
        # Initialize a dictionary with 0.0 for all 7 days (0=Mon, 6=Sun)
        daily_totals = {i: 0.0 for i in range(7)}
        
        # Get all transactions for this user from this week
        start_datetime = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_datetime
        ).all()
        
        # Add the transaction amounts to the correct day
        for tx in transactions:
            day_index = tx.date.weekday()
            daily_totals[day_index] += tx.amount
            
        # Return a simple list of the 7 totals in order
        return [daily_totals[i] for i in range(7)]
    
    @staticmethod
    def export_transactions_csv(user_id):
        """Feature 19: Export transaction history to CSV."""
        transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Title', 'Category', 'Amount'])
        
        for tx in transactions:
            cat_name = tx.category.name if tx.category else 'Uncategorized'
            writer.writerow([tx.date.strftime('%Y-%m-%d'), tx.title, cat_name, tx.amount])
            
        return output.getvalue()

    @staticmethod
    def search_transactions(user_id, keyword):
        """Feature 20: Filter transactions by keyword."""
        search = f"%{keyword}%"
        return Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.title.ilike(search)
        ).all()

    @staticmethod
    def get_global_stats():
        """Feature 27: Admin global statistics."""
        user_count = User.query.count()
        total_spending = db.session.query(func.sum(Transaction.amount)).scalar() or 0.0
        return {'user_count': user_count, 'total_spending': total_spending}