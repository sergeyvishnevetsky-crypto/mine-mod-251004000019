from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash
import csv, os
from datetime import datetime

bp = Blueprint("moves", __name__, template_folder="templates")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
WCSV = os.path.join(BASE, "data", "fgwh.csv")
PCSV = os.path.join(BASE, "data", "products.csv")
RCSV = os.path.join(BASE, "data", "recipes.csv")
MCSV = os.path.join(BASE, "data", "moves.csv")

M_FIELDS = ["id","date","doc_type","status","warehouse_id","warehouse_id_to",
            "product_id","qty_in","qty_out","recipe_id","input_qty","output_qty",
            "loss_qty","pair_id","note","author"]

def _ensure_moves():
    os.makedirs(os.path.join(BASE, "data"), exist_ok=True)
    if not os.path.exists(MCSV):
        with open(MCSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=M_FIELDS).writeheader()

def _read_csv(path):
    if not os.path.exists(path): return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _warehouses():
    ws = _read_csv(WCSV)
    for w in ws:
        for k in ("id",): w[k] = int(w.get(k) or 0)
        for k in ("is_active","can_receive_raw","can_process","can_ship","can_transfer"):
            w[k] = (str(w.get(k,"0")) in ("1","true","True","on"))
    return ws

def _products():
    ps = _read_csv(PCSV)
    for p in ps:
        p["id"] = int(p.get("id") or 0)
        p["is_active"] = (str(p.get("is_active","0")) in ("1","true","True","on"))
    return ps

def _recipes():
    rs = _read_csv(RCSV)
    for r in rs:
        r["id"] = int(r.get("id") or 0)
        r["warehouse_id"] = int(r.get("warehouse_id") or 0)
        r["input_product_id"] = int(r.get("input_product_id") or 0)
        r["output_product_id"] = int(r.get("output_product_id") or 0)
        r["yield_pct"] = float(r.get("yield_pct") or 0)
        r["loss_pct"] = float(r.get("loss_pct") or 0)
        r["is_active"] = (str(r.get("is_active","0")) in ("1","true","True","on"))
    return rs

def _moves():
    _ensure_moves()
    ms = _read_csv(MCSV)
    for m in ms:
        m["id"] = int(m.get("id") or 0)
        m["warehouse_id"] = int(m.get("warehouse_id") or 0)
        m["warehouse_id_to"] = int(m.get("warehouse_id_to") or 0) if (m.get("warehouse_id_to") or "").strip() else None
        m["product_id"] = int(m.get("product_id") or 0) if (m.get("product_id") or "").strip() else None
        m["qty_in"] = float(m.get("qty_in") or 0)
        m["qty_out"] = float(m.get("qty_out") or 0)
        m["recipe_id"] = int(m.get("recipe_id") or 0) if (m.get("recipe_id") or "").strip() else None
        m["input_qty"] = float(m.get("input_qty") or 0)
        m["output_qty"] = float(m.get("output_qty") or 0)
        m["loss_qty"] = float(m.get("loss_qty") or 0)
        m["pair_id"] = int(m.get("pair_id") or 0) if (m.get("pair_id") or "").strip() else None
    ms.sort(key=lambda r: r["date"], reverse=True)
    return ms

def _write_moves(rows):
    tmp = MCSV + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=M_FIELDS); w.writeheader()
        for r in rows:
            rr = {k: "" for k in M_FIELDS}
            rr.update(r)
            w.writerow(rr)
    os.replace(tmp, MCSV)

def _next_id(rows): return (max([r["id"] for r in rows]) + 1) if rows else 1

def _stock_until(dt_iso, warehouse_id, product_id):
    """остаток на дату/время по складу+продукту среди status=posted"""
    bal = 0.0
    for m in _moves():
        if m["status"] != "posted": continue
        if m["date"] > dt_iso: continue
        if m["warehouse_id"] == warehouse_id and m["product_id"] == product_id:
            bal += m["qty_in"] - m["qty_out"]
        if m.get("warehouse_id_to") == warehouse_id and m["product_id"] == product_id:
            bal += 0  # приходы на склад-получатель уже учитываются как qty_in у соответствующей строки
    return bal

@bp.route("/")
def index():
    # -- inject pending rows for Шахта --
    try:
        from .pending_store import list_rows, total_qty, debug_counts
        _pending_mining_url = url_for('mining_report.export_csv', _external=True)
        _pending_mining_url = (request.url_root.rstrip('/') + '/mining-report/export.csv')
        _pending_rows = list_rows(warehouse="Шахта", status="pending", mining_url=_pending_mining_url)
        _pending_dbg = debug_counts(mining_url=_pending_mining_url)
        _pending_dbg = debug_counts(mining_url=_pending_mining_url)
        _pending_total = total_qty(_pending_rows)
    except Exception:
        _pending_rows = []
        _pending_total = 0.0
    ws = {w["id"]: w for w in _warehouses()}
    ps = {p["id"]: p for p in _products()}
    rows = []
    for m in _moves()[:500]:
        r = dict(m)
        r["warehouse_name"] = ws.get(m["warehouse_id"],{}).get("name","")
        r["warehouse_to_name"] = ws.get(m.get("warehouse_id_to") or 0,{}).get("name","") if m.get("warehouse_id_to") else ""
        r["product_name"] = ps.get(m.get("product_id") or 0,{}).get("name","") if m.get("product_id") else ""
        rows.append(r)
    return render_template("moves/index.html", rows=rows, pending_rows=_pending_rows, pending_total=_pending_total, pending_dbg=_pending_dbg)

@bp.route("/receipt", methods=["GET","POST"])
def receipt():
    ws = [w for w in _warehouses() if w["is_active"] and w.get("can_receive_raw")]
    ps = [p for p in _products() if p["is_active"]]
    if request.method == "POST":
        date = (request.form.get("date") or "").strip() or datetime.utcnow().isoformat(timespec="seconds")
        wid = int(request.form.get("warehouse_id") or 0)
        pid = int(request.form.get("product_id") or 0)
        qty = float(request.form.get("qty") or 0)
        note = (request.form.get("note") or "").strip()
        if not any(w["id"]==wid for w in ws):
            flash("Склад не умеет принимать добычу", "warning"); return render_template("moves/receipt_form.html", ws=ws, ps=ps)
        if qty <= 0 or not pid:
            flash("Укажите продукт и количество", "warning"); return render_template("moves/receipt_form.html", ws=ws, ps=ps)
        rows = _moves()
        rows.append({
            "id": _next_id(rows), "date": date, "doc_type":"receipt", "status":"posted",
            "warehouse_id": wid, "warehouse_id_to":"", "product_id": pid,
            "qty_in": qty, "qty_out":"", "recipe_id":"", "input_qty":"", "output_qty":"", "loss_qty":"", "pair_id":"",
            "note": note, "author":""
        })
        _write_moves(rows); flash("Приём проведён","success")
        return redirect(url_for("moves.index"))
    return render_template("moves/receipt_form.html", ws=ws, ps=ps)

@bp.route("/process", methods=["GET","POST"])
def process():
    ws_all = [w for w in _warehouses() if w["is_active"] and w.get("can_process")]
    ps = [p for p in _products() if p["is_active"]]
    rs = _recipes()
    if request.method == "POST":
        date = (request.form.get("date") or "").strip() or datetime.utcnow().isoformat(timespec="seconds")
        wid = int(request.form.get("warehouse_id") or 0)
        pid_in = int(request.form.get("input_product_id") or 0)
        qty_in = float(request.form.get("input_qty") or 0)
        recipe_id = int(request.form.get("recipe_id") or 0) if (request.form.get("recipe_id") or "").strip() else None
        note = (request.form.get("note") or "").strip()
        if not any(w["id"]==wid for w in ws_all):
            flash("Склад не умеет перерабатывать", "warning"); return render_template("moves/process_form.html", ws=ws_all, ps=ps, rs=rs)
        # подобрать рецепт, если не указан
        recipe = None
        if recipe_id:
            recipe = next((r for r in rs if r["id"]==recipe_id and r["warehouse_id"]==wid and r["input_product_id"]==pid_in and r["is_active"]), None)
        if not recipe:
            recipe = next((r for r in rs if r["warehouse_id"]==wid and r["input_product_id"]==pid_in and r["is_active"]), None)
        if not recipe:
            flash("Нет активного рецепта для выбранного склада и входа", "warning"); 
            return render_template("moves/process_form.html", ws=ws_all, ps=ps, rs=rs)
        # расчёт выхода/потерь
        qty_out = round(qty_in * recipe["yield_pct"]/100.0, 6)
        loss = round(qty_in * recipe["loss_pct"]/100.0, 6)
        # проверка остатка входа
        bal = _stock_until(date, wid, pid_in)
        if bal < qty_in:
            flash(f"Недостаточно входного продукта на складе (остаток {bal}, нужно {qty_in})", "warning")
            return render_template("moves/process_form.html", ws=ws_all, ps=ps, rs=rs)
        rows = _moves()
        # списание входа
        rows.append({
            "id": _next_id(rows), "date": date, "doc_type":"process", "status":"posted",
            "warehouse_id": wid, "warehouse_id_to":"", "product_id": pid_in,
            "qty_in":"", "qty_out": qty_in, "recipe_id": recipe["id"], "input_qty":qty_in, "output_qty":qty_out, "loss_qty":loss,
            "pair_id":"", "note": note, "author":""
        })
        # приход выхода (на тот же склад)
        rows.append({
            "id": _next_id(rows), "date": date, "doc_type":"process", "status":"posted",
            "warehouse_id": wid, "warehouse_id_to":"", "product_id": recipe["output_product_id"],
            "qty_in": qty_out, "qty_out":"", "recipe_id": recipe["id"], "input_qty":qty_in, "output_qty":qty_out, "loss_qty":loss,
            "pair_id":"", "note": note, "author":""
        })
        _write_moves(rows); flash("Переработка проведена","success")
        return redirect(url_for("moves.index"))
    return render_template("moves/process_form.html", ws=ws_all, ps=ps, rs=rs)


@bp.post("/pending_action")
def pending_action():
    try:
        ids = request.form.getlist("ids")
        op  = request.form.get("op")
        if not ids or op not in ("accept","cancel"):
            return redirect(url_for("moves.index"))
        bulk_update(ids, op)
    except Exception:
        pass
    return redirect(url_for("moves.index"))
