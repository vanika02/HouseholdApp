from flask import Flask
from app.config import Config 
from app.extensions import db 

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)