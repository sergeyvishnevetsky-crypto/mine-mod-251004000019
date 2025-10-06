from flask import Blueprint, render_template
fgwh_bp = Blueprint("fg_warehouse", __name__, template_folder="templates")
@fgwh_bp.route("/", methods=["GET"])
def index():
    return render_template("fg_warehouse/index.html")
