from dotenv import load_dotenv
import os

load_dotenv()

class Config:

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SECRET_KEY= os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI= os.getenv('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS= os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS') == 'True'
    DEBUG = os.getenv('FLASK_DEBUG')

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")