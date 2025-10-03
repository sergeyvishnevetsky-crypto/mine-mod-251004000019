from flask import Blueprint, render_template
cabinet_bp = Blueprint("cabinet", __name__, template_folder="templates")

@cabinet_bp.get("/")
def index():
    return render_template("cabinet.html", title="Кабинет участка")
