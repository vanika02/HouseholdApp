from flask import Blueprint, request, render_template, flash, redirect, url_for, current_app, session
from app.models import User, Service, Professional, Service_request
from app.extensions import db
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import uuid

prof_router = Blueprint("professional", __name__)

# decorator for prof required
def prof_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash("Please login to continue")
            return redirect(url_for('login'))
    return inner



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
            email_exists = Professional.query.filter_by(email_id=email).first()
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
            filename = f"{uuid.uuid4()}_{secure_filename(document.filename)}"
            document_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            document.save(document_path)


            new_professional = Professional(user_id = new_user.id, email_id=email, fullname=fullname, address=address, pin_code = pin, document=filename, service_price=service_price,experience=experience, description=description, service_id=service_id, is_rejected=False, age=age)
            db.session.add(new_professional)
            db.session.commit()
            flash("Registration successfull, Please wait for Admin Approval!")
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash("Registration failed, try again!")
            print(str(e))

    services = Service.query.all()
    return render_template('register_prof.html',services=services)


@prof_router.route('/dashboard/professional')
@prof_required  # Assuming a decorator for ensuring the user is a professional
def professional_dashboard():
    user_id = session.get('user_id')  # Get the logged-in user's ID
    user = User.query.get(user_id)

    if user.role != 'professional':
        flash("Access Denied: Professional only!")
        return redirect(url_for("login"))

    # retrieve search parameters
    search_type = request.args.get("search_type")
    query = request.args.get("query", "").strip()

    # Initialize variables for filtered results
    professional = Professional.query.filter_by(user_id=user_id).first()  # Get only the logged-in professional
    service_requests = Service_request.query.filter_by(professional_id=professional.id).all() if professional else []

    # Apply search filters based on search_type for professional's data
    if search_type == "pin" and query:
        service_requests = Service_request.query.filter(
            Service_request.pin_code.like(f"%{query}%"),
            Service_request.professional_id == professional.id
        ).all()

    elif search_type == "location" and query:
        service_requests = Service_request.query.filter(
            Service_request.location.like(f"%{query}%"),
            Service_request.professional_id == professional.id
        ).all()

    elif search_type == "date" and query:
        service_requests = Service_request.query.filter(
            Service_request.date_of_request.like(f"%{query}%"),
            Service_request.professional_id == professional.id
        ).all()

    elif search_type == "status" and query:
        service_requests = Service_request.query.filter(
            Service_request.status.like(f"%{query}%"),
            Service_request.professional_id == professional.id
        ).all()

    # Return the results to the template
    return render_template("professional_dashboard.html", professional=professional, user=user, service_requests=service_requests, search_type=search_type, query=query)


@prof_router.route("/service_request/<int:id>/complete")
@prof_required
def complete_request(id):
    user_id = session.get('user_id')

    service_request = Service_request.query.filter_by(id=id).first()
    professional = Professional.query.filter_by(user_id=user_id).first()

    if service_request.professional_id != professional.id:
        flash("Unauthorizerd access. Please login to continue.")
        return redirect(url_for("login"))
    
    service_request.status = "completed"
    db.session.commit()
    flash("Service marked as completed. Awating customer confirmation.")
    return redirect(url_for("professional_dashboard"))


@prof_router.route("/summary/prodessional")
@prof_required
def professional_summary():
    user_id = session.get('user_id')
    user_role = session.get('user_role')

    professional = Professional.query.filter_by(user_id=user_id).first()
    service_requests = Service_request.query.filter_by(professional_id=professional.id).all()

    # initialize a dictionary to store counts for each service
    status_counts = {
        "Pending": sum(1 for request in service_requests if request.status == "pending"),
        "Accepted": sum(1 for request in service_requests if request.status == "accepted"),
        "Completed": sum(1 for request in service_requests if request.status == "completed"),
        "Closed": sum(1 for request in service_requests if request.status == "closed"),
    }

    # extract bar chart data
    status_labels = list(status_counts.keys())
    status_values = list(status_counts.values())
    
    # pie chart data
    ratings = [request.rating for request in service_requests if request.rating is not None]
    rating_distribution = {
        '1 Star': sum(1 for r in ratings if 1 <= r < 2),
        '2 Stars': sum(1 for r in ratings if 2 <= r < 3),
        '3 Stars': sum(1 for r in ratings if 3 <= r < 4),
        '4 Stars': sum(1 for r in ratings if 4 <= r < 5),
        '5 Stars': sum(1 for r in ratings if r == 5),
    }
     # extracting date for pie chart
    rating_labels = list(rating_distribution.keys())
    rating_counts = list(rating_distribution.values())

    return render_template("/summary/professional.html", status_labels=status_labels, status_values=status_values, rating_labels=rating_labels, rating_counts=rating_counts)

@prof_router.route("/professional/edit_profile", methods=['GET', 'POST'])
@prof_required
def edit_professional():
    user_id = session.get('user_id')
    user_role = session.get('user_role')

    user = User.query.get(user_id)
    
    if user_role != 'professional':
        flash("Access Denied: Only verfied professionals can edit their profiles.")
    professional = Professional.query.filter_by(user_id=user_id).first()

    if request.method == "POST":
        email = request.form.get("email")
        address = request.form.get("address")
        pin_code = request.form.get("pin_code")
        description = request.form.get("description")
        experience = request.form.get("experience")
        service_price = request.form.get("price")
        


        professional.email_id = email
        professional.address = address
        professional.pin_code = pin_code
        professional.description = description
        professional.experience = experience
        professional.service_price = service_price

        db.session.commit()
        flash("Profile updated successfully")
        return redirect(url_for("professional.professional_dashboard"))

    return render_template("professional_edit.html",  user=user, professional=professional)

@prof_router.route('/professional/profile')
@prof_required
def professional_profile():
    user_id = session.get('user_id')
    user_role = session.get("user_role")

    if not user_id:
        flash("Unauthorized access. Login to continue")
        return redirect(url_for("login"))
    
    if user_role != "professional":
        flash("Unauthorized access. Login to continue")
        return redirect(url_for("login"))

    user = User.query.filter_by(id=user_id).first()
    professional = Professional.query.filter_by(user_id=user_id).first()

    return render_template("professional_profile.html", user=user, professional=professional)

@prof_router.route('/professional/<int:id>/approve_request', methods=['GET', 'POST'])
@prof_required
def accept_request(id):
    user_id = session.get('user_id')
    user_role = session.get("user_role")

    if not user_id:
        flash("Please login to continue!")
        return redirect(url_for("auth.login"))
    if user_role != 'professional':
        flash("Access denied: only verified professiaonl can accpet/reject service requests.")
        return redirect(url_for("auth.login"))
    
    user = User.query.get(user_id)
    professional = Professional.query.filter_by(user_id=user_id).first()
    service_request = Service_request.query.get(id)

    if not service_request:
        flash("service request does not exist!")
        return redirect("url_for('professional.professional_dashboard)")
    
    if service_request.professional_id != professional.id:
        flash("You are unauthorized to approve this request!")
        return redirect(url_for("professional.professional_dashboard"))
    
    if request.method == "POST":
        
        # check if professional has already accepted request for the same day
        same_day_requests = Service_request.query.filter_by(professional_id=professional.id, date_of_request=service_request.date_of_request, status="accepted").all()

        if same_day_requests:
            flash("You have already accepted a service request for this date!")
            return redirect(url_for("professional.professional_dashboard"))

        service_request.status = "accepted"

        # reject all other pending request for the same date
        other_requests = Service_request.query.filter_by(professional_id=professional.id, date_of_request=service_request.date_of_request, status="pending").all()
    
        for requests in other_requests:
            requests.status = "rejected"

        db.session.commit()
        flash("Request has been Accepted successfully and other pending requests for the same date have been rejected!")
        return redirect(url_for("professional.professional_dashboard"))
    
    return render_template("/professional/approve.html", professional=professional, service_request=service_request) 


@prof_router.route("/reject_service_request/<int:service_request_id>", methods=["GET", "POST"])
@prof_required
def reject_request(service_request_id):

    # Retrieve the service request from the database
    service_request = Service_request.query.get(service_request_id)

    if service_request.status == 'accepted':
        # If the status is not 'pending', return an error or show a warning
        flash("This request cannot be rejected as it is already accepted.")
        return redirect(url_for("professional_dashboard"))
    
    if service_request.status == 'closed':
    # If the status is not 'pending', return an error or show a warning
        flash("This request cannot be rejected as it is already closed.")
        return redirect(url_for("professional_dashboard"))

    if service_request.status == 'completed':
        # If the status is not 'pending', return an error or show a warning
        flash("This request cannot be rejected as it is already completed.")
        return redirect(url_for("professional_dashboard"))


    if request.method == "POST":
        # Perform rejection logic
        service_request.status = "rejected"
        db.session.commit()
        flash("Service request has been rejected.", "success")
        return redirect(url_for("professional_dashboard", id=service_request.professional.id))

    return render_template("professional/service_reject.html", service_request=service_request, professional=service_request.professional)
