from flask import Blueprint, render_template, request, Response, redirect, url_for, flash

employees_bp = Blueprint("employees", __name__, template_folder="templates")

# Демо-данные c раздельным ФИО и новыми полями
SEED=[
    {"id":1,"last_name":"Вишневецкий","first_name":"Сергей","middle_name":"","personnel_no":1001,"inn":"1234567890","position":"Начальник участка","dept":"Добыча-1","phone":"+380 67 000 00 01","status":"Активен","access":"Кабинет"},
    {"id":2,"last_name":"Осташевский","first_name":"Егор","middle_name":"","personnel_no":1002,"inn":"1234567891","position":"Казначей","dept":"Финансы","phone":"+380 67 000 00 02","status":"Активен","access":"Полный"},
    {"id":3,"last_name":"Мишустин","first_name":"Владимир","middle_name":"","personnel_no":1003,"inn":"1234567892","position":"Директор шахты","dept":"Управление","phone":"+380 67 000 00 03","status":"Ограничен","access":"Чтение"},
]

def _next_id():
    return (max((r["id"] for r in SEED), default=0) + 1) if SEED else 1

def _next_personnel_no():
    used=[r.get("personnel_no") for r in SEED if r.get("personnel_no")]
    start=1001
    return (max(used) + 1) if used else start

def _full_name(r):
    parts=[r.get("last_name","").strip(), r.get("first_name","").strip(), r.get("middle_name","").strip()]
    return " ".join([p for p in parts if p])

def apply_filters(rows):
    q = request.args.get("q","").strip().lower()
    dept = request.args.get("dept","").strip()
    status = request.args.get("status","").strip()
    role = request.args.get("role","").strip()
    res = rows
    if q:
        def hay(r):
            return " ".join([
                _full_name(r).lower(),
                r.get("position","").lower(), r.get("dept","").lower(), r.get("phone","").lower(),
                str(r.get("personnel_no","")), r.get("inn","").lower()
            ])
        res = [r for r in res if q in hay(r)]
    if dept:
        res = [r for r in res if r.get("dept")==dept]
    if status:
        res = [r for r in res if r.get("status")==status]
    if role:
        res = [r for r in res if r.get("access")==role]
    return res

# Список
@employees_bp.get("/")
def index():
    rows = apply_filters(SEED)
    return render_template("employees.html", title="Сотрудники", rows=rows, full_name=_full_name, total=len(rows), page=1, pages=1)

# Карточка
@employees_bp.get("/<int:emp_id>")
def show(emp_id:int):
    r = next((x for x in SEED if x["id"]==emp_id), None)
    if not r:
        flash("Сотрудник не найден", "err")
        return redirect(url_for("employees.index"))
    return render_template("employee_show.html", title=_full_name(r), r=r, full_name=_full_name)

# Создание
@employees_bp.get("/add")
def add():
    return render_template("employee_form.html", title="Добавить сотрудника", r=None)

@employees_bp.post("/add")
def add_post():
    f = request.form
    inn = f.get("inn","").strip()
    if not inn:
        flash("ИНН обязателен", "err")
        return redirect(url_for("employees.add"))
    pn = f.get("personnel_no","").strip()
    pn = int(pn) if pn.isdigit() else _next_personnel_no()
    new = {
        "id": _next_id(),
        "last_name": f.get("last_name","").strip(),
        "first_name": f.get("first_name","").strip(),
        "middle_name": f.get("middle_name","").strip(),
        "personnel_no": pn,
        "inn": inn,
        "position": f.get("position","").strip(),
        "dept": f.get("dept","").strip(),
        "phone": f.get("phone","").strip(),
        "status": f.get("status","Активен").strip() or "Активен",
        "access": f.get("access","Кабинет").strip() or "Кабинет",
    }
    SEED.append(new)
    flash("Сотрудник добавлен", "ok")
    return redirect(url_for("employees.index"))

# Редактирование
@employees_bp.get("/<int:emp_id>/edit")
def edit(emp_id:int):
    r = next((x for x in SEED if x["id"]==emp_id), None)
    if not r:
        flash("Сотрудник не найден", "err")
        return redirect(url_for("employees.index"))
    return render_template("employee_form.html", title=f"Редактирование: {_full_name(r)}", r=r)

@employees_bp.post("/<int:emp_id>/edit")
def edit_post(emp_id:int):
    r = next((x for x in SEED if x["id"]==emp_id), None)
    if not r:
        flash("Сотрудник не найден", "err")
        return redirect(url_for("employees.index"))
    f = request.form
    inn = f.get("inn","").strip()
    if not inn:
        flash("ИНН обязателен", "err")
        return redirect(url_for("employees.edit", emp_id=emp_id))
    pn = f.get("personnel_no","").strip()
    r.update({
        "last_name": f.get("last_name", r["last_name"]).strip(),
        "first_name": f.get("first_name", r["first_name"]).strip(),
        "middle_name": f.get("middle_name", r.get("middle_name","")).strip(),
        "personnel_no": int(pn) if pn.isdigit() else r.get("personnel_no") or _next_personnel_no(),
        "inn": inn,
        "position": f.get("position", r["position"]).strip(),
        "dept": f.get("dept", r["dept"]).strip(),
        "phone": f.get("phone", r["phone"]).strip(),
        "status": f.get("status", r["status"]).strip(),
        "access": f.get("access", r["access"]).strip(),
    })
    flash("Изменения сохранены", "ok")
    return redirect(url_for("employees.index"))

# Мягкое удаление (в архив)
@employees_bp.get("/<int:emp_id>/archive")
def archive(emp_id:int):
    r = next((x for x in SEED if x["id"]==emp_id), None)
    if not r:
        flash("Сотрудник не найден", "err")
    else:
        r["status"]="Архив"
        flash("Сотрудник перенесен в архив", "ok")
    return redirect(url_for("employees.index"))

# Восстановление из архива
@employees_bp.get("/<int:emp_id>/restore")
def restore(emp_id:int):
    r = next((x for x in SEED if x["id"]==emp_id), None)
    if not r:
        flash("Сотрудник не найден", "err")
    else:
        r["status"]="Активен"
        flash("Сотрудник восстановлен", "ok")
    return redirect(url_for("employees.index"))

# Жёсткое удаление (навсегда)
@employees_bp.get("/<int:emp_id>/delete")
def delete(emp_id:int):
    idx = next((i for i,x in enumerate(SEED) if x["id"]==emp_id), None)
    if idx is None:
        flash("Сотрудник не найден", "err")
    else:
        del SEED[idx]
        flash("Сотрудник удалён навсегда", "ok")
    return redirect(url_for("employees.index"))

# Импорт/Экспорт CSV c новыми полями
@employees_bp.get("/import")
def import_view():
    return render_template("employee_import.html", title="Импорт сотрудников (CSV)")

@employees_bp.post("/import")
def import_post():
    f = request.files.get("file")
    if not f:
        flash("Файл не выбран", "err")
        return redirect(url_for("employees.import_view"))
    import csv, io
    try:
        data = f.read().decode("utf-8", errors="ignore")
        rows = list(csv.DictReader(io.StringIO(data)))
        count = 0
        for row in rows:
            inn = (row.get("inn","") or "").strip()
            if not inn:
                # пропускаем строки без ИНН
                continue
            pn = (row.get("personnel_no","") or "").strip()
            pn = int(pn) if str(pn).isdigit() else _next_personnel_no()
            SEED.append({
                "id": _next_id(),
                "last_name": (row.get("last_name","") or "").strip(),
                "first_name": (row.get("first_name","") or "").strip(),
                "middle_name": (row.get("middle_name","") or "").strip(),
                "personnel_no": pn,
                "inn": inn,
                "position": (row.get("position","") or "").strip(),
                "dept": (row.get("dept","") or "").strip(),
                "phone": (row.get("phone","") or "").strip(),
                "status": (row.get("status","Активен") or "Активен").strip(),
                "access": (row.get("access","Кабинет") or "Кабинет").strip(),
            })
            count += 1
        flash(f"Импортировано: {count}", "ok")
    except Exception as e:
        flash(f"Ошибка импорта: {e}", "err")
    return redirect(url_for("employees.index"))

@employees_bp.get("/export.csv")
def export_csv():
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id","last_name","first_name","middle_name","personnel_no","inn","position","dept","phone","status","access"])
    for r in SEED:
        w.writerow([
            r.get("id"), r.get("last_name",""), r.get("first_name",""), r.get("middle_name",""),
            r.get("personnel_no",""), r.get("inn",""),
            r.get("position",""), r.get("dept",""), r.get("phone",""),
            r.get("status",""), r.get("access","")
        ])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=employees.csv"})
