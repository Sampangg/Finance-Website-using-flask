# Save this file as run.py in your main project folder
from app import create_app, db

# This calls the factory function from app/__init__.py
app = create_app()

if __name__ == '__main__':
    # This creates the database file (finance.db) before running the app
    with app.app_context():
        db.create_all()
        
    # Start the Flask development server
    app.run(debug=True)