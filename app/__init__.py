from flask import Flask
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash
from app.admin.routes import admin_router
from app.config import Config


def create_app():

    app = Flask(__name__)

    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
    app.config['DEBUG'] = Config.DEBUG

    db.init_app(app)

    app.register_blueprint(admin_router)
    app.register_blueprint(auth_router)

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

    return app 

app = create_app()