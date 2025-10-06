from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
import csv, os, io, time
from datetime import datetime

bp = Blueprint("fgwh", __name__, template_folder="templates")

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "fgwh.csv")
CSV_FIELDS = ['id', 'name', 'code', 'location', 'is_active', 'note', 'created_at', 'updated_at', 'can_receive_raw', 'can_process', 'can_ship', 'can_transfer']

def _ensure_csv():
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            w.writeheader()

def _read_all():
    _ensure_csv()
    rows = []
    import csv
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # приведение типов и заполнение дефолтов
            row = {k: row.get(k, "") for k in CSV_FIELDS}
            try:
                row["id"] = int(row["id"])
            except Exception:
                row["id"] = 0
            row["is_active"] = (str(row.get("is_active","0")) in ("1","true","True","on"))
            for k in ("can_receive_raw","can_process","can_ship","can_transfer"):
                row[k] = (str(row.get(k,"0")) in ("1","true","True","on"))
            rows.append(row)
    rows.sort(key=lambda r: (0 if r["is_active"] else 1, (r.get("name") or "").lower()))
    return rows

def _write_all(rows):
    import csv, os
    tmp = CSV_PATH + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            r = r.copy()
            r["is_active"] = "1" if r.get("is_active") in (True,"1","true","on") else "0"
            for k in ("can_receive_raw","can_process","can_ship","can_transfer"):
                r[k] = "1" if r.get(k) in (True,"1","true","on") else "0"
            # нормализация пустых полей
            for k in CSV_FIELDS:
                if r.get(k) is None:
                    r[k] = ""
            w.writerow(r)
    import os
    os.replace(tmp, CSV_PATH)

def _next_id(rows):
    return (max([r["id"] for r in rows]) + 1) if rows else 1

@bp.route("/")
def index():
    q = (request.args.get("q") or "").strip().lower()
    rows = _read_all()
    if q:
        rows = [r for r in rows if q in (r["name"] or "").lower() or q in (r["code"] or "").lower() or q in (r["location"] or "").lower()]
    return render_template("fgwh/index.html", rows=rows, q=q)

@bp.route("/create", methods=["GET","POST"])
def create():
    if request.method == "POST":
        rows = _read_all()
        now = datetime.utcnow().isoformat(timespec="seconds")
        rec = {
            "id": _next_id(rows),
            "name": request.form.get("name","").strip(),
            "code": request.form.get("code","").strip(),
            "location": request.form.get("location","").strip(),
            "is_active": "1" if request.form.get("is_active") else "0",
            "note": request.form.get("note","").strip(),
            "can_receive_raw": "1" if request.form.get("can_receive_raw") else "0",
            "can_process": "1" if request.form.get("can_process") else "0",
            "can_ship": "1" if request.form.get("can_ship") else "0",
            "can_transfer": "1" if request.form.get("can_transfer") else "0",
            "created_at": now,
            "updated_at": now,
        }
        if not rec["name"]:
            flash("Укажите название склада", "warning")
            return render_template("fgwh/form.html", rec=rec, mode="create")
        rows.append(rec)
        _write_all(rows)
        flash("Склад создан", "success")
        return redirect(url_for("fgwh.index"))
    return render_template("fgwh/form.html", rec={}, mode="create")

@bp.route("/<int:rid>/edit", methods=["GET","POST"])
def edit(rid: int):
    rows = _read_all()
    rec = next((r for r in rows if r["id"] == rid), None)
    if not rec:
        flash("Склад не найден", "danger")
        return redirect(url_for("fgwh.index"))
    if request.method == "POST":
        rec["name"] = request.form.get("name","").strip()
        rec["code"] = request.form.get("code","").strip()
        rec["location"] = request.form.get("location","").strip()
        rec["is_active"] = "1" if request.form.get("is_active") else "0"
        rec["note"] = request.form.get("note","").strip()
        rec["can_receive_raw"] = "1" if request.form.get("can_receive_raw") else "0"
        rec["can_process"] = "1" if request.form.get("can_process") else "0"
        rec["can_ship"] = "1" if request.form.get("can_ship") else "0"
        rec["can_transfer"] = "1" if request.form.get("can_transfer") else "0"
        rec["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
        if not rec["name"]:
            flash("Укажите название склада", "warning")
            return render_template("fgwh/form.html", rec=rec, mode="edit")
        _write_all(rows)
        flash("Изменения сохранены", "success")
        return redirect(url_for("fgwh.index"))
    return render_template("fgwh/form.html", rec=rec, mode="edit")

@bp.route("/<int:rid>/delete", methods=["POST"])
def delete(rid: int):
    rows = _read_all()
    before = len(rows)
    rows = [r for r in rows if r["id"] != rid]
    if len(rows) == before:
        flash("Склад не найден", "warning")
    else:
        _write_all(rows)
        flash("Склад удалён", "success")
    return redirect(url_for("fgwh.index"))

@bp.route("/export.csv")
def export_csv():
    rows = _read_all()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    w.writeheader()
    for r in rows:
        r = r.copy()
        r["is_active"] = "1" if r["is_active"] else "0"
        w.writerow(r)
    data = io.BytesIO(buf.getvalue().encode("utf-8"))
    fname = f"fgwh_{int(time.time())}.csv"
    return send_file(data, mimetype="text/csv", as_attachment=True, download_name=fname)
