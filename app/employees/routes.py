from flask import Blueprint, render_template, request, Response, redirect, url_for, flash
employees_bp = Blueprint("employees", __name__, template_folder="templates")
SEED=[
 {"id":1,"fio":"Вишневецкий Сергей","position":"Начальник участка","dept":"Добыча-1","phone":"+380 67 000 00 01","status":"Активен","access":"Кабинет"},
 {"id":2,"fio":"Осташевский Егор","position":"Казначей","dept":"Финансы","phone":"+380 67 000 00 02","status":"Активен","access":"Полный"},
 {"id":3,"fio":"Мишустин Владимир","position":"Директор шахты","dept":"Управление","phone":"+380 67 000 00 03","status":"Ограничен","access":"Чтение"},
]
def _next_id(): return (max((r["id"] for r in SEED), default=0)+1) if SEED else 1
def apply_filters(rows):
    q=request.args.get("q","").lower().strip(); dept=request.args.get("dept","").strip()
    status=request.args.get("status","").strip(); role=request.args.get("role","").strip()
    res=rows
    if q: res=[r for r in res if q in (r["fio"]+" "+r["position"]+" "+r["dept"]+" "+r["phone"]).lower()]
    if dept: res=[r for r in res if r["dept"]==dept]
    if status: res=[r for r in res if r["status"]==status]
    if role: res=[r for r in res if r["access"]==role]
    return res
@employees_bp.get("/")
def index():
    rows=apply_filters(SEED); return render_template("employees.html", title="Сотрудники", rows=rows, total=len(rows), page=1, pages=1)
@employees_bp.get("/<int:emp_id>")
def show(emp_id:int):
    r=next((x for x in SEED if x["id"]==emp_id), None)
    if not r: flash("Сотрудник не найден","err"); return redirect(url_for("employees.index"))
    return render_template("employee_show.html", title=r["fio"], r=r)
@employees_bp.get("/add")
def add(): return render_template("employee_form.html", title="Добавить сотрудника", r=None)
@employees_bp.post("/add")
def add_post():
    f=request.form
    SEED.append({"id":_next_id(),"fio":f.get("fio","").strip(),"position":f.get("position","").strip(),
                 "dept":f.get("dept","").strip(),"phone":f.get("phone","").strip(),
                 "status":(f.get("status","Активен") or "Активен").strip(),
                 "access":(f.get("access","Кабинет") or "Кабинет").strip()})
    flash("Сотрудник добавлен","ok"); return redirect(url_for("employees.index"))
@employees_bp.get("/<int:emp_id>/edit")
def edit(emp_id:int):
    r=next((x for x in SEED if x["id"]==emp_id), None)
    if not r: flash("Сотрудник не найден","err"); return redirect(url_for("employees.index"))
    return render_template("employee_form.html", title=f"Редактирование: {r['fio']}", r=r)
@employees_bp.post("/<int:emp_id>/edit")
def edit_post(emp_id:int):
    r=next((x for x in SEED if x["id"]==emp_id), None)
    if not r: flash("Сотрудник не найден","err"); return redirect(url_for("employees.index"))
    f=request.form
    r.update({"fio":f.get("fio",r["fio"]).strip(),"position":f.get("position",r["position"]).strip(),
              "dept":f.get("dept",r["dept"]).strip(),"phone":f.get("phone",r["phone"]).strip(),
              "status":f.get("status",r["status"]).strip(),"access":f.get("access",r["access"]).strip()})
    flash("Изменения сохранены","ok"); return redirect(url_for("employees.index"))
@employees_bp.get("/<int:emp_id>/archive")
def archive(emp_id:int):
    r=next((x for x in SEED if x["id"]==emp_id), None)
    if not r: flash("Сотрудник не найден","err")
    else: r["status"]="Архив"; flash("Сотрудник перенесен в архив","ok")
    return redirect(url_for("employees.index"))
@employees_bp.get("/<int:emp_id>/restore")
def restore(emp_id:int):
    r=next((x for x in SEED if x["id"]==emp_id), None)
    if not r: flash("Сотрудник не найден","err")
    else: r["status"]="Активен"; flash("Сотрудник восстановлен","ok")
    return redirect(url_for("employees.index"))
@employees_bp.get("/import")
def import_view(): return render_template("employee_import.html", title="Импорт сотрудников (CSV)")
@employees_bp.post("/import")
def import_post():
    f=request.files.get("file")
    if not f: flash("Файл не выбран","err"); return redirect(url_for("employees.import_view"))
    import csv, io
    try:
        data=f.read().decode("utf-8",errors="ignore"); rows=list(csv.DictReader(io.StringIO(data)))
        for row in rows:
            SEED.append({"id":_next_id(),"fio":row.get("fio","").strip(),"position":row.get("position","").strip(),
                         "dept":row.get("dept","").strip(),"phone":row.get("phone","").strip(),
                         "status":(row.get("status","Активен") or "Активен").strip(),
                         "access":(row.get("access","Кабинет") or "Кабинет").strip()})
        flash(f"Импортировано: {len(rows)}","ok")
    except Exception as e:
        flash(f"Ошибка импорта: {e}","err")
    return redirect(url_for("employees.index"))
@employees_bp.get("/export.csv")
def export_csv():
    import csv, io
    buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(["id","fio","position","dept","phone","status","access"])
    for r in SEED: w.writerow([r[k] for k in ["id","fio","position","dept","phone","status","access"]])
    return Response(buf.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=employees.csv"})
