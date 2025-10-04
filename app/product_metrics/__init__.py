from flask import Blueprint, render_template, jsonify, request

bp = Blueprint("product_metrics", __name__, template_folder="templates")

@bp.route("/")
def index():
    # Проста страница-заглушка — чтобы точно не было 500
    return render_template(
        "product_metrics/index.html",
        title="Показатели готовой продукции"
    )

@bp.route("/params")
def params():
    # Заглушка параметров для модалки / AJAX
    return jsonify({
        "ok": True,
        "title": "Показатели готовой продукции",
        "q": request.args.get("q","")
    })


# Совместимость со старым путём /dict/r/ — отдельный компакт-блюпринт
compat_bp = Blueprint("product_metrics_compat", __name__)

@compat_bp.route("/")
def compat_index():
    # Просто отдаём ту же страницу
    return index()

@compat_bp.route("/params")
def compat_params():
    return params()
