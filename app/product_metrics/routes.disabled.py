from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
import io, csv
try:
    import pandas as pd
except Exception:
    pd = None

metrics_bp = Blueprint("product_metrics", __name__, template_folder="templates")

ROWS = []  # {id, fraction, grade, ash, moisture, sulfur, note}
def _next_id(): return (max((r["id"] for r in ROWS), default=0) + 1)

def _num(x):
    try:
        v = float(str(x).replace(",", ".").replace(" ", ""))
        return min(max(v, 0.0), 100.0)
    except:
        return 0.0

@metrics_bp.get("/")
def index():
    q_frac = (request.args.get("fraction","") or "").strip().lower()
    q_grade = (request.args.get("grade","") or "").strip().lower()
    def ok(r):
        if q_frac and q_frac not in r.get("fraction","").lower(): return False
        if q_grade and q_grade not in r.get("grade","").lower(): return False
        return True
    rows = [r for r in ROWS if ok(r)]
    return render_template("metrics_index.html", title="Показатели готовой продукции", rows=rows)

@metrics_bp.get("/new")
def new():
    r = {"fraction":"","grade":"","ash":"","moisture":"","sulfur":"","note":""}
    return render_template("metrics_form.html", title="Новая запись", r=r, mode="create")

@metrics_bp.post("/new")
def create():
    f = request.form
    ROWS.append({
        "id": _next_id(),
        "fraction": (f.get("fraction") or "").strip(),
        "grade":    (f.get("grade") or "").strip(),
        "ash":      _num(f.get("ash")),
        "moisture": _num(f.get("moisture")),
        "sulfur":   _num(f.get("sulfur")),
        "note":     (f.get("note") or "").strip(),
    })
    flash("Запись добавлена","ok")
    return redirect(url_for("product_metrics.index"))

@metrics_bp.get("/edit/<int:mid>")
def edit(mid:int):
    r = next((x for x in ROWS if x["id"]==mid), None)
    if not r:
        flash("Запись не найдена","err"); return redirect(url_for("product_metrics.index"))
    return render_template("metrics_form.html", title="Редактирование", r=r, mode="edit")

@metrics_bp.post("/edit/<int:mid>")
def update(mid:int):
    f = request.form
    r = next((x for x in ROWS if x["id"]==mid), None)
    if not r:
        flash("Запись не найдена","err"); return redirect(url_for("product_metrics.index"))
    r.update({
        "fraction": (f.get("fraction") or "").strip(),
        "grade":    (f.get("grade") or "").strip(),
        "ash":      _num(f.get("ash")),
        "moisture": _num(f.get("moisture")),
        "sulfur":   _num(f.get("sulfur")),
        "note":     (f.get("note") or "").strip(),
    })
    flash("Сохранено","ok")
    return redirect(url_for("product_metrics.index"))

@metrics_bp.post("/import")
def import_():
    file = request.files.get("file")
    if not file:
        flash("Файл не выбран","err"); return redirect(url_for("product_metrics.index"))
    name = (file.filename or "").lower()
    added = 0
    try:
        def add_row(d):
            nonlocal added
            ROWS.append({
                "id": _next_id(),
                "fraction": str(d.get("fraction") or d.get("фракция","")).strip(),
                "grade":    str(d.get("grade")    or d.get("марка","")).strip(),
                "ash":      _num(d.get("ash")     or d.get("зола","")),
                "moisture": _num(d.get("moisture")or d.get("влага","")),
                "sulfur":   _num(d.get("sulfur")  or d.get("сера","")),
                "note":     str(d.get("note")     or d.get("примечание","")).strip(),
            })
            added += 1

        if name.endswith(".csv"):
            import io, csv
            rdr = csv.DictReader(io.StringIO(file.read().decode("utf-8", errors="ignore")))
            for row in rdr: add_row(row)
        else:
            if pd is None:
                flash("Для XLSX импортa нужен pandas/openpyxl","err"); return redirect(url_for("product_metrics.index"))
            df = pd.read_excel(file, dtype=str).fillna("")
            for _, row in df.iterrows(): add_row(row)
        flash(f"Импортировано: {added}","ok")
    except Exception as e:
        flash(f"Ошибка импорта: {e}","err")
    return redirect(url_for("product_metrics.index"))

@metrics_bp.get("/export.csv")
def export_csv():
    import io, csv
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["fraction","grade","ash","moisture","sulfur","note"])
    for r in ROWS:
        w.writerow([r.get("fraction",""), r.get("grade",""), r.get("ash",""),
                    r.get("moisture",""), r.get("sulfur",""), r.get("note","")])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=product_metrics.csv"})
