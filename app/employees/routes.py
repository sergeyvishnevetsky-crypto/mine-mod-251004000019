from flask import Blueprint, render_template, request, Response
employees_bp = Blueprint("employees", __name__, template_folder="templates")

SEED = [
    {"id":1,"fio":"Вишневецкий Сергей","position":"Начальник участка","dept":"Добыча-1","phone":"+380 67 000 00 01","status":"Активен","access":"Кабинет"},
    {"id":2,"fio":"Осташевский Егор","position":"Казначей","dept":"Финансы","phone":"+380 67 000 00 02","status":"Активен","access":"Полный"},
    {"id":3,"fio":"Мишустин Владимир","position":"Директор шахты","dept":"Управление","phone":"+380 67 000 00 03","status":"Ограничен","access":"Чтение"},
]

def apply_filters(rows):
    q = request.args.get("q","").strip().lower()
    dept = request.args.get("dept","").strip()
    status = request.args.get("status","").strip()
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
    rows = apply_filters(SEED)
    return render_template("employees.html", title="Сотрудники", rows=rows, total=len(rows), page=1, pages=1)

@employees_bp.get("/export.csv")
def export_csv():
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id","fio","position","dept","phone","status","access"])
    for r in SEED:
        w.writerow([r["id"],r["fio"],r["position"],r["dept"],r["phone"],r["status"],r["access"]])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=employees.csv"})
