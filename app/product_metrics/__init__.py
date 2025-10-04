from flask import Blueprint, render_template

bp = Blueprint("product_metrics", __name__, template_folder="templates")

@bp.route("/")
def index():
    # Заглушка-страница: чтобы работало без 500, потом добавим логику
    return render_template(
        "product_metrics/index.html",
        title="Показатели готовой продукции"
    )
