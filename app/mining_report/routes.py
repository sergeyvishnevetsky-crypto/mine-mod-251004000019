from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
import io, csv, datetime as dt

try:
    import pandas as pd
except Exception:
    pd = None

mining_bp = Blueprint("mining_report", __name__, template_folder="templates")

# Временное «хранилище» в памяти. Позже заменим БД.
ROWS = []   # [{id,date,shift,site,brigade,material,unit,plan,fact,note}]
def _next_id(): return (max((r["id"] for r in ROWS), default=0) + 1)

# Допустимые ключи и «мягкое» сопоставление заголовков файла по подстрокам
MAP = {
    "date":    ["дата","date"],
    "shift":   ["смен","shift"],
    "site":    ["участ","цех","site"],
    "brigade": ["бриг","brig"],
    "material":["матер","уголь","порода","material"],
    "unit":    ["ед","изм","unit"],
    "plan":    ["план","plan"],
    "fact":    ["факт","fact"],
    "note":    ["прим","комм","note","remark"],
}
def _best_key(colname:str):
    n = colname.lower()
    for key, hints in MAP.items():
        if any(h in n for h in hints):
            return key
    return None

@mining_bp.get("/")
def index():
    # Фильтры
    q_site  = (request.args.get("site","") or "").strip().lower()
    q_brig  = (request.args.get("brigade","") or "").strip().lower()
    q_shift = (request.args.get("shift","") or "").strip().lower()
    q_mat   = (request.args.get("material","") or "").strip().lower()
    q_from  = request.args.get("from","")
    q_to    = request.args.get("to","")

    def ok(r):
        if q_site and q_site not in (r.get("site","").lower()): return False
        if q_brig and q_brig not in (r.get("brigade","").lower()): return False
        if q_shift and q_shift != str(r.get("shift","")).lower(): return False
        if q_mat and q_mat not in (r.get("material","").lower()): return False
        if q_from:
            try:
                if r.get("date") < q_from: return False
            except: pass
        if q_to:
            try:
                if r.get("date") > q_to: return False
            except: pass
        return True

    rows = [r for r in ROWS if ok(r)]

    # Итоги
    plan_sum = sum(float(r.get("plan") or 0) for r in rows)
    fact_sum = sum(float(r.get("fact") or 0) for r in rows)
    diff_sum = fact_sum - plan_sum

    return render_template("mining_index.html",
                           title="Отчёт о добыче",
                           rows=rows, plan_sum=plan_sum, fact_sum=fact_sum, diff_sum=diff_sum)

@mining_bp.get("/new")
def new():
    r = {"date": dt.date.today().isoformat(), "shift": "", "site": "", "brigade": "",
         "material": "", "unit": "т", "plan": "", "fact": "", "note": ""}
    return render_template("mining_form.html", title="Новая запись отчёта", r=r, mode="create")

@mining_bp.post("/new")
def create():
    f=request.form
    ROWS.append({
        "id": _next_id(),
        "date":  (f.get("date") or "").strip(),
        "shift": (f.get("shift") or "").strip(),
        "site":  (f.get("site") or "").strip(),
        "brigade": (f.get("brigade") or "").strip(),
        "material": (f.get("material") or "").strip(),
        "unit": (f.get("unit") or "").strip(),
        "plan": float(f.get("plan") or 0),
        "fact": float(f.get("fact") or 0),
        "note": (f.get("note") or "").strip(),
    })
    flash("Запись добавлена","ok")
    return redirect(url_for("mining_report.index"))

@mining_bp.post("/import")
def import_():
    f = request.files.get("file")
    if not f:
        flash("Файл не выбран","err"); return redirect(url_for("mining_report.index"))
    name=(f.filename or "").lower()
    try:
        rows = []
        if name.endswith(".csv"):
            rdr = csv.DictReader(io.StringIO(f.read().decode("utf-8", errors="ignore")))
            for row in rdr:
                rec = {"id": _next_id()}
                for col,val in row.items():
                    key = _best_key(col) or col
                    rec[key] = str(val).strip()
                # нормализуем
                rec.setdefault("unit","т")
                rec["plan"] = float(rec.get("plan") or 0)
                rec["fact"] = float(rec.get("fact") or 0)
                rows.append(rec)
        else:
            if pd is None:
                flash("Для XLSX нужен pandas/openpyxl","err")
                return redirect(url_for("mining_report.index"))
            df = pd.read_excel(f, dtype=str).fillna("")
            for _, row in df.iterrows():
                rec = {"id": _next_id()}
                for col in df.columns:
                    key = _best_key(str(col)) or str(col)
                    rec[key] = str(row[col]).strip()
                rec.setdefault("unit","т")
                # каст чисел
                def num(x):
                    try: return float(str(x).replace(" ","").replace(",", "."))
                    except: return 0.0
                rec["plan"] = num(rec.get("plan"))
                rec["fact"] = num(rec.get("fact"))
                rows.append(rec)
        # массовое добавление
        ROWS.extend(rows)
        flash(f"Импортировано строк: {len(rows)}","ok")
    except Exception as e:
        flash(f"Ошибка импорта: {e}","err")
    return redirect(url_for("mining_report.index"))

@mining_bp.get("/export.csv")
def export_csv():
    buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(["id","date","shift","site","brigade","material","unit","plan","fact","diff","note"])
    for r in ROWS:
        w.writerow([
            r.get("id"), r.get("date"), r.get("shift"), r.get("site"), r.get("brigade"),
            r.get("material"), r.get("unit"), r.get("plan"), r.get("fact"),
            float(r.get("fact") or 0) - float(r.get("plan") or 0), r.get("note","")
        ])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=mining_report.csv"})
