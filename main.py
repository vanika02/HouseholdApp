from flask import Flask, render_template
from app import app
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash
from app.admin.routes import admin_router



app=Flask(__name__)

app.register_blueprint(admin_router)

with app.app_context():
    db.create_all()

    admin = User.query.filter_by(role="admin").first()

    if not admin:
        password_hash = generate_password_hash("admin")
        admin = User(
            username="admin",
            passhash=password_hash,
            role="admin",
            is_blocked=False,
            is_verified=True
        )
        db.session.add(admin)
        db.session.commit()
    

if __name__ == "__main__":
    app.run(debug=True)