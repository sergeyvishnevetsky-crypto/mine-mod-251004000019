from flask import Blueprint, render_template, jsonify, send_file
from io import BytesIO
import csv

try:
    import pandas as pd
except Exception:
    pd = None

product_metrics_bp = Blueprint(
    "product_metrics",
    __name__,
    template_folder="templates",
)

COLUMNS = [
    {"key":"code",     "title":"Код",        "type":"str",  "required":True},
    {"key":"brand",    "title":"Марка",      "type":"str",  "required":True},
    {"key":"fraction", "title":"Фракция",    "type":"str",  "required":True},
    {"key":"ash",      "title":"Зола,%",     "type":"num",  "required":False},
    {"key":"moist",    "title":"Влага,%",    "type":"num",  "required":False},
    {"key":"sulfur",   "title":"Сера,%",     "type":"num",  "required":False},
    {"key":"status",   "title":"Статус",     "type":"str",  "required":False, "enum":["активен","архив"]},
]

@product_metrics_bp.get("/")
def index():
    return render_template("product_metrics/index.html",
                           title="Показатели готовой продукции", columns=COLUMNS)

@product_metrics_bp.get("/params")
def params():
    return jsonify({
        "title": "Показатели готовой продукции",
        "columns": COLUMNS,
        "import": {"accept": [".csv", ".xlsx"]},
        "export": {"csv": True, "xlsx": True},
        "notes": "Импорт: code,brand,fraction,ash,moist,sulfur,status",
    })

@product_metrics_bp.get("/template.xlsx")
def template_xlsx():
    headers = [c["key"] for c in COLUMNS]
    buf = BytesIO()
    if pd is not None:
        pd.DataFrame(columns=headers).to_excel(buf, index=False)
    else:
        tmp = BytesIO()
        cw = csv.writer(tmp); cw.writerow(headers)
        buf.write(tmp.getvalue())
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name="product-metrics-template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@product_metrics_bp.get("/export.csv")
def export_csv():
    headers = [c["key"] for c in COLUMNS]
    buf = BytesIO()
    cw = csv.writer(buf); cw.writerow(headers)
    return send_file(BytesIO(buf.getvalue()), as_attachment=True,
                     download_name="product-metrics.csv", mimetype="text/csv")
