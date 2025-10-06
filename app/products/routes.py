from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash
import csv, os
from datetime import datetime

bp = Blueprint("products", __name__, template_folder="templates")

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "products.csv")
CSV_FIELDS = ["id","name","code","type","uom","is_active","note","created_at","updated_at"]

def _ensure_csv():
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            w.writeheader()
            # минимальные продукты по умолчанию
            w.writerow({"id":1,"name":"Сырец","code":"RAW","type":"raw","uom":"t","is_active":"1","note":"","created_at":datetime.utcnow().isoformat(timespec="seconds"),"updated_at":datetime.utcnow().isoformat(timespec="seconds")})
            w.writerow({"id":2,"name":"Концентрат","code":"CONC","type":"processed","uom":"t","is_active":"1","note":"","created_at":datetime.utcnow().isoformat(timespec="seconds"),"updated_at":datetime.utcnow().isoformat(timespec="seconds")})

def _read_all():
    _ensure_csv()
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["id"] = int(r["id"])
            r["is_active"] = (r.get("is_active") in ("1","true","True","on"))
            rows.append(r)
    rows.sort(key=lambda r: (0 if r["is_active"] else 1, (r["name"] or "").lower()))
    return rows

def _write_all(rows):
    tmp = CSV_PATH + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            r = r.copy()
            r["is_active"] = "1" if r.get("is_active") in (True,"1","true","on") else "0"
            for k in CSV_FIELDS:
                r.setdefault(k, "")
            w.writerow(r)
    os.replace(tmp, CSV_PATH)

def _next_id(rows): return (max([r["id"] for r in rows])+1) if rows else 1

@bp.route("/")
def index():
    q = (request.args.get("q") or "").strip().lower()
    rows = _read_all()
    if q:
        rows = [r for r in rows if q in (r["name"] or "").lower() or q in (r["code"] or "").lower()]
    return render_template("products/index.html", rows=rows, q=q)

@bp.route("/create", methods=["GET","POST"])
def create():
    if request.method == "POST":
        rows = _read_all()
        now = datetime.utcnow().isoformat(timespec="seconds")
        rec = {
            "id": _next_id(rows),
            "name": request.form.get("name","").strip(),
            "code": request.form.get("code","").strip().upper(),
            "type": request.form.get("type","raw"),
            "uom": request.form.get("uom","t"),
            "is_active": "1" if request.form.get("is_active") else "0",
            "note": request.form.get("note","").strip(),
            "created_at": now, "updated_at": now
        }
        if not rec["name"] or not rec["code"]:
            flash("Название и код — обязательны", "warning")
            return render_template("products/form.html", rec=rec, mode="create")
        rows.append(rec); _write_all(rows); flash("Продукт создан","success")
        return redirect(url_for("products.index"))
    return render_template("products/form.html", rec={}, mode="create")

@bp.route("/<int:rid>/edit", methods=["GET","POST"])
def edit(rid:int):
    rows = _read_all()
    rec = next((r for r in rows if r["id"]==rid), None)
    if not rec:
        flash("Продукт не найден","danger"); return redirect(url_for("products.index"))
    if request.method=="POST":
        rec["name"] = request.form.get("name","").strip()
        rec["code"] = request.form.get("code","").strip().upper()
        rec["type"] = request.form.get("type","raw")
        rec["uom"] = request.form.get("uom","t")
        rec["is_active"] = "1" if request.form.get("is_active") else "0"
        rec["note"] = request.form.get("note","").strip()
        rec["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
        if not rec["name"] or not rec["code"]:
            flash("Название и код — обязательны", "warning")
            return render_template("products/form.html", rec=rec, mode="edit")
        _write_all(rows); flash("Сохранено","success")
        return redirect(url_for("products.index"))
    return render_template("products/form.html", rec=rec, mode="edit")
