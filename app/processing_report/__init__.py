from flask import Blueprint, render_template
proc_bp = Blueprint("processing_report", __name__, template_folder="templates")
@proc_bp.route("/", methods=["GET"])
def index():
    return render_template("processing_report/index.html")
