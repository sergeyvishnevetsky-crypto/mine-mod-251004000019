from flask import Blueprint, render_template, request, redirect, url_for, jsonify, Response
import io, csv
import pandas as pd

prod_bp = Blueprint("prod_metrics", __name__, template_folder="templates")

# Память процесса для быстрого старта
_STATE = {
    "rows": []  # list of dicts
}

# Колонки (порядок отображения и экспорта)
COLUMNS = [
    ("fraction", "Фракция"),
    ("grade",    "Марка"),
    ("ash",      "Зола (%)"),
    ("moist",    "Влага (%)"),
    ("sulfur",   "Сера (%)"),
    ("note",     "Примечание"),
    ("status",   "Статус"),  # active/archived
]

def _normalize_row(d):
    return {
        "fraction": str(d.get("fraction","")).strip(),
        "grade":    str(d.get("grade","")).strip(),
        "ash":      str(d.get("ash","")).strip(),
        "moist":    str(d.get("moist","")).strip(),
        "sulfur":   str(d.get("sulfur","")).strip(),
        "note":     str(d.get("note","")).strip(),
        "status":   (str(d.get("status","active")).strip() or "active"),
    }

@prod_bp.route("/", methods=["GET"])
def index():
    return render_template("prod_metrics/index.html", rows=_STATE["rows"], columns=COLUMNS)

@prod_bp.route("/params", methods=["GET"])
def params():
    return jsonify({
        "title": "Показатели готовой продукции",
        "columns": [{"key":k, "title": t} for k,t in COLUMNS],
        "count": len(_STATE["rows"])
    })

@prod_bp.route("/add", methods=["POST"])
def add_row():
    row = _normalize_row(request.form.to_dict())
    _STATE["rows"].append(row)
    return redirect(url_for("prod_metrics.index"))

@prod_bp.route("/delete/<int:idx>", methods=["POST"])
def delete_row(idx):
    if 0 <= idx < len(_STATE["rows"]):
        del _STATE["rows"][idx]
    return redirect(url_for("prod_metrics.index"))

@prod_bp.route("/import", methods=["POST"])
def import_data():
    f = request.files.get("file")
    if not f or not f.filename:
        return redirect(url_for("prod_metrics.index"))
    # XLSX или CSV
    if f.filename.lower().endswith(".xlsx"):
        df = pd.read_excel(f)
    else:
        df = pd.read_csv(f)
    # ожидаем колонки по ключам
    wanted = [k for k,_ in COLUMNS]
    cols = [c for c in df.columns]
    # попытка сопоставить русские заголовки
    rus_to_key = {title:key for key,title in COLUMNS}
    mapped = []
    for c in cols:
        k = rus_to_key.get(str(c).strip())
        mapped.append(k if k else str(c).strip())
    df.columns = mapped
    df = df[[k for k in wanted if k in df.columns]].copy()
    rows = [ _normalize_row(m) for m in df.to_dict(orient="records") ]
    _STATE["rows"] = rows
    return redirect(url_for("prod_metrics.index"))

@prod_bp.route("/template.xlsx", methods=["GET"])
def template_xlsx():
    df = pd.DataFrame([{k:t} for k,t in COLUMNS]).T.iloc[1:].T
    df.columns = [title for _,title in COLUMNS]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return Response(buf.getvalue(),
        headers={
            "Content-Disposition":"attachment; filename=prod-metrics-template.xlsx",
            "Cache-Control":"no-cache"
        },
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@prod_bp.route("/export.csv")
def export_csv():
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow([title for _,title in COLUMNS])
    for r in _STATE["rows"]:
        writer.writerow([r.get(k,"") for k,_ in COLUMNS])
    return Response(si.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=prod-metrics.csv"})

@prod_bp.route("/export.xlsx")
def export_xlsx():
    df = pd.DataFrame([[r.get(k,"") for k,_ in COLUMNS] for r in _STATE["rows"]],
                      columns=[title for _,title in COLUMNS])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return Response(buf.getvalue(),
        headers={"Content-Disposition":"attachment; filename=prod-metrics.xlsx"},
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
