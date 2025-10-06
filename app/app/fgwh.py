# -*- coding: utf-8 -*-
import os, io, csv
from typing import Optional
from flask import Blueprint, request, render_template, redirect, url_for, flash, send_file

# Простая работа с БД через SQLAlchemy Core (Postgres/SQLite)
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, text, select, insert, update, delete
from sqlalchemy.exc import IntegrityError

def _db_url(u: str) -> str:
    # Heroku иногда даёт postgres:// — приводим к postgresql+psycopg2://
    if u.startswith("postgres://"):
        return u.replace("postgres://", "postgresql+psycopg2://", 1)
    return u

DATABASE_URL = _db_url(os.getenv("DATABASE_URL", "sqlite:///local.db"))
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
meta = MetaData()

FGW = Table(
    "fg_warehouses", meta,
    Column("id", Integer, primary_key=True),
    Column("code", String(64), unique=True, nullable=False),
    Column("name", String(255), nullable=False),
    Column("address", String(255)),
    Column("responsible", String(255)),
    Column("capacity_tons", Float),
    Column("active", Boolean, server_default=text("1"), nullable=False),
    Column("note", String(500)),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False),
    Column("updated_at", DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False),
)

# создаём таблицу при первом импорте
with engine.begin() as conn:
    meta.create_all(conn)

bp = Blueprint("fgwh", __name__, template_folder="../templates")

def _row_from_form():
    def _f(name, default=""):
        return (request.form.get(name) or default).strip()
    cap = _f("capacity_tons")
    try:
        cap = float(cap.replace(",", ".")) if cap else None
    except ValueError:
        cap = None
    return {
        "code": _f("code"),
        "name": _f("name"),
        "address": _f("address"),
        "responsible": _f("responsible"),
        "capacity_tons": cap,
        "active": (request.form.get("active") == "on"),
        "note": _f("note"),
    }

@bp.route("/fgwh/")
def list_warehouses():
    q = select(FGW).order_by(FGW.c.code)
    with engine.begin() as c:
        rows = list(c.execute(q).mappings())
    return render_template("fgwh/list.html", rows=rows, TITLE="Склады готовой продукции")

@bp.route("/fgwh/create", methods=["POST"])
def create_warehouse():
    data = _row_from_form()
    if not data["code"] or not data["name"]:
        flash("Код и Наименование обязательны", "warning")
        return redirect(url_for("fgwh.list_warehouses"))
    try:
        with engine.begin() as c:
            c.execute(insert(FGW).values(**data))
        flash("Склад добавлен", "success")
    except IntegrityError:
        flash("Код уже существует", "danger")
    return redirect(url_for("fgwh.list_warehouses"))

@bp.route("/fgwh/update/<int:pk>", methods=["POST"])
def update_warehouse(pk):
    data = _row_from_form()
    with engine.begin() as c:
        c.execute(update(FGW).where(FGW.c.id == pk).values(**data))
    flash("Изменения сохранены", "success")
    return redirect(url_for("fgwh.list_warehouses"))

@bp.route("/fgwh/delete/<int:pk>", methods=["POST"])
def delete_warehouse(pk):
    with engine.begin() as c:
        c.execute(delete(FGW).where(FGW.c.id == pk))
    flash("Склад удалён", "info")
    return redirect(url_for("fgwh.list_warehouses"))

@bp.route("/fgwh/export.csv")
def export_csv():
    q = select(FGW).order_by(FGW.c.code)
    with engine.begin() as c:
        rows = list(c.execute(q))
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["Код","Наименование","Адрес","Ответственный","Вместимость_т","Активен","Примечание"])
    for r in rows:
        w.writerow([r.code, r.name, r.address or "", r.responsible or "", r.capacity_tons or "", int(r.active), r.note or ""])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode("utf-8-sig")),
                     mimetype="text/csv",
                     as_attachment=True,
                     download_name="fg_warehouses.csv")

@bp.route("/fgwh/import", methods=["POST"])
def import_csv():
    f = request.files.get("file")
    if not f:
        flash("Файл не выбран", "warning")
        return redirect(url_for("fgwh.list_warehouses"))
    content = f.read().decode("utf-8-sig").splitlines()
    rdr = csv.DictReader(content)
    cnt=0
    with engine.begin() as c:
        for row in rdr:
            data = {
                "code": (row.get("Код") or row.get("code") or "").strip(),
                "name": (row.get("Наименование") or row.get("name") or "").strip(),
                "address": (row.get("Адрес") or row.get("address") or "").strip(),
                "responsible": (row.get("Ответственный") or row.get("responsible") or "").strip(),
                "capacity_tons": float((row.get("Вместимость_т") or row.get("capacity_tons") or "0").replace(",", ".") or 0) if (row.get("Вместимость_т") or row.get("capacity_tons")) else None,
                "active": str(row.get("Активен") or row.get("active") or "1").strip() in ("1","True","true","on","yes","да","Да"),
                "note": (row.get("Примечание") or row.get("note") or "").strip(),
            }
            if not data["code"] or not data["name"]:
                continue
            try:
                c.execute(insert(FGW).values(**data))
            except IntegrityError:
                c.execute(update(FGW).where(FGW.c.code==data["code"]).values(**data))
            cnt += 1
    flash(f"Импортировано/обновлено: {cnt}", "success")
    return redirect(url_for("fgwh.list_warehouses"))
