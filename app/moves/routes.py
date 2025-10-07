from flask import Blueprint, render_template, request, redirect, url_for, flash
from .pending_source import fetch_pending_from_mining

bp = Blueprint("moves", __name__, template_folder="templates")

@bp.get("/")
def index():
    # основная таблица пока пустая — заполняем только «нераспределённую добычу»
    rows = []

    base = request.url_root
    pending_rows, pending_dbg = fetch_pending_from_mining(base)
    pending_total = sum((r.get("qty") or 0) for r in pending_rows)

    return render_template(
        "moves/index.html",
        rows=rows,
        pending_rows=pending_rows,
        pending_total=pending_total,
        pending_dbg=pending_dbg,
    )

# страницы-оболочки уже используются шаблоном
@bp.get("/receipt")
def receipt():
    return render_template("moves/receipt_form.html")

@bp.get("/process")
def process():
    return render_template("moves/process_form.html")

@bp.post("/pending_action")
def pending_action():
    act = (request.form.get("act") or "").strip().lower()  # accept|discard
    # прототип: просто сообщение и назад в журнал
    if act == "accept":
        flash("Выбранные записи приняты на склад (прототип).", "success")
    elif act == "discard":
        flash("Выбранные записи списаны (прототип).", "warning")
    else:
        flash("Действие не выбрано.", "secondary")
    return redirect(url_for("moves.index"))
