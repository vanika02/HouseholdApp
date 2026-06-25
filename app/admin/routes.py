from flask import Blueprint, render_template, request, abort, flash, session, redirect, url_for
from functools import wraps
from app.models import User, Service_request, Professional, Customer, Service
from app.extensions import db


admin_router = Blueprint("admin", __name__)

# decorater admin routes
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


@admin_router.route('/admin/dashboard')
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

@admin_router.route('/service/add', methods=['GET', 'POST'])
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

@admin_router.route('/service/<int:id>')
@admin_required
def show_service(id):
    service = Service.query.get(id)
    if not service:
        flash("service does not exist!")
        return redirect(url_for("admin.admin_dashboard"))

    return render_template("/services/show.html", service=service) 
    
@admin_router.route('/service/<int:id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_service(id):
    service = Service.query.get(id)
    if request.method == 'POST':
    
        if not service:
            flash("Service does not exist!")
            return redirect(url_for("admin.admin_dashboard"))
        
        professionals = Professional.query.filter_by(service_id=service.id).all()
        for professional in professionals:
            if professional.user:  # Ensure the professional has an associated user
                db.session.delete(professional.user)  # Delete the user entry
            db.session.delete(professional)
            
        # Delete the service
        db.session.delete(service)
        db.session.commit()
        
        flash("Service and associated data deleted successfully.")
        return redirect(url_for("admin.admin_dashboard"))
    
    return render_template("/services/delete.html", service=service)

@admin_router.route('/service/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_service(id):
    service = Service.query.get(id)
    if not service:
        flash("Service does not exist!")
        return redirect(url_for("admin.admin_dashboard"))
    
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
        return redirect(url_for('admin.admin_dashboard'))

    return render_template("services/edit.html", service=service)  

@admin_router.route("/summary/admin")
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
