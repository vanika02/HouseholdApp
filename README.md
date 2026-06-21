# Household Services Application

## Description

The Household Services Application is a multi-user platform designed to manage household services efficiently. It includes three user roles: Admin, Professional, and Customer. The admin oversees the system, handling professional approvals, managing users, and maintaining service-related data. Professionals sign up to offer one service, and their applications require admin approval. Customers register to book available services. The system also features visual analytics, like bar and pie charts, to display ratings and service requests, providing actionable insights for stakeholders.

## Folder Structure 
```
.
├── README.md
├── api.py
├── app
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── routes.py
│   └── templates
│       ├── admin_dashboard.html
│       ├── customer
│       ├── customer_dashboard.html
│       ├── customer_edit.html
│       ├── customer_profile.html
│       ├── index.html
│       ├── layout.html
│       ├── login.html
│       ├── messages.html
│       ├── navbar.html
│       ├── professional
│       ├── professional_dashboard.html
│       ├── professional_edit.html
│       ├── professional_profile.html
│       ├── register_cust.html
│       ├── register_prof.html
│       ├── search
│       ├── search_results.html
│       ├── searchbar.html
│       ├── services
│       └── summary
├── app.py
├── instance
│   └── db.sqlite3
├── requirements.txt
└── static
    ├── css
    │   └── style.css
    └── images
        ├── HouseHold.png
        ├── lake-view.svg
        └── window.svg

12 directories, 29 files
```


## Technologies Used

Flask: Backend framework for building the web application.
Flask-SQLAlchemy: ORM (Object-Relational Mapping) tool for database interactions.
SQLite: Database management system for storing application data.
HTML/CSS/JavaScript: Frontend technologies for user interface design and interactivity.
Chart.js: JavaScript library for creating interactive data visualizations (e.g., bar and pie charts).
Flask-Login: Extension for managing user sessions and authentication.
Python-dotenv: For managing environment variables securely.
Jinja2: Template engine for rendering HTML pages dynamically.
Werkzeug: Utility library for WSGI applications.
Supporting Libraries: Blinker, SQLAlchemy, and others to enhance functionality and performance.


## Architecture

The application is modularly designed to ensure clear separation of concerns and ease of maintenance. The main application code resides in app.py, and additional components are organized as follows:

routes.py: Defines all the application routes and maps them to corresponding functionalities for customers, professionals, and admins.
models.py: Contains database models and relationships for the application's entities like users, services, and service requests.
config.py: Manages the application's configuration settings (e.g., database URI, secret keys, and debug flags).
templates/: Contains all the HTML files used to render dynamic web pages for different functionalities and user roles.
static/: Stores static assets like CSS, and media files.
instance/: Holds application-specific data like the SQLite database file (db.sqlite3).
requirements.txt: Lists all dependencies required to run the application.

## Features

### User Management

Registration & Authentication: Allows customers and professionals to register, with a separate signup process for each type of user. Professionals must be approved by the admin before they can log in.
Role-Based Access Control: Three distinct roles — Admin, Customer, and Professional — each with different permissions. Admins manage all aspects of the platform, professionals can offer services, and customers can book services.
Profile Management: Both customers and professionals can manage their profiles to update personal information such as email, addresses, experience, description.
Service Management
Service Catalog & Categorization: Services are categorized under various types, and professionals can list their offerings in specific categories.
Service Listings: Customers can browse the catalog of services and request bookings for the services they need.
Service Offering by Professionals: Each professional can offer only one service but can update or modify it as required.
Service Requests & Status
Request Management: Customers can create service requests, which professionals can accept or reject based on availability.
Automatic Static Updates: The system automatically updates status after service completion, with an option for customers to close and rate the service.
Service Status Tracking: Customers and professionals can track service request progress, including status updates, through the application.
Admin Dashboard
Professional Approval Workflow: Admins review and approve professional registrations before they can log in and offer services.
Transaction & Request Monitoring: Admins can monitor all service requests and their status across the platform.
Notifications: Admins are notified about rejected professionals, ensuring smooth communication with users.
Feedback & Ratings
Service Feedback: Customers can provide feedback on the service received, allowing professionals to improve their offerings.
Ratings System:  Professionals are rated out of 5 stars, and the feedback system helps assess service quality and customer satisfaction.

## DB SCHEMA
1. User
Columns:
id (PK): Unique ID.
username (Unique), email (Unique), role (admin, customer, professional).
status (active, blocked), is_verified.	

2. Service
Columns:
id (PK): Unique ID.
name, description, price.
category_id (FK), professional_id (FK, one-to-one).

3. Category
Columns:
id (PK): Unique ID.
name: Category name.

4. Transaction
Columns:
id (PK): Unique ID.
customer_id (FK), service_request_id (FK).
amount, status, timestamp.

5. Feedback
Columns:
id (PK): Unique ID.
service_request_id (FK), rating (1-5), remarks, timestamp.	

6. Service Requests
Columns:
id (PK): Unique ID.
customer_id (FK), professional_id (FK), service_id (FK).
status (pending, accepted, completed), timestamp.

## Key Relationships

User ↔ Service Requests:
One customer/professional ↔ multiple requests.
Service ↔ Category:
Many services ↔ one category.
Service Requests ↔ Feedback:
One request ↔ one feedback.
Service Requests ↔ Transaction:
One request ↔ one transaction.	

Real-Time Chat System:

Add a Messages table:
Columns: id, service_request_id, sender_id, receiver_id, message, timestamp.
Advanced Search and Filtering:

Payment Gateway Integration:
Extend the Transaction table to include:
payment_gateway: Name of the payment gateway used.
transaction_reference: External transaction ID.
Professional Dashboard Enhancements:


