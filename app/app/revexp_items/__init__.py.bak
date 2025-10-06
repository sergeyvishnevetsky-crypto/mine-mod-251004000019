from flask import Blueprint, render_template, jsonify, send_file, request
import io
import pandas as pd

revexp_bp = Blueprint("revexp_items", __name__, template_folder="templates")

# Простейшее in-memory «хранилище» на случай пустых данных
_SAMPLE = [
    {"type": "Доход",   "code": "R-001", "name": "Выручка от продаж", "cfo": "ЦФО-1"},
    {"type": "Расход",  "code": "E-001", "name": "Аренда",            "cfo": "ЦФО-2"},
]

@revexp_bp.get("/")
def index():
    return render_template("revexp_items/index.html", rows=_SAMPLE)

@revexp_bp.get("/params")
def params():
    return jsonify({
        "title": "Статьи доходов и расходов",
        "columns": [
            {"key": "type", "title": "Тип (Доход/Расход)"},
            {"key": "code", "title": "Код статьи"},
            {"key": "name", "title": "Статья"},
            {"key": "cfo",  "title": "Центр финансовой ответственности"},
        ],
        "endpoints": {
            "index": "/dict/revexp-items/",
            "params": "/dict/revexp-items/params",
            "export_csv": "/dict/revexp-items/export.csv",
            "export_xlsx": "/dict/revexp-items/export.xlsx",
            "template_xlsx": "/dict/revexp-items/template.xlsx",
            "import": "/dict/revexp-items/import",
        },
    })

def _to_dataframe(rows):
    return pd.DataFrame(rows, columns=["type","code","name","cfo"])

@revexp_bp.get("/export.csv")
def export_csv():
    df = _to_dataframe(_SAMPLE)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    data = buf.getvalue().encode("utf-8")
    return send_file(io.BytesIO(data), mimetype="text/csv",
                     as_attachment=True, download_name="revexp-items.csv")

@revexp_bp.get("/export.xlsx")
def export_xlsx():
    df = _to_dataframe(_SAMPLE)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="revexp")
    buf.seek(0)
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="revexp-items.xlsx")

@revexp_bp.get("/template.xlsx")
def template_xlsx():
    df = pd.DataFrame(columns=["Тип (Доход/Расход)", "Код статьи", "Статья", "ЦФО"])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="template")
    buf.seek(0)
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="revexp-template.xlsx")

@revexp_bp.post("/import")
def import_post():
    # Заглушка: возвращаем, что импорт принят (без сохранения)
    # Чтобы не падало при вызове из формы
    return jsonify({"status": "ok", "imported_rows": 0})
