from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date
from .pending_source import fetch_pending_from_mining, consume

bp = Blueprint("moves", __name__, template_folder="templates")

# Простое хранилище «журнала» в памяти процесса dyno
# Элемент: {date, doc_type, warehouse_name, product_name, qty_in, qty_out, status, note}
MOVES: list[dict] = []

@bp.get("/")
def index():
    rows = list(MOVES)  # показываем накопленные движения
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

@bp.get("/receipt")
def receipt():
    return render_template("moves/receipt_form.html")

@bp.get("/process")
def process():
    return render_template("moves/process_form.html")

@bp.post("/pending_action")
def pending_action():
    act = (request.form.get("act") or "").strip().lower()  # accept|discard
    ids = set(request.form.getlist("ids"))

    if not ids:
        flash("Не выбрано ни одной строки.", "warning")
        return redirect(url_for("moves.index"))

    # Тянем актуальные pending-строки (stateless)
    base = request.url_root
    pending_rows, _dbg = fetch_pending_from_mining(base)
    pick = [r for r in pending_rows if str(r.get("id")) in ids]

    if act == "accept":
        consume(list(ids), "accept")
        added = 0
        for r in pick:
            MOVES.append({
                "date": r.get("date") or date.today().isoformat(),
                "doc_type": "Приём",
                "warehouse_name": "Шахта",
                "product_name": r.get("product_name") or "Добыча",
                "qty_in": float(r.get("qty") or 0),
                "qty_out": "",
                "status": "Готово",
                "note": (r.get("note") or "") + " (из отчёта о добыче)",
            })
            added += 1
        flash(f"Принято на склад: {added} строк(и).", "success")
    elif act == "discard":
        consume(list(ids), "discard")
        flash(f"Списано (прототип): {len(pick)} строк(и).", "warning")
    else:
        flash("Действие не выбрано.", "secondary")

    return redirect(url_for("moves.index"))
