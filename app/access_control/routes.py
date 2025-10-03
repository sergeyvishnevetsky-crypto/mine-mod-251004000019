from flask import Blueprint, render_template
access_bp = Blueprint("access", __name__, template_folder="templates")

@access_bp.get("/")
def index():
    return render_template("access.html", title="Пропускной режим")
