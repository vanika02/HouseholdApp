from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash
from app.extensions import db 

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable= False)
    passhash = db.Column(db.String(256), nullable = False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'customer', 'professional'
    is_blocked = db.Column(db.Boolean, default=False, nullable=False) # dafault=False means active, if True means Blocked
    is_verified = db.Column(db.Boolean, default=False, nullable=False) # False means not verified and True means verified
   
    # Relationships: one-to-one with customer and professional
    customer = db.relationship('Customer', backref = 'user', uselist = False, cascade="all, delete-orphan")
    professional = db.relationship('Professional', backref = 'user', uselist = False, cascade="all, delete-orphan")

class Professional(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), unique = True, nullable = False) # one-to-one
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'), nullable = False) # many prof one service but one prof one service

    # Relationship with service-request
    service_request = db.relationship('Service_request', backref='professional', lazy = True, cascade="all, delete-orphan")

    # professional details
    email_id = db.Column(db.String(100), nullable = True) # default value of nullable is True
    fullname = db.Column(db.String(32), nullable = True)
    address = db.Column(db.String(255), nullable = False)
    pin_code = db.Column(db.String(10), nullable = False)
    service_price = db.Column(db.Float, nullable = False)
    document = db.Column(db.String(255), nullable = False) # path to attached pdf
    experience = db.Column(db.Integer, nullable = False)
    age = db.Column(db.Integer, nullable = False)
    description = db.Column(db.String(100), nullable = False)
    is_rejected = db.Column(db.Boolean, default=False, nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key = True) # primary_key by default is not null
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique = True, nullable = False)
    
    # customer details
    email_id = db.Column(db.String(100))
    fullname = db.Column(db.String(32))
    address = db.Column(db.String(255), nullable = False)
    pin_code = db.Column(db.String(10), nullable = False)
    # Relationship with service request
    service_requests = db.relationship('Service_request', backref='customer', lazy = True, cascade="all, delete-orphan")

class Service(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(64), unique = True, nullable = False)
    base_price = db.Column(db.Float, nullable = False)
    time_required = db.Column(db.String(50), nullable = False)
    description = db.Column(db.Text, nullable = False)
    # Relationships with professional and service request
    professional = db.relationship('Professional', backref='service', lazy = 'joined', cascade="all, delete-orphan") 
    service_requests = db.relationship('Service_request', backref = 'service', lazy = True, cascade="all, delete-orphan")


class Service_request(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable = False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'), nullable = False)
    professional_id = db.Column(db.Integer, db.ForeignKey('professional.id', ondelete='CASCADE'), nullable = False)


    # Request details
    location = db.Column(db.String(256), nullable = False)
    pin_code = db.Column(db.String(10), nullable = False)
    date_of_request = db.Column(db.Date, default=func.now())
    date_of_completion = db.Column(db.Date)
    status = db.Column(db.String(20), default = 'pending') # pending, accepted, completed, closed
    remarks = db.Column(db.String(256), nullable = True)
    rating = db.Column(db.Integer, nullable = True) # ratings out of 5
