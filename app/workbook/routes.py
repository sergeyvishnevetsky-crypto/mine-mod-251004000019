from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
import io, csv, datetime as dt

try:
    import pandas as pd
except Exception:
    pd = None

workbook_bp = Blueprint("workbook", __name__, template_folder="templates")

# ====== ВРЕМЕННО: справочники (демо до подключения БД/реальных модулей) ======
EMPLOYEES = [
    {"id": 1, "tab_no": "0001", "name": "Иванов И.И.", "role": "ГРОЗ"},
    {"id": 2, "tab_no": "0002", "name": "Петров П.П.", "role": "Маш."},
    {"id": 3, "tab_no": "0003", "name": "Сидоренко О.О.", "role": "Слес."},
]
NORMS = [
    {"id": 1, "code": "R-100", "name": "Погрузка угля в вагон", "unit": "т", "norm": 1.25, "rate": 540.00, "rate_unit": "грн/т"},
    {"id": 2, "code": "R-101", "name": "Перевалка ТМЦ", "unit": "т", "norm": 0.80, "rate": 420.00, "rate_unit": "грн/т"},
    {"id": 3, "code": "R-102", "name": "Ремонт агрегата", "unit": "час", "norm": 1.00, "rate": 1200.00, "rate_unit": "грн/час"},
]

# ====== Хранилище строк смены в памяти ======
ROWS = []  # элементы: dict(id, date, shift, site, brigade, employee_id, norm_id, unit, norm, rate, qty_plan, sum_plan, qty_fact, sum_fact, note)
def _next_id(): return (max((r["id"] for r in ROWS), default=0) + 1)

def _get_date():  # по умолчанию — сегодня (Europe/Kyiv)
    d = request.args.get("date")
    try:
        return dt.date.fromisoformat(d) if d else dt.date.today()
    except Exception:
        return dt.date.today()

def _shift_list(): return ["I", "II", "III", "IV"]
def _get_shift(): 
    s = (request.args.get("shift") or "I").upper()
    return s if s in _shift_list() else "I"

def _filters():
    return {
        "date": _get_date().isoformat(),
        "shift": _get_shift(),
        "site": request.args.get("site","Добыча-1"),
        "brigade": request.args.get("brigade","Бр. №1"),
    }

def _rows_for(flt):
    return [r for r in ROWS if r["date"]==flt["date"] and r["shift"]==flt["shift"] and r["site"]==flt["site"] and r["brigade"]==flt["brigade"]]

def _find_emp(eid): return next((e for e in EMPLOYEES if str(e["id"])==str(eid)), None)
def _find_norm(nid): return next((n for n in NORMS if str(n["id"])==str(nid)), None)
def _find_norm_by_code(code): return next((n for n in NORMS if n["code"]==code), None)

def _recalc(row):
    # суммы = кол-во * rate
    row["sum_plan"] = round(float(row.get("qty_plan",0) or 0) * float(row.get("rate",0) or 0), 2)
    row["sum_fact"] = round(float(row.get("qty_fact",0) or 0) * float(row.get("rate",0) or 0), 2)

@workbook_bp.get("/")
def index():
    flt = _filters()
    rows = _rows_for(flt)
    # агрегаты
    plan_qty = sum(r.get("qty_plan",0) or 0 for r in rows)
    plan_sum = sum(r.get("sum_plan",0) or 0 for r in rows)
    fact_qty = sum(r.get("qty_fact",0) or 0 for r in rows)
    fact_sum = sum(r.get("sum_fact",0) or 0 for r in rows)
    return render_template("workbook_index.html", title="Книга нарядов", rows=rows, flt=flt,
                           plan_qty=plan_qty, plan_sum=plan_sum, fact_qty=fact_qty, fact_sum=fact_sum,
                           employees=EMPLOYEES, norms=NORMS, shifts=_shift_list())

@workbook_bp.post("/add_row")
def add_row():
    flt = _filters()
    f = request.form
    emp_id = int(f.get("employee_id"))
    norm_id = None
    # можно прислать norm_id или norm_code
    if f.get("norm_id"):
        norm_id = int(f.get("norm_id"))
        norm = _find_norm(norm_id)
    else:
        code = (f.get("norm_code","") or "").strip()
        norm = _find_norm_by_code(code)
        norm_id = norm["id"] if norm else None
    if not _find_emp(emp_id) or not norm:
        flash("Сотрудник или норма не найдены","err")
        return redirect(url_for("workbook.index", **flt))
    row = {
        "id": _next_id(),
        "date": flt["date"], "shift": flt["shift"], "site": flt["site"], "brigade": flt["brigade"],
        "employee_id": emp_id, "norm_id": norm_id,
        "unit": norm["unit"], "norm": norm["norm"], "rate": norm["rate"],
        "qty_plan": float(f.get("qty_plan","0") or 0),
        "qty_fact": float(f.get("qty_fact","0") or 0),
        "sum_plan": 0.0, "sum_fact": 0.0,
        "note": (f.get("note","") or "").strip(),
    }
    _recalc(row)
    ROWS.append(row)
    flash("Строка добавлена","ok")
    return redirect(url_for("workbook.index", **flt))

@workbook_bp.post("/copy_plan_to_fact")
def copy_plan_to_fact():
    flt = _filters()
    rows = _rows_for(flt)
    for r in rows:
        r["qty_fact"] = r.get("qty_plan",0)
        _recalc(r)
    flash("План скопирован в факт","ok")
    return redirect(url_for("workbook.index", **flt))

@workbook_bp.get("/<int:rid>/delete")
def delete(rid:int):
    flt = _filters()
    idx = next((i for i,x in enumerate(ROWS) if x["id"]==rid), None)
    if idx is None: flash("Строка не найдена","err")
    else:
        del ROWS[idx]; flash("Удалено","ok")
    return redirect(url_for("workbook.index", **flt))

@workbook_bp.get("/<int:rid>/edit")
def edit(rid:int):
    flt = _filters()
    r = next((x for x in ROWS if x["id"]==rid), None)
    if not r:
        flash("Строка не найдена","err")
        return redirect(url_for("workbook.index", **flt))
    return render_template("workbook_form.html", title=f"Редактирование строки {rid}", r=r, flt=flt, employees=EMPLOYEES, norms=NORMS)

@workbook_bp.post("/<int:rid>/edit")
def edit_post(rid:int):
    flt = _filters()
    r = next((x for x in ROWS if x["id"]==rid), None)
    if not r:
        flash("Строка не найдена","err")
        return redirect(url_for("workbook.index", **flt))
    f = request.form
    emp_id = int(f.get("employee_id"))
    norm_id = int(f.get("norm_id"))
    emp = _find_emp(emp_id); norm = _find_norm(norm_id)
    if not emp or not norm:
        flash("Сотрудник/норма не найдены","err")
        return redirect(url_for("workbook.index", **flt))
    r.update({
        "employee_id": emp_id, "norm_id": norm_id,
        "unit": norm["unit"], "norm": norm["norm"], "rate": norm["rate"],
        "qty_plan": float(f.get("qty_plan","0") or 0),
        "qty_fact": float(f.get("qty_fact","0") or 0),
        "note": (f.get("note","") or "").strip(),
    })
    _recalc(r)
    flash("Сохранено","ok")
    return redirect(url_for("workbook.index", **flt))

# ===== Импорт/экспорт плана =====
@workbook_bp.post("/import_plan")
def import_plan():
    flt = _filters()
    file = request.files.get("file")
    if not file: flash("Файл не выбран","err"); return redirect(url_for("workbook.index", **flt))
    fname = (file.filename or "").lower()
    count = 0
    try:
        if fname.endswith(".csv"):
            data = file.read().decode("utf-8",errors="ignore")
            for row in csv.DictReader(io.StringIO(data)):
                emp = next((e for e in EMPLOYEES if e["tab_no"]==row.get("tab_no","")), None)
                norm = _find_norm_by_code(row.get("norm_code",""))
                if not emp or not norm: continue
                r = {
                    "id": _next_id(),
                    "date": flt["date"], "shift": flt["shift"], "site": flt["site"], "brigade": flt["brigade"],
                    "employee_id": emp["id"], "norm_id": norm["id"],
                    "unit": norm["unit"], "norm": norm["norm"], "rate": norm["rate"],
                    "qty_plan": float(row.get("qty_plan","0") or 0),
                    "qty_fact": 0.0, "sum_plan": 0.0, "sum_fact": 0.0, "note": (row.get("note","") or "").strip(),
                }
                _recalc(r); ROWS.append(r); count += 1
        else:
            if pd is None: flash("Для XLSX нужен pandas/openpyxl","err"); return redirect(url_for("workbook.index", **flt))
            df = pd.read_excel(file, dtype=str).fillna("")
            for _, row in df.iterrows():
                emp = next((e for e in EMPLOYEES if e["tab_no"]==row.get("tab_no","")), None)
                norm = _find_norm_by_code(row.get("norm_code",""))
                if not emp or not norm: continue
                r = {
                    "id": _next_id(),
                    "date": flt["date"], "shift": flt["shift"], "site": flt["site"], "brigade": flt["brigade"],
                    "employee_id": emp["id"], "norm_id": norm["id"],
                    "unit": norm["unit"], "norm": float(norm["norm"]), "rate": float(norm["rate"]),
                    "qty_plan": float(row.get("qty_plan","0") or 0),
                    "qty_fact": 0.0, "sum_plan": 0.0, "sum_fact": 0.0, "note": (row.get("note","") or "").strip(),
                }
                _recalc(r); ROWS.append(r); count += 1
        flash(f"Импортировано строк плана: {count}","ok")
    except Exception as e:
        flash(f"Ошибка импорта: {e}","err")
    return redirect(url_for("workbook.index", **flt))

@workbook_bp.get("/export.csv")
def export_csv():
    flt = _filters()
    rows = _rows_for(flt)
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["date","shift","site","brigade","tab_no","employee","role","norm_code","norm_name","unit","norm","rate","qty_plan","sum_plan","qty_fact","sum_fact","note"])
    for r in rows:
        emp = _find_emp(r["employee_id"]); norm = _find_norm(r["norm_id"])
        w.writerow([r["date"],r["shift"],r["site"],r["brigade"],
                    emp["tab_no"],emp["name"],emp["role"],
                    norm["code"],norm["name"],r["unit"],r["norm"],r["rate"],
                    r.get("qty_plan",0),r.get("sum_plan",0),r.get("qty_fact",0),r.get("sum_fact",0),
                    r.get("note","")])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=workbook_export.csv"})

@workbook_bp.get("/template_plan.xlsx")
def template_plan():
    cols = ["tab_no","norm_code","qty_plan","note"]
    if pd is None:
        buf=io.StringIO(); csv.writer(buf).writerow(cols)
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition":"attachment; filename=workbook_plan_template.csv"})
    df = pd.DataFrame(columns=cols)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="plan")
    return Response(buf.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition":"attachment; filename=workbook_plan_template.xlsx"})
