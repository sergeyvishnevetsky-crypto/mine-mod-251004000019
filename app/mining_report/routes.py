from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
import io, csv, datetime as dt

from datetime import datetime
from flask import flash

def _parse_date_ru(s):
    if not s: return None
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    # последний шанс: fromisoformat
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        raise ValueError(f"Некорректная дата: {s}")

def _num(s, kind=float, default=0):
    if s is None: return default
    s = str(s).strip().replace(",", ".")
    if s == "": return default
    try:
        return kind(s)
    except Exception:
        # пробуем как int, если просили int и там дробь без точки/запятой
        if kind is int:
            try:
                return int(float(s))
            except Exception:
                pass
        raise ValueError(f"Некорректное число: {s}")
try:
    import pandas as pd
except Exception:
    pd = None

mining_bp = Blueprint("mining_report", __name__, template_folder="templates")

# В памяти (потом вынесем в БД)
# {id,date,fraction,quality,plan_total,fact_s1..s4,fact_total,note,unit='т'}
ROWS=[]
def _next_id(): return (max((r["id"] for r in ROWS), default=0) + 1)
def _num(x):
    try: 
        return float(str(x).replace(" ","").replace(",","."))
    except: 
        return 0.0

@mining_bp.get("/")
def index():
    q_from = request.args.get("from","")
    q_to   = request.args.get("to","")
    q_frac = (request.args.get("fraction","") or "").strip().lower()

    def ok(r):
        if q_frac and q_frac not in r.get("fraction","").lower(): return False
        if q_from and r["date"] < q_from: return False
        if q_to   and r["date"] > q_to:   return False
        return True

    rows = [r for r in ROWS if ok(r)]
    plan_sum = sum(_num(r.get("plan_total")) for r in rows)
    fact_sum = sum(_num(r.get("fact_total")) for r in rows)
    diff_sum = fact_sum - plan_sum
    return render_template("mining_index.html", title="Отчёт о добыче",
                           rows=rows, plan_sum=plan_sum, fact_sum=fact_sum, diff_sum=diff_sum)

@mining_bp.get("/new")
def new():
    r = {
        "date": dt.date.today().isoformat(),
        "fraction": "",
        "quality": "",
        "plan_total": "",
        "fact_s1": "", "fact_s2": "", "fact_s3": "", "fact_s4": "",
        "fact_total": "",
        "unit": "т",
        "note": ""
    }
    return render_template("mining_form.html", title="Новая суточная запись", r=r, mode="create")

@mining_bp.post("/new")
def create():
    f = request.form
    s1=_num(f.get("fact_s1")); s2=_num(f.get("fact_s2")); s3=_num(f.get("fact_s3")); s4=_num(f.get("fact_s4"))
    ROWS.append({
        "id": _next_id(),
        "date": (f.get("date") or "").strip(),
        "fraction": (f.get("fraction") or "").strip(),
        "quality": (f.get("quality") or "").strip(),
        "plan_total": _num(f.get("plan_total")),
        "fact_s1": s1, "fact_s2": s2, "fact_s3": s3, "fact_s4": s4,
        "fact_total": s1+s2+s3+s4,
        "unit": "т",
        "note": (f.get("note") or "").strip()
    })
    flash("Запись добавлена","ok")
    return redirect(url_for("mining_report.index"))

# --------- Импорт / Экспорт ----------
COLS = ["date","fraction","quality","plan_total","fact_s1","fact_s2","fact_s3","fact_s4","note"]

@mining_bp.post("/import")
def import_():
    file = request.files.get("file")
    if not file:
        flash("Файл не выбран","err"); return redirect(url_for("mining_report.index"))
    name=(file.filename or "").lower()
    added=0
    try:
        def add_row(d):
            nonlocal added
            s1=_num(d.get("fact_s1")); s2=_num(d.get("fact_s2")); s3=_num(d.get("fact_s3")); s4=_num(d.get("fact_s4"))
            ROWS.append({
                "id": _next_id(),
                "date": str(d.get("date") or "").strip(),
                "fraction": str(d.get("fraction") or "").strip(),
                "quality": str(d.get("quality") or "").strip(),
                "plan_total": _num(d.get("plan_total")),
                "fact_s1": s1, "fact_s2": s2, "fact_s3": s3, "fact_s4": s4,
                "fact_total": s1+s2+s3+s4,
                "unit": "т",
                "note": str(d.get("note") or "").strip()
            }); added += 1

        if name.endswith(".csv"):
            rdr=csv.DictReader(io.StringIO(file.read().decode("utf-8",errors="ignore")))
            for row in rdr:
                add_row(row)
        else:
            if pd is None:
                flash("Для XLSX нужен pandas/openpyxl","err"); return redirect(url_for("mining_report.index"))
            df=pd.read_excel(file, dtype=str).fillna("")
            # допускаем русские заголовки:
            # дата, фракция, качество, план, факт1..факт4, примечание
            RU_MAP={"дата":"date","фракция":"fraction","качество":"quality",
                    "план":"plan_total","факт1":"fact_s1","факт2":"fact_s2",
                    "факт3":"fact_s3","факт4":"fact_s4","примечание":"note"}
            df2=df.copy()
            df2.columns=[RU_MAP.get(str(c).strip().lower(), str(c).strip().lower()) for c in df.columns]
            for _,row in df2.iterrows():
                add_row({k:row.get(k,"") for k in COLS})
        flash(f"Импортировано строк: {added}","ok")
    except Exception as e:
        flash(f"Ошибка импорта: {e}","err")
    return redirect(url_for("mining_report.index"))

@mining_bp.get("/export.csv")
def export_csv():
    buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(COLS + ["fact_total","unit"])
    for r in ROWS:
        w.writerow([r.get(k,"") for k in COLS] + [r.get("fact_total",""), r.get("unit","т")])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=mining_report_daily.csv"})
