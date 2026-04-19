from app import create_app, db

app = create_app()

# We moved this OUTSIDE the 'if __name__' block.
# Now, Gunicorn will trigger this and build your database on Render!
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)