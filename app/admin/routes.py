from flask import Blueprint, render_template, abort, flash, session, redirect, url_for
from functools import wraps

admin_router = Blueprint("/admin", __name__, url_prefix="/admin")

# decorator for auth function
def auth_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('Please login to continue')
            return redirect(url_for('login'))
    return inner

