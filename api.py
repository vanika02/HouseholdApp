from flask_restful import Resource, Api, reqparse
from flask import request, session, jsonify, make_response, current_app, abort, flash, redirect
from app import app
from functools import wraps
import jwt
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import os
from datetime import date
from models import db, User, Customer, Service, Service_request, Professional
# from flasgger import Swagger



api = Api(app)

class loginApi(Resource):
    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        # validate form inputs
        if not username or not password:
            return make_response(jsonify({"message": "Please fill out all the fields!"}), 400)
        
        # check if username exists
        user = User.query.filter_by(username=username).first()
        if not user:
            return  make_response(jsonify({"message": "username not found. Please check and try again."}), 404)
        
        # verify passsword 
        if not check_password_hash(user.passhash, password):
            return make_response(jsonify({"message": "Incorrect passsword. Please try again"}), 401)
    

        # set session details
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['is_verified'] = user.is_verified
        session['is_blocked'] = user.is_blocked

        # admin login
        if user.role == "admin":
            return make_response(jsonify({"message": "Login successful", "role": "admin"}), 200)
        
        # professional role
        if user.role == "professional":
            professional = Professional.query.filter_by(user_id=user.id).first()
            if not professional:
                return make_response(jsonify({"message": "Professional does not exist! Please register to conitnue."}),  404)
            
            if not user.is_verified:
                return make_response(jsonify({"message": "You are not yet verified!"}), 403)

            if user.is_blocked:
                return make_response(jsonify({"message": "You are blocked by the Admin!"}), 403)

            if professional.is_rejected:
                return make_response(jsonify({"message": "Your application was rejected by the admin. Please register again"}), 403)

            if not professional.service_id:
                return make_response(jsonify({"message": "The service you were offering has been deleted. Please register again."}), 403)

            return make_response(jsonify({"message": "Login successful", "role": "professional"}), 200)

        elif user.role == "customer":
            if user.is_blocked:
                return make_response(jsonify({"message": "Your account has been blocked!"}), 403) 
            return make_response(jsonify({"message": "Login successful", "role": "customer"}), 200)

        else:
            return make_response(jsonify({"message": "Invalid role detected."}), 400)


api.add_resource(loginApi, "/api/login")       

class professionalRegistrationApi(Resource):
    def post(self):

        # extracting data from json body
        data = request.get_json()

        username = data.get("username")
        password = data.get("password")
        confirm_password = data.get("confirm_password")
        service_id = data.get("service_id")
        email = data.get("email")
        fullname = data.get("fullname")
        address = data.get("address")
        experience = data.get("experience")
        age = data.get("age")
        description = data.get("description")
        pin = data.get("pin")
        service_price = data.get("price")

        # file upload
        document_data = data.get("document")

        # validate mandatory fields
        if not all([username, password, confirm_password, service_id, email, fullname, address, experience, age, description, pin, service_price, document_data]):
            return make_response(jsonify({"message": "Please fill out all the fields!"}), 400)

        # password confirmation
        if password != confirm_password:
            return make_response(jsonify({"message": "Passwords do not match!"}), 400)

        # age validation
        if int(age) < 18:
            return make_response(jsonify({"message": "Only professionals above 18 are allowed!"}), 400)

        # check if username exists
        user = User.query.filter_by(username=username).first()
        if user:
            return make_response(jsonify({"message": "Username already exists!"}), 409)

        # password hashing
        password_hash= generate_password_hash(password)

        # create and save the new user
        new_user = User(username=username, passhash=password_hash, role='professional', is_verified=False, is_blocked=False)
        db.session.add(new_user)
        db.session.commit()

        # save the document
        filename = secure_filename(f"{username}_document.pdf")
        document_path = os.path.join('static/files', filename)
        with open(document_path, 'wb') as f:
            f.write(document_data.encode())

        # create and save new professional
        new_professional = Professional(
            user_id=user.id,
            email_id=email,
            fullname=fullname, 
            pin_code=pin,
            document = filename,
            service_price=service_price,
            experience=experience,
            description=description,
            service_id=service_id,
            is_rejected = False,
            age=age
        )
        db.session.add(new_professional)
        db.session.commit()

        return make_response(jsonify({"message": "Professional registered successfully!"}), 201)
    
class customerRegisterApi(Resource):
    def post(self):

        # extracting data from json body
        data = request.get_json()

        username = data.get('username')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        email = data.get('email')
        fullname = data.get('fullname')
        address = data.get('address')
        pin = data.get('pin')

        # validate form inputs
        if not all([username, password, confirm_password, address, pin]):
            return make_response(jsonify({"message": "Please fill out all the fields!"}), 400)
        
        # password confirmation
        if password != confirm_password:
            return make_response(jsonify({"message": "Passwords do not match!"}), 400)
        
        # checking if username exists
        user = User.query.filter_by(username=username).first()
        if user:
            return make_response(jsonify({"message": "Username already exists. Please register again."}), 409)
        
        # hashing password
        password_hash = generate_password_hash(password)

        # creating a new user
        new_user = User(
            username=username,
            passhash=password_hash,
            role='customer',
            is_blocked = False,
            is_verified = True
        )
        db.session.add(new_user)
        db.session.commit()

        # creating new customer
        new_customer = Customer(
            user_id=user.id,
            email_id=email,
            fullname=fullname,
            address=address,
            pin_code=pin
        )
        db.session.add(new_customer)
        db.session.commit()

        return make_response(jsonify({"message": "Registration is successfull."}), 201)
    
# --------------------------------------------------- Admin api's---------------------------------

# helper function for admin authentication
def admin_required_api(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        data = request.get_json()
        user_id = data.get('user_id')
        password = data.get('password')

        user = User.query.get(user_id)

        if not user or not password:
            return make_response(jsonify({"message": "Missing credentials"}), 400)
        

        if not user or user.role != 'admin':
            return {"message": "Access Denied: Admin only!"}, 403
        
        passhash = check_password_hash(user.passhash, password)
        if not passhash:
            return {"message": "Invalid credentials!"}, 403

        return func(*args, **kwargs)
    return wrapper

class adminDashboardApi(Resource):
    @admin_required_api
    def get(self):
        # parse search parameters
        parser = reqparse.RequestParser()
        parser.add_argument("search_type", type=str, required=False, help = "Type of search: services, professionals, or service_requests")
        parser.add_argument("query", type=str, required=False, help="search query")
        args = parser.parse_args()


        search_type = args.get("search_type")
        query = args.get("query", "").strip()

        # initialize response data
        response_data = {
            "services":[],
            "professionals": [],
            "service_requests": []
        }

        # fetch and filter data based on search_type
        if search_type == "services" and query:
            services = Service.query.filter(Service.name.like(f"{query}%")).all()
            response_data["services"] = [{"id": s.id, "name": s.name} for s in services]
            
        elif search_type == "professionals" and query:
            if query.lower() in ['approved', 'rejected', 'not approved']:
                status_mapping = {
                    "approved": True,
                    "rejected": False,
                    "not approved": False,
                }        
                status = status_mapping.get(query.lower())
                professionals = Professional.query.join(Service).join(User).filter(User.is_verified == status).all()
            else:
                professionals = Professional.query.filter(Professional.fullname.like(f"%{query}%")).all()

            response_data["professionals"] = [
                {
                    "id": P.id,
                    "fullname": P.fullname,
                    "is_verified": P.user.is_Verified,
                    "service": P.service.name,
                }
                for P in professionals
            ]                                           
        elif search_type == "service_requests" and query:
            service_requests = Service_request.query.filter(Service_request.status.like(f"%{query}%")).all()
            response_data['service_requests'] = [
                {
                    "id":sr.id,
                    "status":sr.status,
                    "customer":sr.customer.fullname,
                    "professional":sr.professional.fullname
                }
                for sr in service_requests
            ]
        else:
            # default: return all data
            services = Service.query.all()
            response_data["services"] = [{"id": s.id, "name": s.name} for s in services]

            professionals = Professional.query.all()
            response_data["professionals"] = [
                {
                    "id": p.id,
                    "fullname": p.fullname,
                    "is_verified": p.user.is_verified,
                    "service": p.service.name
                }
                for p in professionals
            ]

            service_requests = Service_request.query.all()
            response_data["service_requests"] = [
                {
                    "id": sr.id,
                    "status": sr.status,
                    "customer": sr.customer.fullname,
                    "professional": sr.professional.fullname
                }
                for sr in service_requests
            ]

        return jsonify(response_data)
    
api.add_resource(adminDashboardApi, '/api/dashboard/admin')

class addServiceApi(Resource):
    @admin_required_api
    def get(self):
        services = Service.query.all()
        service_list = [
            {
                "id": service.id,
                "name": service.name,
                "base_price": service.base_price,
                "time_required": service.time_required,
                "description": service.description,
            }
            for service in services
        ]
        return {"services": service_list}, 200
    @admin_required_api
    def post(self):
        # parse incoming JSON data
        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str, required=True, help="service name is required")
        parser.add_argument("base_price", type=float, required=True, help="service price is required")
        parser.add_argument("time_required", type=str, required=True, help=" Time taken for service is required")
        parser.add_argument("description", type=str, required=True, help="service description is required")
        args = parser.parse_args()

        name = args.get("name")
        base_price = args.get("base_price")
        time_required = args.get("time_required")
        description = args.get("description")

        # validate form inputs
        if not name or not base_price or not time_required or not description:
            return  make_response(jsonify({"message": "Please fill out all the fields!"}), 400)
        
        name_lower = name.strip().lower()
        # unique constraint check
        service = Service.query.filter_by(name=name_lower).first()
        if service:
            return make_response(jsonify({"message": "Service already exists!"}), 409)
        
        # adding new service to the database
        try:
            new_service = Service(
                name=name_lower,
                base_price=base_price,
                time_required=time_required,
                description=description
            )
            db.session.add(new_service)
            db.session.commit()
            return make_response(jsonify({"message": "Service added successfully.", "service_id": new_service.id}), 201)
        
        except Exception as E:
            return make_response(jsonify({"message": "Failed to add the service.", "error":str(E)}), 500)

api.add_resource(addServiceApi, "/api/service/add")

class showServiceApi(Resource):
    @admin_required_api
    def get(self, id):
        # get service detail
        service = Service.query.get(id)
        if not service:
            return make_response(jsonify({"message": "Service does not exist!"}), 404)
        
        # service details
        service_data = {
            "Id":service.id,
            "Name":service.name,
            "Price":service.base_price,
            "Time Required":service.time_required,
            "Description":service.description
        }
        return make_response(jsonify({"Service": service_data}), 200)
    
api.add_resource(showServiceApi, "/api/service/<int:id>")


class deleteServiceApi(Resource):
    @admin_required_api
    def get(self, id):
        # get service details
        service = Service.query.get(id)
        if not service:
            return make_response(jsonify({"message": "Service does not exist!"}), 404)
        
        try:
            professionals = Professional.query.filter_by(service_id=service.id).all()
            for professional in professionals:
                if professional.user:
                    db.session.delete(professional.user)
                db.session.delete(professional)

            # delete service
            db.session.delete(service)
            db.session.commit()

            return make_response(jsonify({"message": "Service and associated data deleted successfully."}), 200)
        
        except Exception as E:
            return make_response(jsonify({"message": "An error occurred during deletion.", "error": str(E)}), 500)

api.add_resource(deleteServiceApi, "/api/service/delete/<int:id>")


class editServiceApi(Resource):
    def put(self, id):
        # get service details
        service = Service.query.get(id)
        if not service:
            return make_response(jsonify({"message": "Service does not exist!"}), 404)
        
        parser = reqparse.RequestParser()
        parser.add_argument("base_price", type=float, required=True, help="Base price is required")
        parser.add_argument("time_required", type=str, required=True, help="Time taken for service is required")
        parser.add_argument("description", type=str, required=True, help="Service description is required")
        args = parser.parse_args()

        try:
            service.base_price = args["base_price"]
            service.time_required = args["time_required"]
            service.description = args["description"]

            db.session.commit()
            return make_response(jsonify({"message": "Service edited successfully!"}), 200)
        

        except Exception as E:
            return make_response(jsonify({"message": "An error occurred while editing.", "error": str(E)}), 500)
        
api.add_resource(editServiceApi, "/api/service/edit/<int:id>")

class adminSummaryApi(Resource):
    @admin_required_api
    def get(self):

        # retrieve the data for summary
        try:
            services = Service.query.all()
            service_requests = Service_request.query.all()

            service_request_count = {service.name: 0 for service in services}

            for request in service_requests:
                for service in services:
                    if request.service_id == service.id:
                        service_request_count[service.name] += 1
            
            # extracting data for bar chart
            service_names = list(service_request_count.keys())
            request_counts = list(service_request_count.values())

            # pie chart data 
            rating_distribution = {'1 Star': 0, '2 Star': 0, '3 Star': 0, '4 Star': 0, '5 Star': 0}

            for request in service_requests:
                if request.rating is not None:
                    if request.rating == 1:
                        rating_distribution["1 Star"] += 1
                    elif request.rating == 2:
                        rating_distribution["2 Star"] += 1
                    elif request.rating == 3:
                        rating_distribution["3 Star"] += 1
                    elif request.rating == 4:
                        rating_distribution["4 Star"] += 1
                    elif request.rating == 5:
                        rating_distribution["5 Star"] += 1

            rating_labels = list(rating_distribution.keys())
            rating_counts = list(rating_distribution.values())

            # JSON response
            summary_data = {
                "bar_chart" : {
                    "service_names": service_names,
                    "request_counts": request_counts
                },
                "pie_chart" : {
                    "rating_lables" : rating_labels,
                    "rating_counts" : rating_counts
                }
            }
            return make_response(jsonify({"summary": summary_data}), 200)
        
        except Exception as E:
            return make_response(jsonify({"message": "Failed to retreive summary.", "error": str(E)}), 500)
        
api.add_resource(adminSummaryApi, "/api/summary/admin")


# ----------------------------------------------------------- customer apis---------------------------------------------

# helper function for admin authentication
def auth_required_api(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        data = request.get_json()
        user_id = data.get('user_id')
        password = data.get('password')

        user = User.query.get(user_id)

        if not user or not password:
            return make_response(jsonify({"message": "Missing credentials"}), 400)
        

        if not user:
            return {"message": "Access Denied: Registered users only!"}, 403
        
        passhash = check_password_hash(user.passhash, password)
        if not passhash:
            return {"message": "Invalid credentials!"}, 403

        return func(*args, **kwargs)
    return wrapper


class customerDashboardApi(Resource):
    @auth_required_api
    def get(self, current_user):
        # authentication check
        if current_user.role != "customer":
            return make_response(jsonify({"message": "Access Denied: Registered customers only!", "data": None, "error": "Forbidden"}), 403)

        try:
            # fetch customer record
            customer = Customer.query.filter_by(user_id=current_user.id).first()
            if not customer:
                return make_response(jsonify({"message": "User not found!", "data": None, "error": "Not found"}), 404)
            
            # retreive service requests for the customer
            service_requests = Service_request.query.filter_by(customer_id=customer.id).all()

            # fetch professionals with their ratings
            professionals_with_ratings = {}
            for request in service_requests:
                professional = request.professional
                rating = request.rating

            if professional not in professionals_with_ratings:
                professionals_with_ratings[professional] = []
            if rating is not None:
                professionals_with_ratings[professional].append(rating)
            
            # fetch services and associated professionals
            professionals_with_avg_rating = {
                prof.id: round(sum(ratings) / len(ratings), 1) if ratings else 0
                for prof, ratings in professionals_with_ratings.items()
            }
            # retreive search parameters
            search_type = request.args.get("search_type")
            query = request.args.get("query", "").strip()

            # fetch services and associated professionals
            if search_type == "services" and query:
                # search professional by service description
                professionals = Professional.query.filter(
                    Professional.description.ilike(f"%{query}%"),
                    Professional.user.has(is_verified=True, is_blocked=False),
                    Professional.is_rejected == False
                ).all()
                services_with_professionals = [
                    {"service": prof.service, "professionals": [prof]}
                    for prof in professionals
                ]
            elif search_type == "pin_code" and query:
                # search professional by pin code
                professionals = Professional.query.filter(
                    Professional.pin_code.ilike(f"%{query}%"),
                    Professional.user.has(is_verified=True, is_blocked=False),
                    Professional.is_rejected == False
                ).all()
                services_with_professionals = [
                    {"services": prof.service, "professionals": [prof]}
                    for prof in professionals
                ]
            else:
                # default case: fetch all services with verified, non-rejected professionals
                services_with_professionals = [
                    {
                        "service": service,
                        "professionals": [
                            prof for prof in service.professional if 
                            prof.user.is_verified and 
                            not prof.user.is_blocked and 
                            not prof.is_rejected
                        ]
                    } for service in Service.query.all()
                ]

                # prepare response data
                data = {
                    "user": {
                        "id": current_user.id,
                        "username": current_user.username,
                        "email": current_user.email
                    },
                    "services_With_professionals": services_with_professionals,
                    "service_requests": [
                        {
                            "id": req.id,
                            "service_name": req.service.name,
                            "professional": {
                                "id": req.professional.id,
                                "name": req.professional.user.username
                            },
                            "rating": req.rating,
                            "remarks": req.remarks,
                        } for req in service_requests
                    ],
                    "professionals_with_average_rating": professionals_with_avg_rating
                }
                return {
                    "message": "Customer dashboard data fetched successfully.",
                    "data": data,
                    "error": None
                }, 200
        except Exception as e:
            return {
                "message": "An unexpected error occured",
                "data": None,
                "error": str(e)
            }, 500


api.add_resource(customerDashboardApi, "/api/customer/dashboard")


class closeRequestApi(Resource):
    @auth_required_api
    def post(self, id):
        try:
            # fetch the service requests and validate access
            data = request.get_json()
            user_id = data.get('user_id')
            service_request = Service_request.query.get(id)
            customer = Customer.query.filter_by(user_id=user_id).first()

            if not service_request or service_request.customer_id != customer.id:
                return make_response(jsonify({"message": "Unauthorized access.", "error": "Forbidden"}), 403)
            
            # update service request details 
            data = request.get_json()
            service_request.rating = float(data.get("rating"))
            service_request.remarks = data.get("remarks")
            service_request.date_of_completion = date.fromisoformat(data.get("date_of_completion"))
            service_request.status = "closed"

            db.session.commit()
            return make_response(jsonify({"message": "Service closed successfully.", "error": None}), 200)
        
        
        except Exception as e:
            return {"message": "An unexpected error occurred.", "error": str(e)}, 500

class customerSummaryApi(Resource):
    @auth_required_api
    def get(self):
         # authentication check
        data = request.get_json()
        user_id = data.get('user_id')
        user = User.query.get(user_id)
        if user.role != "customer":
            return make_response(jsonify({"message": "Access Denied: Registered customers only!", "data": None, "error": "Forbidden"}), 403)

        try:
            # fetch customer record
            customer = Customer.query.filter_by(user_id=user.id).first()
            if not customer:
                return make_response(jsonify({"message": "User not found!", "data": None, "error": "Not found"}), 404)

                        # retreive service requests for the customer
            service_requests = Service_request.query.filter_by(customer_id=customer.id).all()
            
            # initialize a dictionay to store counts for each service
            status_counts = {
                "Pending": sum(1 for request in service_requests if request.status == "pending"),
                "Accepted": sum(1 for request in service_requests if request.status == "accepted"),
                "Completed": sum(1 for request in service_requests if request.status == "completed"),
                "Closed": sum(1 for request in service_requests if request.status == "closed")

            }

            # extract bar chart data
            status_lables = list(status_counts.keys())
            status_values = list(status_counts.values())

            # JSON response
            summary_data = {
                "bar_chart" : {
                    "request_status": status_lables,
                    "request_counts": status_counts
                }
            }
            return make_response(jsonify({"summary": summary_data}), 200)
        
        except Exception as E:
            return make_response(jsonify({"message": "Failed to retreive summary.", "error": str(E)}), 500)
        
api.add_resource(customerSummaryApi, "/api/summary/customer")

class editCustomerApi(Resource):
    @auth_required_api
    def put(self):
        data = request.get_json()
        user_id = data.get('user_id')
        # Fetch and return customer details

        if not user_id:
            return make_response(jsonify({"message": "Missing credentials!"}), 400)
        
        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)
        
        if user.role != 'customer':
            return make_response(jsonify({"message": "Registered customers only!"}), 403)

        customer = Customer.query.filter_by(user_id=user_id).first()

        parser = reqparse.RequestParser()
        parser.add_argument("email", type=str, required=True, help="Email Id is required")
        parser.add_argument("address", type=str, required=True, help="customer address is required")
        parser.add_argument("pin_code", type=int, required=True, help="Customer pin code is required")
        args = parser.parse_args()

        try:
            customer.email_id = args["email"]
            customer.address = args["address"]
            customer.pin_code = args["pin_code"]

            db.session.commit()       
            return make_response(jsonify({"message": "Profile edited successfully!"}), 200)

        except Exception as e:
            return make_response(jsonify({"message": str(e)}), 500)
        
api.add_resource(editCustomerApi, "/api/edit/customer")


class  availableServiceApi(Resource):
    @auth_required_api
    def get(self, service_name):
        data = request.get_json()
        user_id =  data.get('user_id')

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        customer = Customer.query.filter_by(user_id=user_id).first()
        if not customer:
            return make_response(jsonify({"message": "Access Denied! Registered customers only."}), 403)
        
        service = Service.query.filter_by(name=service_name).first()
        if not service:
            return make_response(jsonify({"message": "Service dose not exist."}), 403)
        professionals = Professional.query.filter_by(service_id=service.id).all()
        if not professionals:
            return make_response(jsonify({"message": "No professionals found for this service"}), 404)
        
        professional_data = []
        for professional in professionals:
            service_requests = professional.service_request
            ratings = [req.rating for req in service_requests if req.rating is not None]

            avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

            professional_data.append({
                "professional_name": professional.fullname,
                "service_name": service.name,
                "package": professional.description,
                "rating": avg_rating,
                "price": int(professional.service_price) + int(service.base_price)
            })

            return make_response(jsonify({"message": "Service details", "data": professional_data}), 200)
api.add_resource(availableServiceApi, "/api/service/<service_name>")



class  bookServiceApi(Resource):
    @auth_required_api
    def post(self, professional_id, service_id):
        data = request.get_json()
        user_id = data.get('user_id')

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)
        
        customer = Customer.query.filter_by(user_id=user_id).first()
        if not customer:
            return make_response(jsonify({"message": "Access denied! Only registered customers."}), 403)
        
        professional = Professional.query.get(professional_id)
        if not professional:
            return make_response(jsonify({"message": "Professional not found."}), 404)

        service = Service.query.get(service_id)
        if not service:
            return make_response(jsonify({"message": "Service not found."}), 404)

        parser = reqparse.RequestParser()
        parser.add_argument("date_of_req", type=str, required=True, help="Date of Request for service is required!")
        parser.add_argument("location", type=str, required=True, help="Location is required")
        parser.add_argument("pin_code", type=int, required=True, help="pin-code is required")
        args = parser.parse_args()


        try:
            date_of_req = args['date_of_req']
            location = args['location']
            pin_code = args['pin_code']

            #  convert date string into date object
            date_of_request = date.fromisoformat(date_of_req)
            service_request = Service_request(customer_id=customer.id, professional_id=professional.id, service_id=service.id, date_of_request=date_of_request, status="pending", location=location, pin_code=pin_code)
            db.session.add(service_request)
            db.session.commit()       
            return make_response(jsonify({"message": "Service Request sent successfully!"}), 200)

        except Exception as e:
            return make_response(jsonify({"message": str(e)}), 500)
        
api.add_resource(bookServiceApi, "/api/book/<int:professional_id>/<int:service_id>")


class  editServiceRequestApi(Resource):
    @auth_required_api
    def put(self, request_id):

        data = request.get_json()
        user_id = data.get('user_id')

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)
        
        customer = Customer.query.filter_by(user_id=user_id).first()
        if not customer:
            return make_response(jsonify({"message": "Access denied! Only registered customers."}), 403)

        parser = reqparse.RequestParser()
        parser.add_argument("date_of_req", type=str, required=True, help="Date of Request for service is required!")
        parser.add_argument("location", type=str, required=True, help="Location is required")
        parser.add_argument("pin_code", type=int, required=True, help="pin-code is required")
        args = parser.parse_args()

        try:
            date_of_req = args['date_of_req']
            location = args['location']
            pin_code = args['pin_code']

            #  convert date string into date object
            date_of_request = date.fromisoformat(date_of_req)
            service_request = Service_request.query.get(request_id)
            if not service_request:
                return make_response(jsonify({"message": "Invalid Service Id!"}), 403)

            service_request.date_of_request = date_of_request
            service_request.location = location
            service_request.pin_code = pin_code
            db.session.commit()       
            return make_response(jsonify({"message": "Service edited successfully!"}), 200)

        except Exception as e:
            return make_response(jsonify({"message": str(e)}), 500)
        
api.add_resource(editServiceRequestApi, "/api/edit/<int:request_id>")
       

class  customerProfileApi(Resource):
    @auth_required_api
    def get(self):
        data = request.get_json()
        user_id = data.get('user_id')

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)
        
        customer = Customer.query.filter_by(user_id=user_id).first()
        if not customer:
            return make_response(jsonify({"message": "Access denied! Only registered customers."}), 403)
        
        summary_data = {
            "user_id" : user_id,
            "email": customer.email_id,
            "username": user.username,
            "fullname": customer.fullname,
            "pin-code": customer.pin_code,
            "service-requests": len(customer.service_requests)
        }
        return make_response(jsonify({"data": summary_data}), 200)
    
api.add_resource(customerProfileApi, "/api/profile/customer")

#  ------------------------------------------------------- professional apis -------------------------------

class ProfessionalDashboardApi(Resource):
    @auth_required_api
    def get(self):
        # Parse JSON data from request body
        data = request.get_json()
        if not data:
            return make_response(jsonify({"message": "Invalid input! JSON body is required."}), 400)

        user_id = data.get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Missing 'user_id' in request body."}), 400)

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        if user.role != "professional":
            return make_response(jsonify({"message": "Access denied! Registered professionals only."}), 403)

        professional = Professional.query.filter_by(user_id=user.id).first()
        if not professional:
            return make_response(jsonify({"message": "Professional record not found!"}), 404)

        if not user.is_verified:
            return make_response(jsonify({"message": "Professional is not yet by admin."}), 403)

        if professional.is_rejected:
            return make_response(jsonify({"message": "Professional is rejected by admin."}), 403)

        if user.is_blocked:
            return make_response(jsonify({"message": "Professional is blocked by admin."}), 403)

        # Retrieve optional search_type and query
        search_type = data.get("search_type")
        query = data.get("query", "").strip()

        # Base query for service requests
        service_requests_query = Service_request.query.filter_by(professional_id=professional.id)

        # Apply filters based on search_type
        if search_type == "pin" and query:
            service_requests_query = service_requests_query.filter(Service_request.pin_code.ilike(f"%{query}%"))

        elif search_type == "date" and query:
            try:
                query_date = date.fromisoformat(query)
                service_requests_query = service_requests_query.filter(Service_request.date_of_request == query_date)
            except ValueError:
                return make_response(
                    jsonify({"message": "Invalid date format! Please use YYYY-MM-DD."}), 400
                )

        elif search_type in ["pending", "accepted", "completed", "closed"]:
            service_requests_query = service_requests_query.filter(Service_request.status.ilike(f"%{search_type}%"))

        elif search_type == "location" and query:
            service_requests_query = service_requests_query.filter(Service_request.location.ilike(f"%{query}%"))

        # Fetch filtered results
        service_requests = service_requests_query.all()

        # Prepare response data
        response_data = {
            "user": {
                "user_id": user.id,
                "username": user.username,
            },
            "professional": {
                "id": professional.id,
                "fullname": professional.fullname,
                "service_id": professional.service_id,
            },
            "service_requests": [
                {
                    "id": req.id,
                    "customer_id": req.customer_id,
                    "location": req.location,
                    "date_of_request": str(req.date_of_request),
                    "pin_code": req.pin_code,
                    "status": req.status,
                    "remarks": req.remarks,
                    "ratings": req.rating,
                }
                for req in service_requests
            ],
        }

        return make_response(
            jsonify({"message": "Dashboard data retrieved successfully.", "data": response_data}), 200
        )

api.add_resource(ProfessionalDashboardApi, "/api/dashboard/professional")

class completeRequestApi(Resource):
    @auth_required_api
    def put(self, id):
        # Parse JSON data from request body
        data = request.get_json()
        if not data:
            return make_response(jsonify({"message": "Invalid input! JSON body is required."}), 400)

        user_id = data.get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Missing 'user_id' in request body."}), 400)

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        if user.role != "professional":
            return make_response(jsonify({"message": "Access denied! Registered professionals only."}), 403)

        professional = Professional.query.filter_by(user_id=user.id).first()
        if not professional:
            return make_response(jsonify({"message": "Professional record not found!"}), 404)
        
        service_request = Service_request.query.filter_by(id=id).first()
        if not service_request:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        if service_request.professional_id != professional.id:
            return make_response(jsonify({"message": "Access denied! Login to continue."}), 403)
        
        service_request.status = 'completed'
        db.session.commit()
        return make_response(jsonify({"message": "Service is marked as complete."}), 403)

api.add_resource(completeRequestApi, "/api/requestComplete/<int:id>")   

class professionalSummaryApi(Resource):
    @auth_required_api
    def get(self):
        data = request.get_json()
        if not data:
            return make_response(jsonify({"message": "Invalid input! JSON body is required."}), 400)

        user_id = data.get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Missing 'user_id' in request body."}), 400)

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        if user.role != "professional":
            return make_response(jsonify({"message": "Access denied! Registered professionals only."}), 403)

        professional = Professional.query.filter_by(user_id=user.id).first()
        if not professional:
            return make_response(jsonify({"message": "Professional record not found!"}), 404)

        service_requests = Service_request.query.filter_by(professional_id=professional.id).all()
        
        # initialize a dictionary to store
        status_counts = {
            "Pending": sum(1 for request in service_requests if request.status == "pending"),
            "Accepted": sum(1 for request in service_requests if request.status == "accepted"),
            "Completed": sum(1 for request in service_requests if request.status == "completed"),
            "Closed": sum(1 for request in service_requests if request.status == "closed")
        }

        # extract bar chart data
        status_lables = list(status_counts.keys())
        status_values = list(status_counts.values())

        # pie chart data
        ratings = [request.rating for request in service_requests if request.rating is not None]
        rating_distribution = {
            '1 Star': sum(1 for r in ratings if r==1),
            '1 Star': sum(1 for r in ratings if r==2),
            '1 Star': sum(1 for r in ratings if r==3),
            '1 Star': sum(1 for r in ratings if r==4),
            '1 Star': sum(1 for r in ratings if r==5)
        }

        # extracting data for a pie chart
        rating_labels = list(rating_distribution.keys())
        rating_counts = list(rating_distribution.values())

        summary_data = {
            "bar_chart": {
                "Status_lables": status_lables,
                "Status_counts": status_counts
            },
            "pie_chart": {
                "rating_lables": rating_labels,
                "rating_counts": rating_counts
            }
        }
        return make_response(jsonify({"message": summary_data}), 200)

api.add_resource(professionalSummaryApi, "/api/summary/professional")    

class editProfessionalApi(Resource):
    @auth_required_api
    def put(self):
        data = request.get_json()
        if not data:
            return make_response(jsonify({"message": "Invalid input! JSON body is required."}), 400)

        user_id = data.get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Missing 'user_id' in request body."}), 400)

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        if user.role != "professional":
            return make_response(jsonify({"message": "Access denied! Registered professionals only."}), 403)

        professional = Professional.query.filter_by(user_id=user.id).first()
        if not professional:
            return make_response(jsonify({"message": "Professional record not found!"}), 404)
        
        parser = reqparse.RequestParser()
        parser.add_argument("email", type=str, required=True, help="Email is required!")
        parser.add_argument("address", type=str, required=True, help="Email is required!")
        parser.add_argument("pin_code", type=str, required=True, help="Email is required!")
        parser.add_argument("description", type=str, required=True, help="Email is required!")
        parser.add_argument("experience", type=int, required=True, help="Email is required!")
        parser.add_argument("price", type=float, required=True, help="Email is required!")
        args = parser.parse_args()

        email = args.get("email")
        address = args.get("address")
        pin_code = args.get("pin_Code")
        description = args.get("description")
        experience = args.get("experience")
        price = args.get("price")

        professional.email = email
        professional.address = address
        professional.pin_code = pin_code
        professional.description = description
        professional.experience = experience
        professional.service_price = price

        db.session.commit()
        return make_response(jsonify({"message": "Profile edited successfully!"}), 200)
    
api.add_resource(editProfessionalApi, "/api/edit/professional")

class professionalProfileApi(Resource):
    @auth_required_api
    def get(self):
        data = request.get_json()
        user_id = data.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials! User does not exist!"}), 403)
        
        if user.role != 'professional':
            return make_response(jsonify({"message": "Unauthorized access! login to continue."}), 403)
        
        professional = Professional.query.filter_by(user_id=user.id).first()

        prof_data = {
            "username": user.username,
            "fullname": professional.fullname,
            "id": professional.id,
            "email_id": professional.email_id,
            "address": professional.address,
            "service_name": professional.service.name,
            "service_price": professional.service_price,
            "description": professional.description, 
            "experience": professional.experience,
            "document": professional.document,
            "age": professional.age
        }

        return make_response(jsonify({"message": prof_data}), 200)

api.add_resource(professionalProfileApi, "/api/profile/professional")

class acceptRequestApi(Resource):
    @auth_required_api
    def put(self, id):
        # authenticate
        data = request.get_json()
        if not data:
            return make_response(jsonify({"message": "Invalid input! JSON body is required."}), 400)

        user_id = data.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials! User does not exist!"}), 403)

        if user.role != 'professional':
            return make_response(jsonify({"message": "Unauthorized access! Professional does not exist."}), 403)

        professional = Professional.query.filter_by(user_id=user.id).first()
        if not professional:
            return make_response(jsonify({"message": "Invalid credentails! Professional does not exist."}), 403)

        service_request = Service_request.query.filter_by(id=id).first()
        if not service_request:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        if service_request.professional_id != professional.id:
             return make_response(jsonify({"message": "Unauthorized access!"}), 403)
        
        same_day_request = Service_request.query.filter_by(professional_id=professional.id, date_of_request=service_request.date_of_request, status='accepted').all()

        if same_day_request:
            return make_response(jsonify({"message": "Already accepted service request for this date."}), 403)
        
        service_request.status = 'accepted'

        other_request = Service_request.query.filter_by(professional_id=professional.id, date_of_request=service_request.date_of_request, status='pending').all()

        for s_req in other_request:
            s_req.status = 'rejected'

        db.session.commit()
        return make_response(jsonify({"message": "Request accepted successfully!"}), 200)

api.add_resource(acceptRequestApi, "/api/acceptRequest/<int:id>")

class rejectRequestApi(Resource):
    @auth_required_api
    def put(self, id):
        # authenticate
        data = request.get_json()
        user_id = data.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)
        
        service_request = Service_request.query.get(id)
        if not service_request:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        service_request = Service_request.query.get(id)
        if not service_request:
            return make_response(jsonify({"message": "Invalid credentials! Service request does not exist."}), 403)
        
        if service_request.status == 'accepted':
            return make_response(jsonify({"message": "Serivce request already accepted"}), 403)

        if service_request.status == 'closed':
            return make_response(jsonify({"message": "Serivce request already closed"}), 403)
        
        if service_request.status == 'completed':
            return make_response(jsonify({"message": "Serivce request already completed"}), 403)

        service_request.status = "rejected"
        db.session.commit()
        return make_response(jsonify({"message": "Service request rejected successfully."}), 200)

api.add_resource(rejectRequestApi, "/api/rejectRequest/<int:id>")

class approveProfessionalApi(Resource):
    @admin_required_api
    def put(self, id):
        data = request.get_json()
        if not data:
            return make_response(jsonify({"message": "Invalid input! JSON body is required."}), 400)

        user_id = data.get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Missing 'user_id' in request body."}), 400)

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        professional = Professional.query.get(id)
        if not professional:
            return make_response(jsonify({"message": "Professional record not found!"}), 404)
        
        if user.is_blocked:
            return make_response(jsonify({"message": "User is Blocked"}), 403)
        
        if user.is_verified:
            return make_response(jsonify({"message": "User is already verified"}), 403)

        if professional.is_rejected:
            return make_response(jsonify({"message": "Professional is already rejected."}), 403)
        
        user.is_verified = True
        db.session.commit()
        return make_response(jsonify({"message": "Professional verified successfully!"}), 200)

api.add_resource(approveProfessionalApi, "/api/approve/<int:id>")

class rejectProfessionalApi(Resource):
    @admin_required_api
    def put(self, id):
        data = request.get_json()
        if not data:
            return make_response(jsonify({"message": "Invalid input! JSON body is required."}), 400)

        user_id = data.get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Missing 'user_id' in request body."}), 400)

        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        professional = Professional.query.get(id)
        if not professional:
            return make_response(jsonify({"message": "Professional record not found!"}), 404)
        
        if user.is_blocked:
            return make_response(jsonify({"message": "User is Blocked"}), 403)
        
        if user.is_verified:
            return make_response(jsonify({"message": "User is already verified"}), 403)

        if professional.is_rejected:
            return make_response(jsonify({"message": "Professional is already rejected."}), 403)
        
        professional.is_rejected = True
        db.session.commit()
        return make_response(jsonify({"message": "Professional verified successfully!"}), 200)

api.add_resource(rejectProfessionalApi, "/api/reject/<int:id>")

class blockProfessionalApi(Resource):
    @admin_required_api
    def put(self, id):
        professional = Professional.query.get(id)
        if not professional:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        user = User.query.filter_by(id=professional.user_id).first()

        if professional.is_rejected:
            return make_response(jsonify({"message": "Professional is rejected!"}), 403)

        if user.is_blocked:
            return make_response(jsonify({"message": "Professional is already blocked!"}), 403)

        if not user.is_verified:
            return make_response(jsonify({"message": "User is not yet verified!"}), 403)

        user.is_blocked = True
        db.session.commit()
        return make_response(jsonify({"message": "Professional is successfully blocked!"}), 200)

api.add_resource(blockProfessionalApi, "/api/block/professional/<int:id>")

class blockCustomerApi(Resource):
    @admin_required_api
    def put(self, id):
        customer = Customer.query.get(id)
        if not customer:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        user = User.query.filter_by(id=customer.user_id).first()

        if user.is_blocked:
            return make_response(jsonify({"message": "Customer is already blocked!"}), 403)


        user.is_blocked = True
        db.session.commit()
        return make_response(jsonify({"message": "customer is successfully blocked!"}), 200)

api.add_resource(blockCustomerApi, "/api/block/customer/<int:id>")

class unblockProfessionalApi(Resource):
    @admin_required_api
    def put(self, id):
        professional = Professional.query.get(id)
        if not professional:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        user = User.query.filter_by(id=professional.user_id).first()

        if professional.is_rejected:
            return make_response(jsonify({"message": "Professional is rejected!"}), 403)

        if not user.is_blocked:
            return make_response(jsonify({"message": "Professional is already unblocked!"}), 403)

        if not user.is_verified:
            return make_response(jsonify({"message": "User is not yet verified!"}), 403)

        user.is_blocked = False
        db.session.commit()
        return make_response(jsonify({"message": "Professional is successfully unblocked!"}), 200)

api.add_resource(unblockProfessionalApi, "/api/unblock/professional/<int:id>")

class unblockCustomerApi(Resource):
    @admin_required_api
    def put(self, id):
        customer = Customer.query.get(id)
        if not customer:
            return make_response(jsonify({"message": "Invalid credentials!"}), 403)

        user = User.query.filter_by(id=customer.user_id).first()

        if not user.is_blocked:
            return make_response(jsonify({"message": "Customer is already unblocked!"}), 403)


        user.is_blocked = False
        db.session.commit()
        return make_response(jsonify({"message": "customer is successfully unblocked!"}), 200)

api.add_resource(unblockCustomerApi, "/api/unblock/customer/<int:id>")

