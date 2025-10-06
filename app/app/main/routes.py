from flask import Blueprint, render_template, url_for
main_bp = Blueprint("main", __name__, template_folder="templates")
@main_bp.get("/")
def index():
    tabs=[("Сотрудники",url_for("employees.index")),("Пропускной режим",url_for("access.index")),("Кабинет участка",url_for("cabinet.index"))]
    return render_template("index.html", tabs=tabs, title="Главная")
