from flask import Blueprint, render_template, request, redirect, flash, url_for, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, Service, Service_request, Professional
from app.extensions import db

auth_router = Blueprint("auth", __name__)

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

@auth_router.route('/')
def index():
    return render_template("index.html")

@auth_router.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate form inputs
        if not username or not password:
            flash("Please fill out all the fields!")
            return redirect(url_for("auth.login"))

        # Check if user exists
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Username not found. Please check and try again.")
            return redirect(url_for("auth.login"))

        # Verify password
        if not check_password_hash(user.passhash, password):
            flash("Incorrect password. Please try again!")
            return redirect(url_for("auth.login"))

        # Set session details
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['is_verified'] = user.is_verified
        session['is_blocked'] = user.is_blocked

        # Handle roles
        if user.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))

        elif user.role == "professional":
            professional = Professional.query.filter_by(user_id=user.id).first()
            if not professional:
                flash("Professional does not exist! Please register to continue.")
                return redirect(url_for("prof_register"))

            if not user.is_verified:
                flash("You are not yet verified!")
                return redirect(url_for("auth.login"))

            if user.is_blocked:
                flash("You are blocked by the Admin!")
                return redirect(url_for("auth.login"))

            if professional.is_rejected:
                flash("Your application was rejected by the admin. Please register again.")
                return redirect(url_for("prof_register"))

            if not professional.service_id:
                flash("The service you were offering has been deleted. Please register for a new service.")
                return redirect(url_for("prof_register"))

            return redirect(url_for("professional_dashboard"))

        elif user.role == "customer":
            if user.is_blocked:
                flash("Your account has been blocked!")
                return redirect(url_for("auth.login"))
            return redirect(url_for("customer_dashboard"))

        else:
            flash("Invalid role detected. Please contact support.")
            return redirect(url_for("auth.login"))

    return render_template('login.html')


@auth_router.route('/logout')
@auth_required
def logout():
    session.pop('user_id')
    return redirect(url_for('auth.login'))
