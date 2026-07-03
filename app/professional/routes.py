from flask import Blueprint, request, render_template, flash, redirect, url_for
from app.models import User, Service, Professional
from app.extensions import db
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os

prof_router = Blueprint("professional", __name__)

@prof_router.route('/register/professional', methods=['GET', 'POST'])
def prof_register():
    if request.method == 'POST':
        try :
            username = request.form.get('username')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            service_id = request.form.get('service')
            email= request.form.get('email')
            fullname = request.form.get('fullname')
            address = request.form.get('address')
            document = request.files.get('document')
            experience = request.form.get('experience')
            age = request.form.get('age')
            description = request.form.get('desc')
            pin = request.form.get('pin')
            service_price = request.form.get('price')
            

            if not username or not password or not address or not pin or not service_price  or not service_id or not document or not experience or not description:
                flash("Please fill out all the fields!")
                return redirect(url_for('professional.prof_register'))
            
            if password != confirm_password:
                flash("Passwords do not match!")
                return redirect(url_for('professional.prof_register'))
            
            # email validation
            email_exists = Professional.query.filter_by(email=email).first()
            if email_exists:
                flash("Email already exists try another!")
                return redirect(url_for('professional.prof_register'))

            age = int(age)
            if age < 18:
                flash("Only Professionals above 18 allowed!")
                return redirect(url_for('professional.prof_register'))
            
            username_exists = User.query.filter_by(username=username).first()

            if username_exists:
                flash("Username already exists!")
                return redirect(url_for('professional.prof_register'))
            
            # hash the password
            password_hash = generate_password_hash(password)

            new_user = User(username=username, passhash=password_hash, role='professional', is_blocked=False, is_verified=False)
            db.session.add(new_user)
            db.session.flush()

            #  saving document
            filename = secure_filename(document.filename)
            document_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            document.save(document_path)


            new_professional = Professional(user_id = new_user.id, email_id=email, fullname=fullname, address=address, pin_code = pin, document=filename, service_price=service_price,experience=experience, description=description, service_id=service_id, is_rejected=False, age=age)
            db.session.add(new_professional)
            db.session.commit()
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            flash("Registration failed, try again!")
            print(str(e))

    services = Service.query.all()
    return render_template('register_prof.html',services=services)