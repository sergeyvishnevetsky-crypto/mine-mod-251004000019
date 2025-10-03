from flask import Flask
from .main.routes import main_bp
from .employees.routes import employees_bp
from .access_control.routes import access_bp
from .cabinet.routes import cabinet_bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-me"
    app.register_blueprint(main_bp)
    app.register_blueprint(employees_bp, url_prefix="/employees")
    app.register_blueprint(access_bp, url_prefix="/access")
    app.register_blueprint(cabinet_bp, url_prefix="/cabinet")
    return app
