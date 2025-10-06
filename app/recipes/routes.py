from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash
import csv, os
from datetime import datetime

bp = Blueprint("recipes", __name__, template_folder="templates")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
WCSV = os.path.join(BASE, "data", "fgwh.csv")
PCSV = os.path.join(BASE, "data", "products.csv")
RCSV = os.path.join(BASE, "data", "recipes.csv")
R_FIELDS = ["id","warehouse_id","input_product_id","output_product_id","yield_pct","loss_pct","is_active","note","created_at","updated_at"]

def _read_csv(path):
    if not os.path.exists(path): return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _ensure_rcsv():
    os.makedirs(os.path.join(BASE,"data"), exist_ok=True)
    if not os.path.exists(RCSV):
        with open(RCSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=R_FIELDS); w.writeheader()

def _write_rcsv(rows):
    tmp = RCSV + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=R_FIELDS); w.writeheader()
        for r in rows:
            r = r.copy()
            r["is_active"] = "1" if r.get("is_active") in (True,"1","true","on") else "0"
            for k in R_FIELDS: r.setdefault(k, "")
            w.writerow(r)
    os.replace(tmp, RCSV)

def _next_id(rows): return (max([int(r["id"]) for r in rows])+1) if rows else 1

def _active_warehouses():
    ws = _read_csv(WCSV)
    for w in ws:
        w["id"] = int(w.get("id") or 0)
        w["is_active"] = (w.get("is_active") in ("1","true","True","on"))
    return [w for w in ws if w["is_active"]]

def _active_products():
    ps = _read_csv(PCSV)
    for p in ps:
        p["id"] = int(p.get("id") or 0)
        p["is_active"] = (p.get("is_active") in ("1","true","True","on"))
    return [p for p in ps if p["is_active"]]

@bp.route("/")
def index():
    _ensure_rcsv()
    rows = _read_csv(RCSV)
    ws = {w["id"]: w for w in _active_warehouses()}
    ps = {p["id"]: p for p in _active_products()}
    for r in rows:
        r["id"] = int(r.get("id") or 0)
        r["warehouse_id"] = int(r.get("warehouse_id") or 0)
        r["input_product_id"] = int(r.get("input_product_id") or 0)
        r["output_product_id"] = int(r.get("output_product_id") or 0)
        r["yield_pct"] = float(r.get("yield_pct") or 0)
        r["loss_pct"] = float(r.get("loss_pct") or 0)
        r["is_active"] = (r.get("is_active") in ("1","true","True","on"))
        r["warehouse_name"] = (ws.get(str(r["warehouse_id"])) or ws.get(r["warehouse_id"]) or {}).get("name","")
        r["input_name"] = (ps.get(str(r["input_product_id"])) or ps.get(r["input_product_id"]) or {}).get("name","")
        r["output_name"] = (ps.get(str(r["output_product_id"])) or ps.get(r["output_product_id"]) or {}).get("name","")
    rows.sort(key=lambda r: (not r["is_active"], r["warehouse_name"], r["input_name"]))
    return render_template("recipes/index.html", rows=rows)

@bp.route("/create", methods=["GET","POST"])
def create():
    _ensure_rcsv()
    if request.method=="POST":
        rows = _read_csv(RCSV)
        now = datetime.utcnow().isoformat(timespec="seconds")
        rec = {
            "id": _next_id(rows),
            "warehouse_id": request.form.get("warehouse_id",""),
            "input_product_id": request.form.get("input_product_id",""),
            "output_product_id": request.form.get("output_product_id",""),
            "yield_pct": request.form.get("yield_pct",""),
            "loss_pct": request.form.get("loss_pct",""),
            "is_active": "1" if request.form.get("is_active") else "0",
            "note": request.form.get("note","").strip(),
            "created_at": now, "updated_at": now
        }
        if not rec["warehouse_id"] or not rec["input_product_id"] or not rec["output_product_id"]:
            flash("Склад, вход и выход — обязательны", "warning")
            return render_template("recipes/form.html", rec=rec, warehouses=_active_warehouses(), products=_active_products(), mode="create")
        _write_rcsv(rows + [rec]); flash("Рецепт создан","success")
        return redirect(url_for("recipes.index"))
    return render_template("recipes/form.html", rec={}, warehouses=_active_warehouses(), products=_active_products(), mode="create")

@bp.route("/<int:rid>/edit", methods=["GET","POST"])
def edit(rid:int):
    _ensure_rcsv()
    rows = _read_csv(RCSV)
    rec = next((r for r in rows if int(r.get("id") or 0)==rid), None)
    if not rec:
        flash("Рецепт не найден","danger"); return redirect(url_for("recipes.index"))
    if request.method=="POST":
        rec["warehouse_id"] = request.form.get("warehouse_id","")
        rec["input_product_id"] = request.form.get("input_product_id","")
        rec["output_product_id"] = request.form.get("output_product_id","")
        rec["yield_pct"] = request.form.get("yield_pct","")
        rec["loss_pct"] = request.form.get("loss_pct","")
        rec["is_active"] = "1" if request.form.get("is_active") else "0"
        rec["note"] = request.form.get("note","").strip()
        rec["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
        _write_rcsv(rows); flash("Сохранено","success")
        return redirect(url_for("recipes.index"))
    return render_template("recipes/form.html", rec=rec, warehouses=_active_warehouses(), products=_active_products(), mode="edit")
