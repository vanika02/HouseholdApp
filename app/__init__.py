from flask import Flask
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash
from app.admin.routes import admin_router
from app.config import Config