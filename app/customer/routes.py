from flask import Blueprint, request, render_template, flash, redirect, url_for
from werkzeug.security import generate_password_hash
from app.models import User, Customer
from app.extensions import db

cust_router = Blueprint("customer", __name__)

@cust_router.route('/register/customer', methods = ['GET', 'POST'])
def cust_register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email= request.form.get('email')
        fullname = request.form.get('fullname')
        address = request.form.get('address')
        pin = request.form.get('pin')
        
        if not username or not password or not confirm_password or not address or not pin:
            flash("Please fill out all the fields!")
            return redirect(url_for('customer.cust_register'))
        
        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('customer.cust_register'))
        
        user = User.query.filter_by(username=username).first()

        if user:
            flash("Username already exists!")
            return redirect(url_for('customer.cust_register'))

        password_hash = generate_password_hash(password)

        new_user = User(username=username, passhash=password_hash, role='customer', is_blocked=False, is_verified=True)
        db.session.add(new_user)
        db.session.commit()

        new_customer = Customer(user_id = new_user.id, email_id=email, fullname=fullname, address=address, pin_code = pin)
        db.session.add(new_customer)
        db.session.commit()

        return redirect(url_for('login'))
    
    return render_template('register_cust.html')