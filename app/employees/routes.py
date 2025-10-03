from flask import Blueprint, render_template
employees_bp = Blueprint("employees", __name__, template_folder="templates")

@employees_bp.get("/")
def index():
    return render_template("employees.html", title="Сотрудники")
