from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound

admin_router = Blueprint("/admin", __name__, url_prefix="/admin")

