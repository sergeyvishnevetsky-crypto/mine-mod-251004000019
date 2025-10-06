from flask import Blueprint, render_template_string

bp = Blueprint("fgwh", __name__)

@bp.route("/")
def index():
    # TODO: заменить на реальный шаблон, пока заглушка, чтобы /fgwh/ отвечал 200
    return render_template_string("<div class='container py-4'><h3>Склады готовой продукции</h3><p>Раздел в разработке.</p></div>")
