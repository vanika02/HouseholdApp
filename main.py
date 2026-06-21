from flask import Flask, render_template
from app.admin.routes import admin_router



app=Flask(__name__)

app.register_blueprint(admin_router)

if __name__ == "__main__":
    app.run(debug=True)