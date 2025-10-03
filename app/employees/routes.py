from flask import Blueprint, render_template, request, Response, redirect, url_for

employees_bp = Blueprint("employees", __name__, template_folder="templates")

# Временный "in-memory" список (потом заменим БД/импортом)
SEED = [
    {"id":1,"fio":"Вишневецкий Сергей","position":"Начальник участка","dept":"Добыча-1","phone":"+380 67 000 00 01","status":"Активен","access":"Кабинет"},
    {"id":2,"fio":"Осташевский Егор","position":"Казначей","dept":"Финансы","phone":"+380 67 000 00 02","status":"Активен","access":"Полный"},
    {"id":3,"fio":"Мишустин Владимир","position":"Директор шахты","dept":"Управление","phone":"+380 67 000 00 03","status":"Ограничен","access":"Чтение"},
    {"id":4,"fio":"Прудкай Леонид","position":"Гл. механик","dept":"Техслужба","phone":"+380 67 000 00 04","status":"Активен","access":"Кабинет"},
    {"id":5,"fio":"Гуцал Денис","position":"Гл. инженер","dept":"Техслужба","phone":"+380 67 000 00 05","status":"Активен","access":"Кабинет"},
    {"id":6,"fio":"Прудник Виталий","position":"Снабжение","dept":"Логистика","phone":"+380 67 000 00 06","status":"Архив","access":"Нет"},
]

def apply_filters(rows):
    q = request.args.get("q","").strip().lower()
    dept = request.args.get("dept","").strip()
    status = request.args.get("status","").strip()
    role = request.args.get("role","").strip()  # сейчас не используем, placeholder
    res = rows
    if q:
        res = [r for r in res if q in (r["fio"]+" "+r["position"]+" "+r["dept"]+" "+r["phone"]).lower()]
    if dept:
        res = [r for r in res if r["dept"]==dept]
    if status:
        res = [r for r in res if r["status"]==status]
    return res

@employees_bp.get("/")
def index():
    page = int(request.args.get("page", 1))
    per_page = 10
    filtered = apply_filters(SEED)
    total = len(filtered)
    pages = max(1, (total + per_page - 1) // per_page)
    start = (page-1)*per_page
    rows = filtered[start:start+per_page]
    return render_template("employees.html", title="Сотрудники", rows=rows, total=total, page=page, pages=pages)

# --- Заглушки действий ---
@employees_bp.get("/add")
def add():
    return Response("Форма добавления (заглушка).", mimetype="text/plain")

@employees_bp.get("/import")
def import_view():
    return Response("Импорт (заглушка). Позже подключим xlsx/CSV.", mimetype="text/plain")

@employees_bp.get("/export.csv")
def export_csv():
    # простой экспорт текущего "SEED"
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id","fio","position","dept","phone","status","access"])
    for r in SEED:
        w.writerow([r["id"],r["fio"],r["position"],r["dept"],r["phone"],r["status"],r["access"]])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=employees.csv"})

@employees_bp.get("/<int:emp_id>")
def show(emp_id:int):
    return Response(f"Карточка сотрудника #{emp_id} (заглушка).", mimetype="text/plain")

@employees_bp.get("/<int:emp_id>/edit")
def edit(emp_id:int):
    return Response(f"Редактирование сотрудника #{emp_id} (заглушка).", mimetype="text/plain")

@employees_bp.get("/<int:emp_id>/archive")
def archive(emp_id:int):
    return Response(f"Архивирование сотрудника #{emp_id} (заглушка).", mimetype="text/plain")

@employees_bp.get("/<int:emp_id>/restore")
def restore(emp_id:int):
    return Response(f"Восстановление сотрудника #{emp_id} (заглушка).", mimetype="text/plain")
