from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
import os, io
import pandas as pd

revexp_bp = Blueprint("revexp_items", __name__, template_folder="templates")

STORE = os.environ.get("REVEXP_STORE", "/tmp/revexp_items.csv")
COLS  = ["code","type","name","cfo","vat","status"]

def load_df():
    if os.path.exists(STORE):
        df = pd.read_csv(STORE, dtype=str).fillna("")
    else:
        df = pd.DataFrame(columns=COLS)
    # нормализуем набор столбцов
    for c in COLS:
        if c not in df.columns:
            df[c] = ""
    return df[COLS].copy()

def save_df(df: pd.DataFrame):
    df = df[COLS].fillna("")
    df.to_csv(STORE, index=False)

@revexp_bp.route("/", methods=["GET","POST"])
def index():
    # импорт файлов, если пришёл
    if request.method == "POST" and "file" in request.files:
        f = request.files["file"]
        if f and f.filename:
            try:
                if f.filename.lower().endswith(".xlsx"):
                    xls = pd.read_excel(f)
                else:
                    xls = pd.read_csv(f)
                xls.columns = [str(c).strip().lower() for c in xls.columns]
                # маппим распространённые заголовки
                rename = {
                    "код":"code", "тип":"type", "статья":"name", "цфо":"cfo",
                    "vat":"vat", "ндс":"vat", "статус":"status"
                }
                xls = xls.rename(columns=rename)
                xls = xls[[c for c in COLS if c in xls.columns]]
                df = load_df()
                # upsert по code
                for _, r in xls.iterrows():
                    rec = {c: str(r.get(c,"") or "") for c in COLS}
                    if not rec["code"]:
                        continue
                    mask = df["code"] == rec["code"]
                    if mask.any():
                        for c in COLS:
                            df.loc[mask, c] = rec[c]
                    else:
                        df.loc[len(df)] = [rec[c] for c in COLS]
                save_df(df)
                flash("Импорт выполнен", "success")
                return redirect(url_for(".index"))
            except Exception as e:
                flash(f"Ошибка импорта: {e}", "danger")
                return redirect(url_for(".index"))

    # фильтры
    df = load_df()
    q = (request.args.get("q","") or "").strip().lower()
    t = (request.args.get("type","") or "").strip()
    if t:
        df = df[df["type"] == t]
    if q:
        df = df[df.apply(lambda r: q in (r["code"]+r["name"]+r["cfo"]).lower(), axis=1)]
    items = [dict(r) for _, r in df.iterrows()]
    return render_template("revexp_items/index.html", items=items)

@revexp_bp.post("/add")
def add():
    form = {c: (request.form.get(c,"") or "").strip() for c in COLS}
    if not form["code"]:
        flash("Код обязателен", "danger")
        return redirect(url_for(".index"))
    df = load_df()
    mask = df["code"] == form["code"]
    if mask.any():
        for c in COLS:
            df.loc[mask, c] = form[c]
        msg = "Запись обновлена"
    else:
        df.loc[len(df)] = [form[c] for c in COLS]
        msg = "Запись добавлена"
    save_df(df)
    flash(msg, "success")
    return redirect(url_for(".index"))

@revexp_bp.post("/delete/<code>")
def delete(code):
    df = load_df()
    before = len(df)
    df = df[df["code"] != code]
    save_df(df)
    flash("Удалено" if len(df) < before else "Не найдено", "info")
    return redirect(url_for(".index"))

@revexp_bp.get("/params")
def params():
    return jsonify({"columns": COLS, "store": STORE})

@revexp_bp.get("/export.csv")
def export_csv():
    df = load_df()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode("utf-8")), as_attachment=True,
                     download_name="revexp.csv", mimetype="text/csv")

@revexp_bp.get("/export.xlsx")
def export_xlsx():
    df = load_df()
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="revexp", index=False)
    out.seek(0)
    return send_file(out, as_attachment=True,
                     download_name="revexp.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@revexp_bp.get("/template.xlsx")
def template_xlsx():
    df = pd.DataFrame(columns=COLS)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="template", index=False)
    out.seek(0)
    return send_file(out, as_attachment=True,
                     download_name="revexp-template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
