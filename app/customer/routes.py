from flask import Blueprint, request, render_template, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash
from app.models import User, Customer, Service, Service_request, Professional
from app.extensions import db
from functools import wraps
from datetime import datetime, date

cust_router = Blueprint("customer", __name__)


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

        return redirect(url_for('auth.login'))
    
    return render_template('register_cust.html')


@cust_router.route('/dashboard/customer')
@auth_required
def customer_dashboard():
    user_id = session.get('user_id')
    role = session.get('user_role')
    user = User.query.filter_by(id=user_id).first()

    # Check user role 
    if role != 'customer':   
        flash("Access Denied: Registered Customers only!")
        return redirect(url_for("auth.login"))
    
    # Check user ID
    if user_id != user.id:
        flash("Access Denied! User not Valid.")
        return redirect(url_for("auth.login"))

    # Retrieve search parameters
    search_type = request.args.get("search_type")
    query = request.args.get("query", "").strip()

    # Initially retrieve all services and associated professionals
    services_with_professionals = [
        {
            'service': service,
            'professionals': [professional for professional in service.professional if 
                               professional.user.is_verified and
                               not professional.is_rejected and 
                               not professional.user.is_blocked]
        }
        for service in Service.query.all()
    ]
    customer = Customer.query.filter_by(user_id=user.id).first()

    if not customer:
        flash("Customer not found!")
        return redirect(url_for("auth.login"))

    service_requests = Service_request.query.filter_by(customer_id=customer.id).all()

    professionals_with_ratings = {}
    for service_request in service_requests:
        professional = service_request.professional
        rating = service_request.rating
        if professional not in professionals_with_ratings:
            professionals_with_ratings[professional] = []
        professionals_with_ratings[professional].append(rating)

# Calculate the average rating for each professional
    professionals_with_average_rating = {}
    for professional, ratings in professionals_with_ratings.items():
    # Filter out None values from ratings
        valid_ratings = [rating for rating in ratings if rating is not None]
        avg_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else 0

        # Format the rating to show only one decimal point
        avg_rating = round(avg_rating, 1)
        professionals_with_average_rating[professional] = avg_rating

    # Apply search filters based on search type
    if search_type == "services" and query:
        # Search professionals by their service descriptions
        professionals = Professional.query.filter(Professional.description.like(f"%{query}%")).all()

        # Filter verified, non-rejected, and non-blocked professionals
        professionals = [
            professional for professional in professionals if 
            professional.user.is_verified and 
            not professional.is_rejected and 
            not professional.user.is_blocked
        ]
        
        # Retrieve services for those filtered professionals
        services_with_professionals = [{'service': professional.service, 'professionals': [professional]} for professional in professionals]
    
    elif search_type == "pin_code" and query:
        # Search professionals by pin code
        professionals = Professional.query.filter(Professional.pin_code.like(f"%{query}%")).all()

        # Filter verified, non-rejected, and non-blocked professionals
        professionals = [
            professional for professional in professionals if 
            professional.user.is_verified and 
            not professional.is_rejected and 
            not professional.user.is_blocked
        ]
        
        # Retrieve services for those filtered professionals
        services_with_professionals = [{'service': professional.service, 'professionals': [professional]} for professional in professionals]

    return render_template(
        "customer_dashboard.html",
        user=user,
        services_with_professionals=services_with_professionals,
        customer=customer,
        professionals_with_average_rating=professionals_with_average_rating, 
        service_requests=service_requests,
        search_type=search_type,
        query=query
    )


@cust_router.route("/service_request/<int:id>/close", methods=['GET', 'POST'])
@auth_required
def close_request(id):

    user_id =session.get('user_id')
    service_request = Service_request.query.get(id)
    customer = Customer.query.filter_by(user_id=user_id).first()
    
    if service_request.id != id:
        flash("unauthorized access. Login to continue")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        rating = float(request.form.get("rating"))
        remarks = request.form.get("remarks")
        date_of_completion_str = request.form.get("date_of_completion")

        date_of_completion = date.fromisoformat(date_of_completion_str)

        service_request.rating = rating
        service_request.remarks = remarks
        service_request.date_of_completion = date_of_completion
        service_request.status = "closed"
        db.session.commit()
        flash("Thank you for your feedback. Service is closed successfully!")
        return redirect(url_for("customer.customer_dashboard"))
    
    return render_template("/customer/close.html", service_request=service_request)

@cust_router.route("/summary/customer")
@auth_required
def customer_summary():
    user_id = session.get('user_id')
    user_role = session.get('role')

    customer = Customer.query.filter_by(user_id=user_id).first()
    service_requests = Service_request.query.filter_by(customer_id=customer.id).all()

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


    return render_template("/summary/customer.html", status_labels=status_labels, status_values=status_values)

@cust_router.route("/customer/edit_profile", methods=['GET', 'POST'])
@auth_required
def edit_customer():
    user_id = session.get('user_id')
    user_role = session.get('user_role')

    user = User.query.get(user_id)

    if user_role != 'customer':
        flash("Access Denied: Only registered users can edit their profiles.")
    customer = Customer.query.filter_by(user_id=user_id).first()

    if request.method == "POST":
        email = request.form.get("email")
        address = request.form.get("address")
        pin_code = request.form.get("pin_code")
        # print(email)
        # print(address)
        # print(pin_code)

        if not email or not address or not pin_code:
            flash("Please provide all the details!")
            return redirect(url_for("customer.customer_dashboard"))
        
        
        customer.email_id = email
        customer.address = address
        customer.pin_code = pin_code
        db.session.commit()
        flash("Profile updated successfully")
        return redirect(url_for("customer.customer_dashboard"))

    return render_template("customer_edit.html",  user=user, customer=customer)

@cust_router.route('/customer/profile')
@auth_required
def customer_profile():
    user_id = session.get('user_id')
    user_role = session.get("user_role")

    if not user_id:
        flash("Unauthorized access. Login to continue")
        return redirect(url_for("auth.login"))
    
    if user_role != "customer":
        flash("Unauthorized access. Login to continue")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(id=user_id).first()
    customer = Customer.query.filter_by(user_id=user_id).first()

    return render_template("customer_profile.html", user=user, customer=customer)

@cust_router.route("/customer/<service_name>")
@auth_required
def available_service(service_name):
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    service = Service.query.filter_by(name=service_name).first()
    customer = Customer.query.filter_by(user_id = user.id).first()
    professional = Professional.query.filter_by(service_id=service.id).first()
    return render_template("/customer/show.html", service =service, professional=professional, customer=customer)

@cust_router.route("/book service/<int:professional_id>/<int:service_id>", methods=['GET', 'POST'])
@auth_required
def book_service(professional_id,service_id):
    if request.method == "POST":
        user_id = session.get('user_id')
        user = User.query.filter_by(id=user_id).first()
        customer = Customer.query.filter_by(user_id = user.id).first() 

        customer_id = customer.id
        date_of_request_str = request.form.get("date_of_request")
        location = request.form.get("location")
        pin_code = request.form.get("pin")


        # Convert the date string to a date object
        date_of_request = date.fromisoformat(date_of_request_str)
        # creating a new service request
        service_request = Service_request(customer_id=customer_id, professional_id=professional_id, service_id=service_id, date_of_request=date_of_request, status="pending", location=location, pin_code=pin_code) # default status
        db.session.add(service_request)
        db.session.commit()
        flash("Request send successfully!")
        return redirect(url_for("customer.customer_dashboard"))
    
    current_date = date.today().isoformat()
    service = Service.query.filter_by(id=service_id).first()
    professional = Professional.query.filter_by(id=professional_id).first()
    return render_template("/customer/book.html", service=service, professional=professional, current_date=current_date)

@cust_router.route("/service_request/<int:request_id>/edit" , methods=['GET', 'POST'])
@auth_required
def edit_service_request(request_id):
    service_request = Service_request.query.get(request_id)
    if request.method == "POST":
        date_of_request_str = request.form.get("date_of_request")
        location = request.form.get("location")
        pin_code = request.form.get("pin")

        service_request.date_of_request = date.fromisoformat(date_of_request_str)
        service_request.location = location
        service_request.pin_code = pin_code
        db.session.commit()
        flash("Service request date updated successfully!")
        return redirect(url_for("customer.customer_dashboard"))

    return render_template("customer/edit.html", service_request=service_request, current_date=service_request.date_of_request)
