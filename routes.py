from flask import render_template, request, url_for, flash, redirect,session
from app import app
from models import db, User, Customer, Service, Service_request, Professional
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate form inputs
        if not username or not password:
            flash("Please fill out all the fields!")
            return redirect(url_for("login"))

        # Check if user exists
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Username not found. Please check and try again.")
            return redirect(url_for("login"))

        # Verify password
        if not check_password_hash(user.passhash, password):
            flash("Incorrect password. Please try again!")
            return redirect(url_for("login"))

        # Set session details
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['is_verified'] = user.is_verified
        session['is_blocked'] = user.is_blocked

        # Handle roles
        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))

        elif user.role == "professional":
            professional = Professional.query.filter_by(user_id=user.id).first()
            if not professional:
                flash("Professional does not exist! Please register to continue.")
                return redirect(url_for("prof_register"))

            if not user.is_verified:
                flash("You are not yet verified!")
                return redirect(url_for("login"))

            if user.is_blocked:
                flash("You are blocked by the Admin!")
                return redirect(url_for("login"))

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
                return redirect(url_for("login"))
            return redirect(url_for("customer_dashboard"))

        else:
            flash("Invalid role detected. Please contact support.")
            return redirect(url_for("login"))

    return render_template('login.html')


@app.route('/register/professional', methods=['GET', 'POST'])
def prof_register():
    if request.method == 'POST':

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
            return redirect(url_for('prof_register'))
        
        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('prof_register'))
        
        age = int(age)
        if age < 18:
            flash("Only Professionals above 18 allowed!")
            return redirect(url_for('prof_register'))
        
        user = User.query.filter_by(username=username).first()

        if user:
            flash("Username already exists!")
            return redirect(url_for('prof_register'))
        
        # hash the password
        password_hash = generate_password_hash(password)

        new_user = User(username=username, passhash=password_hash, role='professional', is_blocked=False, is_verified=False)
        db.session.add(new_user)
        db.session.commit()

        #  saving document
        filename = secure_filename(document.filename)
        document_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        document.save(filename)


        new_professional = Professional(user_id = new_user.id, email_id=email, fullname=fullname, address=address, pin_code = pin, document=filename, service_price=service_price,experience=experience, description=description, service_id=service_id, is_rejected=False, age=age)
        db.session.add(new_professional)
        db.session.commit()
        return redirect(url_for('login'))

    services = Service.query.all()
    return render_template('register_prof.html',services=services)


@app.route('/register/customer', methods = ['GET', 'POST'])
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
            return redirect(url_for('cust_register'))
        
        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('cust_register'))
        
        user = User.query.filter_by(username=username).first()

        if user:
            flash("Username already exists!")
            return redirect(url_for('cust_register'))

        password_hash = generate_password_hash(password)

        new_user = User(username=username, passhash=password_hash, role='customer', is_blocked=False, is_verified=True)
        db.session.add(new_user)
        db.session.commit()

        new_customer = Customer(user_id = new_user.id, email_id=email, fullname=fullname, address=address, pin_code = pin)
        db.session.add(new_customer)
        db.session.commit()

        return redirect(url_for('login'))
    
    return render_template('register_cust.html')


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
#  ------------------- Admin pages----------------------------------

def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user.role == "admin":
            flash("You are not authorized to access to this page!")
            return redirect(url_for("index"))
        return func(*args, **kwargs)
    return inner

@app.route('/dashboard/admin')
@admin_required
def admin_dashboard():
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if user.role != 'admin':
        flash("Access Denied: Admin only!")
        return redirect(url_for("login"))

    # retrieve search parameters
    search_type = request.args.get("search_type")
    query = request.args.get("query", "").strip()

    # Initialize variables for filtered results
    services = Service.query.all()
    professionals = Professional.query.all()
    service_requests = Service_request.query.all()
    customers = Customer.query.all()

    # Apply search filters based on search_type
    if search_type == "services" and query:
        services = Service.query.filter(Service.name.like(f"%{query}%")).all()

    elif search_type == 'professionals' and query:
        # Check if the query matches a status
        if query.lower() in ['approved', 'rejected', 'not approved']:
            status_mapping = {
                'approved': True,
                'rejected': False,
                'not approved': False
            }
            status = status_mapping.get(query.lower())
            professionals = Professional.query.join(Service).join(User).filter(User.is_verified == status).all()

        else:
            # Default to searching by name if not a status
            professionals = Professional.query.filter(Professional.fullname.like(f"%{query}%")).all()
    elif search_type == 'service_requests' and query:
        service_requests = Service_request.query.filter(Service_request.status.like(f"%{query}%")).all()

    # Return the results to the template
    return render_template("admin_dashboard.html", user=user, services=services, professionals=professionals, customers=customers, service_requests=service_requests, search_type=search_type, query=query)

@app.route('/service/add', methods=['GET', 'POST'])
@admin_required
def add_service():
    if request.method == "POST":
        name = request.form.get("name")
        base_price = request.form.get("price")
        time_required = request.form.get("time")
        description = request.form.get("desc")

        # validate form inputs
        if not name or not base_price or not time_required or not description:
            flash("Please fill out all the fileds!")
            return redirect(url_for("add_service"))
        
        name_lower = name.strip().lower()
        # unique constraint check
        service = Service.query.filter_by(name=name_lower).first()
        if service:
            flash("Service already exists!")
            return redirect(url_for("add_service"))
        
        new_service = Service(name=name_lower, base_price=base_price, time_required=time_required, description=description)
        db.session.add(new_service)
        db.session.commit()
        
        flash("Service added successfully!")
        return redirect(url_for("admin_dashboard"))
    

    return render_template("/services/add.html") 

@app.route('/service/<int:id>')
@admin_required
def show_service(id):
    service = Service.query.get(id)
    if not service:
        flash("service does not exist!")
        return redirect(url_for("admin_dashboard"))

    return render_template("/services/show.html", service=service) 
    
@app.route('/service/<int:id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_service(id):
    service = Service.query.get(id)
    if request.method == 'POST':
    
        if not service:
            flash("Service does not exist!")
            return redirect(url_for("admin_dashboard"))
        
        professionals = Professional.query.filter_by(service_id=service.id).all()
        for professional in professionals:
            if professional.user:  # Ensure the professional has an associated user
                db.session.delete(professional.user)  # Delete the user entry
            db.session.delete(professional)
            
        # Delete the service
        db.session.delete(service)
        db.session.commit()
        
        flash("Service and associated data deleted successfully.")
        return redirect(url_for("admin_dashboard"))
    
    return render_template("/services/delete.html", service=service)

@app.route('/service/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_service(id):
    service = Service.query.get(id)
    if not service:
        flash("Service does not exist!")
        return redirect(url_for("admin_dashboard"))
    
    if request.method == "POST":
        print(request.form)
        price = request.form.get("price")
        time = request.form.get("time")
        desc = request.form.get("desc")

        service.base_price = price
        service.time_required = time
        service.description = desc
        db.session.commit()
        flash("Service Edited successfully!")
        return redirect(url_for('admin_dashboard'))

    return render_template("services/edit.html", service=service)  

@app.route("/summary/admin")
@admin_required
def admin_summary():
    services = Service.query.all()
    service_requests = Service_request.query.all()

    service_requests_count = {service.name: 0 for service in services}

    for request in service_requests:
        for service in services:
            if request.service_id == service.id:
                service_requests_count[service.name] += 1

    # Extracting data for bar chart
    service_names = list(service_requests_count.keys())
    request_counts = list(service_requests_count.values())

    # Pie chart data: Count ratings (1 to 5 stars)
    rating_distribution = {'1 Star': 0, '2 Stars': 0,'3 Stars': 0, '4 Stars': 0,'5 Stars': 0}

    for request in service_requests:
        if request.rating is not None: 
            if request.rating == 1:
                rating_distribution['1 Star'] += 1
            elif request.rating == 2:
                rating_distribution['2 Stars'] += 1
            elif request.rating == 3:
                rating_distribution['3 Stars'] += 1
            elif request.rating == 4:
                rating_distribution['4 Stars'] += 1
            elif request.rating == 5:
                rating_distribution['5 Stars'] += 1

    rating_labels = list(rating_distribution.keys())
    rating_counts = list(rating_distribution.values())

    return render_template("/summary/admin.html", service_names=service_names, request_counts=request_counts,  rating_labels=rating_labels, rating_counts=rating_counts)

@app.route('/customer/<int:id>/block')
@auth_required
def block_customer(id):
    customer = Customer.query.get(id)
    user = User.query.get(customer.user_id)
    
    if not customer:
        flash("Customer does not exist!")
        return redirect(url_for("admin_dashboard"))

    if user.is_blocked:
        flash("Customer is blocked!")
        return redirect(url_for("admin_dashboard"))
    else:
        user.is_blocked = True
        db.session.commit()
        flash("Customer has been successfully Blocked!")
        return redirect(url_for("admin_dashboard"))

@app.route('/customer/<int:id>/unblock')
@auth_required
def unblock_customer(id):
    customer = Customer.query.get(id)
    user = User.query.get(customer.user_id)
    
    if not customer:
        flash("Customer does not exist!")
        return redirect(url_for("admin_dashboard"))

    if not user.is_blocked:
        flash("Customer is not blocked!")
        return redirect(url_for("admin_dashboard"))
    else:
        user.is_blocked = False
        db.session.commit()
        flash("Customer has been successfully unblocked!")
        return redirect(url_for("admin_dashboard"))


# ------------------------------ Customer pages-----------------------------
@app.route('/dashboard/customer')
@auth_required
def customer_dashboard():
    user_id = session.get('user_id')
    role = session.get('user_role')
    user = User.query.filter_by(id=user_id).first()

    # Check user role 
    if role != 'customer':   
        flash("Access Denied: Registered Customers only!")
        return redirect(url_for("login"))
    
    # Check user ID
    if user_id != user.id:
        flash("Access Denied! User not Valid.")
        return redirect(url_for("login"))

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


@app.route("/service_request/<int:id>/close", methods=['GET', 'POST'])
@auth_required
def close_request(id):

    user_id =session.get('user_id')
    service_request = Service_request.query.get(id)
    customer = Customer.query.filter_by(user_id=user_id).first()
    
    if service_request.id != id:
        flash("unauthorized access. Login to continue")
        return redirect(url_for("login"))

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
        return redirect(url_for("customer_dashboard"))
    
    return render_template("/customer/close.html", service_request=service_request)

@app.route("/summary/customer")
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

@app.route("/customer/edit_profile", methods=['GET', 'POST'])
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

        if not email or address or pin_code:
            flash("Please provide all the details!")
            return redirect(url_for("customer_dashboard"))
        
        
        customer.email_id = email
        customer.address = address
        customer.pin_code = pin_code
        db.session.commit()
        flash("Profile updated successfully")
        return redirect(url_for("customer_dashboard"))

    return render_template("customer_edit.html",  user=user, customer=customer)

@app.route('/customer/profile')
@auth_required
def customer_profile():
    user_id = session.get('user_id')
    user_role = session.get("user_role")

    if not user_id:
        flash("Unauthorized access. Login to continue")
        return redirect(url_for("login"))
    
    if user_role != "customer":
        flash("Unauthorized access. Login to continue")
        return redirect(url_for("login"))

    user = User.query.filter_by(id=user_id).first()
    customer = Customer.query.filter_by(user_id=user_id).first()

    return render_template("customer_profile.html", user=user, customer=customer)

@app.route("/customer/<service_name>")
@auth_required
def available_service(service_name):
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    service = Service.query.filter_by(name=service_name).first()
    customer = Customer.query.filter_by(user_id = user.id).first()
    professional = Professional.query.filter_by(service_id=service.id).first()
    return render_template("/customer/show.html", service =service, professional=professional, customer=customer)

@app.route("/book service/<int:professional_id>/<int:service_id>", methods=['GET', 'POST'])
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
        return redirect(url_for("customer_dashboard"))
    
    current_date = date.today().isoformat()
    service = Service.query.filter_by(id=service_id).first()
    professional = Professional.query.filter_by(id=professional_id).first()
    return render_template("/customer/book.html", service=service, professional=professional, current_date=current_date)

@app.route("/service_request/<int:request_id>/edit" , methods=['GET', 'POST'])
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
        return redirect(url_for("customer_dashboard"))

    return render_template("customer/edit.html", service_request=service_request, current_date=service_request.date_of_request)


# -------------------------------- professional pages-----------------------------

@app.route('/dashboard/professional')
@auth_required  # Assuming a decorator for ensuring the user is a professional
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


@app.route("/service_request/<int:id>/complete")
@auth_required
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


@app.route("/summary/prodessional")
@auth_required
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

@app.route("/professional/edit_profile", methods=['GET', 'POST'])
@auth_required
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
        


        professional.email = email
        professional.address = address
        professional.pin_code = pin_code
        professional.description = description
        professional.experience = experience
        professional.service_price = service_price

        db.session.commit()
        flash("Profile updated successfully")
        return redirect(url_for("professional_dashboard"))

    return render_template("professional_edit.html",  user=user, professional=professional)

@app.route('/professional/profile')
@auth_required
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

@app.route('/professional/<int:id>/approve_request', methods=['GET', 'POST'])
@auth_required
def accept_request(id):
    user_id = session.get('user_id')
    user_role = session.get("user_role")

    if not user_id:
        flash("Please login to continue!")
        return redirect(url_for("login"))
    if user_role != 'professional':
        flash("Access denied: only verified professiaonl can accpet/reject service requests.")
        return redirect(url_for("login"))
    
    user = User.query.get(user_id)
    professional = Professional.query.filter_by(user_id=user_id).first()
    service_request = Service_request.query.get(id)

    if not service_request:
        flash("service request does not exist!")
        return redirect("url_for('professional_dashboard)")
    
    if service_request.professional_id != professional.id:
        flash("You are unauthorized to approve this request!")
        return redirect(url_for("professional_dashboard"))
    
    if request.method == "POST":
        
        # check if professional has already accepted request for the same day
        same_day_requests = Service_request.query.filter_by(professional_id=professional.id, date_of_request=service_request.date_of_request, status="accepted").all()

        if same_day_requests:
            flash("You have already accepted a service request for this date!")
            return redirect(url_for("professional_dashboard"))

        service_request.status = "accepted"

        # reject all other pending request for the same date
        other_requests = Service_request.query.filter_by(professional_id=professional.id, date_of_request=service_request.date_of_request, status="pending").all()
    
        for requests in other_requests:
            requests.status = "rejected"

        db.session.commit()
        flash("Request has been Accepted successfully and other pending requests for the same date have been rejected!")
        return redirect(url_for("professional_dashboard"))
    
    return render_template("/professional/approve.html", professional=professional, service_request=service_request) 


@app.route("/reject_service_request/<int:service_request_id>", methods=["GET", "POST"])
@auth_required
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


@app.route('/professional/<int:id>/show')
@auth_required
def show_professional(id):
    professional = Professional.query.get(id)
    return render_template("/professional/show.html", professional=professional) 

@app.route('/professional/<int:id>/approve')
@auth_required
def approve_professional(id):
    professional = Professional.query.get(id)
    user = User.query.get(professional.user_id)
    
    if not professional:
        flash("professional does not exist!")
        return redirect(url_for("admin_dashboard"))

    if user.is_blocked:
        flash("Professional is blocked!")
        return redirect(url_for("admin_dashboard"))
    if user.is_verified:
        flash("Professional is already verfied!")
        return redirect(url_for("admin_dashboard"))
    
    if professional.is_rejected:
        flash("Professional is Rejected!")
        return redirect(url_for("admin_dashboard"))
    else:
        user.is_verified = True
        db.session.commit()
        flash("Professional has been verified successfully!")
        return redirect(url_for("admin_dashboard"))

@app.route('/professional/<int:id>/reject', methods=['GET', 'POST'])
@admin_required
def reject_professional(id):
    professional = Professional.query.get(id)
    if not professional:
        flash("Professional does not exist!")
        return redirect(url_for("admin_dashboard"))

    user = User.query.get(professional.user_id)
    
    if request.method == "POST":
        if not professional:
            flash("Professional does not exist!")
            return redirect(url_for("admin_dashboard"))

        if user.is_blocked:
            flash("Professional is already blocked!")
            return redirect(url_for("admin_dashboard"))

        if user.is_verified:
            flash("This professional is already approved and cannot be rejected.")
            return redirect(url_for("admin_dashboard"))
        
        professional.is_rejected = True
        db.session.commit()
        flash("Professional has been rejected.")
        return redirect(url_for("admin_dashboard"))
    else:
        return render_template("professional/reject.html", professional=professional)

@app.route('/professional/<int:id>/block')
@auth_required
def block_professional(id):
    professional = Professional.query.get(id)
    user = User.query.get(professional.user_id)
    
    if not professional:
        flash("professional does not exist!")
        return redirect(url_for("admin_dashboard"))

    if user.is_blocked:
        flash("Professional is blocked!")
        return redirect(url_for("admin_dashboard"))
    else:
        user.is_blocked = True
        db.session.commit()
        flash("Professional has been Blocked!")
        return redirect(url_for("admin_dashboard"))

@app.route('/professional/<int:id>/unblock')
@auth_required
def unblock_professional(id):
    professional = Professional.query.get(id)
    user = User.query.get(professional.user_id)
    
    if not professional:
        flash("professional does not exist!")
        return redirect(url_for("admin_dashboard"))

    if not user.is_blocked:
        flash("Professional is not blocked!")
        return redirect(url_for("admin_dashboard"))
    else:
        user.is_blocked = False
        db.session.commit()
        flash("Professional has been unblocked!")
        return redirect(url_for("admin_dashboard"))

@app.route('/logout')
@auth_required
def logout():
    session.pop('user_id')
    return redirect(url_for('login'))
