from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash
from pathlib import Path
import csv
from datetime import datetime

bp = Blueprint("moves", __name__, url_prefix="/moves")

DATA = Path("data")
DATA.mkdir(exist_ok=True)
CSV_PATH = DATA / "moves.csv"
HEADERS = [
    "id","date","type","warehouse","product","qty_in","qty_out",
    "status","comment","batch_id","fraction","loss_pct"
]

def _ensure_csv():
    if not CSV_PATH.exists():
        CSV_PATH.parent.mkdir(exist_ok=True)
        with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)

def _read_all():
    _ensure_csv()
    rows = []
    with CSV_PATH.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

@bp.route("/")
def index():
    rows = _read_all()
    # сортируем по дате/ид убыв.
    rows.sort(key=lambda x: (x.get("date") or "", x.get("id") or ""), reverse=True)
    return render_template("moves/index.html", rows=rows)

@bp.route("/receipt", methods=["GET","POST"])
def receipt():
    if request.method == "POST":
        _ensure_csv()
        with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            nowid = int(datetime.utcnow().timestamp())
            w.writerow([
                nowid,
                request.form.get("date") or datetime.utcnow().date().isoformat(),
                "receipt",
                request.form.get("warehouse") or "",
                request.form.get("product") or "",
                request.form.get("qty") or "",
                "",
                "ok",
                request.form.get("comment") or "",
                "",
                "",
                ""
            ])
        flash("Приём записан", "success")
        return redirect(url_for("moves.index"))
    return render_template("moves/receipt_form.html")

@bp.route("/process", methods=["GET","POST"])
def process():
    # Простая заглушка POST, чтобы не падало (детали можно докрутить позже)
    if request.method == "POST":
        _ensure_csv()
        batch = str(int(datetime.utcnow().timestamp()))
        in_qty = float(request.form.get("in_qty") or 0)
        # одна строка «списание сырья»
        with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            nowid = int(datetime.utcnow().timestamp())
            w.writerow([
                nowid, request.form.get("date") or datetime.utcnow().date().isoformat(),
                "process", request.form.get("warehouse") or "",
                request.form.get("product_in") or "",
                "", in_qty, "ok", request.form.get("comment") or "", batch, "", ""
            ])
        flash("Переработка сохранена (пакет %s)" % batch, "success")
        return redirect(url_for("moves.index"))
    return render_template("moves/process_form.html")
