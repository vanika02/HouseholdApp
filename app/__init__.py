from flask import Flask
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash
from app.admin.routes import admin_router
from app.config import Config


def create_app():

    app = Flask(__name__)


    return app 

app = create_app()