from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
import io, csv, datetime as dt

try:
    import pandas as pd  # для XLSX
except Exception:  # на случай локального запуска без обновления pip
    pd = None

norms_bp = Blueprint("norms", __name__, template_folder="templates", static_folder="static")

# Демоданные в памяти (до подключения БД)
ROWS = [
    {"id":1,"code":"R-100","name":"Погрузка угля в вагон","unit":"т","norm":1.25,"rate":540.00,"rate_unit":"грн/т","start_date":"2025-01-01","status":"Активен"},
    {"id":2,"code":"R-101","name":"Перевалка ТМЦ","unit":"т","norm":0.80,"rate":420.00,"rate_unit":"грн/т","start_date":"2025-02-01","status":"Активен"},
    {"id":3,"code":"R-102","name":"Ремонт агрегата","unit":"шт","norm":1.00,"rate":1200.00,"rate_unit":"грн/шт","start_date":"2025-03-15","status":"Ограничен"},
]
def _next_id(): return (max(r["id"] for r in ROWS)+1) if ROWS else 1

COLUMNS = ["code","name","unit","norm","rate","rate_unit","start_date","status"]

def _filter(rows):
    q = (request.args.get("q","") or "").strip().lower()
    unit = (request.args.get("unit","") or "").strip()
    status = (request.args.get("status","") or "").strip()
    res = rows
    if q:
        def hay(r):
            return " ".join([r.get("code",""), r.get("name",""), r.get("unit",""),
                             str(r.get("norm","")), str(r.get("rate","")), r.get("rate_unit",""),
                             r.get("start_date",""), r.get("status","")]).lower()
        res = [r for r in res if q in hay(r)]
    if unit:
        res = [r for r in res if r.get("unit","")==unit]
    if status:
        res = [r for r in res if r.get("status","")==status]
    return res

@norms_bp.get("/")
def index():
    rows = _filter(ROWS)
    return render_template("norms_index.html", title="Нормы и расценки", rows=rows, total=len(rows), page=1, pages=1)

@norms_bp.get("/add")
def add():
    return render_template("norms_form.html", title="Добавить норму", r=None)

@norms_bp.post("/add")
def add_post():
    f = request.form
    ROWS.append({
        "id": _next_id(),
        "code": f.get("code","").strip(),
        "name": f.get("name","").strip(),
        "unit": f.get("unit","").strip(),
        "norm": float(f.get("norm","0") or 0),
        "rate": float(f.get("rate","0") or 0),
        "rate_unit": f.get("rate_unit","").strip(),
        "start_date": f.get("start_date","").strip() or dt.date.today().isoformat(),
        "status": f.get("status","Активен").strip() or "Активен",
    })
    flash("Норма добавлена","ok")
    return redirect(url_for("norms.index"))

@norms_bp.get("/<int:rid>/edit")
def edit(rid:int):
    r = next((x for x in ROWS if x["id"]==rid), None)
    if not r: flash("Запись не найдена","err"); return redirect(url_for("norms.index"))
    return render_template("norms_form.html", title=f"Редактирование: {r['code']}", r=r)

@norms_bp.post("/<int:rid>/edit")
def edit_post(rid:int):
    r = next((x for x in ROWS if x["id"]==rid), None)
    if not r: flash("Запись не найдена","err"); return redirect(url_for("norms.index"))
    f = request.form
    r.update({
        "code": f.get("code", r["code"]).strip(),
        "name": f.get("name", r["name"]).strip(),
        "unit": f.get("unit", r["unit"]).strip(),
        "norm": float(f.get("norm", r["norm"]) or 0),
        "rate": float(f.get("rate", r["rate"]) or 0),
        "rate_unit": f.get("rate_unit", r["rate_unit"]).strip(),
        "start_date": f.get("start_date", r["start_date"]).strip(),
        "status": f.get("status", r["status"]).strip(),
    })
    flash("Изменения сохранены","ok")
    return redirect(url_for("norms.index"))

@norms_bp.get("/<int:rid>/archive")
def archive(rid:int):
    r = next((x for x in ROWS if x["id"]==rid), None)
    if not r: flash("Запись не найдена","err")
    else: r["status"]="Архив"; flash("Перенесено в архив","ok")
    return redirect(url_for("norms.index"))

@norms_bp.get("/<int:rid>/delete")
def delete(rid:int):
    idx = next((i for i,x in enumerate(ROWS) if x["id"]==rid), None)
    if idx is None: flash("Запись не найдена","err")
    else: del ROWS[idx]; flash("Удалено навсегда","ok")
    return redirect(url_for("norms.index"))

# ----- Импорт / Экспорт -----
@norms_bp.get("/template.xlsx")
def template_xlsx():
    """Шаблон XLSX для импорта."""
    if pd is None:
        # Минимальный CSV-заменитель, если pandas не доступен
        buf = io.StringIO()
        w = csv.writer(buf); w.writerow(COLUMNS)
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition":"attachment; filename=norms_template.csv"})
    df = pd.DataFrame(columns=COLUMNS)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="norms")
    return Response(buf.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition":"attachment; filename=norms_template.xlsx"})

@norms_bp.post("/import")
def import_post():
    """Импорт XLSX/CSV. Ожидаемые колонки: code,name,unit,norm,rate,rate_unit,start_date,status"""
    file = request.files.get("file")
    if not file:
        flash("Файл не выбран","err"); return redirect(url_for("norms.index"))
    fname = (file.filename or "").lower()
    count = 0
    try:
        if fname.endswith(".csv"):
            data = file.read().decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(data))
            for row in reader:
                ROWS.append({
                    "id": _next_id(),
                    "code": (row.get("code","") or "").strip(),
                    "name": (row.get("name","") or "").strip(),
                    "unit": (row.get("unit","") or "").strip(),
                    "norm": float(row.get("norm","0") or 0),
                    "rate": float(row.get("rate","0") or 0),
                    "rate_unit": (row.get("rate_unit","") or "").strip(),
                    "start_date": (row.get("start_date","") or "").strip(),
                    "status": (row.get("status","Активен") or "Активен").strip(),
                }); count += 1
        else:
            if pd is None:
                flash("Для импорта XLSX требуется pandas/openpyxl","err")
                return redirect(url_for("norms.index"))
            df = pd.read_excel(file, dtype=str).fillna("")
            for _, row in df.iterrows():
                ROWS.append({
                    "id": _next_id(),
                    "code": row.get("code","").strip(),
                    "name": row.get("name","").strip(),
                    "unit": row.get("unit","").strip(),
                    "norm": float(row.get("norm","0") or 0),
                    "rate": float(row.get("rate","0") or 0),
                    "rate_unit": row.get("rate_unit","").strip(),
                    "start_date": row.get("start_date","").strip(),
                    "status": (row.get("status","Активен") or "Активен").strip(),
                }); count += 1
        flash(f"Импортировано: {count}","ok")
    except Exception as e:
        flash(f"Ошибка импорта: {e}","err")
    return redirect(url_for("norms.index"))

@norms_bp.get("/export.csv")
def export_csv():
    rows = _filter(ROWS)
    buf = io.StringIO()
    w = csv.writer(buf); w.writerow(["id"] + COLUMNS)
    for r in rows:
        w.writerow([r.get("id")] + [r.get(k,"") for k in COLUMNS])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=norms_export.csv"})

@norms_bp.get("/export.xlsx")
def export_xlsx():
    rows = _filter(ROWS)
    if pd is None:
        # Fallback: отдать CSV, если нет pandas
        return export_csv()
    df = pd.DataFrame([{k: r.get(k,"") for k in ["id"]+COLUMNS} for r in rows])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="norms")
    return Response(buf.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition":"attachment; filename=norms_export.xlsx"})
