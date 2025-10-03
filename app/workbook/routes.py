from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
import io, csv, datetime as dt
from collections import defaultdict

try:
    import pandas as pd
except Exception:
    pd = None

workbook_bp = Blueprint("workbook", __name__, template_folder="templates")

# ====== ВРЕМЕННЫЕ СПРАВОЧНИКИ (до подключения реальных модулей) ======
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

# ====== Хранилища в памяти ======
# ROWS: строки нарядов (план/факт) для конкретной смены
ROWS = []  # dict(id, date, shift, site, brigade, employee_id, norm_id, unit, norm, rate, qty_plan, sum_plan, qty_fact, sum_fact, note)
# SHIFTS: статусы смен: "plan" | "fact" | "closed"
SHIFTS = {}  # key()-> {"status": ..., "created_at": date, "approved_at": dt or None}

def _next_id(): return (max((r["id"] for r in ROWS), default=0) + 1)

def _shift_list(): return ["I", "II", "III", "IV"]

def _get_date():
    d = request.args.get("date")
    try:
        return dt.date.fromisoformat(d) if d else dt.date.today()
    except Exception:
        return dt.date.today()

def _filters():
    return {
        "date": _get_date().isoformat(),
        "shift": (request.args.get("shift") or "I").upper() if request.args.get("shift") else "I",
        "site": request.args.get("site","Добыча-1"),
        "brigade": request.args.get("brigade","Бр. №1"),
    }

def _key(flt):
    return (flt["date"], flt["shift"], flt["site"], flt["brigade"])

def _ensure_shift(flt):
    k = _key(flt)
    if k not in SHIFTS:
        SHIFTS[k] = {"status": "plan", "created_at": dt.datetime.now(), "approved_at": None}
    return SHIFTS[k]

def _rows_for(flt):
    return [r for r in ROWS if (r["date"], r["shift"], r["site"], r["brigade"]) == _key(flt)]

def _find_emp(eid): return next((e for e in EMPLOYEES if str(e["id"])==str(eid)), None)
def _find_norm(nid): return next((n for n in NORMS if str(n["id"])==str(nid)), None)
def _find_norm_by_code(code): return next((n for n in NORMS if n["code"]==code), None)

def _recalc(row):
    row["sum_plan"] = round((row.get("qty_plan") or 0) * (row.get("rate") or 0), 2)
    row["sum_fact"] = round((row.get("qty_fact") or 0) * (row.get("rate") or 0), 2)

def _calc_totals(rows):
    return {
        "plan_qty": sum(r.get("qty_plan",0) or 0 for r in rows),
        "plan_sum": sum(r.get("sum_plan",0) or 0 for r in rows),
        "fact_qty": sum(r.get("qty_fact",0) or 0 for r in rows),
        "fact_sum": sum(r.get("sum_fact",0) or 0 for r in rows),
    }

def _history(limit=30):
    # агрегируем по ключу смены
    agg = defaultdict(lambda: {"plan_qty":0,"plan_sum":0,"fact_qty":0,"fact_sum":0})
    for r in ROWS:
        k = (r["date"], r["shift"], r["site"], r["brigade"])
        agg[k]["plan_qty"] += r.get("qty_plan",0) or 0
        agg[k]["plan_sum"] += r.get("sum_plan",0) or 0
        agg[k]["fact_qty"] += r.get("qty_fact",0) or 0
        agg[k]["fact_sum"] += r.get("sum_fact",0) or 0
    items = []
    for k,v in agg.items():
        st = SHIFTS.get(k, {"status":"plan"})
        items.append({"date":k[0], "shift":k[1], "site":k[2], "brigade":k[3], "status":st["status"],
                      "plan_qty":v["plan_qty"], "plan_sum":v["plan_sum"],
                      "fact_qty":v["fact_qty"], "fact_sum":v["fact_sum"]})
    # сортировка по дате/смене (свежие сверху)
    items.sort(key=lambda x:(x["date"], _shift_list().index(x["shift"])), reverse=True)
    return items[:limit]

@workbook_bp.get("/")
def index():
    flt = _filters()
    sh = _ensure_shift(flt)
    rows = _rows_for(flt)
    totals = _calc_totals(rows)
    return render_template("workbook_index.html", title="Книга нарядов",
                           rows=rows, flt=flt, shifts=_shift_list(), shift=sh,
                           employees=EMPLOYEES, norms=NORMS, **totals,
                           history=_history(50))

# ====== ДЕЙСТВИЯ С ФАЗАМИ ======
@workbook_bp.post("/lock_plan")
def lock_plan():
    flt = _filters(); sh = _ensure_shift(flt)
    if sh["status"] != "plan":
        flash("План уже зафиксирован или смена закрыта","err")
    else:
        sh["status"] = "fact"  # переходим к вводу факта
        flash("План зафиксирован. Перейдите к вводу факта.","ok")
    return redirect(url_for("workbook.index", **flt))

@workbook_bp.post("/close_shift")
def close_shift():
    flt = _filters(); sh = _ensure_shift(flt)
    if sh["status"] != "fact":
        flash("Нельзя закрыть: сначала зафиксируйте план и внесите факт.","err")
    else:
        sh["status"] = "closed"; sh["approved_at"] = dt.datetime.now()
        flash("Смена закрыта.","ok")
    return redirect(url_for("workbook.index", **flt))

@workbook_bp.post("/reopen_to_plan")
def reopen_to_plan():
    flt = _filters(); sh = _ensure_shift(flt)
    sh["status"] = "plan"; sh["approved_at"] = None
    flash("Смена возвращена в стадию ПЛАН.","ok")
    return redirect(url_for("workbook.index", **flt))

# ====== CRUD-СТРОК ======
@workbook_bp.post("/add_row")
def add_row():
    flt = _filters(); sh = _ensure_shift(flt)
    if sh["status"] not in ("plan","fact"):
        flash("Смена закрыта — редактирование запрещено","err")
        return redirect(url_for("workbook.index", **flt))
    f = request.form
    emp_id = int(f.get("employee_id"))
    norm_id = int(f.get("norm_id")) if f.get("norm_id") else None
    if norm_id is None and f.get("norm_code"):
        norm = _find_norm_by_code((f.get("norm_code") or "").strip())
        norm_id = norm["id"] if norm else None
    emp = _find_emp(emp_id); norm = _find_norm(norm_id)
    if not emp or not norm:
        flash("Сотрудник/норма не найдены","err")
        return redirect(url_for("workbook.index", **flt))
    row = {
        "id": _next_id(),
        "date": flt["date"], "shift": flt["shift"], "site": flt["site"], "brigade": flt["brigade"],
        "employee_id": emp_id, "norm_id": norm_id,
        "unit": norm["unit"], "norm": float(norm["norm"]), "rate": float(norm["rate"]),
        "qty_plan": float(f.get("qty_plan","0") or 0),
        "qty_fact": float(f.get("qty_fact","0") or 0) if sh["status"]=="fact" else 0.0,
        "sum_plan": 0.0, "sum_fact": 0.0,
        "note": (f.get("note","") or "").strip(),
    }
    _recalc(row)
    ROWS.append(row)
    flash("Строка добавлена","ok")
    return redirect(url_for("workbook.index", **flt))

@workbook_bp.get("/<int:rid>/delete")
def delete(rid:int):
    flt = _filters(); sh = _ensure_shift(flt)
    if sh["status"] == "closed":
        flash("Смена закрыта — удаление запрещено","err")
        return redirect(url_for("workbook.index", **flt))
    idx = next((i for i,x in enumerate(ROWS) if x["id"]==rid), None)
    if idx is None: flash("Строка не найдена","err")
    else: del ROWS[idx]; flash("Удалено","ok")
    return redirect(url_for("workbook.index", **flt))

@workbook_bp.get("/<int:rid>/edit")
def edit(rid:int):
    flt = _filters(); sh = _ensure_shift(flt)
    r = next((x for x in ROWS if x["id"]==rid), None)
    if not r:
        flash("Строка не найдена","err")
        return redirect(url_for("workbook.index", **flt))
    # в режиме PLAN редактируем план; в FACT — план трогаем нельзя, только факт
    return render_template("workbook_form.html", title=f"Редактирование строки {rid}", r=r, flt=flt,
                           employees=EMPLOYEES, norms=NORMS, mode=sh["status"])

@workbook_bp.post("/<int:rid>/edit")
def edit_post(rid:int):
    flt = _filters(); sh = _ensure_shift(flt)
    r = next((x for x in ROWS if x["id"]==rid), None)
    if not r:
        flash("Строка не найдена","err")
        return redirect(url_for("workbook.index", **flt))
    f = request.form
    if sh["status"] == "plan":
        emp = _find_emp(int(f.get("employee_id"))); norm = _find_norm(int(f.get("norm_id")))
        if not emp or not norm:
            flash("Сотрудник/норма не найдены","err"); return redirect(url_for("workbook.index", **flt))
        r.update({
            "employee_id": emp["id"], "norm_id": norm["id"],
            "unit": norm["unit"], "norm": float(norm["norm"]), "rate": float(norm["rate"]),
            "qty_plan": float(f.get("qty_plan","0") or 0),
            "note": (f.get("note","") or "").strip(),
        })
    elif sh["status"] == "fact":
        r.update({
            "qty_fact": float(f.get("qty_fact","0") or 0),
            "note": (f.get("note","") or "").strip(),
        })
    else:
        flash("Смена закрыта — редактирование запрещено","err"); return redirect(url_for("workbook.index", **flt))
    _recalc(r); flash("Сохранено","ok")
    return redirect(url_for("workbook.index", **flt))

@workbook_bp.post("/copy_plan_to_fact")
def copy_plan_to_fact():
    flt = _filters(); sh = _ensure_shift(flt)
    if sh["status"] != "fact":
        flash("Доступно только в фазе ФАКТ","err")
        return redirect(url_for("workbook.index", **flt))
    for r in _rows_for(flt):
        r["qty_fact"] = r.get("qty_plan",0)
        _recalc(r)
    flash("План скопирован в факт","ok")
    return redirect(url_for("workbook.index", **flt))

# ===== Импорт/экспорт =====
@workbook_bp.post("/import_plan")
def import_plan():
    flt = _filters(); sh = _ensure_shift(flt)
    if sh["status"] != "plan":
        flash("Импорт плана возможен только в фазе ПЛАН","err")
        return redirect(url_for("workbook.index", **flt))
    file = request.files.get("file")
    if not file: flash("Файл не выбран","err"); return redirect(url_for("workbook.index", **flt))
    fname = (file.filename or "").lower(); count = 0
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
                    "unit": norm["unit"], "norm": float(norm["norm"]), "rate": float(norm["rate"]),
                    "qty_plan": float(row.get("qty_plan","0") or 0),
                    "qty_fact": 0.0, "sum_plan": 0.0, "sum_fact": 0.0,
                    "note": (row.get("note","") or "").strip(),
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
                    "qty_fact": 0.0, "sum_plan": 0.0, "sum_fact": 0.0,
                    "note": (row.get("note","") or "").strip(),
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
